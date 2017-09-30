from abc import ABC, abstractmethod
import time
import heapq
import numpy as np

from math import *
from random import *
from scipy import optimize

from constants import *
from sokoban import *
from util import *

# functions

def trace_history(prev, sokoban):
    """retrace steps from goal state to start state"""
    history = [sokoban]
    while prev[sokoban] is not None:
        sokoban, action = prev[sokoban]
        history = [sokoban, action] + history
    return history

# classes

class Solver(ABC):
    @abstractmethod
    def solve(self, sokoban):
        """input: sokoban puzzle
           output: list that alternates btwn state, action, state ...
        """
        pass

class WFSSolver(Solver):
    # whatever-first search (i.e., uninformed search)
    def solve(self, sokoban, max_nodes = 10 ** 6, state = None, quiet = True):
        # first move player to normalized position
        sokoban = sokoban.copy()
        sokoban.player = sokoban.get_normalized_player_position()
        if state is not None:
            seed(state)
        
        self.frontier = frontier = self.data_structure([sokoban])
        self.visited = visited = set([sokoban])
        self.prev = prev = { sokoban : None }
        
        while len(frontier) > 0 and len(visited) < max_nodes:
            sokoban = frontier.get()

            if sokoban.solved():
                quiet or print("visited: " + str(len(visited)))
                return trace_history(prev, sokoban)

            neighbors = list(sokoban.neighbors)
            shuffle(neighbors)
            for sokoban_, action in neighbors:
                if sokoban_ not in visited:
                    frontier.add(sokoban_)
                    visited.add(sokoban_)
                    prev[sokoban_] = (sokoban, action)

        return None

class Queue(list):
    def add(self, item):
        self.append(item)

    def get(self):
        return self.pop(0)

class Stack(list):
    def add(self, item):
        self.append(item)

    def get(self):
        return self.pop()

class BFSSolver(WFSSolver):
    # breadth-first search
    def data_structure(self, init = []):
        return Queue(init)

class DFSSolver(WFSSolver):
    # depth-first search
    def data_structure(self, init = []):
        return Stack(init)

class Heuristic(ABC):
    def __init__(self):
        self._max_with = []
        
    @abstractmethod
    def _evaluate(self, sokoban):
        pass

    def evaluate(self, sokoban):
        value = self._evaluate(sokoban)
        for heuristic in self._max_with:
            value = max(value, heuristic.evaluate(sokoban))
        return value

    def max(self, heuristic):
        """combine two heuristics in a way that maintains admissibility"""
        self._max_with.append(heuristic)
        return self

class NoHeuristic(Heuristic):
    def _evaluate(self, sokoban):
        # a* search becomes djikstra's search when h(x) = 0
        return 0

class RemainingBoxesHeuristic(Heuristic):
    def _evaluate(self, sokoban):
        # count the number of boxes that are not on top of a goal
        return sum([int(box not in sokoban.goals)
                    for box in sokoban.board.boxes])

class ManhattanDistHeuristic(Heuristic):
    def _evaluate(self, sokoban):
        # use manhattan distance from each box to closest goal as lower bound
        distance = 0
        for box in sokoban.board.boxes:
            min_dist = min([manhattan_dist(box, goal)
                            for goal in sokoban.goals])
            distance += min_dist
        return distance

class MinMatchingHeuristic(Heuristic):
    def _evaluate(self, sokoban):
        # solve minimum matching problem using hungarian algorithm
        costs = [[manhattan_dist(box, goal)
                  for goal in sokoban.goals]
                 for box in sokoban.board.boxes]
        cost_matrix = np.array(costs, dtype = np.uint8)
        row_ind, col_ind = optimize.linear_sum_assignment(cost_matrix)
        return cost_matrix[row_ind, col_ind].sum()

class DeadlockHeuristic(Heuristic):
    def __init__(self, deadlock_table = {}):
        super(DeadlockHeuristic, self).__init__()
        self.deadlock_table = deadlock_table
        
    def _evaluate(self, sokoban):
        # heuristic value is inf if deadlock detected, else defaults to 0
        # boxes that are on top of goal do not count towards deadlock
        board = sokoban.board.copy()
        for goal in sokoban.goals:
            board[goal] = SPACE

        # lookup all subboards in deadlock table, for each subboard size
        for area in self.deadlock_table:
            if subboard_in_deadlock_table(self.deadlock_table[area],
                                          sokoban, area):
                return inf
        return 0

class GreedyBestFSSolver(Solver):
    def __init__(self, heuristic = RemainingBoxesHeuristic()):
        self.heuristic = heuristic

    def solve(self, sokoban, max_nodes = 10 ** 6, quiet = True):
        sokoban = sokoban.copy()
        sokoban.player = sokoban.get_normalized_player_position()

        self.frontier = frontier = [sokoban]
        self.visited = visited = set(frontier)
        self.prev = prev = { sokoban : None }

        while len(frontier) > 0 and len(visited) < max_nodes:
            sokoban = frontier.pop()

            if sokoban.solved():
                quiet or print("visited: " + str(len(visited)))
                return trace_history(prev, sokoban)

            neighbors = []
            for sokoban_, action in sokoban.neighbors:
                if sokoban_ not in visited:
                    neighbors.append(sokoban_)
                    visited.add(sokoban_)
                    prev[sokoban_] = (sokoban, action)

            neighbors = list(sorted(neighbors, key = self.heuristic.evaluate,
                                    reverse = True))
            frontier.extend(neighbors)

        return None

class AStarSolver(Solver):
    def __init__(self, heuristic = NoHeuristic()):
        self.heuristic = heuristic

    def solve(self, sokoban, max_nodes = 10 ** 6, state = None, quiet = True):
        sokoban = sokoban.copy()
        sokoban.player = sokoban.get_normalized_player_position()
        if state is not None:
            seed(state)
        
        # total distance from start to goal for each node found so far
        self.tot_dist_map = tot_dist_map = \
                            { sokoban : self.heuristic.evaluate(sokoban) }

        # least distance from start node to each node found so far
        self.cur_dist_map = cur_dist_map = { sokoban : 0 }
        
        # heap containing (current dist + estimated dist to goal, sokoban) pairs
        self.frontier = frontier = [(tot_dist_map[sokoban], sokoban)]

        # set of visited sokoban problem instances
        self.visited = visited = set([sokoban])

        # mapping from puzzle instance to state + action that produced it
        self.prev = prev = { sokoban : None }
        
        while len(frontier) > 0 and len(visited) < max_nodes:
            # skip if node is outdated
            tot_dist, sokoban = heapq.heappop(frontier)
            if tot_dist != tot_dist_map[sokoban]:
                continue

            # check if goal has been reached
            if sokoban.solved():
                quiet or print("visited: " + str(len(visited)))
                return trace_history(prev, sokoban)
            visited.add(sokoban)

            neighbors = list(sokoban.neighbors)
            shuffle(neighbors)
            cur_dist = cur_dist_map[sokoban]
            for sokoban_, action in neighbors:
                if sokoban_ in visited:
                    continue

                # skip if solution is not as good as the one already found
                dist = cur_dist + 1
                if not dist < cur_dist_map.get(sokoban_, inf):
                    continue

                cur_dist_map[sokoban_] = dist
                tot_dist_map[sokoban_] = dist + \
                                         self.heuristic.evaluate(sokoban_)
                heapq.heappush(frontier, (tot_dist_map[sokoban_], sokoban_))
                prev[sokoban_] = (sokoban, action)

        return None
