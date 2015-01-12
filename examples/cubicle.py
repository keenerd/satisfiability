#! /usr/bin/env python

from sat import *

# http://web.mit.edu/puzzle/www/2003/www.acme-corp.com/teamGuest/R/5_092/index.html 
# a time-sequence logic puzzle
# python cubicle.py | column -t | less -S

puzzle = Sequence('/tmp/cubicle.cnf')
f = puzzle.f

events = 'spill handwrite guy_leaves 50cups 40cups 25cups 4cups'.split()
events += 'full_punch half_punch low_punch empty_punch'.split()
pages = '#1 #2 #3 #4 #5 #6 #7 #8'.split()

puzzle.load_axes(events, pages)
puzzle.every_event_happens()

puzzle.auto_mode = 'ro'

puzzle.comment('physical orderings')
puzzle.ordered('50cups 40cups 25cups 4cups'.split())
puzzle.ordered('full_punch half_punch low_punch empty_punch'.split())

puzzle.comment('spill')
f('spill', 'before', '#1')
f('spill', 'after', '#2')
f('spill', 'after', '#4')
f('spill', 'during', '#7')
f('spill', 'after', '#8')

puzzle.comment('handwrite phone number')
f('handwrite', 'during', '#2')
f('handwrite', 'after', '#5')
f('handwrite', 'before', '#7')
f('handwrite', 'before', '#8')

puzzle.comment('guy who left')
f('guy_leaves', 'after', '#3')
f('guy_leaves', 'after', '#5')
f('guy_leaves', 'during', '#6')
f('guy_leaves', 'after', '#8')

puzzle.comment('punch levels')
f('full_punch', 'during', '#3')
f('empty_punch', 'during', '#4')
f('half_punch', 'during', '#5')
f('low_punch', 'during', '#6')

puzzle.comment('solo cups')
f('4cups', 'during', '#1')
f('40cups', 'during', '#2')
f('50cups', 'during', '#3')
f('25cups', 'during', '#4')

puzzle.show_solutions(10)
#puzzle.verbose_solutions(extra_verbose=True)


