# deadlock basis and table generation

import time
from itertools import product

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

def build_inverse_area_containment_mapping(max_area = (4, 5)):
    """returns mapping of { area : [all subareas directly contained by area] }
    """
    contained_by = build_area_containment_mapping(max_area)
    contains = {}
    for area in contained_by:
        contains[area] = contains.get(area, [])
        for sup_area in contained_by[area]:
            contains[sup_area] = contains.get(sup_area, []) + [area]
    return contains

def next_area_in_topo_order(contains, area_list):
    return [area for area in contains
            if area not in area_list
            and all([sub_area in area_list for sub_area in contains[area]])][0]

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
def gen_deadlock_table_from_basis_same_size(deadlock_basis):
    """input: list of boards in deadlock state
       output: mapping from { area : set(board, ...) }
    """
    deadlock_table = {}
    for board in deadlock_basis:
        area = board.shape
        for board_ in board.isometric_boards:
            spaces = list(board_.spaces)
            for config in product(*([(SPACE, WALL, BOX)] * len(spaces))):
                board__ = board_.copy()
                for space, obj in zip(spaces, config):
                    board__[space] = obj
                mapping = deadlock_table.get(area, set())
                mapping.add(board__)
                deadlock_table[area] = mapping
    return deadlock_table

def subboard_matches(patterns, board):
    # check if any pattern in list matches part of board
    # iterate over all rotational / reflected variants of patterns
    for pattern in patterns:
        for pattern_ in pattern.isometric_boards:
            # check if pattern matches part of the board
            # TODO: optimize by using convolution? 
            for dx in range(board.cols - pattern_.cols + 1):
                for dy in range(board.rows - pattern_.rows + 1):
                    subboard = board[dy : dy + pattern_.rows,
                                     dx : dx + pattern_.cols]
                    if (subboard | pattern_) == subboard:
                        return True
    return False

def generate_dynamic_deadlock_basis(max_area = (4, 5), max_box = 4,
                                    current_basis = None, quiet = True):
    """generate a minimal set of deadlock patterns"""
    contains = build_inverse_area_containment_mapping(max_area)

    # maps from { area : set([deadlocked boards ...]) }
    deadlock_basis = {}
    deadlock_table = {}
    if current_basis is not None:
        # initialize basis with basis that has been previously generated
        basis = parse_deadlock_table(current_basis)
        for board in basis:
            area = tuple(board.shape)
            deadlock_basis[area] = deadlock_basis.get(area, set())
            deadlock_basis[area].add(board)
            table = gen_deadlock_table_from_basis_same_size([board])[area]
            deadlock_table[area] = deadlock_table.get(area, set()).union(table)

    @record_time
    def board_in_dynamic_deadlock(board):
        """determine if board is in dynamic deadlock,
           i.e. if it is possible to push all boxes off of the board
        """
        # embed board in larger board w/ 1-space padding
        board = Board.from_array(np.pad(board, 1, 'constant',
                                        constant_values = SPACE))
        sokoban = Sokoban(board, player = Position(0, 0), goals = [])

        # check if it is possible to push all boxes off the board
        gbfs_solver = GreedyBestFSSolver(RemainingBoxesHeuristic())
        solution = gbfs_solver.solve(sokoban, max_nodes = 10 ** 4)
        if solution is None:
            heuristic = DynamicDeadlockHeuristic(deadlock_table) \
                        .max(RemainingBoxesHeuristic())
            astar_solver = AStarSolver(heuristic)
            solution = astar_solver.solve(sokoban, max_nodes = 10 ** 5)
            return solution is None

    @record_time
    def add_box_and_test_deadlock(area, board, box_index = 0, n_box = max_box):
        """recursively add boxes and determine if board is in deadlock state"""
        for i, box in list(enumerate(board.positions))[box_index :]:
            if board[box] != SPACE:
                continue
            board_ = board.copy()
            board_[box] = BOX
            if deadlock_detected(deadlock_table, Sokoban(board_), None):
                continue

            if board_in_dynamic_deadlock(board_):
                for possibly_redundant_board in deadlock_basis[area].copy():
                    if subboard_matches([board_], possibly_redundant_board):
                        deadlock_basis[area].remove(possibly_redundant_board)

                deadlock_basis[area].add(board_)
                patterns = gen_deadlock_table_from_basis_same_size([board_])
                deadlock_table[area] = deadlock_table[area] \
                                       .union(patterns[area])
                print(str(board_), flush = True)

            elif n_box > 1:
                add_box_and_test_deadlock(area, board_, i + 1, n_box - 1)

    # choose areas in topological order def by containment relation
    while len(deadlock_basis) < len(contains):
        # choose area s.t. deadlock table has been filled in for both subareas
        area = next_area_in_topo_order(contains, deadlock_basis)
        deadlock_basis[area] = set()
        deadlock_table[area] = set()
        print("area: " + str(area), flush = True)

        total_configs = 2 ** (area[0] * area[1])
        one_perc = total_configs // 100
        for i, board in enumerate(generate_board_configs(area)):
            if total_configs > 100 and i % int(one_perc // 100) == 0:
                quiet or print(str(i / one_perc) + "%", flush = True)
            add_box_and_test_deadlock(area, board)

    return deadlock_basis

@record_time
def generate_static_deadlock_basis(max_area = (4, 5), max_box = 4,
                                   quiet = True):
    """generate a minimal set of deadlock patterns"""
    contains = build_inverse_area_containment_mapping(max_area)

    # maps from { area : set([deadlocked boards ...]) }
    deadlock_basis = {}
    deadlock_table = {}

    @record_time
    def board_in_static_deadlock(board):
        """determine if board is in static deadlock,
           i.e. if no box is stuck in a position where it cannot be moved
        """
        # embed board in larger board w/ 1-space padding
        board = Board.from_array(np.pad(board, 1, 'constant',
                                        constant_values = SPACE))
        sokoban = Sokoban(board, player = Position(0, 0),
                          goals = [Position(*p) for p in board.spaces])

        # check if it is possible to move all boxes to new position
        gbfs_solver = GreedyBestFSSolver(RemainingBoxesHeuristic())
        solution = gbfs_solver.solve(sokoban, max_nodes = 10 ** 3)
        if solution is None:
            astar_solver = AStarSolver(RemainingBoxesHeuristic())
            solution = astar_solver.solve(sokoban, max_nodes = 10 ** 4)
            # TODO: check individual boxes
            return solution is None

    @record_time
    def add_box_and_test_deadlock(area, board, box_index = 0, n_box = max_box):
        """recursively add boxes and determine if board is in deadlock state"""
        for i, box in list(enumerate(board.positions))[box_index :]:
            if board[box] != SPACE:
                continue
            board_ = board.copy()
            board_[box] = BOX
            if deadlock_detected(deadlock_table, Sokoban(board_), None):
                continue

            if board_in_static_deadlock(board_):
                for possibly_redundant_board in deadlock_basis[area].copy():
                    if subboard_matches([board_], possibly_redundant_board):
                        deadlock_basis[area].remove(possibly_redundant_board)

                deadlock_basis[area].add(board_)
                patterns = gen_deadlock_table_from_basis_same_size([board_])
                deadlock_table[area] = deadlock_table[area] \
                                       .union(patterns[area])
                print(str(board_), flush = True)

            elif n_box > 1:
                add_box_and_test_deadlock(area, board_, i + 1, n_box - 1)

    # choose areas in topological order def by containment relation
    while len(deadlock_basis) < len(contains):
        # choose area s.t. deadlock table has been filled in for both subareas
        area = next_area_in_topo_order(contains, deadlock_basis)
        deadlock_basis[area] = set()
        deadlock_table[area] = set()
        print("area: " + str(area), flush = True)

        total_configs = 2 ** (area[0] * area[1])
        one_perc = total_configs // 100
        for i, board in enumerate(generate_board_configs(area)):
            if total_configs > 100 and i % int(one_perc) == 0:
                quiet or print(str(i / one_perc) + "%", flush = True)
            add_box_and_test_deadlock(area, board)

    return deadlock_basis
