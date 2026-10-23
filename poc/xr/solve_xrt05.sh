#!/bin/bash
# XRT-05 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt05.sh <XR01 の管理 IP> [m4t5 … m4t8](既定= 全部)
#   誤答の確かめ用: m4t5-nolevel(LSP の認証をレベルなしで)・m4t8-swap(NET を 1 コミットで入れ替え)・m4t8-back(49.0001 だけに戻す)
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m4t5 m4t6 m4t7 m4t8}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error" || true; }
KEY=( 'key chain ISIS-L2' 'key 1' 'key-string clear Bb0ne-2026' 'cryptographic-algorithm HMAC-MD5'
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' root )
for s in $steps; do case $s in
m4t5)
  X configure "${KEY[@]}" 'router isis CORE' 'lsp-password keychain ISIS-L2 level 2' \
    'interface GigabitEthernet0/0/0/1' 'hello-password keychain ISIS-L2' exit \
    'interface GigabitEthernet0/0/0/2' 'hello-password keychain ISIS-L2' commit end ;;
m4t5-nolevel)
  X configure "${KEY[@]}" 'router isis CORE' 'lsp-password keychain ISIS-L2' \
    'interface GigabitEthernet0/0/0/1' 'hello-password keychain ISIS-L2' exit \
    'interface GigabitEthernet0/0/0/2' 'hello-password keychain ISIS-L2' commit end ;;
m4t6)
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/3' 'circuit-type level-2-only' 'priority 100' \
    'hello-password keychain ISIS-L2' 'address-family ipv4 unicast' exit 'address-family ipv6 unicast' commit end ;;
m4t7)
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'summary-prefix 10.11.0.0/16 level 2' exit \
    'address-family ipv6 unicast' 'summary-prefix 2001:db8:1011::/48 level 2' commit end ;;
m4t8)
  X configure 'router isis CORE' 'net 49.0010.0102.5500.0001.00' commit end
  sleep 20
  X configure 'router isis CORE' 'no net 49.0001.0102.5500.0001.00' commit end ;;
m4t8-swap)
  X configure 'router isis CORE' 'no net 49.0001.0102.5500.0001.00' 'net 49.0010.0102.5500.0001.00' commit end ;;
m4t8-back)
  X configure 'router isis CORE' 'no net 49.0010.0102.5500.0001.00' 'net 49.0001.0102.5500.0001.00' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
