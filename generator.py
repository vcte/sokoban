from abc import ABC, abstractmethod
import time
import numpy as np

from random import *

from constants import *
from sokoban import *
from util import *

# classes

class Generator(ABC):
    @abstractmethod
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

    def generate(self, width = 10, height = 10, boxes = 4, state = None):
        if state is not None:
            seed(state)
        
        # TODO: fix bug where >4 boxes generated, and box on top of goal
        for _ in range(self.max_room_tries):
            board = Board.from_array(np.full((height, width), WALL))

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
                    break
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

                # collect statistics about box movement, mapping from
                # puzzle state to (id of last box moved, box_positions, # swaps)
                box_positions = list(board.boxes)
                goal_positions = box_positions.copy()
                statistics = { (board, player) : (None, box_positions, 0) }
                
                while len(visited) < self.total_positions and len(frontier) > 0:
                    board, player, depth = frontier.pop()

                    if depth >= self.max_action_depth:
                        continue
                    
                    last_box_moved, box_positions, box_swaps = \
                        statistics[(board, player)]
                    shuffle(moves)
                    
                    for direction, do_pull in moves:
                        if board[player + direction] == SPACE:
                            board_ = board.copy()
                            player_ = player.copy()
                            depth_ = depth + 1
                            last_box_moved_ = last_box_moved
                            box_pos_ = box_positions.copy()
                            box_swaps_ = box_swaps
                        
                            # pull box towards player, if do_pull is true
                            if do_pull and board[player - direction] == BOX:
                                board_[player - direction] = SPACE
                                board_[player] = BOX

                                # keep track of identity of box when moved
                                box_id = box_positions.index(player - direction)
                                box_pos_[box_id] = tuple(player)
                                if last_box_moved != None and \
                                   last_box_moved != box_id:
                                    box_swaps_ += 1
                                last_box_moved_ = box_id
                            player_ += direction

                            if (board_, player_) not in visited:
                                frontier.append((board_, player_, depth_))
                                visited.add((board_, player_))

                                statistics[(board_, player_)] = \
                                    (last_box_moved_, box_pos_, box_swaps_)
                            
                def score(board, player, _, box_positions, box_swaps):
                    # score is 0 whenever box or player is on top of goal
                    if any([player == goal for goal in goals]):
                        return 0
                    elif any([box == goal for box, goal in
                              zip(box_positions, goal_positions)]):
                        return 0

                    box_displacements = [manhattan_dist(box, goal)
                                         for box, goal in
                                         zip(box_positions, goal_positions)]
                    return box_swaps * sum(box_displacements)

                # calculate scores, find room that maximizes score
                board, player = \
                    max(statistics, key = lambda k: score(*k, *statistics[k]))
                best_score = score(board, player, *statistics[(board, player)])

                if best_score <= 0:
                    continue

                return Sokoban(board, player, goals)

