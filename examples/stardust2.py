#! /usr/bin/env python

from sat import *

# http://brownbuffalo.sourceforge.net/ComputerRomanceClues.html

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

# notes on stuff below:
# write_one(A)          -> A must be true
# write_one(-B)         -> B must be false
# window([C,D], 1, 1)   -> XOR relationship between C and D

cnf.comment("1. Silver Rose, who wore a blue velvet dress, did not meet her date through either the Baseball or the Opera news group.")
cnf.write_one(f('rose', 'dress'))
cnf.write_one(-f('rose', 'baseball'))
cnf.write_one(-f('rose', 'opera'))

cnf.comment("2. Hal9000 (who carried either the 'Herald' or the 'Times') met his date (who calls herself either Crafty Lady or Misty Morning) through their common love of fishing.")
cnf.write_one(f('hal', 'fishing'))
cnf.write(window([f('hal', 'herald'), f('hal', 'times')], 1, 1))
cnf.write(window([f('hal', 'crafty'), f('hal', 'misty')], 1, 1))
cnf.write(window([f('fishing', 'crafty'), f('fishing', 'misty')], 1, 1))

cnf.comment("3. Brenda (who is not a moviegoer) and the one who met her date through the Astronomy news group are the woman who encountered Midnight Rider and the one who wore scarlet begonias tucked into her curls, in some order.")
cnf.write_one(-f('brenda', 'movies'))
cnf.write_one(-f('brenda', 'astronomy'))
cnf.write_one(-f('rider', 'begonias'))
cnf.write(window([f('brenda', 'rider'), f('brenda', 'begonias')], 1, 1))
cnf.write(window([f('astronomy', 'rider'), f('astronomy', 'begonias')], 1, 1))

cnf.comment("4. Dorian and the man who carried the 'Bugle' are the man who met Sugar Magnolia and the one who recognized his date by her raspberry beret, in some order.")
cnf.write_one(-f('dorian', 'bugle'))
cnf.write_one(-f('magnolia', 'beret'))
cnf.write(window([f('dorian', 'magnolia'), f('dorian', 'beret')], 1, 1))
cnf.write(window([f('bugle', 'magnolia'), f('bugle', 'beret')], 1, 1))

cnf.comment("5. The man carrying the 'Star' (who isn't Brian) didn't meet Silver Rose.")
cnf.write_one(-f('star', 'brian'))
cnf.write_one(-f('star', 'rose'))

cnf.comment("6. Lori (who frequents either the Baseball or the Opera news group) met either Joel or Dr. Who.")
cnf.write_one(-f('joel', 'who'))
cnf.write(window([f('lori', 'baseball'), f('lori', 'opera')], 1, 1))
cnf.write(window([f('lori', 'joel'), f('lori', 'who')], 1, 1))

cnf.comment("7. The man carrying the 'Gazette' recognized his date from either the raspberry beret or the scarlet begonia.")
cnf.write(window([f('gazette', 'beret'), f('gazette', 'begonias')], 1, 1))

cnf.comment("8. Tracy, who is either the baseball enthusiast or the woman who wore the black veil, met Rocket Man.")
cnf.write_one(-f('baseball', 'veil'))
cnf.write_one(f('tracy', 'rocket'))
cnf.write(window([f('tracy', 'baseball'), f('tracy', 'veil')], 1, 1))

cnf.comment("9. Elusive Butterfly, who is either Christine or Olivia, wore neither the raspberry beret nor the black veil.")
cnf.write(window([f('butterfly', 'christine'), f('butterfly', 'olivia')], 1, 1))
cnf.write_one(-f('butterfly', 'beret'))
cnf.write_one(-f('butterfly', 'veil'))

cnf.comment("10. Christine met either Brian or the man with the 'Bugle', and Olivia's date is either Dr. Who or Walter.")
cnf.write(window([f('christine', 'brian'), f('christine', 'bugle')], 1, 1))
cnf.write_one(-f('brian', 'bugle'))
cnf.write(window([f('olivia', 'who'), f('olivia', 'walter')], 1, 1))
cnf.write_one(-f('who', 'walter'))

cnf.comment("11. Either Walter was carrying the 'Times', or he met Crafty Lady.")
cnf.write(window([f('walter', 'times'), f('walter', 'crafty')], 1, 1))

cnf.comment("12. Misty Morning is not a baseball fan.")
cnf.write_one(-f('misty', 'baseball'))

print('clauses:', cnf.clauses, '\n\n')
assert cnf.verify()

cnf.show('groups women she_alias articles men he_alias papers'.split())


