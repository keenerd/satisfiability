#! /usr/bin/env python

from sat import *

# Make a game of life board that grows into a subset of braille.
# The GoL and braille rule generators are intentionally suboptimal, 
# to demonstrate how to do complicated things without thinking hard.

z_size = 2
x_size = 6
y_size = 9

assert x_size % 2 == 0
assert y_size % 3 == 0
assert z_size >= 2

# top-down, left-right
braille = {'a': (1,0,0, 0,0,0),
           'c': (1,0,0, 1,0,0),
           'g': (1,1,0, 1,1,0),
           't': (0,1,1, 1,1,0),
}

def conway(now, future, ns):
    "takes 10 bits of cells, return true if legit arrangement"
    n_count = sum(ns)
    if n_count == 3:
        return future
    if n_count == 2:
        return now == future
    return not future

f = lambda x,y,z: x + y*(x_size+2) + z*(x_size+2)*(y_size+2) + 1

cells = [f(x,y,n) for x,y,n in product(range(x_size+2), range(y_size+2), range(z_size))]
assert sanity(cells)

cnf = CNF()

cnf.comment("dead edges")
for x,y,z in panel((0,x_size+1), 0, range(z_size)):
    cnf.write_one(-f(x,y,z))
for x,y,z in panel(x_size+1, (0,y_size+1), range(z_size)):
    cnf.write_one(-f(x,y,z))
for x,y,z in panel((0,x_size+1), y_size+1, range(z_size)):
    cnf.write_one(-f(x,y,z))
for x,y,z in panel(0, (0,y_size+1), range(z_size)):
    cnf.write_one(-f(x,y,z))

cnf.comment("GoL rules")
for x,y,z in panel((1,x_size), (1,y_size), (0, z_size-2)):
    ns = neighbors(x, y, None, None, diagonals = True)
    cells = [f(x,y,z), f(x,y,z+1)] + [f(x2,y2,z) for x2,y2 in ns]
    for mult in product([-1, 1], repeat = 10):
        tfs = [m>0 for m in mult]
        if conway(tfs[0], tfs[1], tfs[2:]):
            continue
        cells2 = [c*m for c,m in zip(cells, mult)]
        cnf.write([neg(cells2)])

cnf.comment("braille")
b_offset = [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2)]
for pattern in product([0,1], repeat=6):
    pattern = tuple(pattern)
    if pattern in braille.values():
        continue
    for xo,yo in product(range(1,x_size,2), range(1,y_size,3)):
        points = [(xb+xo, yb+yo) for xb,yb in b_offset]
        cells = [f(x,y,z_size-1) for x,y in points]
        cells = [(c, -c)[p] for c,p in zip(cells,pattern)]
        cnf.write([cells])

print('terms:', cnf.maxterm)
print('clauses:', cnf.clauses)
cnf.verify()

# pretty print
for solution in cnf.solutions(10):
    line = ''
    #for z,y,x in product([0], range(1,y_size+1), range(1,x_size+1)):
    for z,y,x in product(range(z_size), range(1,y_size+1), range(1,x_size+1)):
        if f(x, y, z) in solution:
            line += 'X '
        else:
            line += '- '
        if x == x_size:
            print(line)
            line = ''
            if y == y_size:
                print('\n')
    print('\n\n')

