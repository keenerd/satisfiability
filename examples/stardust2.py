#! /usr/bin/env python

from sat import *

# http://brownbuffalo.sourceforge.net/ComputerRomanceClues.html

# GPLv3

# Zebra() requires that every tag be unique
groups = 'astronomy baseball fishing movies opera'.split()
women = 'brenda christine lori olivia tracy'.split()
she_alias = 'crafty butterfly misty rose magnolia'.split()
articles = 'ribbon dress begonias beret veil'.split()
men = 'brian dorian joel nick walter'.split()
he_alias = 'who hal rider flyer rocket'.split()
papers = 'herald times bugle star gazette'.split()

cnf = Zebra('/tmp/stardust.cnf')

all_axes = {'groups':groups, 'women':women, 'she_alias':she_alias,
            'articles':articles, 'men':men, 'he_alias':he_alias, 'papers':papers}

cnf.load_axes(all_axes)
f = cnf.f

true  = lambda a,b: cnf.write_one(f(a,b))
false = lambda a,b: cnf.write_one(-f(a,b))
xor   = lambda ab, cd: cnf.write(window([f(*ab), f(*cd)], 1, 1))

cnf.comment("1. Silver Rose, who wore a blue velvet dress, did not meet her date through either the Baseball or the Opera news group.")
true('rose', 'dress')
false('rose', 'baseball')
false('rose', 'opera')

cnf.comment("2. Hal9000 (who carried either the 'Herald' or the 'Times') met his date (who calls herself either Crafty Lady or Misty Morning) through their common love of fishing.")
true('hal', 'fishing')
xor(('hal', 'herald'), ('hal', 'times'))
xor(('hal', 'crafty'), ('hal', 'misty'))
xor(('fishing', 'crafty'), ('fishing', 'misty'))

cnf.comment("3. Brenda (who is not a moviegoer) and the one who met her date through the Astronomy news group are the woman who encountered Midnight Rider and the one who wore scarlet begonias tucked into her curls, in some order.")
false('brenda', 'movies')
false('brenda', 'astronomy')
false('rider', 'begonias')
xor(('brenda', 'rider'), ('brenda', 'begonias'))
xor(('astronomy', 'rider'), ('astronomy', 'begonias'))

cnf.comment("4. Dorian and the man who carried the 'Bugle' are the man who met Sugar Magnolia and the one who recognized his date by her raspberry beret, in some order.")
false('dorian', 'bugle')
false('magnolia', 'beret')
xor(('dorian', 'magnolia'), ('dorian', 'beret'))
xor(('bugle', 'magnolia'), ('bugle', 'beret'))

cnf.comment("5. The man carrying the 'Star' (who isn't Brian) didn't meet Silver Rose.")
false('star', 'brian')
false('star', 'rose')

cnf.comment("6. Lori (who frequents either the Baseball or the Opera news group) met either Joel or Dr. Who.")
false('joel', 'who')
xor(('lori', 'baseball'), ('lori', 'opera'))
xor(('lori', 'joel'), ('lori', 'who'))

cnf.comment("7. The man carrying the 'Gazette' recognized his date from either the raspberry beret or the scarlet begonia.")
xor(('gazette', 'beret'), ('gazette', 'begonias'))

cnf.comment("8. Tracy, who is either the baseball enthusiast or the woman who wore the black veil, met Rocket Man.")
false('baseball', 'veil')
true('tracy', 'rocket')
xor(('tracy', 'baseball'), ('tracy', 'veil'))

cnf.comment("9. Elusive Butterfly, who is either Christine or Olivia, wore neither the raspberry beret nor the black veil.")
xor(('butterfly', 'christine'), ('butterfly', 'olivia'))
false('butterfly', 'beret')
false('butterfly', 'veil')

cnf.comment("10. Christine met either Brian or the man with the 'Bugle', and Olivia's date is either Dr. Who or Walter.")
xor(('christine', 'brian'), ('christine', 'bugle'))
false('brian', 'bugle')
xor(('olivia', 'who'), ('olivia', 'walter'))
false('who', 'walter')

cnf.comment("11. Either Walter was carrying the 'Times', or he met Crafty Lady.")
xor(('walter', 'times'), ('walter', 'crafty'))

cnf.comment("12. Misty Morning is not a baseball fan.")
false('misty', 'baseball')

print('clauses:', cnf.clauses, '\n\n')
assert cnf.verify()

cnf.show('groups women she_alias articles men he_alias papers'.split())


