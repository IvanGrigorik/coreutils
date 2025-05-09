#!/bin/bash


rm out.txt

# out="$(../build/optarg-parser ../../src/kill.c -- -I../../lib/)"
# "$out" >> out.txt
# echo "File output:"
# echo "$out" > "out.txt"

for file in ../../src/*.c; do
    echo "File: $file"
    out="$(../build/optarg-parser "$file" -- -I../../lib/ 2> /dev/null)"
    if [[ ! "$out" ]]; then
        continue
    fi

    echo "File: $file:" >> "out.txt"
    echo "$out" >> "out.txt"
    echo "------------------------" >> "out.txt"
done