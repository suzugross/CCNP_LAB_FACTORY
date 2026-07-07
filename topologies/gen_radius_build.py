#!/usr/bin/env python3
"""FreeRADIUS×IOS AAA 組み立て問題の生成器（Linuxサーバ構築ラボ第2弾）。

正準トポロジ(2RT+RADIUSサーバ):
  SRV01(FreeRADIUS) --- RT01 --- RT02
  - SRV01(ubuntu): freeradius/freeradius-utils を導入済み・未設定で渡す。
    ens2=MGMT(採点/SSH), ens3=インバンド 10.99.0.2/30(netplan 永続)。
  - RT01/RT02: IF/OSPF は健全構成で投入済み。受験者の課題は
    サーバ側(clients.conf/authorize) と 機器側(aaa 認証/認可の RADIUS 化)。

PoC 実証済みの設計要点(2026-07-04):
  - FreeRADIUS 3.2.5(Ubuntu24.04) は apt で数十秒。設定は改行区切り(セミコロン不可)。
  - Cisco-AVPair "shell:priv-lvl=N" で SSH ログイン即 priv N を実証(IOL 17.15)。
  - ★教育核心: `aaa authentication login default group radius local` の local は
    「サーバ無応答(ERROR)時のみ」のフォールバック。RADIUS が Reject を返すと
    local へは切り替わらない → 既存自動化ユーザ SUZUKI を RADIUS へ登録しないと
    締め出される(採点も全滅する)。task で要件化し、注意書きで仕組みを明示する。
  - RT02 の RADIUS 送信元は egress IF(10.1.12.2) → clients.conf は 2 台分必要。

採点: 挙動ベース。
  - SRV01 上 radclient -x (localhost クライアント testing123 経由) で
    Accept/Reject と応答 AVPair(priv-lvl) を実測 → localhost client は消すな(task 明記)
  - 各 RT で `test aaa group radius ... legacy`(secret/client/到達性の複合証明)
  - `show aaa servers` でサーバ定義の実効値
  - 方式リスト(フォールバック順序)のみ show run 検査(挙動で見るには
    サーバ断が必要なため config 検査を許容)

出力: problems/GEN-RADIUS-<seed>/
  {problem.yml, initial/{RT01,RT02}.cfg.j2, SRV01.cfg.j2(空), SRV01.sh.j2,
   grading.yml, task.md, solution/{solution.md, fix.json, SRV01_solve.sh}}
使い方: gen_radius_build.py --repo . --seed <int>
"""
import argparse
import json
import os
import random

import yaml

SRV = "SRV01"
RTS = ["RT01", "RT02"]
SRV_IP = "10.99.0.2"
RT_SRC = {"RT01": "10.99.0.1", "RT02": "10.1.12.2"}   # 各RTのRADIUS送信元
ADMINS = ["noc-taro", "noc-hanako", "netadmin"]
HELPDESKS = ["helpdesk", "monitor-op"]


def rand_values(rnd):
    ks, lo = set(), {}
    for rt in RTS:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in ks:
                ks.add(k)
                lo[rt] = f"{k}.{k}.{k}.{k}"
                break
    return {
        "lo": lo,
        "admin": rnd.choice(ADMINS),
        "admin_pass": f"Noc-{rnd.randint(1000, 9999)}",
        "help": rnd.choice(HELPDESKS),
        "help_pass": f"Desk-{rnd.randint(1000, 9999)}",
        "secret": f"Ccnp-Rad-{rnd.randint(1000, 9999)}",
    }


def rt_cfg(node, v):
    lo = v["lo"][node]
    if node == "RT01":
        ifs = [("Ethernet0/0", "10.99.0.1", "255.255.255.252", "to SRV01 (RADIUS)"),
               ("Ethernet0/1", "10.1.12.1", "255.255.255.252", "to RT02")]
        nets = ["10.99.0.0 0.0.0.3", "10.1.12.0 0.0.0.3"]
    else:
        ifs = [("Ethernet0/0", "10.1.12.2", "255.255.255.252", "to RT01")]
        nets = ["10.1.12.0 0.0.0.3"]
    lines = ["! --- data plane (構築済み・変更不可) ---",
             "interface Loopback0",
             f" ip address {lo} 255.255.255.255"]
    for ifname, ip, mask, desc in ifs:
        lines += [f"interface {ifname}",
                  f" description === {desc} ===",
                  f" ip address {ip} {mask}",
                  " no shutdown"]
    lines += ["router ospf 1", f" router-id {lo}",
              f" network {lo} 0.0.0.0 area 0"]
    lines += [f" network {net} area 0" for net in nets]
    return "\n".join(lines) + "\n"


def srv_init_sh():
    """SRV01: パッケージ導入とネットワーク永続化のみ。RADIUS 設定は受験者の課題。"""
    return """#!/bin/bash
# SRV01 (RADIUS サーバ素体) 初期化 — 生成: gen_radius_build.py
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "in-band NIC / 社内への経路を netplan で永続化"
rm -f /etc/netplan/50-cloud-init.yaml
cat > /etc/netplan/60-ccnp.yaml <<'EOF'
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{{ mgmt_ip }}/{{ mgmt_prefixlen }}]
      routes:
        - to: default
          via: {{ mgmt_gw }}
      nameservers:
        addresses: {{ mgmt_dns | to_json }}
    ens3:
      addresses: [10.99.0.2/30]
      routes:
        - to: 10.1.12.0/30
          via: 10.99.0.1
EOF
chmod 600 /etc/netplan/60-ccnp.yaml
netplan apply

log "パッケージ導入 (freeradius / freeradius-utils)"
for i in 1 2 3; do
  apt-get update -qq && \\
  apt-get install -y -qq freeradius freeradius-utils && break
  sleep 10
done
systemctl enable -q freeradius || true
log "DONE"
"""


def srv_solve_sh(v):
    """模範解答（SRV01）。PoC 実証済みの構文（改行区切り・タブ字下げ）。"""
    a, ap, h, hp, sec = v["admin"], v["admin_pass"], v["help"], v["help_pass"], v["secret"]
    return f"""#!/bin/bash
# GEN-RADIUS 模範解答投入（自己検品用）
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"

cat > /etc/freeradius/3.0/clients.conf <<'EOF'
# ローカルテスト用（採点も使用・削除禁止）
client localhost {{
	ipaddr = 127.0.0.1
	secret = testing123
}}
client rt01 {{
	ipaddr = {RT_SRC['RT01']}
	secret = {sec}
}}
client rt02 {{
	ipaddr = {RT_SRC['RT02']}
	secret = {sec}
}}
EOF

cat > /etc/freeradius/3.0/mods-config/files/authorize <<'EOF'
{a} Cleartext-Password := "{ap}"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"

{h} Cleartext-Password := "{hp}"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=1"

SUZUKI Cleartext-Password := "CCNP"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"
EOF

freeradius -XC >/dev/null
systemctl restart freeradius
systemctl is-active freeradius
echo SOLVED
"""


def build(repo, seed):
    rnd = random.Random(seed)
    pid = f"GEN-RADIUS-{seed}"
    v = rand_values(rnd)
    a, ap, h, hp, sec = v["admin"], v["admin_pass"], v["help"], v["help_pass"], v["secret"]

    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    for rt in RTS:
        with open(f"{pdir}/initial/{rt}.cfg.j2", "w", encoding="utf-8") as fp:
            fp.write(rt_cfg(rt, v))
    with open(f"{pdir}/initial/{SRV}.cfg.j2", "w", encoding="utf-8") as fp:
        fp.write("# server ノードは baseline_server.cfg.j2 が全て描画（このスタブは連結対策の空ファイル）\n")
    with open(f"{pdir}/initial/{SRV}.sh.j2", "w", encoding="utf-8") as fp:
        fp.write(srv_init_sh())

    pmeta = {
        "id": pid,
        "title": f"中央認証(FreeRADIUS)×IOS AAA 構築 (seed={seed})",
        "exam": "ENCOR",
        "topics": ["aaa", "radius", "security", "linux", "server", "generated"],
        "difficulty": 4,
        "topology": "generated",
        "target_nodes": RTS + [SRV],
        "points": 100,
        "access": "ssh",
        "node_image_families": {SRV: "ubuntu"},
        "lab": {"links": [
            {"a": SRV, "a_if": 1, "b": "RT01", "b_if": 0},
            {"a": "RT01", "a_if": 1, "b": "RT02", "b_if": 0},
        ]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_radius_build.py) seed={seed}\n")
        yaml.safe_dump(pmeta, fp, allow_unicode=True, sort_keys=False, width=4096)

    def radclient(user, password):
        return (f"echo \"User-Name={user},User-Password={password}\" | "
                f"radclient -x 127.0.0.1 auth testing123")

    checks = [
        # --- SRV01: RADIUS サーバ (42) ---
        {"name": "SRV01: freeradius が稼働", "node": SRV, "exec": "shell",
         "command": "systemctl is-active freeradius",
         "raw": [{"regex": "^active"}], "points": 6},
        {"name": f"SRV01: {a} 認証OK＋priv15 属性", "node": SRV, "exec": "shell",
         "command": radclient(a, ap),
         "raw": [{"regex": "Received Access-Accept"},
                 {"contains": "priv-lvl=15"}], "points": 12},
        {"name": f"SRV01: {h} 認証OK＋priv1 属性", "node": SRV, "exec": "shell",
         "command": radclient(h, hp),
         "raw": [{"regex": "Received Access-Accept"},
                 {"regex": r"priv-lvl=1\b"}], "points": 10},
        {"name": "SRV01: SUZUKI(自動化用) 認証OK", "node": SRV, "exec": "shell",
         "command": radclient("SUZUKI", "CCNP"),
         "raw": [{"regex": "Received Access-Accept"}], "points": 8},
        {"name": f"SRV01: {a} 誤パスワードは Reject", "node": SRV, "exec": "shell",
         "command": radclient(a, "WrongPass999"),
         "raw": [{"regex": "Received Access-Reject"}], "points": 6},
    ]
    # --- 各RT: AAA 実効 (58) ---
    for rt in RTS:
        checks += [
            {"name": f"{rt}: test aaa で {a} 認証成功", "node": rt,
             "command": f"test aaa group radius {a} {ap} legacy",
             "raw": [{"contains": "successfully authenticated"}], "points": 15},
            {"name": f"{rt}: RADIUS サーバ定義が実効", "node": rt,
             "command": "show aaa servers",
             "raw": [{"contains": SRV_IP}, {"contains": "auth-port 1812"}],
             "points": 7},
            {"name": f"{rt}: ログイン認証が RADIUS優先+local予備", "node": rt,
             "command": "show running-config | include aaa authentication",
             "raw": [{"regex": "aaa authentication login default group radius local"}],
             "points": 7},
        ]
    assert sum(c["points"] for c in checks) == 100
    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_radius_build.py) seed={seed}\n")
        yaml.safe_dump(grading, fp, allow_unicode=True, sort_keys=False, width=4096)

    # solution
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fp:
        json.dump({"fixes": [x for rt in RTS for x in (
            {"node": rt, "lines": ["aaa new-model"]},
            {"node": rt, "parents": ["radius server SRV01"],
             "lines": ["address ipv4 10.99.0.2 auth-port 1812 acct-port 1813",
                       f"key {sec}"]},
            {"node": rt, "lines": [
                "aaa authentication login default group radius local",
                "aaa authorization exec default group radius local"]},
        )]}, fp, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/SRV01_solve.sh", "w", encoding="utf-8") as fp:
        fp.write(srv_solve_sh(v))
    os.chmod(f"{pdir}/solution/SRV01_solve.sh", 0o755)
    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as fp:
        fp.write(f"""# {pid} 模範解答（採点者用）

## サーバ側: SRV01_solve.sh（clients.conf 2台分＋authorize 3ユーザ＋restart）
## NW側: fix.json（aaa new-model → radius server ブロック → 方式リスト）

## レビュー観点
- SUZUKI を RADIUS に登録したか（**Reject では local へフォールバックしない**。
  登録漏れ＝自動化/採点の締め出し。これが本問最大の学び）
- clients.conf が 2 台分あるか（RT02 の送信元は {RT_SRC['RT02']}）
- priv-lvl を AVPair で返しているか（{h} は priv1 = show 系のみ）
- 機器側は `test aaa` で検証してからセッションを切ったか
""")

    task = f"""# 問題 {pid} : 中央認証(FreeRADIUS)×IOS AAA 構築（難易度4）

## シナリオ
監査対応のため、ルータのログイン認証を**中央 RADIUS サーバ(SRV01)**へ統合します。
アカウントは RADIUS で一元管理し、ローカルユーザは**サーバ障害時の予備**とします。

```
 SRV01 ────── RT01 ────── RT02
(FreeRADIUS)
 10.99.0.0/30   10.1.12.0/30
```

## 構成（初期状態で投入済み・変更不可）
- ルーティング(OSPF)・各 IF の IP は設定済み（RT02 からも SRV01 へ到達可能）
- SRV01: ens3 = `{SRV_IP}/30`。**freeradius / freeradius-utils 導入済み（未設定）**
- 両ルータは現在ローカル認証（SUZUKI / CCNP）

## 要件
### A. RADIUS サーバ（SRV01 / FreeRADIUS）
- **アカウント台帳**（この 3 ユーザを認証できること）:

| ユーザ | パスワード | 権限 |
|--------|-----------|------|
| {a} | `{ap}` | 管理者（ログイン直後から **priv 15**） |
| {h} | `{hp}` | 閲覧のみ（ログイン直後 **priv 1**） |
| SUZUKI | `CCNP` | 自動化・採点用（**priv 15・登録必須**） |

- 権限レベルは RADIUS の応答属性で機器へ渡すこと（Cisco の VSA を使う）
- **クライアント**: RT01・RT02 の 2 台。共有シークレット `{sec}`
- 既定で入っている **localhost クライアント（secret testing123）は採点が使うため残すこと**

### B. 機器側 AAA（RT01・RT02 の両方）
- ログイン認証を **RADIUS 優先・ローカル予備**に切り替えること
- exec 権限(認可)も RADIUS の属性に従うこと
- RADIUS サーバ定義: `{SRV_IP}`、認証ポート 1812 / アカウンティング 1813

## 到達目標
- {a} / {h} / SUZUKI が RADIUS 経由で両ルータへ SSH ログインできる
  （{a}=即 priv15、{h}=priv1、SUZUKI=即 priv15）
- 誤パスワードは拒否される
- 各ルータで `test aaa group radius <user> <pass> legacy` が成功する

## サーバ操作ガイド（NW 機器と勝手が違う所だけ。設定値は要件から組み立てること）
SRV01 へは SSH `SUZUKI / CCNP`（sudo 可）。設定は **/etc/freeradius/3.0/** 配下。
- クライアント（NAS）定義: `clients.conf` — `client <名前> {{ ipaddr = … / secret = … }}`
  の**改行区切り**（セミコロン不要。付けると構文エラー）
- ユーザ定義: `mods-config/files/authorize` — 1 ユーザ =
  `<名前> Cleartext-Password := "<パス>"` ＋ 続く行に**タブ字下げで応答属性**
  （属性行は最後の 1 行以外、行末カンマ）。Cisco の権限属性は
  `Cisco-AVPair = "shell:priv-lvl=<N>"`
- 検証と反映:
  - 構文チェック: `sudo freeradius -XC`
  - `sudo systemctl restart freeradius` → `systemctl status freeradius`
  - ローカル試験: `radtest <user> '<pass>' 127.0.0.1 0 testing123`
    （Access-Accept / Access-Reject が返る）
  - 詳細ログ: いったん `sudo systemctl stop freeradius` →
    `sudo freeradius -X`（フォアグラウンドデバッグ。Ctrl+C で戻し、start を忘れずに）
- ★**クライアントの ipaddr は「機器が RADIUS を送る送信元 IP」**。
  対向直結でないルータはどの IP から届くか（経路の出口 IF）を考えること

## 注意（締め出しリスク — 本問最大の落とし穴）
- `… group radius local` の **local 予備が効くのは「サーバ無応答」の時だけ**。
  RADIUS が生きていて **Reject を返した場合、ローカル認証へは切り替わらない**。
  → 台帳の SUZUKI 登録を漏らすと、自分も採点も締め出される
- 機器側の AAA を書いたら、**ログアウトする前に** 別セッション or `test aaa` で
  ログインできることを必ず確認すること（コンソールからは復旧可能）

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13）
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=10 \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as fp:
        fp.write(task)

    print(f"generated {pid}: admin={a}/{ap} help={h}/{hp} secret={sec} lo={v['lo']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args()
    build(a.repo, a.seed)


if __name__ == "__main__":
    main()
