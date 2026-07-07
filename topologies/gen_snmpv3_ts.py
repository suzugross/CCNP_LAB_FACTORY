#!/usr/bin/env python3
"""SNMPv3×Zabbix監視 トラブルシュート生成器（監視ダッシュボード起点TS）。

正準トポロジ(3RT+監視サーバ):
  ZBX01 --- RT01 --- RT02 --- RT03
  - ZBX01(ubuntu): cloud-init が Zabbix 7.0 を自動構築（initial/ZBX01.sh.j2）。
    ens2=MGMT(WebUI/採点), ens3=インバンド 10.99.0.2/30。
  - 監視はインバンド経由で各 RT の Loopback0 を SNMPv3(authPriv SHA/AES) ポーリング
    → 経路障害も「監視断」としてダッシュボードに現れる。
  - IGP は OSPF area0（全 RT 健全構成が基準、故障はカタログから注入）。

設計方針（拡張性）: 故障は「ダッシュボード上のシグネチャ」で分類する。
  SNMP_ONLY_DOWN … ping 緑 / SNMP 赤 → SNMPv3 設定系（user/認証/priv/view/ACL）
  HOST_DOWN      … ping も赤       → 到達性系（OSPF 広告漏れ 等）
  新しい故障クラスは FAULTS に {inject,fix} を足すだけで追加できる。
  監視ホスト登録は problem.yml の monitoring セクション（zbx_setup.py が解釈）。

採点（grade.yml の exec:shell 拡張を使用）:
  - ZBX01 から snmpget / ping（監視サーバ視点の実測）
  - ZBX01 上の zbx_check.py で Zabbix API の availability（ダッシュボード復旧）
  - 機器側 show snmp user のサニティ
  ※Zabbix の availability 反映はポーリング周期の関係で数十秒〜数分遅れる。
    grade.yml は -e max_attempts=20 程度で回すこと（task.md に記載）。

出力: problems/GEN-SNMPTS-<seed>/
  {problem.yml, initial/{RT*.cfg.j2, ZBX01.cfg.j2(空), ZBX01.sh.j2},
   grading.yml, task.md, solution/{fault.json, fix.json}}
使い方: gen_snmpv3_ts.py --repo . --seed <int> [--count 2] [--faults a,b,...]

--mode build（2026-07-04 Lv1）= 監視一貫構築ラボ GEN-ZBXBUILD-<seed>:
  同一トポロジで初期は「IP/OSPF のみ・SNMP 無し・Zabbix ホスト未登録」。
  受験者が仕様書どおりにルータの SNMPv3 と Zabbix 側の監視登録を一から構築する。
  problem.yml に monitoring を出さない(=lab_up の自動登録が走らない)のが肝。
  採点: snmpget(機器側) / zbx_check hostinfo(登録属性) / fresh(データ鮮度=通し) /
        show snmp user・ACL(機器サニティ)。
  模範解答: solution/fix.json(機器側, fix_generated.yml 互換) と
            solution/monitoring.yml(Zabbix側, zbx_setup.py --monitoring-yml で投入)。
  Lv2 への布石: 採点は極力「効果ベース」。仕様の書きぶり依存は ACL 番号チェックのみ。

--mode build --level 2（2026-07-05 Lv2）= 要件型 GEN-ZBXBUILD2-<seed>:
  仕様書を渡さず「運用要件」のみ提示（view/group 名・ACL 実装は自由）。
  ACL 採点は効果ベース: ポーラ網を /29 化し ZBX01 に検証端末アドレス .3 を追加、
  「.2 から取得成功かつ .3 から拒否(Timeout)」を snmpget --clientaddr で実測する。
"""
import argparse
import json
import os
import random

import yaml

RTS = ["RT01", "RT02", "RT03"]
ZBX = "ZBX01"
POLLER_NET = "10.99.0"          # ZBX01-RT01 インバンド /30（.1=RT01, .2=ZBX01）
V3_USER, V3_GROUP, V3_VIEW = "MONUSER", "MONGRP", "MONVIEW"
V3_AUTH_PASS, V3_PRIV_PASS = "CCNP-Auth-2026", "CCNP-Priv-2026"
ZBX_WEB_PORT = 8080

# ---- 故障カタログ ---------------------------------------------------------
# inject(node,ctx) -> 初期configへ加える差分（healthyからの置換/追加）
# fix(node,ctx)    -> fix_generated.yml 互換の fix エントリ list
# signature        -> ダッシュボード上の見え方（task/解説用・採点には使わない）

def user_line():
    return (f"snmp-server user {V3_USER} {V3_GROUP} v3 "
            f"auth sha {V3_AUTH_PASS} priv aes 128 {V3_PRIV_PASS}")


FAULTS = {
    # --- SNMP_ONLY_DOWN 系（ping 緑 / SNMP 赤） ---
    "user_missing": {
        "difficulty": 3, "signature": "SNMP_ONLY_DOWN",
        "desc": "SNMPv3 ユーザ未設定（show snmp user が空）",
        "snmp_user": None,
        "fixes": lambda n, c: [{"node": n, "lines": [user_line()]}],
    },
    "user_no_priv": {
        "difficulty": 4, "signature": "SNMP_ONLY_DOWN",
        "desc": "ユーザが auth のみ（priv 鍵なし）→ authPriv 要求が unsupportedSecurityLevel",
        "snmp_user": f"snmp-server user {V3_USER} {V3_GROUP} v3 auth sha {V3_AUTH_PASS}",
        "fixes": lambda n, c: [{"node": n, "lines": [
            f"no snmp-server user {V3_USER} {V3_GROUP} v3", user_line()]}],
    },
    "wrong_auth_proto": {
        "difficulty": 4, "signature": "SNMP_ONLY_DOWN",
        "desc": "認証プロトコル不一致（md5 で作成、NOC 標準は sha）→ 認証失敗",
        "snmp_user": (f"snmp-server user {V3_USER} {V3_GROUP} v3 "
                      f"auth md5 {V3_AUTH_PASS} priv aes 128 {V3_PRIV_PASS}"),
        "fixes": lambda n, c: [{"node": n, "lines": [
            f"no snmp-server user {V3_USER} {V3_GROUP} v3", user_line()]}],
    },
    "view_excluded": {
        "difficulty": 4, "signature": "SNMP_ONLY_DOWN",
        "desc": "view で mib-2 が excluded → 認証は通るが authorizationError",
        "extra_global": [f"snmp-server view {V3_VIEW} mib-2 excluded"],
        "fixes": lambda n, c: [{"node": n, "lines": [
            f"no snmp-server view {V3_VIEW} mib-2 excluded"]}],
    },
    "group_acl": {
        "difficulty": 4, "signature": "SNMP_ONLY_DOWN",
        "desc": "group の ACL がポーラ送信元を deny → SNMP タイムアウト",
        "group_acl": 99,
        "extra_global": ["access-list 99 deny   10.99.0.2",
                         "access-list 99 permit any"],
        "fixes": lambda n, c: [{"node": n, "lines": [
            "no access-list 99", "access-list 99 permit any"]}],
    },
    "if_acl": {
        "difficulty": 4, "signature": "SNMP_ONLY_DOWN",
        "desc": "受信 IF の ACL が UDP/161 を deny（ping は permit）",
        "if_acl": True,
        "fixes": lambda n, c: [
            {"node": n, "parents": [f"interface {c['ingress_if'][n]}"],
             "lines": ["no ip access-group MONBLOCK in"]},
            {"node": n, "lines": ["no ip access-list extended MONBLOCK"]},
        ],
    },
    # --- HOST_DOWN 系（ping も赤） ---
    "ospf_missing_net": {
        "difficulty": 3, "signature": "HOST_DOWN",
        "desc": "Loopback0 が OSPF 未広告 → ポーラから到達不能（ping/SNMP 両断）",
        "drop_lo_network": True,
        "victims": ["RT02", "RT03"],   # RT01はポーラ直結+静的経路で無効化するため除外
        "fixes": lambda n, c: [{"node": n, "parents": ["router ospf 1"],
                                "lines": [f"network {c['lo'][n]} 0.0.0.0 area 0"]}],
    },
    # --- 監視入口の拡張(2026-07-04): SNMP以外の故障類型もダッシュボード起点で出題 ---
    "if_down": {
        "difficulty": 3, "signature": "HOST_DOWN",
        "desc": "上流IF shutdown → 当該機と配下がまとめて監視断（複数ホスト赤＝上流障害の読み解き）",
        "if_shutdown": True,
        "fixes": lambda n, c: [{"node": n,
                                "parents": [f"interface {c['ingress_if'][n]}"],
                                "lines": ["no shutdown"]}],
    },
    # --- 難問拡張(2026-07-05): show の見た目では割れにくい高難度系 ---
    "wrong_auth_pass": {
        "difficulty": 5, "signature": "SNMP_ONLY_DOWN",
        "desc": ("認証パスワード不一致（プロトコルは正しく SHA/AES128）"
                 "→ show snmp user は完全に正常に見える（鍵は表示されない）"),
        "snmp_user": (f"snmp-server user {V3_USER} {V3_GROUP} v3 "
                      f"auth sha CCNP-Auth-2025 priv aes 128 {V3_PRIV_PASS}"),
        "fixes": lambda n, c: [{"node": n, "lines": [
            f"no snmp-server user {V3_USER} {V3_GROUP} v3", user_line()]}],
    },
    "group_wrong_view": {
        "difficulty": 5, "signature": "SNMP_ONLY_DOWN",
        "desc": ("group の read view 名がタイポ（MONVEIW・未定義 view 参照）"
                 "→ 認証は通るが GET が全て失敗。show snmp group で readview を見ると割れる"),
        "group_view": "MONVEIW",
        "fixes": lambda n, c: [{"node": n, "lines": [
            f"snmp-server group {V3_GROUP} v3 priv read {V3_VIEW}"]}],
    },
    "ospf_passive_if": {
        "difficulty": 5, "signature": "HOST_DOWN",
        "desc": ("ポーラ向き IF が OSPF passive-interface → IF は up/up・直結 ping 可なのに"
                 "隣接が張れず当該機と配下が監視断（show ip ospf neighbor で割れる）"),
        "ospf_passive": True,
        "victims": ["RT02", "RT03"],   # RT01のポーラ向きIFは隣接なし(ZBX直結)で無効のため除外
        "fixes": lambda n, c: [{"node": n, "parents": ["router ospf 1"],
                                "lines": [f"no passive-interface {c['ingress_if'][n]}"]}],
    },
    "acl_transit_block": {
        "difficulty": 4, "signature": "HOST_DOWN",
        "desc": "受信IF ACL が自Lo宛を deny（OSPF/転送は通す）→ この機だけ赤・配下は緑",
        "acl_all": True,
        "fixes": lambda n, c: [
            {"node": n, "parents": [f"interface {c['ingress_if'][n]}"],
             "lines": ["no ip access-group MONBLOCK-ALL in"]},
            {"node": n, "lines": ["no ip access-list extended MONBLOCK-ALL"]},
        ],
    },
}

DASH = {"SNMP_ONLY_DOWN": "ping=緑 / SNMP=赤", "HOST_DOWN": "ping=赤 / SNMP=赤"}


# ---- 値の採番 --------------------------------------------------------------

def rand_values(rnd):
    """Loopback(k.k.k.k) をランダム化。リンクは規約どおり 10.1.<a><b>.0/30。"""
    used, lo = set(), {}
    for r in RTS:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k)
                lo[r] = f"{k}.{k}.{k}.{k}"
                break
    return lo


# ---- initial config --------------------------------------------------------

def rt_config(node, ctx, fault, include_snmp=True):
    """RT の initial（healthy を基準に fault を注入）。
    include_snmp=False（build モード）は SNMP 節を丸ごと出さない＝受験者が構築する。"""
    lo = ctx["lo"][node]
    f = FAULTS[fault] if fault else {}
    lines = ["! --- data plane ---",
             "interface Loopback0",
             f" ip address {lo} 255.255.255.255"]
    for ifname, ip, mask, desc in ctx["ifs"][node]:
        # if_down 故障: ポーラ向き ingress IF を admin-down で投入
        down = f.get("if_shutdown") and ifname == ctx["ingress_if"][node]
        lines += [f"interface {ifname}",
                  f" description === {desc} ===",
                  f" ip address {ip} {mask}",
                  " shutdown" if down else " no shutdown"]
    # IF ACL 故障: ポーラ側 ingress IF に UDP/161 deny を掛ける（ping は通す）
    if f.get("if_acl"):
        lines += ["ip access-list extended MONBLOCK",
                  " deny udp any any eq snmp",
                  " permit ip any any",
                  f"interface {ctx['ingress_if'][node]}",
                  " ip access-group MONBLOCK in"]
    # 全遮断 ACL 故障: 自 Lo 宛だけ deny（OSPF/転送は許可）→ 単一ホスト HOST_DOWN
    if f.get("acl_all"):
        lines += ["ip access-list extended MONBLOCK-ALL",
                  " permit ospf any any",
                  f" deny ip any host {lo}",
                  " permit ip any any",
                  f"interface {ctx['ingress_if'][node]}",
                  " ip access-group MONBLOCK-ALL in"]
    # OSPF（healthy: 全 IF + Lo を area0 広告）
    lines += ["router ospf 1", f" router-id {lo}"]
    if not f.get("drop_lo_network"):
        lines.append(f" network {lo} 0.0.0.0 area 0")
    for _, ip, mask, _ in ctx["ifs"][node]:
        seg = ip.rsplit(".", 1)[0] + ".0"
        wc = ".".join(str(255 - int(o)) for o in mask.split("."))
        lines.append(f" network {seg} {wc} area 0")
    # passive-interface 故障: ポーラ向き IF の hello 停止（IF は up/up のまま隣接断）
    if f.get("ospf_passive"):
        lines.append(f" passive-interface {ctx['ingress_if'][node]}")
    # SNMPv3（healthy: view/group/user。fault により差し替え）
    if include_snmp:
        acl = f" access {f['group_acl']}" if f.get("group_acl") else ""
        gview = f.get("group_view", V3_VIEW)   # group_wrong_view 故障: 未定義 view 参照
        lines += ["! --- SNMPv3 (NOC 監視標準) ---",
                  f"snmp-server view {V3_VIEW} iso included",
                  f"snmp-server group {V3_GROUP} v3 priv read {gview}{acl}",
                  "snmp-server location CCNP-LAB"]
        lines += f.get("extra_global", [])
        if "snmp_user" in f:            # fault が user を差し替え/削除
            if f["snmp_user"]:
                lines.append(f["snmp_user"])
        else:
            lines.append(user_line())
    return "\n".join(lines) + "\n"


def zbx_init_sh(ctx):
    """ZBX01 の構築スクリプト（cloud-init が /opt/ccnp/init.sh として実行）。
    PoC(poc/zabbix-monitoring) で検証済みの手順:
      - スキーマ投入は zabbix ロールで（postgres だと所有者不一致で起動不能）
      - php8.3-pgsql 必須 / zabbix.conf.php 直接配置でウィザードスキップ
    """
    # 監視対象は ctx["lo"] 駆動（他生成器から流用可能: 例 gen_bgp_complex_ts --monitoring）
    routes = "\n".join(
        f"ip route add {ctx['lo'][r]}/32 via {POLLER_NET}.1 || true"
        for r in sorted(ctx["lo"]))
    return f"""#!/bin/bash
# Zabbix 7.0 自動構築（生成: gen_snmpv3_ts.py / 手順は PoC 検証済み）
set -e
export DEBIAN_FRONTEND=noninteractive
log() {{ echo "[$(date -Is)] $*"; }}

log "in-band NIC / 監視対象への経路"
ip addr add {POLLER_NET}.2/29 dev ens3 || true
# .3 = NOC 検証端末アドレス（build Lv2 の効果ベースACL採点: .3 からの SNMP は拒否されること）
ip addr add {POLLER_NET}.3/29 dev ens3 || true
ip link set ens3 up
{routes}

log "Zabbix リポジトリ・パッケージ"
wget -q https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_7.0+ubuntu24.04_all.deb -O /tmp/zbx.deb
dpkg -i /tmp/zbx.deb >/dev/null
apt-get update -qq
apt-get install -y -qq zabbix-server-pgsql zabbix-frontend-php php8.3-pgsql \\
  zabbix-nginx-conf zabbix-sql-scripts zabbix-agent2 postgresql >/dev/null

log "DB 作成・スキーマ投入（zabbix ロールで）"
sudo -u postgres psql -qc "CREATE USER zabbix WITH PASSWORD 'zabbix';" || true
sudo -u postgres createdb -O zabbix zabbix || true
zcat /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz | sudo -u zabbix psql -q zabbix >/dev/null

log "設定・起動"
sed -i 's/^# DBPassword=.*/DBPassword=zabbix/' /etc/zabbix/zabbix_server.conf
sed -i 's/^#\\s*listen\\s\\+8080;/        listen {ZBX_WEB_PORT};/; s/^#\\s*server_name\\s\\+example.com;/        server_name _;/' /etc/zabbix/nginx.conf
cat > /etc/zabbix/web/zabbix.conf.php <<'EOF'
<?php
$DB["TYPE"]      = "POSTGRESQL";
$DB["SERVER"]    = "localhost";
$DB["PORT"]      = "0";
$DB["DATABASE"]  = "zabbix";
$DB["USER"]      = "zabbix";
$DB["PASSWORD"]  = "zabbix";
$DB["SCHEMA"]    = "";
$DB["ENCRYPTION"] = false;
$DB["DOUBLE_IEEE754"] = true;
$ZBX_SERVER_NAME = "CCNP-LAB-ZBX";
$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;
EOF
chown www-data:www-data /etc/zabbix/web/zabbix.conf.php
systemctl restart zabbix-server zabbix-agent2 nginx php8.3-fpm
systemctl enable -q zabbix-server zabbix-agent2 nginx php8.3-fpm

log "採点/確認ヘルパー zbx_check.py"
cat > /opt/ccnp/zbx_check.py <<'EOF'
#!/usr/bin/env python3
# usage: zbx_check.py availability <HOST> | problems | hostinfo <HOST> | fresh <HOST> [限度秒]
import json, sys, time, urllib.request
URL = "http://127.0.0.1:{ZBX_WEB_PORT}/api_jsonrpc.php"
_i = [0]
def rpc(m, p, t=None):
    _i[0] += 1
    r = urllib.request.Request(URL, json.dumps(
        {{"jsonrpc": "2.0", "method": m, "params": p, "id": _i[0]}}).encode(),
        {{"Content-Type": "application/json-rpc"}})
    if t:
        r.add_header("Authorization", "Bearer " + t)
    d = json.load(urllib.request.urlopen(r, timeout=20))
    if "error" in d:
        sys.exit("API error: " + str(d["error"]))
    return d["result"]
t = rpc("user.login", {{"username": "Admin", "password": "zabbix"}})
cmd = sys.argv[1]
if cmd == "availability":
    hs = rpc("host.get", {{"filter": {{"host": [sys.argv[2]]}},
                           "selectInterfaces": ["available", "error"]}}, t)
    if not hs:
        sys.exit("HOST_NOT_FOUND")
    i = hs[0]["interfaces"][0]
    print(f"HOST={{sys.argv[2]}} SNMP_AVAILABLE={{i['available']}} ERROR={{i['error']!r}}")
elif cmd == "problems":
    for p in rpc("problem.get", {{"output": ["name", "severity"]}}, t):
        print("PROBLEM:", p["name"])
    print("(end)")
elif cmd == "hostinfo":
    # 監視ホストの登録内容を 1 行に整形（採点は raw regex で属性ごとに判定）
    hs = rpc("host.get", {{"filter": {{"host": [sys.argv[2]]}},
                           "selectParentTemplates": ["host"],
                           "selectHostGroups": ["name"],
                           "selectInterfaces": ["ip", "port", "type", "details"]}}, t)
    if not hs:
        sys.exit("HOST_NOT_FOUND")
    h = hs[0]
    SEC = {{"0": "noAuthNoPriv", "1": "authNoPriv", "2": "authPriv"}}
    AUTH = {{"0": "MD5", "1": "SHA", "2": "SHA224", "3": "SHA256", "4": "SHA384", "5": "SHA512"}}
    PRIV = {{"0": "DES", "1": "AES128", "2": "AES192", "3": "AES256", "4": "AES192C", "5": "AES256C"}}
    for i in h["interfaces"]:
        d = i.get("details") or {{}}
        if isinstance(d, list):
            d = {{}}
        print("HOST=%s TYPE=%s IF=%s:%s GROUP=%s TEMPLATE=%s V3USER=%s SECLEVEL=%s AUTH=%s PRIV=%s" % (
            h["host"], i["type"], i["ip"], i["port"],
            ",".join(g["name"] for g in h.get("hostgroups", [])),
            ",".join(x["host"] for x in h.get("parentTemplates", [])),
            d.get("securityname", "-"),
            SEC.get(str(d.get("securitylevel", "")), "-"),
            AUTH.get(str(d.get("authprotocol", "")), "-"),
            PRIV.get(str(d.get("privprotocol", "")), "-")))
elif cmd == "fresh":
    # 監視データの鮮度＝実際にポーリングできている事の通し証明
    # (availability の緑はエージェント応答のみで、データ取得の保証にならない)
    hs = rpc("host.get", {{"filter": {{"host": [sys.argv[2]]}}}}, t)
    if not hs:
        sys.exit("HOST_NOT_FOUND")
    items = rpc("item.get", {{"hostids": hs[0]["hostid"],
                              "output": ["lastclock"], "filter": {{"status": "0"}}}}, t)
    last = max((int(i["lastclock"]) for i in items if i["lastclock"] != "0"), default=0)
    age = int(time.time()) - last if last else -1
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    ok = "true" if 0 <= age <= limit else "false"
    print(f"HOST={{sys.argv[2]}} FRESH={{ok}} AGE={{age}} LIMIT={{limit}}")
EOF
chmod 755 /opt/ccnp/zbx_check.py
log "DONE"
"""


# ---- 出力 ------------------------------------------------------------------

def build(repo, seed, count, forced, mode="ts", level=1):
    rnd = random.Random(seed)
    if mode == "ts":
        pid = f"GEN-SNMPTS-{seed}"
    else:
        pid = f"GEN-ZBXBUILD-{seed}" if level == 1 else f"GEN-ZBXBUILD2-{seed}"
    lo = rand_values(rnd)
    # 物理: ZBX01(ens3/slot1)-RT01(E0/0) / RT01(E0/1)-RT02(E0/0) / RT02(E0/1)-RT03(E0/0)
    ctx = {
        "lo": lo,
        "ifs": {
            "RT01": [("Ethernet0/0", f"{POLLER_NET}.1", "255.255.255.248", "to ZBX01(poller)"),
                     ("Ethernet0/1", "10.1.12.1", "255.255.255.252", "to RT02")],
            "RT02": [("Ethernet0/0", "10.1.12.2", "255.255.255.252", "to RT01"),
                     ("Ethernet0/1", "10.1.23.1", "255.255.255.252", "to RT03")],
            "RT03": [("Ethernet0/0", "10.1.23.2", "255.255.255.252", "to RT02")],
        },
        # ポーラからの受信 IF（if_acl 故障で使う）
        "ingress_if": {"RT01": "Ethernet0/0", "RT02": "Ethernet0/0",
                       "RT03": "Ethernet0/0"},
    }
    # 故障選定: ノードごとに最大1件、count ノードに注入（1台は緑で残すのが既定）。
    # build モードは故障なし（初期＝SNMP未構築が「課題」そのもの）。
    def assign(chosen):
        """victims 制約（FAULTS[f]['victims']）を満たすまで再抽選。
        例: OSPF 系故障は RT01(ポーラ直結・隣接なし/静的経路)だと無効化するため除外。"""
        for _ in range(200):
            victims = rnd.sample(RTS, k=len(chosen))
            faults = dict(zip(victims, chosen))   # node -> fault name
            if all(n in FAULTS[f].get("victims", RTS) for n, f in faults.items()):
                return faults
        raise SystemExit(f"victims 制約を満たす割当が見つかりません: {chosen}")

    if mode == "build":
        chosen, faults = [], {}
    elif forced:
        chosen = forced
        faults = assign(chosen)
    else:
        chosen = rnd.sample(sorted(FAULTS), k=count)
        faults = assign(chosen)

    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    # initial（RT / ZBX01 スタブ / ZBX01 構築スクリプト）
    for r in RTS:
        with open(f"{pdir}/initial/{r}.cfg.j2", "w", encoding="utf-8") as f:
            f.write(rt_config(r, ctx, faults.get(r),
                              include_snmp=(mode == "ts")))
    with open(f"{pdir}/initial/{ZBX}.cfg.j2", "w", encoding="utf-8") as f:
        f.write("# server ノードは baseline_server.cfg.j2 が全て描画（このスタブは連結対策の空ファイル）\n")
    with open(f"{pdir}/initial/{ZBX}.sh.j2", "w", encoding="utf-8") as f:
        f.write(zbx_init_sh(ctx))

    # problem.yml。monitoring セクション＝lab_up の自動ホスト登録内容。
    # ★build モードでは monitoring を出さない（登録は受験者の課題）。
    #   同内容は solution/monitoring.yml に置き、検証時は
    #   zbx_setup.py --monitoring-yml で模範解答として投入する。
    monitoring = {
        "server": ZBX,
        "web_port": ZBX_WEB_PORT,
        "group": "CCNP-LAB",
        "hosts": [{
            "host": r, "ip": lo[r],
            "snmpv3": {"user": V3_USER,
                       "auth_protocol": "SHA", "auth_pass": V3_AUTH_PASS,
                       "priv_protocol": "AES", "priv_pass": V3_PRIV_PASS},
            "templates": ["Cisco IOS by SNMP"],
        } for r in RTS],
    }
    difficulty = max(FAULTS[f]["difficulty"] for f in chosen) if chosen else 3
    pmeta = {
        "id": pid,
        "title": (f"SNMPv3×Zabbix監視 複合TS (seed={seed})" if mode == "ts"
                  else f"監視一貫構築 — SNMPv3×Zabbix (seed={seed})"),
        "exam": "ENCOR",
        "topics": ["snmp", "snmpv3", "monitoring", "zabbix", "generated"]
                  + (["troubleshooting"] if mode == "ts" else ["build"]),
        "difficulty": difficulty,
        "topology": "generated",
        "target_nodes": RTS + [ZBX],
        "points": 100,
        "access": "ssh",
        "node_image_families": {ZBX: "ubuntu"},
        "node_ram": {ZBX: 3072},
        "lab": {"links": [
            {"a": ZBX, "a_if": 1, "b": "RT01", "b_if": 0},
            {"a": "RT01", "a_if": 1, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 0},
        ]},
    }
    if mode == "ts":
        pmeta["monitoring"] = monitoring
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_snmpv3_ts.py) seed={seed}\n")
        yaml.safe_dump(pmeta, f, allow_unicode=True, sort_keys=False, width=4096)

    # grading.yml（監視サーバ視点＝ZBX01 から実測 + Zabbix API + 機器サニティ）
    snmpget = (f"snmpget -v3 -u {V3_USER} -l authPriv -a SHA -A {V3_AUTH_PASS} "
               f"-x AES -X {V3_PRIV_PASS} -t 2 -r 1")
    checks = []
    if mode == "ts":
        for r in RTS:
            checks += [
                {"name": f"{r}: ZBX01からSNMPv3で応答(sysName)", "node": ZBX,
                 "exec": "shell",
                 "command": f"{snmpget} {lo[r]} 1.3.6.1.2.1.1.5.0",
                 "raw": [{"contains": r}], "points": 15},
                {"name": f"{r}: Zabbix 監視が正常(SNMP available)", "node": ZBX,
                 "exec": "shell",
                 "command": f"python3 /opt/ccnp/zbx_check.py availability {r}",
                 "raw": [{"regex": "SNMP_AVAILABLE=1"}], "points": 10},
                {"name": f"{r}: ZBX01から ping 到達", "node": ZBX,
                 "exec": "shell",
                 "command": f"ping -c 2 -W 1 {lo[r]}",
                 "raw": [{"regex": " 0% packet loss"}], "points": 5},
                {"name": f"{r}: SNMPv3 ユーザが NOC 標準で存在", "node": r,
                 "command": "show snmp user",
                 "raw": [{"contains": V3_USER}], "points": 3},
            ]
    else:
        # build: ①機器側(snmpget=効果) ②Zabbix登録属性(hostinfo) ③通し(fresh)
        #        ④機器サニティ(show snmp user=効果 / ACL=仕様準拠)
        for r in RTS:
            checks += [
                {"name": f"{r}: ZBX01からSNMPv3で応答(sysName)=機器側構築OK",
                 "node": ZBX, "exec": "shell",
                 "command": f"{snmpget} {lo[r]} 1.3.6.1.2.1.1.5.0",
                 "raw": [{"contains": r}], "points": 9},
                {"name": f"{r}: Zabbix登録(対象IP/SNMP種別/テンプレ/グループ)",
                 "node": ZBX, "exec": "shell",
                 "command": f"python3 /opt/ccnp/zbx_check.py hostinfo {r}",
                 "raw": [{"regex": "TYPE=2"},
                         {"regex": f"IF={lo[r]}:161"},
                         {"regex": "TEMPLATE=[^ ]*Cisco IOS by SNMP"},
                         {"regex": "GROUP=[^ ]*CCNP-LAB"}], "points": 7},
                {"name": f"{r}: Zabbix登録(SNMPv3パラメータ)",
                 "node": ZBX, "exec": "shell",
                 "command": f"python3 /opt/ccnp/zbx_check.py hostinfo {r}",
                 "raw": [{"regex": f"V3USER={V3_USER}"},
                         {"regex": "SECLEVEL=authPriv"},
                         {"regex": "AUTH=SHA "},
                         {"regex": "PRIV=AES128"}], "points": 7},
                {"name": f"{r}: 監視データが流れている(鮮度180秒以内)",
                 "node": ZBX, "exec": "shell",
                 "command": f"python3 /opt/ccnp/zbx_check.py fresh {r} 180",
                 "raw": [{"regex": "FRESH=true"}], "points": 5},
                {"name": f"{r}: SNMPv3ユーザ仕様(SHA/AES128)",
                 "node": r, "command": "show snmp user",
                 "raw": [{"contains": V3_USER},
                         {"contains": "Authentication Protocol: SHA"},
                         {"contains": "Privacy Protocol: AES128"}], "points": 3},
            ]
            if level == 1:
                checks += [
                    # ★IOS-XE は番号付き標準ACLを running-config で `ip access-list standard 99`
                    #   ブロック表示するため旧形式行では引っ掛からない → show access-lists で効果を見る
                    {"name": f"{r}: group にポーラ限定ACL(99)適用",
                     "node": r,
                     "command": "show running-config | include snmp-server group",
                     "raw": [{"regex": "access 99"}], "points": 1},
                    {"name": f"{r}: ACL 99 がポーラ({POLLER_NET}.2)を許可",
                     "node": r,
                     "command": "show access-lists 99",
                     "raw": [{"regex": f"permit {POLLER_NET}\\.2"}], "points": 1},
                ]
            else:
                # Lv2: 実装(ACL番号/名前/方式)を問わない効果ベース。
                # ZBX01 の検証用アドレス .3 から送信 → 拒否(タイムアウト)されること。
                # 到達性そのものは 9点チェック(.2から成功)が担保するので偽合格しない。
                checks += [
                    {"name": f"{r}: SNMPがポーラ限定(検証端末{POLLER_NET}.3からは拒否)",
                     "node": ZBX, "exec": "shell",
                     "command": (f"{snmpget} --clientaddr={POLLER_NET}.3 "
                                 f"{lo[r]} 1.3.6.1.2.1.1.5.0 2>&1 || true"),
                     "raw": [{"regex": "Timeout"}], "points": 2},
                ]
    checks.append({"name": "ZBX01: Web UI 稼働", "node": ZBX, "exec": "shell",
                   "command": f"curl -s -o /dev/null -w '%{{http_code}}' "
                              f"http://127.0.0.1:{ZBX_WEB_PORT}/",
                   "raw": [{"regex": "200|302"}], "points": 1})
    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_snmpv3_ts.py) seed={seed}\n")
        yaml.safe_dump(grading, f, allow_unicode=True, sort_keys=False, width=4096)

    # solution（fix.json = fix_generated.yml 互換。ts=故障修正 / build=機器側の模範構築）
    if mode == "ts":
        fixes = []
        for node, fname in faults.items():
            fixes += FAULTS[fname]["fixes"](node, ctx)
        with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
            json.dump({"count": len(faults),
                       "faults": [{"type": fn, "node": n,
                                   "signature": FAULTS[fn]["signature"],
                                   "difficulty": FAULTS[fn]["difficulty"],
                                   "desc": FAULTS[fn]["desc"]}
                                  for n, fn in faults.items()]},
                      f, ensure_ascii=False, indent=2)
    else:
        fixes = [{"node": r, "lines": [
            f"snmp-server view {V3_VIEW} iso included",
            f"snmp-server group {V3_GROUP} v3 priv read {V3_VIEW} access 99",
            f"access-list 99 permit {POLLER_NET}.2",
            "snmp-server location CCNP-LAB",
            user_line(),
        ]} for r in RTS]
        # Zabbix 側の模範解答（zbx_setup.py --monitoring-yml で投入して自己検証）
        with open(f"{pdir}/solution/monitoring.yml", "w", encoding="utf-8") as f:
            f.write("# 模範解答(Zabbix側の登録内容)。検証: zbx_setup.py --monitoring-yml <this>\n")
            yaml.safe_dump({"monitoring": monitoring}, f,
                           allow_unicode=True, sort_keys=False, width=4096)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    # task.md（ts=ヒント控えめ / build=仕様書スタイル・状態要件のみで手順は書かない）
    lo_rows = "\n".join(f"| {r} | `{lo[r]}` |" for r in RTS)
    if mode == "build" and level == 2:
        task = f"""# 問題 {pid} : 監視一貫構築 Lv2 — SNMPv3×Zabbix（難易度4）

## 状況
新設ルータ RT01〜RT03 を NOC の Zabbix 監視に組み込みます。監視サーバ ZBX01 は
構築済み（Web UI ログイン可・**ホスト未登録**）です。今回は詳細な設定仕様書は
ありません。以下の**運用要件**を満たすように、機器側・Zabbix 側の設計と実装を
両方行ってください。実装方式（view/group 名、ACL の種類・番号・名前 等）は
要件を満たす限り自由です。

## 環境
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:{ZBX_WEB_PORT}/`（`Admin` / `zabbix`）
  - MGMT IP は出題時の案内を参照
- ZBX01 のインバンドアドレス: **{POLLER_NET}.2/29**（各ルータへ経路設定済み）
  - 同セグメントに NOC 検証端末 **{POLLER_NET}.3** が存在する（後述の要件4で使用）
- ルータの IP/OSPF は設定済み。**SNMP はどの機器にも未設定**。

## 運用要件
1. **監視プロトコル**: 機器の監視は SNMPv3 の最高セキュリティレベル（認証＋暗号化）
   で行うこと。NOC 標準監視アカウントを使用する:
   user `{V3_USER}`（認証 **SHA** `{V3_AUTH_PASS}` / 暗号化 **AES128** `{V3_PRIV_PASS}`）。
   システム情報・IF 情報（MIB-2 相当）が取得できること。
2. **監視登録**: Zabbix に 3 ホストを登録し監視を開始すること。NOC の運用規程:
   ホスト名は機器名と大文字完全一致（`RT01`〜`RT03`）・ホストグループ `CCNP-LAB`・
   テンプレート `Cisco IOS by SNMP`・監視対象は各機の Loopback0（下表）/UDP 161。
3. **継続性**: 登録して終わりではなく、**監視データが流れ続けている**こと
   （Latest data の値が更新され続ける。緑アイコンだけでは不十分）。
4. **アクセス制御**: 機器への SNMP アクセスは監視サーバ（{POLLER_NET}.2）**のみ**に
   限定すること。実装方法は問わないが、検証端末 {POLLER_NET}.3 からの SNMP
   アクセスが**拒否される**ことをもって確認する（採点もこの方法で行う）。

| ルータ | 監視対象 (Loopback0) |
|--------|----------------------|
{lo_rows}

## 注意
- ZBX01 の OS/Zabbix 本体はいじらない（Web UI での登録操作のみ）。
- `snmp-server user` は running-config に表示されない仕様に注意。
- 登録直後の初回ポーリングまで最大 1 分待つこと。

## アクセス・採点
ルータ: SSH/コンソール `SUZUKI / CCNP`。採点は反映ラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=20 \\
  -e settle_delay=15 --vault-password-file <(printf 'CCNP\\n')
```
"""
        with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
            f.write(task)
        print(f"generated {pid} (mode=build Lv2): 要件型・効果ベースACL採点")
        print("  Zabbix targets: " + ", ".join(f"{r}={lo[r]}" for r in RTS))
        return
    if mode == "build":
        task = f"""# 問題 {pid} : 監視一貫構築 — SNMPv3×Zabbix（難易度{difficulty}）

## 状況
新設ルータ RT01〜RT03 を NOC の Zabbix 監視に組み込みます。監視サーバ ZBX01 は
構築済み（Web UI ログイン可・**ホスト未登録**）です。以下の**仕様書どおりの状態**を、
ルータ側・Zabbix 側の両方に構築してください。手順・画面操作は問いません。

## 環境
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:{ZBX_WEB_PORT}/`（`Admin` / `zabbix`）
  - MGMT IP は provision 時の割当（既定 RT01=.11〜ZBX01=.14。並行ラボ運用時は
    オフセットされるため出題時の案内を参照）
- ZBX01 はインバンド {POLLER_NET}.2 から各ルータへ到達可（経路設定済み）
- ルータの IP/OSPF は設定済み。**SNMP はどの機器にも未設定**。

## 仕様書 1: ルータ側 SNMPv3（RT01〜RT03 共通）
| 項目 | 値 |
|------|-----|
| view | `{V3_VIEW}`（iso 配下すべて読み取り可） |
| group | `{V3_GROUP}`（v3 / **authPriv** / read view={V3_VIEW}） |
| user | `{V3_USER}`（認証 **SHA** `{V3_AUTH_PASS}` / 暗号化 **AES128** `{V3_PRIV_PASS}`） |
| アクセス制限 | **標準ACL 99** で SNMP 要求元を {POLLER_NET}.2 のみに限定し group に適用 |
| その他 | location `CCNP-LAB` |

## 仕様書 2: Zabbix 側 監視登録（3 ホスト）
| 項目 | 値 |
|------|-----|
| ホスト名 | `RT01` / `RT02` / `RT03`（**大文字・完全一致**） |
| ホストグループ | `CCNP-LAB`（無ければ作成） |
| インターフェース | **SNMP**・対象 IP は下表の Loopback0・ポート 161 |
| SNMPv3 | 仕様書 1 のアカウント（authPriv / SHA / AES128） |
| テンプレート | `Cisco IOS by SNMP` |

| ルータ | 監視対象 (Loopback0) |
|--------|----------------------|
{lo_rows}

## 到達目標（この状態になれば合格）
- ZBX01 から各 Loopback0 へ仕様のアカウントで SNMPv3 取得が成功する
- Zabbix の **Latest data で 3 ホストとも値が更新され続けている**（緑表示だけでは不十分）

## 注意
- ZBX01 の OS/Zabbix 本体はいじらない（登録操作のみ）。
- `snmp-server user` は running-config に表示されない仕様に注意。
- 登録直後の初回ポーリングまで最大 1 分待つこと。

## アクセス・採点
ルータ: SSH/コンソール `SUZUKI / CCNP`。採点は反映ラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=20 \\
  -e settle_delay=15 --vault-password-file <(printf 'CCNP\\n')
```
"""
        with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
            f.write(task)
        print(f"generated {pid} (mode=build): SNMP/監視登録なし初期状態・仕様書型")
        print("  Zabbix targets: " + ", ".join(f"{r}={lo[r]}" for r in RTS))
        return

    task = f"""# 問題 {pid} : 監視サービス復旧 — SNMPv3×Zabbix（難易度{difficulty}）

## 状況
NOC の Zabbix で一部ルータの監視に異常が出ています。ダッシュボードの
「見え方」から障害を切り分け、**全ルータの監視が正常（SNMP 取得成功・緑）**に
戻るよう復旧してください。原因は 1 台・1 種類とは限りません。

## 監視環境
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:{ZBX_WEB_PORT}/`（`Admin` / `zabbix`）
  - MGMT IP は provision 時の割当（既定 RT01=.11〜ZBX01=.14。並行ラボ運用時は
    オフセットされるため出題時の案内を参照）
  - Monitoring → Hosts / Latest data / Problems を活用
- 監視サーバ ZBX01 はインバンド（{POLLER_NET}.2）から各ルータの **Loopback0** を
  SNMPv3 でポーリングしている:

| ルータ | 監視対象 (Loopback0) |
|--------|----------------------|
{lo_rows}

## NOC 標準の監視アカウント（機器側はこの仕様に合致していること）
- SNMPv3 user `{V3_USER}` / group `{V3_GROUP}`（**authPriv**）
- 認証: **SHA** / `{V3_AUTH_PASS}`、暗号化: **AES128** / `{V3_PRIV_PASS}`
- view `{V3_VIEW}`（システム情報・IF 情報が取得できること）

## 到達目標
- Zabbix 上で RT01〜RT03 の SNMP 監視がすべて正常（緑・エラーなし）
- ZBX01 から各 Loopback0 への SNMPv3 取得と ping が成功

## 注意
- ZBX01（監視サーバ）の設定は正しい。**触るのはルータ側のみ**。
- `snmp-server user` は running-config に表示されない仕様に注意。
- 修正後、Zabbix の表示が緑に戻るまでポーリング周期ぶん（〜1分）待つこと。

## アクセス・採点
ルータ: SSH `SUZUKI / CCNP`。採点は修正反映のラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=20 \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)

    print(f"generated {pid}: faults={faults} difficulty={difficulty}")
    print(f"  Zabbix polls: " + ", ".join(f"{r}={lo[r]}" for r in RTS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--mode", choices=["ts", "build"], default="ts",
                    help="ts=故障TS(既定) / build=監視一貫構築(Lv1)")
    ap.add_argument("--count", type=int, default=2,
                    help="故障ノード数（ts のみ。既定2: 1台は緑で残し対比させる）")
    ap.add_argument("--faults", help="カンマ区切りで故障を固定（ts のみ。既定 seed 乱択）")
    ap.add_argument("--level", type=int, choices=[1, 2], default=1,
                    help="build のみ。1=仕様書型(既定) / 2=要件型+効果ベースACL採点")
    a = ap.parse_args()
    forced = a.faults.split(",") if a.faults else None
    if forced:
        for x in forced:
            if x not in FAULTS:
                raise SystemExit(f"unknown fault: {x} (candidates: {sorted(FAULTS)})")
    build(a.repo, a.seed, a.count, forced, mode=a.mode, level=a.level)


if __name__ == "__main__":
    main()
