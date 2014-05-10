#! /usr/bin/env python

import sys, subprocess
from collections import defaultdict
from itertools import *

"""
GPLv3
given a bad CNF
chop into comment:clause sets
disable permutes of clauses
add solution counts?
"""

if len(sys.argv) == 1 or len(sys.argv) > 3:
    print("debugger.py - find what blocks a good SAT")
    print("use: debugger.py [errors] filename.cnf")
    print("    [errors] is optional, default is 1")
    print("    'all' is legal but takes some time")
    print("    requires a well commented CNF file")
    sys.exit()

path  = sys.argv[-1]
path2 = '/tmp/debugger.tmp.cnf'
if len(sys.argv) == 3 and sys.argv[1] == 'all':
    limit = 'all'
elif len(sys.argv) == 3:
    limit = int(sys.argv[1])
else:
    limit = 1

def valid(cnf_path):
    pipe = subprocess.PIPE
    status = subprocess.call(['minisat', cnf_path], stdout=pipe, stderr=pipe)
    if status == 10:
        return True
    if status == 20:
        return False
    raise Exception("unknown minisat return")

def all_combinations(thing):
    for i in range(1, len(thing)+1):
        for cs in combinations(thing, i):
            yield set(cs)

def trivial_superset(test_set, many_sets):
    "many_sets must be a list of sets"
    # shame you can't have a set of sets
    # 'all' filters pure supersets, but 'any' catches trivial ones
    return any(subset in many_sets for subset in all_combinations(test_set))

if valid(path):
    print('No bugs in CNF.')
    sys.exit(0)

clauses = defaultdict(list)
ordered_comments = []
comment = 'beginning of file'
ordered_comments.append([comment])
for line in open(path):
    if line.startswith('c'):
        comment = line[1:].strip()
        ordered_comments.append([comment])
        continue
    clauses[comment].append(line)
if limit == 'all':
    limit = len(clauses)

error_sets = []
print('rules:', sum(bool(len(v)) for v in clauses.values()),'\n')
for i in range(1, limit+1):
    if limit > 1:
        print('combination size', i, '\n')
    if i == 1:
        # easier to read when order matches the source
        trials = ordered_comments
    else:
        trials = combinations(clauses, i)
    for skip in trials:
        skip = set(skip)
        if trivial_superset(skip, error_sets):
            continue
        fh = open(path2, 'w')
        for comment in clauses:
            if comment in skip:
                continue
            fh.write('c ' + comment + '\n')
            fh.writelines(clauses[comment])
        fh.close()
        if not valid(path2):
            continue
        print('\n'.join(skip), '\n')
        error_sets.append(skip)
    print('\n')

