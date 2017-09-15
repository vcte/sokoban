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

def subboard_matches(patterns, board):
    # check if any pattern in list matches part of board
    # iterate over all rotational / reflected variants of patterns
    for pattern in patterns:
        for pattern_ in pattern.isometric_boards:
            # TODO: optimize by using convolution? 
            for dx in range(board.cols - pattern_.cols + 1):
                for dy in range(board.rows - pattern_.rows + 1):
                    subboard = board[dy : dy + pattern_.rows,
                                     dx : dx + pattern_.cols]
                    if (subboard | pattern_) == subboard:
                        return True
    return False

def subboard_in_lookup_table(patterns, board, area):
    # check if any pattern in list matches part of board
    # iterate over subboards of size (area) and lookup pattern in table
    for dx in range(board.cols - area[1] + 1):
        for dy in range(board.rows - area[0] + 1):
            subboard = board[dy : dy + area[0], dx : dx + area[1]]
            if subboard in patterns:
                return True
    return False
