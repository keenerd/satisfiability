#! /usr/bin/env python

# works in python 2 or 3
# GPLv3

from sat import *

# todo
# multiplication

def addition(A, B, C):
    "A + B = C, big endian input"
    # little endian makes math easier though
    A = list(reversed(A))
    B = list(reversed(B))
    C = list(reversed(C))
    for clause in window((A[0], B[0], C[0]), 2, 2):
        yield clause
    # fix this to work with different length ints
    # 24 clauses per bit, could be better?
    for i in range(1, min(map(len, (A, B, C)))):
        j = i - 1
        for clause in maybe((A[i], B[i] ,C[i]), 2):
            #yield (-A[j], -B[j], -C[j]) + clause
            #yield (-A[j], -B[j], C[j]) + clause
            yield (-A[j], -B[j]) + clause
            yield (-A[j], B[j], C[j]) + clause
            yield (A[j], -B[j], C[j]) + clause
        for clause in one_or_three((A[i], B[i] ,C[i])):
            yield (-A[j], B[j], -C[j]) + clause
            yield (A[j], -B[j], -C[j]) + clause
            #yield (A[j], B[j], C[j]) + clause
            #yield (A[j], B[j], -C[j]) + clause
            yield (A[j], B[j]) + clause

def one_set_true(*star_cells):
    "combinatorial explosion!  use summary vars instead"
    # sets can be different lengths
    # multiple sets can be true
    # dunno why this works
    # wrote it by listing all bad sequences and eliminating vars
    chop = lambda cells, n: [-c for c in cells[:n]] + [cells[n]]
    for xs in product(*[range(len(sc)) for sc in star_cells]):
        yield tuple(chain.from_iterable(starmap(chop, zip(star_cells, xs))))



