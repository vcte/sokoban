# utility functions

import time

from constants import *

def manhattan_dist(x, y):
    """calculate L1 distance between two iterables or Positions"""
    return sum([abs(a - b) for a, b in zip(x, y)])

def generate_unique(f):
    # decorator that ensures each output is generated at most one time
    def wrapper(*args):
        unique = []
        for item in f(*args):
            if item not in unique:
                unique.append(item)
        return iter(unique)
    return wrapper

timing_records = {}
timing_parents = {}
timing_current = set()
timing_active = None

def record_time(f):
    # associate name, parent function w/ list of timings
    global timing_records
    name = f.__name__
    records = timing_records.get(name)
    if records is None:
        records = timing_records[name] = []
    
    def wrapper_(*args, **kwargs):
        global timing_parents, timing_current, timing_active
        if name != timing_active:
            timing_parents[name] = timing_active
        last_active = timing_active
        timing_active = name

        if name not in timing_current:
            timing_current.add(name)
            t = time.time()
            ret = f(*args, **kwargs)
            records.append(time.time() - t)
            timing_current.remove(name)
        else:
            ret = f(*args, **kwargs)
        
        timing_active = last_active
        return ret
    return wrapper_

def print_timings(parent = None, indent = ""):
    for name in sorted(timing_records):
        if parent == timing_parents.get(name):
            records = timing_records[name]
            total = sum(records)
            print(indent + name + ": " + str(total))
            print_timings(name, indent + " ")

@record_time
def deadlock_detected(deadlock_table, sokoban, deadlock_type = None):
    """match every subboard against the deadlock lookup table
       input: deadlock_table: mapping from { area : set(board, ...) }
              sokoban: Sokoban object
              deadlock_type: "static" | "dynamic" | None
       output: boolean
    """
    for area in deadlock_table:
        # check if any pattern in list matches part of board
        # iterate over subboards of size (area) and lookup pattern in table
        for dx in range(sokoban.board.cols - area[1] + 1):
            for dy in range(sokoban.board.rows - area[0] + 1):
                if deadlock_type == "dynamic":
                    bounds = (dy, dy + area[0], dx, dx + area[1])
                    # skip if a goal is contained within the subboard
                    if any([goal.in_bounds(*bounds) for goal in sokoban.goals]):
                        continue
                elif deadlock_type == "static":
                    # skip if a box is on top of a goal
                    if any([sokoban.board[goal] == BOX
                            for goal in sokoban.goals]):
                        continue

                # look up the subboard in the deadlock table
                subboard = sokoban.board[dy : dy + area[0], dx : dx + area[1]]
                if subboard in deadlock_table[area]:
                    return True
    return False
