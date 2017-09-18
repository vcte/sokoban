# deadlock basis and table generation

import time

from constants import *
from file import *
from sokoban import *
from solver import *

def build_area_containment_mapping(max_area = (4, 5)):
    """"area of size i x j, i <= j, where i is #rows and j is #cols
       is said to directly contain area of size i' x j' if and only if
       i' = i - 1 or j' = j - 1, but not both
    """
    contained_by = { max_area : [] }
    if max_area == (2, 2):
        return contained_by
    sub_area_1 = tuple(sorted([max(max_area[0] - 1, 2), max_area[1]]))
    sub_area_2 = tuple(sorted([max_area[0], max(max_area[1] - 1, 2)]))
    for sub_area in [sub_area_1, sub_area_2]:
        if sub_area not in contained_by:
            sub_map = build_area_containment_mapping(sub_area)
            sub_map[sub_area] += [max_area]
            for area in sub_map:
                contained_by[area] = contained_by.get(area, [])
                for sup_area_ in sub_map[area]:
                    if sup_area_ not in contained_by[area]:
                        contained_by[area].append(sup_area_)
    return contained_by

def generate_board_configs(area, objs = [SPACE, WALL]):
    # TODO: enumerate boards w/ 0 walls, then 1 walls, ...
    def generate_board_configs_(row, col):
        if row < 0 or col < 0:
            yield np.zeros(area, dtype = np.uint8)
            return

        if col == 0:
            col_ = area[1] - 1
            row_ = row - 1
        else:
            col_ = col - 1
            row_ = row
        
        for board_array in generate_board_configs_(row_, col_):
            for obj in objs:
                board_array_ = board_array.copy()
                board_array_[row, col] = obj
                yield board_array_

    for board_array in generate_board_configs_(area[0] - 1, area[1] - 1):
        yield Board.from_array(board_array)

@record_time
def generate_deadlock_basis(max_area = (4, 5), max_box = 4, quiet = True):
    """generate a minimal set of deadlock patterns"""
    contained_by = build_area_containment_mapping(max_area)
    contains = {}
    for area in contained_by:
        contains[area] = contains.get(area, [])
        for sup_area in contained_by[area]:
            contains[sup_area] = contains.get(sup_area, []) + [area]

    # maps from { area : set([deadlocked boards ...]) }
    deadlock_basis = {}

    @record_time
    def get_all_subareas(area):
        # get all subareas contained directly or recursively by area
        # includes area itself
        all_subareas = [area]
        if area not in contains or len(contains[area]) == 0:
            return all_subareas
        
        for subarea in contains[area]:
            for subarea_ in get_all_subareas(subarea):
                if subarea_ not in all_subareas:
                    all_subareas.append(subarea_)
        return all_subareas

    @record_time
    def check_subboard_deadlock(area, board):
        for subarea in reversed(get_all_subareas(area)):
            if subboard_matches(deadlock_basis[subarea], board):
                return True
        return False

    @record_time
    def board_in_deadlock(board):
        """determine if board is in dynamic deadlock"""
        # embed board in larger board w/ 1-space padding
        board = Board.from_array(np.pad(board, 1, 'constant',
                                        constant_values = SPACE))
        sokoban = Sokoban(board, player = Position(0, 0), goals = [])

        # check if it is possible to push all boxes off the board
        gbfs_solver = GreedyBestFSSolver()
        solution = gbfs_solver.solve(sokoban, max_nodes = 10 ** 4)
        if solution is None:
            heuristic = DeadlockHeuristic(deadlock_basis) \
                        .max(RemainingBoxesHeuristic())
            astar_solver = AStarSolver(heuristic)
            solution = astar_solver.solve(sokoban, max_nodes = 10 ** 5)
            return solution is None

    @record_time
    def add_box_and_test_deadlock(area, board, box_index = 0, n_box = max_box):
        """recursively add boxes and determine if board is in deadlock state"""
        for i, box in list(enumerate(board.positions))[box_index :]:
            board_ = board.copy()
            board_[box] = BOX
            if check_subboard_deadlock(area, board_):
                continue

            if board_in_deadlock(board_):
                for possibly_redundant_board in deadlock_basis[area].copy():
                    if subboard_matches([board_], possibly_redundant_board):
                        deadlock_basis[area].remove(possibly_redundant_board)

                deadlock_basis[area].add(board_)
                print(str(board_))

            if n_box > 1:
                add_box_and_test_deadlock(area, board_, i + 1, n_box - 1)

    # choose areas in topological order def by containment relation
    while len(deadlock_basis) < len(contains):
        # choose area s.t. deadlock table has been filled in for both subareas
        area = [area for area in contains
                if area not in deadlock_basis
                and all([sub_area in deadlock_basis
                         for sub_area in contains[area]])][0]
        deadlock_basis[area] = set()
        print("area: " + str(area))

        total_configs = 2 ** (area[0] * area[1])
        for i, board in enumerate(generate_board_configs(area)):
            if total_configs > 100 and i % int(total_configs // 100) == 0:
                quiet or print(str(i / (total_configs // 100)) + "%")
            add_box_and_test_deadlock(area, board)

    return deadlock_basis
