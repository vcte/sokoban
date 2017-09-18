# functions for generating data

import os
from random import choice

from constants import *
from deadlock import *
from file import *
from solver import *
from sokoban import *
from util import *

puzzles_dir = "puzzles/i2a_generated"
n_puzzles = 1000

deadlock_basis_file = "deadlock_basis.txt"
deadlock_table_file = "deadlock_table.txt"
deadlock_data_dir = "deadlock_data"

def gen_deadlock_table_from_basis(area = (4, 5),
                                  deadlock_basis_file = deadlock_basis_file,
                                  deadlock_table_file = deadlock_table_file,
                                  quiet = True):
    if os.path.exists(deadlock_table_file) and \
       os.path.getsize(deadlock_table_file) > 0:
        print("Warning: appending to a table file with existing content")
    
    deadlock_basis = parse_deadlock_table(deadlock_basis_file)
    total_configs = 3 ** (area[0] * area[1])
    with open(deadlock_table_file, mode = "a", encoding = "utf-8") as f:
        for i, board in enumerate(
            generate_board_configs(area = area, objs = [SPACE, WALL, BOX])):
            if total_configs > 1000 and i % int(total_configs // 1000) == 0:
                quiet or print(str(i / (total_configs // 100)) + "%")
            if subboard_matches(deadlock_basis, board):
                f.write(str(board) + "\n")

def gen_deadlock_data(deadlock_table_file = deadlock_table_file,
                      deadlock_data_dir = deadlock_data_dir):
    deadlock_table = parse_deadlock_table(deadlock_table_file)
    deadlock_heuristic = DeadlockHeuristic(deadlock_table)
    heuristic = ManhattanDistHeuristic().max(deadlock_heuristic)
    astar = AStarSolver(heuristic = heuristic)
    for i in range(1, n_puzzles + 1):
        print("puzzle #" + str(i))
        sokoban_file = puzzles_dir + "/gen_" + str(i) + ".txt"
        sokoban = parse_puzzle(sokoban_file)
        for j in range(5):
            # pick random puzzle state from solution path
            solution = astar.solve(sokoban, state = j)
            sokoban_no_deadlock = choice(solution[::2])
            negative_data_file = deadlock_data_dir + \
                                 "/negative/puzzle_%d_%d.txt" % (i, j)
            with open(negative_data_file, mode = "w", encoding = "utf-8") as f:
                f.write(str(sokoban_no_deadlock))

            # pick random puzzle state with deadlock from visited set
            for sokoban_ in astar.visited:
                if deadlock_heuristic.evaluate(sokoban_) == inf:
                    positive_data_file = deadlock_data_dir + \
                                         "/positive/puzzle_%d_%d.txt" % (i, j)
                    with open(positive_data_file,
                              mode = "w", encoding = "utf-8") as f:
                        f.write(str(sokoban_))
                    break
