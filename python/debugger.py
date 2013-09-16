#! /usr/bin/env python

import sys, subprocess
from collections import defaultdict
from itertools import *

"""
given a bad CNF
chop into comment:clause sets
disable permutes of clauses
"""

path  = sys.argv[-1]
path2 = '/tmp/debugger.tmp.cnf'

def valid(cnf_path):
    pipe = subprocess.PIPE
    status = subprocess.call(['minisat', cnf_path], stdout=pipe, stderr=pipe)
    if status == 10:
        return True
    if status == 20:
        return False
    raise "unknown minisat return"

clauses = defaultdict(list)
comment = None
for line in open(path):
    if line.startswith('c'):
        comment = line
        continue
    clauses[comment].append(line)

#print(clauses)

if len(sys.argv) == 3:
    limit = int(sys.argv[1])
else:
    limit = 1

for i in range(1, limit+1):
    for skip in combinations(clauses, i):
        fh = open(path2, 'w')
        for comment in clauses:
            if comment in skip:
                continue
            fh.write(comment)
            fh.writelines(clauses[comment])
        fh.close()
        if valid(path2):
            print(''.join(skip))
    print('\n')






