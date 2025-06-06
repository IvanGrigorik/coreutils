#!/bin/sh
# move a directory into itself, with a twist

# Copyright (C) 1998-2025 Free Software Foundation, Inc.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

. "${srcdir=.}/tests/init.sh"; path_prepend_ ./src
print_ver_ mv

dir1=is3-dir1
dir2=is3-dir2

mkdir $dir1 $dir2 || framework_failure_

# This mv command should exit nonzero.
mv $dir1 $dir2 $dir2 > out 2>&1 && fail=1

sed \
   -e "s,mv:,XXX:,g" \
   -e "s,$dir2,ZZZ,g" \
  out > out2

cat > exp <<\EOF
XXX: cannot move 'ZZZ' to a subdirectory of itself, 'ZZZ/ZZZ'
EOF

compare exp out2 || fail=1

Exit $fail
