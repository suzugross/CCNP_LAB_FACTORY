#!/bin/bash
# JNT-02 の確認を 1 本流し、PASS/FAIL と未充足だけを出す(E2E 用)
cd /home/suzuki/ansible/CCNP01
LAB_CP_ATTEMPTS=${A:-2} timeout 600 scripts/lab.sh checkpoint JNT-02 "$1" 2>&1 | grep -E "^\s+- '(\[PASS\]|\[FAIL\]|\s+未充足)" | sed -E "s/^\s+- '//; s/'$//" | cut -c1-170
