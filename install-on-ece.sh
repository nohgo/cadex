#!/bin/sh
set -eu
cd "$(dirname "$0")"
ssh -O check ece
COPYFILE_DISABLE=1 tar --no-xattrs -cf - AGENTS.md install.py skills scripts |
  ssh ece "sh -c 'set -eu; d=\$(mktemp -d); cd \"\$d\"; tar -xf -; python3 install.py; cd /; rm -r \"\$d\"'"
