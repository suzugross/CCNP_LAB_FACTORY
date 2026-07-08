#!/usr/bin/env bash
# STEP 1: まずは curl で RESTCONF を叩いてみる（GET = 読むだけ・壊れない）。
#   -k : ラボの自己署名証明書を許容
#   -u : Basic認証（機器のローカルユーザ = SSH と同じ SUZUKI/CCNP）
RT01=10.1.10.11

echo "=== 1-1. RESTCONF ルート（疎通確認） ==="
curl -sk -u SUZUKI:CCNP \
  -H "Accept: application/yang-data+json" \
  "https://$RT01/restconf/"
echo

echo "=== 1-2. 全インタフェース設定（ietf-interfaces モジュール） ==="
curl -sk -u SUZUKI:CCNP \
  -H "Accept: application/yang-data+json" \
  "https://$RT01/restconf/data/ietf-interfaces:interfaces"
echo
