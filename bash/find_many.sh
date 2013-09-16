#! /bin/bash

# takes a cnf on $1
# solve is scratch file
# solutions has solutions

neg()
{
    tail -n 1 solve | sed -r -e 's/[1-9][0-9]* /-&/g' -e 's/--//g'
}

echo -n "" > solutions
cp "$1" "$1.tmp"

while ! minisat "$1.tmp" solve; do
    if grep -q UNSAT solve; then
        break
    fi
    tail -n 1 solve >> solutions
    echo "$(neg)" >> "$1.tmp"
done

rm "$1.tmp"

