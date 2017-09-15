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
