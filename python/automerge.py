#! /usr/bin/env python

import os, sys

# GPLv3

# lut file is tab separated key:value list
# (value could be inferred from order, but why chance it)
# could be more paranoid, assumes input luts are well formed

if len(sys.argv) < 4:
    print('automerge.py output in1 in2 ...')
    sys.exit(2)

out_cnf = sys.argv[1] + '.cnf'
out_lut = sys.argv[1] + '.lut'

if os.path.isfile(out_cnf):
    print('%s already exists' % out_cnf)
    sys.exit(1)

if os.path.isfile(out_lut):
    print('%s already exists' % out_lut)
    sys.exit(1)

def load_lut(path):
    lut = {}
    for line in open(path):
        k,v = line.strip().split('\t')
        lut[k] = v
    return lut

def sorted_keys(lut):
    return [vk[1] for vk in sorted((v,k) for k,v in in_lut.items())]

new_cnf = open(out_cnf, 'w')
tmp_lut = {}

for in_name in sys.argv[2:]:
    # load lut
    in_lut = load_lut(in_name + '.lut')
    translate = {}
    for k in sorted_keys(in_lut):
        if k not in new_lut:
            tmp_lut[k] = len(tmp_lut) + 1
        translate[in_lut[k]] = tmp_lut[k]
    # update cnf
    new_cnf.write('c automerge %s\n' % in_name)
    for line in open(in_name + '.cnf'):
        if line.startswith('c'):
            new_cnf.write(line)
            continue
        clause = map(int, line.strip().split())
        new_clause = []
        for term in clause:
            sign = term / abs(term)
            new_clause.append(sign * translate[abs(term)])
        new_cnf.write(' '.join(map(str, new_clause)) + ' 0\n')
new_cnf.close()

new_lut = open(out_lut, 'w')
for k in sorted_keys(tmp_lut):
    new_lut.write('%i\t%i\n' % (k, tmp_lut[k]))
new_lut.close()


