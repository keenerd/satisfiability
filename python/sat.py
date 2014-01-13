#! /usr/bin/env python

# works in python 2 or 3
# GPLv3

import os, time, shutil, tempfile, subprocess
from itertools import *
from collections import defaultdict

# todo
# more puzzle specific classes
# auto_term saving and preloading
# summary of automatic terms (debugging)
# "write protect" flag for auto_term   (auto_mode = rw|wo|ro)
# sanity check that all auto_terms are used?
# hybrid manual/auto_term

class CNF(object):
    def __init__(self, path=None, stdout=False, preloads=None):
        self.cnf_path = path
        if path is None:
            fh = tempfile.NamedTemporaryFile(delete=False)
            self.cnf_path = fh.name
            fh2 = tempfile.NamedTemporaryFile(delete=False)
            self.lut_path = fh2.name
            self.del_flag = True
        else:
            if path.endswith('.cnf'):
                path = path[:-4]
            self.cnf_path = path + '.cnf'
            self.lut_path = path + '.lut'
            fh = open(self.cnf_path, 'w+b')
            fh2 = open(self.lut_path, 'w+b')
            self.del_flag = False
        # closed file needed for py2 and windows compatibility
        fh.close()
        fh2.close()
        # adjust to whatever path you need
        self.minisat = 'minisat'
        self.clauses = 0
        self.limit = 100000
        self.maxterm = 0
        self.terms = set()
        self.stdout = stdout
        self.quiet = True
        self.term_lut = {}
        self.auto_history = []
        if preloads is None:
            preloads = []
        for preload in preloads:
            # todo, auto_term lut support
            self.comment('preloading %s' % preload)
            fh = open(self.cnf_path, 'ab')
            shutil.copyfileobj(open(preload, 'rb'), fh)
            fh.close()
    def write(self, cnf):
        "consumes an iterator of tuple clauses"
        fh = open(self.cnf_path, 'a')
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
        fh = open(self.cnf_path, 'a')
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
        shutil.copy(self.cnf_path, copy_path)
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
                solution = [n for n in solution if abs(n) in interesting] + [0]
            negative = ' '.join(map(str, [-n for n in solution]))
            open(cnf_path, 'a').write(negative + '\n')
        os.remove(cnf_path)
        os.remove(solve_path)
    def clear(self):
        "wipe the temp files, for interactive use only"
        fh = open(self.cnf_path, 'w+b')
        fh.close()
        fh = open(self.lut_path, 'w+b')
        fh.close()
        self.clauses = 0
    def close(self):
        if self.del_flag:
            os.remove(self.cnf_path)
            os.remove(self.lut_path)
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
            self.auto_history.append(args)
            self.term_lut[args] = self.maxterm + 1
            self.maxterm += 1
            fh = open(self.lut_path, 'a')
            # should not be a tuple?
            fh.write(repr(args) + '\t' + repr(self.term_lut[args]) + '\n')
            fh.close()
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

def if_gen(a, b, modeA=None, modeB=None, bidirectional=False):
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
    generator = []
    if modeA is None or modeB is None:
        raise Exception("must specify mode")
    if modeA == 'all' and modeB == 'all':
        generator = (neg(a) + (eb,) for eb in b)
    if modeA == 'all' and modeB == 'any':
        generator = [ (neg(a) + tuple(b)) ]
    if modeA == 'any' and modeB == 'all':
        generator = ((-ea, eb) for ea,eb in product(a, b))
    if modeA == 'any' and modeB == 'any':
        generator = ((-ea,) + tuple(b) for ea in a)
    for line in generator:
        yield line
    if bidirectional:
        for line in if_gen(b, a, modeB, modeA, bidirectional=False):
            yield line

def if_wrap(cell, clauses):
    for clause in clauses:
        yield [-cell] + list(clause)

def one_or_three(cells):
    assert len(cells) == 3  # crude prototype
    for clause in maybe(cells, 2):
        yield neg(clause)

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
        return self.auto_term(a, b)
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

def cartesian_adjacency(table, diagonals=False):
    "takes a 2D array (row major), returns adj dict"
    xlim = len(table[0])
    ylim = len(table)
    adj = defaultdict(set)
    for x,y in product(range(xlim), range(ylim)):
        points = neighbors(x, y, (0,xlim-1), (0,ylim-1), diagonals=diagonals)
        points = [table[yp][xp] for xp,yp in points]
        adj[table[y][x]].update(points)
    return adj

def expand(adj, cells):
    cells2 = set(cells)
    for c in cells:
        cells2 |= adj[c]
    return cells2

# is flood even possible with non-auto functions?
# add more cnf comments?
# might not work quite right with tuple keys in the base
# probably needs an option for slitherlink style fills

def floodfill(cnf, prefix, adj, size, exact=False, seed=None):
    "cnf object, unique prefix, adjacent table, z size, exact size, seed label.  returns summary labels"
    base = set(adj.keys())
    if seed is None:
        cells = base
    else:
        cells = set([seed])
    volume = set()
    f = cnf.auto_term
    method = ('unbounded', 'exact')[exact]
    cnf.comment('%s %s flood fill, size %i' % (prefix, method, size))
    for layer in range(size):
        # starting layer
        cells2 = [(prefix,c,layer) for c in cells]
        volume |= set(cells2)
        # single starting point
        if layer == 0:
            cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
            cells = expand(adj, cells)
            continue
        if exact:
            # always one per layer
            cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
        # growth rules
        for c in cells:
            cells3 = expand(adj, [c])
            if exact:
                # if none in previous layers, then not you
                cells3.discard(c)
                cells3 = set((prefix,c3,l3) for c3,l3 in product(cells3, range(layer)))
            else:
                # if under you, then also you
                cnf.write(if_then(f(prefix,c,layer-1), f(prefix,c,layer)))
                # if none under you, then not you
                cells3 = set((prefix,c3,layer-1) for c3 in cells3)
            cells3 &= volume
            cells3 = [f(*c3) for c3 in cells3]
            cnf.write([cells3 + [-f(prefix,c,layer)]])
        cells = expand(adj, cells)
    # misc linkages
    columns = defaultdict(set)
    for _,c,l in volume:
        columns[c].add((prefix,c,l))
    for c in columns:
        cells = [f(prefix,c,l) for _,_,l in columns[c]]
        if exact:
            # at most one per column
            cnf.write(window(cells, 0, 1))
        # if any in column, then summary
        cnf.write(if_gen(cells, f(prefix,'summary',c), modeA=any, bidirectional=True))
    # dead columns
    flat_volume = set(c for _,c,_ in volume)
    dead = base - flat_volume
    for c in dead:
        cnf.write_one(-f(prefix,'summary',c))
    summary_map = dict((c,(prefix,'summary',c)) for c in base)
    return summary_map

def line(cnf, prefix, adj, size, exact=False, closed=False, seed_start=None, seed_end=None, seed_mid=None):
    # todo, double conic with seed_end
    if seed_mid and (seed_start or seed_end):
        raise Exception("use only one seed")
    if closed and (seed_start or seed_end):
        raise Exception("loops don't have ends, use seed_mid")
    # place seeds
    seed = None
    if seed_start:
        seed = seed_start
    if seed_mid:
        seed = seed_mid
    base = set(adj.keys())
    if seed is None:
        cells = base
    else:
        cells = set([seed])
    volume = set()
    f = cnf.auto_term
    if seed:
        cnf.write(f(prefix, seed, 0))
    if seed_end:
        cnf.write(f(prefix, seed_end, size-1))
    steps = [(0, None)] + [(i, i-1) for i in range(1, size)]
    if closed:
        steps.append((size-1, 0))
    for layer,target in steps:
        cells2 = [(prefix,c,first) for c in cells]
        volume |= set(cells2)
        # one per layer
        cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
        # single starting point
        if layer == 0:
            cells = expand(adj, cells)
            continue
        # growth
        for c in cells:
            cells3 = expand(adj, [c])
            if exact:
                # no idling
                cells3.discard(c)
            cells3 = set((prefix,c3,target) for c3 in cells3)
            cells3 &= volume
            cells3 = [f(*c3) for c3 in cells3]
            cnf.write([cells3 + [-f(prefix,c,layer)]])
        cells = expand(adj, cells)
    # at most one per column
    columns = defaultdict(set)
    for _,c,l in volume:
        columns[c].add((prefix,c,l))
    for c in columns:
        cells = [f(prefix,c,l) for _,_,l in columns[c]]
        if exact:
            cnf.write(window(cells, 0, 1))
        else:
            cnf.write(window(cells, 1, 1))
    # summarize into a very weird adjacency table
    # unidirectional?  bidirectional?
    for c,links in adj.items():
        for l,t in steps:
            if t is None:
                continue
            for c2 in links:
                first = (prefix,c,t)
                second = (prefix,c2,l)
                if first not in volume or second not in volume:
                    cnf.write_one(-f(prefix, 'summary', c, c2))
                    continue
                cnf.write(if_gen([f(first), f(second)], f(prefix, 'summary', c, c2), modeA=all))
    # also summarize to a flat sheet?
    return

def segment(center, n, e, s, w):
    "binary points to unicode char"
    # full width character?  double line symbols?
    if not center:
        return ' '
    t = True
    f = False
    chars = {(t,t,t,t):'┼', (t,f,t,f):'│', (f,t,f,t):'─',
             (f,t,t,t):'┬', (t,f,t,t):'┤', (t,t,f,t):'┴', (t,t,t,f):'├',
             (t,t,f,f):'└', (f,t,t,f):'┌', (f,f,t,t):'┐', (t,f,f,t):'┘',
             (t,f,f,f):'╵', (f,t,f,f):'╶', (f,f,t,f):'╷', (f,f,f,t):'╴'}
    return chars[(n,e,s,w)]


