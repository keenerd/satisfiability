#! /usr/bin/env python

from sat import *

"""
many many flood fills!
a limited flood for each number
one big flood for stream
optimization: exact floods don't cover the whole board
"""

puzzle = """\
2........2
......2...
.2..7.....
..........
......3.3.
..2....3..
2..4......
..........
.1....2.4."""

def clean(puz):
    puz = [list(line) for line in puz.split('\n')]
    table = {}
    for y,line in enumerate(puz):
        for x,n in enumerate(line):
            if n == '.':
                continue
            table[(x,y)] = int(n)
    return table

table = clean(puzzle)
y_dim = len(puzzle.split('\n'))
x_dim = len(puzzle.split('\n')[0].strip())
z_dim = int(x_dim * y_dim / 2)
xs = range(x_dim)
ys = range(y_dim)

cnf = CNF('/tmp/nurikabe.cnf')

f = cnf.auto_term

# hit all the base numbers early for clean ordering
base_layer = [f('base', x, y) for x,y in product(xs, ys)]

cnf.comment('numbers are clear')
for x,y in table:
    cnf.write_one(-f('base', x, y))

cnf.comment('no pools')
for x,y in product(xs[:-1], ys[:-1]):
    cells = [f('base',x,y), f('base',x+1,y), f('base',x,y+1), f('base',x+1,y+1)]
    cnf.write([neg(cells)])

adj = cartesian_table(xs, ys)

cnf.comment('walls')
wall_labels = []
wall_summaries = set()
for x,y in table:
    label = 'wall %i %i' % (x,y)
    wall_labels.append(label)
    size = table[(x,y)]
    cnf.comment(label)
    mapping = floodfill(cnf, label, adj, size, exact=True, seed=(x,y))
    wall_summaries.update(mapping.values())
    cnf.comment('link ' + label)
    for x2,y2 in mapping:
        cnf.write(if_then(f(*mapping[(x2,y2)]), -f('base', x2, y2)))

cnf.comment("walls can't touch")
# little tricky to explain
# forbid summary + !summary neighbor + !base neighbor
for x,y in table:
    label = 'wall %i %i' % (x,y)
    cnf.comment('dont touch ' + label)
    for x2,y2 in product(xs,ys):
        for x3,y3 in neighbors(x2,y2,xs,ys):
            cell1 = f(label, 'summary', (x2,y2))
            cell2 = f(label, 'summary', (x3,y3))
            cell3 = f('base', x3, y3)
            cnf.write_one(-cell1, cell2, cell3)

cnf.comment("stream")
# use a seed for faster fill
seed = None
for x,y in table:
    if table[(x,y)] == 1:
        seed = neighbors(x,y,xs,ys)[0]
        break
mapping = floodfill(cnf, 'stream', adj, z_dim, seed=seed)

cnf.comment("stream summary")
for x,y in mapping:
    cnf.write(if_then(f(*mapping[(x,y)]), f('base', x, y)))

cnf.comment('no overlap between regions')
for x,y in product(xs,ys):
    cells = [f(label, 'summary', (x,y)) for label in wall_labels + ['stream']]
    cnf.write(window(cells, 1, 1))

print('terms:', cnf.maxterm)
print('clauses:', cnf.clauses)
print()
cnf.verify()

# pretty print
for solution in cnf.solutions(interesting = base_layer):
    for y in ys:
        line = ''
        for x in xs:
            if (x,y) in table:
                line += str(table[(x,y)])
                line += ' '
            elif f('base', x, y) in solution:
                line += 'X '
            else:
                line += '. '
        print(line)
    print('\n')

