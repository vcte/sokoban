# utility functions

from constants import *
from sokoban import *

def parse_puzzle(file_path, game_encoding = microban_encoding):
    array = []
    game_decoding = {game_encoding[k] : k for k in game_encoding}
    with open(file_path, mode = "r", encoding = "utf-8") as f:
        for line in f.readlines():
            array.append([game_decoding.get(c, SPACE) for c in line])

    # zero-pad the right side of each row to have equal width
    max_length = max([len(row) for row in array])
    array = [row + [SPACE] * (max_length - len(row)) for row in array]
    board = Board((len(array), max_length))
    board[:] = array

    # figure out where the player, goals are on the board
    player = None
    goals = []
    for r, c in board.positions:
        if board[r, c] & PLAYER:
           player = Position(r, c)
           board[r, c] ^= PLAYER
        if board[r, c] & GOAL:
            goals.append(Position(r, c))
            board[r, c] ^= GOAL
    return Sokoban(board, player, goals)

def parse_deadlock_table(file_path):
    table = set()
    with open(file_path, mode = "r", encoding = "utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            row = line.replace(" ", "").strip("[]")
            if line.startswith("[["):
                current_board = []
            current_board.append(list(row))
            if line.endswith("]]"):
                table.add(Board.from_array(current_board))
    return table
