from abc import ABC, abstractmethod
import copy
import time
import numpy as np

from random import *
from skimage import measure

from constants import *
from util import *

# classes

class Action(ABC):
    @abstractmethod
    def act(self, game):
        pass

class KeyboardAction(Action):
    def __init__(self, key = None):
        self.key = key

    def act(self, game):
        direction = directions[self.key]

        # do nothing if player will move out of bounds
        bounds = game.board.bounds
        if not (game.player + direction).in_bounds(*bounds):
            return

        # do nothing if player will collide into a wall
        elif game.board[game.player + direction] == WALL:
            return

        # if player will move into a space, then move player
        elif game.board[game.player + direction] == SPACE:
            game.player += direction

        # if player will move into box, and empty space ahead,
        # then move player and box in direction
        # however, if object is in the way of box, then do nothing
        elif game.board[game.player + direction] & BOX:
            if not (game.player + direction + direction).in_bounds(*bounds):
                game.board[game.player + direction] ^= BOX
            elif game.board[game.player + direction + direction] == SPACE:
                game.board[game.player + direction] ^= BOX
                game.board[game.player + direction + direction] ^= BOX
            else:
                return

class BoxPushAction(Action):
    def __init__(self, box_position, direction):
        self.box_position = box_position
        self.direction = direction

    def act(self, game):
        # check legality of action
        if game.board[self.box_position] == BOX:
            bounds = game.board.bounds
            if not (self.box_position + self.direction).in_bounds(*bounds):
                # remove box from board
                game.player = self.box_position
                game.board[self.box_position] ^= BOX
            elif game.board[self.box_position + self.direction] == SPACE:
                # perform the box push
                game.player = self.box_position
                game.board[self.box_position] ^= BOX
                game.board[self.box_position + self.direction] ^= BOX

            # move player to new normalized position
            game.player = game.get_normalized_player_position()

    def __str__(self):
        return "box = " + str(self.box_position) + \
               ", dir = " + str(self.direction)

class Position:
    def __init__(self, row, col):
        self.row = int(row)
        self.col = int(col)

    def in_bounds(self, r_min, r_max, c_min, c_max):
        return r_min <= self.row < r_max and c_min <= self.col < c_max

    def copy(self):
        return Position(self.row, self.col)

    def __getitem__(self, index):
        if index == 0:
            return self.row
        elif index == 1 or index == -1:
            return self.col
        else:
            raise IndexError("Invalid index: " + str(index))

    def __setitem__(self, index, value):
        if index == 0:
            self.row = value
        elif index == 1 or index == -1:
            self.col = value
        else:
            raise IndexError("Invalid index: " + str(index))

    def __add__(self, pos):
        return Position(self.row + pos[0], self.col + pos[1])

    def __iadd__(self, pos):
        self.row += pos[0]
        self.col += pos[1]
        return self

    def __sub__(self, pos):
        return Position(self.row - pos[0], self.col - pos[1])

    def __isub__(self, pos):
        self.row -= pos[0]
        self.col -= pos[1]
        return self

    def __lt__(self, pos):
        return self[0] < pos[0] and self[1] < pos[1]

    def __eq__(self, pos):
        return self[0] == pos[0] and self[1] == pos[1]

    def __hash__(self):
        return 173 * self.row + 311 * self.col

    def __str__(self):
        return "(" + str(self.row) + ", " + str(self.col) + ")"

class Board(np.ndarray):
    # 2d array of walls + boxes. player + goals represented in separate var

    def __new__(self, shape):
        return super(Board, self).__new__(self, shape, dtype = np.uint8)

    @property
    def rows(self):
        return self.shape[0]

    @property
    def cols(self):
        return self.shape[1]

    @property
    def bounds(self):
        return (0, self.rows, 0, self.cols)

    @property
    def positions(self):
        for r in range(self.rows):
            for c in range(self.cols):
                yield (r, c)

    @property
    def spaces(self):
        return zip(*(self == SPACE).nonzero())

    @property
    def boxes(self):
        return zip(*(self == BOX).nonzero())

    @property
    @generate_unique
    def isometric_boards(self):
        """returns all boards that can be created from
           rotating + flipping this board, including itself"""
        for r in [0, 1]:
            yield np.rot90(self, r)
            yield np.rot90(np.flip(self, 0), r)
            yield np.rot90(np.flip(self, 1), r)
            yield np.rot90(np.flip(np.flip(self, 0), 1), r)

    @staticmethod
    def from_array(array):
        array = np.array(array, dtype = np.uint8)
        board = Board(array.shape)
        board[:] = array
        return board

    @staticmethod
    def from_encoding(code, shape):
        decoding = { 0 : SPACE, 1 : WALL, 2 : BOX }
        board = Board(shape)
        for r in range(shape[0]):
            for c in range(shape[1]):
                board[r, c] = decoding[code % 3]
                code = code // 3
        return board

    def in_bounds(self, position):
        return 0 <= position[0] < self.rows and 0 <= position[1] < self.cols

    def encode(self):
        encoding = { SPACE : 0, WALL : 1, BOX : 2 }
        return sum([encoding[self[r, c]] * (3 ** i)
                    for i, (r, c) in enumerate(self.positions)])

    def __getitem__(self, pos):
        """pos = either Position or (row, col) tuple"""
        if type(pos) is Position:
            return super(Board, self).__getitem__((pos[0], pos[1]))
        else:
            return super(Board, self).__getitem__(pos)

    def __setitem__(self, pos, value):
        if type(pos) is Position:
            super(Board, self).__setitem__((pos[0], pos[1]), value)
        else:
            super(Board, self).__setitem__(pos, value)

    def __eq__(self, board):
        if type(board) is Board:
            return self.shape == board.shape and \
                   super(Board, self).__eq__(board).all()
        else:
            return super(Board, self).__eq__(board)

    def __lt__(self, board):
        if type(board) is Board:
            return self.shape == board.shape and \
                   super(Board, self).__lt__(board).all()
        else:
            return super(Board, self).__lt__(board)

    def __hash__(self):
        return hash(self.tostring())

class Sokoban:
    def __init__(self, board = [], player = None, goals = []):
        # board is row x col array of numerical constants
        self.board = board

        # player is position with row, col information
        self.player = player

        # goals are list of positions
        self.goals = goals

    def copy(self):
        return Sokoban(self.board.copy(), self.player.copy(),
                       [goal.copy() for goal in self.goals])

    def solved(self):
        return all([box in self.goals for box in self.board.boxes])

    @property
    def neighbors(self):
        for action in self.get_push_actions():
            sokoban_ = self.copy()
            action.act(sokoban_)
            yield sokoban_, action

    def get_player_reachable_positions(self):
        # perform flood fill to get spaces reachable from player position
        labels = measure.label(self.board, background = -1, connectivity = 1)
        label = labels[tuple(self.player)]
        positions = zip(*(labels == label).nonzero())
        return list(positions)

    def get_normalized_player_position(self):
        # find top-left position reachable by the player
        position = min(self.get_player_reachable_positions())
        return Position(*position)

    def get_push_actions(self):
        reachable = list(self.get_player_reachable_positions())
        for box_position in self.board.boxes:
            box_position = Position(*box_position)
            for direction in directions.values():
                if not self.board.in_bounds(box_position + direction) \
                   or self.board[box_position + direction] == SPACE:
                    if self.board.in_bounds(box_position - direction) \
                       and box_position - direction in reachable:
                        yield BoxPushAction(box_position, direction)

    def to_str(self, encoding = microban_encoding):
        s = ""
        for r, row in enumerate(self.board):
            for c, obj in enumerate(row):
                if self.player == (r, c):
                    obj = PLAYER
                    
                if (r, c) in self.goals:
                    obj |= GOAL
                s += encoding[obj]
            s += "\n"
        return s

    def __str__(self):
        return self.to_str()

    def __lt__(self, sokoban):
        return False

    def __eq__(self, sokoban):
        return type(sokoban) is Sokoban and \
               self.board == sokoban.board and \
               self.player == sokoban.player and \
               len(self.goals) == len(sokoban.goals) and \
               all([g1 == g2 for g1, g2 in zip(self.goals, sokoban.goals)])

    def __hash__(self):
        return hash(self.board) + hash(self.player) + sum(map(hash, self.goals))
