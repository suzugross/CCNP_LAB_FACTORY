#!/usr/bin/env python3
"""GEN-AAAGRP — IOS AAA サーバグループ構築問の生成器（難易度4・BL-001 / BL-101 P2）。

紙面ファミリ `shape=aaa` と**同じ盤面・同じ語彙**の実機側。紙面で読んだ症状を
ここで自分の手で組む(両刀)。設計= problems/_drafts/GEN-AAAGRP.design.md ＋
problems/_drafts/AAA-BASE.design.md §1/§4。

正準盤面(4ノード):
    SRV01(FreeRADIUS 標準ポート) ──┐
                                   RT01 ────── RT02
    SRV02(FreeRADIUS 非標準ポート)─┘
  ★RT01=サーバ直結 / RT02=1ホップ先。サーバ側 clients は **各ルータの Loopback0 のみ**
    許可 → `ip radius source-interface Loopback0` が無いと**無言破棄→タイムアウト**。
    これが本問の主罠(GEN-RADIUS-* と違い、サーバ側は完成品で渡す)。

★実測に基づく採点設計(poc/aaa/results-grade.md・2026-08-09):
  - `_grade_attempt.yml` は **exec=ios を全件先に集めてから exec=shell** を回す。
    そのため「サーバを止めてからルータを見る」順序はチェックの並びでは作れない。
    → **破壊フェーズ(片系断/全断)は SRV01 上の 1 本のスクリプトに閉じ込める**。
      スクリプトの中から sshpass+ssh でルータへ実ログインして観測する(G1= 素の ssh で可)。
  - 採点は最大 10 回再試行されるので、破壊フェーズは**冪等かつ自己復旧**。
    スクリプトは trap で必ず両サーバを起動して終わる。
  - ★懸念だった `deadtime` の残留は**実測で否定**された(G3)。全断で両サーバが dead に
    なっても、復旧させれば **0 秒**で RADIUS が再び使える。採点が収束しなくなる恐れは無い。
  - 遅延は `timeout × (retransmit+1) × 到達不能サーバ数` で説明できる(実測 6.3s / 12.3s)。

出力: problems/GEN-AAAGRP-<seed>/
使い方: gen_aaa_build.py --repo . --seed <int>
"""
import argparse
import json
import os
import random

import yaml

RTS = ["RT01", "RT02"]
SRVS = ["SRV01", "SRV02"]
CORE = "10.1.12"                     # RT01=.1 / RT02=.2
RT02_INBAND = "10.1.12.2"

ADMINS = ["noc-taro", "noc-hanako", "netadmin", "adm-kato", "ope-suzuki"]
VIEWERS = ["helpdesk", "monitor-op", "watch-op", "desk-01"]
EMERGENCY = ["emg-admin", "local-admin", "break-glass"]
GROUPS = ["AAA-SRV", "RADGRP", "NOC-RADIUS", "RAD-GROUP", "AUTH-GRP"]
# SRV02 の非標準ポート候補(auth, acct)
NONSTD = [(1912, 1913), (11812, 11813), (1645, 1646), (21812, 21813)]


def rand_values(rnd):
    n1 = rnd.randint(1, 120)
    n2 = n1 + 1
    k = rnd.choice([0, 2, 3, 4, 5, 6, 7, 8, 9])      # Lo0 の第2オクテット(10.1 は幹線と衝突)
    p2 = rnd.choice(NONSTD)
    return {
        "n1": n1, "n2": n2,
        "srv1": f"10.99.{n1}.2", "srv2": f"10.99.{n2}.2",
        "rt_if1": f"10.99.{n1}.1", "rt_if2": f"10.99.{n2}.1",
        "lo": {"RT01": f"10.{k}.0.1", "RT02": f"10.{k}.0.2"},
        "grp": rnd.choice(GROUPS),
        "admin": rnd.choice(ADMINS), "admin_pw": f"Noc-{rnd.randint(1000, 9999)}",
        "viewer": rnd.choice(VIEWERS), "viewer_pw": f"Desk-{rnd.randint(1000, 9999)}",
        "emg": rnd.choice(EMERGENCY), "emg_pw": f"Emg-{rnd.randint(1000, 9999)}",
        "key1": f"Srv1-{rnd.randint(1000, 9999)}", "key2": f"Srv2-{rnd.randint(1000, 9999)}",
        "p2auth": p2[0], "p2acct": p2[1],
        "deadtime": 1,               # 応答不能サーバを外す時間(分)
        "max_delay": 5,              # 片系断時のログイン遅延の上限(秒)
    }


# --- ルータ初期構成(データプレーンのみ。AAA は一切入っていない) ----------------

def rt_cfg(node, v):
    lo = v["lo"][node]
    if node == "RT01":
        ifs = [("Ethernet0/0", v["rt_if1"], f"to SRV01 (RADIUS)"),
               ("Ethernet0/1", v["rt_if2"], f"to SRV02 (RADIUS)"),
               ("Ethernet0/2", f"{CORE}.1", "to RT02")]
        nets = [f"10.99.{v['n1']}.0 0.0.0.3", f"10.99.{v['n2']}.0 0.0.0.3",
                f"{CORE}.0 0.0.0.3"]
    else:
        ifs = [("Ethernet0/0", f"{CORE}.2", "to RT01")]
        nets = [f"{CORE}.0 0.0.0.3"]
    out = ["! ============================================================",
           f"! {node} — データプレーンは構築済み(変更不可)。AAA は未設定。",
           "! ============================================================",
           "interface Loopback0",
           f" ip address {lo} 255.255.255.255"]
    for ifname, ip, desc in ifs:
        out += [f"interface {ifname}",
                f" description === {desc} ===",
                f" ip address {ip} 255.255.255.252",
                " no shutdown"]
    out += ["!", "router ospf 1", f" router-id {lo}",
            f" network {lo} 0.0.0.0 area 0"]
    out += [f" network {n} area 0" for n in nets]
    out += ["!",
            "! --- 緊急用ローカル管理者(サーバ全断時の最後の砦) ---",
            f"username {v['emg']} privilege 15 secret {v['emg_pw']}",
            "!",
            "ip ssh version 2"]
    return "\n".join(out) + "\n"


# --- サーバ初期化(FreeRADIUS は完成品で渡す) ---------------------------------

def _clients_conf(v, key):
    return f"""# ★受理するのは各ルータの Loopback0 のみ。
#   機器側で送信元を Loopback0 に固定していない要求は「不明なクライアント」として
#   無言で破棄される(Reject は返らない= 機器からはタイムアウトに見える)。
client localhost {{
	ipaddr = 127.0.0.1
	secret = testing123
}}
client rt01-lo {{
	ipaddr = {v['lo']['RT01']}
	secret = {key}
}}
client rt02-lo {{
	ipaddr = {v['lo']['RT02']}
	secret = {key}
}}
"""


def _authorize(v):
    return f"""{v['admin']} Cleartext-Password := "{v['admin_pw']}"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"

{v['viewer']} Cleartext-Password := "{v['viewer_pw']}"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=1"

SUZUKI Cleartext-Password := "CCNP"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"
"""


def _netplan(self_ip, gw, others):
    routes = "".join(f"\n        - to: {net}\n          via: {gw}" for net in others)
    return f"""rm -f /etc/netplan/50-cloud-init.yaml
cat > /etc/netplan/60-ccnp.yaml <<'EOF'
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{{{{ mgmt_ip }}}}/{{{{ mgmt_prefixlen }}}}]
      routes:
        - to: default
          via: {{{{ mgmt_gw }}}}
      nameservers:
        addresses: {{{{ mgmt_dns | to_json }}}}
    ens3:
      addresses: [{self_ip}/30]
      routes:{routes}
EOF
chmod 600 /etc/netplan/60-ccnp.yaml
netplan apply
"""


def srv_init_sh(node, v):
    is1 = node == "SRV01"
    self_ip = v["srv1"] if is1 else v["srv2"]
    gw = v["rt_if1"] if is1 else v["rt_if2"]
    peer_net = f"10.99.{v['n2'] if is1 else v['n1']}.0/30"
    others = [f"{CORE}.0/30", peer_net,
              f"{v['lo']['RT01']}/32", f"{v['lo']['RT02']}/32"]
    key = v["key1"] if is1 else v["key2"]

    port_patch = "" if is1 else f"""
log "★非標準ポートへ変更 (auth {v['p2auth']} / acct {v['p2acct']})"
python3 - <<'PY'
import re
p = '/etc/freeradius/3.0/sites-enabled/default'
s = open(p).read()

def fix(m):
    blk = m.group(0)
    t = re.search(r'type\\s*=\\s*(auth|acct)', blk)
    if not t:
        return blk
    port = '{v['p2auth']}' if t.group(1) == 'auth' else '{v['p2acct']}'
    return re.sub(r'(?m)^(\\s*)port\\s*=\\s*0\\s*$', r'\\g<1>port = ' + port, blk)

open(p, 'w').write(re.sub(r'(?ms)^listen\\s*\\{{.*?^\\}}', fix, s))
PY
"""
    phase = _phase_sh(v) if is1 else ""
    phase_install = "" if is1 else ""
    if is1:
        phase_install = f"""
log "採点用の挙動フェーズスクリプトを設置(受験者は触らなくてよい)"
install -d -m 755 /opt/ccnp
cat > /opt/ccnp/aaa_phase.sh <<'PHASEEOF'
{phase}PHASEEOF
chmod 755 /opt/ccnp/aaa_phase.sh
"""
    return f"""#!/bin/bash
# {node} (FreeRADIUS{' 標準ポート' if is1 else ' ★非標準ポート'}) 初期化 — 生成: gen_aaa_build.py
# ★サーバ側は**完成品**で渡す。受験者の課題は機器側 AAA だけ。
set -e
export DEBIAN_FRONTEND=noninteractive
log() {{ echo "[$(date -Is)] $*"; }}

log "in-band NIC / 学習網への経路を netplan で永続化"
{_netplan(self_ip, gw, others)}
log "パッケージ導入 (freeradius / freeradius-utils{' / sshpass' if is1 else ''})"
for i in 1 2 3; do
  apt-get update -qq && \\
  apt-get install -y -qq freeradius freeradius-utils{' sshpass' if is1 else ''} && break
  sleep 10
done
{port_patch}
log "clients.conf — ★ルータの Loopback0 のみ許可・このサーバの鍵は {key}"
cat > /etc/freeradius/3.0/clients.conf <<'EOF'
{_clients_conf(v, key)}EOF

log "ユーザ台帳(2 台とも同一。切替が起きても権限で判別できないようにする)"
cat > /etc/freeradius/3.0/mods-config/files/authorize <<'EOF'
{_authorize(v)}EOF
{phase_install}
log "設定検査 → 起動"
freeradius -XC >/dev/null
systemctl enable -q freeradius || true
systemctl restart freeradius
systemctl is-active freeradius
log "DONE"
"""


def _phase_sh(v):
    """★3フェーズ挙動採点の実体(SRV01 に設置・採点の shell チェックから呼ばれる)。

    grade.yml は ios → shell の順にしか回せないので、破壊と観測をこの 1 本に閉じ込める。
    最後は trap で必ず両サーバを起動して戻す(採点は最大 10 回再試行される)。
    """
    return f"""#!/bin/bash
# GEN-AAAGRP 挙動採点(片系断/全断) — 採点系が呼ぶ。受験者が実行する必要はない。
# ★冪等・自己復旧: どこで失敗しても trap で両サーバを起動して終わる。
OUT=/run/ccnp-aaa-phase.out
PEER={v['srv2']}
RT={RT02_INBAND}
# ★ServerAlive を必ず付ける。IOL は **強制終了された SSH の VTY を解放しない**
#   (`clear line` は [OK] を返すのに残り、`clear tcp line` は「TCP が無い」と言い、
#   `exec-timeout` でも刈られない。VTY は 5 本固定で `line vty 5 15` は拒否される)。
#   → ssh を kill せず、**ssh 自身に切断させる**。これを怠ると採点 1 回で VTY を
#   使い切り、以後ルータへ SSH できなくなる(実測 2026-08-09)。
SSHO="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
      -o ConnectTimeout=20 -o LogLevel=ERROR -o NumberOfPasswordPrompts=1 \\
      -o ServerAliveInterval=5 -o ServerAliveCountMax=8"

rm -f "$OUT"                     # 途中で死んだら後続チェックも落ちるように先に消す

# ★ssh は必ず `timeout` で包む。ConnectTimeout は TCP 接続までしか効かず、
#   認証で固まると**無限に待つ**(実測: 1 本の ssh が 30 分ハングし採点全体が止まった)。
peer() {{ timeout 30 sshpass -p 'CCNP' ssh $SSHO SUZUKI@$PEER "$1" 2>&1; }}
restore() {{
  sudo -n systemctl start freeradius >/dev/null 2>&1
  peer 'sudo -n systemctl start freeradius' >/dev/null 2>&1
}}
trap restore EXIT

# $1=user $2=pass → "OK|NG <秒>"
login() {{
  local t0 t1 out
  t0=$(date +%s.%N)
  out=$(timeout 45 sshpass -p "$2" ssh $SSHO "$1"@$RT 'show privilege' 2>&1)
  t1=$(date +%s.%N)
  local d
  d=$(echo "$t1 $t0" | awk '{{printf "%.1f", $1-$2}}')
  if echo "$out" | grep -q 'privilege level is 15'; then echo "OK $d"; else echo "NG $d"; fi
}}

R=""
add() {{ R="$R$1"$'\\n'; }}

# ★前回の採点で優先サーバを DEAD 記録したまま次の試行が始まると、停止しても
#   最初から速く、切り離しの観測が壊れる(実測: 3 連続とも 0.3s・PRIMARY=NG)。
#   → **優先サーバが UP に戻るまで待ってから**測る。deadtime 分の待ちが入り得る。
wait_primary() {{
  local i out
  for i in $(seq 1 24); do
    out=$(timeout 25 sshpass -p 'CCNP' ssh $SSHO SUZUKI@$RT \\
          'show aaa servers | include host|State' 2>&1)
    if echo "$out" | grep -A1 'host {v['srv1']},' | grep -q 'current UP'; then
      return 0
    fi
    sleep 5
  done
  return 1
}}

restore; sleep 2
wait_primary && add "READY=OK" || add "READY=NG"

# --- 基線: RADIUS 利用者が入れるか ------------------------------------------
set -- $(login '{v['admin']}' '{v['admin_pw']}')
add "PHASE1=$1"

# --- フェーズ2: SRV01 停止(片系断) ------------------------------------------
sudo -n systemctl stop freeradius
set -- $(login '{v['admin']}' '{v['admin_pw']}'); s1=$1; d1=$2
set -- $(login '{v['admin']}' '{v['admin_pw']}'); s2=$1; d2=$2
set -- $(login '{v['admin']}' '{v['admin_pw']}'); s3=$1; d3=$2
add "PHASE2=$s1"
add "PHASE2_FIRST=$d1"
add "PHASE2_SECOND=$d2"
add "PHASE2_THIRD=$d3"
# 優先サーバが SRV01 でなければ 1 回目から速い= 要件2(SRV01 優先)の取り違え
add "PRIMARY=$(awk -v d=$d1 'BEGIN{{print (d>2)?"OK":"NG"}}')"
# 遅延要件: 1 回目が {v['max_delay']} 秒以内(ssh 自体の 1 秒を上乗せして判定)
add "DELAY=$(awk -v d=$d1 'BEGIN{{print (d<={v['max_delay']}+1)?"OK":"NG"}}')"
# ★応答不能サーバの切り離し: 実測(results-deadcrit.md)では deadtime だけでは
#   何も起きず毎回 6.3s。dead-criteria を入れると 6.4 → 3.3 → 0.3s と落ちる。
#   よって判定は **3 回目**で行う。
add "DEADTIME=$(awk -v a=$d1 -v c=$d3 'BEGIN{{print (c<=2 && c<a/2)?"OK":"NG"}}')"

# --- フェーズ3: SRV02 も停止(全断) ------------------------------------------
peer 'sudo -n systemctl stop freeradius' >/dev/null 2>&1
set -- $(login '{v['emg']}' '{v['emg_pw']}')
add "PHASE3_LOCAL=$1"
add "PHASE3_LOCAL_SEC=$2"
# ★「ローカルで入れた」だけでは AAA 未設定でも通ってしまう。**サーバを試した末に**
#   ローカルへ落ちたことを、待ち時間(最低でもタイムアウト 1 回分)で裏取りする。
add "PHASE3_VIA_FALLBACK=$(awk -v d=$2 'BEGIN{{print (d>1.5)?"OK":"NG"}}')"
set -- $(login '{v['admin']}' '{v['admin_pw']}')
# RADIUS 利用者は入れないのが正: 入れたら**ローカル台帳に写した**ということ
add "PHASE3_RADIUS_DENIED=$([ "$1" = NG ] && echo OK || echo NG)"

# --- 復旧 -------------------------------------------------------------------
restore; sleep 3
set -- $(login '{v['admin']}' '{v['admin_pw']}')
add "RECOVER=$1"

printf '%s' "$R" | tee "$OUT"
"""


# --- 生成 ---------------------------------------------------------------------

def build(repo, seed):
    rnd = random.Random(seed)
    pid = f"GEN-AAAGRP-{seed}"
    v = rand_values(rnd)
    g = v["grp"]

    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    for rt in RTS:
        with open(f"{pdir}/initial/{rt}.cfg.j2", "w", encoding="utf-8") as fp:
            fp.write(rt_cfg(rt, v))
    for s in SRVS:
        with open(f"{pdir}/initial/{s}.cfg.j2", "w", encoding="utf-8") as fp:
            fp.write("# server ノードは baseline_server.cfg.j2 が描画(連結対策の空ファイル)\n")
        with open(f"{pdir}/initial/{s}.sh.j2", "w", encoding="utf-8") as fp:
            fp.write(srv_init_sh(s, v))

    pmeta = {
        "id": pid,
        "title": f"冗長 AAA(RADIUS サーバグループ)構築 (seed={seed})",
        "exam": "ENCOR",
        "topics": ["aaa", "radius", "security", "server", "generated"],
        "difficulty": 4,
        "topology": "generated",
        "target_nodes": RTS + SRVS,
        "points": 100,
        "access": "ssh",
        "image_family": "iol",
        "node_image_families": {s: "ubuntu" for s in SRVS},
        "lab": {"links": [
            {"a": "SRV01", "a_if": 1, "b": "RT01", "b_if": 0},
            {"a": "SRV02", "a_if": 1, "b": "RT01", "b_if": 1},
            {"a": "RT01", "a_if": 2, "b": "RT02", "b_if": 0},
        ]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_aaa_build.py) seed={seed}\n")
        yaml.safe_dump(pmeta, fp, allow_unicode=True, sort_keys=False, width=4096)

    phase_out = "cat /run/ccnp-aaa-phase.out"
    checks = []
    for rt in RTS:
        checks += [
            {"name": f"{rt}: test aaa がサーバグループ {g} で成功", "node": rt,
             "command": f"test aaa group {g} {v['admin']} {v['admin_pw']} legacy",
             "raw": [{"contains": "successfully authenticated"}], "points": 10},
            {"name": f"{rt}: 2 台のサーバが実効(標準/非標準ポート)", "node": rt,
             "command": "show aaa servers",
             "raw": [{"contains": v["srv1"]}, {"contains": v["srv2"]},
                     {"contains": "auth-port 1812"},
                     {"contains": f"auth-port {v['p2auth']}"}], "points": 8},
            {"name": f"{rt}: 認証・認可とも グループ優先 + ローカル予備", "node": rt,
             "command": "show running-config | include aaa auth",
             "raw": [{"regex": rf"(?m)^aaa authentication login default group {g} local\s*$"},
                     {"regex": rf"(?m)^aaa authorization exec default group {g} local\s*$"}],
             "points": 8},
        ]
    # ★診断(0点)= BL-001 初出題で露見した実機の罠。`aaa group server radius` の中に
    #   書いた `timeout` / `retransmit` は**受理されるが名前付きサーバには効かない**
    #   (値は per-server → global の順で解決され、グループの記述はその探索に入らない)。
    #   結果、片系断でタイムアウトも再送も起きず、ログインが数十分返らなくなる。
    #   ★ユーザ判断(2026-08-10)で**罠は残す**方針。ただし落ちた理由が分かるよう
    #   名前付きで検出する。減点は挙動①②③が既に行うのでここは 0 点。
    for rt in RTS:
        checks.append(
            {"name": f"{rt}: 診断 — 応答待ちのタイマ(timeout/retransmit)の置き場所",
             "node": rt,
             "command": "show running-config | section aaa group server radius",
             "raw": [{"contains": f"aaa group server radius {g}"},
                     {"not_regex": r"(?m)^\s+timeout\s+\d+"},
                     {"not_regex": r"(?m)^\s+retransmit\s+\d+"}],
             "points": 0})
    checks += [
        # ★2 台**まとめて**見る。前の試行の破壊フェーズで SRV01 が一時的に dead 記録
        #   された直後だと、課金は SRV02 側へ飛ぶ。片方だけ見ると再試行で揺れる。
        #   ディレクトリ名は NAS-IP-Address = Loopback0 なので、送信元要件の裏付けにもなる。
        {"name": "課金記録が両ルータの Loopback0 名で残っている(いずれかのサーバに)",
         "node": "SRV01", "exec": "shell",
         "command": ("sudo -n ls /var/log/freeradius/radacct/ 2>&1; "
                     f"timeout 30 sshpass -p 'CCNP' ssh -o StrictHostKeyChecking=no "
                     f"-o UserKnownHostsFile=/dev/null -o ConnectTimeout=20 "
                     f"-o LogLevel=ERROR SUZUKI@{v['srv2']} "
                     f"'sudo -n ls /var/log/freeradius/radacct/' 2>&1"),
         "raw": [{"contains": v["lo"]["RT01"]}, {"contains": v["lo"]["RT02"]}],
         "points": 10},
        # --- ここから挙動採点。最初の1本がサーバを止めて観測し、必ず復旧させる ---
        {"name": "挙動①: 片系断(SRV01 停止)でも RADIUS 認証が継続する",
         "node": "SRV01", "exec": "shell",
         # ★採点側にも上限を置く(スクリプト内の timeout が漏れても採点は止まらない)
         "command": "timeout 420 sudo -n /opt/ccnp/aaa_phase.sh",
         "raw": [{"regex": r"(?m)^PHASE1=OK$"}, {"regex": r"(?m)^PHASE2=OK$"}],
         "points": 10},
        {"name": f"挙動②: 片系断のログイン遅延が {v['max_delay']} 秒以内",
         "node": "SRV01", "exec": "shell", "command": phase_out,
         # ★ログインが失敗していれば当然速い。PHASE2=OK と抱き合わせないと
         #   未設定の盤面で無条件に通ってしまう(基線採点で実際に 6 点入った)。
         "raw": [{"regex": r"(?m)^PHASE2=OK$"},
                 {"regex": r"(?m)^DELAY=OK$"}], "points": 6},
        {"name": "挙動③: 応答しない優先サーバへの問い合わせが停止し、待ちが消える",
         "node": "SRV01", "exec": "shell", "command": phase_out,
         # ★ログイン自体が失敗していると d1 が大きく d3 が 0 になり、**失敗の組み合わせで
         #   DEADTIME=OK が立つ**(実測で偽陽性を確認)。PHASE2=OK と抱き合わせる。
         "raw": [{"regex": r"(?m)^PHASE2=OK$"},
                 {"regex": r"(?m)^PRIMARY=OK$"},
                 {"regex": r"(?m)^DEADTIME=OK$"}], "points": 6},
        {"name": "挙動④: 全断でサーバを試した末にローカル管理者へフォールバックする",
         "node": "SRV01", "exec": "shell", "command": phase_out,
         "raw": [{"regex": r"(?m)^PHASE3_LOCAL=OK$"},
                 {"regex": r"(?m)^PHASE3_VIA_FALLBACK=OK$"}], "points": 10},
        {"name": "挙動⑤: 全断のとき RADIUS 利用者は入れない(ローカルへ写していない)",
         "node": "SRV01", "exec": "shell", "command": phase_out,
         "raw": [{"regex": r"(?m)^PHASE3_RADIUS_DENIED=OK$"},
                 {"regex": r"(?m)^RECOVER=OK$"}], "points": 6},
    ]
    assert sum(c["points"] for c in checks) == 100, sum(c["points"] for c in checks)
    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_aaa_build.py) seed={seed}\n")
        yaml.safe_dump(grading, fp, allow_unicode=True, sort_keys=False, width=4096)

    # --- 模範解答 -------------------------------------------------------------
    fixes = []
    for rt in RTS:
        fixes += [
            {"node": rt, "lines": ["aaa new-model"]},
            {"node": rt, "parents": ["radius server RAD1"],
             "lines": [f"address ipv4 {v['srv1']} auth-port 1812 acct-port 1813",
                       f"key {v['key1']}"]},
            {"node": rt, "parents": ["radius server RAD2"],
             "lines": [f"address ipv4 {v['srv2']} auth-port {v['p2auth']} "
                       f"acct-port {v['p2acct']}",
                       f"key {v['key2']}"]},
            {"node": rt, "parents": [f"aaa group server radius {g}"],
             "lines": ["server name RAD1", "server name RAD2",
                       f"deadtime {v['deadtime']}"]},
            {"node": rt, "lines": [
                "ip radius source-interface Loopback0",
                "radius-server timeout 2",
                "radius-server retransmit 1",
                "radius-server dead-criteria time 5 tries 1",
                f"aaa authentication login default group {g} local",
                f"aaa authorization exec default group {g} local",
                f"aaa accounting exec default start-stop group {g}"]},
        ]
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fp:
        json.dump({"fixes": fixes}, fp, ensure_ascii=False, indent=2)

    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as fp:
        fp.write(f"""# {pid} 模範解答（採点者用）

投入は `solution/fix.json`（両ルータ同一）。要点だけ:

```
aaa new-model
radius server RAD1
 address ipv4 {v['srv1']} auth-port 1812 acct-port 1813
 key {v['key1']}
radius server RAD2
 address ipv4 {v['srv2']} auth-port {v['p2auth']} acct-port {v['p2acct']}
 key {v['key2']}
aaa group server radius {g}
 server name RAD1
 server name RAD2
 deadtime {v['deadtime']}
ip radius source-interface Loopback0
radius-server timeout 2
radius-server retransmit 1
radius-server dead-criteria time 5 tries 1
aaa authentication login default group {g} local
aaa authorization exec default group {g} local
aaa accounting exec default start-stop group {g}
```

## レビュー観点

- **送信元**: サーバの `clients.conf` は各ルータの **Loopback0 のみ**許可。
  `ip radius source-interface Loopback0` が無いと RT01 は直結 IF、RT02 は
  出口 IF の IP で送るため**不明クライアントとして無言破棄**され、
  Reject ではなく**タイムアウト**になる。「拒否されている」と読み違えやすい所。
- **サーバ毎の鍵**: SRV01={v['key1']} / SRV02={v['key2']}。`radius server` ブロック内の
  `key` で個別に持つ。旧来の `radius-server host` 形は非推奨。
- **遅延**: 片系断のログイン遅延は `timeout × (retransmit+1)` で決まる
  (実測= timeout 3・retransmit 1 で 6.3 秒)。要件の {v['max_delay']} 秒以内には
  `timeout 2 / retransmit 1`(4 秒)などが要る。
- ★**`deadtime` だけでは何も起きない**(実測 poc/aaa/results-deadcrit.md)。
  サーバが「応答不能」と判定されて初めて `deadtime` の出番になり、その判定条件は
  `radius-server dead-criteria` が決める。既定のままだと片系断で連続ログインしても
  **毎回 6.3 秒**待たされ続ける(DEAD 化しない)。`dead-criteria time 5 tries 1` を
  入れると 6.4 → 3.3 → **0.3 秒**と落ちる。挙動③はこの 3 回目で見ている。
  「書いたのに効かない」典型で、本問の主眼のひとつ。
- **ローカル予備の意味**: `group {g} local` の `local` が使われるのは
  **サーバ無応答のときだけ**。サーバが Reject を返した場合はローカルへ落ちない。
  だから RADIUS 台帳の SUZUKI 登録が必須(生成器が投入済み)。
- **やってはいけない解**: RADIUS 利用者を `username` でローカルにも作ると挙動④は
  通るが**挙動⑤で落ちる**(全断時に RADIUS 利用者が入れてしまうため)。
""")

    # --- task.md --------------------------------------------------------------
    task = f"""# 問題 {pid} : 冗長 AAA（RADIUS サーバグループ）構築（難易度4）

## シナリオ

管理者のログイン認証を、**2 台の RADIUS サーバ**による冗長構成へ移行します。
サーバ側（SRV01 / SRV02）は情報システム部門が構築済みで、**変更できません**。
あなたの作業は **RT01・RT02 の機器側 AAA** です。

```
 SRV01 ──┐
         RT01 ────── RT02
 SRV02 ──┘   {CORE}.0/30
```

## 構成（初期状態で投入済み・変更不可）

- 各 IF の IP・OSPF は設定済み（RT02 からも両サーバへ到達可能）
- 緊急用のローカル管理者 `{v['emg']}` / `{v['emg_pw']}`（priv 15）が両機に登録済み
- 現在は AAA 未設定（ローカル認証。SUZUKI / CCNP）

| ルータ | Loopback0 | サーバ方向 |
|---|---|---|
| RT01 | {v['lo']['RT01']} | E0/0 = {v['rt_if1']} / E0/1 = {v['rt_if2']} |
| RT02 | {v['lo']['RT02']} | E0/0 = {CORE}.2（RT01 経由） |

## 認証サーバ仕様書（情報システム部門より）

| 項目 | SRV01 | SRV02 |
|---|---|---|
| アドレス | {v['srv1']} | {v['srv2']} |
| 待受ポート（認証 / 課金） | 1812 / 1813 | **{v['p2auth']} / {v['p2acct']}** |
| 共有鍵 | `{v['key1']}` | `{v['key2']}` |
| **受理する送信元** | 各ルータの **Loopback0** のみ | 同左 |
| 台帳 | 下表の 3 名 | 同左 |

### 台帳(両サーバに登録済み)

| 利用者 | パスワード | 権限レベル |
|---|---|---|
| {v['admin']} | `{v['admin_pw']}` | 15 |
| {v['viewer']} | `{v['viewer_pw']}` | 1 |
| SUZUKI | `CCNP` | 15 |

※ 権限レベルはサーバが応答属性で通知します（ルータ側で `username` を作る必要はありません）。

## 要件（RT01・RT02 の両方）

1. 2 台のサーバを個別に定義し、**サーバごとに異なる共有鍵**と、仕様書どおりの
   待受ポートを設定すること。
2. 2 台をひとつのサーバグループ **`{g}`** にまとめ、認証はこのグループを用いること。
   問い合わせは **SRV01 を優先**し、応答が無い場合に SRV02 を用いること。
3. 利用者 `{v['admin']}` が両ルータへログインでき、**ログイン直後に権限レベル 15**
   であること。`{v['viewer']}` は権限レベル 1 であること。
4. **サーバが応答しない場合に限り**、ローカルの利用者データベースで認証できること。
5. 片系のサーバが停止しても認証が継続すること。そのときの**ログインの遅延は
   {v['max_delay']} 秒以内**であること。
6. サーバが応答しないことを**検出したうえで**、そのサーバへの問い合わせを
   **以後 {v['deadtime']} 分間停止**すること。停止できていれば、続けてログインした
   ときの待ち時間が消える。
7. exec セッションの開始と終了を、サーバグループ **`{g}`** へ記録すること。

## 禁止事項

- サーバ（SRV01 / SRV02）の設定変更。**サーバ側は完成しています。**
- 台帳の利用者（{v['admin']} / {v['viewer']} / SUZUKI）を、ルータのローカル
  利用者データベースに登録すること。**採点で検出されます。**
- データプレーン（IF / OSPF）の変更。

## 注意（締め出し）

- `aaa new-model` を入れた時点で、**VTY もコンソールも**既定の方式リストに従います。
  方式リストを作る前に切断しないこと。
- 方式リストの `local` が使われるのは **サーバが無応答のとき**だけです。サーバが
  生きていて**拒否**を返した場合、ローカルへは切り替わりません。
- 復旧はコンソール（CML）から可能です。

## アクセス・採点

SSH `SUZUKI / CCNP`。採点は片系断・全断を実際に起こして挙動を確認します
（**採点が終わるとサーバは自動で復旧します**。採点中は 1 分ほどログインが不安定に
なります）。

```
ansible-playbook playbooks/grade.yml -e problem={pid} \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as fp:
        fp.write(task)

    print(f"generated {pid}")
    print(f"  group={g} admin={v['admin']}/{v['admin_pw']} viewer={v['viewer']}/{v['viewer_pw']}")
    print(f"  emg={v['emg']}/{v['emg_pw']} keys={v['key1']}/{v['key2']} "
          f"srv2-ports={v['p2auth']}/{v['p2acct']}")
    print(f"  srv1={v['srv1']} srv2={v['srv2']} lo={v['lo']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args()
    build(a.repo, a.seed)


if __name__ == "__main__":
    main()
