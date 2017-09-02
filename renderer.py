import copy
import curses
import numpy as np

from random import *

# constants

WIDTH = 80
HEIGHT = 24

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

directions = {
    UP      : (-1, 0),
    RIGHT   : (0, 1),
    DOWN    : (1, 0),
    LEFT    : (0, -1),
}

SPACE   = 0b0000
WALL    = 0b0001
PLAYER  = 0b0010
BOX     = 0b0100
GOAL    = 0b1000

microban_encoding = {
    SPACE           : ' ',
    WALL            : '#',
    PLAYER          : '@',
    BOX             : '$',
    GOAL            : '.',
    PLAYER + GOAL   : '&',
    BOX + GOAL      : '*',
}

# class

class Action:
    def act(self, game):
        pass

class KeyboardAction(Action):
    def __init__(self, key = None):
        self.key = key

    def act(self, game):
        direction = directions[self.key]

        # do nothing if player will move out of bounds
        bounds = (0, game.board.rows, 0, game.board.cols)
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
            if game.board[game.player + direction + direction] == SPACE:
                game.board[game.player + direction] ^= BOX
                game.board[game.player + direction + direction] ^= BOX
            else:
                return

class Position:
    def __init__(self, row, col):
        self.row = row
        self.col = col

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

class Board:
    def __init__(self, array):
        # 2d array of walls + boxes, and optionally player + goals
        self.array = np.array(array)

    @property
    def rows(self):
        return self.array.shape[0]

    @property
    def cols(self):
        return self.array.shape[1]

    @property
    def positions(self):
        for r in range(self.rows):
            for c in range(self.cols):
                yield (r, c)

    @property
    def spaces(self):
        for r, c in self.positions:
            if self[r, c] == SPACE:
                yield (r, c)

    @property
    def boxes(self):
        for r, c in self.positions:
            if self[r, c] == BOX:
                yield (r, c)

    def copy(self):
        return Board(copy.deepcopy(self.array))

    def __getitem__(self, pos):
        """pos = either Position or (row, col) tuple"""
        return self.array[pos[0]][pos[1]]

    def __setitem__(self, pos, value):
        self.array[pos[0]][pos[1]] = value

    def __eq__(self, board):
        return self.array.shape == board.array.shape and \
               (self.array == board.array).all()

    def __lt__(self, board):
        return self.array.shape == board.array.shape and \
               (self.array < board.array).all()

    def __hash__(self):
        return hash(self.array.tostring())

class Sokoban:
    def __init__(self, board = [], player = None, goals = []):
        # board is row x col array of numerical constants
        self.board = board

        # player is position with row, col information
        self.player = player

        # goals are list of positions
        self.goals = goals

    def solved(self):
        return all([self.board[goal] & BOX for goal in self.goals])

class Generator:
    def generate(self):
        pass

class I2AGenerator(Generator):

    patterns = [[(0, 0), (0, -1), (0, 1)],
                [(0, 0), (-1, 0), (1, 0)],
                [(0, 0), (0, -1), (1, 0)],
                [(0, 0), (0, -1), (1, -1), (1, 0)],
                [(0, 0), (1, 0), (0, 1)]]
    
    def __init__(self, max_room_tries = 10, max_position_tries = 10,
                 max_action_depth = 300, total_positions = 10 ** 6,
                 new_direction_prob = 0.35, walk_steps = 1.5):
        self.max_room_tries     = max_room_tries
        self.max_position_tries = max_position_tries
        self.max_action_depth   = max_action_depth
        self.total_positions    = total_positions
        self.new_direction_prob = new_direction_prob
        self.walk_steps         = walk_steps

    def generate(self, width = 10, height = 10, boxes = 4):
        def manhattan_dist(x, y):
            return sum([abs(a - b) for a, b in zip(x, y)])
        
        for _ in range(self.max_room_tries):
            board = Board(np.full((height, width), WALL))

            # random walk from random start position + direction
            bounds = (1, height - 2, 1, width - 2)
            position = Position(randint(1, height - 2), randint(1, width - 2))
            direction = choice(directions)
            walk_steps = int(self.walk_steps * width * height) \
                         if self.walk_steps <= 3 else self.walk_steps
            for _ in range(walk_steps):
                # carve out randomly selected pattern around position
                pattern = choice(self.patterns)
                for d in pattern:
                    if (position + d).in_bounds(*bounds):
                        board[position] = SPACE

                # move one step in direction, if won't reach edge of board
                if (position + direction).in_bounds(*bounds):
                    position += direction

                # with some probability, change direction
                if random() < self.new_direction_prob:
                    direction = choice(directions)

            # randomly choose initial player position and goal positions
            for _ in range(self.max_position_tries):
                spaces = list(board.spaces)
                if len(spaces) < 1 + boxes:
                    continue
                shuffle(spaces)
                player = Position(*spaces[0])
                goals = [Position(r, c) for (r, c) in spaces[1 : 1 + boxes]]
                for goal in goals:
                    board[goal] = BOX

                # use dfs to play puzzle in reverse
                # TODO: optimize (cur: 15s for 10 ^ 6 pos, no clear bottlenecks)
                moves = [(d, b) for d in directions.values()
                         for b in (True, False)]
                frontier = [(board, player, 0)]
                visited = set(); visited.add((board, player))

                # collect statistics about box movement
                box_positions = list(board.boxes)
                goal_positions = box_positions.copy()
                statistics = { (board, player) : (None, box_positions, 0) }
                
                while len(visited) < self.total_positions and len(frontier) > 0:
                    board, player, depth = frontier.pop()
                    last_box_moved, box_positions, box_swaps = \
                        statistics[(board, player)]

                    if depth < self.max_action_depth:
                        shuffle(moves)
                        for direction, do_pull in moves:
                            board_ = board.copy()
                            player_ = player.copy()
                            depth_ = depth + 1
                            last_box_moved_ = last_box_moved
                            box_pos_ = box_positions.copy()
                            box_swaps_ = box_swaps

                            if board[player + direction] == SPACE:
                                # pull box towards player, if do_pull is true
                                if do_pull and board[player - direction] == BOX:
                                    board_[player - direction] ^= BOX
                                    board_[player] = BOX
                                player_ += direction

                                if (board_, player_) not in visited:
                                    frontier.append((board_, player_, depth_))
                                    visited.add((board_, player_))

                            # keep track of identity of boxes as they are moved
                            if (board_, player_) not in statistics:
                                matches = [box in board_.boxes
                                           for box in box_positions]
                                if not all(matches):
                                    moved_box = [box for box in board_.boxes
                                                 if box not in box_positions][0]
                                    box_id = matches.index(False)
                                    box_pos_[box_id] = moved_box
                                    if last_box_moved != None and \
                                       last_box_moved != box_id:
                                        box_swaps_ += 1
                                    last_box_moved_ = box_id
                                statistics[(board_, player_)] = \
                                    (last_box_moved_, box_pos_, box_swaps_)

                def score(board, player, _, box_positions, box_swaps):
                    # score is 0 whenever box or player is on top of goal
                    if any([player == goal or goal == box
                            for goal in goals for box in board.boxes]):
                        return 0
                    
                    box_displacements = [manhattan_dist(box, goal)
                                         for box, goal in
                                         zip(box_positions, goal_positions)]
                    return box_swaps * sum(box_displacements)

                # calculate scores, find room that maximizes score
                best_score, (board, player) = \
                    max([(score(*k, *statistics[k]), k) for k in statistics])

                if best_score <= 0:
                    continue
                return Sokoban(board, player, goals)
    
def parse_puzzle(file_path, game_encoding = microban_encoding):
    array = []
    game_decoding = {game_encoding[k] : k for k in game_encoding}
    with open(file_path, mode = "r", encoding = "utf-8") as f:
        for line in f.readlines():
            array.append([game_decoding.get(c, SPACE) for c in line])

    # zero-pad the right side of each row to have equal width
    max_length = max([len(row) for row in array])
    array = [row + [SPACE] * (max_length - len(row)) for row in array]
    board = Board(array)

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

def render_board(window, sokoban, encoding = microban_encoding):
    window.clear()
    r_off = (HEIGHT - sokoban.board.rows) // 2
    c_off = (WIDTH - sokoban.board.cols) // 2
    for r, c in sokoban.board.positions:
        if sokoban.player == (r, c):
            obj = PLAYER
        else:
            obj = sokoban.board[r, c]
            
        if (r, c) in sokoban.goals:
            obj |= GOAL
        window.addch(r_off + r, c_off + c, encoding[obj])
    window.refresh()

def play_game(stdscr):
    def load(puzzle_n):
        return parse_puzzle("puzzles/microban/microban_" +
                            str(puzzle_n) + ".txt")
    puzzle_n = 1
    sokoban = load(puzzle_n)

    gen = I2AGenerator(total_positions = 10 ** 4)

    window = stdscr.derwin(HEIGHT, WIDTH, 0, 0)
    window.clear()

    char = None
    while True:
        solved_flag = None
        if sokoban.solved():
            solved_flag = puzzle_n
            puzzle_n = min(puzzle_n + 1, 155)
            sokoban = load(puzzle_n)
        render_board(window, sokoban)
        if solved_flag:
            window.addstr(0, 0, "Solved puzzle #" + str(solved_flag) + "!")
            window.refresh()
        char = stdscr.getch()

        action = None
        if char == curses.KEY_UP:
            action = KeyboardAction(UP)
        elif char == curses.KEY_RIGHT:
            action = KeyboardAction(RIGHT)
        elif char == curses.KEY_DOWN:
            action = KeyboardAction(DOWN)
        elif char == curses.KEY_LEFT:
            action = KeyboardAction(LEFT)
        elif char == ord('r'):
            sokoban = load(puzzle_n)
        elif char == ord('w'):
            puzzle_n = max(puzzle_n - 1, 1)
            sokoban = load(puzzle_n)
        elif char == ord('e'):
            puzzle_n = min(puzzle_n + 1, 155)
            sokoban = load(puzzle_n)
        elif char == ord('g'):
            window.addstr(0, 0, "Generating new puzzle...")
            window.refresh()
            sokoban = gen.generate()
        elif char == ord('q'):
            break
        else:
            continue

        if action:
            action.act(sokoban)

if __name__ == "__main__":
    curses.wrapper(play_game)
