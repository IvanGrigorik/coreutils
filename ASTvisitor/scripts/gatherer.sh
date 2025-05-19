#!/bin/bash

# Files preparation
mkdir -p ../out/
out_file="../out/nonunified.yaml"
rm $out_file

# Output YAML
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