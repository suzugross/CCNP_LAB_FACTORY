#!/usr/bin/env python3
"""コマンドの素振り台(BL-278)の組み立て・配信・試験。

機器を起動せずに、Junos のコマンドを `?`・Tab 補完・モードの出入り・commit の型で打つ練習をする画面
(games/cli-drill/)のための道具。CLI の動きは games/cli-drill/junos.js(ブラウザで動く)、この道具はデータを揃える。

  python3 topologies/cli_drill.py harvest     # PoC の記録(poc/junos/*.log)から ? の一覧を採る → private/cli-drill/junos/help.json
  python3 topologies/cli_drill.py build       # 骨組み・? の一覧・練習・盤面の初めの設定を束ねる → private/cli-drill/site/
  python3 topologies/cli_drill.py serve [--port 8894]   # 束ねたものを配信(既定 0.0.0.0:8894。コンテナの中だけ。LAN からは
                                                         #   ポータルの /_read/_cli-drill/ で開く= build が reading/ へも写す)
  python3 topologies/cli_drill.py selftest    # 見えないブラウザで ?selftest=1 を開き、練習の答えの例と実機の記録の再現を確かめる
  python3 topologies/cli_drill.py embedtest   # 読み物の区切り(:::drill)のあるページを日英で開き、枠の中でどのお題も解けるか(tests/embed.html)
  python3 topologies/cli_drill.py session --host <IP> --script <台本> --out <記録>   # 実機と台本どおりに対話して記録する(採取)
  python3 topologies/cli_drill.py xr-board --log <board の記録> --out <盤面の JSON>  # XR の盤面(稼働中の設定＋コミットの履歴)

扱う OS: Junos(junos.js)・IOS XR(iosxr.js)。単元のファイル(drills/*.yml)の os: で選ぶ。素振り台の約束(CLAUDE.md)= 実機の動きを
必ず確かめて外れない形に。XR は実機の記録を素振り台で打ち直して手ごとに突き合わせる試験を持つ(tests/iosxr.yml・design §8)。

データの置き場(BL-278 の取り決め= 採ったヘルプの文言は公開側に置かず、採る道具だけ公開):
  公開   games/cli-drill/syntax/junos.txt(構文の骨組み)・drills/*.yml(練習)・tests/*.yml(実機の記録の再現の試験)
  非公開 private/cli-drill/junos/help.json(実機の ? の一覧)・doc.json(公式文書の文言)・site/(束ねたもの)
"""
from __future__ import annotations

import argparse
import copy
import functools
import glob
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.parse

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "games", "cli-drill")
PRIV = os.path.join(ROOT, "private", "cli-drill")
SITE = os.path.join(PRIV, "site")
PORTAL_DIR = os.path.join(ROOT, "reading", "_cli-drill")     # → http://<ポータル>:8899/_read/_cli-drill/


# ---------------------------------------------------------------- 骨組み(DSL → JSON)
def parse_syntax(path: str) -> dict:
    root = {"t": "R", "ch": []}
    stack = [(-1, root)]
    named: dict[str, dict] = {}
    for no, line in enumerate(open(path, encoding="utf-8"), 1):
        body = line.split("#", 1)[0].rstrip()
        if not body.strip():
            continue
        ind = (len(body) - len(body.lstrip(" "))) // 2
        toks = body.split()
        if "!確認" in toks:
            toks = toks[: toks.index("!確認")]
            chk = True
        else:
            chk = False
        flags = [t for t in toks if t[0] in "@&*"]
        toks = [t for t in toks if t[0] not in "@&*"]
        kind = toks[0]
        nodes: list[dict] = []
        if kind == "C":
            nodes = [{"t": "C", "kw": toks[1], "ch": [], "one": "@1" in flags}]
        elif kind == "N":
            ph = toks[3] if len(toks) > 3 else "<value>"
            nodes = [{"t": "N", "kw": toks[1], "vt": toks[2], "ph": ph, "ch": [],
                      "one": "@1" in flags, "e": "@e" in flags}]
        elif kind in ("L", "M"):
            nodes = [{"t": kind, "kw": toks[1], "vt": toks[2]}]
        elif kind == "F":
            nodes = [{"t": "F", "kw": toks[1]}]
        elif kind == "X":
            grp = toks[1]
            nodes = [{"t": "F", "kw": w, "xg": grp} for w in grp.split("|")]
        elif kind == "T":
            nodes = [{"t": "T", "kw": toks[1], "vts": toks[2:]}]
        else:
            raise SystemExit(f"{path}:{no}: 種類 {kind} は知らない")
        for n in nodes:
            if chk:
                n["chk"] = True
        while stack[-1][0] >= ind:
            stack.pop()
        parent = stack[-1][1]
        parent["ch"].extend(nodes)
        n = nodes[0]
        for f in flags:
            if f.startswith("&"):
                named[f[1:]] = n
            if f.startswith("*"):
                n["ch"] = copy.deepcopy(named[f[1:]]["ch"])
        if kind in ("C", "N"):
            stack.append((ind, n))
    return root


def parse_syntax_xr(path: str) -> dict:
    """syntax/iosxr.txt(書式はファイルの頭の注記)→ JSON。下位モードの入れ子・語と値の並び・表示の並びの規則。"""
    root = {"t": "R", "ch": [], "mode": "config", "uid": 0}
    stack = [(-1, root)]
    uid = 1
    for no, line in enumerate(open(path, encoding="utf-8"), 1):
        body = line.split("#", 1)[0].rstrip()
        if not body.strip():
            continue
        ind = (len(body) - len(body.lstrip(" "))) // 2
        toks = re.findall(r"\[[^\]]*\]|\S+", body)      # [語 {型}] は 1 つの字句(選べる語)
        kind = toks[0]
        if kind not in ("M", "L", "K", "F", "O"):
            raise SystemExit(f"{path}:{no}: 種類 {kind} は知らない")
        node: dict = {"t": kind, "toks": [], "uid": uid}
        uid += 1

        def valtok(t):
            spec, tok = t[1:-1], {}
            if spec.endswith("!"):
                tok["tr"], spec = True, spec[:-1]
            if "=" in spec:
                spec, tok["def"] = spec.split("=", 1)
            mm = re.match(r"(\w+)(\?)?(?::(.*))?$", spec)
            if not mm:
                raise SystemExit(f"{path}:{no}: 値の型 {t} が読めない")
            tok["v"] = mm.group(1)
            if mm.group(2):
                tok["opt"] = True
            if mm.group(3):
                tok["arg"] = mm.group(3)
            return tok
        for t in toks[1:]:
            if t.startswith("%"):
                node["mode"] = t[1:]
            elif t.startswith("sort:"):
                node["sort"] = t[5:]
            elif t == "@nest":
                node["nest"] = True
            elif t in ("@any", "@gone", "@seq", "@delkey", "@deldef", "@nestfull", "@dkeep"):
                node[t[1:]] = True
            elif t.startswith("@stub:"):
                node["stub"] = t[6:]
            elif t == "!確認":
                node["chk"] = True
            elif t == "|":
                node["idn"] = sum(1 for x in node["toks"] if "v" in x)
            elif t.startswith("["):              # 選べる語: [語]・[語 {型}]。語の後ろの $ = これで文が終わる・* = 区別に使う
                inner = t[1:-1].split()
                kw, opt = inner[0], {}
                while kw and kw[-1] in "$*":
                    opt["term" if kw[-1] == "$" else "id"] = True
                    kw = kw[:-1]
                opt["o"] = kw
                if len(inner) > 1:
                    opt["val"] = valtok(inner[1])
                node.setdefault("opts", []).append(opt)
            elif t.startswith("{"):
                node["toks"].append(valtok(t))
            else:
                node["toks"].append({"w": t})
        if kind == "M":
            node["ch"] = []
            if "mode" not in node:
                raise SystemExit(f"{path}:{no}: M にはモード名(%…)が要る")
        while stack[-1][0] >= ind:
            stack.pop()
        stack[-1][1]["ch"].append(node)
        if kind == "M":
            stack.append((ind, node))
    return root


XR_HELP_RE = re.compile(r"^  (\S(?:.*?\S)?)(?:\s{2,}(.*))?$")


def harvest_xr(args=None) -> None:
    """XR の採取の記録(private/cli-drill/iosxr/raw/*.log)→ ? の一覧(help.json)。
    文脈は「? を押した時のモード|打ってあった語」(値の正規化は素振り台の側で骨組みに沿って行う)。
    口の下位モード(config-if・config-ospf-ar-if)の一覧は口の型で違う(記録 ifnames4.log)ので、Loopback 以外の口に
    入っていた時はモードに型を付ける(config-if@GigabitEthernet)。入った口は、その下位モードへ入った手から読む。
    ★版・機種ごとの組(BL-283): raw/ の直下= 既定の組(XRT-01 の XRv 9000 24.3.1)。raw/<組>/ の下= 別の組
    (例 raw/xrd-26.1.1/ = XRT-16 の XRd 26.1.1)。組どうしは混ぜない(版で一覧が違う)。盤面の JSON の helpset が組を選ぶ。"""
    raw = os.path.join(PRIV, "iosxr", "raw")
    sets = {"": sorted(glob.glob(os.path.join(raw, "*.log")))}
    for d in sorted(glob.glob(os.path.join(raw, "*", ""))):
        sets[os.path.basename(os.path.dirname(d))] = sorted(glob.glob(os.path.join(d, "*.log")))
    res = {name: _harvest_xr_files(files) for name, files in sets.items()}
    out = os.path.join(PRIV, "iosxr", "help.json")
    d0 = res.pop("")
    json.dump({"help": d0[0], "src": d0[1], "sets": {k: {"help": h, "src": s_} for k, (h, s_) in res.items()}},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    per = "".join(f"・{k} {len(h)} 文脈" for k, (h, _) in res.items())
    print(f"→ {os.path.relpath(out, ROOT)}(既定 {len(d0[0])} 文脈{per})")


def _harvest_xr_files(files: list[str]) -> tuple[dict, dict]:
    help_, src = {}, {}
    iftypes = ("Loopback", "MgmtEth", "GigabitEthernet", "Null")

    def iftype(word):
        return next((t for t in iftypes if t.lower().startswith(word.lower()) and (len(word) >= 2 or t == "Null")), None)
    for f in files:
        in_if = {}                                # 口の下位モード → 入った口の型
        steps = _steps(f)
        for idx, (cmd, body, prompt) in enumerate(steps):
            mm = re.search(r"(?:\(([^)]*)\))?#", prompt)
            mode = (mm.group(1) or "exec") if mm else "exec"
            if not cmd.endswith("?"):
                m3 = re.search(r"\binterface\s+([A-Za-z-]+)\s*[\d/]", cmd, re.I)
                nx = re.search(r"\(([^)]*)\)#", steps[idx + 1][2]) if idx + 1 < len(steps) else None   # 手の後のモード
                if m3 and nx and nx.group(1).endswith("-if"):
                    in_if[nx.group(1)] = iftype(m3.group(1))
                continue
            if cmd.endswith(" ??"):
                continue
            if mode.endswith("-if") and in_if.get(mode) not in (None, "Loopback"):
                mode = f"{mode}@{in_if[mode]}"
            text = cmd[:-1].rstrip()
            if not cmd.endswith(" ?") and cmd != "?":
                continue                          # 語の途中の ?(sh? など)は一覧から作れる
            lines = body.split("\n") if body else []
            if not lines or lines[0].startswith("%") or lines[0].strip().startswith("^"):
                continue                          # 誤り(試験の記録の側で使う)
            items = []
            for raw in lines:
                if not raw.strip():
                    continue
                m2 = XR_HELP_RE.match(raw)
                if raw.startswith("   ") and items and (not m2 or raw.startswith(" " * 4)):
                    items[-1]["raw"].append(raw)      # 説明の続きの行
                    continue
                if not m2:
                    continue
                items.append({"n": m2.group(1), "h": (m2.group(2) or ""), "raw": [raw]})
            key = f"{mode}|{text}"
            if items and key not in help_:
                help_[key], src[key] = items, os.path.relpath(f, ROOT)
    return help_, src


# ---------------------------------------------------------------- 階層の設定(カーリー)→ set の行
def curly_to_set(text: str) -> list[str]:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|[{};\[\]]|[^\s{};\[\]"]+', text)
    out: list[str] = []
    path: list[list[str]] = []
    cur: list[str] = []
    for t in toks:
        if t == "{":
            path.append(cur)
            cur = []
        elif t == "}":
            path.pop()
            cur = []
        elif t == ";":
            words = [w for p in path for w in p] + cur
            if words:
                out.append("set " + " ".join(words))
            cur = []
        elif t.startswith("#"):
            continue
        else:
            cur.append(t)
    return out


# ---------------------------------------------------------------- 実機の記録から ? の一覧を採る
NAMED_KW = {"policy-statement", "group", "term", "neighbor", "prefix-list", "community", "area",
            "interface", "route", "unit", "filter", "family"}
COMP_RE = re.compile(r"^([>+ ]) (\S+)(\s+(.*))?$")


def ctx_key(cmd: str) -> str:
    toks = cmd.split()
    assert toks[0] == "set"
    toks = toks[1:]
    out = []
    i = 0
    while i < len(toks):
        t = toks[i]
        out.append(t)
        if t in NAMED_KW or (t == "interfaces" and not out[:-1]):
            if i + 1 < len(toks):
                out.append("*")
                i += 1
        i += 1
    return " ".join(out)


def harvest(args) -> None:
    logs = sorted(glob.glob(os.path.join(ROOT, "poc", "junos", "*.log")))
    help_: dict[str, list] = {}
    src: dict[str, str] = {}
    for f in logs:
        lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        for i, ln in enumerate(lines):
            if ln.strip() != "Possible completions:" or i == 0:
                continue
            m = re.match(r"^(set\s.*?)\s*\?\s*$", lines[i - 1])
            if not m:
                continue
            ctx = ctx_key(m.group(1))
            items = []
            for raw in lines[i + 1:]:
                mm = COMP_RE.match(raw)
                if not mm or raw.startswith("[edit"):
                    break
                items.append({"m": mm.group(1), "n": mm.group(2), "h": (mm.group(4) or "").strip(), "raw": raw.rstrip()})
            if items and ctx not in help_:
                help_[ctx] = items
                src[ctx] = os.path.relpath(f, ROOT)
    os.makedirs(os.path.join(PRIV, "junos"), exist_ok=True)
    out = os.path.join(PRIV, "junos", "help.json")
    json.dump({"help": help_, "src": src}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k in sorted(help_):
        print(f"  {k:45s} {len(help_[k]):3d} 語  ← {src[k]}")
    print(f"→ {os.path.relpath(out, ROOT)}({len(help_)} 階層)")


# ---------------------------------------------------------------- 盤面の図(clab のトポロジファイル＋初めの設定 → 図のモデル)
#   配線は目で写さず一次情報から機械的に起こす(ワークスペースの結線図と同じ考え)。配線と座標はトポロジファイル
#   (labels の graph-posX/Y)、アドレス・AS・OSPF・BGP・静的経路は各ノードの startup-config から拾う。
def _junos_facts(lines: list[str]) -> dict:
    f = {"ifs": {}, "ospf": {}, "bgp": [], "static": [], "as": None, "rid": None}
    grp: dict[str, dict] = {}
    for ln in lines:
        w = ln.split()[1:]
        if w[:1] == ["interfaces"] and len(w) >= 3:
            ent = f["ifs"].setdefault(w[1], {"addr": [], "desc": ""})
            if w[2] == "description":
                ent["desc"] = " ".join(w[3:]).strip('"')
            elif w[2:4] == ["unit", "0"] and w[4:7] == ["family", "inet", "address"] and len(w) > 7:
                ent["addr"].append(w[7])
        elif w[:2] == ["routing-options", "autonomous-system"]:
            f["as"] = w[2]
        elif w[:2] == ["routing-options", "router-id"]:
            f["rid"] = w[2]
        elif w[:3] == ["routing-options", "static", "route"] and len(w) >= 5:
            f["static"].append({"p": w[3], "nh": " ".join(w[5:]) if w[4] == "next-hop" else " ".join(w[4:])})
        elif w[:3] == ["protocols", "ospf", "area"] and len(w) >= 6 and w[4] == "interface":
            ent = f["ospf"].setdefault(w[5], {"area": w[3], "passive": False})
            if w[6:7] == ["passive"]:
                ent["passive"] = True
        elif w[:3] == ["protocols", "bgp", "group"] and len(w) >= 6:
            g = grp.setdefault(w[3], {"group": w[3], "type": "", "peer_as": "", "nbr": []})
            if w[4] == "type":
                g["type"] = w[5]
            elif w[4] == "peer-as":
                g["peer_as"] = w[5]
            elif w[4] == "neighbor" and w[5] not in g["nbr"]:
                g["nbr"].append(w[5])
    f["bgp"] = [{"peer": n, "as": g["peer_as"], "type": g["type"], "group": g["group"]}
                for g in grp.values() for n in g["nbr"]]
    return f


def _frr_facts(text: str) -> dict:
    f = {"ifs": {}, "ospf": {}, "bgp": [], "static": [], "as": None, "rid": None, "net": [], "dflt": False}
    cur = None
    for raw in text.splitlines():
        ln = raw.strip()
        w = ln.split()
        if not w or w[0] == "!":
            continue
        if w[0] == "interface":
            cur = f["ifs"].setdefault(w[1], {"addr": [], "desc": ""})
        elif w[0] == "exit":
            cur = None
        elif cur is not None and w[:2] == ["ip", "address"]:
            cur["addr"].append(w[2])
        elif cur is not None and w[0] == "description":
            cur["desc"] = " ".join(w[1:])
        elif w[:2] == ["ip", "route"]:
            f["static"].append({"p": w[2], "nh": " ".join(w[3:])})
        elif w[:2] == ["router", "bgp"]:
            f["as"] = w[2]
        elif w[:2] == ["bgp", "router-id"] and len(w) > 2:
            f["rid"] = w[2]
        elif w[0] == "neighbor" and len(w) >= 4 and w[2] == "remote-as":
            f["bgp"].append({"peer": w[1], "as": w[3], "type": "", "group": ""})
        elif w[0] == "neighbor" and w[2:3] == ["default-originate"]:
            f["dflt"] = True
        elif w[0] == "network":
            f["net"].append(w[1])
    return f


def topo_model(clab_rel: str) -> dict:
    """トポロジファイル(リポからの相対パス)→ {lab, nodes, links}。ノードの名前はワークスペースと同じく大文字。"""
    import ipaddress
    sys.path.insert(0, os.path.join(ROOT, "topologies"))
    import clab_ops                    # noqa: E402  種類(junos/frr)と「ホスト役」の判定はワークスペースと共通
    import lab_console                 # noqa: E402  ethN → 機器の中の名前(et-0/0/N-1 など)も共通
    path = os.path.join(ROOT, clab_rel)
    spec = yaml.safe_load(open(path, encoding="utf-8"))
    nodes = (spec.get("topology") or {}).get("nodes") or {}
    m = re.search(r"problems/([^/]+)/", clab_rel)
    out_nodes, facts = [], {}
    for name, nd in nodes.items():
        nd = nd or {}
        fam = clab_ops.node_family(nd)
        cfgp = nd.get("startup-config")
        text = open(os.path.join(os.path.dirname(path), cfgp), encoding="utf-8").read() if cfgp else ""
        fx = _junos_facts(curly_to_set(text)) if fam == "junos" else _frr_facts(text) if fam == "frr" else \
            {"ifs": {}, "ospf": {}, "bgp": [], "static": [], "as": None, "rid": None}
        label = str(name).upper()
        facts[label] = fx
        lab = nd.get("labels") or {}
        img = str(nd.get("image", ""))
        mv = re.search(r"\d+(?:\.\d+)+\S*$", img.rsplit(":", 1)[-1]) if ":" in img else None
        tag = mv.group(0) if mv else ""
        os_ = ("vJunos-Evolved" if "vjunosevolved" in str(nd.get("kind", "")).lower() else "Junos") if fam == "junos" \
            else "FRR" if fam == "frr" else str(nd.get("kind", ""))
        lo = next((a for i, e in fx["ifs"].items() if i in ("lo0", "lo") for a in e["addr"]), None)
        out_nodes.append({"label": label, "fam": fam, "host": clab_ops.node_is_host(nd), "os": os_, "ver": tag,
                          "x": float(lab.get("graph-posX", 0)), "y": float(lab.get("graph-posY", 0)),
                          "lo": lo, "as": fx["as"], "rid": fx["rid"],
                          "ifs": [{"n": i, "a": e["addr"], "d": e["desc"]} for i, e in fx["ifs"].items()],
                          "ospf": [{"i": i, **v} for i, v in fx["ospf"].items()], "bgp": fx["bgp"],
                          "static": fx["static"], "net": fx.get("net", []), "dflt": fx.get("dflt", False)})
    links = []
    for lk in (spec.get("topology") or {}).get("links") or []:
        ends = []
        for ep in (lk or {}).get("endpoints") or []:
            node, ifname = (ep.get("node"), ep.get("interface")) if isinstance(ep, dict) else (str(ep).split(":", 1) + [""])[:2]
            ends.append((node, ifname))
        if len(ends) != 2 or any(n not in nodes for n, _ in ends) or ends[0][0] == ends[1][0]:
            continue
        ent = {"tags": []}
        for side, (n, i) in zip("ab", ends):
            label = str(n).upper()
            ifn = lab_console.clab_if((nodes[n] or {}).get("kind", ""), i)
            addr = (facts[label]["ifs"].get(ifn) or {}).get("addr") or []
            ent[side], ent[side + "_if"], ent[side + "_addr"] = label, ifn, addr[0] if addr else None
        nets = {str(ipaddress.ip_interface(ent[s + "_addr"]).network) for s in "ab" if ent[s + "_addr"]}
        if len(nets) > 1:
            raise SystemExit(f"{clab_rel}: {ent['a']} {ent['a_if']} と {ent['b']} {ent['b_if']} のアドレスの網が違う: {sorted(nets)}")
        ent["net"] = nets.pop() if nets else None
        # OSPF: 両端の口(unit 0)がどちらも同じ area に入っていれば
        areas = [(facts[ent[s]]["ospf"].get(ent[s + "_if"] + ".0") or {}).get("area") for s in "ab"]
        if areas[0] and areas[0] == areas[1]:
            ent["tags"].append(f"OSPF area {areas[0]}")
        # BGP: 両端の neighbor が互いのこの口のアドレスを指している時だけ(片方だけの設定では張れない)
        peers = {}
        for s, o in (("a", "b"), ("b", "a")):
            peer = ent[o + "_addr"].split("/")[0] if ent[o + "_addr"] else None
            peers[s] = next((b for b in facts[ent[s]]["bgp"] if peer and b["peer"] == peer), None)
        if peers["a"] and peers["b"]:
            b = peers["a"]
            ext = b["type"] == "external" or (facts[ent["a"]]["as"] and facts[ent["b"]]["as"] and facts[ent["a"]]["as"] != facts[ent["b"]]["as"])
            ent["tags"].append("eBGP" if ext else "iBGP")
        links.append(ent)
    return {"lab": m.group(1) if m else os.path.basename(clab_rel), "nodes": out_nodes, "links": links}


def _mask_len(m: str) -> int:
    return sum(bin(int(x)).count("1") for x in m.split("."))


def _ios_facts(text: str) -> dict:
    """IOS/IOS XE の設定(CML の day0)→ 口のアドレス・OSPF・BGP・静的経路。管理用の口(vrf MGMT)は除く。"""
    f = {"ifs": {}, "ospf": {}, "bgp": [], "static": [], "as": None, "rid": None, "net": [], "dflt": False}
    cur, sect, mgmt = None, None, set()
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("!"):
            continue
        ind = len(raw) - len(raw.lstrip())
        w = raw.split()
        if ind == 0:
            cur, sect = None, None
            if w[0] == "interface":
                cur = w[1]
                f["ifs"].setdefault(cur, {"addr": [], "desc": ""})
            elif w[:2] == ["router", "bgp"]:
                sect, f["as"] = "bgp", w[2]
            elif w[:2] == ["router", "ospf"]:
                sect = "ospf"
            elif w[:2] == ["ip", "route"] and len(w) >= 5 and "vrf" not in w:
                f["static"].append({"p": f"{w[2]}/{_mask_len(w[3])}", "nh": w[4]})
            continue
        if cur:
            e = f["ifs"][cur]
            if w[:2] == ["ip", "address"] and len(w) >= 4:
                e["addr"].append(f"{w[2]}/{_mask_len(w[3])}")
            elif w[:2] == ["ipv6", "address"]:
                e["addr"].append(w[2].lower())
            elif w[0] == "description":
                e["desc"] = " ".join(w[1:])
            elif w[:2] == ["vrf", "forwarding"] and w[2] == "MGMT":
                mgmt.add(cur)
            elif w[:2] == ["ip", "ospf"] and len(w) >= 5 and w[3] == "area":
                f["ospf"][cur] = {"area": w[4], "passive": False}
        elif sect == "bgp":
            if w[0] == "neighbor" and len(w) >= 4 and w[2] == "remote-as":
                f["bgp"].append({"peer": w[1], "as": w[3], "type": "", "group": ""})
            elif w[:2] == ["bgp", "router-id"]:
                f["rid"] = w[2]
            elif w[0] == "network" and len(w) >= 4 and w[2] == "mask":
                f["net"].append(f"{w[1]}/{_mask_len(w[3])}")
        elif sect == "ospf" and w[0] == "router-id":
            f["rid"] = f["rid"] or w[1]
    for i in mgmt:
        f["ifs"].pop(i, None)
    return f


def _xr_facts(text: str) -> dict:
    """IOS XR の running-config(盤面の記録)→ 口のアドレス・VRF・OSPF・BGP・静的経路。管理用の口(MgmtEth)は除く。"""
    f = {"ifs": {}, "ospf": {}, "bgp": [], "static": [], "as": None, "rid": None, "net": [], "dflt": False}
    path: list[str] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("!") or raw.strip() == "end":
            continue
        ind = len(raw) - len(raw.lstrip())
        path = path[:ind] + [raw.strip()]
        w = raw.split()
        top = path[0].split()
        if top[0] == "interface" and ind == 1 and not top[1].startswith("MgmtEth"):
            e = f["ifs"].setdefault(top[1], {"addr": [], "desc": "", "vrf": ""})
            if w[:2] == ["ipv4", "address"]:
                e["addr"].append(f"{w[2]}/{_mask_len(w[3])}")
            elif w[:2] == ["ipv6", "address"]:
                e["addr"].append(w[2])
            elif w[0] == "description":
                e["desc"] = " ".join(w[1:])
            elif w[0] == "vrf":
                e["vrf"] = w[1]
        elif top[0] == "interface" and ind == 0 and not top[1].startswith("MgmtEth"):
            f["ifs"].setdefault(top[1], {"addr": [], "desc": "", "vrf": ""})
        elif top[:2] == ["router", "ospf"]:
            if ind == 1 and w[0] == "router-id":
                f["rid"] = w[1]
            if ind == 2 and w[0] == "interface":
                area = path[1].split()[1]
                f["ospf"][w[1]] = {"area": area, "passive": False}
            if ind == 3 and w[0] == "passive" and w[1:2] != ["disable"]:
                f["ospf"][path[2].split()[1]]["passive"] = True
        elif top[:2] == ["router", "static"] and ind == 2:
            f["static"].append({"p": w[0], "nh": " ".join(w[1:])})
        elif top[:2] == ["router", "bgp"]:
            f["as"] = top[2]
            if ind == 1 and w[0] == "neighbor":
                f["bgp"].append({"peer": w[1], "as": "", "type": "", "group": ""})
            if ind == 2 and w[0] == "remote-as" and f["bgp"]:
                f["bgp"][-1]["as"] = w[1]
    return f


def topo_model_cml(lab_rel: str, boards: dict) -> dict:
    """CML のラボ定義(構築時に生成された lab.yaml の控え)→ {lab, nodes, links}。配線・座標・機種はラボ定義から、
    口のアドレス・OSPF・BGP は機器の設定から(盤面の記録がある機器はその running-config、ほかはラボ定義の day0)。
    管理網の部品(MGMT-SW・外への接続)と管理用の口は描かない(ワークスペースの結線図と同じ)。"""
    import ipaddress
    spec = yaml.safe_load(open(os.path.join(ROOT, lab_rel), encoding="utf-8"))
    m = re.search(r"/([A-Z][A-Z0-9-]+)\.lab\.yaml$", lab_rel)
    skip = {"unmanaged_switch", "external_connector"}
    nodes, facts, iflabel = [], {}, {}
    for n in spec.get("nodes") or []:
        for i in n.get("interfaces") or []:
            iflabel[i["id"]] = i["label"]
        if n.get("node_definition") in skip:
            continue
        nd, lab = n["node_definition"], n["label"]
        xr = nd in ("iosxrv9000", "xrd")
        bd = boards.get(lab)
        text = bd["running"] if isinstance(bd, dict) and bd.get("running") else (n.get("configuration") or "")
        fx = _xr_facts(text) if xr else _ios_facts(text)
        facts[lab] = fx
        img = n.get("image_definition") or ""
        mv = re.search(r"(\d+)-(\d+)-(\d+)", img)
        lo = next((a for i, e in fx["ifs"].items() if i in ("Loopback0",) for a in e["addr"]), None)
        nodes.append({"label": lab, "fam": "iosxr" if xr else "ios", "host": False,
                      "os": {"iosxrv9000": "IOS XRv 9000", "xrd": "XRd"}.get(nd, "IOL" if nd.startswith("iol") else nd),
                      "ver": ".".join(str(int(x)) for x in mv.groups()) if mv else "",
                      "x": float(n.get("x", 0)), "y": float(n.get("y", 0)), "lo": lo, "as": fx["as"], "rid": fx["rid"],
                      "ifs": [{"n": i, "a": e["addr"], "d": e["desc"], **({"vrf": e["vrf"]} if e.get("vrf") else {})}
                              for i, e in fx["ifs"].items()],
                      "ospf": [{"i": i, **v} for i, v in fx["ospf"].items()], "bgp": fx["bgp"],
                      "static": fx["static"], "net": fx["net"], "dflt": False})
    labels = {n["label"] for n in nodes}
    byid = {n["id"]: n["label"] for n in spec.get("nodes") or []}
    links = []
    for lk in spec.get("links") or []:
        a, b = byid.get(lk["n1"]), byid.get(lk["n2"])
        if a not in labels or b not in labels:
            continue
        ent = {"tags": []}
        for side, nm, iid in (("a", a, lk["i1"]), ("b", b, lk["i2"])):
            ifn = iflabel[iid]
            e = facts[nm]["ifs"].get(ifn) or {}
            v4 = [x for x in e.get("addr", []) if "." in x]
            ent[side], ent[side + "_if"], ent[side + "_addr"] = nm, ifn, v4[0] if v4 else None
            if e.get("vrf"):
                ent[side + "_vrf"] = e["vrf"]
        nets = {str(ipaddress.ip_interface(ent[s + "_addr"]).network) for s in "ab" if ent[s + "_addr"]}
        if len(nets) > 1:
            raise SystemExit(f"{lab_rel}: {ent['a']} {ent['a_if']} と {ent['b']} {ent['b_if']} のアドレスの網が違う: {sorted(nets)}")
        ent["net"] = nets.pop() if nets else None
        areas = [(facts[ent[s]]["ospf"].get(ent[s + "_if"]) or {}).get("area") for s in "ab"]
        if areas[0] and areas[1] and (areas[0] == areas[1] or {areas[0], areas[1]} <= {"0", "0.0.0.0"}):
            ent["tags"].append(f"OSPF area {areas[0]}")
        peers = {}
        for s, o in (("a", "b"), ("b", "a")):      # 両端の neighbor が互いを指している時だけ(片方だけの設定では張れない)
            peer = ent[o + "_addr"].split("/")[0] if ent[o + "_addr"] else None
            peers[s] = next((bp for bp in facts[ent[s]]["bgp"] if peer and bp["peer"] == peer), None)
        if peers["a"] and peers["b"]:
            ent["tags"].append("iBGP" if facts[ent["a"]]["as"] == facts[ent["b"]]["as"] else "eBGP")
        links.append(ent)
    return {"lab": m.group(1) if m else os.path.basename(lab_rel), "nodes": nodes, "links": links}


# ---------------------------------------------------------------- XR の盤面の記録(実機の記録 → 盤面の JSON)
def _steps(log: str) -> list[tuple[str, str, str]]:
    """session の記録 → [(打った手, 出力の本文, 直前のプロンプト)]。本文はエコー行と最後のプロンプト行を除く。"""
    parts = re.split(r"^### >>> (.*)$", open(log, encoding="utf-8").read(), flags=re.M)
    out, prompt = [], ""
    head = parts[0].rstrip("\n").split("\n")
    prompt = head[-1] if head else ""
    for i in range(1, len(parts), 2):
        cmd, body = parts[i], parts[i + 1]
        lines = [ln for ln in body.split("\n") if not ln.startswith("### ")]
        while lines and lines[0] == "":
            lines.pop(0)
        while lines and lines[-1] == "":
            lines.pop()
        last = lines[-1] if lines else ""
        if lines and (XR_PROMPT_RE.match(last) or ASK_RE.search(last)):
            lines = lines[:-1]                    # 最後の行= プロンプトか問い(yes/no …)
        echo = lines[0] if lines else ""
        out.append((cmd, "\n".join(lines[1:] if echo.rstrip() == cmd.replace("<TAB>", "").rstrip() or cmd.endswith("?") else lines), prompt))
        if last and (XR_PROMPT_RE.match(last) or ASK_RE.search(last)):
            prompt = last
    return out


def _cfg_body(text: str) -> str:
    """show の出力から、先頭の時刻の行を除いた本文。"""
    lines = text.split("\n")
    if lines and re.match(r"^\w{3} \w{3} +\d+ \d\d:\d\d:\d\d\.\d+ UTC$", lines[0]):
        lines = lines[1:]
    return "\n".join(lines)


def xr_board(args) -> None:
    """board.txt の記録 → 盤面の JSON(稼働中の設定・コミットの履歴と各回の中身・版)。非公開側に置く。"""
    steps = {c: (b, p) for c, b, p in _steps(args.log)}
    run = _cfg_body(steps["show running-config"][0])
    ver = re.search(r"^!! IOS XR Configuration (\S+)", run, re.M).group(1)
    host = re.search(r"^hostname (\S+)", run, re.M).group(1)
    det = _cfg_body(steps["show configuration commit list detail"][0])
    commits = []
    for blk in ([] if "The commit database is empty." in det else re.split(r"\n\s*\n", det.strip("\n"))):
        g = lambda k: (re.search(k + r"\s*(.*?)(?:\s{2,}\w+:|$)", blk, re.M) or [None, ""])[1]
        cid = re.search(r"CommitId: (\d+)", blk).group(1)
        lab = re.search(r"Label: (\S+)", blk).group(1)
        c = {"id": cid, "label": None if lab == "NONE" else lab,
             "user": re.search(r"UserId:\s+(\S+)", blk).group(1), "line": re.search(r"Line:\s+(\S+)", blk).group(1),
             "client": re.search(r"Client:\s+(\S+)", blk).group(1),
             "time": re.search(r"Time:\s+(.+)$", blk, re.M).group(1).rstrip(),
             "comment": re.search(r"Comment:(.*)$", blk, re.M).group(1)}
        key = c["label"] or cid
        for kind, cmd in (("changes", "commit changes"), ("rollback", "rollback changes")):
            got = steps.get(f"show configuration {cmd} {key}") or steps.get(f"show configuration {cmd} {cid}")
            c[kind] = _cfg_body(got[0]) if got else None
        commits.append(c)
    commits.reverse()                       # 古い順
    board = {"host": host, "version": ver, "running": run, "commits": commits,
             "source": os.path.relpath(args.log, ROOT)}
    sub = os.path.basename(os.path.dirname(os.path.abspath(args.log)))
    if sub != "raw":                        # raw/<組>/ の記録から作った盤面は、その組の ? の一覧を使う(harvest_xr)
        board["helpset"] = sub
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(board, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {args.out}(版 {ver}・コミット {len(commits)} 回・中身 {sum(1 for c in commits if c['changes'])}・"
          f"戻し {sum(1 for c in commits if c['rollback'])})")


# ---------------------------------------------------------------- 束ねる
def load_drills() -> list[dict]:
    units = []
    for f in sorted(glob.glob(os.path.join(GAME, "drills", "*.yml"))):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        devs = {}
        for name, cfg in (d.get("devices") or {}).items():
            path = os.path.join(ROOT, cfg)
            if not os.path.exists(path):
                raise SystemExit(f"{f}: 盤面の記録が無い: {cfg}(XR は cli_drill.py xr-board で実機の記録から作る)")
            if cfg.endswith(".json"):            # 実機の記録から作った盤面(XR: 稼働中の設定＋コミットの履歴)
                devs[name] = json.load(open(path, encoding="utf-8"))
            else:                                # Junos: 階層の設定 → set の行
                devs[name] = curly_to_set(open(path, encoding="utf-8").read())
        d["devices"] = devs
        if d.get("topology"):
            t = d["topology"]
            d["topo"] = topo_model_cml(t, devs) if t.endswith("lab.yaml") else topo_model(t)
            miss = sorted(set(devs) - {n["label"] for n in d["topo"]["nodes"]})
            if miss:
                raise SystemExit(f"{f}: 盤面の図に無い機器: {miss}")
        d["file"] = os.path.relpath(f, ROOT)
        units.append(d)
    return units


OSES = ("junos", "iosxr")          # 素振り台が扱う OS(syntax/<os>.txt と <os>.js があるもの)


def os_bundle(os_: str, args) -> dict | None:
    """OS ごとの束= 骨組み・実機の ? の一覧(非公開)・公式文書の文言(非公開)・実機の記録の再現の試験。"""
    syn = os.path.join(GAME, "syntax", f"{os_}.txt")
    if not os.path.exists(syn):
        return None
    hp = os.path.join(PRIV, os_, "help.json")
    if os_ == "junos" and not os.path.exists(hp):
        harvest(args)
    if os_ == "iosxr" and os.path.isdir(os.path.join(PRIV, "iosxr", "raw")):
        harvest_xr(args)                     # 記録が増えたら採り直す(数秒)
    hj = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
    help_ = hj.get("help") or {}
    help_sets = {k: v["help"] for k, v in (hj.get("sets") or {}).items()}   # 版・機種ごとの組(XR。harvest_xr)
    dp = os.path.join(PRIV, os_, "doc.json")
    doc = json.load(open(dp, encoding="utf-8")) if os.path.exists(dp) else {}
    tests = []
    for f in sorted(glob.glob(os.path.join(GAME, "tests", f"{os_}*.yml"))):
        tests.extend(yaml.safe_load(open(f, encoding="utf-8")) or [])
    extra = {}
    xp = os.path.join(PRIV, os_, "extra.json")    # 実機の記録から採った表示の型など(OS ごとの中身は採る道具の docstring)
    if os.path.exists(xp):
        extra = json.load(open(xp, encoding="utf-8"))
    schema = parse_syntax_xr(syn) if os_ == "iosxr" else parse_syntax(syn)
    if os_ == "iosxr":
        tests = [xr_replay_test(t) for t in tests]
    return {"schema": schema, "help": help_, "helpSets": help_sets, "doc": doc, "tests": tests, "extra": extra}


def xr_replay_test(t: dict) -> dict:
    """XR の試験= 実機の記録(session の log)を素振り台で同じ順に打ち直し、手ごとの出力とプロンプトを突き合わせる。
    t = {name, log: <private からの相対>, device, skip: [打った手の番号(1 から)…], note}。記録は非公開なので束にだけ入れる。"""
    path = os.path.join(ROOT, t["log"])
    if not os.path.exists(path):
        return {**t, "steps": None}
    steps = [{"cmd": c, "out": b, "prompt": p} for c, b, p in _steps(path)]
    return {**t, "steps": steps}


def build(args) -> None:
    oses = {o: b for o in OSES if (b := os_bundle(o, args))}
    units = load_drills()
    for u in units:
        u.setdefault("os", "junos")
        if u["os"] not in oses:
            raise SystemExit(f"{u['file']}: os {u['os']} の骨組み(syntax/{u['os']}.txt)が無い")
    bundle = {"os": oses, "units": units}
    os.makedirs(SITE, exist_ok=True)
    for name in ["index.html"] + [f"{o}.js" for o in oses]:
        shutil.copy(os.path.join(GAME, name), os.path.join(SITE, name))
    json.dump(bundle, open(os.path.join(SITE, "bundle.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # ポータル(8899)の /_read/ は reading/ をそのまま配るので、そこへも写す(コード変更・再起動なしで LAN から開ける)。
    # reading/ は .gitignore 済み。_ で始まるのでポータルの棚には載らず、Drive への同期(reading/_offline/)にも入らない。
    shutil.copytree(SITE, PORTAL_DIR, dirs_exist_ok=True)
    nd = sum(len(s["drills"]) for u in units for s in u["sections"])
    per = "・".join(f"{o}: ? の一覧 {len(b['help'])} 階層・試験 {len(b['tests'])}" for o, b in oses.items())
    print(f"→ {os.path.relpath(SITE, ROOT)}/(単元 {len(units)}・お題 {nd}・{per})")


# ---------------------------------------------------------------- 配信
class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *a):
        pass


def serve(args) -> None:
    if not os.path.exists(os.path.join(SITE, "bundle.json")):
        build(args)
    h = functools.partial(Handler, directory=SITE)
    srv = http.server.ThreadingHTTPServer((args.host, args.port), h)
    print(f"素振り台: http://{args.host}:{args.port}/ (止めるには Ctrl-C)", flush=True)
    srv.serve_forever()


# ---------------------------------------------------------------- 試験(見えないブラウザで ?selftest=1)
def chrome_bin() -> str:
    c = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))
    if not c:
        raise SystemExit("chrome-headless-shell が見つからない(~/.cache/ms-playwright)")
    return c[-1]


def selftest(args) -> None:
    build(args)
    h = functools.partial(Handler, directory=SITE)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory() as prof:
        cmd = [chrome_bin(), "--headless", "--no-sandbox", "--disable-gpu", f"--user-data-dir={prof}",
               "--virtual-time-budget=60000", "--dump-dom", f"http://127.0.0.1:{port}/?selftest=1"]
        dom = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    srv.shutdown()
    m = re.search(r'<pre id="selftest"[^>]*>(.*?)</pre>', dom, re.S)
    if not m:
        print(dom[-2000:])
        raise SystemExit("selftest の結果が出なかった")
    import html as _h
    txt = _h.unescape(m.group(1))
    print(txt)
    if "NG 0" not in txt.splitlines()[-1]:
        raise SystemExit(1)


def embedtest(args) -> None:
    """読み物(reading/<本>/*.html)のうち区切り(:::drill)を持つページを、ポータルと同じ配置(/_read/ → reading/)で
    日英それぞれ開き、tests/embed.html が区切りのボタンから素振り台を操作する。読み物と素振り台は先にビルドしておく
    (素振り台は build で reading/_cli-drill/ へ写る。読み物は scripts/course.sh <本> build)。"""
    build(args)
    reading = os.path.join(ROOT, "reading")
    pages = sorted(os.path.relpath(p, reading) for p in glob.glob(os.path.join(reading, "*", "*.html"))
                   if not os.path.basename(os.path.dirname(p)).startswith("_")
                   and '<div class="drillbreak"' in open(p, encoding="utf-8").read())
    if not pages:
        raise SystemExit("区切り(:::drill)のある読み物のページが無い(読み物をビルドしたか)")
    tests = os.path.join(GAME, "tests")

    class H(Handler):
        def translate_path(self, path):
            p = urllib.parse.unquote(path.split("?")[0])
            if p.startswith("/_read/"):
                return os.path.join(reading, p[len("/_read/"):])
            return os.path.join(tests, os.path.basename(p))
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import html as _h
    bad = 0
    for page in pages:
        for lang in ("en", "ja"):
            with tempfile.TemporaryDirectory() as prof:
                cmd = [chrome_bin(), "--headless", "--no-sandbox", "--disable-gpu", f"--user-data-dir={prof}",
                       "--window-size=1000,1250", "--virtual-time-budget=120000", "--dump-dom",
                       f"http://127.0.0.1:{port}/embed.html?p={urllib.parse.quote(page)}&lang={lang}"]
                dom = subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
            m = re.search(r'<pre id="selftest"[^>]*>(.*?)</pre>', dom, re.S)
            txt = _h.unescape(m.group(1)) if m else "NG 結果が出なかった\nNG 1"
            last = txt.splitlines()[-1]
            ngs = [ln for ln in txt.splitlines()[:-1] if ln.startswith("NG")]
            print(f"{page} [{lang}] {len(txt.splitlines()) - 1 - len(ngs)} 項目 OK・{last}")
            for ln in ngs:
                print("   ", ln)
            bad += last != "NG 0"
    srv.shutdown()
    if bad:
        raise SystemExit(1)


# ---------------------------------------------------------------- 実機と対話して記録する(採取の道具)
#   台本(1 行 1 手)を SSH の対話シェルで順に打ち、打った手と出力をそのまま記録する。素振り台の約束(実機の動きを
#   確かめて外れない形に)のための一次情報を採る。記録は非公開側(private/cli-drill/<os>/raw/)に置く。
#   台本の書き方:
#     末尾が ? の行   … Enter を押さずに送る(ヘルプ)。出力を記録した後、行を消す(Ctrl-U)
#     末尾が <TAB> の行 … その前までを送って Tab を押す。記録の後、行を消す
#     ^C / ^Z         … その制御文字だけを送る
#     #SLEEP <秒>     … 待って、その間に機器が自分から出した表示を記録する
#     # で始まる行     … 注記(送らない・記録に残す)
#     それ以外         … そのまま送って Enter
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[=>]")
XR_PROMPT_RE = re.compile(r"^(?:RP/\d+/\S+?:)?[A-Za-z0-9_.-]+(?:\([^)]*\))?[#>]")
ASK_RE = re.compile(r"(\]:|\[(?:yes|no|confirm)[^\]]*\]\s*|\?\s*\[[^\]]*\]:?|[Pp]assword:)\s*$")


def _read_until(ch, quiet: float, limit: float) -> str:
    import time
    buf, last = "", time.time()
    start = last
    while True:
        if ch.recv_ready():
            buf += ch.recv(65535).decode("utf-8", errors="replace")
            last = time.time()
            continue
        now = time.time()
        tail = ANSI_RE.sub("", buf).replace("\r", "").rstrip("\n").split("\n")[-1] if buf else ""
        done = bool(XR_PROMPT_RE.match(tail) or ASK_RE.search(tail))
        if (done and now - last >= quiet) or now - start >= limit or (now - last >= max(quiet * 8, 6) and buf):
            return buf
        time.sleep(0.05)


def session(args) -> None:
    import paramiko
    user, pw = os.environ.get("NODE_USER"), os.environ.get("NODE_PASS")
    if not user or not pw:
        raise SystemExit("NODE_USER / NODE_PASS が要る(source poc/xr/env.sh)")
    steps = [ln.rstrip("\n") for ln in open(args.script, encoding="utf-8")]
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(args.host, username=user, password=pw, look_for_keys=False, allow_agent=False, timeout=20)
    ch = cli.invoke_shell(width=args.width, height=200)
    out = [f"# session {os.path.basename(args.script)} → {args.host}"]
    first = _read_until(ch, 1.0, 30)
    out.append(ANSI_RE.sub("", first).replace("\r", ""))
    for st in steps:
        if not st.strip():
            continue
        if st.startswith("#SLEEP"):              # 待つ(確認つきコミットの期限切れなど、機器が自分から出す表示を採る)
            import time
            time.sleep(float(st.split()[1]))
            got = ch.recv(65535).decode("utf-8", errors="replace") if ch.recv_ready() else ""
            out.append(f"### >>> {st}")
            out.append(ANSI_RE.sub("", got).replace("\r", ""))
            continue
        if st.startswith("#"):
            out.append(f"### {st}")
            continue
        if st in ("^C", "^Z"):
            ch.send({"^C": "\x03", "^Z": "\x1a"}[st])
            mark = st
        elif st.endswith("?"):
            ch.send(st)
            mark = st
        elif st.endswith("<TAB>"):
            ch.send(st[:-5] + "\t")
            mark = st
        else:
            ch.send(st + "\n")
            mark = st
        got = _read_until(ch, args.quiet, args.limit)
        out.append(f"### >>> {mark}")
        out.append(ANSI_RE.sub("", got).replace("\r", ""))
        if st.endswith("?") or st.endswith("<TAB>"):
            ch.send("\x15")                      # 行を消す(Ctrl-U)
            _read_until(ch, 0.3, 5)
    ch.close()
    cli.close()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"→ {args.out}({len(steps)} 行の台本)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("harvest")
    sub.add_parser("build")
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=8894)
    sub.add_parser("selftest")
    sub.add_parser("embedtest", help="読み物の区切り(:::drill)から素振り台を開く試験")
    se = sub.add_parser("session", help="実機と台本どおりに対話して記録する(採取)")
    se.add_argument("--host", required=True)
    se.add_argument("--script", required=True)
    se.add_argument("--out", required=True)
    se.add_argument("--width", type=int, default=250)
    se.add_argument("--quiet", type=float, default=0.6, help="プロンプトが出てから静かになるまで待つ秒")
    se.add_argument("--limit", type=float, default=90, help="1 手の上限秒")
    xb = sub.add_parser("xr-board", help="XR の盤面の記録(board.txt の session)→ 盤面の JSON")
    xb.add_argument("--log", required=True)
    xb.add_argument("--out", required=True)
    a = ap.parse_args()
    {"harvest": harvest, "build": build, "serve": serve, "selftest": selftest, "embedtest": embedtest,
     "session": session, "xr-board": xr_board}[a.cmd](a)


if __name__ == "__main__":
    main()
