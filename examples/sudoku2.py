#! /usr/bin/env python

puzzle = """\
.........
.....3.85
..1.2....
...5.7...
..4...1..
.9.......
5......73
..2.1....
....4...9"""

from sat import *
cnf = CNF('/tmp/sudoku.cnf')
# all values 0-8
f = lambda x,y,i: 81*y + 9*x + i + 1

def block(z):
    "takes 0-8, returns xy pairs"
    xs = (z * 3) % 9
    ys = (z // 3) * 3
    return product(range(xs, xs+3), range(ys, ys+3))

cnf.comment('one per number')
for x,y in product(range(9), range(9)):
    cells = [f(x,y,i) for i in range(9)]
    cnf.write(window(cells, 1, 1))
cnf.comment('one per column')
for x,i in product(range(9), range(9)):
    cells = [f(x,y,i) for y in range(9)]
    cnf.write(window(cells, 1, 1))
cnf.comment('one per row')
for y,i in product(range(9), range(9)):
    cells = [f(x,y,i) for x in range(9)]
    cnf.write(window(cells, 1, 1))
cnf.comment('one per block')
for z,i in product(range(9), range(9)):
    cells = [f(x,y,i) for x,y in block(z)]
    cnf.write(window(cells, 1, 1))

cnf.comment('clues')
puzzle = puzzle.replace('\n', '')
for yx,c in zip(product(range(9), range(9)), puzzle):
    if c != '.':
        cnf.write_one(f(yx[1], yx[0], int(c)-1))

for solution in cnf.solutions(3):
    for y in range(9):
        line = [i+1 for x,i in product(range(9), range(9)) if f(x,y,i) in solution]
        print(' '.join(map(str, line)))
    print('\n\n')

