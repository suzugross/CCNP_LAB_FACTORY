#!/usr/bin/env python3
"""CML サーバの定義類をまるごと控え、あとで照合する(アップグレード前後の比較用)。

  save  [--out DIR]          : 定義類を DIR(既定 private/cml-backup/<版>-<日時>/)に保存
  diff  OLD NEW              : 2 つの控えを照合(ノード定義・イメージ定義・ラボ一覧の差分)
  check [SNAP]               : 今の CML(または控え)で、device_profiles が参照するイメージ ID が揃っているか
  smoke [--defs a,b,...]     : 使い捨てのラボを作り、指定ノード定義を 1 台ずつ起動して BOOTED を待ち、片付ける

保存するもの: system_information / licensing / system_stats / ノード定義(1 件 1 ファイル・JSON)/
イメージ定義(同)/ ラボ一覧とラボごとの topology YAML。ラボの YAML には初期設定(パスワード含む)が
入るので、保存先は private/(git 除外)を既定にしている。

認証は環境変数 CML_HOST / CML_USER / CML_PASSWORD、無ければ group_vars/all/local.yml の cml_*。
"""
import argparse
import datetime as dt
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# smoke の既定= このリポの device_profiles が使う軽いもの(XRv9000 は重いので明示指定時だけ)
SMOKE_DEFAULT = ["iol-xe", "ioll2-xe", "iosv", "iosvl2", "ubuntu"]


class Api:
    def __init__(self):
        loc = {}
        p = ROOT / "group_vars/all/local.yml"
        if p.exists():
            loc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        host = os.environ.get("CML_HOST") or loc.get("cml_host")
        self.base = f"https://{host}/api/v0"
        user = os.environ.get("CML_USER") or loc.get("cml_username")
        pw = os.environ.get("CML_PASSWORD") or loc.get("cml_password")
        self.token = self.req("POST", "/authenticate", {"username": user, "password": pw}, auth=False)

    def req(self, method, path, body=None, auth=True, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        if auth:
            r.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(r, context=CTX, timeout=120) as res:
            txt = res.read().decode("utf-8", errors="replace")
        if raw:
            return txt
        return json.loads(txt) if txt.strip() else None


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------- save
def cmd_save(a):
    api = Api()
    info = api.req("GET", "/system_information")
    ver = info["version"].split("+")[0]
    out = Path(a.out) if a.out else ROOT / "private/cml-backup" / f"{ver}-{dt.datetime.now():%Y%m%d-%H%M}"
    dump(out / "system_information.json", info)
    for p in ("licensing", "system_stats", "system_health"):
        try:
            dump(out / f"{p}.json", api.req("GET", f"/{p}"))
        except urllib.error.HTTPError as e:
            print(f"  [skip] {p}: {e}")
    nds = api.req("GET", "/node_definitions")
    for d in nds:
        dump(out / "node_definitions" / f"{d['id']}.json", d)
    ids = api.req("GET", "/image_definitions")
    for d in ids:
        dump(out / "image_definitions" / f"{d['id'].replace('/', '_')}.json", d)
    labs = []
    for lid in api.req("GET", "/labs?show_all=true"):
        l = api.req("GET", f"/labs/{lid}")
        labs.append({k: l.get(k) for k in ("id", "lab_title", "state", "node_count", "link_count", "owner_username")})
        try:
            dump(out / "labs" / f"{lid}.yaml", api.req("GET", f"/labs/{lid}/download", raw=True))
        except urllib.error.HTTPError as e:
            print(f"  [skip] lab {lid}: {e}")
    dump(out / "labs.json", labs)
    print(f"保存先: {out}")
    print(f"  CML {info['version']} / ノード定義 {len(nds)} / イメージ定義 {len(ids)} / ラボ {len(labs)}")


# ---------------------------------------------------------------- diff
def load_dir(d):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))}


def flat(o, pre=""):
    if isinstance(o, dict):
        r = {}
        for k, v in o.items():
            r.update(flat(v, f"{pre}.{k}" if pre else k))
        return r
    return {pre: o}


# 版が変われば必ず動く/照合の役に立たない鍵
NOISE = ("schema_version", "read_only", "id")


def diff_defs(kind, old, new):
    print(f"\n== {kind}: 旧 {len(old)} / 新 {len(new)}")
    for k in sorted(set(old) - set(new)):
        print(f"  ★消えた  {k}")
    for k in sorted(set(new) - set(old)):
        print(f"  ＋増えた  {k}")
    for k in sorted(set(old) & set(new)):
        fo, fn = flat(old[k]), flat(new[k])
        ch = [p for p in sorted(set(fo) | set(fn))
              if fo.get(p) != fn.get(p) and p.split(".")[-1] not in NOISE]
        if ch:
            print(f"  ～変わった {k}")
            for p in ch[:40]:
                print(f"      {p}: {json.dumps(fo.get(p), ensure_ascii=False)[:90]}"
                      f"  →  {json.dumps(fn.get(p), ensure_ascii=False)[:90]}")
            if len(ch) > 40:
                print(f"      … ほか {len(ch) - 40} 件")


def cmd_diff(a):
    o, n = Path(a.old), Path(a.new)
    vo = json.loads((o / "system_information.json").read_text())["version"]
    vn = json.loads((n / "system_information.json").read_text())["version"]
    print(f"旧 {vo}  →  新 {vn}")
    diff_defs("ノード定義", load_dir(o / "node_definitions"), load_dir(n / "node_definitions"))
    diff_defs("イメージ定義", load_dir(o / "image_definitions"), load_dir(n / "image_definitions"))
    lo = {l["id"]: l for l in json.loads((o / "labs.json").read_text())}
    ln = {l["id"]: l for l in json.loads((n / "labs.json").read_text())}
    print(f"\n== ラボ: 旧 {len(lo)} / 新 {len(ln)}")
    for k in sorted(set(lo) - set(ln)):
        print(f"  ★消えた  {lo[k]['lab_title']}")
    for k in sorted(set(lo) & set(ln)):
        if (lo[k]["node_count"], lo[k]["link_count"]) != (ln[k]["node_count"], ln[k]["link_count"]):
            print(f"  ～ノード/リンク数が変わった {lo[k]['lab_title']}")


# ---------------------------------------------------------------- check
def profile_refs():
    """group_vars の device_profiles が参照する (node_definition, image_definition) の組。"""
    gv = yaml.safe_load((ROOT / "group_vars/all/main.yml").read_text(encoding="utf-8"))
    refs = set()

    def walk(o):
        if isinstance(o, dict):
            if "node_definition" in o:
                refs.add((o["node_definition"], o.get("image_definition")))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(gv)
    return sorted(refs, key=str)


def cmd_check(a):
    if a.snap:
        nds = set(load_dir(Path(a.snap) / "node_definitions"))
        ims = {v["id"]: v.get("node_definition_id") for v in load_dir(Path(a.snap) / "image_definitions").values()}
    else:
        api = Api()
        nds = {d["id"] for d in api.req("GET", "/node_definitions")}
        ims = {d["id"]: d.get("node_definition_id") for d in api.req("GET", "/image_definitions")}
    bad = 0
    for nd, im in profile_refs():
        ok_nd = nd in nds
        ok_im = im is None or (im in ims and ims[im] == nd)
        mark = "OK " if ok_nd and ok_im else "★NG"
        bad += not (ok_nd and ok_im)
        why = "" if ok_nd and ok_im else (" (ノード定義なし)" if not ok_nd else
                                            f" (イメージ定義なし/紐づき先={ims.get(im)})")
        print(f"  {mark} {nd:<16} {im}{why}")
    print("全件 OK" if not bad else f"★不一致 {bad} 件")
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------- smoke
def cmd_smoke(a):
    api = Api()
    defs = a.defs.split(",") if a.defs else SMOKE_DEFAULT
    title = f"_SMOKE-{dt.datetime.now():%Y%m%d-%H%M}"
    lab = api.req("POST", "/labs", {"title": title})
    lid = lab["id"]
    print(f"ラボ {title} ({lid})")
    nodes = {}
    try:
        for i, d in enumerate(defs):
            n = api.req("POST", f"/labs/{lid}/nodes",
                        {"label": d.replace("-", "")[:20], "node_definition": d, "x": 120 * i, "y": 0})
            nodes[n["id"]] = d
        api.req("PUT", f"/labs/{lid}/start")
        t0 = time.time()
        while True:
            st = {nid: api.req("GET", f"/labs/{lid}/nodes/{nid}")["state"] for nid in nodes}
            line = " ".join(f"{nodes[k]}={v}" for k, v in st.items())
            print(f"  [{int(time.time() - t0):4d}s] {line}", flush=True)
            if all(v == "BOOTED" for v in st.values()) or time.time() - t0 > a.timeout:
                break
            time.sleep(20)
        bad = [nodes[k] for k, v in st.items() if v != "BOOTED"]
        print("全ノード BOOTED" if not bad else f"★BOOTED にならなかった: {', '.join(bad)}")
    finally:
        if not a.keep:
            for p in ("stop", "wipe"):
                try:
                    api.req("PUT", f"/labs/{lid}/{p}")
                except urllib.error.HTTPError:
                    pass
            api.req("DELETE", f"/labs/{lid}")
            print("ラボを削除しました")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("save"); p.add_argument("--out"); p.set_defaults(f=cmd_save)
    p = sp.add_parser("diff"); p.add_argument("old"); p.add_argument("new"); p.set_defaults(f=cmd_diff)
    p = sp.add_parser("check"); p.add_argument("snap", nargs="?"); p.set_defaults(f=cmd_check)
    p = sp.add_parser("smoke")
    p.add_argument("--defs", help="カンマ区切りのノード定義 ID(既定: " + ",".join(SMOKE_DEFAULT) + ")")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--keep", action="store_true", help="終わってもラボを消さない")
    p.set_defaults(f=cmd_smoke)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
