# functions for generating data

import os
import array
from math import *
from random import choice
from itertools import product

from constants import *
from deadlock import *
from file import *
from solver import *
from sokoban import *
from util import *

puzzles_dir = "puzzles/i2a_generated"
n_puzzles = 1000

deadlock_basis_file = "deadlock_basis.txt"
deadlock_table_file = "deadlock_table"
deadlock_data_dir = "deadlock_data"

def gen_deadlock_table_from_basis(max_area = (4, 5),
                                  deadlock_basis_file = deadlock_basis_file,
                                  deadlock_table_file = deadlock_table_file,
                                  max_boxes = inf,
                                  quiet = True):
    if os.path.exists(deadlock_table_file) and \
       os.path.getsize(deadlock_table_file) > 0:
        print("Warning: appending to a table file with existing content")
    
    deadlock_basis = parse_deadlock_table(deadlock_basis_file)
    deadlock_patterns = {}
    for board in deadlock_basis:
        area = board.shape
        for board_ in board.isometric_boards:
            spaces = list(board_.spaces)
            for config in product(*([(SPACE, WALL, BOX)] * len(spaces))):
                board__ = board_.copy()
                for space, obj in zip(spaces, config):
                    board__[space] = obj
                mapping = deadlock_patterns.get(area, set())
                mapping.add(board__)
                deadlock_patterns[area] = mapping

    print(str(len(deadlock_patterns)) + " areas in dict")
    for area in deadlock_patterns:
        print(str(len(deadlock_patterns[area])) + " elements in " + str(area))

    def deadlock_detected(board):
        for area in deadlock_patterns:
            for dx in range(board.cols - area[1] + 1):
                for dy in range(board.rows - area[0] + 1):
                    subboard = board[dy : dy + area[0], dx : dx + area[1]]
                    if subboard in deadlock_patterns[area]:
                        return True
        return False
    
    total_configs = 3 ** (max_area[0] * max_area[1])
    with open(deadlock_table_file, mode = "ab") as f:
        for i, board in enumerate(
            generate_board_configs(area = max_area, objs = [SPACE, WALL, BOX])):
            if i % int(total_configs // 10000) == 0:
                quiet or print(str(i / (total_configs // 100)) + "%")
            if len(list(board.boxes)) > max_boxes:
                continue

            if deadlock_detected(board):
                # formats other than (4, 5) are not supported currently
                f.write(array.array('L', [board.encode()]))
            
def gen_deadlock_data(deadlock_table_file = deadlock_table_file,
                      deadlock_data_dir = deadlock_data_dir):
    deadlock_table = parse_deadlock_table(deadlock_table_file)
    area = next(iter(deadlock_table)).shape
    deadlock_heuristic = DeadlockHeuristic({ area : deadlock_table })
    heuristic = ManhattanDistHeuristic().max(deadlock_heuristic)
    astar = AStarSolver(heuristic = heuristic)
    bfs = BFSSolver()
    for i in range(2001, 3001): #(1, n_puzzles + 1):
        print("puzzle #" + str(i))
        sokoban_file = puzzles_dir + "/gen_" + str(i) + ".txt"
        sokoban = parse_puzzle(sokoban_file)
        positive_cases = []
        negative_cases = []
        optimal_distances = []
        for j in range(5):
            print(" A star seed: " + str(j))
            # pick random puzzle state from solution path of A*
            solution = astar.solve(sokoban, state = j)
            solution_states = solution[::2]
            shuffle(solution_states)
            for sokoban_ in solution_states:
                if sokoban_ not in negative_cases:
                    negative_cases.append(sokoban_)
                    dist = (len(solution) - solution.index(sokoban_) - 1) // 2
                    optimal_distances.append(dist)
                    negative_data_file = deadlock_data_dir + \
                                         "/negative/puzzle_%d_%d.txt" % (i, j)
                    with open(negative_data_file,
                              mode = "w", encoding = "utf-8") as f:
                        f.write(str(sokoban_))
                    break
            else:
                print("Negative case not found: %d, %d" % (i, j))
                optimal_distances.append(inf)
            
            # pick random puzzle state with deadlock from visited set of BFS
            bfs.solve(sokoban, max_nodes = 10 ** 3, state = j)
            visited = list(bfs.visited)
            shuffle(visited)
            for sokoban_ in visited:
                if sokoban_ not in positive_cases and \
                   deadlock_heuristic.evaluate(sokoban_) == inf:
                    positive_cases.append(sokoban_)
                    positive_data_file = deadlock_data_dir + \
                                         "/positive/puzzle_%d_%d.txt" % (i, j)
                    with open(positive_data_file,
                              mode = "w", encoding = "utf-8") as f:
                        f.write(str(sokoban_))
                    break
            else:
                print("Postive case not found: %d, %d" % (i, j))

        with open(deadlock_data_dir + "/distances.txt",
                  mode = "a", encoding = "utf-8") as f:
            f.write(" ".join(map(str, optimal_distances)) + "\n")

# TODO - regenerate positive data w/ BFS solver
# update deadlock table w/ (3, 4) basis
# regenerate negative data using deadlock heuristic w/ new deadlock table
