#!/bin/bash
# XRT-15 の「やり直しでサーバも戻るか」の E2E(2026-11-14)。
#   白紙の最終採点 → 模範解+学ぶ側の痕跡(雛形を書き換え・ホームとテンプにファイル・gnmic の設定・http.server)→ 最終採点
#   → lab.sh reset → SRV01 と XR01 の残りを見る → すぐに課題ごとの確認(0 点のはず。M13-4 は直前まで届いていた)
#   → もう一度 模範解 → 最終採点(受け手が戻した後も動く)→ reset → 最終採点(白紙)
# usage: source poc/xr/env.sh; poc/xr/e2e_reset_xrt15.sh   記録= 標準出力(呼ぶ側で tee)
cd "$(dirname "$0")/../.."
M=topologies/_generated/XRT-15/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ipof XR01) SV=$(ipof SRV01)
L() { .venv/bin/python poc/xr/lxsh.py "$SV" "$@" 2>&1 | sed "s/$NODE_PASS/***/g"; }
X() { .venv/bin/python poc/xr/xrsh.py "$X1" "$@" 2>&1 | grep -vE "^\s*$|UTC$"; }
srv_state() {
  echo "-- SRV01 の状態"
  L 'true; echo "8080: $(ss -ltn | grep -c ":8080 ")"; pgrep -u "$USER" -a -f "python3|gnmic" | grep -v pgrep || echo "no python3/gnmic of $USER";
     ls -A ~ | tr "\n" " "; echo; ls -A ~/m13 | tr "\n" " "; echo; grep -c "MY-EDIT" ~/m13/nc_edit.py;
     ls -A /tmp | grep -E "mine|nc_" || echo "no learner files in /tmp";
     sudo -n wc -c /var/log/telegraf/mdt.json /var/log/snmptrapd-lab.log 2>&1 | head -3; echo "nfcapd files: $(ls /var/cache/nfdump/lab | wc -l)";
     systemctl is-active telegraf nfcapd-lab snmptrapd-lab | tr "\n" " "; echo'
  echo "-- XR01 の harddisk: の PEM"
  X 'run ls /harddisk:/ | grep -iE "pem|cert" || echo none'
}
step() { echo; echo "######## $(date -u +%H:%M:%S) $*"; }

step "1. 白紙の最終採点"
poc/xr/e2e_xrt15.sh final
step "2. 模範解+学ぶ側の痕跡"
PID=XRT-15 poc/xr/solve_xrt15.sh
L 'true; echo "# MY-EDIT" >> ~/m13/nc_edit.py; echo note > ~/mine-notes.txt; echo "skip-verify: true" > ~/.gnmic.yml; echo t > /tmp/mine.txt'
L "true; (setsid nohup gnmic -a 10.0.50.1:57400 -u '$NODE_USER' -p '$NODE_PASS' -e json_ietf --skip-verify --tls-cert ~/pki/client.pem --tls-key ~/pki/client.key subscribe --path openconfig-interfaces:interfaces/interface/state/counters --stream-mode sample --sample-interval 10s > /dev/null 2>&1 < /dev/null &); sleep 3; true"
srv_state
step "3. 最終採点(100 のはず)"
poc/xr/e2e_xrt15.sh final
step "3b. 採点の窓: SRV01 は戻さずに XR01 の送信だけを止め、すぐに M13-4 を確認(SRV01 の側は FAIL のはず)"
X configure 'no telemetry model-driven subscription SUB-IF' commit end | grep -iE "fail|error" || true
poc/xr/e2e_xrt15.sh m13t4 | grep -E "PASS|FAIL|合計" | cut -c1-140
step "3c. フローの確認の出力(読んだファイルの数)"
LAB_USER="$NODE_USER" LAB_PASS="$NODE_PASS" .venv/bin/python topologies/nms_probe.py XRT-15 flow CE1 Loopback100 10.255.0.1 SRV01 /var/cache/nfdump/lab --count 37 --wait 100 2>&1 | grep "^=="
step "4. lab.sh reset"
scripts/lab.sh reset XRT-15 2>&1 | grep -E "\[(XR01|PE2|SRV01)\]|ERROR|FAILED|退避|failed=" | cut -c1-200
srv_state
step "5. すぐに課題ごとの確認(すべて 0 のはず)"
poc/xr/e2e_xrt15.sh m13t4 m13t5 m13t1 m13t2 m13t3 m13t6 | grep -E "合計"
step "6. もう一度 模範解 → 最終採点(100 のはず)"
PID=XRT-15 poc/xr/solve_xrt15.sh
poc/xr/e2e_xrt15.sh final
step "7. reset → 最終採点(0 のはず)"
scripts/lab.sh reset XRT-15 2>&1 | grep -E "\[(SRV01)\]|ERROR|FAILED" | cut -c1-200
poc/xr/e2e_xrt15.sh final | grep -E "合計"
srv_state
