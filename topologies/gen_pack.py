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
  new    --paper 3 [--lab N] [--lab-mode default] [--budget 40] [--dry-run]
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
    "bgp": ["bgpbest", "bgpdbg", "bgppol"],
    # ★BL-176(2026-09-18): svc 型の思考系ファミリ(--require-shape で指名できる。既定の必須枠には入れない)
    "ipv6": ["fhs", "dhcp6"],
    "vpn": ["dmvpn"],
    "ospf": ["ospfdbg"],
    "eigrp": ["eigrpkb"],
    "route": ["rtbasic"],
    "mpls": ["mpls"],           # ★BL-186(2026-09-19): --require-shape mpls で指名可(既定の必須枠には入れない)
    "cloze": ["cloze"],         # ★BL-191(2026-09-19): 解説穴埋め形。--require-shape cloze で指名可(既定の必須枠には入れない)
}

# 紙面の問題数を `auto` にしたときの範囲(2026-08-11「10〜20問で適当に」→ 2026-09-05「5問程度」に変更)
PAPER_AUTO_MIN, PAPER_AUTO_MAX = 2, 2   # ★2026-09-28 ユーザ指示「1パック7問程度×3」= 思考2+瞬発3+穴埋め2(旧 5〜6・その前 10〜20)

# ★BL-136(2026-08-23): 紙面の shape/kind 反復回避の参照日数。answers/ の種別履歴で
#   直近 N 日に出た kind を抽選順の後ろへ(gen_paper_mcq --avoid-recent-days)、
#   必須ジャンルの shape も最終出題日の古い順に選ぶ。
AVOID_KIND_DAYS = 4

# ==========================================================================
# ★BL-213(2026-09-21): 単元プロファイル(--profile)。topologies/units.yml(+private/units.yml)の
#   単元タグ表から「この単元集合に属する紙面 shape/kind グロブ・ラボ genre・ラボ候補 ID」を導き、
#   紙面は gen_paper_mcq --only-kinds、ラボは固定ジャンルと TS プールの絞り込みで実現する。
#   指定= カンマ区切りで profile 名(ccna/encor/enarsi/ccie/vendor)と単元 ID(U-A3 …)を混在可。
# ==========================================================================
PROFILE = None                       # main() で解決した dict(無指定なら None)
PAPER_GENRES_ACTIVE = None           # profile で絞った必須ジャンル表(None= PAPER_GENRES)


def load_units(repo=REPO):
    import yaml
    data = {"profiles": {}, "units": {}}
    for rel in ("topologies/units.yml", "private/units.yml"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        data["profiles"].update(d.get("profiles") or {})
        for uid, u in (d.get("units") or {}).items():
            cur = data["units"].setdefault(uid, {"name": "", "blueprint": [], "paper": {"kinds": []}, "lab": {"genres": [], "ids": []}})
            cur["name"] = u.get("name") or cur["name"]
            cur["blueprint"] = sorted(set(cur["blueprint"]) | set(u.get("blueprint") or []))
            cur["paper"]["kinds"] += list((u.get("paper") or {}).get("kinds") or [])
            cur["lab"]["genres"] += list((u.get("lab") or {}).get("genres") or [])
            cur["lab"]["ids"] += list((u.get("lab") or {}).get("ids") or [])
    return data


def resolve_profile(spec, repo=REPO):
    """`--profile` の文字列 → {"units", "paper_kinds", "lab_genres", "lab_ids", "flags", "label"}。"""
    if not (spec or "").strip():
        return None
    data = load_units(repo)
    units, flags = [], set()
    for tok in (t.strip() for t in spec.split(",") if t.strip()):
        tok = tok[5:] if tok.lower().startswith("unit:") else tok
        if tok.upper().startswith("U-"):
            if tok.upper() not in data["units"]:
                sys.exit(f"--profile: 単元 {tok} は units.yml にありません")
            units.append(tok.upper())
            continue
        prof = data["profiles"].get(tok.lower())
        if prof is None:
            sys.exit(f"--profile: {tok} は profile 名(" + "/".join(data["profiles"]) + ")でも単元 ID でもありません")
        flags |= set(prof.get("lab_flags") or [])
        if prof.get("blueprint"):
            units += [u for u, d in data["units"].items() if prof["blueprint"] in d["blueprint"]]
        units += list(prof.get("units") or [])
    units = sorted(set(units))
    kinds, genres, ids = [], [], []
    for u in units:
        d = data["units"][u]
        kinds += d["paper"]["kinds"]
        genres += d["lab"]["genres"]
        ids += d["lab"]["ids"]
    return {"label": spec, "units": units,
            "paper_kinds": sorted(set(kinds)), "lab_genres": sorted(set(genres)),
            "lab_ids": sorted(set(ids)), "flags": flags}


def _profile_shapes(prof):
    return {g.split("/", 1)[0] for g in (prof or {}).get("paper_kinds", [])}


def _profile_only_args(prof):
    ks = (prof or {}).get("paper_kinds") or []
    return ["--only-kinds", ",".join(ks)] if ks else []


def _profile_allows_id(prof, pid):
    if not prof:
        return True
    return any(pid == x or pid.startswith(x) for x in prof.get("lab_ids", []))


def _recent_shape_dates(repo, days):
    """answers/ の `種別: \\`shape/...\\`` 行から shape ごとの最終出題日を集める。"""
    today = datetime.date.today()
    floor = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    ceil = today.strftime("%Y%m%d")
    last = {}
    pat = re.compile(r"種別:\s*`?([a-z0-9]+)/")
    # ★chain だけ歴史的に `種別: \`missing\`` と素の kind 名で書く(quota の
    #   genres.yml も bare kind を igp に畳んでいる)。shape/ 形式に揃えると
    #   quota 側の解析に波及するので、走査側で chain へ写像する。
    bare = re.compile(r"種別:\s*`?(missing|no_seed|filter|wrong_id)`")
    for path in glob.glob(os.path.join(repo, "answers", "*.md")):
        stamp = os.path.basename(path)[:8]
        # ★未来日付は除外(20261229-* は BL-103 の検証アーティファクト)
        if not (stamp.isdigit() and floor <= stamp <= ceil):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        m = pat.search(text)
        sh = m.group(1) if m else ("chain" if bare.search(text) else None)
        if sh:
            last[sh] = max(last.get(sh, ""), stamp)
    return last

# ラボの固定ジャンル: この中から2つ選ぶ(+余裕があれば通常TSプールから1問)。
# H型は EIGRP版/OSPF版をまとめて1ジャンル扱い(同時に2本入れると盤面がほぼ同じ)。
# ★生成器ごとの既定追加引数(ユーザ指示)。固定ジャンル枠でも TS プール経由でも効かせる。
#   H型VRF(EIGRP版/OSPF版)は **最大故障数 3 で出題する**(2026-09-20 ユーザ指示)。
#   理由= 実試験再現の原本 PVT-EIGRP-VRF-H-01 が 3 故障同時で、量産形の既定
#   `--faults 1` では体感難度が原本に届かなかった(本人の指摘)。
#   生成器側の pick_faults は「中央系故障は最大2・3個目は CE 故障へ差し替え」を
#   自前で担保するので、3 指定で組合せが破綻することはない。
GEN_DEFAULT_ARGS = {
    "PVT-EGVRFH": ["--faults", "3"],
    "PVT-OSVRFH": ["--faults", "3"],
}

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
    # ★純粋経路制御(2026-08-23 追加・ユーザ指示「パックに既定で混ぜて」)。
    #   構築問(TSでない)だが固定ジャンル枠は _is_ts を通らないので混ぜられる。
    #   v2 で骨格・手段・PL集合形が seed 抽選されるため連投にも耐える(BL-143)。
    "rtctl": {"label": "純粋経路制御(構築)", "build": True,
              "prefixes": ["GEN-RTCTL"], "tags": ["redistribution", "routing"]},
    # ★GEN-STP(2026-09-22・BL-076)= STP TS(ioll2×5・telnet 採点・故障 10 種)。
    "l2": {"label": "L2(EtherChannel)TS", "group": "l2",
           "prefixes": ["GEN-L2TS"], "tags": ["l2", "etherchannel"]},
    # ★STP(2026-09-22・BL-076)= gen_stp.py。単元 U-A3 の段階ごとにジャンルを分ける(`--lab-genres` で段階を絞れる):
    #   stpts= L3 TS(Rapid PVST+・ioll2×5+MGMTSW/EXTC)/ stpmst= L4 TS(MST+旧機境界・ioll2×4+2)/
    #   stpbuild= L2 構築 / stpmstbuild= L4 構築。variants は生成器にそのまま渡るので GEN-L2TS とは別ジャンル。
    #   group は TS 同士・構築同士で分ける(STP 限定パックで TS と構築を 1 本ずつ出せるように)。
    # ★2026-09-26: ラボは **IOSvL2(--image iosv)** で出す。理由= 長時間稼働した ioll2 で
    #   「特定 VLAN・片方向だけ BPDU が落ちる」現象(BL-219)に 2 度当たり採点が揺れたため。
    #   IOSvL2 は 3 分計測で全リンク全 VLAN 完全一致。IOL 版は `--image iol` で手動生成できる。
    "stpts": {"label": "STP TS(Rapid PVST+)", "group": "stp-ts",
              "prefixes": ["GEN-STP"], "tags": ["stp", "rstp", "l2"], "nodes": 7,
              "variants": [{"args": ["--image", "iosv"], "nodes": 7, "label": "IOSvL2"}]},
    "stpmst": {"label": "STP TS(MST+旧機境界)", "group": "stp-ts",
               "prefixes": ["GEN-STP"], "tags": ["stp", "mst", "l2"], "nodes": 6,
               "variants": [{"args": ["--world", "mst"], "nodes": 6, "label": "L4"}]},
    # ★STP 構築(2026-09-22・BL-076)= gen_stp.py --mode build(L2= --level 2 / L4= --world mst)。
    #   既定 --lab-genres には入れていない(--profile U-A3 か明示指定で出る)。L1 は手動出題用。
    "stpbuild": {"label": "STP 構築(要件書・Rapid PVST+)", "build": True, "group": "stp-build",
                 "prefixes": ["GEN-STP"], "tags": ["stp", "rstp", "l2"], "nodes": 7,
                 "variants": [{"args": ["--mode", "build", "--level", "2", "--image", "iosv"],
                               "nodes": 7, "label": "L2/IOSvL2"}]},
    "stpmstbuild": {"label": "STP 構築(MST 導入)", "build": True, "group": "stp-build",
                    "prefixes": ["GEN-STP"], "tags": ["stp", "mst", "l2"], "nodes": 6,
                    "variants": [{"args": ["--mode", "build", "--world", "mst"], "nodes": 6, "label": "L4"}]},
    # ★STP 3 層キャンパス(2026-09-26・BL-221 の T4)= gen_stp.py --world 3tier(構築のみ・難5)。
    #   7 スイッチ(コア2+分配2+アクセス2+持ち込み)+MGMTSW+EXTC= 9 ノード。IOSvL2 既定(BL-219)。
    "stp3build": {"label": "STP 構築(3 層キャンパス)", "build": True, "group": "stp-build",
                  "prefixes": ["GEN-STP"], "tags": ["stp", "rstp", "l2"], "nodes": 9,
                  "variants": [{"args": ["--mode", "build", "--world", "3tier", "--image", "iosv"],
                                "nodes": 9, "label": "T4/IOSvL2"}]},
    # ★STP 3 層キャンパス TS(2026-09-27・BL-221)= gen_stp.py --world 3tier --mode ts(故障 12 種から 2〜3・難5)。
    #   保護機構の記述方式(port/global/any・BL-222)は seed で抽選。9 ノード(予算 20 以下なら大型スロット扱い)。
    "stp3ts": {"label": "STP TS(3 層キャンパス)", "group": "stp-ts",
               "prefixes": ["GEN-STP"], "tags": ["stp", "rstp", "l2"], "nodes": 9,
               "variants": [{"args": ["--mode", "ts", "--world", "3tier", "--image", "iosv"],
                             "nodes": 9, "label": "T4/IOSvL2"}]},
    # ★services 枠(2026-08-22 追加・BL-134)= IP SLA/track TS。ENARSI は TS 傾向という
    #   ユーザ方針で新設。4 IOL と軽く台数予算に優しい。★既定 --lab-genres にも
    #   参加(2026-08-22 ユーザ指示・hvrf/dhcp/dmvpn と同格の抽選)。
    "ipsla": {"label": "IP SLA/track TS",
              "prefixes": ["GEN-IPSLATS"], "tags": ["ip-sla", "track"]},
    # ★IPv6 自動アドレッシング(2026-09-05 追加・BL-149/146/153)。
    #   v6addr= TS 生成器。board(盤面)を variants から抽選して `--board` を渡す
    #   (a=4 IOL 点対点 17 故障 / rogue=不正RA 5 IOL+非管理SW / pd=委任 5 IOL /
    #    fhs=ioll2 SWB の RA Guard・DHCPv6 Guard 6 故障・telnet 採点)。台数は
    #   MGMTSW/EXTC を含む CML 実ノード数で見積る。
    #   v6build= 要件書駆動の構築問(fhs 盤面・security 枠)。構築問だが固定ジャンル枠は
    #   _is_ts を通らないので混ぜられる(rtctl と同じ扱い)。
    "v6addr": {"label": "IPv6 自動アドレッシング TS",
               "prefixes": ["GEN-V6ADDR"], "tags": ["ipv6", "dhcpv6", "slaac"],
               "variants": [{"args": ["--board", "a"], "nodes": 6, "label": "board=a"},
                            {"args": ["--board", "rogue"], "nodes": 8, "label": "board=rogue"},
                            {"args": ["--board", "pd"], "nodes": 7, "label": "board=pd"},
                            {"args": ["--board", "fhs"], "nodes": 8, "label": "board=fhs"}]},
    "v6build": {"label": "IPv6 自動アドレッシング 構築(FHS)", "build": True,
                "prefixes": ["GEN-V6BUILD"], "tags": ["ipv6", "security", "first-hop-security"],
                "nodes": 8},
    # ★BL-158(2026-09-07 ユーザ指示「ENARSI 範囲は構築問(DMVPN 等)も・MPLS-VPN も」)。
    #   build=True のジャンルは「構築スロット」(1 パック最大 1 本・--build-rate で付く)からしか
    #   選ばれない = TS 多めの比率を規則で担保する(select_genre_labs)。
    #   group= 同じ題材の TS/構築が同居しないための排他キー(dmvpn TS × vpnbuild 等)。
    #   gap_days= その題材(prefixes/ids の family)の再出題間隔。MPLS は 12 台で重いので週 1 程度。
    #   minutes= パック index の所要目安(既定 60)。
    #   ids= 静的問題(seed 無し)のローテーション。段(tier)ごとのリストで、前の段に
    #        直近 repeat_days(既定 90 日)未出題のものがあればそこから選ぶ。全て直近なら最古へ。
    "mpls": {"label": "MPLS L3VPN TS", "group": "mpls", "gap_days": 6, "minutes": 75,
             "prefixes": ["GEN-MPLSTS"], "tags": ["mpls", "l3vpn", "vpnv4"],
             # 間隔判定は同題材の構築(静的)と --pece ebgp の GEN-MPLSEB も含める
             "gap_families": ["GEN-MPLSEB"],
             "gap_ids": ["ENARSI-MPLS-L3VPN-01", "ENARSI-MPLS-L3VPN-02", "ENARSI-MPLS-L3VPN-03",
                         "ENARSI-MPLS-L3VPN-04", "ENARSI-MPLS-L3VPN-05", "ENARSI-MPLS-L3VPN-06"],
             # 12 IOL + MGMTSW を台数に見込む(旧 CML 20 ノード上限の 6 割 = 大型スロット)
             "nodes": 13,
             "variants": [{"args": ["--pece", "ospf"], "label": "pece=ospf"},
                          {"args": ["--pece", "ebgp"], "label": "pece=ebgp"}]},
    "vpnbuild": {"label": "VPN 構築(DMVPN/IPsec)", "build": True, "group": "vpn",
                 "tags": ["dmvpn", "tunnel", "ipsec"],
                 # 1 段目= DMVPN 構築 4 本(優先)/ 2 段目= IPsec 構築 3 本。全て IOSv・console 採点
                 "ids": [["DMVPN-POC-01", "DMVPN-PHASE3-01",
                          "ENARSI-DMVPN-BGP-01", "ENARSI-DMVPN-IPSEC-01"],
                         ["ENARSI-IPSEC-VTI-01", "ENARSI-IPSEC-IKEV2-01",
                          "ENARSI-GREIPSEC-MAP-01"]]},
    # ★security 枠(2026-09-19 ユーザ指示・ブループリント突合せ報告の推奨4)=
    #   既定プールに Security のラボが無く、8/23 以降のラボは security 11 件に留まっていた。
    #   urpf= uRPF TS(3 IOL・4 故障・データプレーン効果採点)= TS プール側。
    #   aaa= 冗長 AAA(RADIUS サーバグループ)構築(RT×2 + FreeRADIUS×2・3 フェーズ挙動採点)
    #        = 構築スロット側。nodes は MGMTSW/EXTC を含む CML 実ノード数の見積り。
    "urpf": {"label": "uRPF TS",
             "prefixes": ["GEN-URPF"], "tags": ["urpf", "security", "anti-spoofing"],
             "nodes": 5},
    "aaa": {"label": "冗長 AAA 構築(RADIUS)", "build": True,
            "prefixes": ["GEN-AAAGRP"], "tags": ["aaa", "radius", "security"],
            "nodes": 6},
    "mplsbuild": {"label": "MPLS L3VPN 構築", "build": True, "group": "mpls",
                  "gap_days": 6, "minutes": 90, "tags": ["mpls", "l3vpn", "vpnv4"],
                  "gap_families": ["GEN-MPLSTS", "GEN-MPLSEB"],
                  # 05(12 台)は大型すぎるので除外。06 は 9 台(大型スロット扱い)
                  "ids": [["ENARSI-MPLS-L3VPN-01", "ENARSI-MPLS-L3VPN-02",
                           "ENARSI-MPLS-L3VPN-03", "ENARSI-MPLS-L3VPN-04",
                           "ENARSI-MPLS-L3VPN-06"]]},
}

# ★大型スロット(BL-158): この台数以上のラボを選んだら、相方は BIG_PARTNER_MAX 台以下の
#   ジャンルに限定し、追加枠(--lab-extra)は自動で 0 にする(CML Personal 20 ノード上限)。
#   ★実測(2026-09-07 E2E PACK-20260907-D): MPLS TS(12 IOL)+VPN 構築(4 IOSv)で CML 実ノードは
#   14+6=**20/20 ちょうど**(MGMTSW/EXTC も数に入る)。相方に 5 台ルータを許すと 21 で
#   ライセンス超過になるため上限は 4。
#   ★2026-09-27 Personal Plus(40 ノード)化= この制限は予算が BIG_RULE_BUDGET 以下の時だけ
#   掛ける(--budget 20 で旧挙動)。それより大きい予算では通常の台数予算検査だけで足りる。
BIG_NODES = 9
BIG_PARTNER_MAX = 4
BIG_RULE_BUDGET = 20
# ★CML ライセンスの同時起動上限(2026-09-27 Personal Plus = 40)。実効予算は MGMT プールの
#   大きさ(group_vars/all/local.yml の mgmt_pool・現 30)でも頭打ちにする: CML 実ノード数 ≥
#   MGMT リース数なので、ノード総数をプール以下に抑えれば IP 枯渇で provision が落ちない。
CML_NODE_LIMIT = 40


def default_budget(repo, log=print):
    try:
        import mgmt_alloc
        pool = len(mgmt_alloc.load_pool(repo))
    except (SystemExit, Exception) as e:
        log(f"[台数] ★mgmt_pool を読めず、予算は CML 上限 {CML_NODE_LIMIT} のまま: {e}")
        return CML_NODE_LIMIT
    return min(CML_NODE_LIMIT, pool)


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
    # ★2026-08-22: GEN-IPSLATS(既存インスタンス無し)の散文推定が空になり
    #   分野重複チェックをすり抜けたため追加
    "ip-sla": ("IP SLA", "IPSLATS"),
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

    セルは `GEN-MPLSTS / GEN-MPLSEB` のような書き方が混ざるので、
    最初の GEN-トークンだけを採る(紙面・params 行は None で候補外になる)。
    `GEN-DOJO-DLIST` のような多段の接頭辞は末尾まで採る(`GEN-DOJO-*` は `GEN-DOJO`)。
    ★ここで採れる接頭辞は生成器が実際に書く ID と一致させること(食い違うと履歴と突き合わない・BL-175)。
    """
    m = re.search(r"(?:GEN|PVT)-[A-Z0-9]+(?:-[A-Z][A-Z0-9]*)*", cell or "")
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


def pool_base(ref):
    """紙面プールの変種ID `<基底ID>-s<数字>` → 基底ID(履歴照合の単位)。"""
    return re.sub(r"-s\d+$", "", ref)


def pool_papers(repo, rnd, today, log=print, exclude=()):
    """別置きの紙面プール(`private/paper_pools.yml`・任意)から紙面を抽選する。

    プール= `dir/questions/<pattern>` の紙面 md と `dir/answers/<同名>.md` の正解キー
    (--extra-paper と同じ置き方)。同じ基底ID(末尾の `-s<数字>` を除いた部分)は、
    両方の出題履歴で直近 repeat_days 日に出ていれば避け、候補が尽きたら最も古いものを再演する。
    基底IDごとに変種を1つだけ選ぶ(同じ問題の変種を同じパックに2つ入れない)。
    `exclude` の基底ID(--extra-paper で明示指定済みのもの)は候補から外す。

      pools:
        - dir: private/<系統>/out     # 相対パス。questions/ と answers/ を持つ
          pattern: "*-s*.md"          # 抽選対象(既定 *.md)
          count: 1                    # 1パックあたりの抽選数
          repeat_days: 30             # 基底IDの再出題を避ける日数(既定 30)
          extra: false                # true= 紙面数に上乗せ / false= 紙面数の内数(既定)
    """
    cfg_path = os.path.join(repo, "private", "paper_pools.yml")
    if not os.path.exists(cfg_path):
        return []
    import yaml                      # manifest と同じく必要な時だけ読む
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    last = {}                                   # 基底ID → 最終出題からの日数
    for d, pid in parse_history(repo):
        age = _age(d, today)
        if age is None:
            continue
        b = pool_base(pid)
        if b not in last or age < last[b]:
            last[b] = age
    picks = []
    for pool in cfg.get("pools") or []:
        d, n = pool.get("dir"), int(pool.get("count") or 0)
        if not d or n <= 0:
            continue
        rdays = int(pool.get("repeat_days") or 30)
        by_base = {}
        for p in sorted(glob.glob(os.path.join(repo, d, "questions",
                                               pool.get("pattern") or "*.md"))):
            ref = os.path.splitext(os.path.basename(p))[0]
            key = os.path.join(d, "answers", os.path.basename(p))
            if not os.path.exists(os.path.join(repo, key)):
                continue
            by_base.setdefault(pool_base(ref), []).append(
                {"ref": ref, "src": os.path.relpath(p, repo), "key": key,
                 "extra": bool(pool.get("extra"))})
        if not by_base:
            log(f"[紙面] プール {d}: 候補なし")
            continue
        for b in set(exclude):
            by_base.pop(b, None)
        fresh = sorted(b for b in by_base
                       if last.get(b) is None or last[b] > rdays)
        if len(fresh) >= n:
            bases = rnd.sample(fresh, n)
            why = f"直近{rdays}日外 {len(fresh)}/{len(by_base)} 問から抽選"
        else:
            stale = sorted((b for b in by_base if b not in fresh),
                           key=lambda b: -last[b])
            bases = fresh + stale[: n - len(fresh)]
            why = f"直近{rdays}日外が {len(fresh)} 問しか無く最古を再演"
        for b in bases:
            picks.append(rnd.choice(by_base[b]))
        log(f"[紙面] プール {d}: {', '.join(x['ref'] for x in picks[-len(bases):])}"
            f" ({why})")
    return picks


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
def _lab_candidates(cat, allow_special=False):
    """CATALOG の静的問題＋生成器 → 出題候補の辞書の列(select_labs と発掘枠が共用)。

    生成器は「新 seed で新インスタンス」= 台数・分野は既存インスタンスから見積る
    (生成器一覧の表は 内容/軸 が散文で、分野タグとしては使えないため)。
    後継がある旧生成器は落とさず `deprecated` を立てて返す(呼び出し側が判断する)。
    """
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
                      "args": list(GEN_DEFAULT_ARGS.get(g["prefix"], [])),
                      "deprecated": _deprecated(g["note"]), "pvt": bool(g.get("pvt")),
                      "star": g["note"].count("★") + g["desc"].count("★")})
    return cands


def select_labs(cat, hist, *, count, budget, used, rnd,
                diff_range=(3, 5), repeat_days=90, family_days=21,
                allow_special=False,
                today=None, pin=(), allow_non_cisco=False,
                allow_automation=False, ts_only=True, only=None):
    """台数合計・分野重複・出題履歴の制約下でラボ問題を選ぶ。

    only= ID/接頭辞の列(BL-213 プロファイル)。与えられたら候補をそれに前方一致するものへ絞る。

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

    cands = [c for c in _lab_candidates(cat, allow_special=allow_special)
             if not c.get("deprecated")]   # 後継に置き換えられた旧生成器は出さない

    # --lab-id で名指しされたものは制約(履歴・難易度)を素通しで最優先に入れる
    picked_pin, notes = [], []
    for pid in pin:
        hit = [c for c in cands if c["id"] == pid]
        if hit:
            picked_pin.append(hit[0])
            notes.append(f"指定 {pid} を採用({hit[0]['nodes']}台)")
        else:
            notes.append(f"★指定 {pid} は CATALOG に無いので無視した")

    if only is not None:
        before = len(cands)
        cands = [c for c in cands if any(c["id"] == x or c["id"].startswith(x) for x in only)]
        notes.append(f"プロファイルの単元に限定: {before} → {len(cands)} 種")
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


def _genre_gap_hit(spec, hist, today):
    """gap_days 付きジャンルが直近に出ていれば (日数, ID) を返す(BL-158)。

    対象= spec の prefixes(生成器 family)と ids(静的 ID)。variants で接頭辞が変わる
    生成器(GEN-MPLSTS → --pece ebgp は GEN-MPLSEB)は同じ題材なので `gap_families` で補う。
    """
    gap = spec.get("gap_days")
    if not gap:
        return None
    fams = set(spec.get("prefixes", [])) | set(spec.get("gap_families", []))
    ids = {i for tier in spec.get("ids", []) for i in tier} | set(spec.get("gap_ids", []))
    best = None
    for d, pid in hist:
        age = _age(d, today)
        if age is None or age > gap:
            continue
        if family(pid) in fams or pid in ids:
            if best is None or age < best[0]:
                best = (age, pid)
    return best


def _resolve_static(cat, spec, hist, rnd, repeat_days, today):
    """静的 ID ローテーション(BL-158): 段ごとに直近 repeat_days 未出題のものから抽選。

    全段とも直近なら**最も古く出したもの**へフォールバックする(候補ゼロで欠落させない。
    静的問題は seed が無い= 同じ問題の再演になるので、間隔だけは最大化する)。
    """
    byid = {it["id"]: it for it in cat["normal"]}
    last = {}
    for d, pid in hist:
        age = _age(d, today)
        if age is not None and (pid not in last or age < last[pid]):
            last[pid] = age
    tiers = [[i for i in tier if i in byid] for tier in spec.get("ids", [])]
    known = [i for tier in tiers for i in tier]
    if not known:
        return None, "静的 ID が CATALOG に無い"
    for tier in tiers:
        fresh = [i for i in tier if last.get(i) is None or last[i] > repeat_days]
        if fresh:
            pick = rnd.choice(fresh)
            return byid[pick], f"未出題/直近{repeat_days}日外から抽選"
    pick = max(known, key=lambda i: last.get(i, 10 ** 6))
    return byid[pick], f"全て直近{repeat_days}日内 → 最古({last.get(pick)}日前)を再演"


def resolve_genre(cat, genre, hist, rnd, family_days, today, log=print,
                  repeat_days=90, ignore_gap=False):
    """固定ジャンル → 実際に使う生成器(接頭辞・スクリプト・台数)か静的問題を決める。

    H型は **EIGRP 版を優先**し、直近 family_days に出ていれば OSPF 版へ回す
    (ユーザ指示 2026-08-09)。片方しか無ければそれを使う。
    ★BL-158: `ids` を持つジャンルは静的問題のローテーション(_resolve_static)。
      `gap_days` 付きジャンルは直近に同題材が出ていれば今回は見送る(None)。
    """
    spec = LAB_GENRES.get(genre)
    if not spec:
        return None
    hit = None if ignore_gap else _genre_gap_hit(spec, hist, today)
    if hit:
        log(f"[選定] {spec['label']}: {hit[1]} を {hit[0]} 日前に出題済"
            f"(間隔 {spec['gap_days']} 日) → 今回は見送り")
        return None
    common = {"tags": spec["tags"], "genre": genre, "build": bool(spec.get("build")),
              "group": spec.get("group"), "minutes": spec.get("minutes", 60)}
    if spec.get("ids"):
        it, why = _resolve_static(cat, spec, hist, rnd, repeat_days, today)
        if it is None:
            log(f"[選定] ★ジャンル {genre}: {why}")
            return None
        log(f"[選定] {spec['label']}: {it['id']} ({why})")
        return dict(common, id=it["id"], script=None, nodes=it["nodes"] or DEFAULT_NODES,
                    diff=it["diff"], source="static", kind=it.get("kind", "normal"),
                    label=spec["label"], args=[],
                    variant=it.get("variant", ""), pvt=bool(it.get("pvt")))
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
    nodes = spec.get("nodes") or _nodes_from_text(pick["desc"] + " " + pick["note"]) or DEFAULT_NODES
    args, label = list(GEN_DEFAULT_ARGS.get(pick["prefix"], [])), spec["label"]
    if spec.get("variants"):
        # 盤面/形の variant を抽選し、生成器へ渡す追加引数と台数を確定する
        var = rnd.choice(spec["variants"])
        args, nodes = args + list(var.get("args", [])), var.get("nodes", nodes)
        label = f"{spec['label']}({var.get('label', ' '.join(args))})"
    return dict(common, id=pick["prefix"], script=pick["script"], nodes=nodes,
                diff=pick["diff"], source="generator", kind="generator",
                label=label, args=args, pvt=bool(pick.get("pvt")))


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
                      family_days=21, today=None, log=print,
                      build_rate=0.4, repeat_days=90):
    """固定ジャンルから count 個を選ぶ(台数予算に収まる組合せを探す)。

    ★固定ジャンルは**履歴による重複回避も分野タグ重複チェックも適用しない**。
      毎晩指定する枠なので履歴で弾くと2日目から候補ゼロになるし、H型と他が
      `vrf` 等で衝突して落ちるのも意図に反する(新 seed で盤面と故障は変わる)。
      例外= `group` が同じジャンル同士(同じ題材の TS と構築)・`gap_days`(BL-158)。

    ★BL-158 2 段抽選(TS 多めの比率を規則で担保):
      1. 構築スロット: 確率 build_rate で build ジャンルから **1 つだけ**引き、先頭に置く。
         外れれば構築 0。build_rate=0 で従来どおり(構築ジャンルは選ばれない)。
      2. 残りは TS ジャンルのシャッフルで埋める。
      大型(BIG_NODES 以上)を選んだら相方は BIG_PARTNER_MAX 台以下に限定する。
    """
    today = today or datetime.date.today()
    pool = [g for g in genres if g in LAB_GENRES]
    notes = []
    build_pool = [g for g in pool if LAB_GENRES[g].get("build")]
    ts_pool = [g for g in pool if not LAB_GENRES[g].get("build")]
    rnd.shuffle(ts_pool)
    order = []
    if build_pool and rnd.random() < build_rate:
        order.append(rnd.choice(build_pool))
        notes.append(f"構築スロット(確率{build_rate:.2f}): {order[0]} を先頭に")
    elif build_pool:
        notes.append(f"構築スロット(確率{build_rate:.2f}): 外れ → 今回は TS のみ")
    order += ts_pool
    picked, total, groups = [], 0, set()
    big = False
    big_rules = budget <= BIG_RULE_BUDGET
    for genre in order:
        if len(picked) >= count:
            break
        spec = LAB_GENRES[genre]
        if spec.get("group") and spec["group"] in groups:
            notes.append(f"{spec['label']} は同題材({spec['group']})を既に選んだので見送り")
            continue
        lb = resolve_genre(cat, genre, hist, rnd, family_days, today, log=log,
                           repeat_days=repeat_days)
        if lb is None:
            continue
        if big_rules and big and lb["nodes"] > BIG_PARTNER_MAX:
            notes.append(f"{lb['label']} は大型ラボの相方には大きすぎるので見送り"
                         f"({lb['nodes']}台 > {BIG_PARTNER_MAX})")
            continue
        if big_rules and picked and lb["nodes"] >= BIG_NODES and any(
                p["nodes"] > BIG_PARTNER_MAX for p in picked):
            notes.append(f"{lb['label']} は大型({lb['nodes']}台)で既選定と同居できず見送り")
            continue
        if total + lb["nodes"] + used > budget:
            notes.append(f"{lb['label']} は台数予算に入らず見送り"
                         f"({lb['nodes']}台・稼働中{used}/{budget})")
            continue
        picked.append(lb)
        total += lb["nodes"]
        if spec.get("group"):
            groups.add(spec["group"])
        if big_rules and lb["nodes"] >= BIG_NODES:
            big = True
            lb["big"] = True
            notes.append(f"{lb['label']} は大型({lb['nodes']}台) → 相方は"
                         f"{BIG_PARTNER_MAX}台以下・追加枠なし")
    got = "・".join(f"{p['label']}({p['id']}/{p['nodes']}台"
                    f"{'・構築' if p.get('build') else ''})" for p in picked)
    n_build = sum(1 for p in picked if p.get("build"))
    notes.insert(0, f"固定ジャンル {len(picked)}/{count} 問(構築 {n_build}): {got or '(なし)'}")
    return picked, notes, total


def select_rotation_labs(cat, hist, *, mode_name, count, budget, used, rnd,
                         family_days=21, today=None, log=print,
                         build_rate=0.4, repeat_days=90, repo=REPO, exclude_units=(),
                         allow_build=True):
    """単元ローテーション(BL-223・lab_rotation.py)で count 本を選ぶ。

    単元の順序は lab_rotation.plan_units(曜日表＋遅れ補正)。単元の中では構築を --build-rate の
    当たり時だけ候補に入れ(1 パック最大 1 本)、前回出した日が古いジャンルから解決する。
    解決できない単元(台数予算・カタログ欠落)は遅れ度順の代わりの単元で埋める。
    gap_days は掛けない(頻度は曜日表が決める)。大型スロット制限は予算 20 以下の時だけ。
    count= 単元に回す本数(None なら mode の slots から発掘枠を引いた残り)。
    exclude_units= 今日は発掘枠(BL-233)が同じ単元の問題を出すので外す単元。
    allow_build= False なら単元側は TS のみ(発掘枠が構築問を出した日。構築は 1 日最大 1 本を保つ)。
    """
    import lab_rotation
    mode = lab_rotation.load_mode(repo, mode_name)
    count = lab_rotation.rotation_slots(mode) if count is None else count
    seen = lab_rotation.last_seen(repo, mode, LAB_GENRES, today, hist)
    plan = lab_rotation.plan_units(mode, today, seen, slots=count, exclude=exclude_units)
    for line in lab_rotation.describe(mode, today, seen, plan):
        log(line)
    picks, fallback, _ = plan
    genre_last = lab_rotation.genre_last_issued(repo)
    notes, picked, total, groups = [], [], 0, set()
    big_rules = budget <= BIG_RULE_BUDGET
    build_ok = rnd.random() < build_rate and allow_build
    notes.append("構築: 発掘枠が構築問なので単元側は TS のみ" if not allow_build else
                 f"構築(確率{build_rate:.2f}): {'当たり= 1 本まで構築を候補に' if build_ok else '外れ → TS のみ'}")
    for unit in picks + fallback:
        if len(picked) >= count:
            break
        uspec = mode["units"][unit]
        gens = [g for g in uspec["genres"] if g in LAB_GENRES]
        use_build = build_ok and not any(p.get("build") for p in picked)
        cands = [g for g in gens if use_build or not LAB_GENRES[g].get("build")]
        rnd.shuffle(cands)
        cands.sort(key=lambda g: genre_last.get(g, ""))       # 前回が古い(未記録)ジャンルから
        if use_build and any(LAB_GENRES[g].get("build") for g in cands):
            # 構築の当たりは「構築のある最初の単元」で使う(TS に流れて当たりが消えないように)
            cands.sort(key=lambda g: not LAB_GENRES[g].get("build"))
        got = None
        for genre in cands:
            spec = LAB_GENRES[genre]
            if spec.get("group") and spec["group"] in groups:
                continue
            lb = resolve_genre(cat, genre, hist, rnd, family_days, today, log=log,
                               repeat_days=repeat_days, ignore_gap=True)
            if lb is None:
                continue
            if big_rules and any(p.get("big") for p in picked) and lb["nodes"] > BIG_PARTNER_MAX:
                continue
            if total + lb["nodes"] + used > budget:
                notes.append(f"{uspec['label']}: {lb['label']} は台数予算に入らず見送り"
                             f"({lb['nodes']}台・稼働中{used}+選定{total}/{budget})")
                continue
            got = lb
            break
        if got is None:
            notes.append(f"{uspec['label']}: 出せるジャンルが無い → 次の単元へ")
            continue
        got["unit"] = unit
        if big_rules and got["nodes"] >= BIG_NODES:
            got["big"] = True
        picked.append(got)
        total += got["nodes"]
        if LAB_GENRES[got["genre"]].get("group"):
            groups.add(LAB_GENRES[got["genre"]]["group"])
    desc = "・".join(f"{mode['units'][p['unit']]['label']}={p['label']}({p['id']}/{p['nodes']}台"
                     f"{'・構築' if p.get('build') else ''})" for p in picked)
    notes.insert(0, f"単元ローテーション {len(picked)}/{count} 問: {desc or '(なし)'}")
    return picked, notes, total


# ==========================================================================
# 発掘枠(BL-233): 単元ローテーションが引けない資産を「最後に出した日が古い順」で回す
# ==========================================================================
DISCOVERY_KIND_JA = {"generator": "生成器", "static": "静的"}


def rotation_reach(mode):
    """単元ローテーションが引ける生成器接頭辞と静的 ID(= 発掘枠では扱わないもの)。"""
    prefixes, ids = set(), set()
    for spec in mode["units"].values():
        for g in spec["genres"]:
            gs = LAB_GENRES.get(g) or {}
            prefixes |= set(gs.get("prefixes", []))
            ids |= {i for tier in gs.get("ids", []) for i in tier}
    return prefixes, ids


def _issued_as(pid, cand):
    """出題履歴の ID が候補 cand のものか。

    生成器は接頭辞の前方一致で見る(`family()` は `GEN-DOJO-DLIST-123` のような多段の接頭辞を
    拾えないため)。`GEN-REDIST` が `GEN-REDISTMP-…` を拾わないよう、区切りの `-` まで含めて比べる。
    """
    if cand["source"] != "generator":
        return pid == cand["id"]
    return pid == cand["id"] or pid.startswith(cand["id"] + "-")


def discovery_last_issued(repo):
    """発掘枠が出した候補キー → 最後に出した日(パック manifest のラボ行の `pool` から)。

    ★履歴の ID 接頭辞だけに頼らない理由: 生成器が書く ID がカタログの接頭辞と食い違うと
      (BL-175 の型)その候補は永久に「記録なし」= 毎回先頭に来て、他が回らなくなる。
      発掘枠が自分で選んだキーを控えておけば、ID の付け方に関係なく一巡が保証される。
    """
    out = {}
    for path in glob.glob(os.path.join(repo, "packs", "*", "manifest.yml")):
        try:
            man = read_manifest(os.path.dirname(path))
        except Exception:                 # 古い書式・壊れた manifest は読み飛ばす(順序の参考情報なので)
            continue
        if str(man.get("dry_run", "")).lower() == "true":
            continue                      # プレビューは出題していない
        created = str(man.get("created", ""))[:10]
        for it in man["items"]:
            key = it.get("pool")
            if key and not it.get("error") and created > out.get(key, ""):
                out[key] = created
    return out


def discovery_pool(cat, mode, *, allow_non_cisco=False, allow_automation=False):
    """発掘枠の候補と、対象から外したもの。返り値 (候補の列, [(ID, 理由)])。

    対象= 単元ローテーション(mode の units → LAB_GENRES)が引けない生成器と静的問題。
    外すもの= 保留(mode の discovery.hold)・後継がある旧生成器・非 Cisco・自動化・
    専用 CLI 運用(パックの構築/採点が lab.sh 前提)・難易度が min_diff 未満。
    """
    disc = mode["discovery"]
    prefixes, ids = rotation_reach(mode)
    pool, skipped, seen = [], [], set()
    for c in _lab_candidates(cat, allow_special=True):
        if c["source"] == "generator":
            if c["id"] in prefixes or "paper" in c["script"]:
                continue                  # ローテーション側の生成器・紙面の生成器
        elif c["id"] in ids or "紙面" in c.get("access", ""):
            continue                      # ローテーション側の静的問題・機器なしの紙面
        if c["id"] in seen:
            continue                      # 同じ接頭辞の行が複数ある(1 つの生成器の別モード等)
        seen.add(c["id"])
        if c["id"] in disc["hold"]:
            why = f"保留: {disc['hold'][c['id']]}"
        elif c.get("deprecated"):
            why = "後継の生成器がある"
        elif c["kind"] == "special":
            why = "専用 CLI 運用(パック未対応)"
        elif _non_cisco(c) and not allow_non_cisco:
            why = "非 Cisco"
        elif _automation(c) and not allow_automation:
            why = "自動化"
        elif c["diff"] and c["diff"] < disc["min_diff"]:
            why = f"難{c['diff']}(下限 {disc['min_diff']})"
        else:
            pool.append(c)
            continue
        skipped.append((c["id"], why))
    return pool, skipped


def discovery_queue(cat, hist, mode, today, *, repo=REPO, **flags):
    """発掘枠の待ち行列。各候補に `last`(最後に出した日・無ければ "")を付けて返す。"""
    pool, skipped = discovery_pool(cat, mode, **flags)
    by_pool = discovery_last_issued(repo)
    day = today.isoformat()
    for c in pool:
        dates = [d for d, pid in hist if d <= day and _issued_as(pid, c)]
        if by_pool.get(c["id"], "") and by_pool[c["id"]] <= day:
            dates.append(by_pool[c["id"]])
        c["last"] = max(dates, default="")
    return pool, skipped


def select_discovery_labs(cat, hist, *, mode, count, budget, used, rnd, today,
                          repo=REPO, log=print, **flags):
    """発掘枠で count 本を選ぶ。返り値 (選定リスト, メモ, 合計台数)。

    ★順序は「最後に出した日が古い順」(記録なしが最優先)で、乱数は同じ日のもの同士の並びにしか
      使わない。候補が N 件なら N 回以内に必ず全件が一巡する(抽選だけだと偏って出ないものが残る)。
    ★種別(生成器/静的)は mode の discovery.kinds の順に日替わりで交互。生成器は新 seed で何度でも
      出せるが、静的問題は 1 問 1 回なので、混ぜて古い順にすると未出題の静的問題が先に並び切ってしまう。
      その種別で出せるもの(台数予算)が無い日はもう一方から選ぶ。
    """
    if count <= 0:
        return [], [], 0
    pool, _ = discovery_queue(cat, hist, mode, today, repo=repo, **flags)
    kinds = [k for k in mode["discovery"]["kinds"] if k in DISCOVERY_KIND_JA] or list(DISCOVERY_KIND_JA)
    extra_args = mode["discovery"]["args"]
    for c in pool:
        c["_tie"] = rnd.random()
    pool.sort(key=lambda c: (c["last"], c["_tie"]))
    picked, notes, total = [], [], 0
    for slot in range(count):
        start = (today.toordinal() + slot) % len(kinds)
        got = None
        for kind in kinds[start:] + kinds[:start]:
            for c in pool:
                if c["source"] != kind or c in picked:
                    continue
                if total + c["nodes"] + used > budget:
                    notes.append(f"発掘枠: {c['id']} は台数予算に入らず次回へ"
                                 f"({c['nodes']}台・稼働中{used}+選定{total}/{budget})")
                    continue
                got = c
                break
            if got:
                break
        if got is None:
            notes.append("発掘枠: 出せる候補が無い(台数予算か、候補ゼロ)")
            break
        picked.append(got)
        total += got["nodes"]
    labs = []
    for c in picked:
        kind_ja = DISCOVERY_KIND_JA[c["source"]]
        extra = extra_args.get(c["id"]) or []
        if extra and isinstance(extra[0], list):
            extra = rnd.choice(extra)     # 引数の組が複数あれば 1 組を抽選(検証済みの故障だけに絞る等)
        labs.append({"id": c["id"], "script": c.get("script"), "nodes": c["nodes"] or DEFAULT_NODES,
                     "diff": c["diff"], "source": c["source"], "kind": c["kind"],
                     "label": f"発掘枠({kind_ja})", "tags": c.get("tags", []),
                     "args": list(c.get("args", [])) + list(extra),
                     "variant": c.get("variant", ""), "pvt": bool(c.get("pvt")),
                     "genre": "discovery", "pool": c["id"], "build": not _is_ts(c), "group": None,
                     "minutes": 60, "last": c["last"]})
    desc = "・".join(f"{lb['id']}({DISCOVERY_KIND_JA[lb['source']]}/{lb['nodes']}台・"
                     f"前回 {lb['last'] or '記録なし'})" for lb in labs)
    notes.insert(0, f"発掘枠 {len(labs)}/{count} 問(ローテーション外を古い順に): {desc or '(なし)'}")
    return labs, notes, total


def describe_discovery(cat, hist, mode, today, *, repo=REPO, full=False, head=6, **flags):
    """発掘枠の待ち行列を人が読む形で(lab_rotation.py の単体実行が出す)。"""
    n = mode["discovery"]["slots"]
    if n <= 0:
        return ["[発掘] このモードは発掘枠を使わない(discovery.slots = 0)"]
    pool, skipped = discovery_queue(cat, hist, mode, today, repo=repo, **flags)
    kinds = [k for k in mode["discovery"]["kinds"] if k in DISCOVERY_KIND_JA] or list(DISCOVERY_KIND_JA)
    first = kinds[today.toordinal() % len(kinds)]
    lines = [f"[発掘] 1 日 {n} 本・今日の種別= {DISCOVERY_KIND_JA[first]}"
             f"(日替わりで {'→'.join(DISCOVERY_KIND_JA[k] for k in kinds)})"]
    for kind in kinds:
        q = sorted((c for c in pool if c["source"] == kind), key=lambda c: (c["last"], c["id"]))
        never = sum(1 for c in q if not c["last"])
        lines.append(f"[発掘] {DISCOVERY_KIND_JA[kind]} {len(q)} 件(うち出題記録なし {never} 件)・古い順:")
        for c in (q if full else q[:head]):
            lines.append(f"[発掘]    {c['id']:<28} 前回 {c['last'] or '記録なし':<10} 難{c['diff']} {c['nodes']}台")
        if not full and len(q) > head:
            lines.append(f"[発掘]    … ほか {len(q) - head} 件(--all で全件)")
    why = {}
    for pid, w in skipped:
        why.setdefault(w, []).append(pid)
    for w, pids in sorted(why.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"[発掘] 対象外 {len(pids)} 件 — {w}: {', '.join(pids) if full or len(pids) <= 6 else ', '.join(pids[:6]) + ' …'}")
    return lines


# ==========================================================================
# 紙面3問の調達
# ==========================================================================
WROTE_RE = re.compile(r"wrote questions/(\d{8}-\d+)\.md")


def _run_paper_gen(repo, seed, count, shape, exam, hard, log, label, extra_args=()):
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
           "--shape", shape,
           # ★BL-136: 履歴参照の kind 反復回避(mixed には無効=無害)。
           "--avoid-recent-days", str(AVOID_KIND_DAYS)]
    if exam:
        cmd.append("--exam")
    if hard:
        cmd.append("--hard")
    cmd += list(extra_args)
    if PROFILE and PROFILE.get("paper_kinds"):
        cmd += _profile_only_args(PROFILE)            # ★BL-213: プロファイルの単元だけに限定
    log(f"[紙面] {label}: shape={shape} count={count} seed={seed}"
        + (f" profile={PROFILE['label']}" if PROFILE else ""))
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


# ==========================================================================
# 1日 N パック(BL-205・2026-09-20 ユーザ指示)
#   「思考2 + 瞬発3 + 穴埋め2」(=7問・2026-09-28。旧 5+8+5)を1日3パック出し、**配分は1日全体で考える**。
#   - 必須ジャンルは 1日で全ジャンルを1周するよう 3 パックへ配り分ける
#     (--require-shape auto)。
#   - 既に出した (shape/kind) は次のパックの抽選から外す(--exclude-kinds)。
#   - ラボは 1 本目だけに付ける(CML の予算は1日ぶんで共通なので増やせない)。
# ==========================================================================
REQUIRE_PER_PACK = 2          # 1パックの必須ジャンル枠(思考系 2 問のうち・2026-09-28 に 4→2。
                              #   単元ローテ既定では使わない= --profile/--require-shape 明示時だけ)


def _exclude_args(exclude):
    """gen_paper_mcq に渡す --exclude-kinds 引数(空なら付けない)。"""
    ex = sorted({e for e in (exclude or ()) if e})
    return ["--exclude-kinds", ",".join(ex)] if ex else []


def kinds_of_stamps(repo, stamps):
    r"""answers/<stamp>.md の `種別: \`shape/kind\`` を集める(パック間の重複回避用)。"""
    pat = re.compile(r"種別:\s*`?([a-z0-9]+)/([a-z0-9_]+)")
    out = set()
    for st in stamps or ():
        try:
            with open(os.path.join(repo, "answers", f"{st}.md"),
                      encoding="utf-8") as fh:
                m = pat.search(fh.read())
        except OSError:
            continue
        if m:
            out.add(f"{m.group(1)}/{m.group(2)}")
    return out


def plan_genres(spec, n_packs, rnd):
    """必須ジャンルをパックへ配り分ける。`auto`= 1日で全ジャンルを1周。

    明示指定(カンマ区切り)なら従来どおり全パックに同じ必須ジャンルを課す。
    auto は core 4 ジャンル(redist/aaa/acl/bgp)を先に配り、残りを続けて
    ラウンドロビンする(3パックなら 4/3/3 ジャンル= 全10ジャンルが1日で1周)。
    """
    if (spec or "").strip().lower() != "auto":
        req = [g.strip() for g in (spec or "").split(",") if g.strip()]
        return [list(req) for _ in range(n_packs)]
    table = PAPER_GENRES_ACTIVE if PAPER_GENRES_ACTIVE is not None else PAPER_GENRES
    core = [g for g in ["redist", "aaa", "acl", "bgp"] if g in table]
    rest = [g for g in table if g not in core and g != "cloze"]
    rnd.shuffle(core)
    rnd.shuffle(rest)
    plan = [[] for _ in range(n_packs)]
    for i, g in enumerate((core + rest)[:n_packs * REQUIRE_PER_PACK]):
        plan[i % n_packs].append(g)
    return plan


def gen_papers(repo, count, seed, shape, exam, hard, log, require=(), rnd=None,
               exclude=()):
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
        # ★BL-136: shape も履歴参照で選ぶ(最終出題日が最も古いものを優先。
        #   例: bgp 枠の bgpbest/bgpdbg が乱択で bgpdbg に3連続偏った対策)。
        #   リトライ2回目以降は従来どおり乱択(壊れた shape で詰まらないため)。
        last_sh = _recent_shape_dates(repo, AVOID_KIND_DAYS)
        ordered = sorted(shapes, key=lambda s: last_sh.get(s, ""))
        for attempt in range(1, RETRY_MAX + 1):
            sh = ordered[0] if attempt == 1 else rnd.choice(shapes)
            new = _run_paper_gen(repo, seed + 7000 + gi * 100 + attempt, 1, sh,
                                 exam, hard, log, f"必須[{genre}] 試行{attempt}",
                                 extra_args=_exclude_args(exclude))
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
                             exam, hard, log, f"残り 試行{attempt}",
                             extra_args=_exclude_args(exclude))
        made += new
        log(f"[紙面] 累計 {len(made)}/{count} 問")
    if got_genre:
        log(f"[紙面] 必須ジャンルの充足: {got_genre}")
    return made[:count], got_genre


def gen_rotation_papers(repo, rot, slot, count, seed, a, log, exclude=()):
    """紙面の単元ローテーション(BL-224・paper_rotation.py)で slot 枠を count 問作る。

    最終実施日が古い単元から 1 問ずつ、その単元の shape/kind に絞って(`--only-kinds`)生成する。
    同じ kind は 1 枠の中で 2 度出さない(除外に積む)。生成に失敗した単元は飛ばして次へ。
    """
    import paper_rotation
    made, ex, skipped, tries, got = [], set(exclude), set(), 0, []
    while len(made) < count and tries < count * 4:
        order = [u for u in rot.order(slot) if u not in skipped]
        if not order:
            log(f"[紙面] ★{paper_rotation.SLOT_JA[slot]}枠: 出せる単元が尽きた")
            break
        uid = order[0]
        tries += 1
        shape, only = rot.args_for(uid, slot)
        new = _run_paper_gen(repo, seed + tries * 37, 1, shape, a.exam,
                             a.hard if slot != "cloze" else False, log,
                             f"{paper_rotation.SLOT_JA[slot]}枠[{uid} {rot.units[uid]['name']}]",
                             extra_args=only + _exclude_args(ex))
        if new:
            made += new
            ex |= kinds_of_stamps(repo, new)
            rot.take(uid)
            got.append(uid)
        else:
            skipped.add(uid)
            log(f"[紙面] {uid} は生成できず(除外で種切れ等) → 次の単元へ")
    log(f"[紙面] {paper_rotation.SLOT_JA[slot]}枠(単元ローテ): {len(made)}/{count} 問 — "
        + "・".join(f"{u}{rot.units[u]['name']}" for u in got))
    return made


def run(cmd, repo, log, label, timeout=3600, env=None):
    """外部コマンドを回してログに落とす。(rc, stdout) を返す。env= 追加の環境変数。"""
    log(f"[{label}] $ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                           timeout=timeout,
                           env={**os.environ, **env} if env else None)
    except subprocess.TimeoutExpired:
        log(f"[{label}] ★タイムアウト({timeout}s)")
        return 124, ""
    out = (r.stdout or "") + (r.stderr or "")
    log(f"[{label}] rc={r.returncode}\n{out[-6000:]}")
    return r.returncode, out


def gen_instance(repo, script, seed, log, args=None):
    """GEN 生成器を新 seed で回し、できた problems/<ID> を突き止める。

    生成器の標準出力の書式は生成器ごとに違うため、**problems/ の差分**で特定する
    (文字列パースより頑健)。args= 固定ジャンルの variant が渡す追加引数(`--board fhs` 等)。
    """
    before = set(os.listdir(os.path.join(repo, "problems")))
    cmd = [os.path.join(repo, ".venv/bin/python3"),
           os.path.join(repo, "topologies", script),
           "--repo", repo, "--seed", str(seed)] + list(args or [])
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
    # パックのラボはキャンバスの要約注釈を貼らない(盤面を開いただけで題材が割れるため)。
    rc, out = run(cmd, repo, log, f"provision {prob_id}",
                  env={"LAB_TASK_ANNOTATION": "off"})
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
    # ★IOSvL2 は**データ VLAN の SVI も起動後 down で固着**する(2026-09-26・BL-076 の IOSvL2 版検証で判明)。
    #   未接続のエッジポートが本当に down なので VLAN に up のアクセスポートが無く、trunk が forwarding でも
    #   SVI が上がらない(IOL は未接続でも connected 扱いなので起きない)。mgmt が上がった後に telnet で bounce。
    if _iosvl2_nodes(repo, prob_id):
        try:
            import stp_ops
            stp_ops.bounce_down_svis(prob_id, log)
        except Exception as e:                       # 救済は best-effort(失敗しても provision は続ける)
            log(f"[bringup] {prob_id}: データ SVI bounce に失敗 {e}")
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
    """問題ページの題名(画面の枠= 英語・BL-236)。解答.md の見出し(紙面/ラボ)とは別物。"""
    kind = "Paper" if item["kind"] == "paper" else "Lab"
    return f"Q{no} ({kind} {item['ref']})"


def cloze_inline_selects(it, src_path):
    """穴埋め形なら {丸数字: <select> HTML} を返す(本文中の ［①］ に埋め込む・BL-198)。それ以外は {}。"""
    import html as H
    if it.get("kind") != "paper" or not src_path or not os.path.exists(src_path):
        return {}
    with open(src_path, encoding="utf-8") as fh:
        qtext = fh.read()
    letters = render_html.choice_letters(qtext)
    blanks = render_html.blank_terms(qtext) if letters else []
    if not blanks or any(render_html.MATCH_HEAD_RE.match(l) for l in qtext.split("\n") if l.startswith("#")):
        return {}
    texts = dict(render_html.choice_texts(qtext))
    out = {}
    for i, (tk, _ctx) in enumerate(blanks, 1):
        opts = f'<option value="">{tk}</option>' + "".join(
            f'<option value="{tk}{l}">{l}. {H.escape((texts.get(l) or "")[:60])}</option>' for l in letters)
        out[tk] = (f'<select class="msel inline" name="ans{it["no"]}_{i}" data-k="{tk}" '
                   f'title="Blank {tk}">{opts}</select>')
    return out


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
            f"<h2>Answer</h2>")
    if kind == "lab":
        body = ('<label class="row">Notes (optional — the configuration on the devices is your answer)</label>'
                '<textarea class="memo"></textarea>'
                '<label class="done"><input type="checkbox"> Done</label>')
    else:
        letters, pick, terms = [], 1, []
        if src_path and os.path.exists(src_path):
            with open(src_path, encoding="utf-8") as fh:
                qtext = fh.read()
            letters = render_html.choice_letters(qtext)
            pick = render_html.pick_count(qtext)
            terms = render_html.match_terms(qtext)
        blanks = render_html.blank_terms(qtext) if letters else []
        if letters and blanks and not any(
                render_html.MATCH_HEAD_RE.match(l) for l in qtext.split("\n") if l.startswith("#")):
            # ★穴埋め形(BL-191・2026-09-19 ユーザ要望「プルダウンで選べる形式に」):
            #   空欄①〜ごとに <select>。option の値は組合せ形と同じ「①D」なので、ansValue()/
            #   match_of()/採点はそのまま効く。表示は「D. 語句」(語句は 60 字で切る)。
            # ★2026-09-20 ユーザ要望: プルダウンは本文中の ［①］ の位置に埋め込む(cloze_inline_selects →
            #   render_html.render(inline_blanks=…))。解答欄には案内と選択状況の要約だけを置く。
            last = blanks[-1][0]
            ansfield = (f'<label class="row">Fill blanks ①–{last} with the <b>drop-downs in the text</b> '
                        '(your selections are mirrored below).</label><div class="clsum"></div>')
        elif letters and terms:
            # ★組合せ形(項目①〜と記号A〜の対応付け・BL-168): 項目ごとに記号を1つ選ぶ。
            #   値は「①D」の形。ページの ansValue() はチェック済みを全部「・」でつなぐので
            #   解答: 行は「①D・②A・③C・④B」になり、採点は match_of() が読む。
            rows = []
            for i, (tk, ttext) in enumerate(terms, 1):
                opts = "".join(
                    f'<label><input type="radio" name="ans{it["no"]}_{i}" '
                    f'value="{tk}{l}">{l}</label>' for l in letters)
                rows.append(f'<div class="mrow"><span class="mterm">{tk} '
                            f'{H.escape(ttext)}</span><div class="opts">{opts}</div></div>')
            ansfield = ('<label class="row">Choose <b>one</b> letter for each item.</label>'
                        + "".join(rows))
        elif letters:
            # ★複数選択(「2つを選択してください」)はチェックボックスにする。
            #   ラジオのままだと1つしか選べず**解答不能**になる(2026-08-11 発覚)。
            # ★pick == -1 は数非明示(「すべて選んでください」= BL-125 allthat)。
            #   チェックボックスにするが、個数のヒントは出さない(数非明示が主題)。
            typ = "radio" if pick == 1 else "checkbox"
            opts = "".join(
                f'<label><input type="{typ}" name="ans{it["no"]}" '
                f'value="{l}">{l}</label>' for l in letters)
            hint = ("" if pick == 1 else
                    '<label class="row">Select <b>all that apply</b> '
                    '(the number is not given).</label>' if pick == -1 else
                    f'<label class="row">Select <b>{pick}</b> answers.</label>')
            ansfield = f'{hint}<div class="opts">{opts}</div>'
        else:                       # 記述式(選択肢なし)
            ansfield = ('<label class="row">Answer</label>'
                        '<textarea class="ans"></textarea>')
        # ★BL-212(2026-09-21 ユーザ要望): 「答え合わせ」ボタン。押した時点の解答で正誤を
        #   即時表示(緑/赤)し、その問の入力をロックする(=初回解答の確定。解説は採点後のまま)。
        #   2026-09-28 から選択肢ごとの正解/不正解も色分けする(render_html.ANSWER_JS の markKey)。
        #   判定は pack_server の /_api/check がサーバ側で行う(正解キーはページに置かない)。
        body = (ansfield +
                '<label class="row">Rationale (optional)</label>'
                '<textarea class="why"></textarea>'
                '<div class="chkrow"><button type="button" class="chk">Check answer</button>'
                '<span class="chkres"></span>'
                '<span class="chknote">Shows whether you are right and marks the correct choices in color, '
                'then locks your answer for this question (explanations come after grading).</span></div>'
                '<label class="done"><input type="checkbox"> Answered</label>')
    return head + body + '<div class="savemsg"></div></section>'


def q_href(it, pack_id=""):
    """問題へのリンク先。ラボは最初からワークスペースで開く(BL-236・2026-10-07 ユーザ指示)。

    行き先は配信サーバの /_lab(そこからワークスペースのサーバ lab_console.py へ転送される。
    ワークスペースが上がっていなければ、単体の問題ページ q<N>.html へ落ちる)。
    """
    if pack_id and it.get("kind") == "lab" and it.get("src"):
        return f"/_lab?pack={pack_id}&no={it['no']}"
    return f"q{it['no']}.html"


def build_nav(items, cur_no, pack_id="", workspace_link=True):
    """ナビ帯(画面の下端= render_html の .nav)。target=_top = ワークスペースの左枠の中で押しても画面ごと移る。

    workspace_link= ラボの問題ページ単体(q<N>.html)に、ワークスペースへの入口を帯の右端に置く。
    ワークスペースの中で出す版(q<N>.ws.html)には置かない(すでに中に居る)。
    """
    nav = [{"label": "Contents", "href": "index.html", "target": "_top"}]
    for it in items:
        n = it["no"]
        nav.append({"label": f"Q{n}", "href": q_href(it, pack_id), "current": n == cur_no,
                    "target": "_top"})
    cur = next((it for it in items if it["no"] == cur_no), None)
    if workspace_link and pack_id and cur and cur.get("kind") == "lab" and cur.get("src"):
        nav.append({"label": "Open lab workspace ▸", "href": q_href(cur, pack_id),
                    "spacer": True, "target": "_top"})
    return nav


def write_workspace_pages(src, pdir, it, items, pack_id, meta, mermaid_js, mermaid_mode):
    """ラボのワークスペース(lab_console.py・BL-234)用の別版を書く。

    ワークスペースには CML から起こした結線図の Topology タブがあるので、問題文の盤面の節
    (トポロジ／構成図)は Task タブに出さず Topology タブへ移す。節にはアドレス・AS など
    結線図に無い情報が載るので、消さずに置き場所だけ変える(2026-10-06 ユーザ指示)。
      q<N>.ws.html   … ワークスペースの左枠に出す問題ページ。盤面の節を除き、ナビ帯に
                       「Open lab workspace」を置かない(すでに中に居る)。解答欄は q<N>.html と同じ
      q<N>.topo.html … 盤面の節だけ(結線図の下に出す)。盤面の節がある問題だけ
    問題ページ単体(q<N>.html)は従来どおり全文(ワークスペースが上がっていない時の受け皿)。
    """
    with open(src, encoding="utf-8") as fh:
        rest, topo = render_html.split_topology(fh.read())
    no = it["no"]
    with open(os.path.join(pdir, f"q{no}.ws.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html.render(rest, title=q_title(no, it),
                                    nav=build_nav(items, no, pack_id, workspace_link=False), meta=meta,
                                    mermaid_js=mermaid_js, mermaid_mode=mermaid_mode,
                                    answer_form=answer_form(pack_id, it, src)))
    if not topo:
        return
    with open(os.path.join(pdir, f"q{no}.topo.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html.render(topo, title=f"{q_title(no, it)} — Topology",
                                    mermaid_js=mermaid_js, mermaid_mode=mermaid_mode))


def write_pages(repo, pdir, items, mermaid_js, mermaid_mode="cdn", pack_id=""):
    """各問の HTML を書く。入力は questions/ と lab/ に限る(answers/ は読まない)。"""
    written = []
    for it in items:
        src = os.path.join(repo, it["src"]) if it.get("src") else ""
        out = os.path.join(pdir, f"q{it['no']}.html")
        for variant in ("ws", "topo"):          # ワークスペース用の別版は毎回作り直す(差し替え後の残骸を残さない)
            stale = os.path.join(pdir, f"q{it['no']}.{variant}.html")
            if os.path.exists(stale):
                os.remove(stale)
        if not src or not os.path.exists(src):
            body = (f"# {q_title(it['no'], it)}\n\n"
                    f"> ★This question could not be prepared ({it.get('error', 'unknown reason')}).\n"
                    f"> Tell the examiner (Claude).\n")
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(render_html.render(body, title=q_title(it["no"], it),
                                            nav=build_nav(items, it["no"], pack_id),
                                            mermaid_mode=mermaid_mode,
                                            answer_form=answer_form(pack_id, it, "")))
        else:
            meta = ("Hands-on lab. Connect to the devices to solve it. Working folder: lab/%s/" % it["ref"]
                    if it["kind"] == "lab" else
                    "Paper question. Do not connect to any device; answer from the output shown.")
            # ラボは英文出題が基本: 英語版(lab/<ID>/Task.md)が置かれていればそちらを描画する。
            # 置くのは出題者(quiz スキル「英語出題」節)。無ければ日本語の 問題.md のまま。
            en = os.path.join(repo, "lab", it["ref"], "Task.md")
            if it["kind"] == "lab" and os.path.exists(en):
                src = en
            render_html.render_file(src, out, title=q_title(it["no"], it),
                                    nav=build_nav(items, it["no"], pack_id), meta=meta,
                                    mermaid_js=mermaid_js,
                                    mermaid_mode=mermaid_mode,
                                    answer_form=answer_form(pack_id, it, src),
                                    inline_blanks=cloze_inline_selects(it, src))
            if it["kind"] == "lab":
                write_workspace_pages(src, pdir, it, items, pack_id, meta, mermaid_js, mermaid_mode)
        written.append(out)
    return written


def index_md(pack_id, items, notes, dry_run, report=False):
    est = {"paper": 8, "lab": 60}     # 紙面は1問8分・ラボは1問60分の目安

    def _est(it):                     # ラボはジャンルごとの目安(MPLS 構築 90 等・BL-158)
        return int(it.get("est") or est[it["kind"]])
    total = sum(_est(it) for it in items)
    lines = [f"# {pack_id} — Question Pack", ""]
    if report:
        # ★採点後は解説ページへの導線を最上部に置く(2026-09-20 ユーザ指示)
        lines += ["> 📘 **Graded** — [Open the review page (correct answers, your answers, "
                  "and why)](report.html)", ""]
    if dry_run:
        lines += ["> ★This is a **--dry-run preview**. The paper questions are borrowed from earlier ones",
                  "> to check the layout, and the labs are not built.", ""]
    # dry-run で「ラボ未構築」は想定どおりなので警告しない(本番の失敗だけを目立たせる)
    broken = [it for it in items if not it.get("src")
              and not (dry_run and it["kind"] == "lab")]
    if broken:
        lines += ["> ★**Some questions could not be prepared**: " +
                  ", ".join(f"Q{it['no']}" for it in broken),
                  "> Tell the examiner (Claude).", ""]
    lines += [f"{len(items)} questions / about {total // 60} h {total % 60} min. "
              "Your answers are saved to `解答.md`.", "",
              "| # | Type | Question | Est. | How to solve |",
              "|---|------|----------|------|--------------|"]
    for it in items:
        if it["kind"] == "paper":
            how = "No device access (answer from the output shown)"
        else:
            how = (f"Solve on the device consoles (opens in the lab workspace: task, topology, and "
                   f"consoles on one screen. Working folder `lab/{it['ref']}/`)")
        lines.append(f"| [Q{it['no']}]({q_href(it, pack_id)}) | "
                     f"{'Paper' if it['kind'] == 'paper' else 'Lab'} | "
                     f"`{it['ref']}` | {_est(it)} min | {how} |")
    lines += ["", "## How to proceed", "",
              "1. Open each question from the table above (in any order).",
              "2. **Enter your answer in the answer area at the bottom of each page** "
              "(it is saved to `解答.md` automatically). "
              "For a lab, **the configuration on the devices is your answer**, so you only need to tick `Done`.",
              "3. When you have finished, ask for grading (「採点して」).", "",
              "Note: if the answer area reports that it cannot save, the page was not opened through "
              "`scripts/pack.sh serve`. Editing `解答.md` directly has the same effect.", "",
              "## Build notes", ""]
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
        for k in ("kind", "slot", "ref", "src", "key", "form", "variant",
                  "nodes", "state", "ops", "error", "warn", "genre", "unit", "pool",
                  "lab_score", "lab_fails"):   # ラボ採点の結果(再描画で使う)
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
        # 所要時間(BL-144: ページ内ストップウォッチが書く。書式= mm:ss / h:mm:ss)
        m = re.search(r"^[ \t]*所要:[ \t]*([0-9:]+)( *\(自動開始\))?", blob, re.M)
        it["duration"] = (m.group(1) if m else "")
        it["dur_auto"] = bool(m and m.group(2))
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


# ★組合せ形(項目①〜⑳ × 記号A〜J の対応付け・BL-168)。解答欄・正解キーとも
#   「①D・②A・③C・④B」(項目順に整列・「・」区切り)へ正規化して文字列比較する。
MATCH_PAIR_RE = re.compile(r"([①-⑳])\s*[－\-–—:：=]?\s*([A-Ja-jＡ-Ｊａ-ｊ])")
_FW_LETTERS = {ord(c): ord(c) - 0xFEE0 for c in "ＡＢＣＤＥＦＧＨＩＪａｂｃｄｅｆｇｈｉｊ"}


def match_of(text):
    """組合せ形の記入 → 正規形 "①D・②A・③C・④B"。丸数字と記号の対が無ければ ""。

    「①D・②A」(ページの自動保存)でも「①-D、②-A」(手書き)でも読む。
    同じ項目を書き直していたら後の方を採る。
    """
    if not text:
        return ""
    pairs = {}
    for t, l in MATCH_PAIR_RE.findall(text):
        pairs[t] = l.translate(_FW_LETTERS).upper()
    return "・".join(f"{t}{pairs[t]}" for t in sorted(pairs))


def match_key_of(text):
    """解答 md の「## 正解」節から組合せ形の正解(`**①－D、②－A…**`)を読む。無ければ ""。"""
    m = re.search(r"^##\s*正解\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return match_of(m.group(1)) if m else ""


def is_match_key(key):
    """key_of() の戻りが組合せ形の正規形か(先頭が丸数字)。"""
    return bool(key) and "①" <= key[0] <= "⑳"


def fmt_answer(text):
    """解答欄の記入を表示用に(組合せ形はその正規形・選択式は整列した記号)。"""
    return match_of(text) or fmt_letters(choice_of(text))


def key_of(repo, ref, key_path=None):
    """正解キーから記号を読む。記述式なら None。
    組合せ形(`**①－D、②－A…**`)は正規形 "①D・②A…" を返す(match_key_of)。

    既定は `answers/<ref>.md`。`key_path`(repo 相対)が渡されればそちらを見る
    (questions/ 以外の場所に置いた紙面を混ぜたとき用)。

    ★この関数の戻り値は採点結果の表示にしか使わない。キー本文は packs/ に書かない。
    """
    path = (os.path.join(repo, key_path) if key_path
            else os.path.join(repo, "answers", f"{ref}.md"))
    if not os.path.exists(path):
        return None, "キー無し"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "ルーブリック" in text:
        return None, "記述式(ルーブリック採点)"
    # ★複数正解(`**B・D**`)にも対応。整列した記号列で返す(choice_of と同じ形)。
    # ★記号の範囲は A-J(2026-08-11): 8択の問題が実在し、`**H**` を読めず
    #   「正解記号を読めず」で無言の採点不能になっていた(実データ3件で発覚)。
    pat = r"([A-J](?:\s*[・,、]\s*[A-J])*)"
    m = re.search(r"^##\s*正解\s*$\s*\n+\s*\*\*" + pat + r"\*\*", text, re.M)
    if not m:
        m = re.search(r"^\s*\*\*" + pat + r"\*\*\s*$", text, re.M)
    if not m:
        mk = match_key_of(text)          # 組合せ形(①－D、②－A…)
        if mk:
            return mk, ""
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
# 採点レポート(report.html) = 「解説ページ」
#   ★2026-09-20 ユーザ指示で恒久変更: **初回採点から全紙面の正答と解説を出す**。
#     (旧運用= 誤答があるうちは正解率と問番号だけ。再挑戦の学習価値を優先していた)
#     解説の素材は answers/<ID>.md に**パック生成時から存在する**ので、ここでは
#     「解答との突き合わせ」と「読みやすい並べ替え」だけを採点時に行う。
#   ★ラボは対象外(従来どおり正解 config は求められてから)。
# ==========================================================================
# 解説に出してはいけない行(仕込みの種別・seed・生成コマンド等。型が割れる)
_META_LINE = re.compile(
    r"^\s*[-*]\s*(種別|形式|出題形|出題形式|生成|仕込み|要件世界|世界|"
    r"実出力の正典|検証 seed|sub-seed)\s*[:：]")


def _key_text(repo, ref, key_path=None):
    path = (os.path.join(repo, key_path) if key_path
            else os.path.join(repo, "answers", f"{ref}.md"))
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _section(text, title_re):
    """`## <見出し>` 節の本文を取り出す(次の ## まで)。"""
    m = re.search(rf"^## {title_re}[^\n]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def _strip_meta(body):
    """メタ行を落とし、節内の見出し(## / ###)を1段下げる(問題見出しと混ざらないように)。"""
    out = []
    for l in body.split("\n"):
        if _META_LINE.match(l):
            continue
        if l.startswith("### "):
            l = "##### " + l[4:]
        elif l.startswith("## "):
            l = "##### " + l[3:]
        out.append(l)
    return "\n".join(out).strip()


# --------------------------------------------------------------------------
# 可読性(2026-09-20 ユーザ指示「解説ページはもう少し改行を工夫して読みやすく」)
#   解説の地の文は 600〜800 字の一段落になりがちで、そのままだと壁になる。
#   ここで **文ごとに改行**し、句点が来ないまま伸びる文は読点で折る。
#   表・コードブロック・見出し・生 HTML 行には触らない。
# --------------------------------------------------------------------------
# 「af-interface= …」「分類: …」のように頭にラベルが立つ文(ラベルを太字にする)
_LEAD_LABEL = re.compile(r"^([^\s、。]{1,28}?)\s*([=＝:：])\s*(\S.*)$")


def _sentences(s):
    """一段落を文に割る(句点は文末に残す)。"""
    return [t for t in re.split(r"(?<=。)", (s or "").strip()) if t.strip()]


def _soft_wrap(sent, limit=130, chunk=55):
    """句点が来ないまま伸びる文を読点で折る(短すぎる断片は作らない)。"""
    if len(sent) <= limit:
        return [sent]
    out, cur = [], ""
    for part in re.split(r"(?<=、)", sent):
        cur += part
        if len(cur) >= chunk:
            out.append(cur)
            cur = ""
    if cur:
        if out and len(cur) < 12:
            out[-1] += cur
        else:
            out.append(cur)
    return out


# 段落の途中で改行されている原文(編集の都合で 60 字前後に折ってある)は、
# いったん1本につないでから文で割り直す。行頭がこれらの行は別ブロックの始まり。
_BLOCK_START = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|>|#|\||```|<)")


def _join_paragraph(lines):
    """段落内の改行をほどく(和文はそのまま・英数の境目だけ空白を残す)。"""
    text = lines[0]
    for nxt in lines[1:]:
        sep = " " if (text[-1:].isascii() and text[-1:].strip()
                      and nxt[:1].isascii() and nxt[:1].strip()) else ""
        text += sep + nxt
    return text


def _paragraphs(body):
    """(行, それが段落本文か) の列に整える(コード/表/見出しは触らない印を付ける)。"""
    out, buf, in_fence = [], [], False
    def flush():
        if buf:
            out.append((_join_paragraph(buf), True))
            buf.clear()
    for line in (body or "").split("\n"):
        st = line.strip()
        if line.lstrip().startswith("```"):
            flush()
            in_fence = not in_fence
            out.append((line, False))
            continue
        if in_fence or not st:
            flush()
            out.append((line, False))
            continue
        if _BLOCK_START.match(st):
            flush()
            buf.append(line)            # 箇条書き・引用も、続き行はつないで扱う
            continue
        if buf:
            buf.append(st)
            continue
        out.append((line, True))
    flush()
    return out


def _readable(body, limit=60):
    """長い段落・箇条書きを文ごとに改行する(解説ページ専用の整形)。

    ・原文が途中改行されていても、段落単位でつなぎ直してから文で割る
    ・コードブロック・表・見出し・生 HTML 行には触らない
    """
    out = []
    for line, is_text in _paragraphs(body):
        st = line.lstrip()
        if not is_text or len(line) <= limit or st.startswith(("|", "#", "<")):
            out.append(line)
            continue
        pieces = []
        for sent in _sentences(st):
            chunks = _soft_wrap(sent)
            # 文の途中で折った行は全角空白で字下げ= 句点での改行と見分けがつく
            pieces += [chunks[0]] + ["\u3000" + c for c in chunks[1:]]
        out.append(line[:len(line) - len(st)] + "<br>".join(pieces)
                   if len(pieces) > 1 else line)
    return "\n".join(out)


def _inline_code(s):
    """エスケープ済みテキストの `x` を <code> にする(素のバッククォート除去)。"""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def oneliner_html(one):
    """「一行でいうと」を読める形に組む。

    短ければ従来どおり 1 行。長ければ **先頭の文を見出し**にし、残りは
    1 文 1 行に割って並べる(`ラベル=` で始まる文はラベルを太字にする)。
    """
    sents = _sentences(one)
    if len(sents) <= 1 and len(one) <= 80:
        return ('<div class="oneliner">💡 <b>一行でいうと</b> — '
                f'{_inline_code(html_escape(one))}</div>')
    lead, rest = sents[0], sents[1:]
    if not rest:                       # 1 文だが長い= 読点で折って並べる
        parts = _soft_wrap(lead, limit=80, chunk=40)
        lead, rest = parts[0], parts[1:]
    parts = ['<div class="ol-head">💡 一行でいうと</div>',
             f'<div class="ol-lead">{_inline_code(html_escape(lead))}</div>']
    for sent in rest:
        for i, piece in enumerate(_soft_wrap(sent, limit=110, chunk=48)):
            m = _LEAD_LABEL.match(piece) if i == 0 else None
            if m:
                txt = (f'<b>{_inline_code(html_escape(m.group(1) + m.group(2)))}</b> '
                       + _inline_code(html_escape(m.group(3))))
            else:
                txt = _inline_code(html_escape(piece))
            cls = "ol-s" if i == 0 else "ol-s cont"   # 続きの行には ▸ を付けない
            parts.append(f'<div class="{cls}">{txt}</div>')
    return '<div class="oneliner">' + "".join(parts) + "</div>"


def _choice_letters(repo, src):
    """その問題に実在する選択肢記号(A,B,C…)。比較表を全選択肢ぶん出すために使う。"""
    if not src:
        return []
    path = os.path.join(repo, src)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            return render_html.choice_letters(fh.read())
    except Exception:
        return []


def _one_liner(text):
    """`- 種別: `shape/kind` — <説明>` の説明部分を「一行でいうと」に使う。

    穴埋め形は `— 要点語: ...` が続くのでそこで切る。説明が無い形は空を返す。
    """
    m = re.search(r"^\s*[-*]\s*種別\s*[:：]\s*`[^`]*`\s*[—-]\s*(.+)$", text, re.M)
    if not m:
        return ""
    s = m.group(1).strip()
    s = re.split(r"\s*[—-]\s*要点語\s*[:：]", s)[0].strip()
    return s if len(s) > 8 else ""


_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def _tokens(s):
    return [t for t in re.split(r"[・,、\s]+", (s or "").strip()) if t and t != "-"]


def answer_compare_md(given, key, letters=()):
    """あなたの解答と正解を**並べる**(判定は ✅/❌ だけ・理由は本文で書く)。

    letters= その問題に実在する選択肢。渡せば選ばなかった肢も行に出す。
    """
    g, k = _tokens(given), _tokens(key)
    if k and all(t[0] in _CIRCLED for t in k):          # 穴埋め・組合せ形
        gmap = {t[0]: t[1:].lstrip("－-") for t in g if t and t[0] in _CIRCLED}
        out = ["| 空欄 | あなたの解答 | 正解 | |", "|---|---|---|---|"]
        for t in k:
            n, v = t[0], t[1:].lstrip("－-")
            mine = gmap.get(n) or "（無回答）"
            out.append(f"| {n} | {mine} | **{v}** | {'✅' if mine == v else '❌'} |")
        return "\n".join(out)
    gs, ks = set(g), set(k)                             # 選択形(単一・複数)
    out = ["| 選択肢 | あなたの解答 | 正解 | |", "|---|---|---|---|"]
    for letter in (list(letters) or sorted(gs | ks)):
        mine, ans = letter in gs, letter in ks
        mark = ("✅" if mine and ans else
                "❌ 余分" if mine else "❌ 選べていない" if ans else "")
        out.append(f"| {letter} | {'選んだ' if mine else '—'} | "
                   f"{'**正解**' if ans else '—'} | {mark} |")
    return "\n".join(out)


def explain_parts(repo, ref, key_path=None):
    """解説ページ1問ぶんの部品(仕込みの種別・seed は落とす)。"""
    text = _key_text(repo, ref, key_path)
    if not text:
        return {}
    why = _strip_meta(_section(text, "解説"))
    judge = _strip_meta(_section(text, "各選択肢の判定"))
    core = _strip_meta(_section(text, "教育核心")) or \
        _strip_meta(_section(text, r"★この分野の最重要知見"))
    verify = _strip_meta(_section(text, "検証コマンドと期待される出力"))
    note = _strip_meta(_section(text, "原典との記号対応"))
    return {"summary": _one_liner(text), "why": why, "judge": judge,
            "core": core, "verify": verify, "note": note}


# 解説ページ専用のテーマ(問題用紙= 試験シム風の白一色 とは意図的に別の見た目にする)
REPORT_CSS = """
body.report{background:#eef1f7}
body.report main{max-width:940px; background:#ffffff; margin:1.2rem auto;
  padding:1.4rem 1.6rem 4rem; border:1px solid #d8dee9; border-radius:14px;
  box-shadow:0 2px 12px rgba(16,24,40,.07)}
body.report h1{border-bottom:3px solid #4b5bd6; color:#1f2a55}
body.report h2{border-bottom:1px solid #dfe4ee; color:#33406b; margin-top:2.2rem}
body.report .nav{background:#1f2a55; border:none}
body.report .nav a{color:#cdd6ff}
body.report .nav .cur{color:#9aa6d8}
.scorebox{display:flex; align-items:baseline; gap:.9rem; color:#ffffff;
  background:linear-gradient(90deg,#4b5bd6,#7b88f2); border-radius:12px;
  padding:.85rem 1.2rem; margin:1rem 0 .6rem}
.scorebox .big{font-size:1.9rem; font-weight:700}
.scorebox .sub{font-size:.95rem; opacity:.93}
.jumps{margin:.2rem 0 1.4rem; font-size:.92rem}
.jumps .lead{color:#5a6580; margin-right:.4rem}
.jumps a{display:inline-block; margin:.15rem .3rem .15rem 0; padding:.12rem .6rem;
  border-radius:999px; background:#fdecec; color:#b3261e; text-decoration:none;
  border:1px solid #f3c7c7}
.jumps a:hover{background:#fbdada}
.qcard{border:1px solid #dfe4ee; border-radius:12px; padding:1rem 1.2rem .5rem;
  margin:1.1rem 0; background:#ffffff}
.qcard.ng{border-left:6px solid #d23f3f; background:#fffafa}
.qcard.ok{border-left:6px solid #1f9d55}
.qhead{display:flex; align-items:center; gap:.55rem; flex-wrap:wrap;
  margin-bottom:.4rem; padding-bottom:.45rem; border-bottom:1px dashed #e2e6f0}
.qhead .qno{font-size:1.12rem; font-weight:700; color:#1f2a55}
.qhead code{font-size:.8rem; color:#6b7280}
.badge{font-size:.8rem; font-weight:700; border-radius:999px; padding:.1rem .6rem}
.badge.ok{background:#e6f5ec; color:#1f7a45; border:1px solid #bfe3cd}
.badge.ng{background:#fdecec; color:#b3261e; border:1px solid #f3c7c7}
.slot{font-size:.78rem; color:#5a6580; background:#eef1f7; border-radius:6px;
  padding:.08rem .5rem}
.oneliner{background:#fff8e1; border:1px solid #f2d492; border-left:5px solid #e8a33d;
  border-radius:8px; padding:.7rem 1rem; margin:.9rem 0; font-size:.98rem;
  line-height:1.85}
.oneliner .ol-head{font-weight:700; color:#8a6d1f; font-size:.86rem;
  letter-spacing:.04em; margin-bottom:.35rem}
.oneliner .ol-lead{font-weight:700; color:#5c4708}
.oneliner .ol-s{margin-top:.34rem; padding-left:1.2em; text-indent:-1.2em}
.oneliner .ol-s::before{content:"▸ "; color:#c08b2c; font-weight:700}
.oneliner .ol-s.cont{margin-top:.1rem; text-indent:0}
.oneliner .ol-s.cont::before{content:""}
.oneliner .ol-s b{color:#8a6d1f}
.oneliner code{background:#fff2cc; border:1px solid #efdca6; border-radius:4px;
  padding:0 .25em}
/* 地の文は 1 文ごとに改行する(gen_pack._readable)。行間と行長を読みやすく */
body.report .qcard p, body.report .qcard li{line-height:1.9}
body.report .qcard>p, body.report .qcard>ul, body.report .qcard>ol{max-width:46em}
body.report .qcard li{margin:.4rem 0}
body.report .qcard ul, body.report .qcard ol{padding-left:1.4rem}
body.report .qcard :not(pre)>code{background:#eef1f7; border-radius:4px;
  padding:0 .25em}
body.report .qcard h4{font-size:.87rem; font-weight:700; color:#3b4a7a;
  margin:1.7rem 0 .45rem; padding-top:.55rem; border-top:1px dashed #edf0f6;
  display:flex; align-items:center; gap:.45rem}
body.report .qcard h4::before{content:""; width:.45rem; height:.45rem;
  border-radius:2px; background:#4b5bd6}
body.report .qcard h5{font-size:.95rem; color:#1f2a55; margin:.9rem 0 .3rem}
body.report table{border-collapse:collapse; font-size:.93rem; margin:.6rem 0}
body.report th{background:#f1f4fa; color:#33406b; border:1px solid #dfe4ee;
  padding:.35rem .7rem; text-align:left}
body.report td{border:1px solid #e6eaf3; padding:.32rem .7rem}
body.report tr.bad td{background:#fff1f1}
body.report tr.good td{background:#f5fbf7}
body.report blockquote{background:#f7f9fd; border:1px solid #dfe4ee;
  border-left:4px solid #9aa6d8; border-radius:8px}
body.report pre.code{background:#0f172a; border:none; border-radius:8px}
body.report pre.code code{color:#e5e9f5}
.qbody{background:#f8f9fc; border:1px solid #e2e6f0; border-left:4px solid #b9c2dd;
  border-radius:8px; padding:.35rem 1rem .8rem; margin:.7rem 0 .9rem; font-size:.95rem}
.qbody h5{color:#5a6580 !important; font-size:.82rem !important; font-weight:700;
  letter-spacing:.04em; margin:.7rem 0 .3rem !important}
.qbody ul{margin:.35rem 0 .35rem 1.1rem; padding:0}
.qbody li{margin:.18rem 0}
.qbody pre.code, .qbody pre.mermaid{background:#ffffff !important; border:1px solid #dfe4ee !important;
  border-radius:6px}
.qbody pre.code code{color:#0f172a !important}
.qfold{margin:.7rem 0 .9rem}
.qfold>summary{cursor:pointer; font-size:.82rem; font-weight:700; color:#5a6580;
  background:#f1f4fa; border:1px solid #e2e6f0; border-radius:8px; padding:.3rem .8rem;
  list-style:none}
.qfold>summary::marker{content:""}
.qfold>summary::before{content:"▸ "; color:#8a94b5}
.qfold[open]>summary::before{content:"▾ "}
.qfold .qbody{margin-top:.4rem}
.qlink{font-size:.78rem; margin-left:auto; color:#4b5bd6; text-decoration:none;
  border:1px solid #ccd3ef; border-radius:999px; padding:.08rem .55rem}
.qlink:hover{background:#eef1ff}
.whyline{display:inline-block; color:#5a6580; font-size:.9rem; background:#f8f9fc;
  border-left:3px solid #c9d2e8; border-radius:4px; padding:.1rem .5rem; margin:.1rem 0}
.miss{background:#ffe3e3; border-bottom:2px solid #d23f3f; border-radius:3px;
  padding:0 .15rem}
/* 出題文と採点の統合(2026-09-20): 選択肢の行に直接「あなた/正解」を出す */
.mk{font-size:.78rem; font-weight:700; border-radius:999px; padding:.06rem .5rem;
  white-space:nowrap; margin-right:.3rem}
.mk.ok{background:#e6f5ec; color:#1f7a45; border:1px solid #bfe3cd}
.mk.ng{background:#fdecec; color:#b3261e; border:1px solid #f3c7c7}
.mk.miss{background:#fff4e0; color:#a35b00; border:1px solid #f0d3a6}
body.report .qbody li:has(.mk.ok){background:#f2fbf5}
body.report .qbody li:has(.mk.ng){background:#fff5f5}
body.report .qbody li:has(.mk.miss){background:#fffaf0}
body.report .qbody li:has(.mk){border-radius:6px; padding:.18rem .45rem;
  margin:.3rem 0 .3rem -.45rem}
body.report .qbody li li{background:none !important; color:#4a5568;
  font-size:.92em; margin:.15rem 0}
body.report .qbody ul{list-style:none; padding-left:.2rem}
body.report .qbody ul ul{list-style:disc; padding-left:1.3rem}
/* 穴埋め形: 本文の空欄をその場で埋める */
.fill{border-radius:5px; padding:0 .3em; font-weight:600}
.fill.ok{background:#e6f5ec; border:1px solid #bfe3cd; color:#14613a}
.fill.ng{background:#fdecec; border:1px solid #f3c7c7; color:#8f1d16}
.fill.ng s{color:#b3261e; font-weight:400; opacity:.75}
.qhead .pick{font-size:.82rem; color:#33406b; background:#eef1ff;
  border:1px solid #ccd3ef; border-radius:6px; padding:.08rem .55rem}
.qhead .pick b{color:#1f2a55}
.qhead .pick i{font-style:normal; color:#8a94b5; margin:0 .25rem}
.qhead .pick.ok{background:#e6f5ec; border-color:#bfe3cd; color:#1f7a45}
.tag-miss{color:#b3261e; font-size:.86rem; font-weight:700; white-space:nowrap}
.tag-pick{color:#8a6d1f; font-size:.86rem; font-weight:700; white-space:nowrap}
.labnote{color:#5a6580; font-size:.92rem}
"""


def _question_md(repo, src, marks=None, fills=None, applied=None):
    """出題された問題文を解説カードに埋め込む形に整える。

    ・先頭の `# 問題 <ID>` と「機器に接続せずに解答」の注意書きは落とす
    ・見出しは h5 まで降格(カードの見出し階層に合わせる)
    ・選択肢の行は箇条書きにする(元の `.choice` 装飾はカード内では使わない)
    ・図(mermaid)とコードブロックはそのまま残す = 何を見て答える問題かが分かる

    ★2026-09-20(ユーザ指示「出題文と『あなたの解答と正解』は統合できないか」):
      `marks` = {記号: (バッジ, 理由)} を渡すと、**選択肢の行に採点結果と理由を併記**する
      (= 別表と「選択肢ごとの理由」節が要らなくなる)。
      `fills` = {丸数字: (状態, 正解記号, 正解語, あなたの記号, あなたの語)} を渡すと、
      本文中の ［n］ を**その場で埋める**(穴埋め形)。コードブロックの中だけは
      生 HTML が使えないので素のテキストで埋める。
      `applied` にリストを渡すと、**実際に印を付けられた記号・空欄番号**が入る
      (1つも付かなければ呼び出し側は従来の対比表に戻す)。
    """
    if not src:
        return ""
    path = os.path.join(repo, src)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out, in_fence, pending = [], False, ""
    def flush():                      # 設定ブロック選択肢の理由はブロックの**後**に置く
        nonlocal pending
        if pending:
            out.extend(["", f'<span class="whyline">{pending}</span>', ""])
            pending = ""
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            if not in_fence:
                flush()
            continue
        if fills:
            line, hit = _fill_blanks(line, fills, plain=in_fence)
            if applied is not None:
                applied += hit
        if not in_fence:
            if line.startswith("# "):
                continue                       # タイトル行(問題ID)は不要
            if line.startswith("> ") and "機器に接続せず" in line:
                continue                       # 解答時の注意書きは解説では不要
            if line.strip() in ("## 設問", "### 設問"):
                continue                       # パネル見出しと重複するので落とす
            if marks is not None and line.strip() in ("## 選択肢", "### 選択肢"):
                out += ["##### 選択肢 — あなたの解答・正解・理由", ""]
                continue
            if line.startswith("### "):
                line = "##### " + line[4:]
            elif line.startswith("## "):
                line = "##### " + line[3:]
            m = re.match(r"^([A-J])([.．)）])\s*(.+)$", line)
            if m:
                # 直前の空行を捨てて詰まった箇条書きにする(選択肢が間延びしない)
                if out and not out[-1].strip() and len(out) > 1 and \
                        out[-2].lstrip().startswith(("- ", "- **")):
                    out.pop()
                letter, body = m.group(1), m.group(3)
                badge, why = (marks or {}).get(letter, ("", ""))
                if badge and applied is not None:
                    applied.append(letter)
                line = f"- {badge}**{letter}.** {body}" if badge else \
                       f"- **{letter}.** {body}"
                out.append(line)
                if why:
                    out.append(f"  - {_readable(why)}")
                continue
            # 設定ブロックを選択肢にする形(`**A.**` の次行から ``` が続く)は
            # 箇条書きにできない(フェンスが入れ子にならない)。行の末尾に印を足す
            m = re.match(r"^\*\*([A-J])[.．)）]?\*\*\s*(.*)$", line.strip())
            if m and marks is not None:
                letter, body = m.group(1), m.group(2)
                badge, why = marks.get(letter, ("", ""))
                if badge and applied is not None:
                    applied.append(letter)
                flush()                 # 前の選択肢の理由が残っていれば先に出す
                if out and out[-1].strip():
                    out.append("")          # 直前が見出し/本文なら段落を分ける
                out.append(f"**{letter}.** {body} {badge}".rstrip())
                pending = _readable(why) if why else ""
                continue
        out.append(line)
    flush()
    # 解説ページに載せる再掲なので、地の文は文ごとに改行する(用紙そのものは変えない)
    return _readable("\n".join(out).strip())


# --------------------------------------------------------------------------
# 出題文と採点結果の統合(2026-09-20)
#   ・選択形= 選択肢の行に「あなたの解答／正解」と理由を併記する
#   ・穴埋め形= 本文の ［n］ をその場で埋め、誤答は取り消し線で併記する
# --------------------------------------------------------------------------
def _choice_pairs(repo, src):
    """その問題の [(記号, 選択肢の本文), ...]。"""
    if not src:
        return []
    path = os.path.join(repo, src)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            return render_html.choice_texts(fh.read())
    except Exception:
        return []


def _badge(mine, ans):
    if ans and mine:
        return '<span class="mk ok">✅ 正解＝あなたの解答</span> '
    if ans:
        return '<span class="mk miss">★ 正解（選べていない）</span> '
    if mine:
        return '<span class="mk ng">❌ あなたの解答</span> '
    return ""


def _judge_map(judge):
    """`- **A**: 理由` を {記号: 理由} に割る。対応しない行は注記として返す。"""
    by, rest, cur = {}, [], None
    for line in (judge or "").split("\n"):
        m = re.match(r"^\s*[-*]\s*\*\*([A-J])\*\*\s*[:：]?\s*(.*)$", line)
        if m:
            cur = m.group(1)
            by[cur] = m.group(2).strip()
        elif cur and line[:1] in (" ", "\t") and line.strip():
            by[cur] += " " + line.strip()      # ぶら下がりの続き行
        elif line.strip():
            cur = None
            rest.append(line)
    # 「(正解)」だけの行は情報が無いので落とす
    by = {k: v for k, v in by.items() if re.sub(r"[()（）\s]|正解", "", v)}
    return by, "\n".join(rest).strip()


def choice_marks(repo, src, given, key, judge, why=""):
    """選択形: ({記号: (バッジ, 理由)}, 判定節の残り, 解説節の残り)。

    理由は「各選択肢の判定」節から採るが、その節を持たず**解説の中で
    `- **A**: …` と並べている**ファミリもあるので、そちらも拾って本文へ移す
    (同じ選択肢の列挙がページに 2 回出るのを避ける)。
    """
    letters = [l for l, _ in _choice_pairs(repo, src)]
    g, k = set(_tokens(given)), set(_tokens(key))
    if not letters or not k or not k <= set(letters):
        return {}, judge, why
    by, rest_j = _judge_map(judge)
    by_w, rest_w = _judge_map(why)
    # 解説側は「選択肢の列挙」と確信できるときだけ動かす(別用途の箇条書き対策)
    if len(by_w) >= 2 and set(by_w) <= set(letters) and len(by_w) * 2 >= len(letters):
        by = {**by_w, **by}
    else:
        rest_w = why
    return ({l: (_badge(l in g, l in k), by.get(l, "")) for l in letters},
            rest_j, rest_w)


def cloze_fills(repo, src, given, key):
    """穴埋め形: {丸数字: (状態, 正解記号, 正解語, あなたの記号, あなたの語)}。"""
    texts = dict(_choice_pairs(repo, src))
    def parse(s):
        return {t[0]: t[1:].lstrip("－-") for t in _tokens(s)
                if t and t[0] in _CIRCLED}
    g, k = parse(given), parse(key)
    if not k:
        return {}
    fills = {}
    for n, kl in k.items():
        gl = g.get(n)
        fills[n] = ("ok" if gl == kl else "ng", kl, texts.get(kl, ""),
                    gl, texts.get(gl, "") if gl else "")
    return fills


def _fill_blanks(line, fills, plain=False):
    """本文中の ［n］ を答えで埋める(plain= コードブロック内なので素のテキスト)。

    戻り= (置換後の行, 埋めた空欄番号のリスト)。
    """
    hit = []
    def rep(m):
        n = m.group(1)
        if n not in fills:
            return m.group(0)
        hit.append(n)
        st, kl, ktxt, gl, gtxt = fills[n]
        ans = f"{kl}. {ktxt}" if ktxt else kl
        if plain:      # コードブロック内= 設定行を崩さないよう最短で埋める
            word = ktxt or kl
            if st == "ok":
                return f"［{n}］{word}"
            mine = (gtxt or gl) if gl else "無回答"
            return f"［{n}］{word}《あなた: {mine}》"
        if st == "ok":
            return (f'<span class="fill ok">［{n}］{html_escape(ans)}</span>')
        mine = f"{gl}. {gtxt}" if gl else "（無回答）"
        return (f'<span class="fill ng">［{n}］<s>{html_escape(mine)}</s> → '
                f'<b>{html_escape(ans)}</b></span>')
    return re.sub(r"［([①-⑳])］", rep, line), hit


def cloze_choice_marks(fills, letters):
    """穴埋め形の語群にも印を付ける(どの空欄の正解か・どこで誤って選んだか)。"""
    hit = {}
    for n, (st, kl, _kt, gl, _gt) in sorted(fills.items()):
        hit.setdefault(kl, []).append(f'<span class="mk ok">✅ {n} の正解</span> ')
        if st == "ng" and gl:
            hit.setdefault(gl, []).append(
                f'<span class="mk ng">❌ あなたは {n} に選んだ</span> ')
    return {l: ("".join(hit.get(l, [])), "") for l in letters}


def _strip_completed(why):
    """穴埋め形の解説から「完成文」節を落とす(本文を埋めたので重複するため)。"""
    return re.sub(r"^#{3,6}\s*完成文[^\n]*\n(?:(?!^#{1,6}\s).*\n?)*", "",
                  why or "", flags=re.M).strip()


def _diff_marks(given, key):
    """(取りこぼした空欄番号, 余分に選んだ肢, 選べなかった肢) を返す。"""
    g, k = _tokens(given), _tokens(key)
    if k and all(t[0] in _CIRCLED for t in k):
        gmap = {t[0]: t[1:].lstrip("－-") for t in g if t and t[0] in _CIRCLED}
        miss = [t[0] for t in k if gmap.get(t[0]) != t[1:].lstrip("－-")]
        return miss, set(), set()
    gs, ks = set(g), set(k)
    return [], gs - ks, ks - gs


def _mark_blanks(text, blanks):
    """解説本文の ［②］ のうち、取りこぼした空欄だけ色を付ける。"""
    for b in blanks:
        text = text.replace(f"［{b}］", f'<span class="miss">［{b}］</span>')
    return text


def _mark_judge(judge, picked, missed):
    """選択肢ごとの理由に「あなたが選んだ」「選べていない正解」の目印を足す。"""
    if not judge or not (picked or missed):
        return judge
    out = []
    for line in judge.split("\n"):
        m = re.match(r"^\s*[-*]\s*\*\*([A-J])\*\*", line)
        if m and m.group(1) in picked:
            line += ' <span class="tag-pick">← あなたが選んだ</span>'
        elif m and m.group(1) in missed:
            line += ' <span class="tag-miss">← これを選べていない</span>'
        out.append(line)
    return "\n".join(out)


def html_escape(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def explain_block(repo, no, ref, given, key, ok, slot, key_path=None, src=None):
    """1問ぶんの解説カード(見出し＋解答の並置＋なぜ＋選択肢＋記憶のフック)。

    カードの枠は生 HTML で出す(`render(allow_html=True)`)。中身は Markdown のまま
    書き、空行で挟むことで通常どおり解釈させる。
    """
    label = {"think": "思考系", "speed": "瞬発力", "cloze": "穴埋め"}.get(slot, "紙面")
    cls, badge = ("ok", "正解") if ok else ("ng", "誤答")
    p = explain_parts(repo, ref, key_path) or {}
    letters = _choice_letters(repo, src)
    # --- 出題文と採点結果を1つに畳む(2026-09-20) ---------------------------
    #   選択形= 選択肢の行に「あなたの解答／正解」＋理由 / 穴埋め形= 本文の ［n］ を埋める
    fills = cloze_fills(repo, src, given, key) if _CIRCLED[0] in (key or "") else {}
    marks, rest, rest_why = {}, p.get("judge", ""), p.get("why", "")
    if fills:
        marks = cloze_choice_marks(fills, letters)
    else:
        marks, rest, rest_why = choice_marks(repo, src, given, key,
                                             p.get("judge", ""), p.get("why", ""))
    applied = []
    qmd = _question_md(repo, src, marks=marks or None, fills=fills or None,
                       applied=applied)
    merged = bool(applied)      # 本文に印を付けられたときだけ対比表を省く
    if merged and not fills:
        p["judge"], p["why"] = rest, rest_why
    pick = (f'<span class="pick">あなた <b>{html_escape(given)}</b>'
            f'<i>／</i>正解 <b>{html_escape(key)}</b></span>' if not ok else
            f'<span class="pick ok">解答 <b>{html_escape(given)}</b></span>')
    out = [f'<section class="qcard {cls}" id="q{no}">', "",
           f'<div class="qhead"><span class="badge {cls}">{badge}</span>'
           f'<span class="qno">Q{no}</span><span class="slot">{label}</span>'
           f'{pick}<code>{html_escape(ref)}</code>'
           f'<a class="qlink" href="q{no}.html">問題ページ</a></div>', ""]
    if qmd:
        # 誤答カードは常に展開。正解カードは長文なら折りたたむ(図がある問題は
        # 閉じた <details> の中だと mermaid が描画に失敗するので常に展開する)
        fold = ok and len(qmd) > 1500 and "```mermaid" not in qmd
        head = "##### 出題された問題と採点" if merged else "##### 出題された問題"
        if fold:
            out += ["<details class=\"qfold\">",
                    "<summary>出題された問題と採点を開く</summary>",
                    '<div class="qbody">', "", qmd, "", "</div>", "</details>", ""]
        else:
            out += ['<div class="qbody">', "", head, "", qmd, "", "</div>", ""]
    if not merged:      # 併記できない形(組合せ表・記述式など)は従来どおり別表で出す
        out += ["#### あなたの解答と正解", "",
                answer_compare_md(given, key, letters), ""]
    if not p:
        return "\n".join(out + ["（この問題の解説は用意されていません）", "", "</section>", ""])
    miss_blanks, picked, missed = _diff_marks(given, key)
    why = _strip_completed(p["why"]) if fills else p["why"]
    why = _mark_blanks(why, miss_blanks)
    if not merged:
        p["judge"] = _mark_judge(p["judge"], picked, missed)
    if p["summary"]:
        one = p["summary"].replace("**", "")
        out += [oneliner_html(one), ""]
        # 種別行と解説本文が同文のファミリがある(svc/mpls 等)。二度書かない
        # ★整形(_readable)の**前**に突き合わせる(改行を入れると一致しなくなる)
        if why and (why == p["summary"] or why.startswith(p["summary"])):
            why = why[len(p["summary"]):].strip()
    if p["note"]:
        out += ["#### 出題の注記", "", _readable(p["note"]), ""]
    if why:
        out += ["#### なぜこの答えになるか", "", _readable(why), ""]
    if p["judge"]:
        head = "#### 選択肢についての補足" if merged else "#### 選択肢ごとの理由"
        out += [head, "", _readable(p["judge"]), ""]
    if p["verify"]:
        out += ["#### 実機での確かめ方", "", _readable(p["verify"]), ""]
    if p["core"]:
        out += ["#### 記憶のフック（この分野の核心）", "", _readable(p["core"]), ""]
    out += ["</section>", ""]
    return "\n".join(out)


def decorate_report(page_html):
    """採点済みの表に色を付ける(❌ の行＝赤・✅ の行＝緑の薄い背景)。"""
    def _row(m):
        row = m.group(0)
        if "❌" in row:
            return row.replace("<tr>", '<tr class="bad">', 1)
        if "✅" in row:
            return row.replace("<tr>", '<tr class="good">', 1)
        return row
    return re.sub(r"<tr>.*?</tr>", _row, page_html, flags=re.S)


def build_report(repo, pack_id, pdir, man, rows, lab_rows):
    """採点結果＋解説を1枚の HTML にまとめる(解説ページ)。

    並び= ①正答率 ②誤答へのジャンプ ③ラボの採点 ④解説(誤答→正解) ⑤成績一覧。
    **学習に使う順**に置く(長い成績表は最後)。
    ★未解答の問題については正解を書かない(まだ解ける状態を壊さないため)。
    """
    md = [f"# {pack_id} — 採点結果と解説", "",
          f'<p class="labnote">作成日 {man.get("created", "")} ／ 採点日 '
          f'{datetime.date.today().isoformat()}</p>', ""]
    papers = [r for r in rows if r[1] == "紙面" and r[4] not in ("-", "")]
    wrong = [r for r in papers if "不正解" in (r[5] or "")]
    if papers:
        got = len(papers) - len(wrong)
        md += [f'<div class="scorebox"><span class="big">{got} / {len(papers)}</span>'
               f'<span class="sub">紙面 正解'
               f'{"（全問正解）" if not wrong else ""}</span></div>', ""]
        if wrong:
            chips = "".join(f'<a href="#q{r[0]}">Q{r[0]}</a>' for r in wrong)
            md += [f'<div class="jumps"><span class="lead">誤答した問題'
                   f'（クリックで解説へ）:</span>{chips}</div>', ""]
    if lab_rows:
        md += ["## ラボの採点", "",
               "| # | 問題 | 得点 | 未充足のチェック |",
               "|---|------|------|------------------|"]
        for no, ref, g, total, fails in lab_rows:
            if fails:
                f = "<br>".join(fails)
            else:   # 満点でないのにチェック名が無い= 再描画で拾えなかったとき
                f = "（なし・全 PASS）" if str(g) == str(total) else "（記録なし）"
            md.append(f"| Q{no} | `{ref}` | **{g}/{total}** | {f} |")
        md += ["", '<p class="labnote">※ ラボの模範 config はこのページには載せない'
               '（従来どおり、求められたときに出す）。</p>', ""]
    # --- 解説: 誤答を先に、正解は確認用に後ろへ -------------------------------
    key_paths = {it["no"]: it.get("key") for it in man["items"]}
    slots = {it["no"]: it.get("slot") for it in man["items"]}
    srcs = {it["no"]: it.get("src") for it in man["items"]}
    right = [r for r in papers if r not in wrong]
    if wrong:
        md += ["", "## 解説 — まず誤答した問題", ""]
        for no, kind, ref, given, key, note, dur in wrong:
            md += [explain_block(repo, no, ref, given, key, False,
                                 slots.get(no), key_paths.get(no),
                                 srcs.get(no)), ""]
    if right:
        md += ["", "## 解説 — 正解した問題（確認用）", ""]
        for no, kind, ref, given, key, note, dur in right:
            md += [explain_block(repo, no, ref, given, key, True,
                                 slots.get(no), key_paths.get(no),
                                 srcs.get(no)), ""]
    # --- 一覧(長いので最後) ---------------------------------------------------
    md += ["", "## 成績一覧", "",
           "| # | 種別 | 問題 | あなたの解答 | 正解 | 判定 | 所要 |",
           "|---|------|------|------|------|------|------|"]
    total_s = 0
    for no, kind, ref, given, key, note, dur in rows:
        link = f"[Q{no}](#q{no})" if (kind == "紙面" and key not in ("-", "")) else f"Q{no}"
        md.append(f"| {link} | {kind} | `{ref}` | {given} | {key} | {note} | {dur} |")
        m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d\d)(?:\(自\))?", dur or "")
        if m:
            total_s += int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    if total_s:
        h, rem = divmod(total_s, 3600)
        md += ["", f'<p class="labnote">計測合計 <b>{h}:{rem // 60:02d}:{rem % 60:02d}</b>'
               f'（ストップウォッチ計測分のみ・(自)=自動開始）</p>']
    return "\n".join(md) + "\n"


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


def todays_packs(repo):
    """今日ぶんのパックID(PACK-YYYYMMDD / -B / -C …)を古い順に返す。★BL-205"""
    base = f"PACK-{datetime.date.today().strftime('%Y%m%d')}"
    return sorted(os.path.basename(d)
                  for d in glob.glob(os.path.join(repo, PACKS, base + "*"))
                  if os.path.isdir(d))


def latest_pack(repo):
    dirs = sorted(glob.glob(os.path.join(repo, PACKS, "PACK-*")))
    if not dirs:
        sys.exit("パックがありません(先に new を実行)")
    return os.path.basename(dirs[-1])


def cmd_new(a):
    """パックを --packs 本まとめて作る(既定3本・BL-205)。

    配分は**1日全体**で決める: 必須ジャンルを全パックへ配り分け、先行パックで
    出した (shape/kind) を後続の抽選から外す。ラボは1本目にだけ付ける。
    """
    repo = os.path.abspath(a.repo)
    n_packs = max(1, a.packs)
    rnd = random.Random(a.seed if a.seed is not None
                        else random.randrange(1, 10 ** 9))
    plan = plan_genres(a.require_shape, n_packs, rnd)
    a._paper_rot = None
    if getattr(a, "paper_rotation", False):
        # ★BL-224: 必須ジャンルは使わず、3 枠とも単元ローテーションで 1 問ずつ割り当てる
        import lab_rotation
        import paper_rotation
        rday = (datetime.date.fromisoformat(a.lab_date) if a.lab_date
                else lab_rotation.quota_today(repo))
        a._paper_rot = paper_rotation.PaperRotation(repo, a.lab_mode, rday, rnd)
        plan = [[] for _ in range(n_packs)]
        for line in a._paper_rot.describe():
            print(line)
    if n_packs > 1:
        print(f"== {n_packs} パックを作る(思考{a.paper}・瞬発{a.speed}・穴埋め{a.cloze}"
              f"／ラボは1本目のみ)")
        for i, gs in enumerate(plan, 1):
            if a._paper_rot is None:
                print(f"   {i} 本目の必須ジャンル: {', '.join(gs) or '(なし)'}")
        if a._paper_rot is not None:
            print("   紙面: 単元ローテーション(必須ジャンルなし・全単元を最終実施日の古い順に)")
    made, exclude = [], set()
    for i in range(n_packs):
        seed_override = (None if a.seed is None else a.seed + i * 9001)
        # ★--pack-id を明示した時は 2 本目以降を <ID>-2, -3 … にする
        #   (既定の日付ID なら default_pack_id が -B/-C を振る)
        pid_i = a.pack_id if i == 0 else (f"{a.pack_id}-{i + 1}" if a.pack_id else None)
        pid, kinds = build_pack(a, pack_no=i + 1, n_packs=n_packs,
                                require=plan[i], exclude=exclude,
                                pack_id=pid_i, seed_override=seed_override)
        made.append(pid)
        exclude |= kinds
    if n_packs > 1:
        print("\n== 作成したパック ==")
        for pid in made:
            print(f"  {pid}: {os.path.join(pack_dir(repo, pid), 'index.html')}")
        print(f"採点は `scripts/pack.sh grade --today --no-lab`(紙面のみ)/"
              f"`scripts/pack.sh grade {made[0]}`(ラボ込み)")
    return made


def build_pack(a, pack_no=1, n_packs=1, require=None, exclude=(),
               pack_id=None, seed_override=None):
    """パックを1本作る。戻り値= (pack_id, この回に出した kind の集合)。

    ★BL-205: 1日3パック運用では 2 本目以降を紙面だけ(paper_only)にし、
      `exclude`(先行パックで出した shape/kind)を抽選から外して回す。
    """
    repo = os.path.abspath(a.repo)
    today = datetime.date.today()
    paper_only = a.paper_only or pack_no > 1
    pack_id = pack_id or (a.pack_id if pack_no == 1 else None) \
        or default_pack_id(repo, today)
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

    seed = (seed_override if seed_override is not None
            else a.seed if a.seed is not None else random.randrange(1, 10 ** 9))
    rnd = random.Random(seed)
    log(f"===== {pack_id} 生成開始 (seed={seed}, dry_run={a.dry_run}"
        f"{f', {pack_no}/{n_packs} 本目' if n_packs > 1 else ''}) =====")
    if exclude:
        log(f"[紙面] 先行パックと同じ型を除外: {len(exclude)} 種")
    if PROFILE:
        log(f"[profile] {PROFILE['label']}: 単元 {len(PROFILE['units'])}"
            f"({', '.join(PROFILE['units'][:12])}{'…' if len(PROFILE['units']) > 12 else ''})"
            f" / 紙面グロブ {len(PROFILE['paper_kinds'])} / ラボ genre {PROFILE['lab_genres'] or '(なし)'}"
            f" / ラボ候補 {len(PROFILE['lab_ids'])}")

    used, per = cml_started_nodes(repo)
    if used is None:
        used, per = leased_nodes(repo)
        log(f"[台数] ★CML に問い合わせできず、リース台帳で代用: {used} ノード")
    log(f"[台数] CML 起動中 {used} ノード {per or '(なし)'} / 予算 {a.budget}")
    if a.dry_run and a.assume_used is not None:
        # ★選定ロジックの確認用(BL-158)。構築しない dry-run でだけ稼働台数を上書きできる
        log(f"[台数] dry-run: 稼働台数を {used} → {a.assume_used} と仮定して選定する")
        used = a.assume_used

    # --- 紙面フェーズ ---
    require = (list(require) if require is not None else
               plan_genres(a.require_shape, 1, rnd)[0])
    n_paper = resolve_paper_count(a.paper, rnd)
    # ★明示指定された紙面(--extra-paper)を先に取り込み、その数だけ自動調達を減らす
    extra_papers = []
    for rel in (a.extra_paper or []):
        rel = os.path.relpath(os.path.abspath(rel), repo)
        if not os.path.exists(os.path.join(repo, rel)):
            log(f"[紙面] ★--extra-paper が見つからない: {rel}")
            continue
        if "/questions/" in rel:
            key = rel.replace("/questions/", "/answers/")
        else:
            key = os.path.join("answers", os.path.basename(rel))
        extra_papers.append({"ref": os.path.splitext(os.path.basename(rel))[0],
                             "src": rel, "key": key})
    if extra_papers:
        log(f"[紙面] 明示指定 {len(extra_papers)} 問: "
            + ", ".join(e["ref"] for e in extra_papers))
    if not a.no_pool:
        # ★別置きの紙面プール(private/paper_pools.yml)からの抽選も明示指定と同じ扱い
        extra_papers += pool_papers(
            repo, rnd, today, log, exclude={pool_base(e["ref"]) for e in extra_papers})
    n_on_top = sum(1 for e in extra_papers if e.get("extra"))
    n_auto = max(0, n_paper - (len(extra_papers) - n_on_top))
    log(f"[紙面] 問題数: {n_paper + n_on_top} 問(指定={a.paper}) / 自動調達 {n_auto} 問 / "
        f"必須ジャンル {require or '(なし)'}")
    n_paper_total, n_paper = n_paper + n_on_top, n_auto
    if a.dry_run:
        stamps = borrow_papers(repo, n_paper, today)
        log(f"[紙面] dry-run: 既出の紙面を {len(stamps)} 問借用"
            f"(必須ジャンルの個別生成は実生成時のみ)")
    elif n_paper <= 0:
        # ★BL-133: 0問指定でも必須ジャンル確保ループが走り、パック未収載の
        #   孤児 questions/answers が残っていた → 紙面フェーズごとスキップ
        stamps = []
        log("[紙面] 0問指定のため紙面フェーズをスキップ(必須ジャンルも生成しない)")
    elif getattr(a, "_paper_rot", None):
        stamps = gen_rotation_papers(repo, a._paper_rot, "think", n_paper, seed + 7000,
                                     a, log, exclude)
    else:
        stamps, _got = gen_papers(repo, n_paper, seed, a.shape, a.exam, a.hard,
                                  log, require=require, rnd=rnd,
                                  exclude=exclude)
    if len(stamps) < n_paper:
        log(f"[紙面] ★不足: {len(stamps)}/{n_paper} 問しか用意できなかった")

    # --- 瞬発力枠(即答形・別枠) --------------------------------------------
    # ★2026-09-13 ユーザ指示: 「深くないが瞬発力で答える問題」を思考系とは別枠で
    #   既定で入れる。思考系(--paper)の数は減らさず、この枠ぶんを上乗せする。
    #   shape=svc は 1 回の生成で kind が重複しない(kinds[i % 9])ので 5 問=5 種。
    speed_stamps = []
    if a.speed > 0:
        if a.dry_run:
            log(f"[紙面] dry-run: 瞬発力枠 {a.speed} 問(shape={a.speed_shape})は実生成時のみ")
        else:
            # ★BL-185 二次是正: 思考系で既に出した shape/kind は瞬発力枠から外す(同 kind の連発防止)
            _think_kinds = []
            for _st in stamps:
                try:
                    _m = re.search(r"種別: `([a-z0-9]+/[a-z0-9_]+)`", open(f"{repo}/answers/{_st}.md", encoding="utf-8").read())
                    if _m:
                        _think_kinds.append(_m.group(1))
                except OSError:
                    pass
            _ex = set(_think_kinds) | set(exclude)      # ★BL-205: 先行パックぶんも外す
            _extra = _exclude_args(_ex)
            if _think_kinds:
                log(f"[紙面] 瞬発力枠から除外(思考系と同 kind): {sorted(set(_think_kinds))}")
            if getattr(a, "_paper_rot", None):
                speed_stamps = gen_rotation_papers(repo, a._paper_rot, "speed", a.speed,
                                                   seed + 31000, a, log, _ex)
            else:
                speed_stamps = _run_paper_gen(repo, seed + 31000, a.speed,
                                              a.speed_shape, a.exam, a.hard, log,
                                              f"瞬発力枠[{a.speed_shape}]", extra_args=_extra)
            if len(speed_stamps) < a.speed:
                log(f"[紙面] ★瞬発力枠 不足: {len(speed_stamps)}/{a.speed} 問")
        log(f"[紙面] 瞬発力枠: {len(speed_stamps)} 問(shape={a.speed_shape}"
            f"・思考系 {n_paper_total} 問とは別枠)")

    # --- 穴埋め枠(解説穴埋め形・別枠・BL-191) -------------------------------------
    # ★2026-09-19 ユーザ指示: 「問題を解きながら解説も頭に入れる」穴埋め形を新規ジャンルとして
    #   5 問程度、思考系・瞬発力枠とは別枠で毎パックに混ぜる。shape=cloze は 1 実行で kind が
    #   重複せず(kinds[i % n])、--avoid-recent-days で直近に出た kind を後ろへ回す。
    cloze_stamps = []
    if a.cloze > 0:
        if a.dry_run:
            log(f"[紙面] dry-run: 穴埋め枠 {a.cloze} 問(shape=cloze)は実生成時のみ")
        else:
            if getattr(a, "_paper_rot", None):
                cloze_stamps = gen_rotation_papers(repo, a._paper_rot, "cloze", a.cloze,
                                                   seed + 47000, a, log, exclude)
            else:
                cloze_stamps = _run_paper_gen(repo, seed + 47000, a.cloze, "cloze",
                                              a.exam, False, log, "穴埋め枠[cloze]",
                                              extra_args=_exclude_args(exclude))
            if len(cloze_stamps) < a.cloze:
                log(f"[紙面] ★穴埋め枠 不足: {len(cloze_stamps)}/{a.cloze} 問")
        log(f"[紙面] 穴埋め枠: {len(cloze_stamps)} 問(shape=cloze・思考系/瞬発力枠とは別枠)")

    papers = []
    for st in stamps:
        src = f"questions/{st}.md"          # manifest には repo 相対で持つ
        key = f"answers/{st}.md"
        form = "essay" if _is_essay(repo, st) else "mcq"
        papers.append({"kind": "paper", "ref": st, "src": src,
                       "key": key, "form": form, "slot": "think",
                       "state": "未着手"})
    for e in extra_papers:
        papers.append({"kind": "paper", "ref": e["ref"], "src": e["src"],
                       "key": e["key"], "form": "mcq", "slot": "think",
                       "state": "未着手"})
    for st in speed_stamps:
        papers.append({"kind": "paper", "ref": st, "src": f"questions/{st}.md",
                       "key": f"answers/{st}.md", "form": "mcq",
                       "slot": "speed", "state": "未着手"})
    for st in cloze_stamps:
        papers.append({"kind": "paper", "ref": st, "src": f"questions/{st}.md",
                       "key": f"answers/{st}.md", "form": "mcq",
                       "slot": "cloze", "state": "未着手"})
    for _ in range(n_paper - len(stamps)):
        papers.append({"kind": "paper", "ref": "(未生成)", "src": "",
                       "state": "準備失敗", "error": "紙面の生成に失敗"})
    # ★明示指定ぶんが末尾に固まらないよう、紙面のなかで並びを混ぜる
    rnd.shuffle(papers)
    items, no = [], 0
    for it in papers:
        no += 1
        it["no"] = no
        items.append(it)
    n_paper = n_paper_total + len(speed_stamps)

    # --- ラボ選定フェーズ ---
    cat = parse_catalog(repo)
    hist = parse_history(repo)
    n_lab = 0 if paper_only else a.lab
    n_extra = 0 if paper_only else a.lab_extra
    if paper_only:
        log("[選定] 紙面だけのパック: ラボは作らない(CML のラボ枠を使わない)"
            + ("" if a.paper_only else f" — {pack_no} 本目(ラボは1本目に集約)"))
    genres = [g.strip() for g in (a.lab_genres or "").split(",") if g.strip()]
    if getattr(a, "rotation", False) and not paper_only:
        # ★BL-223: 単元ローテーション(曜日表＋遅れ補正)。日付/曜日はノルマ日(JST 04:00 境界)
        import lab_rotation
        rday = (datetime.date.fromisoformat(a.lab_date) if a.lab_date
                else lab_rotation.quota_today(repo))
        mode = lab_rotation.load_mode(repo, a.lab_mode)
        n_total = mode["slots"] if a.lab is None else a.lab
        n_disc = mode["discovery"]["slots"] if a.discovery is None else a.discovery
        if n_total <= n_disc:
            n_disc = 0                    # 本数を絞った回は単元ローテーションを優先する
        # ★BL-233: 発掘枠を先に取る(後回しにすると大型の候補が台数予算に入らず永久に出ない)。
        #   同じ単元を同じ日に 2 本出さないよう、発掘枠が当たった単元は今日のローテーションから外す。
        disc_labs, dnotes, disc_nodes = select_discovery_labs(
            cat, hist, mode=mode, count=n_disc, budget=a.budget, used=used, rnd=rnd,
            today=rday, repo=repo, log=log, allow_non_cisco=a.allow_non_cisco,
            allow_automation=a.allow_automation)
        matchers = lab_rotation.unit_matchers(mode, LAB_GENRES)
        skip = {u for u in (lab_rotation.unit_of(lb["id"], matchers) for lb in disc_labs) if u}
        labs, notes, used_nodes = select_rotation_labs(
            cat, hist, mode_name=a.lab_mode, count=n_total - len(disc_labs), budget=a.budget,
            used=used + disc_nodes, rnd=rnd, family_days=a.family_days, today=rday, log=log,
            build_rate=a.build_rate, repeat_days=a.repeat_days, repo=repo, exclude_units=skip,
            allow_build=not any(lb["build"] for lb in disc_labs))
        labs, notes, used_nodes = labs + disc_labs, notes + dnotes, used_nodes + disc_nodes
    else:
        labs, notes, used_nodes = ([], [], 0) if n_lab <= 0 else select_genre_labs(
            cat, hist, genres=genres, count=n_lab, budget=a.budget, used=used,
            rnd=rnd, family_days=a.family_days, today=today, log=log,
            build_rate=a.build_rate, repeat_days=a.repeat_days)
    # ★大型ラボ(MPLS 12 台等)を選んだ日は追加枠を使わない(BL-158)
    if n_extra > 0 and any(lb.get("big") for lb in labs):
        notes.append("追加枠: 大型ラボを選んだので使わない")
        n_extra = 0
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
            allow_automation=a.allow_automation, ts_only=not a.any_lab,
            only=(PROFILE["lab_ids"] if PROFILE else None))
        chosen_tags = {t for lb in labs for t in lb.get("tags", [])}
        chosen_ids = {lb["id"] for lb in labs}
        # ★同一ファミリ(同じ生成器)の二重選定を防ぐ(2026-08-22: タグ推定が空の
        #   生成器が分野重複チェックをすり抜け、固定枠+追加枠で重複した)
        extra = [e for e in extra
                 if e["id"] not in chosen_ids
                 and not (chosen_tags & set(e.get("tags", [])))]
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
              "nodes": lb["nodes"], "state": "未着手",
              "genre": lb.get("genre", ""), "unit": lb.get("unit", ""),
              "pool": lb.get("pool", ""),          # 発掘枠の候補キー(discovery_last_issued が読む)
              "est": int(lb.get("minutes") or 60)}
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
            prob_id = gen_instance(repo, lb["script"], rnd.randrange(1000, 99999), log, lb.get("args"))
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
        fh.write(render_html.render(idx, title=f"{pack_id} — Question Pack",
                                    nav=build_nav(items, 0, pack_id),
                                    mermaid_mode=a.mermaid))
    log(f"[出力] 図の描画方法: {a.mermaid}")
    sheet = os.path.join(pdir, "解答.md")
    # ★2026-09-22: dry-run も packs/<ID>/ に出力するため、同日の下見と同じ ID を本番が採番すると
    #   下見の解答用紙(別の問題)が残っていた。前回の出力が dry-run なら上書きする。
    import yaml
    old_mf = os.path.join(pdir, "manifest.yml")
    prev_dry = False
    if os.path.exists(old_mf):
        try:
            prev_dry = bool((yaml.safe_load(open(old_mf, encoding="utf-8")) or {}).get("dry_run"))
        except Exception:
            prev_dry = False
    if os.path.exists(sheet) and not (prev_dry and not a.dry_run):
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
    return pack_id, kinds_of_stamps(repo, stamps + speed_stamps + cloze_stamps)


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
        prob_id = gen_instance(repo, lb["script"], rnd.randrange(1000, 99999), log, lb.get("args"))
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
        fh.write(render_html.render(idx, title=f"{pack_id} — Question Pack",
                                    nav=build_nav(items, 0, pack_id),
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
        fh.write(render_html.render(idx, title=f"{pack_id} — Question Pack",
                                    nav=build_nav(items, 0, pack_id),
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
        ans = (f"  解答={fmt_answer(s.get('answer'))}"
               if s.get("answer") else "")
        dur = (f"  所要={s['duration']}{'(自)' if s.get('dur_auto') else ''}"
               if s.get("duration") else "")
        slot = {"speed": " (瞬発)", "cloze": " (穴埋め)", "think": ""}.get(it.get("slot"), "")
        print(f"  Q{it['no']} [{it.get('kind')}{slot}] {it.get('ref')}  {mark}{ans}{dur}")
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
    report_only = getattr(a, "report_only", False)   # 解説ページの組み直しだけ
    rows, lab_rows, correct, gradable, lab_graded = [], [], 0, 0, False

    for it in man["items"]:
        s_it = sheet.get(it["no"], {})
        # 所要時間(BL-144)。"(自)" = スタート押し忘れ→初回入力で自動開始した計測
        dur = (s_it.get("duration") or "-") + ("(自)" if s_it.get("dur_auto") else "")
        dmemo = f"所要 {dur}" if dur != "-" else ""
        if it.get("kind") == "paper":
            # choice_of / key_of は整列済みの記号列を返す("D" / "BD")。
            # 複数選択は**過不足なしで正解**なので、文字列一致がそのまま集合一致。
            key, why = key_of(repo, it.get("ref", ""), it.get("key"))
            if is_match_key(key):
                # 組合せ形(BL-168): 正規形どうし(項目順・「・」区切り)の文字列一致
                given = match_of(s_it.get("answer"))
                gs, ks = given, key
            else:
                given = choice_of(s_it.get("answer")) or ""
                gs = "・".join(given)
                ks = "・".join(key) if key else ""
            if key is None:
                rows.append((it["no"], "紙面", it.get("ref", ""), gs or "-", "-",
                             why or "自動採点不可(Claude が採点)", dur))
            elif not given:
                rows.append((it["no"], "紙面", it.get("ref", ""), "(未記入)", "-",
                             "未解答", dur))
            else:
                gradable += 1
                ok = given == key
                correct += 1 if ok else 0
                note = "正解" if ok else "不正解"
                if not ok and is_match_key(key):
                    kp, gp = key.split("・"), given.split("・")
                    note += f"(一致 {len(set(kp) & set(gp))}/{len(kp)})"
                elif not ok and len(key) > 1:
                    g, k = set(given), set(key)
                    if g < k:
                        note += "(選択が不足)"
                    elif g > k:
                        note += "(選択が過剰)"
                rows.append((it["no"], "紙面", it.get("ref", ""), gs, ks, note, dur))
                if report_only:      # 再描画のときは二重記録しない
                    continue
                history_upsert(repo, it["ref"], state="採点済", paper=True,
                               score=f"{'正解' if ok else '不正解'}({ks})",
                               memo=f"パック {pack_id} の Q{it['no']}")
                # ノルマ台帳(BL-114): 採点が確定した瞬間の JST で記録する
                quota.log_attempt(repo, "paper", it["ref"],
                                  result="ok" if ok else "ng",
                                  src=f"pack:{pack_id}", memo=dmemo, quiet=True)
        else:
            ref = it.get("ref", "")
            if a.no_lab or report_only or it.get("error"):
                prev = it.get("lab_score") if report_only else None
                if prev:            # 前回の採点結果をそのまま載せ直す
                    got, _, total = prev.partition("/")
                    fails = [f for f in (it.get("lab_fails") or "").split("｜") if f]
                    lab_rows.append((it["no"], ref, got, total, fails))
                    rows.append((it["no"], "ラボ", ref, "-", "-", f"{prev} 点", dur))
                else:
                    rows.append((it["no"], "ラボ", ref, "-", "-", "ラボ採点は省略",
                                 dur))
                continue
            print(f"  Q{it['no']} [ラボ] {ref}: 採点中…", flush=True)
            got, total, why = grade_lab(repo, ref, it.get("variant"))
            if got is None:
                rows.append((it["no"], "ラボ", ref, "-", "-", f"採点できず({why})",
                             dur))
                continue
            fails = why if isinstance(why, list) else []
            lab_rows.append((it["no"], ref, got, total, fails))
            # --report-only で組み直すときのために結果を manifest に残す
            it["lab_score"] = f"{got}/{total}"
            it["lab_fails"] = "｜".join(f.replace("\n", " ") for f in fails)
            lab_graded = True
            rows.append((it["no"], "ラボ", ref, "-", "-", f"{got}/{total} 点", dur))
            history_upsert(repo, ref, state="採点済", score=str(got),
                           memo=f"パック {pack_id} の Q{it['no']}")
            quota.log_attempt(repo, "lab", ref, score=got, total=total,
                              src=f"pack:{pack_id}", memo=dmemo, quiet=True)

    print(f"== {pack_id} 採点", flush=True)
    for no, kind, ref, given, key, note, dur in rows:
        extra = f" 解答={given} 正解={key}" if kind == "紙面" else ""
        dtxt = f"（所要 {dur}）" if dur != "-" else ""
        print(f"  Q{no} [{kind}] {ref}:{extra} … {note}{dtxt}")
    if gradable:
        print(f"  -- 紙面 MCQ {correct}/{gradable} 問正解")

    if lab_graded:      # ラボの結果を manifest に残す(--report-only の再描画用)
        write_manifest(pdir, {"pack_id": pack_id, "created": man.get("created", ""),
                              "dry_run": False, "seed": man.get("seed", ""),
                              "items": man["items"],
                              "notes": man.get("notes", [])})
    md = build_report(repo, pack_id, pdir, man, rows, lab_rows)
    out = os.path.join(pdir, "report.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(decorate_report(render_html.render(
            md, title=f"{pack_id} — 採点結果と解説",
            nav=[{"label": "問題パックの目次", "href": "index.html"},
                 {"label": "採点結果と解説", "href": "report.html", "current": True}],
            mermaid_mode=a.mermaid, extra_css=REPORT_CSS,
            body_class="report", allow_html=True)))
    print(f"  レポート: {out}")
    # ★index.html に解説ページへのリンクを足して貼り替える(2026-09-20 ユーザ指示)
    try:
        idx = index_md(pack_id, man["items"], man.get("notes", []),
                       man.get("dry_run") == "true", report=True)
        with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(render_html.render(idx, title=f"{pack_id} — Question Pack",
                                        nav=build_nav(man["items"], 0, pack_id),
                                        mermaid_mode=a.mermaid))
    except Exception as e:                 # 目次の更新失敗で採点自体は壊さない
        print(f"  ★index.html の更新に失敗（解説は {out} から開ける）: {e}")
    # ノルマ台帳(BL-114): 採点直後に当日の進捗を出す
    cfg = quota.config(repo)
    print(quota.render_today(quota.summarize(
        repo, quota.quota_day(quota.now_jst(), cfg["day_start"]))))


def grade_lab(repo, prob_id, variant=None, timeout=1800, _retry=True):
    """grade.yml を実走して (得点, 満点, 未充足チェック名) を返す。

    ★2026-09-26: 得点行が読めなかったら **bringup を挟んで 1 度だけ再試行**する。
      IOSvL2 は provision 時に救済しても、しばらく経つと mgmt(Vlan999)が再び固着して
      telnet 収集が丸ごと失敗する(= 採点できず)。実際に PACK-20260926-D で発生した。
    """
    got, total, fails = _grade_lab_once(repo, prob_id, variant, timeout)
    if got is None and _retry and fails == "得点行を読めず":
        log = print
        log(f"[採点] {prob_id}: 得点行が読めず → bringup を試して再採点する")
        try:
            bringup(repo, prob_id, log)
        except Exception as e:
            log(f"[採点] {prob_id}: bringup 失敗 {e}")
        return _grade_lab_once(repo, prob_id, variant, timeout)
    return got, total, fails


def _grade_lab_once(repo, prob_id, variant=None, timeout=1800):
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
    ap.add_argument("--extra-paper", action="append", default=[],
                    metavar="PATH",
                    help="紙面問題を明示指定して混ぜる(repo 相対の questions md・複数可)。"
                         "正解キーはパス中の /questions/ を /answers/ に置換して探す。"
                         "指定したぶんだけ自動生成・借用の数が減る")
    ap.add_argument("--no-pool", action="store_true",
                    help="private/paper_pools.yml の紙面プールから抽選しない")
    ap.add_argument("--packs", type=int, default=3,
                    help="1回の new で作るパック数(既定3・BL-205 2026-09-20 ユーザ指示)。"
                         "2本目以降は紙面だけ(ラボは1本目に集約)・必須ジャンルは"
                         "全パックへ配り分け・既出 kind は後続から除外する")
    ap.add_argument("--speed", type=int, default=3,
                    help="瞬発力枠(即答形)の問題数。思考系(--paper)とは別枠で"
                         "上乗せする(既定3・2026-09-28「1パック7問程度」。旧 8(3×8=24)・"
                         "その前は単発15問)")
    ap.add_argument("--cloze", type=int, default=2,
                    help="穴埋め枠(解説穴埋め形 shape=cloze・BL-191)の問題数。思考系・瞬発力枠とは"
                         "別枠で上乗せする(既定2・2026-09-28「1パック7問程度」。旧5・0 で無効)")
    ap.add_argument("--speed-shape", default="speed",
                    help="瞬発力枠の shape(既定 speed= svc 型ファミリ(svc/fhs/ospfdbg/dhcp6/dmvpn …)の"
                         "即答 kind を問題ごとに抽選。svc を指定すると従来どおり Services のみ)")
    ap.add_argument("--paper-only", action="store_true",
                    help="紙面だけのパックにする(ラボを作らない=CMLのラボ枠を使わない)")
    ap.add_argument("--require-shape", default="auto",
                    help="紙面の必須ジャンル(カンマ区切り。"
                         f"選択肢: {','.join(PAPER_GENRES)})。"
                         "既定 auto= 全パックへ配り分け(3パックなら 4/3/3 ジャンルで"
                         "1日に全ジャンルを1周)。明示指定すると全パックに同じ必須枠を課す")
    ap.add_argument("--lab", type=int, default=None,
                    help="ラボ数(既定= 単元ローテーションは lab_modes.yml の slots=3・"
                         "--lab-genres/--profile 指定時は 2)")
    # ★既定に ipsla を追加(2026-08-22 ユーザ指示「既定の抽選に混ぜられるように」)。
    #   4ジャンルのシャッフルから2つ選ぶ形になる。
    # ★BL-158(2026-09-07): mpls(TS 12 台)・vpnbuild/mplsbuild(構築の静的ローテーション)を既定に追加。
    #   構築ジャンル(rtctl/v6build/vpnbuild/mplsbuild)は --build-rate の構築スロット 1 本からのみ。
    # ★2026-09-19(ユーザ指示・ブループリント突合せ報告の推奨4): bgp(リングBGP TS)・
    #   urpf(TS)・aaa(構築スロット)を既定に追加= ラボ既定に BGP/Security が無かった穴を塞ぐ。
    # ★BL-223(2026-09-27): 既定は単元ローテーション(--lab-mode)。--lab-genres を明示した時だけ
    #   従来の固定ジャンル抽選(select_genre_labs)。--profile 時の既定は全ジャンル(を単元で絞る)。
    #   旧既定= hvrf,dhcp,dmvpn,ipsla,rtctl,v6addr,v6build,mpls,vpnbuild,mplsbuild,bgp,urpf,aaa
    ap.add_argument("--lab-genres", default="",
                    help=f"ラボの固定ジャンル({','.join(LAB_GENRES)})。明示すると単元ローテーションを使わない")
    ap.add_argument("--lab-mode", default="default",
                    help="単元ローテーションのモード(topologies/lab_modes.yml・BL-223)")
    ap.add_argument("--discovery", type=int, default=None,
                    help="発掘枠の本数(BL-233・既定は lab_modes.yml の discovery.slots。0 で使わない)")
    ap.add_argument("--lab-date", default=None,
                    help="単元ローテーションのノルマ日を仮定(YYYY-MM-DD・曜日/遅れ度の確認用)")
    ap.add_argument("--assume-used", type=int, default=None,
                    help="dry-run 専用: CML 稼働台数をこの値と仮定して選定を確認する")
    ap.add_argument("--build-rate", type=float, default=0.4,
                    help="構築ジャンルを 1 本混ぜる確率(1 パック最大 1 本・0 で構築なし・既定 0.4)")
    ap.add_argument("--lab-extra", type=int, default=None,
                    help="余裕があれば通常TSプールから追加する数(既定1・単元ローテーションは0)")
    ap.add_argument("--reserve", type=int, default=3,
                    help="追加枠が使わずに残すノード数(他セッション用の余白)")
    ap.add_argument("--budget", type=int, default=None,
                    help=f"同時起動ノード上限(既定= min(CML 上限 {CML_NODE_LIMIT}, mgmt_pool の個数)。"
                         f"{BIG_RULE_BUDGET} 以下なら大型スロット制限も掛かる)")
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
    ap.add_argument("--report-only", action="store_true",
                    help="grade: 解説ページ(report.html)を組み直すだけ。"
                         "履歴・ノルマ台帳には記録しない(採点済みパックの再描画用)")
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
    ap.add_argument("--profile", default="",
                    help="★BL-213: 出題範囲のプロファイル(カンマ区切り)。profile 名= ccna/encor/enarsi/ccie/vendor、"
                         "または単元 ID(U-A3 等・CURRICULUM.md)。例: --profile enarsi / --profile U-A3,U-H2。"
                         "紙面は該当単元の shape/kind だけ(--only-kinds)、ラボは該当単元の genre/候補だけになる")
    ap.add_argument("--today", action="store_true",
                    help="status/grade/close/render: 今日のパックを全部まとめて処理する")
    ap.add_argument("--dry-run", action="store_true",
                    help="CML にも questions/ にも触らないプレビュー")
    ap.add_argument("--lab-args", action="append", default=[],
                    help="ラボ生成器の追加引数(PREFIX=引数…・複数可・BL-210/211 のスーパーハード指定用)。"
                         "例: --lab-args 'GEN-DHCPTS=--hard acl_wall' --lab-args 'GEN-DMVPNW=--hard all'")
    a = ap.parse_args()
    if a.budget is None:
        a.budget = default_budget(os.path.abspath(a.repo))
    # ★BL-223: --lab-genres も --profile も無ければ単元ローテーション
    a.rotation = a.cmd == "new" and not a.lab_genres and not a.profile
    if not a.rotation and not a.lab_genres:
        # ★--profile 時は全ジャンルを単元で絞る(旧既定 13 種と交差すると STP 等が落ちていた)
        a.lab_genres = ",".join(LAB_GENRES)
    if a.lab_extra is None:
        a.lab_extra = 0 if a.rotation else 1
    if a.lab is None and not a.rotation:
        a.lab = 2
    # ★BL-224: 紙面も単元ローテーション(資格で絞らず units.yml の全単元を均等に)。
    #   --profile / --require-shape 明示 / --shape・--speed-shape 変更時は従来の抽選。
    a.paper_rotation = (a.cmd == "new" and not a.profile and a.require_shape == "auto"
                        and a.shape == "mixed" and a.speed_shape == "speed")
    if a.paper_rotation:
        a.no_pool = True        # 別置きの ENARSI 模擬プールは資格モード用(デフォルトには混ぜない)
    global PROFILE, PAPER_GENRES_ACTIVE
    PROFILE = resolve_profile(a.profile, os.path.abspath(a.repo))
    if PROFILE and a.cmd == "new":
        shapes = _profile_shapes(PROFILE)
        # 必須ジャンル表は該当 shape を持つものだけに絞る(auto 配分がここから引く)
        PAPER_GENRES_ACTIVE = {g: sh for g, sh in PAPER_GENRES.items() if set(sh) & shapes}
        # 枠ごとに「引ける kind が 1 つも無い」なら 0 問にする(生成器の空振りリトライを避ける)
        import gen_paper_mcq as _gm
        # 瞬発力枠に出せる family だけ(SPEED_KINDS=[] の cloze 等は除く)
        speed_shapes = {f for f, m in _gm.KB_FAMILIES.items()
                        if getattr(m, "SPEED_KINDS", None) is None or m.SPEED_KINDS} | {"mpls"}
        if not (shapes - {"cloze"}):
            a.paper = "0"
        if "cloze" not in shapes:
            a.cloze = 0
        if not (shapes & speed_shapes):
            a.speed = 0
        for fl in PROFILE["flags"]:
            setattr(a, fl, True)
        if "enarsi" not in a.profile.lower():
            a.no_pool = True                       # 別置き紙面プール(ENARSI 模擬)は ENARSI 以外の範囲に混ぜない
        genres = [g for g in (a.lab_genres or "").split(",") if g.strip() and g.strip() in PROFILE["lab_genres"]]
        n_fixed = a.lab if genres else 0
        if not genres and PROFILE["lab_ids"]:
            a.lab_extra = a.lab_extra + a.lab       # 固定ジャンルが無い単元は TS プール側で本数を保つ
        a.lab_genres = ",".join(genres)
        a.lab = n_fixed
        if not PROFILE["lab_ids"] and not genres:
            a.lab, a.lab_extra = 0, 0
        print(f"[profile] {PROFILE['label']}: 単元 {len(PROFILE['units'])} / 紙面 shape {sorted(shapes) or '(なし)'} / "
              f"思考 {a.paper} 瞬発 {a.speed} 穴埋め {a.cloze} / ラボ genre {genres or '(なし)'} + プール候補 {len(PROFILE['lab_ids'])}"
              f" (固定 {a.lab}・追加 {a.lab_extra})", flush=True)
    for spec in a.lab_args:
        import shlex
        if "=" not in spec:
            sys.exit(f"--lab-args は PREFIX=引数 の形: {spec}")
        pfx, rest = spec.split("=", 1)
        GEN_DEFAULT_ARGS.setdefault(pfx.strip(), [])
        GEN_DEFAULT_ARGS[pfx.strip()] = list(GEN_DEFAULT_ARGS[pfx.strip()]) + shlex.split(rest)
    fn = {"new": cmd_new, "status": cmd_status, "grade": cmd_grade,
          "close": cmd_close, "render": cmd_render,
          "replace": cmd_replace, "redeploy": cmd_redeploy}[a.cmd]
    if a.today and a.cmd in ("status", "grade", "close", "render"):
        pids = todays_packs(os.path.abspath(a.repo))
        if not pids:
            sys.exit("今日のパックがありません")
        for pid in pids:
            print(f"\n########## {pid} ##########")
            a.pack_id = pid
            fn(a)
        return
    fn(a)


if __name__ == "__main__":
    main()
