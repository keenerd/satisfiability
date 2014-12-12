#! /usr/bin/env python

# Load a cnf file and try to reduce the clauses
# Use for creating formal algos from brute force specs
# Plenty of room for improvement, many obtuse papers on this topic

# Do not run this on input you'll be feeding to Minisat
# It already does the same thing 1000x faster

# GPLv3

"""
todo: pure terms
    if only x or -x appears
    then remove all x/-x from clauses
    add single x/-x clause
    align the 0 column
"""


import sys
from itertools import *

def load_cnf(path):
    cnf = set()
    for line in open(path):
        line = line.strip()
        if line.startswith('c'):
            continue
        if not line:
            continue
        # int-ify, remove dups and re-sort
        line = set(int(i) for i in line.split() if i!='0')
        line2 = []
        for i in count(1):
            if i in line:
                line2.append(i)
            if -i in line:
                line2.append(-i)
            line.discard(i)
            line.discard(-i)
            if not line:
                break
        # tuples for hashiness
        cnf.add(tuple(line2))
    return cnf

def show(cnf):
    "columnized output for easier eyeballing"
    cnf2 = []
    for clause in cnf:
        s = set(clause)
        line = ''
        for i in count(1):
            if not s:
                break
            assert not(i in s and -i in s)
            if i in s:
                line += '  ' + str(i)
            elif -i in s:
                line += ' ' + str(-i)
            else:
                line += '  ' + ' ' * len(str(i))
            s.discard(i)
            s.discard(-i)
        cnf2.append(line[1:] + ' 0')
    cnf2.sort()
    print('\n'.join(cnf2))

def size(cnf):
    return sum(map(len, cnf))

def plusminus(cnf):
    # finds (1 -1)
    for c in cnf:
        c_len = len(c)
        c_set = set(map(abs, c))
        if c_len != len(c_set):
            return c
    return None

def one_difference(cnf):
    # finds (1 2) (1 -2)
    for c1 in cnf:
        for i in range(len(c1)):
            c2 = list(c1)
            c2[i] *= -1
            c2 = tuple(c2)
            if c2 in cnf:
                return c1, c2
    return None, None

def cancel_difference(c1, c2):
    assert len(c1) == len(c2)
    c3 = []
    for t1,t2 in zip(c1, c2):
        if t1 == t2:
            c3.append(t1)
    c3 = tuple(c3)
    assert len(c3) + 1 == len(c1)
    return c3

def subset(cnf):
    # finds (1 2 3) (1 2)
    # very slow!
    cnf2 = list(cnf)
    for i in range(len(cnf2)):
        c1 = cnf2[i]
        s1 = set(c1)
        for j in range(i+1, len(cnf2)):
            c2 = cnf2[j]
            s2 = set(c2)
            if s1.issuperset(s2):
                return c1, c2
            if s2.issuperset(s1):
                return c2, c1
    return None, None

def shorter(c1, c2):
    assert len(c1) != len(c2)
    if len(c1) < len(c2):
        return c1
    return c2

def none_filter(fn, c1, c2):
    if c1 is None:
        return None
    if c2 is None:
        return None
    return fn(c1, c2)

def main():
    path = sys.argv[1]
    cnf = load_cnf(path)
    print('c before %i %i' % (len(cnf), size(cnf)))
    while True:
        c3 = None
        # try to order these from fast to slow
        if c3 is None:
            c3 = plusminus(cnf)
        if c3 is None:
            c1,c2 = one_difference(cnf)
            c3 = none_filter(cancel_difference, c1, c2)
        if c3 is None:
            c1,c2 = subset(cnf)
            c3 = none_filter(shorter, c1, c2)
        if c3 is None:
            break
        cnf.discard(c1)
        cnf.discard(c2)
        cnf.add(c3)
    print('c after  %i %i' % (len(cnf), size(cnf)))
    show(cnf)

if __name__ == '__main__':
    main()




