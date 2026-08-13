#!/bin/bash
# BL-115 全故障+build の連続実機検証
set -u
cd /home/suzuki/ansible/CCNP01
rm -rf problems/GEN-BGPBEST-9000* problems/GEN-BGPBEST-90010
bash poc/bgpbest/lab_sweep.sh nh_no_self 90001
bash poc/bgpbest/lab_sweep.sh acm_missing 90002
bash poc/bgpbest/lab_sweep.sh crid_missing 90003
bash poc/bgpbest/lab_sweep.sh weight_remote 90004
bash poc/bgpbest/lab_sweep.sh lp_ebgp 90005
bash poc/bgpbest/lab_sweep.sh med_swapped 90006
bash poc/bgpbest/lab_sweep.sh build 90010
echo "=== 全スイープ完了 ==="
grep -h '合計\|===' poc/bgpbest/sweep-*.log | tail -40
