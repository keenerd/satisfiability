#! /usr/bin/env python

# works in python 2 or 3

import os, shutil, tempfile, subprocess
from itertools import *

# todo
# more puzzle specific classes
# automatic term allocation (builds a lookup function for you)
# auto_term saving and loading

class CNF(object):
    def __init__(self, path=None, stdout=False, preloads=None):
        self.path = path
        if path is None:
            fh = tempfile.NamedTemporaryFile(delete=False)
            self.path = fh.name
            self.del_flag = True
        else:
            fh = open(path, 'w+b')
            self.del_flag = False
        # closed file needed for py2 and windows compatibility
        fh.close()
        # adjust to whatever path you need
        self.minisat = 'minisat'
        self.clauses = 0
        self.limit = 100000
        self.maxterm = 0
        self.terms = set()
        self.stdout = stdout
        self.quiet = True
        self.term_lut = {}
        if preloads is None:
            preloads = []
        for preload in preloads:
            self.comment('preloading %s' % preload)
            fh = open(self.path, 'ab')
            shutil.copyfileobj(open(preload, 'rb'), fh)
            fh.close()
    def write(self, cnf):
        "consumes an iterator of tuple clauses"
        fh = open(self.path, 'a')
        for i,line in enumerate(cnf):
            line = list(line)
            if min(map(abs, line)) == 0:
                raise Exception("Illegal term, 0")
            self.maxterm = max(self.maxterm, max(line), abs(min(line)))
            if i > self.limit:
                raise Exception("Overclause!")
            output = ' '.join(map(str, list(line) + [0]))
            #fh.write((output + '\n').encode('utf-8'))
            fh.write(output + '\n')
            if self.stdout:
                print(output)
            self.clauses += 1
            self.terms.update(map(abs, line))
        fh.close()
    def read(self, path):
        "for external CNFs, no error checking"
        for line in open(path):
            if line[0] in ('c', 'p'):
                continue
            line = tuple(map(int, line.split()))[:-1]
            self.write([line])
    def write_one(self, *clause):
        "for single clauses"
        # breaks when passed a list...
        self.write([clause])
    def comment(self, c):
        fh = open(self.path, 'a')
        fh.write('c ' + c + '\n')
        if self.stdout or not self.quiet:
            print('c ' + c)
        fh.close()
    def _run_minisat(self, cnf_path, solve_path):
        pipe = subprocess.PIPE
        status = subprocess.call([self.minisat, cnf_path, solve_path], stdout=pipe, stderr=pipe)
        if status == 10:
            return True
        if status == 20:
            return False
        raise Exception("Unknown minisat return %i" % status)
    def setup_temps(self):
        "returns temp paths, manually delete when done"
        temp2 = tempfile.NamedTemporaryFile(delete=False)
        copy_path = temp2.name
        temp2.close()
        shutil.copy(self.path, copy_path)
        temp3 = tempfile.NamedTemporaryFile(delete=False)
        solve_path = temp3.name
        temp3.close()
        return copy_path, solve_path
    def verify(self, allow_partial = False):
        cnf_path,solve_path  = self.setup_temps()
        status = self._run_minisat(cnf_path, solve_path)
        os.remove(cnf_path)
        os.remove(solve_path)
        if not status:
            raise Exception("No possible solutions")
        if allow_partial:
            return True
        if not min(self.terms) == 1:
            raise Exception("CNF does not start at 1")
        if not max(self.terms) == len(self.terms):
            #print(max(self.terms), len(self.terms))
            #print(set(range(1, max(self.terms)+1)) - self.terms)
            raise Exception("CNF has gaps")
        return True
    def _tail(self, path):
        return open(path).readlines()[-1].strip()
    def solutions(self, how_many=1, interesting=None):
        "'interesting' is the subset of cells that matter for the solution"
        if interesting is None:
            interesting = set([])
        interesting = set(interesting)
        cnf_path,solve_path  = self.setup_temps()
        for i in range(how_many):
            if not self._run_minisat(cnf_path, solve_path):
                break
            solution = self._tail(solve_path)
            solution = list(map(int, solution.split(' ')))
            yield set(n for n in solution if n > 0)
            if interesting:
                solution = [n for n in solution if abs(n) in interesting]
            negative = ' '.join(map(str, [-n for n in solution]))
            open(cnf_path, 'a').write(negative + '\n')
        os.remove(cnf_path)
        os.remove(solve_path)
    def clear(self):
        "wipe the temp file, for interactive use only"
        fh = open(self.path, 'w+b')
        fh.close()
        self.clauses = 0
    def close(self):
        if self.del_flag:
            os.remove(self.path)
        self.del_flag = False
    def __del__(self):
        self.close()
    def auto_term(self, *args, **kw_args):
        "not portable between users, except for load='' and save='' kw args"
        # how to deal with arg ordering...
        if 'save' in kw_args:
            return
        if 'load' in kw_args:
            return
        if 'ordered' in kw_args and kw_args['ordered']==False:
            args = sorted(args)
        if args not in self.term_lut:
            self.term_lut[args] = self.maxterm + 1
            self.maxterm += 1
        return self.term_lut[args]

def write_cnf(cnf):
    for line in cnf:
        print(' '.join(map(str, list(line) + [0])))

def read_cnf(path, skip_first=False):
    skip = int(skip_first)
    for solution in open(path).readlines()[skip:]:
        solution = solution.strip()
        solution = map(int, solution.split())
        solution = set(n for n in solution if n > 0)
        yield solution

def sanity(cells):
    "takes a list of every possible cell"
    assert min(cells) == 1
    assert max(cells) == len(cells)
    assert len(cells) == len(list(set(cells)))
    return True

def neg(cells):
    return tuple(-c for c in cells)

def window(cells, a, b):
    "between a and b true, inclusive"
    cells = list(cells)
    # lower limit
    for cs in combinations(cells, len(cells)+1-a):
        yield cs
    # upper limit
    for cs in combinations(cells, b+1):
        yield neg(cs)

def xnor(a, b):
    "both false or both true"
    # xor is just window(1,1)
    yield (-a, b)
    yield (a, -b)

def ordered(cells1, cells2):
    "element of c1 must come before element of c2"
    # c2 is optional?
    assert len(cells1) == len(cells2)
    for i in range(len(cells1)):
        for c2 in cells2[:i+1]:
            yield (-cells1[i], -c2)

def maybe(cells, n):
    "generalized xnor, 0 or n true"
    cells = list(cells)
    cells_set = set(cells)
    # upper limit
    for cs in combinations(cells, n+1):
        yield neg(cs)
    if n == 1:
        return
    # lower limit
    for cs in combinations(cells, len(cells)+1-n):
        yield cs + neg(cells_set - set(cs))

def link(*cells):
    "force equivalency, 0 or all"
    cells = list(cells)
    assert len(cells) >= 2
    # could be more strongly cross linked
    for i in range(len(cells) - 1):
        yield (cells[i], -cells[i+1])
        yield (-cells[i], cells[i+1])
    if len(cells) > 2:
        yield (cells[-1], -cells[0])
        yield (-cells[-1], cells[0])

def consecutive(cells1, cells2):
    "element of c1 must come immediately before element of c2"
    # both optional?
    cells1 = list(cells1)
    cells2 = list(cells2)
    assert len(cells1) == len(cells2)
    c2 = list(cells2)[1:]
    for pair in zip(cells1, c2):
        for rule in xnor(*pair):
            yield rule
    yield (-cells1[-1],)
    yield (-cells2[0],)

def adjacent(cells1, cells2):
    assert len(cells1) == len(cells2)
    for c1,c2 in zip(cells1, cells2):
        yield (-c1, -c2)
    yield (-cells1[0], cells2[1])
    for c1, c2a, c2b in zip(cells1[1:], cells2, cells2[2:]):
        yield (-c1, c2a, c2b)
    yield (-cells1[-1], cells2[-2])
    # window(0, 1) would be obvious but wrong when length == 2
    for clause in xnor(cells1[0], cells2[1]):
        yield clause
    for clause in xnor(cells1[-1], cells2[0]):
        yield clause

def not_adjacent(cells1, cells2):
    yield (-cells1[0], -cells2[1])
    for c1, c2a, c2b in zip(cells1[1:], cells2, cells2[2:]):
        yield (-c1, -c2a)
        yield (-c1, -c2b)
    yield (-cells1[-1], -cells2[-2])


def if_then(a, b):
    "relationship is one way, b can not affect a"
    yield (-a, b)

def if_gen(a, b, modeA=None, modeB=None):
    "a and b can be lists, mode=any/all"
    # will probably bug out on iterator input
    if type(a) == int:
        a = [a]
        modeA = 'all'
    if type(b) == int:
        b = [b]
        modeB = 'all'
    if modeA == all:
        modeA = 'all'
    if modeB == all:
        modeB = 'all'
    if modeA == any:
        modeA = 'any'
    if modeB == any:
        modeB = 'any'
    if modeA is None or modeB is None:
        raise "must specify mode"
    if modeA == 'all' and modeB == 'all':
        return (neg(a) + (eb,) for eb in b)
    if modeA == 'all' and modeB == 'any':
        return [ (neg(a) + tuple(b)) ]
    if modeA == 'any' and modeB == 'all':
        return ((-ea, eb) for ea,eb in product(a, b))
    if modeA == 'any' and modeB == 'any':
        return ((-ea,) + tuple(b) for ea in a)

def if_wrap(cell, clauses):
    for clause in clauses:
        yield [-cell] + list(clause)

def one_or_three(cells):
    assert len(cells) == 3  # crude prototype
    for clause in maybe(cells, 2):
        yield neg(clause)

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

class Zebra(CNF):
    "handles everything for a zebra puzzle"
    def load_axes(self, values):
        "takes a dictionary of lists"
        self.everything = values
        self.all_sets = list(values.values())
        self.dims = len(values)
        self.side = len(self.all_sets[0])  # only works with square puzzles...
        self.keys = [v for vals in values.values() for v in vals]
        assert len(self.keys) == len(list(set(self.keys)))
        self._layout_grid()
        self._grid_rules()
    def _layout_grid(self):
        self._offsets = dict(zip(self.keys, cycle(range(self.side))))
        gridA = [0]
        for i in range(self.dims-2, 0, -1):
            gridA.append(gridA[-1] + i)
        self._gridA = dict((s,val) for sublist, val in zip(self.all_sets[:-1], gridA) for s in sublist)
        gridB = range(self.dims - 1)
        self._gridB = dict((s,val) for sublist, val in zip(self.all_sets[1:], gridB) for s in sublist)
        # sanity check
        cells = []
        for a_keys, b_keys in combinations(self.all_sets, 2):
            cells.extend(self.f(a,b) for a,b in product(a_keys, b_keys))
        assert len(cells) == len(list(set(cells)))
    def _grid_rules(self):
        f = self.f
        self.comment('one thing per axis')
        for a_keys, b_keys in combinations(self.all_sets, 2):
            for a in a_keys:
                cells = [f(a,b) for b in b_keys]
                self.write(window(cells, 1, 1))
            for b in b_keys:
                cells = [f(a,b) for a in a_keys]
                self.write(window(cells, 1, 1))
        self.comment('links in triples')
        # two of three not allowed
        for ak, bk, ck in combinations(self.all_sets, 3):
            for a,b,c in product(ak, bk, ck):
                c1,c2,c3 = f(a,b), f(a,c), f(b,c)
                self.write_one(c1, -c2, -c3)
                self.write_one(-c1, c2, -c3)
                self.write_one(-c1, -c2, c3)
    def _key_sort(self, a, b):
        if self.keys.index(a) > self.keys.index(b):
            return b, a
        return a, b
    def f(self, a, b):
        a,b = self._key_sort(a, b)
        side = self.side
        return self._offsets[a] * side + self._offsets[b] + 1 + \
               (self._gridA[a] + self._gridB[b]) * side*side
    def show(self, axes, num=3):
        "takes an ordered list of axes"
        for solution in self.solutions(num):
            for a in self.everything[axes[0]]:
                line = [a]
                for axe in axes[1:]:
                    line += [b for b in self.everything[axe] if self.f(a,b) in solution]
                print(' '.join(line))
            print('\n') 

def neighbors(x, y, x_range, y_range, diagonals=False):
    # return a function instead?
    cells = []
    if x_range is None and y_range is None:
        cells.append((x-1, y))
        cells.append((x+1, y))
        cells.append((x, y-1))
        cells.append((x, y+1))
        if not diagonals:
            return cells
        cells.append((x-1, y-1))
        cells.append((x-1, y+1))
        cells.append((x+1, y-1))
        cells.append((x+1, y+1))
        return cells

    x_min = min(x_range)
    x_max = max(x_range)
    y_min = min(y_range)
    y_max = max(y_range)
    if x != x_min:
        cells.append((x-1, y))
    if x != x_max:
        cells.append((x+1, y))
    if y != y_min:
        cells.append((x, y-1))
    if y != y_max:
        cells.append((x, y+1))
    if not diagonals:
        return cells
    if x != x_min and y != y_min:
        cells.append((x-1, y-1))
    if x != x_min and y != y_max:
        cells.append((x-1, y+1))
    if x != x_max and y != y_min:
        cells.append((x+1, y-1))
    if x != x_max and y != y_max:
        cells.append((x+1, y+1))
    return cells

def panel(*ranges):
    """ranges are exhaustive lists or inclusive tuple ranges or ints
    returns x/y/z/... generator"""
    ranges2 = []
    for r in ranges:
        if type(r) == tuple:
            ranges2.append(list(range(r[0], r[1]+1)))
            continue
        if type(r) == int:
            ranges2.append([r])
            continue
        ranges2.append(r)
    return product(*ranges2)


