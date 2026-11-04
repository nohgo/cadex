#!/bin/sh
set -eu
case "${1-}" in
  "") live_arg= ;;
  --live) live_arg=--live ;;
  *) printf 'Usage: sh install-on-ece.sh [--live]\n' >&2; exit 64 ;;
esac
[ "$#" -le 1 ] || exit 64
cd "$(dirname "$0")"
ssh -O check ece
COPYFILE_DISABLE=1 tar --no-xattrs -cf - AGENTS.md install.py skills scripts live |
  ssh ece "sh -c 'set -eu; d=\$(mktemp -d); cd \"\$d\"; tar -xf -; python3 install.py $live_arg; cd /; rm -r \"\$d\"'"
