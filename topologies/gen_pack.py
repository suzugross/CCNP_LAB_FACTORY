#!/usr/bin/env python3
"""問題パック(連続出題)ビルダ — BL-099。

「寝る前に作らせ、翌朝から1日で解く」5問セット(紙面3＋ラボ2)を組み立てる。
成果物は `packs/<PACK-ID>/`(gitignore 済・使い捨て):

  index.html      目次＋進捗＋所要目安
  q1.html … qN.html  問題用紙(外部参照ゼロの単一ファイル HTML)
  解答.md          ★ユーザが書き込む唯一のファイル
  manifest.yml    機械用メタ(問題ID・seed・台数・キーの所在・状態)
  ※ビルドログは topologies/_state/pack-<PACK-ID>.log(故障種が出るため隔離)

サブコマンド:
  new    --paper 3 --lab 2 [--budget 20] [--dry-run]
      パックを作る。--dry-run は **CML にも questions/ にも一切触らない**
      プレビュー用(既出の古い紙面を借りて体裁だけ作る)。
  status [--pack-id P]      解答.md を読んで進捗を表示(オフライン)
  grade  [--pack-id P]      解答.md を採点(紙面=キー突合。ラボは要 CML)
  close  [--pack-id P]      ラボを撤収(要 CML)

設計の要点(問題パック設計メモ = problems/_drafts/QUIZ-PACK.design.md):
  - 正解キー(answers/)は packs/ 配下へ一切コピーしない(render_html.py が二重に拒否)。
  - 夜間バッチなので所要時間は最適化しない。**各フェーズの完成判定**に全振りする
    (紙面が要求数に満たなければ別 seed で自動リトライ、等)。
  - ラボ2問は同時起動。台数合計 + 稼働中リース ≤ budget を選定時に検査する。
"""

import argparse
import datetime
import glob
import json
import os
import random
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_html                                    # noqa: E402
import quota                                          # noqa: E402  (BL-114 ノルマ記録)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = "packs"
RETRY_MAX = 3          # 紙面生成のリトライ上限(夜間バッチなので厚めに取る)

# --------------------------------------------------------------------------
# 夜間バッチ v2 の枠組み(2026-08-09 ユーザ決定・design.md §6.5)
# --------------------------------------------------------------------------
# 紙面の必須ジャンル: 該当 shape を1問ずつ専用に生成し、残りを mixed で埋める。
# (--shape mixed はジャンルを保証しないため、必須枠は個別生成でしか担保できない)
PAPER_GENRES = {
    "redist": ["chain", "ring", "mploop", "riploop", "leakmap", "v6redist"],
    "aaa": ["aaa"],
    "acl": ["acl", "aclv6"],       # IPv4/IPv6 の ACL 紙面(2026-08-11 追加)
    # BGP 紙面(BL-124・2026-08-16 追加): mixed の抽選だけでは BGP ゼロの
    # パックが出るため必須枠にする(BL-100/111 の「BGP 最優先」方針)。
    "bgp": ["bgpbest", "bgpdbg"],
}

# 紙面の問題数を `auto` にしたときの範囲(ユーザ指示 2026-08-11: 10〜20問で適当に)
PAPER_AUTO_MIN, PAPER_AUTO_MAX = 10, 20

# ラボの固定ジャンル: この中から2つ選ぶ(+余裕があれば通常TSプールから1問)。
# H型は EIGRP版/OSPF版をまとめて1ジャンル扱い(同時に2本入れると盤面がほぼ同じ)。
LAB_GENRES = {
    "hvrf": {"label": "H型VRF",
             # ★EIGRP 優先(ユーザ指示)。直近に出ていれば OSPF 版へ回す。
             "prefixes": ["PVT-EGVRFH", "PVT-OSVRFH"], "tags": ["vrf", "hvrf"]},
    "dhcp": {"label": "DHCP TS",
             "prefixes": ["GEN-DHCPTS"], "tags": ["dhcp"]},
    "dmvpn": {"label": "DMVPN TS",
              "prefixes": ["GEN-DMVPN"], "tags": ["dmvpn", "tunnel"]},
    # ★再配送系(2026-08-16 追加)。GEN-RDFIELD は shape 抽選型の統一生成器で、
    #   1 つの ID から chain/twoborder/ring の 3 形が出る(ID から型が割れない)。
    "redist": {"label": "再配送フィールド",
               "prefixes": ["GEN-RDFIELD"], "tags": ["redistribution", "igp"]},
    # ★再配送をもう1問取れるようにする枠(同一ジャンルは1問しか選ばれないため、
    #   別ジャンル名として立てる)。多点相互再配送のループTS(BL-058)。
    "redistmp": {"label": "多点相互再配送ループTS",
                 "prefixes": ["GEN-REDISTMP"], "tags": ["redistribution", "igp"]},
    # ★bgp / l2 枠(2026-08-18 追加)= ノルマのジャンル分散で埋まりにくかった2つ。
    #   bgp= リングBGP(1つのIDから5形が出る統一生成器・4 IOL・実機11サイクル済)。
    #   l2= EtherChannel 等の L2 TS。★IOSvL2 を使うので Vlan999 SVI の
    #      shut/no shut が要る場合がある(CATALOG 備考)・採点は telnet 経路。
    "bgp": {"label": "リングBGP TS",
            "prefixes": ["GEN-BGPRING"], "tags": ["bgp"]},
    "l2": {"label": "L2(EtherChannel)TS",
           "prefixes": ["GEN-L2TS"], "tags": ["l2", "etherchannel"]},
    # ★services 枠(2026-08-22 追加・BL-134)= IP SLA/track TS。ENARSI は TS 傾向という
    #   ユーザ方針で新設。4 IOL と軽く台数予算に優しい。★既定 --lab-genres にも
    #   参加(2026-08-22 ユーザ指示・hvrf/dhcp/dmvpn と同格の抽選)。
    "ipsla": {"label": "IP SLA/track TS",
              "prefixes": ["GEN-IPSLATS"], "tags": ["ip-sla", "track"]},
}


# ==========================================================================
# 台帳の読み取り(CATALOG / _history / MGMT リース)
# ==========================================================================
def _rows(md_text, section_pred):
    """Markdown の表を (見出し, セル列) で列挙する。"""
    sec = ""
    for line in md_text.splitlines():
        if line.startswith("#"):
            sec = line.lstrip("# ").strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        if cells[0] in ("ID", "生成器 (topologies/)", "出題日", "時期"):
            continue
        if section_pred(sec):
            yield sec, cells


def parse_catalog(repo=REPO):
    """CATALOG.md(＋private/CATALOG.md)→ 出題候補の辞書。

    ★private も読む: H型 VRF(PVT-EGVRFH / PVT-OSVRFH)は非公開側にしか無く、
      公開カタログだけ見ていると固定ジャンルが成立しない(CLAUDE.md の台帳分離)。
    """
    out = {"normal": [], "auto": [], "special": [], "gen": [], "generator": []}
    texts = []
    for rel in ("problems/CATALOG.md", "private/CATALOG.md"):
        path = os.path.join(repo, rel)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                texts.append((rel.startswith("private"), fh.read()))
    for is_pvt, text in texts:
        _parse_catalog_text(text, out, is_pvt)
    return out


def _parse_catalog_text(text, out, is_pvt=False):
    for sec, c in _rows(text, lambda s: True):
        try:
            if sec in ("ENCOR 系", "ENARSI 系"):
                out["normal"].append(_item(c, kind="normal"))
            elif sec.startswith("自動化ラボ"):
                out["auto"].append(_item(c, kind="auto"))
            elif sec.startswith("生成済み GEN インスタンス"):
                out["gen"].append(_item(c, kind="gen"))
            elif sec.startswith("特殊ラボ"):
                out["special"].append({
                    "id": c[0], "diff": _int(c[1]), "tags": _tags(c[2]),
                    "nodes": _int(c[3]), "ops": c[4].strip("`"),
                    "note": c[5] if len(c) > 5 else "", "kind": "special",
                })
            elif sec.startswith("生成器一覧") or (is_pvt and sec == "生成器"):
                out["generator"].append({
                    "script": _script_of(c[0]) or c[0].strip("`"),
                    "prefix": _prefix_of(c[1]),
                    "desc": c[2], "note": c[3] if len(c) > 3 else "",
                    "diff": _diff_from_text(c[2] + " " + (c[3] if len(c) > 3 else "")),
                    "kind": "generator", "pvt": is_pvt,
                })
            elif is_pvt and sec == "問題":
                out["normal"].append(dict(_item(c, kind="normal"), pvt=True))
        except (IndexError, ValueError):
            continue


def _item(c, kind):
    return {"id": c[0], "diff": _int(c[1]), "tags": _tags(c[2]), "nodes": _int(c[3]),
            "access": c[4] if len(c) > 4 else "", "variant": c[5] if len(c) > 5 else "",
            "note": c[6] if len(c) > 6 else "", "kind": kind}


def _int(s):
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else 0


def _tags(s):
    return [t.strip() for t in (s or "").split(",") if t.strip()]


# ★純粋な Cisco 問題以外は既定で選定しない(2026-08-08 ユーザ指示)。
# 「設定作業の主対象が Cisco 機でないもの」= 他ベンダ機・Linux サーバ構築系。
# CCNP の試験対策として想定外の分野が混ざるのを防ぐ(--allow-non-cisco で解除)。
NON_CISCO_PREFIX = ("FGT-", "JUNOS", "CLAB-")
NON_CISCO_FAMILY = {
    "GEN-RADIUS",     # FreeRADIUS(Linux)構築
    "GEN-DNSDHCP",    # BIND9 + ISC DHCP(Linux)構築
    "GEN-DNSTS",      # 同 TS
    "GEN-ZBXBUILD",   # Zabbix(Linux)構築
}
NON_CISCO_TAGS = {"junos", "multivendor", "bind9", "dns", "sdwan",
                  "firewall-policy", "address-object", "asa-config-reading"}

# 自動化(Ansible/RESTCONF/NETCONF)も既定で除外(2026-08-08 ユーザ指示)。
# 対象機は Cisco だが、試験のシムレットでは解答を要求されないため。
AUTOMATION_PREFIX = ("ANSIBLE-", "NETAUTO-")
AUTOMATION_TAGS = {"automation", "ansible", "restconf", "netconf", "python"}

# TS(トラブルシュート)判定。ユーザ方針=「Cisco の TS 中心」(2026-08-08)。
# 生成器はスクリプト名(…ts.py / troubleshoot)と説明文、静的問題は ID とタグで見る。
TS_DESC_WORDS = ("TS", "トラブル", "故障", "ループ", "障害")
DEFAULT_NODES = 6      # 台数が読めない生成器の保守的な見積り(予算検査用)

# 既存インスタンスが無い生成器の分野タグを説明文から起こす。
# ★これが無いと説明文がまるごと1タグになり、分野重複チェックを素通りして
#   同じ生成器が毎回選ばれる(2026-08-08 に実際そうなった)。
TAG_KEYWORDS = {
    "bgp": ("BGP",), "ospf": ("OSPF",), "eigrp": ("EIGRP",),
    "rip": ("RIP",), "isis": ("IS-IS",),
    "redistribution": ("再配送",), "mpls": ("MPLS", "L3VPN"),
    "vrf": ("VRF",), "dmvpn": ("DMVPN",), "ipsec": ("IPsec", "IKE"),
    "dhcp": ("DHCP",), "netflow": ("NetFlow", "FNF"), "snmp": ("SNMP",),
    "l2": ("L2", "EtherChannel", "STP", "VLAN"),
    "acl": ("ACL", "uRPF"), "pbr": ("PBR",), "qos": ("QoS",),
    "ipv6": ("IPv6", "v6"), "igp": ("IGP",), "aaa": ("AAA", "RADIUS"),
}


# 分野重複の判定から外すメタタグ。★これを混ぜると「troubleshooting」が共通するだけで
# 他の TS 問題が全て弾かれ、選定が1種類に固定される(2026-08-08 に実際そうなった)。
META_TAGS = {"troubleshooting", "generated", "multivendor", "security"}


def _topic(cand):
    """分野重複の判定に使うタグ集合(メタタグを除いたもの)。"""
    return set(cand.get("tags", [])) - META_TAGS


def _tags_from_text(text):
    """説明文から分野タグを起こす(既存インスタンスが無い生成器用)。"""
    t = text or ""
    return sorted(k for k, words in TAG_KEYWORDS.items()
                  if any(w in t for w in words))


def _prefix_of(cell):
    """生成器一覧の「出題ID接頭」セルから GEN-XXXX を取り出す。

    セルは `GEN-MPLSTS / GEN-MPLSEB` `GEN-EIGRPCX 等` のような書き方が混ざるので、
    最初の GEN-トークンだけを採る(紙面・params 行は None で候補外になる)。
    """
    m = re.search(r"(?:GEN|PVT)-[A-Z0-9]+", cell or "")
    return m.group() if m else None


def _script_of(cell):
    """同じく「生成器」セルから実行可能なスクリプト名を1つ取り出す。"""
    # ★pvt_ 接頭を落とさないこと(PVT系の生成器名は pvt_gen_*.py)
    m = re.search(r"(?:pvt_)?gen_[a-z0-9_]+\.py", cell or "")
    return m.group() if m else None


def _nodes_from_text(text):
    """説明文から台数を読む(既存インスタンスが無い生成器のため)。

    「4 IOL」「3〜8台」「5台」等。範囲は上限を採る(予算検査は安全側に倒す)。
    """
    m = re.search(r"(\d+)\s*[〜~-]\s*(\d+)\s*(?:台|ノード)", text or "")
    if m:
        return int(m.group(2))
    m = re.search(r"(\d+)\s*[台]|(\d+)\s*ノード", text or "")
    if m:
        return int(m.group(1) or m.group(2))
    m = re.search(r"(\d+)\s*(?:IOL|IOSv|IOS|IOLL2)", text or "")
    return int(m.group(1)) if m else None


def _automation(cand):
    """自動化ラボ(Ansible/RESTCONF)か。既定で選定対象外。"""
    pid = cand["id"]
    if pid.startswith(AUTOMATION_PREFIX) or "-AUTO-" in pid:
        return True
    return bool(set(cand.get("tags", [])) & AUTOMATION_TAGS)


def _is_ts(cand):
    """トラブルシュート問題か(構築問・ドリルと区別する)。"""
    if cand.get("source") == "generator":
        script = cand.get("script", "")
        if script.endswith("ts.py") or "troubleshoot" in script:
            return True
        blob = (cand.get("desc", "") or "") + " " + (cand.get("note", "") or "")
        return any(w in blob for w in TS_DESC_WORDS)
    pid = cand["id"]
    return "-TS" in pid or "troubleshooting" in cand.get("tags", [])


def _non_cisco(cand):
    """設定対象が Cisco 機でない問題か(既定で選定対象外)。"""
    pid = cand["id"]
    if pid.startswith(NON_CISCO_PREFIX) or family(pid) in NON_CISCO_FAMILY:
        return True
    return bool(set(cand.get("tags", [])) & NON_CISCO_TAGS)


def _deprecated(note):
    """CATALOG が「後継がある/通常は使わない」と書いている生成器を弾く。"""
    return bool(re.search(r"新規出題はそちら推奨|通常出題は .* を推奨|"
                          r"したい時のみ", note or ""))


def _diff_from_text(s):
    m = re.search(r"難\s*(\d)(?:\s*[-〜~]\s*(\d))?", s or "")
    if not m:
        return 4
    return int(m.group(2) or m.group(1))


def parse_history(repo=REPO):
    """_history.md(＋private)→ [(日付, 問題ID)]。重複出題の回避に使う。"""
    hist = []
    for rel in ("problems/_history.md", "private/_history.md"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.startswith("|"):
                    continue
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) < 2 or not re.match(r"^\d{4}-\d{2}-\d{2}$", c[0]):
                    continue
                pid = re.split(r"[ (]", c[1].replace("紙面 ", ""))[0]
                if pid:
                    hist.append((c[0], pid))
    return hist


def family(pid):
    """GEN-DMVPN-31010 → GEN-DMVPN(生成器ファミリ)。静的問題はそのまま。"""
    m = re.match(r"^((?:GEN|PVT)-[A-Z0-9]+)-\d+$", pid)
    return m.group(1) if m else pid


def cml_started_nodes(repo=REPO, timeout=20):
    """★CML に実際に起動しているノード数を数える(読み取りのみ)。

    リース台帳(mgmt_leases.json)はこのリポが建てたラボしか知らないため、
    ユーザの手組みラボや停止済みラボを取り違える。2026-08-08 の実機で
    「台帳 8 ノード / 実際は 27 ノード起動」→ CML が
    `20 of 20 node licenses are in use` で provision 失敗した。
    予算検査は必ず**実機の実態**を使う。到達不能なら None を返し、呼び元は
    台帳へフォールバックする。
    """
    import json as _json
    import ssl
    import urllib.request
    try:
        import yaml
        loc = yaml.safe_load(open(os.path.join(repo, "group_vars/all/local.yml"),
                                  encoding="utf-8"))
        host, user = loc["cml_host"], loc["cml_username"]
        pw = loc["cml_password"]
    except Exception:
        return None, {}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    base = f"https://{host}/api/v0"

    def api(method, path, token=None, body=None):
        req = urllib.request.Request(base + path, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        data = _json.dumps(body).encode() if body is not None else None
        with urllib.request.urlopen(req, data, context=ctx, timeout=timeout) as r:
            return _json.loads(r.read().decode() or "null")

    try:
        tok = api("POST", "/authenticate",
                  body={"username": user, "password": pw})
        per, total = {}, 0
        for lid in api("GET", "/labs", tok):
            d = api("GET", f"/labs/{lid}", tok)
            if d.get("state") != "STARTED":
                continue
            n = len(api("GET", f"/labs/{lid}/nodes", tok))
            per[d.get("lab_title") or lid] = n
            total += n
        return total, per
    except Exception:
        return None, {}


def leased_nodes(repo=REPO):
    """MGMT リース台帳から稼働ノード数を数える(CML 到達不能時のフォールバック)。"""
    path = os.path.join(repo, "topologies", "_state", "mgmt_leases.json")
    if not os.path.exists(path):
        return 0, {}
    with open(path, encoding="utf-8") as fh:
        st = json.load(fh)
    per = {k: len(v.get("nodes", {})) for k, v in st.get("leases", {}).items()}
    return sum(per.values()), per


# ==========================================================================
# ラボ2問の選定
# ==========================================================================
def select_labs(cat, hist, *, count, budget, used, rnd,
                diff_range=(3, 5), repeat_days=90, family_days=21,
                allow_special=False,
                today=None, pin=(), allow_non_cisco=False,
                allow_automation=False, ts_only=True):
    """台数合計・分野重複・出題履歴の制約下でラボ問題を選ぶ。

    返り値: (選定リスト, 理由メモのリスト)。候補が足りなければ短いリストを返す
    (夜間バッチは黙って諦めず、欠落を index に出すため理由も返す)。
    """
    today = today or datetime.date.today()
    # ★重複回避は2段構え(2026-08-08):
    #   - 同一インスタンス(seed まで同じ)は repeat_days(既定90日)出さない
    #   - **生成器ファミリは family_days(既定21日)**。GEN 系は新 seed で盤面も故障も
    #     変わるため、ファミリ単位で90日も封じると候補が枯れる(実際 4種まで減った)
    recent, recent_fam = set(), set()
    for d, pid in hist:
        try:
            age = (today - datetime.date.fromisoformat(d)).days
        except ValueError:
            continue
        if age <= repeat_days:
            recent.add(pid)
        if age <= family_days:
            recent_fam.add(family(pid))

    # GEN 生成器は「新 seed で新インスタンス」= 台数・分野は既存インスタンスから見積る
    # (生成器一覧の表は 内容/軸 が散文で、分野タグとしては使えないため)
    est, gtags = {}, {}
    for g in cat["gen"]:
        fam = family(g["id"])
        est.setdefault(fam, []).append(g["nodes"])
        gtags.setdefault(fam, set()).update(g["tags"])

    cands = []
    for it in cat["normal"] + cat["auto"] + (cat["special"] if allow_special else []):
        cands.append(dict(it, source="static"))
    for g in cat["generator"]:
        if not g["prefix"] or not g["script"].endswith(".py"):
            continue                      # 紙面・params 行など、ラボでないもの
        if _deprecated(g["note"]):
            continue                      # 後継に置き換えられた旧生成器は出さない
        sizes = sorted(est.get(g["prefix"], []))
        if sizes:
            nodes = sizes[len(sizes) // 2]
        else:
            # ★検証 seed を掃除した生成器は既存インスタンスが無い(主力 TS の多く)。
            #   説明文から台数を読み、それも無ければ既定値で見積る。
            nodes = _nodes_from_text(g["desc"] + " " + g["note"]) or DEFAULT_NODES
        cands.append({"id": g["prefix"], "diff": g["diff"],
                      "tags": (sorted(gtags.get(g["prefix"], set()))
                               or _tags_from_text(g["desc"] + " " + g["note"])),
                      "nodes": nodes, "kind": "generator",
                      "script": g["script"], "note": g["note"],
                      "desc": g["desc"], "source": "generator",
                      "star": g["note"].count("★") + g["desc"].count("★")})

    # --lab-id で名指しされたものは制約(履歴・難易度)を素通しで最優先に入れる
    picked_pin, notes = [], []
    for pid in pin:
        hit = [c for c in cands if c["id"] == pid]
        if hit:
            picked_pin.append(hit[0])
            notes.append(f"指定 {pid} を採用({hit[0]['nodes']}台)")
        else:
            notes.append(f"★指定 {pid} は CATALOG に無いので無視した")

    excluded_nc = [c["id"] for c in cands if _non_cisco(c)]
    if not allow_non_cisco:
        cands = [c for c in cands if not _non_cisco(c)]
        if excluded_nc:
            notes.append(f"非Cisco系を {len(set(excluded_nc))} 種 除外"
                         f"(他ベンダ機・Linuxサーバ構築系)")
    excluded_au = [c["id"] for c in cands if _automation(c)]
    if not allow_automation:
        cands = [c for c in cands if not _automation(c)]
        if excluded_au:
            notes.append(f"自動化ラボを {len(set(excluded_au))} 種 除外"
                         f"(シムレットで解答を要求されないため)")
    if ts_only:
        before = len(cands)
        cands = [c for c in cands if _is_ts(c)]
        notes.append(f"TS問題に限定: {before} → {len(cands)} 種")
    pool = [c for c in cands
            if diff_range[0] <= c["diff"] <= diff_range[1]
            and c["id"] not in recent and family(c["id"]) not in recent_fam
            and c["id"] not in {p["id"] for p in picked_pin}]
    notes.append(f"候補 {len(pool)} 件(難{diff_range[0]}-{diff_range[1]}・"
                 f"同一問題は直近{repeat_days}日・生成器ファミリは"
                 f"直近{family_days}日を除外)")
    if not pool and not picked_pin:
        notes.append("★候補ゼロ: --repeat-days を縮めるか難易度レンジを広げる必要あり")
        return [], notes

    rnd.shuffle(pool)
    # 優先順: ①生成器(新 seed = 既出の可能性が無い) ②★は弱いバイアスに留める
    #   (★だけで並べると毎回同じ生成器が選ばれ、顔ぶれが固定化する)
    for c in pool:
        # ★は弱いタイブレークに留める(重くすると候補が少ない時に固定化する)
        c["_w"] = rnd.random() * 4 + min(c.get("star", 0), 3) * 0.4
    pool.sort(key=lambda c: (0 if c["source"] == "generator" else 1, -c["_w"]))

    picked = list(picked_pin[:count])
    tags_used = {t for c in picked for t in _topic(c)}
    total = sum(c["nodes"] for c in picked)
    for c in pool:
        if len(picked) >= count:
            break
        if total + c["nodes"] + used > budget:
            continue
        if tags_used & _topic(c):   # 分野が被る問題は同じパックに入れない
            continue
        picked.append(c)
        tags_used |= _topic(c)
        total += c["nodes"]
    if len(picked) < count:
        notes.append(f"★{count - len(picked)} 問ぶん、台数予算({budget}・"
                     f"稼働中{used})または分野非重複の条件を満たす候補が無かった")
    notes.append(f"選定 {len(picked)} 問・合計 {total} ノード(稼働中 {used} と合わせて "
                 f"{total + used}/{budget})")
    return picked, notes


def resolve_genre(cat, genre, hist, rnd, family_days, today, log=print):
    """固定ジャンル → 実際に使う生成器(接頭辞・スクリプト・台数)を決める。

    H型は **EIGRP 版を優先**し、直近 family_days に出ていれば OSPF 版へ回す
    (ユーザ指示 2026-08-09)。片方しか無ければそれを使う。
    """
    spec = LAB_GENRES.get(genre)
    if not spec:
        return None
    byprefix = {g["prefix"]: g for g in cat["generator"] if g.get("prefix")}
    recent = {family(pid) for d, pid in hist
              if _age(d, today) is not None and _age(d, today) <= family_days}
    cands = [byprefix[p] for p in spec["prefixes"] if p in byprefix]
    if not cands:
        log(f"[選定] ★ジャンル {genre}: 生成器がカタログに見つからない")
        return None
    pick = next((g for g in cands if g["prefix"] not in recent), cands[0])
    if pick is not cands[0]:
        log(f"[選定] {spec['label']}: 優先の {cands[0]['prefix']} は直近"
            f"{family_days}日に出題済 → {pick['prefix']} へ")
    nodes = _nodes_from_text(pick["desc"] + " " + pick["note"]) or DEFAULT_NODES
    return {"id": pick["prefix"], "script": pick["script"], "nodes": nodes,
            "tags": spec["tags"], "diff": pick["diff"], "source": "generator",
            "kind": "generator", "genre": genre, "label": spec["label"],
            "pvt": bool(pick.get("pvt"))}


def resolve_paper_count(spec, rnd):
    """`--paper` の指定を実際の問題数に解決する。

    `auto`(既定)= PAPER_AUTO_MIN〜MAX から抽選 / `12`= 固定 / `8-14`= 範囲から抽選。
    ★毎晩ばらつかせるのが狙い(ユーザ指示 2026-08-11「10〜20問で適当に」)。
    """
    spec = str(spec or "auto").strip()
    if spec in ("auto", ""):
        return rnd.randint(PAPER_AUTO_MIN, PAPER_AUTO_MAX)
    m = re.fullmatch(r"(\d+)\s*[-〜~]\s*(\d+)", spec)
    if m:
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        return rnd.randint(lo, hi)
    if spec.isdigit():
        return int(spec)
    raise SystemExit(f"--paper の指定を解釈できません: {spec}")


def _age(d, today):
    try:
        return (today - datetime.date.fromisoformat(d)).days
    except ValueError:
        return None


def select_genre_labs(cat, hist, *, genres, count, budget, used, rnd,
                      family_days=21, today=None, log=print):
    """固定ジャンルから count 個を選ぶ(台数予算に収まる組合せを探す)。

    ★固定ジャンルは**履歴による重複回避も分野タグ重複チェックも適用しない**。
      毎晩指定する枠なので履歴で弾くと2日目から候補ゼロになるし、H型と他が
      `vrf` 等で衝突して落ちるのも意図に反する(新 seed で盤面と故障は変わる)。
    """
    today = today or datetime.date.today()
    pool = [g for g in genres if g in LAB_GENRES]
    notes = []
    order = pool[:]
    rnd.shuffle(order)
    picked, total = [], 0
    for genre in order:
        if len(picked) >= count:
            break
        lb = resolve_genre(cat, genre, hist, rnd, family_days, today, log=log)
        if lb is None:
            continue
        if total + lb["nodes"] + used > budget:
            notes.append(f"{lb['label']} は台数予算に入らず見送り"
                         f"({lb['nodes']}台・稼働中{used}/{budget})")
            continue
        picked.append(lb)
        total += lb["nodes"]
    got = "・".join(f"{p['label']}({p['id']}/{p['nodes']}台)" for p in picked)
    notes.insert(0, f"固定ジャンル {len(picked)}/{count} 問: {got or '(なし)'}")
    return picked, notes, total


# ==========================================================================
# 紙面3問の調達
# ==========================================================================
WROTE_RE = re.compile(r"wrote questions/(\d{8}-\d+)\.md")


def _run_paper_gen(repo, seed, count, shape, exam, hard, log, label):
    """gen_paper_mcq.py を1回だけ回し、**この実行が書いた**スタンプを返す。

    ★帰属は「生成器の標準出力の `wrote questions/<stamp>.md`」で判定する。
      以前は questions/ のグロブ差分で数えていたが、**並行セッションが同じ時間帯に
      生成した問題を自分の成果として取り込んでしまう**(2026-08-12 に実際に発生:
      別セッションの shape=bgpbest の1問がパックに混入し、こちらの1問が溢れた)。
      作問セッションとパックのセッションは別に動くので、差分での帰属は成立しない。
    """
    cmd = [os.path.join(repo, ".venv/bin/python3"),
           os.path.join(repo, "topologies/gen_paper_mcq.py"),
           "--repo", repo, "--seed", str(seed), "--count", str(count),
           "--shape", shape]
    if exam:
        cmd.append("--exam")
    if hard:
        cmd.append("--hard")
    log(f"[紙面] {label}: shape={shape} count={count} seed={seed}")
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"[紙面] ★生成器が rc={r.returncode} で終了: {(r.stderr or '')[-1500:]}")
    mine = []
    for st in WROTE_RE.findall(r.stdout or ""):
        if st not in mine and os.path.exists(f"{repo}/questions/{st}.md"):
            mine.append(st)
    if not mine and (r.stdout or ""):
        log("[紙面] ★生成器の出力から生成分を特定できず(書式変更の疑い)")
    return mine


def gen_papers(repo, count, seed, shape, exam, hard, log, require=(), rnd=None):
    """紙面を作る。必須ジャンルは個別に、残りは mixed でまとめて生成する。

    ★`--shape mixed` は問題ごとのルーレットでジャンルを保証しない。
      「再配送を1問以上」「AAA を1問以上」は**専用に1回ずつ生成**するしかない。
    ★完成判定: 要求数に満たなければ別 seed でリトライ(生成器は展開失敗時に
      問題数を黙って減らすため、この検査が無いと朝に問題が足りない事故になる)。
    """
    rnd = rnd or random.Random(seed)
    made, got_genre = [], {}
    for gi, genre in enumerate(require):
        shapes = PAPER_GENRES.get(genre)
        if not shapes:
            log(f"[紙面] ★未知のジャンル指定 {genre} は無視")
            continue
        for attempt in range(1, RETRY_MAX + 1):
            sh = rnd.choice(shapes)
            new = _run_paper_gen(repo, seed + 7000 + gi * 100 + attempt, 1, sh,
                                 exam, hard, log, f"必須[{genre}] 試行{attempt}")
            if new:
                made += new
                got_genre[genre] = sh
                log(f"[紙面] 必須[{genre}] 確保: {new[0]} (shape={sh})")
                break
            log(f"[紙面] 必須[{genre}] 試行{attempt} 失敗 → shape を引き直す")
        else:
            log(f"[紙面] ★必須ジャンル {genre} を確保できなかった")

    for attempt in range(1, RETRY_MAX + 1):
        need = count - len(made)
        if need <= 0:
            break
        new = _run_paper_gen(repo, seed + attempt * 1000, need, shape,
                             exam, hard, log, f"残り 試行{attempt}")
        made += new
        log(f"[紙面] 累計 {len(made)}/{count} 問")
    if got_genre:
        log(f"[紙面] 必須ジャンルの充足: {got_genre}")
    return made[:count], got_genre


def run(cmd, repo, log, label, timeout=3600):
    """外部コマンドを回してログに落とす。(rc, stdout) を返す。"""
    log(f"[{label}] $ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        log(f"[{label}] ★タイムアウト({timeout}s)")
        return 124, ""
    out = (r.stdout or "") + (r.stderr or "")
    log(f"[{label}] rc={r.returncode}\n{out[-6000:]}")
    return r.returncode, out


def gen_instance(repo, script, seed, log):
    """GEN 生成器を新 seed で回し、できた problems/<ID> を突き止める。

    生成器の標準出力の書式は生成器ごとに違うため、**problems/ の差分**で特定する
    (文字列パースより頑健)。
    """
    before = set(os.listdir(os.path.join(repo, "problems")))
    cmd = [os.path.join(repo, ".venv/bin/python3"),
           os.path.join(repo, "topologies", script),
           "--repo", repo, "--seed", str(seed)]
    rc, _ = run(cmd, repo, log, "生成器")
    after = set(os.listdir(os.path.join(repo, "problems")))
    new = sorted(n for n in (after - before) if not n.startswith("_"))
    if rc != 0 or not new:
        return None
    if len(new) > 1:
        log(f"[生成器] ★複数の問題が増えた {new} → 先頭を採用(他セッションと競合の疑い)")
    return new[0]


def provision_lab(repo, prob_id, variant, log):
    """lab.sh provision → 作業フォルダ lab/<ID>/問題.md の存在まで確認する。

    ★失敗したら必ず teardown する(2026-08-08 実機): ライセンス上限に当たって
    provision が落ちた時、作りかけのラボが 14 ノード起動したまま残り、放置すれば
    以後の provision が全てライセンス不足で落ちる状態になった。夜間バッチでは
    翌朝までそれが続くため、失敗時の後始末は必須。
    """
    cmd = [os.path.join(repo, "scripts/lab.sh"), "provision", prob_id]
    if variant:
        cmd.append(variant)
    rc, out = run(cmd, repo, log, f"provision {prob_id}")
    task = os.path.join(repo, "lab", prob_id, "問題.md")
    if rc != 0 or not os.path.exists(task):
        why = f"provision 失敗(rc={rc} / 問題.md {os.path.exists(task)})"
        if "node licenses are in use" in out:
            why += " ※CML のノードライセンス上限"
        log(f"[片付け] {prob_id}: 作りかけのラボを撤収する")
        run([os.path.join(repo, "scripts/lab.sh"), "teardown", prob_id],
            repo, log, f"teardown {prob_id}")
        return None, why
    return f"lab/{prob_id}/問題.md", ""


SCORE_RE = re.compile(r"合計:\s*(\d+)\s*/\s*(\d+)\s*点")


def _gen_dir(repo, prob_id):
    return os.path.join(repo, "topologies", "_generated", prob_id)


def _mgmt_map(repo, prob_id):
    """build_topology が書いた mgmt_map.yml(ノード→MGMT IP)。"""
    path = os.path.join(_gen_dir(repo, prob_id), "mgmt_map.yml")
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _iosvl2_nodes(repo, prob_id):
    """生成 lab.yaml から IOSvL2 ノード名を拾う(SVI bounce の対象判定)。"""
    path = os.path.join(_gen_dir(repo, prob_id), "lab.yaml")
    if not os.path.exists(path):
        return []
    import yaml
    with open(path, encoding="utf-8") as fh:
        lab = yaml.safe_load(fh) or {}
    return [n.get("label") or n.get("id")
            for n in (lab.get("nodes") or [])
            if n.get("node_definition") == "iosvl2"]


def _ping(ip, timeout=2):
    return subprocess.run(["ping", "-c", "1", "-W", str(timeout), ip],
                          capture_output=True).returncode == 0


def bringup(repo, prob_id, log, tries=8, wait=15):
    """★起動後の健全化: 朝ユーザが触る時点で全ノードに到達できる状態にする。

    夜間バッチの肝。ここを飛ばすと「朝、ping が永遠に上がらない」事故になる
    (IOSvL2 は起動後 Vlan999 SVI が down 固着する既知の癖がある)。

      1. 全ノードの MGMT へ ping(最大 tries 回・wait 秒間隔)
      2. 落ちているノードが IOSvL2 なら **Vlan999 の shut/no shut** を
         console 経由(fix_console.py)で打ち、再確認する
      3. それでも落ちていればノード名を返す(呼び元が index.html に明示する)

    ※ IF の no shutdown / CVAC 後の bringup は lab_up.yml が problem.yml の
      bringup_data_ifs / bringup_console フラグで既に面倒を見ている。ここは
      その後段の「実際に到達できるか」の検証と、IOSvL2 固有の救済に絞る。
    """
    mgmt = _mgmt_map(repo, prob_id)
    if not mgmt:
        log(f"[bringup] {prob_id}: mgmt_map が無いため到達性検査を省略")
        return []
    ng = []
    for i in range(1, tries + 1):
        ng = [n for n, ip in mgmt.items() if not _ping(ip)]
        if not ng:
            log(f"[bringup] {prob_id}: 全 {len(mgmt)} ノード到達 OK(試行{i})")
            return []
        log(f"[bringup] {prob_id}: 未到達 {ng} (試行{i}/{tries})")
        if i < tries:
            time.sleep(wait)

    l2 = [n for n in ng if n in _iosvl2_nodes(repo, prob_id)]
    if l2:
        log(f"[bringup] {prob_id}: IOSvL2 {l2} に Vlan999 SVI bounce を試みる")
        if _svi_bounce(repo, prob_id, l2, log):
            time.sleep(20)
            ng = [n for n, ip in mgmt.items() if not _ping(ip)]
            log(f"[bringup] {prob_id}: bounce 後の未到達 {ng or '(なし)'}")
    if ng:
        log(f"[bringup] ★{prob_id}: {ng} に到達できないまま(朝の要確認)")
    return ng


def _svi_bounce(repo, prob_id, nodes, log):
    """IOSvL2 の Vlan999 SVI を console 経由で shut/no shut する。

    ★IOSvL2 は起動後に mgmt SVI が down 固着する(CATALOG の固有注意)。
      SSH が上がらないので console 経路(fix_console.py)を使う。
    """
    import tempfile
    lease = os.path.join(repo, "topologies", "_state", "mgmt_leases.json")
    title = ""
    if os.path.exists(lease):
        with open(lease, encoding="utf-8") as fh:
            title = (json.load(fh).get("leases", {})
                     .get(prob_id, {}).get("lab_name", ""))
    if not title:
        log(f"[bringup] {prob_id}: ラボ名が特定できず bounce を断念")
        return False
    fix = {n: {"config": ["interface Vlan999", "shutdown", "no shutdown"]}
           for n in nodes}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(fix, fh, ensure_ascii=False)
        path = fh.name
    try:
        import yaml
        loc = yaml.safe_load(open(os.path.join(repo, "group_vars/all/local.yml"),
                                  encoding="utf-8"))
        env = dict(os.environ, CML_HOST=str(loc["cml_host"]),
                   CML_USER=str(loc["cml_username"]),
                   CML_PASS=str(loc["cml_password"]), LAB_TITLE=title,
                   NODE_USER=os.environ.get("NODE_USER", "SUZUKI"),
                   NODE_PASS=os.environ.get("NODE_PASS", "CCNP"))
        r = subprocess.run([os.path.join(repo, ".venv/bin/python3"),
                            os.path.join(repo, "topologies/fix_console.py"), path],
                           cwd=repo, capture_output=True, text=True,
                           timeout=900, env=env)
        log(f"[bringup] fix_console rc={r.returncode}\n{(r.stdout or '')[-2000:]}")
        return r.returncode == 0
    except Exception as e:                      # noqa: BLE001
        log(f"[bringup] SVI bounce 失敗: {e}")
        return False
    finally:
        os.unlink(path)


def baseline_grade(repo, prob_id, variant, log, settle=180):
    """出題前に採点し、得点が想定レンジかを見る(★朝の事故を防ぐ最後の砦)。

    TS 系が満点で始まる = 故障が入っていない、構築問が高得点で始まる = 課題が無い、
    といった「実は解けてしまう」パックを夜のうちに検出するために使う。

    ★**収束待ちが必須**(2026-08-08 実機E2Eで判明): provision 直後に測ると
    IGP が収束しておらず、仕込んだ故障ではなく収束途中を測ってしまう
    (実測 GEN-REDISTRO-11153: 直後 25/100 → 4分後 65/100)。
    settle 秒待ってから max_attempts=2 で測り、最後の試行の得点を採る。
    夜間バッチなので待ち時間は問題にならない。
    """
    import tempfile
    if settle:
        log(f"[基線] {prob_id}: 収束待ち {settle}s")
        time.sleep(settle)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write("CCNP\n")
        vault = fh.name
    try:
        cmd = [os.path.join(repo, ".venv/bin/ansible-playbook"),
               os.path.join(repo, "playbooks/grade.yml"),
               "-e", f"problem={prob_id}", "-e", "max_attempts=2",
               "--vault-password-file", vault]
        if variant:
            cmd += ["-e", f"variant={variant}"]
        rc, out = run(cmd, repo, log, f"基線採点 {prob_id}", timeout=1800)
    finally:
        os.unlink(vault)
    hits = SCORE_RE.findall(out)
    if not hits:
        return None, None, "得点行を読めず"
    got, total = int(hits[-1][0]), int(hits[-1][1])
    return got, total, ""


def borrow_papers(repo, count, today):
    """--dry-run 用: 既出の紙面を借りる(生成も CML も行わない)。

    ★**出題履歴に載っている中で最も新しいもの**から借りる。理由は2つ:
      - 未出題の問題を下見で見せてしまわない(履歴にある = ユーザは解答済み)。
      - 古い紙面は BL-087(図の可読性を落とす後処理・2026-08-05)より前の生成物で、
        現行の見え方を反映しない = 下見にならない。
    当日分は他セッションが生成中の可能性があるため常に除外する。
    """
    have = set()
    for p in glob.glob(f"{repo}/questions/*.md"):
        st = os.path.basename(p)[:-3]
        m = re.match(r"^(\d{8})-\d+$", st)
        if m and m.group(1) < today.strftime("%Y%m%d"):
            have.add(st)
    seen = [pid for _d, pid in parse_history(repo) if pid in have]
    ordered = sorted(set(seen), reverse=True)          # 出題済のうち新しい順
    if len(ordered) < count:                           # 保険: 履歴に無ければ古い順
        ordered += [s for s in sorted(have) if s not in ordered]
    return ordered[:count]


# ==========================================================================
# 成果物の生成(HTML / 解答用紙 / manifest)
# ==========================================================================
def q_title(no, item):
    kind = "紙面" if item["kind"] == "paper" else "ラボ"
    return f"Q{no} ({kind} {item['ref']})"


def answer_form(pack_id, it, src_path):
    """問題ページ下部に置く解答欄の HTML。

    紙面(選択式)は実在する選択肢だけのラジオ、記述式は自由記述、ラボはメモのみ。
    入力は pack_server.py の API 経由で 解答.md の該当セクションへ書き戻される。
    """
    import html as H
    kind = it["kind"]
    ref = H.escape(str(it.get("ref", "")))
    head = (f'<section class="answer" data-pack="{H.escape(pack_id)}" '
            f'data-no="{it["no"]}" data-kind="{kind}" data-ref="{ref}">'
            f"<h2>解答</h2>")
    if kind == "lab":
        body = ('<label class="row">メモ（任意・実機の設定が解答の本体です）</label>'
                '<textarea class="memo"></textarea>'
                '<label class="done"><input type="checkbox"> 実装完了</label>')
    else:
        letters, pick = [], 1
        if src_path and os.path.exists(src_path):
            with open(src_path, encoding="utf-8") as fh:
                qtext = fh.read()
            letters = render_html.choice_letters(qtext)
            pick = render_html.pick_count(qtext)
        if letters:
            # ★複数選択(「2つを選択してください」)はチェックボックスにする。
            #   ラジオのままだと1つしか選べず**解答不能**になる(2026-08-11 発覚)。
            # ★pick == -1 は数非明示(「すべて選んでください」= BL-125 allthat)。
            #   チェックボックスにするが、個数のヒントは出さない(数非明示が主題)。
            typ = "radio" if pick == 1 else "checkbox"
            opts = "".join(
                f'<label><input type="{typ}" name="ans{it["no"]}" '
                f'value="{l}">{l}</label>' for l in letters)
            hint = ("" if pick == 1 else
                    '<label class="row">該当するものを<b>すべて選択</b>して'
                    'ください(数は示されていません)</label>' if pick == -1 else
                    f'<label class="row">この問題は <b>{pick}つ選択</b>です</label>')
            ansfield = f'{hint}<div class="opts">{opts}</div>'
        else:                       # 記述式(選択肢なし)
            ansfield = ('<label class="row">解答</label>'
                        '<textarea class="ans"></textarea>')
        body = (ansfield +
                '<label class="row">根拠（任意）</label>'
                '<textarea class="why"></textarea>'
                '<label class="done"><input type="checkbox"> 解答済</label>')
    return head + body + '<div class="savemsg"></div></section>'


def build_nav(items, cur_no):
    nav = [{"label": "目次", "href": "index.html"}]
    for it in items:
        n = it["no"]
        nav.append({"label": f"Q{n}", "href": f"q{n}.html", "current": n == cur_no})
    return nav


def write_pages(repo, pdir, items, mermaid_js, mermaid_mode="cdn", pack_id=""):
    """各問の HTML を書く。入力は questions/ と lab/ に限る(answers/ は読まない)。"""
    written = []
    for it in items:
        src = os.path.join(repo, it["src"]) if it.get("src") else ""
        out = os.path.join(pdir, f"q{it['no']}.html")
        if not src or not os.path.exists(src):
            body = (f"# {q_title(it['no'], it)}\n\n"
                    f"> ★この問題は準備に失敗しました（{it.get('error', '理由不明')}）。\n"
                    f"> 出題者（Claude）に伝えてください。\n")
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(render_html.render(body, title=q_title(it["no"], it),
                                            nav=build_nav(items, it["no"]),
                                            mermaid_mode=mermaid_mode,
                                            answer_form=answer_form(pack_id, it, "")))
        else:
            meta = ("機器に接続して解く問題です。作業フォルダ: lab/%s/" % it["ref"]
                    if it["kind"] == "lab" else
                    "机上問題。機器には接続せず、示された出力だけで解答してください。")
            render_html.render_file(src, out, title=q_title(it["no"], it),
                                    nav=build_nav(items, it["no"]), meta=meta,
                                    mermaid_js=mermaid_js,
                                    mermaid_mode=mermaid_mode,
                                    answer_form=answer_form(pack_id, it, src))
        written.append(out)
    return written


def index_md(pack_id, items, notes, dry_run):
    est = {"paper": 8, "lab": 60}     # 紙面は1問8分・ラボは1問60分の目安
    total = sum(est[it["kind"]] for it in items)
    lines = [f"# {pack_id} — 問題パック", ""]
    if dry_run:
        lines += ["> ★これは **--dry-run のプレビュー**です。紙面は既出のものを借りて",
                  "> 体裁を確認するためのもので、ラボは構築されていません。", ""]
    # dry-run で「ラボ未構築」は想定どおりなので警告しない(本番の失敗だけを目立たせる)
    broken = [it for it in items if not it.get("src")
              and not (dry_run and it["kind"] == "lab")]
    if broken:
        lines += ["> ★**準備できなかった問題があります**: " +
                  ", ".join(f"Q{it['no']}" for it in broken),
                  "> 出題者（Claude）に伝えてください。", ""]
    lines += [f"全 {len(items)} 問 / 目安 約 {total // 60} 時間{total % 60}分。"
              "解答は `解答.md` に書き込んでください。", "",
              "| # | 種別 | 問題 | 目安 | 解き方 |",
              "|---|------|------|------|--------|"]
    for it in items:
        if it["kind"] == "paper":
            how = "機器に接続しない（示された出力だけで解答）"
        else:
            how = f"CML コンソールで解く（作業フォルダ `lab/{it['ref']}/`）"
        lines.append(f"| [Q{it['no']}](q{it['no']}.html) | "
                     f"{'紙面' if it['kind'] == 'paper' else 'ラボ'} | "
                     f"`{it['ref']}` | {est[it['kind']]}分 | {how} |")
    lines += ["", "## 進め方", "",
              "1. 上の表から各問を開く（順不同）。",
              "2. **各ページの下にある解答欄に書き込む**（自動で `解答.md` に保存される）。"
              "ラボ問題は**実機の設定が本体**なので、状態を `実装完了` にするだけでよい。",
              "3. 全部終わったら「採点して」と伝える。", "",
              "※ 解答欄が「保存できません」と出る場合は `scripts/pack.sh serve` 経由で"
              "開いていない。`解答.md` を直接編集しても同じことができる。", "",
              "## この回の構成メモ", ""]
    lines += [f"- {n}" for n in notes]
    return "\n".join(lines) + "\n"


def sheet_section(it):
    """解答用紙の1問ぶん(見出し＋記入欄)。新規作成と差し替えで同じ書式を使う。"""
    kind = "紙面" if it["kind"] == "paper" else "ラボ"
    lines = [f"## Q{it['no']} ({kind} {it['ref']})   状態: [ ] 未着手", ""]
    lines += ["解答: ", "根拠: ", ""] if it["kind"] == "paper" else ["メモ: ", ""]
    return "\n".join(lines)


def answer_sheet_md(pack_id, items):
    lines = [f"# 解答用紙 — {pack_id}", "",
             "各問の `状態:` を `[x]` に変え、解答を書いてください。",
             "紙面は記号（記述式の問はそのまま文章で）、ラボは実機の設定が本体なので",
             "状態だけで構いません。", ""]
    for it in items:
        lines.append(sheet_section(it))
    return "\n".join(lines) + "\n"


def reset_sheet_section(pdir, item):
    """差し替えた問の解答欄を新しい問題IDで作り直す(他の問には触れない)。"""
    path = os.path.join(pdir, "解答.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out, cur_no, skipped = [], None, False
    for line in text.split("\n"):
        m = HDR.match(line)
        if m:
            cur_no = int(m.group(1))
            if cur_no == item["no"]:
                out.append(sheet_section(item).rstrip("\n"))
                skipped = True
                continue
        if cur_no == item["no"] and skipped:
            continue                       # 旧セクションの本文は捨てる
        out.append(line)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip("\n") + "\n")


def write_manifest(pdir, manifest):
    """依存を増やさないため YAML は手書きで出す(読むのは Python 側と人)。"""
    def esc(v):
        s = str(v)
        return f'"{s}"' if re.search(r'[:#\[\]{}]|^\s|\s$', s) or s == "" else s

    lines = [f"pack_id: {manifest['pack_id']}",
             f"created: {manifest['created']}",
             f"dry_run: {str(manifest['dry_run']).lower()}",
             f"seed: {manifest['seed']}",
             "items:"]
    for it in manifest["items"]:
        lines.append(f"  - no: {it['no']}")
        for k in ("kind", "ref", "src", "key", "form", "variant", "nodes",
                  "state", "ops", "error", "warn"):
            if it.get(k) not in (None, ""):
                lines.append(f"    {k}: {esc(it[k])}")
    lines += ["notes:"] + [f"  - {esc(n)}" for n in manifest["notes"]]
    with open(os.path.join(pdir, "manifest.yml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def read_manifest(pdir):
    """write_manifest が書いた素朴な YAML を読み戻す(PyYAML に依存しない)。"""
    path = os.path.join(pdir, "manifest.yml")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    man = {"items": [], "notes": []}
    cur, mode = None, None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("items:"):
            mode = "items"
            continue
        if line.startswith("notes:"):
            mode = "notes"
            continue
        if mode is None:
            k, _, v = line.partition(":")
            man[k.strip()] = v.strip()
        elif mode == "items":
            if line.startswith("  - "):
                cur = {}
                man["items"].append(cur)
                k, _, v = line[4:].partition(":")
                cur[k.strip()] = v.strip()
            else:
                k, _, v = line.strip().partition(":")
                cur[k.strip()] = v.strip().strip('"')
        elif mode == "notes":
            man["notes"].append(line.strip()[2:].strip('"'))
    for it in man["items"]:
        it["no"] = int(it["no"])
    return man


# ==========================================================================
# 解答用紙のパース・採点
# ==========================================================================
HDR = re.compile(r"^##\s+Q(\d+)\s*[（(]\s*(紙面|ラボ)\s+([^）)]+)[）)]\s*(.*)$")


def parse_answer_sheet(path):
    """解答.md → {no: {ref, kind, done, answer, body}}。書式の自由度は残す。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out, cur = {}, None
    for line in text.splitlines():
        m = HDR.match(line)
        if m:
            cur = {"no": int(m.group(1)),
                   "kind": "paper" if m.group(2) == "紙面" else "lab",
                   "ref": m.group(3).strip(), "head": m.group(4), "lines": []}
            out[cur["no"]] = cur
            continue
        if cur is not None:
            cur["lines"].append(line)
    for it in out.values():
        blob = it["head"] + "\n" + "\n".join(it["lines"])
        it["done"] = bool(re.search(r"状態:\s*\[[xX]\]", blob))
        # ★ \s は改行も食うため [ \t] で止める(空欄の「解答:」が次行を拾う事故を防ぐ)
        m = re.search(r"^[ \t]*解答:[ \t]*(.*)$", blob, re.M)
        it["answer"] = (m.group(1).strip() if m else "")
        it["body"] = blob.strip()
    return out


def choice_of(text):
    """解答欄の記入から選択記号を取り出す。`**B**` / `b` / 全角`Ｂ` / 「B. …」に対応。

    ★複数選択(「2つを選択」の形)にも対応する。`BD` / `B,D` / `B・D` / `B と D`
      のいずれでも拾い、**現れた順ではなく整列した文字列**を返す(比較を安定させる)。
      2026-08-09 に authread 形(複数正解)を追加した際、単一記号しか読めず
      **無言で採点不能**になっていたのを修正。
    """
    if not text:
        return ""
    z = text.translate({ord(c): ord(c) - 0xFEE0
                        for c in "ＡＢＣＤＥＦＧＨＩＪａｂｃｄｅｆｇｈｉｊ"})
    # 「B. 選択肢の本文」のような記入で本文中の英字を拾わないよう、
    # 行頭・区切り直後の記号だけを対象にする。
    # ①「BD」「B,D」「B・D」「B と D」のような**記号だけの記入**は、区切りを
    #   取り除いて全文字が A-F なら全部を解答とみなす。
    core = re.sub(r"[\s*,、・/|]|と", "", z)
    if core and len(core) <= 4 and re.fullmatch(r"[A-Ja-j]+", core):
        got = list(core)
    else:
        # ②「B. 選択肢の本文…」のような記入は、**本文中の英字を拾わない**よう
        #   前後が英数字でない 1 文字だけを対象にする。
        got = re.findall(r"(?<![A-Za-z0-9])([A-Ja-j])(?![A-Za-z0-9])", z)
        if not got:
            m = re.search(r"[A-Ja-j]", z)
            got = [m.group()] if m else []
    seen = []
    for c in got:
        c = c.upper()
        if c not in seen:
            seen.append(c)
    return "".join(sorted(seen))


def fmt_letters(s):
    """choice_of/key_of の整列済み記号列を表示用に(複数選択は中黒区切り)。"""
    return "・".join(s) if s else ""


def key_of(repo, ref):
    """answers/<ref>.md から正解記号を読む。記述式なら None。

    ★この関数の戻り値は採点結果の表示にしか使わない。キー本文は packs/ に書かない。
    """
    path = os.path.join(repo, "answers", f"{ref}.md")
    if not os.path.exists(path):
        return None, "キー無し"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "ルーブリック" in text:
        return None, "記述式(ルーブリック採点)"
    # ★複数正解(`**B・D**`)にも対応。整列した記号列で返す(choice_of と同じ形)。
    # ★記号の範囲は A-J(2026-08-11): 8択の問題が実在し、`**H**` を読めず
    #   「正解記号を読めず」で無言の採点不能になっていた(実データ3件で発覚)。
    pat = r"([A-J](?:\s*[・,]\s*[A-J])*)"
    m = re.search(r"^##\s*正解\s*$\s*\n+\s*\*\*" + pat + r"\*\*", text, re.M)
    if not m:
        m = re.search(r"^\s*\*\*" + pat + r"\*\*\s*$", text, re.M)
    if not m:
        return None, "正解記号を読めず"
    return "".join(sorted(re.findall(r"[A-J]", m.group(1)))), ""


# ==========================================================================
# 出題履歴(_history.md)の更新
# ==========================================================================
HIST_HEAD = "|--------|----------------------|----|------|------|------|"


def history_upsert(repo, ref, *, diff="", state="出題中", score="-", memo="",
                   paper=False, date=None, log=print):
    """_history.md の該当行を更新、無ければ表の先頭に追記する。

    ★台帳は他セッションも編集するため、読み→書きの間隔を最短にし、
      既存行の書式(列数)は壊さない。ID が一致する最初の行だけを触る。
    """
    # ★PVT系の行は公開台帳に書かない(CLAUDE.md の台帳分離)
    rel = ("private/_history.md" if str(ref).startswith("PVT-")
           else "problems/_history.md")
    path = os.path.join(repo, rel)
    if not os.path.exists(path):
        return False
    date = date or datetime.date.today().isoformat()
    label = f"紙面 {ref}" if paper else ref
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("|") and re.search(rf"\|\s*(紙面 )?{re.escape(ref)}\b",
                                              line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 6:
                c[3] = state
                if score != "-":
                    c[4] = str(score)
                # ★既存メモは絶対に上書きしない(学習記録の本体。Claude が採点後
                #   レビューで書き込む欄で、自動生成の定型文で潰してはいけない)。
                if memo and c[5] in ("", "-"):
                    c[5] = memo
                lines[i] = "| " + " | ".join(c) + " |"
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(lines))
                log(f"[履歴] 更新: {label} → {state} {score}")
                return True
    for i, line in enumerate(lines):
        if line.startswith(HIST_HEAD[:10]) and "----" in line:
            row = (f"| {date} | {label} | {diff or '-'} | {state} | {score} | "
                   f"{memo} |")
            lines.insert(i + 1, row)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            log(f"[履歴] 追記: {label} ({state})")
            return True
    return False


# ==========================================================================
# 採点レポート(report.html)
# ==========================================================================
def build_report(repo, pack_id, pdir, man, rows, lab_rows):
    """採点結果を1枚の HTML にまとめる(パックの成績表)。

    ★未解答の問題については正解を書かない(まだ解ける状態を壊さないため)。
    """
    md = [f"# {pack_id} — 採点結果", "",
          f"作成日: {man.get('created', '')} / 採点日: "
          f"{datetime.date.today().isoformat()}", "",
          "## 成績", "",
          "| # | 種別 | 問題 | 解答 | 正解 | 判定 |",
          "|---|------|------|------|------|------|"]
    for no, kind, ref, given, key, note in rows:
        md.append(f"| Q{no} | {kind} | `{ref}` | {given} | {key} | {note} |")
    if lab_rows:
        md += ["", "## ラボの採点", "",
               "| # | 問題 | 得点 | 未充足のチェック |",
               "|---|------|------|------------------|"]
        for no, ref, got, total, fails in lab_rows:
            f = "<br>".join(fails) if fails else "（なし・全 PASS）"
            md.append(f"| Q{no} | `{ref}` | **{got}/{total}** | {f} |")
    md += ["", "## 解説", ""]
    for no, kind, ref, given, key, note in rows:
        if kind != "紙面" or key in ("-", ""):
            continue                       # 未解答・記述式はここに出さない(正解を伏せる)
        md += [f"### Q{no} `{ref}` — 正解 {key}（あなたの解答 {given}）", ""]
        md += [explain_of(repo, ref), ""]
    return "\n".join(md) + "\n"


def explain_of(repo, ref):
    """answers/<ref>.md から選択肢の判定だけを取り出す(仕込みの種別は出さない)。"""
    path = os.path.join(repo, "answers", f"{ref}.md")
    if not os.path.exists(path):
        return "（解説なし）"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^## 各選択肢の判定\s*$(.*?)^## ", text, re.M | re.S)
    body = m.group(1).strip() if m else ""
    m2 = re.search(r"^## 教育核心\s*$(.*?)(^## |\Z)", text, re.M | re.S)
    core = m2.group(1).strip() if m2 else ""
    out = body
    if core:
        out += "\n\n**この分野の核心**\n\n" + core
    return out or "（解説なし）"


# ==========================================================================
# サブコマンド
# ==========================================================================
def pack_dir(repo, pack_id):
    return os.path.join(repo, PACKS, pack_id)


def default_pack_id(repo, today):
    base = f"PACK-{today.strftime('%Y%m%d')}"
    if not os.path.exists(pack_dir(repo, base)):
        return base
    for suf in "BCDEFGH":
        cand = f"{base}-{suf}"
        if not os.path.exists(pack_dir(repo, cand)):
            return cand
    return base + "-Z"


def latest_pack(repo):
    dirs = sorted(glob.glob(os.path.join(repo, PACKS, "PACK-*")))
    if not dirs:
        sys.exit("パックがありません(先に new を実行)")
    return os.path.basename(dirs[-1])


def cmd_new(a):
    repo = os.path.abspath(a.repo)
    today = datetime.date.today()
    pack_id = a.pack_id or default_pack_id(repo, today)
    pdir = pack_dir(repo, pack_id)
    os.makedirs(pdir, exist_ok=True)
    # ★ビルドログは packs/ に置かない: 生成器の標準出力には故障種・shape が出るため、
    #   ユーザが開くフォルダに置くと解答前に目に入る。リポ側の _state/ に隔離する。
    logdir = os.path.join(repo, "topologies", "_state")
    os.makedirs(logdir, exist_ok=True)
    logpath = os.path.join(logdir, f"pack-{pack_id}.log")
    logf = open(logpath, "a", encoding="utf-8")

    def log(msg):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        for line in str(msg).rstrip("\n").splitlines() or [""]:
            print(f"{stamp} {line}", flush=True)
            logf.write(f"{stamp} {line}\n")
        logf.flush()

    seed = a.seed if a.seed is not None else random.randrange(1, 10 ** 9)
    rnd = random.Random(seed)
    log(f"===== {pack_id} 生成開始 (seed={seed}, dry_run={a.dry_run}) =====")

    used, per = cml_started_nodes(repo)
    if used is None:
        used, per = leased_nodes(repo)
        log(f"[台数] ★CML に問い合わせできず、リース台帳で代用: {used} ノード")
    log(f"[台数] CML 起動中 {used} ノード {per or '(なし)'} / 予算 {a.budget}")

    # --- 紙面フェーズ ---
    require = [g.strip() for g in (a.require_shape or "").split(",") if g.strip()]
    n_paper = resolve_paper_count(a.paper, rnd)
    log(f"[紙面] 問題数: {n_paper} 問(指定={a.paper}) / 必須ジャンル {require or '(なし)'}")
    if a.dry_run:
        stamps = borrow_papers(repo, n_paper, today)
        log(f"[紙面] dry-run: 既出の紙面を {len(stamps)} 問借用"
            f"(必須ジャンルの個別生成は実生成時のみ)")
    elif n_paper <= 0:
        # ★BL-133: 0問指定でも必須ジャンル確保ループが走り、パック未収載の
        #   孤児 questions/answers が残っていた → 紙面フェーズごとスキップ
        stamps = []
        log("[紙面] 0問指定のため紙面フェーズをスキップ(必須ジャンルも生成しない)")
    else:
        stamps, _got = gen_papers(repo, n_paper, seed, a.shape, a.exam, a.hard,
                                  log, require=require, rnd=rnd)
    if len(stamps) < n_paper:
        log(f"[紙面] ★不足: {len(stamps)}/{n_paper} 問しか用意できなかった")

    items, no = [], 0
    for st in stamps:
        no += 1
        src = f"questions/{st}.md"          # manifest には repo 相対で持つ
        key = f"answers/{st}.md"
        form = "essay" if _is_essay(repo, st) else "mcq"
        items.append({"no": no, "kind": "paper", "ref": st, "src": src,
                      "key": key, "form": form, "state": "未着手"})
    for _ in range(n_paper - len(stamps)):
        no += 1
        items.append({"no": no, "kind": "paper", "ref": "(未生成)", "src": "",
                      "state": "準備失敗", "error": "紙面の生成に失敗"})

    # --- ラボ選定フェーズ ---
    cat = parse_catalog(repo)
    hist = parse_history(repo)
    n_lab = 0 if a.paper_only else a.lab
    n_extra = 0 if a.paper_only else a.lab_extra
    if a.paper_only:
        log("[選定] --paper-only: ラボは作らない(CML のラボ枠を使わない)")
    genres = [g.strip() for g in (a.lab_genres or "").split(",") if g.strip()]
    labs, notes, used_nodes = ([], [], 0) if n_lab <= 0 else select_genre_labs(
        cat, hist, genres=genres, count=n_lab, budget=a.budget, used=used,
        rnd=rnd, family_days=a.family_days, today=today, log=log)
    # ★3問目は「余裕があれば」。入らなければ黙って2問で確定する(無理に詰めない)
    if n_extra > 0:
        # ★追加枠は予算を使い切らない。上限に張り付くと他セッションの provision が
        #   ライセンス不足で落ちる(2026-08-08 に実際に起こした)。reserve ぶん残す。
        extra, xnotes = select_labs(
            cat, hist, count=n_extra, budget=a.budget - a.reserve,
            used=used + used_nodes, rnd=rnd,
            diff_range=(a.min_diff, a.max_diff), repeat_days=a.repeat_days,
            family_days=a.family_days, allow_special=a.allow_special,
            today=today, pin=a.lab_id or (),
            allow_non_cisco=a.allow_non_cisco,
            allow_automation=a.allow_automation, ts_only=not a.any_lab)
        chosen_tags = {t for lb in labs for t in lb.get("tags", [])}
        extra = [e for e in extra if not (chosen_tags & set(e.get("tags", [])))]
        if extra:
            labs += extra
            notes += [f"追加枠: {extra[0]['id']}({extra[0]['nodes']}台)"]
        else:
            notes += ["追加枠: 台数か分野の条件に合う候補が無いので見送り"]
        notes += xnotes
    for n in notes:
        log(f"[選定] {n}")
    private = {"pack_id": pack_id, "seed": seed, "labs": []}
    for lb in labs:
        no += 1
        it = {"no": no, "kind": "lab", "ref": lb["id"], "src": "",
              "nodes": lb["nodes"], "state": "未着手"}
        if a.dry_run:
            it["ref"] = (f"{lb['id']}-<新seed>" if lb["source"] == "generator"
                         else lb["id"])
            it["error"] = "dry-run のため未構築"
            log(f"[ラボ] dry-run: {it['ref']} を選定のみ(構築せず・{lb['nodes']}台)")
            items.append(it)
            continue

        # ① GEN 系は新 seed で新インスタンスを作る(既存インスタンスは既出の可能性)
        prob_id = lb["id"]
        if lb["source"] == "generator":
            prob_id = gen_instance(repo, lb["script"], rnd.randrange(1000, 99999), log)
            if not prob_id:
                it["error"] = "生成器の実行に失敗"
                log(f"[ラボ] ★{lb['id']} の生成に失敗 → この問題は欠落")
                items.append(it)
                continue
            it["ref"] = prob_id
            log(f"[ラボ] 生成: {prob_id}")

        # ② provision(＋作業フォルダの完成判定)
        variant = (lb.get("variant") or "").split(",")[0].strip() or None
        src, err = provision_lab(repo, prob_id, variant, log)
        if not src:
            it["error"] = err
            log(f"[ラボ] ★{prob_id} の構築に失敗: {err}")
            items.append(it)
            continue
        it["src"] = src
        if variant:
            it["variant"] = variant

        # ③ bringup(到達性の確認と IOSvL2 の救済)
        ng = bringup(repo, prob_id, log)
        if ng:
            it["warn"] = f"未到達ノード: {','.join(ng)}"

        # ④ 基線採点(得点は manifest にも index にも書かない = 難度のヒントになるため)
        got, total, why = baseline_grade(repo, prob_id, variant, log,
                                         settle=a.settle)
        if got is None:
            log(f"[ラボ] 基線採点を取得できず({why}) — 朝の確認対象")
        else:
            log(f"[ラボ] 基線 {got}/{total} 点")
            if total and got == total:
                log(f"[ラボ] ★★{prob_id} は最初から満点 = 課題が入っていない疑い。"
                    f"差し替えを検討すること")
        private["labs"].append({"id": prob_id, "variant": variant,
                                "baseline": None if got is None else [got, total]})
        items.append(it)

    if not a.dry_run:
        with open(os.path.join(logdir, f"pack-{pack_id}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(private, fh, ensure_ascii=False, indent=2)

    # --- 出力 ---
    mermaid_js = render_html.read_mermaid() if a.mermaid == "embed" else None
    write_pages(repo, pdir, items, mermaid_js, mermaid_mode=a.mermaid,
                pack_id=pack_id)
    idx = index_md(pack_id, items, notes, a.dry_run)
    with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html.render(idx, title=f"{pack_id} — 問題パック",
                                    nav=build_nav(items, 0),
                                    mermaid_mode=a.mermaid))
    log(f"[出力] 図の描画方法: {a.mermaid}")
    sheet = os.path.join(pdir, "解答.md")
    if os.path.exists(sheet):
        log(f"[出力] 解答.md は既存のため上書きしない: {sheet}")
    else:
        with open(sheet, "w", encoding="utf-8") as fh:
            fh.write(answer_sheet_md(pack_id, items))
    write_manifest(pdir, {"pack_id": pack_id, "created": today.isoformat(),
                          "dry_run": a.dry_run, "seed": seed,
                          "items": items, "notes": notes})
    if not a.dry_run:
        for it in items:
            if it.get("error"):
                continue
            history_upsert(repo, it["ref"], state="出題中",
                           paper=(it["kind"] == "paper"),
                           memo=f"パック {pack_id} の Q{it['no']}", log=log)
    log(f"===== 完了: {pdir} =====")
    print(f"\n目次: {os.path.join(pdir, 'index.html')}")
    print(f"解答: {sheet}")
    logf.close()


def _is_essay(repo, stamp):
    path = os.path.join(repo, "questions", f"{stamp}.md")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as fh:
        return "選択式ではありません" in fh.read()


def cmd_replace(a):
    """パックの1問(ラボ)を別の問題に差し替える。

    用途: 出題方針に合わなかった / 基線採点が想定外だった問題の入れ替え。
    旧ラボは撤収し、新しい問題を選定→生成→provision→基線採点まで通す。
    解答用紙は**該当の問だけ**作り直す(他の問の解答は保持)。
    """
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    pdir = pack_dir(repo, pack_id)
    man = read_manifest(pdir)
    items = man["items"]
    target = next((it for it in items if it["no"] == a.no), None)
    if target is None:
        sys.exit(f"Q{a.no} が見つかりません")
    if target.get("kind") != "lab":
        sys.exit(f"Q{a.no} はラボではありません(差し替え対象はラボのみ)")

    logdir = os.path.join(repo, "topologies", "_state")
    os.makedirs(logdir, exist_ok=True)
    logf = open(os.path.join(logdir, f"pack-{pack_id}.log"), "a", encoding="utf-8")

    def log(msg):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        for line in str(msg).rstrip("\n").splitlines() or [""]:
            print(f"{stamp} {line}", flush=True)
            logf.write(f"{stamp} {line}\n")
        logf.flush()

    old = target.get("ref", "")
    log(f"===== Q{a.no} 差し替え: {old} を撤収して選び直す =====")
    if old and not target.get("error"):
        run([os.path.join(repo, "scripts/lab.sh"), "teardown", old],
            repo, log, f"teardown {old}")

    used, per = cml_started_nodes(repo)
    if used is None:
        used, per = leased_nodes(repo)
    log(f"[台数] CML 起動中 {used} ノード {per or '(なし)'} / 予算 {a.budget}")
    rnd = random.Random(a.seed if a.seed is not None else random.randrange(1, 10 ** 9))
    cat, hist = parse_catalog(repo), parse_history(repo)
    # 同じパック内の他のラボと分野が被らないよう、既存分を履歴扱いで除外する
    others = [it.get("ref", "") for it in items
              if it["no"] != a.no and it.get("kind") == "lab"]
    hist = hist + [(datetime.date.today().isoformat(), o) for o in others if o]
    labs, notes = select_labs(cat, hist, count=1, budget=a.budget, used=used,
                              rnd=rnd, diff_range=(a.min_diff, a.max_diff),
                              repeat_days=a.repeat_days, family_days=a.family_days,
                              allow_special=a.allow_special, pin=a.lab_id or (),
                              allow_non_cisco=a.allow_non_cisco,
                              allow_automation=a.allow_automation,
                              ts_only=not a.any_lab)
    for n in notes:
        log(f"[選定] {n}")
    if not labs:
        sys.exit("差し替え候補が見つかりませんでした(条件を緩めてください)")
    lb = labs[0]

    prob_id = lb["id"]
    if lb["source"] == "generator":
        prob_id = gen_instance(repo, lb["script"], rnd.randrange(1000, 99999), log)
        if not prob_id:
            sys.exit("生成器の実行に失敗しました")
        log(f"[ラボ] 生成: {prob_id}")
    variant = (lb.get("variant") or "").split(",")[0].strip() or None
    src, err = provision_lab(repo, prob_id, variant, log)
    if not src:
        sys.exit(f"構築に失敗しました: {err}")

    target.update({"ref": prob_id, "src": src, "nodes": lb["nodes"],
                   "state": "未着手"})
    target.pop("error", None)
    if variant:
        target["variant"] = variant

    ng = bringup(repo, prob_id, log)
    if ng:
        target["warn"] = f"未到達ノード: {','.join(ng)}"
    got, total, why = baseline_grade(repo, prob_id, variant, log, settle=a.settle)
    if got is None:
        log(f"[ラボ] 基線を取得できず({why})")
    else:
        log(f"[ラボ] 基線 {got}/{total} 点")
        if total and got == total:
            log("[ラボ] ★★最初から満点 = 課題が入っていない疑い。再差し替えを検討")

    write_manifest(pdir, {"pack_id": pack_id, "created": man.get("created", ""),
                          "dry_run": False, "seed": man.get("seed", ""),
                          "items": items, "notes": man.get("notes", [])})
    reset_sheet_section(pdir, target)
    mermaid_js = render_html.read_mermaid() if a.mermaid == "embed" else None
    write_pages(repo, pdir, items, mermaid_js, mermaid_mode=a.mermaid,
                pack_id=pack_id)
    idx = index_md(pack_id, items, man.get("notes", []), False)
    with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html.render(idx, title=f"{pack_id} — 問題パック",
                                    nav=build_nav(items, 0),
                                    mermaid_mode=a.mermaid))
    history_upsert(repo, prob_id, state="出題中",
                   memo=f"パック {pack_id} の Q{a.no}(差し替え)", log=log)
    log(f"===== Q{a.no}: {old} → {prob_id} に差し替え完了 =====")
    logf.close()


def cmd_redeploy(a):
    """パックのラボを**同じ内容のまま**作り直す(問題は差し替えない)。

    用途: CML 側の不調(コンソール出力の乱れ等)でラボが使えなくなった時。
    `problems/<ID>/initial/` から再構築するので、トポロジ・アドレス・仕込みは
    完全に同一。変わるのは CML のラボ実体と MGMT の割当 IP だけ。
    ★`replace`(別の問題に差し替え)とは別物。解答用紙にも触らない。
    """
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    pdir = pack_dir(repo, pack_id)
    man = read_manifest(pdir)
    targets = [it for it in man["items"]
               if it.get("kind") == "lab" and (not a.no or it["no"] == a.no)]
    if not targets:
        sys.exit(f"対象のラボがありません(--no {a.no})")

    logdir = os.path.join(repo, "topologies", "_state")
    os.makedirs(logdir, exist_ok=True)
    logf = open(os.path.join(logdir, f"pack-{pack_id}.log"), "a", encoding="utf-8")

    def log(msg):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        for line in str(msg).rstrip("\n").splitlines() or [""]:
            print(f"{stamp} {line}", flush=True)
            logf.write(f"{stamp} {line}\n")
        logf.flush()

    for it in targets:
        ref = it.get("ref", "")
        log(f"===== Q{it['no']} {ref} を同一内容で再構築 =====")
        if not os.path.exists(os.path.join(repo, "problems", ref)):
            log(f"★{ref}: 問題パックが無いので再構築できない(内容を再現できません)")
            continue
        run([os.path.join(repo, "scripts/lab.sh"), "teardown", ref],
            repo, log, f"teardown {ref}")
        src, err = provision_lab(repo, ref, it.get("variant"), log)
        if not src:
            log(f"★{ref}: 再構築に失敗: {err}")
            it["error"] = err
            continue
        it["src"] = src
        it.pop("error", None)
        ng = bringup(repo, ref, log)
        it["warn"] = f"未到達ノード: {','.join(ng)}" if ng else ""
        if not it["warn"]:
            it.pop("warn", None)
        # ★基線を再測定して**再構築前と同じ点**であることを確かめる
        #   (同じなら内容が同一である裏付けになる)
        got, total, why = baseline_grade(repo, ref, it.get("variant"), log,
                                         settle=a.settle)
        log(f"[基線] {ref}: {got}/{total}" if got is not None
            else f"[基線] 取得できず({why})")
    write_manifest(pdir, {"pack_id": pack_id, "created": man.get("created", ""),
                          "dry_run": False, "seed": man.get("seed", ""),
                          "items": man["items"], "notes": man.get("notes", [])})
    log("===== 再構築 完了(解答用紙・問題文は不変) =====")
    logf.close()


def cmd_render(a):
    """既存パックの HTML だけを作り直す(解答.md には触れない)。

    レンダラを直した時に、出題中のパックへ修正を反映するための入口。
    問題文・ラボ・解答は一切作り直さない。
    """
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    pdir = pack_dir(repo, pack_id)
    man = read_manifest(pdir)
    items = man["items"]
    mermaid_js = render_html.read_mermaid() if a.mermaid == "embed" else None
    write_pages(repo, pdir, items, mermaid_js, mermaid_mode=a.mermaid,
                pack_id=pack_id)
    idx = index_md(pack_id, items, man.get("notes", []),
                   man.get("dry_run") == "true")
    with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html.render(idx, title=f"{pack_id} — 問題パック",
                                    nav=build_nav(items, 0),
                                    mermaid_mode=a.mermaid))
    print(f"再描画しました: {pdir} ({len(items)} 問・解答.md は不変)")


def cmd_status(a):
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    pdir = pack_dir(repo, pack_id)
    man = read_manifest(pdir)
    sheet = parse_answer_sheet(os.path.join(pdir, "解答.md"))
    print(f"== {pack_id} ({man.get('created')}) "
          f"{'[dry-run]' if man.get('dry_run') == 'true' else ''}")
    done = 0
    for it in man["items"]:
        s = sheet.get(it["no"], {})
        mark = "✔ 解答済" if s.get("done") else "・未着手"
        done += 1 if s.get("done") else 0
        ans = (f"  解答={fmt_letters(choice_of(s.get('answer')))}"
               if s.get("answer") else "")
        print(f"  Q{it['no']} [{it.get('kind')}] {it.get('ref')}  {mark}{ans}")
    print(f"  -- {done}/{len(man['items'])} 問 解答済")
    used, per = leased_nodes(repo)
    print(f"== 稼働中ラボ: {per or '(なし)'} 合計 {used} ノード")


def cmd_grade(a):
    """解答.md を採点し、report.html を書き、_history.md を更新する。

    紙面 MCQ = キー突合(自動) / 記述式 = Claude が採点(ここでは印を付けるだけ)
    ラボ = grade.yml を実走(--no-lab で省略可)。
    """
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    pdir = pack_dir(repo, pack_id)
    man = read_manifest(pdir)
    sheet = parse_answer_sheet(os.path.join(pdir, "解答.md"))
    rows, lab_rows, correct, gradable = [], [], 0, 0

    for it in man["items"]:
        s_it = sheet.get(it["no"], {})
        if it.get("kind") == "paper":
            # choice_of / key_of は整列済みの記号列を返す("D" / "BD")。
            # 複数選択は**過不足なしで正解**なので、文字列一致がそのまま集合一致。
            key, why = key_of(repo, it.get("ref", ""))
            given = choice_of(s_it.get("answer")) or ""
            gs = "・".join(given)
            ks = "・".join(key) if key else ""
            if key is None:
                rows.append((it["no"], "紙面", it.get("ref", ""), gs or "-", "-",
                             why or "自動採点不可(Claude が採点)"))
            elif not given:
                rows.append((it["no"], "紙面", it.get("ref", ""), "(未記入)", "-",
                             "未解答"))
            else:
                gradable += 1
                ok = given == key
                correct += 1 if ok else 0
                note = "正解" if ok else "不正解"
                if not ok and len(key) > 1:
                    g, k = set(given), set(key)
                    if g < k:
                        note += "(選択が不足)"
                    elif g > k:
                        note += "(選択が過剰)"
                rows.append((it["no"], "紙面", it.get("ref", ""), gs, ks, note))
                history_upsert(repo, it["ref"], state="採点済", paper=True,
                               score=f"{'正解' if ok else '不正解'}({ks})",
                               memo=f"パック {pack_id} の Q{it['no']}")
                # ノルマ台帳(BL-114): 採点が確定した瞬間の JST で記録する
                quota.log_attempt(repo, "paper", it["ref"],
                                  result="ok" if ok else "ng",
                                  src=f"pack:{pack_id}", quiet=True)
        else:
            ref = it.get("ref", "")
            if a.no_lab or it.get("error"):
                rows.append((it["no"], "ラボ", ref, "-", "-", "ラボ採点は省略"))
                continue
            print(f"  Q{it['no']} [ラボ] {ref}: 採点中…", flush=True)
            got, total, why = grade_lab(repo, ref, it.get("variant"))
            if got is None:
                rows.append((it["no"], "ラボ", ref, "-", "-", f"採点できず({why})"))
                continue
            fails = why if isinstance(why, list) else []
            lab_rows.append((it["no"], ref, got, total, fails))
            rows.append((it["no"], "ラボ", ref, "-", "-", f"{got}/{total} 点"))
            history_upsert(repo, ref, state="採点済", score=str(got),
                           memo=f"パック {pack_id} の Q{it['no']}")
            quota.log_attempt(repo, "lab", ref, score=got, total=total,
                              src=f"pack:{pack_id}", quiet=True)

    print(f"== {pack_id} 採点", flush=True)
    for no, kind, ref, given, key, note in rows:
        extra = f" 解答={given} 正解={key}" if kind == "紙面" else ""
        print(f"  Q{no} [{kind}] {ref}:{extra} … {note}")
    if gradable:
        print(f"  -- 紙面 MCQ {correct}/{gradable} 問正解")

    md = build_report(repo, pack_id, pdir, man, rows, lab_rows)
    out = os.path.join(pdir, "report.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_html.render(md, title=f"{pack_id} — 採点結果",
                                    nav=build_nav(man["items"], 0),
                                    mermaid_mode=a.mermaid))
    print(f"  レポート: {out}")
    # ノルマ台帳(BL-114): 採点直後に当日の進捗を出す
    cfg = quota.config(repo)
    print(quota.render_today(quota.summarize(
        repo, quota.quota_day(quota.now_jst(), cfg["day_start"]))))


def grade_lab(repo, prob_id, variant=None, timeout=1800):
    """grade.yml を実走して (得点, 満点, 未充足チェック名) を返す。"""
    import tempfile
    if not os.path.exists(os.path.join(repo, "problems", prob_id)):
        return None, None, "問題パックが無い"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write("CCNP\n")
        vault = fh.name
    try:
        cmd = [os.path.join(repo, ".venv/bin/ansible-playbook"),
               os.path.join(repo, "playbooks/grade.yml"),
               "-e", f"problem={prob_id}", "--vault-password-file", vault]
        if variant:
            cmd += ["-e", f"variant={variant}"]
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, "タイムアウト"
    finally:
        os.unlink(vault)
    out = (r.stdout or "") + (r.stderr or "")
    hits = SCORE_RE.findall(out)
    if not hits:
        return None, None, "得点行を読めず"
    got, total = int(hits[-1][0]), int(hits[-1][1])
    fails = re.findall(r"\[FAIL\][^\n]*?点\)\s*(.+?)'", out)
    return got, total, sorted(set(fails))


def cmd_close(a):
    repo = os.path.abspath(a.repo)
    pack_id = a.pack_id or latest_pack(repo)
    man = read_manifest(pack_dir(repo, pack_id))
    labs = [it for it in man["items"]
            if it.get("kind") == "lab" and not it.get("error")]
    if not labs:
        print("撤収対象のラボはありません(dry-run パックなど)")
        return
    for it in labs:
        cmd = [os.path.join(repo, "scripts/lab.sh"), "teardown", it["ref"]]
        print("== " + " ".join(cmd))
        if a.dry_run:
            continue
        subprocess.run(cmd, cwd=repo, check=False)
        history_upsert(repo, it["ref"], state="撤収済")


def main():
    ap = argparse.ArgumentParser(description="問題パック(連続出題)ビルダ")
    ap.add_argument("cmd",
                    choices=["new", "status", "grade", "close", "render",
                             "replace", "redeploy"])
    ap.add_argument("--no", type=int, default=0,
                    help="replace/redeploy: 対象の問番号"
                         "(redeploy は省略で全ラボ)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--pack-id", default=None)
    ap.add_argument("--paper", default="auto",
                    help=f"紙面の問題数。`auto`(既定)= {PAPER_AUTO_MIN}〜"
                         f"{PAPER_AUTO_MAX}問から抽選 / `12`= 固定 / `8-14`= 範囲")
    ap.add_argument("--paper-only", action="store_true",
                    help="紙面だけのパックにする(ラボを作らない=CMLのラボ枠を使わない)")
    ap.add_argument("--require-shape", default="redist,aaa,acl,bgp",
                    help="紙面の必須ジャンル(カンマ区切り。"
                         f"選択肢: {','.join(PAPER_GENRES)})")
    ap.add_argument("--lab", type=int, default=2,
                    help="固定ジャンルから選ぶラボ数(v2 既定2)")
    # ★既定に ipsla を追加(2026-08-22 ユーザ指示「既定の抽選に混ぜられるように」)。
    #   4ジャンルのシャッフルから2つ選ぶ形になる。
    ap.add_argument("--lab-genres", default="hvrf,dhcp,dmvpn,ipsla",
                    help=f"ラボの固定ジャンル({','.join(LAB_GENRES)})")
    ap.add_argument("--lab-extra", type=int, default=1,
                    help="余裕があれば通常TSプールから追加する数(既定1)")
    ap.add_argument("--reserve", type=int, default=3,
                    help="追加枠が使わずに残すノード数(他セッション用の余白)")
    ap.add_argument("--budget", type=int, default=20, help="同時起動ノード上限")
    ap.add_argument("--settle", type=int, default=180,
                    help="基線採点の前に待つ秒数(収束待ち。0で無効)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--shape", default="mixed", help="紙面の shape(gen_paper_mcq)")
    ap.add_argument("--exam", action="store_true", default=True)
    ap.add_argument("--no-exam", dest="exam", action="store_false")
    ap.add_argument("--hard", action="store_true")
    ap.add_argument("--min-diff", type=int, default=3)
    ap.add_argument("--max-diff", type=int, default=5)
    ap.add_argument("--repeat-days", type=int, default=90,
                    help="同一問題(seed込み)を再出題しない日数")
    ap.add_argument("--family-days", type=int, default=21,
                    help="同じ生成器ファミリを再出題しない日数(新seedなら別問題)")
    ap.add_argument("--lab-id", action="append", default=[],
                    help="ラボ問題を名指しで指定(静的ID または GEN 接頭・複数可)")
    ap.add_argument("--no-lab", action="store_true",
                    help="grade: ラボの実機採点を省略(紙面だけ採点する)")
    ap.add_argument("--any-lab", action="store_true",
                    help="TS以外(構築問・ドリル)もラボ候補に含める(既定はTSのみ)")
    ap.add_argument("--allow-automation", action="store_true",
                    help="自動化ラボ(Ansible/RESTCONF)も候補に含める(既定は除外)")
    ap.add_argument("--allow-non-cisco", action="store_true",
                    help="他ベンダ機・Linuxサーバ構築系も候補に含める(既定は除外)")
    ap.add_argument("--allow-special", action="store_true",
                    help="特殊ラボ(専用 ops CLI)も候補に含める")
    ap.add_argument("--mermaid", choices=render_html.MERMAID_MODES, default="cdn",
                    help="図の描画方法(既定 cdn=ふつうのHTML / embed=オフライン用)")
    ap.add_argument("--dry-run", action="store_true",
                    help="CML にも questions/ にも触らないプレビュー")
    a = ap.parse_args()
    {"new": cmd_new, "status": cmd_status, "grade": cmd_grade,
     "close": cmd_close, "render": cmd_render,
     "replace": cmd_replace, "redeploy": cmd_redeploy}[a.cmd](a)


if __name__ == "__main__":
    main()
