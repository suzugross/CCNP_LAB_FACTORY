#!/usr/bin/env python3
"""MGMT IP リース台帳 — 複数ラボ同時稼働のための中央アロケータ。

背景: 全ラボが MGMT 10.1.10.0/26 の共有プール(group_vars/all/main.yml の
mgmt_pool, 30個)を使う。従来は build のたびに常に先頭(.11)から割当てていた
ため同時稼働は1ラボのみだった。本スクリプトが「どのラボがどのIPを使用中か」を
台帳(topologies/_state/mgmt_leases.json)で管理し、空きIPを first-fit で
貸し出すことで複数ラボ(複数セッション)の同時稼働を可能にする。

サブコマンド:
  allocate --repo R --problem P --nodes RT01,RT02[,..] [--out mgmt_map.yml]
      空きIPをノード数ぶん確保しリース登録。--out に mgmt_map.yml を書く。
      同一 problem の再 build はノード集合が同じなら既存リースを再利用
      (稼働中ラボと割当がズレない)。プール不足時は使用中リースの内訳と
      対処を表示して rc=2 で停止(CML には一切触らない)。
  release --repo R --problem P
      リース解放(存在しなくてもエラーにしない)。
  status  --repo R
      台帳・空きIP・_generated の突合を表示(オフライン)。
  gc      --repo R [--apply]
      CML の実ラボ(description に埋め込んだリース情報)と台帳を突合:
      - CML に実在するのに台帳に無い → リースを再構築(採用)
      - CML に無く _generated/<problem> も無い → 解放(teardown漏れの回収)
      台帳ファイルが消えても CML から完全復元できる。--apply 無しは dry-run。
      認証は env CML_HOST / CML_USER / CML_PASS (CML_VERIFY 任意)。

排他: fcntl.flock による read-modify-write 保護(同一ホスト上の並行セッション対応)。
"""
import argparse
import base64
import datetime
import fcntl
import hashlib
import json
import os
import sys
import time

import yaml


# ---------------------------------------------------------------- 共通部品

def lab_title(problem):
    """CML ラボ名。gen_cml_lab.py / lab_up.yml と同一規則(md5 で不透明化)。"""
    return "CCNP-LAB-" + hashlib.md5(problem.encode()).hexdigest()[:8]


def lease_description(problem, mgmt_map):
    """CML ラボの description に埋め込むリース情報(JSON 1行)。
    problem ID は技術名を含み受験者に見えるため base64 で不透明化する。
    これにより台帳ファイルが失われても gc が CML から割当を完全復元できる。"""
    return json.dumps(
        {"ccnp_lease": {"p64": base64.b64encode(problem.encode()).decode(),
                        "nodes": mgmt_map}},
        separators=(",", ":"))


def parse_description(text):
    """description からリース情報を復元。無関係な文字列なら (None, None)。"""
    try:
        lease = json.loads(text or "")["ccnp_lease"]
        problem = base64.b64decode(lease["p64"]).decode()
        return problem, dict(lease["nodes"])
    except Exception:
        return None, None


def load_pool(repo):
    # mgmt_pool は環境依存のため group_vars/all/local.yml に置く（.gitignore 済）。
    # 後方互換で main.yml も見る（旧レイアウト救済）。
    for rel in ("group_vars/all/local.yml", "group_vars/all/main.yml"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        gv = yaml.safe_load(open(path, encoding="utf-8")) or {}
        pool = gv.get("mgmt_pool")
        if pool:
            return [str(ip) for ip in pool]
    sys.exit("[mgmt_alloc] mgmt_pool が見つかりません。group_vars/all/local.yml.example を"
             "コピーして group_vars/all/local.yml を作成してください")


def summarize(ips):
    """IP列を最終オクテットの連続レンジ表記に圧縮(表示用)。例: '.11-.14, .31'"""
    octs = sorted(int(str(ip).rsplit(".", 1)[1]) for ip in ips)
    ranges = []
    for o in octs:
        if ranges and o == ranges[-1][1] + 1:
            ranges[-1][1] = o
        else:
            ranges.append([o, o])
    return ", ".join(f".{s}" if s == e else f".{s}-.{e}" for s, e in ranges) or "(なし)"


class Ledger:
    """flock 排他つき台帳。with ブロック中はロック保持(read-modify-write 保護)。"""

    def __init__(self, repo):
        d = os.path.join(repo, "topologies", "_state")
        self.path = os.path.join(d, "mgmt_leases.json")
        self._lockpath = os.path.join(d, "mgmt_leases.lock")
        self._dir = d

    def __enter__(self):
        os.makedirs(self._dir, exist_ok=True)
        self._fd = os.open(self._lockpath, os.O_CREAT | os.O_RDWR)
        deadline = time.time() + 30
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() > deadline:
                    sys.exit("[mgmt_alloc] 台帳ロック取得タイムアウト(30s)。"
                             "別セッションの allocate/release が固まっていないか確認")
                time.sleep(0.2)
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"version": 1, "leases": {}}
        return self

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, self.path)

    def __exit__(self, *exc):
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)

    def used_ips(self, exclude=None):
        return {ip for pid, l in self.data["leases"].items()
                if pid != exclude for ip in l["nodes"].values()}


def write_map(path, mgmt_map):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(mgmt_map, f, sort_keys=False)


# ---------------------------------------------------------------- allocate

def cmd_allocate(a):
    pool = load_pool(a.repo)
    nodes = [n.strip() for n in a.nodes.split(",") if n.strip()]
    if not nodes:
        sys.exit("[mgmt_alloc] --nodes が空です")
    with Ledger(a.repo) as led:
        leases = led.data["leases"]
        cur = leases.get(a.problem)
        if cur and set(cur["nodes"]) == set(nodes):
            # 同一問題の再 build。稼働中ラボと割当がズレないよう既存を維持。
            mm = cur["nodes"]
            print(f"[mgmt_alloc] 既存リースを再利用: {a.problem} "
                  f"{len(mm)}個 ({summarize(mm.values())})")
        else:
            used = led.used_ips(exclude=a.problem)  # ノード構成変更時は取り直し
            free = [ip for ip in pool if ip not in used]
            if len(nodes) > len(free):
                print(f"[mgmt_alloc] 割当失敗: 要求 {len(nodes)} 個 / 空き {len(free)} 個",
                      file=sys.stderr)
                for pid, l in sorted(leases.items()):
                    print(f"  使用中: {pid}  {len(l['nodes'])}個 "
                          f"({summarize(l['nodes'].values())})  {l['lab_name']}  "
                          f"{l['created']}", file=sys.stderr)
                print(f"  → 対処: scripts/lab.sh teardown <PROBLEM_ID> で解放するか、"
                      f"{len(free)} ノード以下の問題にしてください", file=sys.stderr)
                sys.exit(2)
            mm = dict(zip(nodes, free))  # first-fit(プール順の空き先頭から)
            leases[a.problem] = {
                "lab_name": lab_title(a.problem),
                "nodes": mm,
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            led.save()
            print(f"[mgmt_alloc] 割当: {a.problem} → {summarize(mm.values())} "
                  f"(空き残 {len(free) - len(nodes)}個)")
    if a.out:
        write_map(a.out, mm)
        print(f"[mgmt_alloc] wrote {a.out}")


# ---------------------------------------------------------------- release

def cmd_release(a):
    with Ledger(a.repo) as led:
        lease = led.data["leases"].pop(a.problem, None)
        if lease:
            led.save()
            print(f"[mgmt_alloc] released: {a.problem} "
                  f"({summarize(lease['nodes'].values())})")
        else:
            print(f"[mgmt_alloc] リースなし(解放済): {a.problem}")


# ---------------------------------------------------------------- status

def cmd_status(a):
    pool = load_pool(a.repo)
    gen_root = os.path.join(a.repo, "topologies", "_generated")
    with Ledger(a.repo) as led:
        leases = led.data["leases"]
        used = led.used_ips()
        free = [ip for ip in pool if ip not in used]
        print(f"プール: {len(pool)}個  使用中: {len(used)}個  空き: {len(free)}個 "
              f"({summarize(free)})")
        for pid, l in sorted(leases.items()):
            gen = "あり" if os.path.isdir(os.path.join(gen_root, pid)) else "★なし"
            print(f"  {pid}  {len(l['nodes'])}個 ({summarize(l['nodes'].values())})  "
                  f"{l['lab_name']}  {l['created']}  _generated:{gen}")
        # 旧方式(台帳導入前)で build されたままの生成物はサマリのみ表示。
        # 実際に CML で稼働中かはオフラインでは分からない → 突合は gc の仕事。
        if os.path.isdir(gen_root):
            old = [d for d in sorted(os.listdir(gen_root))
                   if d not in leases
                   and os.path.exists(os.path.join(gen_root, d, "mgmt_map.yml"))]
            if old:
                print(f"  参考: リース未登録の旧生成物 {len(old)} 件が _generated に残存"
                      f"(台帳導入前の build 痕跡)。CML 稼働中かの突合は "
                      f"`mgmt_alloc.py gc` で確認")


# ---------------------------------------------------------------- gc

def cmd_gc(a):
    from virl2_client import ClientLibrary  # 遅延import(オフライン系を軽く保つ)
    host = os.environ["CML_HOST"]
    url = host if host.startswith("http") else f"https://{host}"
    verify = os.environ.get("CML_VERIFY", "false").strip().lower() in ("1", "true", "yes")
    cl = ClientLibrary(url, os.environ["CML_USER"], os.environ["CML_PASS"],
                       ssl_verify=verify)

    cml = {}  # problem -> {"lab_name","nodes"}
    for lab in cl.all_labs():
        if not lab.title.startswith("CCNP-LAB-"):
            continue
        problem, nodes = parse_description(lab.description)
        if problem:
            cml[problem] = {"lab_name": lab.title, "nodes": nodes}
        else:
            print(f"  注意: {lab.title} に リース情報なし(台帳導入前のラボ)。"
                  f"使用IPを台帳が把握できない → 手動で teardown を推奨")

    gen_root = os.path.join(a.repo, "topologies", "_generated")
    with Ledger(a.repo) as led:
        leases = led.data["leases"]
        adopt = {p: v for p, v in cml.items() if p not in leases}
        # 「CMLに実体なし かつ _generated も無い」= teardown 済みの残骸のみ回収。
        # build 直後(lab_up 前)のリースは _generated が有るので誤回収しない。
        stale = [p for p in leases
                 if p not in cml
                 and not os.path.isdir(os.path.join(gen_root, p))]
        if not adopt and not stale:
            print("[mgmt_alloc] gc: 台帳と CML は整合しています")
            return
        for p, v in sorted(adopt.items()):
            print(f"  採用(CML→台帳): {p}  {len(v['nodes'])}個 "
                  f"({summarize(v['nodes'].values())})  {v['lab_name']}")
        for p in sorted(stale):
            print(f"  回収(残骸リース): {p}  "
                  f"({summarize(leases[p]['nodes'].values())})")
        if not a.apply:
            print("[mgmt_alloc] dry-run(--apply で反映)")
            return
        now = datetime.datetime.now().isoformat(timespec="seconds")
        for p, v in adopt.items():
            leases[p] = {"lab_name": v["lab_name"], "nodes": v["nodes"],
                         "created": now + " (gc採用)"}
        for p in stale:
            del leases[p]
        led.save()
        print(f"[mgmt_alloc] gc 反映: 採用 {len(adopt)} / 回収 {len(stale)}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("allocate")
    p.add_argument("--repo", required=True)
    p.add_argument("--problem", required=True)
    p.add_argument("--nodes", required=True, help="カンマ区切り(target_nodes 順)")
    p.add_argument("--out", help="mgmt_map.yml の出力先")
    p.set_defaults(func=cmd_allocate)

    p = sub.add_parser("release")
    p.add_argument("--repo", required=True)
    p.add_argument("--problem", required=True)
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("status")
    p.add_argument("--repo", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("gc")
    p.add_argument("--repo", required=True)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_gc)

    a = ap.parse_args()
    a.repo = os.path.abspath(a.repo)
    a.func(a)


if __name__ == "__main__":
    main()
