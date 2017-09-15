import os
import copy
import time
import curses

from random import *

from constants import *
from file import *
from generator import *
from sokoban import *
from solver import *

# classes

def render_legend(window):
    window.addstr((HEIGHT // 2) - 2, WIDTH - 16, "# [wall]")
    window.addstr((HEIGHT // 2) - 1, WIDTH - 16, "@ [player]")
    window.addstr((HEIGHT // 2) - 0, WIDTH - 16, "$ [box]")
    window.addstr((HEIGHT // 2) + 1, WIDTH - 16, ". [goal]")
    window.addstr((HEIGHT // 2) + 2, WIDTH - 16, "* [box on goal]")
    window.refresh()

def render_board(window, sokoban, encoding = microban_encoding):
    window.clear()
    r_off = (HEIGHT - sokoban.board.rows) // 2
    c_off = (WIDTH - sokoban.board.cols) // 2
    for r, row in enumerate(sokoban.to_str(encoding).split("\n")):
        for c, char in enumerate(row):
            window.addch(r_off + r, c_off + c, char)
            
    window.refresh()

def play_game(stdscr):
    puzzle_directory = "puzzles/i2a_generated"
    def load(puzzle_n):
        return parse_puzzle(puzzle_directory + "/gen_" +
                            str(puzzle_n) + ".txt")
    puzzle_n = 1
    total_puzzles = len(os.listdir(puzzle_directory))
    sokoban = load(puzzle_n)

    gen = I2AGenerator(total_positions = 10 ** 4)

    window = stdscr.derwin(HEIGHT, WIDTH, 0, 0)
    window.clear()

    char = None
    while True:
        solved_flag = None
        if sokoban.solved():
            solved_flag = puzzle_n
            puzzle_n = min(puzzle_n + 1, total_puzzles)
            sokoban = load(puzzle_n)
        render_board(window, sokoban)
        render_legend(window)
        window.addstr(0, 0, "Puzzle #" + str(puzzle_n))
        window.refresh()
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
            puzzle_n = ((puzzle_n - 2) % total_puzzles) + 1
            sokoban = load(puzzle_n)
        elif char == ord('e'):
            puzzle_n = (puzzle_n % total_puzzles) + 1
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
