#! /usr/bin/env python
# -*- coding: utf-8 -*-

# works in python 2 or 3
# GPLv3

import os, time, shutil, tempfile, subprocess
from itertools import *
from collections import defaultdict, deque

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
        self.fh_cnf.write('p cnf 0 0\n')
        # adjust to whatever path and options you need
        self.minisat = 'minisat'
        self.picosat = 'picosat'
        self.solver = self._run_minisat  # override this too
        self.clauses = 0
        self.limit = 100000
        self.maxterm = 0
        self.terms = set()
        self.stdout = stdout
        self.quiet = True
        self.term_lut = {}
        self.auto_history = []
        self.auto_mode = 'rw'  # rw, ro, wo
        self._auto_stack = []
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
        self.fh_lut.write('# ' + c + '\n')
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
        cmd = self.minisat
        if type(cmd) == str:
            cmd = [cmd]
        cmd += [cnf_path, solve_path]
        status = subprocess.call(cmd, stdout=pipe, stderr=pipe)
        self._reopen_cnf()
        if status == 1:
            raise Exception("Minisat return 1, SIGINT or unreadable input")
        if status == 3:
            raise Exception("Minisat return 3, input parsing failure")
        if status == 10:
            solution = open(solve_path).readlines()[-1].strip()
            solution = list(map(int, solution.split(' ')))
            return set(n for n in solution if n > 0)
        if status == 20:
            return False
        raise Exception("Unknown minisat return %i" % status)
    def _run_picosat(self, cnf_path, solve_path):
        self._close_cnf()
        pipe = subprocess.PIPE
        cmd = self.picosat
        if type(cmd) == str:
            cmd = [cmd]
        cmd += ['-f', '-o', solve_path, cnf_path]
        status = subprocess.call(cmd, stdout=pipe, stderr=pipe)
        self._reopen_cnf()
        if status == 10:
            solution = set()
            for line in open(solve_path):
                solution.update(line.strip().split())
            solution -= set(['s', 'SATISFIABLE', 'v'])
            return set(int(n) for n in solution if int(n) > 0)
        if status == 20:
            return False
        raise Exception("Unknown picosat return %i" % status)
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
        if not min(self.terms) == 1:
            raise Exception("CNF does not start at 1")
        if not max(self.terms) == len(self.terms):
            #print(max(self.terms), len(self.terms))
            #print(set(range(1, max(self.terms)+1)) - self.terms)
            print('gap size:', abs(max(self.terms) - len(self.terms)))
            for k,v in self.term_lut.items():
                if v not in self.terms:
                    print(k)
            raise Exception("CNF has gaps")
        cnf_path,solve_path  = self.setup_temps()
        status = bool(self.solver(cnf_path, solve_path))
        os.remove(cnf_path)
        os.remove(solve_path)
        if not status:
            raise Exception("No possible solutions")
        if allow_partial:
            return True
        return True
    def solutions(self, how_many=1, interesting=None, extreme_unique=False):
        "'interesting' is the subset of cells that matter for the solution"
        if interesting is None:
            interesting = set([])
        interesting = set(interesting)
        cnf_path,solve_path  = self.setup_temps()
        for i in range(how_many):
            solution = self.solver(cnf_path, solve_path)
            if not solution:
                break
            yield solution
            if interesting:
                solution = [n for n in solution if abs(n) in interesting]
            negative = ' '.join(map(str, [-n for n in solution]))
            open(cnf_path, 'a').write(negative + ' 0\n')
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
                raise Exception("Error: pre-existing label " + str(args))
        else:
            if 'w' not in self.auto_mode:
                raise Exception("Error: ro label creation " + str(args))
        if args not in self.term_lut:
            self.auto_history.append(args)
            self.term_lut[args] = self.maxterm + 1
            self.maxterm += 1
            # should not be a tuple?
            lut_line = repr(args) + '\t' + repr(self.term_lut[args])
            if lut_line.startswith('#'):
                lut_line = lut_line.replace('#', '\#', 1)
            self.fh_lut.write(lut_line + '\n')
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
    def auto_stack_push(self, new_mode):
        "for internal functions to preserve user-set mode state"
        self._auto_stack.append(self.auto_mode)
        self.auto_mode = new_mode
    def auto_stack_pop(self):
        "for internal functions to preserve user-set mode state"
        self.auto_mode = self._auto_stack.pop()

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

def consecutive(cells1, cells2, circular=False):
    "element of c1 must come immediately before element of c2"
    cells1 = list(cells1)
    cells2 = list(cells2)
    assert len(cells1) == len(cells2)
    for c1,c2 in zip(cells1, cells2):
        yield (-c1, -c2)
    for c1,c2 in zip(cells1, cells2[1:]):
        # xnor / maybe(2) / if-then
        yield (-c1, c2)
        yield (c1, -c2)
    if circular:
        yield (-cells1[-1], cells2[0])
        yield (cells1[-1], -cells2[0])
    else:
        yield (-cells1[-1],)
        yield (-cells2[0],)

def adjacent(cells1, cells2, circular=False):
    # todo, make be O(n) again
    assert len(cells1) == len(cells2)
    for i1,i2 in product(range(len(cells1)), range(len(cells2))):
        if i1+1 == i2:
            continue
        if i1-1 == i2:
            continue
        if circular and i1==0 and i2==len(cells2)-1:
            continue
        if circular and i2==0 and i1==len(cells1)-1:
            continue
        yield(-cells1[i1], -cells2[i2])

def not_adjacent(cells1, cells2, circular=False):
    assert len(cells1) == len(cells2)
    for i in range(len(cells1)):
        if not circular and i == 0:
            continue
        yield(-cells1[i], -cells2[i-1])
        yield(-cells2[i], -cells1[i-1])

def if_then(a, b):
    "relationship is one way, b cannot affect a"
    yield (-a, b)

def anyall(n):
    if n == all:
        return 'all'
    if n == any:
        return 'any'
    return n

def if_gen(a, b, modeA=None, modeB=None, bidirectional=False):
    "a and b can be lists, mode=any/all"
    # will probably bug out on iterator input
    if type(a) == int:
        a = [a]
        modeA = 'all'
    if type(b) == int:
        b = [b]
        modeB = 'all'
    modeA = anyall(modeA)
    modeB = anyall(modeB)
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
    def load_axes(self, values, size=None, unconstrained=None):
        "takes a dictionary of lists"
        # uncons. is an experimental feature to let tags to exist multiple times
        self.everything = values
        self.all_sets = list(values.values())
        self.dims = len(values)
        self.size = size
        self.unconstrained = unconstrained
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
        uncon = self.unconstrained
        self.comment('one thing per axis')
        for a_keys, b_keys in combinations(self.all_sets, 2):
            for a in a_keys:
                if len(a_keys) != self.size:  # unless axis is lopsided
                    break
                if a in uncon:
                    break
                cells = [f(a,b) for b in b_keys if b not in uncon]
                if not cells:
                    continue
                self.write(window(cells, 1, 1))
            for b in b_keys:
                if len(b_keys) != self.size:
                    break
                if b in uncon:
                    break
                cells = [f(a,b) for a in a_keys if a not in uncon]
                if not cells:
                    continue
                self.write(window(cells, 1, 1))
        self.comment('links in triples')
        # two of three not allowed, unless lopsided
        for ak, bk, ck in combinations(self.all_sets, 3):
            for a,b,c in product(ak, bk, ck):
                c1,c2,c3 = f(a,b), f(a,c), f(b,c)
                if len(ck) == self.size and c not in uncon:
                    self.write_one(c1, -c2, -c3)
                if len(bk) == self.size and b not in uncon:
                    self.write_one(-c1, c2, -c3)
                if len(ak) == self.size and a not in uncon:
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

class Sequence(CNF):
    "handles everything for a time-sequence puzzle"
    def load_axes(self, events, pages):
        "takes non-overlapping lists"
        assert len(events) + len(pages) == len(set(events) | set(pages))
        self.events = events
        self.pages = pages
        self.ticks = ['time%i' % i for i in range(1, len(list(pages))+1)]
        self._grid_rules()
    def _grid_rules(self):
        f = self.auto_term
        self.auto_stack_push('wo')
        self.comment('generating terms')
        for t,p in product(sorted(self.ticks), sorted(self.pages)):
            f(t, p)
        for t,e in product(sorted(self.ticks), sorted(self.events)):
            f(t, e, 'state')
            f(t, e, 'transition')
        self.auto_mode = 'ro'
        self.comment('each event once')
        for t in self.ticks:
            cells = [f(t,p) for p in self.pages]
            self.write(window(cells, 1, 1))
        for p in self.pages:
            cells = [f(t,p) for t in self.ticks]
            self.write(window(cells, 1, 1))
        for e in self.events:
            cells = [f(t, e, 'transition') for t in self.ticks]
            self.write(window(cells, 0, 1))
        self.comment('time links')
        for e in self.events:
            for t1,t2 in zip(self.ticks[:-1], self.ticks[1:]):
                c1 = f(t1, e, 'state')
                c2 = f(t1, e, 'transition')
                c3 = f(t2, e, 'state')
                c4 = f(t2, e, 'transition')
                self.write_one(-c2,  c1)
                self.write_one(-c4,  c3)
                self.write_one(-c1,  c3)
                self.write_one(-c1, -c4)
                self.write_one( c1,  c4, -c3)
        self.comment('initial state')
        for e in self.events:
            self.write_one(-f('time1', e, 'state'))
        self.auto_stack_pop()
    def every_event_happens(self):
        for e in self.events:
            self.write_one(self.auto_term(self.ticks[-1], e, 'state'))
    def s(self, string):
        "too lazy to quote"
        command = string.split()
        assert len(command) == 3
        self.f(*command)
    def f(self, thing1, mode, thing2):
        "single event, mode is (before during after), single event/page"
        if mode not in ['before', 'during', 'after']:
            raise Exception('bad mode %s' % mode)
        if thing1 not in self.events + self.pages:
            raise Exception('bad thing %s' % thing1)
        if thing2 not in self.events + self.pages:
            raise Exception('bad thing %s' % thing2)
        if thing1 in self.events and thing2 in self.pages:
            return self.f2(thing1, mode, thing2)
        if thing1 in self.events and thing2 in self.events:
            return self.f3(thing1, mode, thing2)
        if thing1 in self.pages and thing2 in self.pages:
            return self.f4(thing1, mode, thing2)
        raise Exception('new f() combo?')
    def f2(self, event, mode, page):
        for t in self.ticks:
            s1 = self.auto_term(t, event, 'state')
            t1 = self.auto_term(t, event, 'transition')
            p1 = self.auto_term(t, page)
            if mode == 'before':
                self.write(if_gen(p1, s1, bidirectional=False))
                self.write(if_gen(-s1, -p1, bidirectional=False))
                self.write(if_gen(p1, -t1, bidirectional=False))
                self.write(if_gen(t1, -p1, bidirectional=False))
            if mode == 'during':
                self.write(if_gen(p1, t1, bidirectional=True))
            if mode == 'after':
                self.write(if_gen(p1, -s1, bidirectional=False))
                self.write(if_gen(s1, -p1, bidirectional=False))
                self.write(if_gen(p1, -t1, bidirectional=False))
                self.write(if_gen(t1, -p1, bidirectional=False))
    def f3(self, event1, mode, event2):
        for t in self.ticks:
            s1 = self.auto_term(t, event1, 'state')
            s2 = self.auto_term(t, event2, 'state')
            t1 = self.auto_term(t, event1, 'transition')
            t2 = self.auto_term(t, event2, 'transition')
            if mode == 'before':
                self.write(if_gen(s2, s1, bidirectional=False))
                self.write(if_gen(-s1, -s2, bidirectional=False))
                self.write_one(-t1, -t2)
            if mode == 'during':
                self.write(if_gen(t1, t2, bidirectional=True))
            if mode == 'after':
                self.write(if_gen(s2, -s1, bidirectional=False))
                self.write(if_gen(s1, -s2, bidirectional=False))
                self.write(if_gen(s2, -t2, bidirectional=False))
                self.write(if_gen(t2, -s2, bidirectional=False))
    def f4(self, page1, mode, page2):
        if mode == 'during':
            raise Exception('bad mode %s' % mode)
        for i,t1 in enumerate(self.ticks):
            for j,t2 in enumerate(self.ticks):
                if t1 == t2:
                    continue
                if mode == 'before' and i < j:
                    continue
                if mode == 'after' and i > j:
                    continue
                p1 = self.auto_term(t1, page1)
                p2 = self.auto_term(t2, page2)
                self.write_one(-p1, -p2)
    def tally_state(self, n, events, page):
        for t in self.ticks:
            cells = [self.auto_term(t, e, 'state') for e in events]
            p = self.auto_term(t, page)
            for line in window(cells, n, n):
                self.write([[-p] + list(line)])
    def tally_transition(self, n, events, page):
        for t in self.ticks:
            cells = [self.auto_term(t, e, 'transition') for e in events]
            p = self.auto_term(t, page)
            for line in window(cells, n, n):
                self.write([[-p] + list(line)])
    def nth_page(self, page, n):
        "n=0 for first, n=-1 for last"
        self.write_one(self.auto_term(self.ticks[n], page))
    def ordered(self, events):
        "list of events from oldest to newest"
        for e1, e2 in zip(events[:-1], events[1:]):
            self.f(e1, 'before', e2)
    def show_solutions(self, n=3):
        print('terms:', self.maxterm)
        print('clauses:', self.clauses)
        #self.verify()
        for solution in self.solutions(n):
            print()
            #print(sorted(list(solution)))
            for t in self.ticks:
                line = [t]
                line.extend(p for p in self.pages if self.auto_term(t, p) in solution)
                line.extend(e for e in self.events if self.auto_term(t, e, 'transition') in solution)
                print(' '.join(line))
    def verbose_solutions(self, n=3):
        #self.verify()
        for solution in self.solutions(n):
            print()
            #print(sorted(list(solution)))
            for t in self.ticks:
                line = [t]
                line.extend(p for p in self.pages if self.auto_term(t, p) in solution)
                line.extend([e, e.upper()][self.auto_term(t, e, 'transition') in solution] for e in self.events if self.auto_term(t, e, 'state') in solution)
                print(' '.join(line))

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
    adj = cartesian_adjacency(adj_table, diagonals)
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

def floodfill(cnf, prefix, adj, size, exact=False, seed=None, wrap=False):
    "cnf object, unique prefix, adjacent table, z size, exact size, seed label.  returns summary labels"
    assert not(not exact and wrap)
    base = set(adj.keys())
    if seed is None:
        cells = base
    else:
        cells = set([seed])
    volume = set()
    f = cnf.auto_term
    method = ('unbounded', 'exact')[exact]
    method += ' ' + ('unbounded', 'wrap-around')[wrap]
    cnf.comment('%s %s flood fill, size %i' % (prefix, method, size))
    for layer in range(size):
        # starting layer
        cells2 = [(prefix,c,layer) for c in cells]
        volume |= set(cells2)
        # single starting point
        if layer == 0:
            cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
        if layer == 0 and not wrap:
            cells = expand(adj, cells)
            continue
        if exact and layer > 0:
            # always one per layer
            cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
        # growth rules
        prev_layer = (layer - 1) % size
        for c in cells:
            cells3 = expand(adj, [c])
            if exact:
                # if none in previous layers, then not you
                cells3.discard(c)
                cells3 = set((prefix,c3,l3) for c3,l3 in product(cells3, range(layer)))
            else:
                # if under you, then also you
                cnf.write(if_then(f(prefix,c,prev_layer), f(prefix,c,layer)))
                # if none under you, then not you
                cells3 = set((prefix,c3,prev_layer) for c3 in cells3)
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
    cnf.auto_stack_pop()
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

def tree_one(cnf, prefix, cells):
    "like window(0,1) or window(1,1) but O(n) instead of O(n^2) (uses autoterm)"
    # returns a summary term: "is there a true in the cells"
    # todo, make as generic as window
    f = cnf.auto_term
    node_count = 0
    cells = deque(cells)
    cnf.auto_stack_push('ro')
    assert len(cells) > 0
    while len(cells) > 1:
        a = cells.pop()
        b = cells.pop()
        cnf.auto_stack_push('wo')
        c = f(prefix, node_count)
        cnf.auto_stack_pop()
        # window(0, 1)
        cnf.write_one(-a, -b)
        # if_then(a, c), if_then(b, c)
        cnf.write_one(-a, c)
        cnf.write_one(-b, c)
        # if c then a or b
        cnf.write_one(-c, a, b)
        cells.appendleft(c)
        node_count += 1
    cnf.auto_stack_pop()
    return cells[0]


