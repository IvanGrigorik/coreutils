#!/bin/bash


out_file="out.yaml"
rm $out_file
# out="$(../build/optarg-parser ../../src/kill.c -- -I../../lib/)"
# "$out" >> $out_file
# echo "File output:"
# echo "$out" > "$out_file"
echo "---" >> "$out_file"

for file in ../../src/*.c; do
    echo "File: $file"
    out="$(../build/optarg-parser "$file" -- -I../../lib/ 2> /dev/null)"
    if [[ ! "$out" ]]; then
        continue
    fi
    filename=$(basename "${file%.c}")
    echo "$filename:" >> "$out_file"
    echo "$out" >> "$out_file"
    # echo "------------------------" >> "$out_file"
done