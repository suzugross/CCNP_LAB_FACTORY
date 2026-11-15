#!/bin/bash
# E2E(J2・BL-275): set の束を Junos の機器に流して commit する。 apply.sh <束のファイル> [<機器 既定 JUN02>]
# clab_ops.py cli は行をそのまま CLI に流す(configure から commit まで 1 つのセッション)。
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
mapfile -t L < "$1"
"$REPO/.venv/bin/python3" "$REPO/topologies/clab_ops.py" cli --repo "$REPO" --problem JNT-03 --node "${2:-JUN02}" -- \
  configure "${L[@]}" 'commit and-quit' | grep -E 'commit complete|error|syntax'
