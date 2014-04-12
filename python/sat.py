#! /usr/bin/env python
# -*- coding: utf-8 -*-

# works in python 2 or 3
# GPLv3

import os, time, shutil, tempfile, subprocess
from itertools import *
from collections import defaultdict

# todo
# more puzzle specific classes
# auto_term saving and preloading
# summary of automatic terms (debugging)
# sanity check that all auto_terms are used?
# hybrid manual/auto_term
# portable auto_term that flattens and strings everything
# maybe move the geometry stuff elsewhere
# random prefix generation

class CNF(object):
    def __init__(self, path=None, stdout=False, preloads=None):
        self.cnf_path = path
        if path is None:
            self.fh_cnf = tempfile.NamedTemporaryFile('w+', 1, delete=False)
            self.cnf_path = self.fh_cnf.name
            self.fh_lut = tempfile.NamedTemporaryFile('w+', 1, delete=False)
            self.lut_path = self.fh_lut.name
            self.del_flag = True
        else:
            if path.endswith('.cnf'):
                path = path[:-4]
            self.cnf_path = path + '.cnf'
            self.lut_path = path + '.lut'
            self.fh_cnf = open(self.cnf_path, 'w+', 1)
            self.fh_lut = open(self.lut_path, 'w+', 1)
            self.del_flag = False
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
        self.auto_mode = 'rw'  # rw, ro, wo
        if preloads is None:
            preloads = []
        for preload in preloads:
            # todo, auto_term lut support
            self.comment('preloading %s' % preload)
            shutil.copyfileobj(open(preload, 'rb'), self.fh_cnf)
    def write(self, cnf):
        "consumes an iterator of tuple clauses"
        for i,line in enumerate(cnf):
            line = list(line)
            if min(map(abs, line)) == 0:
                raise Exception("Illegal term, 0")
            self.maxterm = max(self.maxterm, max(line), abs(min(line)))
            #if i > self.limit:
            #    raise Exception("Overclause!")
            output = ' '.join(map(str, list(line) + [0]))
            #self.fh_cnf.write((output + '\n').encode('utf-8'))
            self.fh_cnf.write(output + '\n')
            if self.stdout:
                print(output)
            self.clauses += 1
            self.terms.update(map(abs, line))
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
        self.fh_cnf.write('c ' + c + '\n')
        if self.stdout or not self.quiet:
            print('c ' + c)
    def _close_cnf(self):
        "probably needed for os compatibility"
        self.fh_cnf.flush()
        os.fsync(self.fh_cnf.fileno())
        self.fh_cnf.close()
    def _reopen_cnf(self):
        "probably needed for os compatibility"
        self.fh_cnf = open(self.cnf_path, 'a+', 1)
    def _run_minisat(self, cnf_path, solve_path):
        self._close_cnf()
        pipe = subprocess.PIPE
        status = subprocess.call([self.minisat, cnf_path, solve_path], stdout=pipe, stderr=pipe)
        self._reopen_cnf()
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
        self._close_cnf()
        shutil.copy(self.cnf_path, copy_path)
        self._reopen_cnf()
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
    def solutions(self, how_many=1, interesting=None, extreme_unique=False):
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
            # goofy, but occasionally useful
            if extreme_unique:
                for n in solution:
                    if n <= 0:
                        continue
                    if interesting and n not in interesting:
                        continue
                    open(cnf_path, 'a').write('%i 0\n' % -n)
        os.remove(cnf_path)
        os.remove(solve_path)
    def clear(self):
        "wipe the temp files, for interactive use only"
        self.fh_cnf.close()
        self.fh_cnf = open(self.cnf_path, 'w+', 1)
        self.fh_lut.close()
        self.fh_lut = open(self.lut_path, 'w+', 1)
        self.clauses = 0
        self.maxterm = 0
        self.terms = set()
        self.term_lut = {}
        self.auto_history = []
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
        if args in self.term_lut:
            if 'r' not in self.auto_mode:
                raise Exception("Error: existing label " + str(args))
        else:
            if 'w' not in self.auto_mode:
                raise Exception("Error: creating label " + str(args))
        if args not in self.term_lut:
            self.auto_history.append(args)
            self.term_lut[args] = self.maxterm + 1
            self.maxterm += 1
            # should not be a tuple?
            self.fh_lut.write(repr(args) + '\t' + repr(self.term_lut[args]) + '\n')
        return self.term_lut[args]
    def auto_search(self, *args):
        "provide matching functions, returns terms"
        # todo, regex or something less messy
        # and allow for variable length matches
        for term in self.term_lut:
            if len(args) != len(term):
                continue
            if all(a(t) for a,t in zip(args, term)):
                yield term

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
    "force equivalency, all false or all true"
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
    "relationship is one way, b cannot affect a"
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
    def load_axes(self, values, size=None):
        "takes a dictionary of lists"
        self.everything = values
        self.all_sets = list(values.values())
        self.dims = len(values)
        self.size = size
        if size is None:  # only works with square puzzles
            self.size = len(self.all_sets[0])
        self.keys = [v for vals in values.values() for v in vals]
        assert len(self.keys) == len(list(set(self.keys)))
        self._sanity_check()
        self._grid_rules()
    def _sanity_check(self):
        cells = []
        for a_keys, b_keys in combinations(self.all_sets, 2):
            cells.extend(self.f(a,b) for a,b in product(a_keys, b_keys))
        assert len(cells) == len(list(set(cells)))
    def _grid_rules(self):
        f = self.f
        self.comment('one thing per axis')
        for a_keys, b_keys in combinations(self.all_sets, 2):
            for a in a_keys:
                if len(a_keys) != self.size:  # unless axis is lopsided
                    break
                cells = [f(a,b) for b in b_keys]
                self.write(window(cells, 1, 1))
            for b in b_keys:
                if len(b_keys) != self.size:
                    break
                cells = [f(a,b) for a in a_keys]
                self.write(window(cells, 1, 1))
        self.comment('links in triples')
        # two of three not allowed, unless lopsided
        for ak, bk, ck in combinations(self.all_sets, 3):
            for a,b,c in product(ak, bk, ck):
                c1,c2,c3 = f(a,b), f(a,c), f(b,c)
                if len(ck) == self.size:
                    self.write_one(c1, -c2, -c3)
                if len(bk) == self.size:
                    self.write_one(-c1, c2, -c3)
                if len(ak) == self.size:
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

def cartesian_table(xs, ys, diagonals=False):
    "adj dict uses (x,y) tuples as keys"
    adj_table = []
    for y in ys:
        adj_table.append([])
        for x in xs:
            adj_table[-1].append((x,y))
    adj = cartesian_adjacency(adj_table)
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

def segment(center, n, e, s, w):
    "binary points to unicode char"
    # full width character?  double line symbols?
    if not center:
        return ' '
    t = True
    f = False
    chars = {(t,t,t,t):'┼', (t,f,t,f):'│', (f,t,f,t):'─', (f,f,f,f):'·',
             (f,t,t,t):'┬', (t,f,t,t):'┤', (t,t,f,t):'┴', (t,t,t,f):'├',
             (t,t,f,f):'└', (f,t,t,f):'┌', (f,f,t,t):'┐', (t,f,f,t):'┘',
             (t,f,f,f):'╵', (f,t,f,f):'╶', (f,f,t,f):'╷', (f,f,f,t):'╴'}
    return chars[(n,e,s,w)]


