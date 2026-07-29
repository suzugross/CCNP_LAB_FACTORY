#!/usr/bin/env python3
"""containerlab ラボのライフサイクル管理 (BL-061 CML×clab 複合ラボ用)。

問題パックの clab 資材(problems/<ID>/clab/)を szk-cl01 へ同期し、
containerlab deploy/destroy を SSH 経由で実行する。lab.sh から
provision/teardown 時に呼ばれる(clab_topology 未定義の問題は即スキップ)。

前提:
  - problem.yml に `clab_topology: clab/<name>.clab.yml`(パック内相対パス)
  - group_vars/all/local.yml に clab_host / clab_username / clab_labs_dir
  - 制御ホスト→clab_host は鍵認証済(BatchMode)。containerlab は SUID で sudo 不要
  - vJunos EVO の startup-config は vrnetlab init.conf への「連結」方式のため
    階層(カーリー)形式で書くこと(set 形式は不可・PoC 実証 2026-07-29)

使い方:
  clab_ops.py deploy  --repo REPO --problem ID [--wait 900] [--force]
  clab_ops.py destroy --repo REPO --problem ID
  clab_ops.py status  --repo REPO
"""
import argparse
import builtins
import json
import os
import subprocess
import sys
import time

import yaml


def print(*args, **kw):  # noqa: A001 — tee/パイプ越しでも進捗が即時に見えるように
    kw.setdefault("flush", True)
    builtins.print(*args, **kw)

EVO_RAM_MB = 7500          # vJunos EVO 1ノードの実測 RAM 消費(≈7.3GiB)+マージン
RAM_FLOOR_MB = 700         # デプロイ後にホストへ残すべき最低 available

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new"]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def clab_conn(repo):
    lv = load_yaml(f"{repo}/group_vars/all/local.yml")
    host = lv.get("clab_host")
    user = lv.get("clab_username")
    if not host or not user:
        sys.exit("group_vars/all/local.yml に clab_host/clab_username がありません")
    return f"{user}@{host}", lv.get("clab_labs_dir", f"/home/{user}/labs")


def ssh(target, cmd, check=True, capture=True):
    r = subprocess.run(["ssh", *SSH_OPTS, target, cmd],
                       capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.exit(f"ssh 失敗 rc={r.returncode}: {cmd}\n{(r.stderr or '')[:800]}")
    return r


def pack_topology(repo, problem):
    """problem.yml から clab トポロジ情報を返す。未定義なら None(=クリーンスキップ)。"""
    pmeta = load_yaml(f"{repo}/problems/{problem}/problem.yml")
    rel = pmeta.get("clab_topology")
    if not rel:
        return None
    topo_local = f"{repo}/problems/{problem}/{rel}"
    if not os.path.exists(topo_local):
        sys.exit(f"clab_topology が見つかりません: {topo_local}")
    topo = load_yaml(topo_local)
    return {
        "rel": rel,                          # パック内相対 (clab/xxx.clab.yml)
        "local_dir": os.path.dirname(topo_local),
        "file": os.path.basename(rel),
        "lab_name": topo["name"],
        "nodes": topo.get("topology", {}).get("nodes", {}) or {},
        "clab_nodes": pmeta.get("clab_nodes", {}) or {},
    }


def lab_containers(target, lab_name):
    """該当ラボのコンテナ {name: status} (docker ラベルで抽出)。"""
    r = ssh(target, f"docker ps --filter label=containerlab={lab_name} "
                    "--format '{{.Names}}\t{{.Status}}'", check=False)
    out = {}
    for line in (r.stdout or "").strip().splitlines():
        name, _, status = line.partition("\t")
        out[name] = status
    return out


def preflight_ram(target, topo, force):
    """vJunos EVO の必要 RAM をホスト available と突き合わせる。"""
    n_evo = sum(1 for n in topo["nodes"].values()
                if isinstance(n, dict) and "vjunos" in str(n.get("kind", "")).lower())
    if n_evo == 0:
        return
    # 同名ラボの再デプロイ(reconfigure)は現行分が解放されるので、その分を差し引く
    running = len(lab_containers(target, topo["lab_name"]))
    need = max(0, n_evo - running) * EVO_RAM_MB + RAM_FLOOR_MB
    avail = int(ssh(target, "free -m | awk '/^Mem:/{print $7}'").stdout.strip() or 0)
    print(f"RAM プリフライト: EVO {n_evo}台(稼働中 {running}) 必要≈{need}MB / available={avail}MB")
    if avail < need and not force:
        sys.exit(f"★RAM 不足: 他の clab ラボを destroy してから再実行してください "
                 f"(強行は --force)。ヒント: clab_ops.py status")


def cmd_deploy(a):
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        print(f"{a.problem}: clab_topology 未定義 → containerlab はスキップ")
        return
    target, labs_dir = clab_conn(a.repo)
    rdir = f"{labs_dir}/ccnp/{a.problem}"

    # 冪等ガード: 既に全ノード healthy なら再デプロイしない(provision の再実行で
    # 起動済み vJunos を壊さないため)。作り直しは --reconfigure で明示。
    conts = lab_containers(target, topo["lab_name"])
    if conts and not a.reconfigure:
        unhealthy = {n: s for n, s in conts.items() if "(healthy)" not in s}
        if not unhealthy:
            print(f"ラボ {topo['lab_name']} は既に全 {len(conts)} ノード healthy → スキップ"
                  f"(作り直しは --reconfigure)")
            return
        sys.exit(f"★ラボ {topo['lab_name']} は存在するが未 healthy: "
                 f"{json.dumps(unhealthy, ensure_ascii=False)}\n"
                 f"ブート中なら待つ / 壊れているなら --reconfigure で作り直し")

    preflight_ram(target, topo, a.force)

    print(f"== clab 資材同期: {topo['local_dir']}/ → {target}:{rdir}/")
    ssh(target, f"mkdir -p {rdir}")
    r = subprocess.run(["scp", *SSH_OPTS, "-r", *(
        [os.path.join(topo["local_dir"], f) for f in os.listdir(topo["local_dir"])]),
        f"{target}:{rdir}/"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"scp 失敗: {r.stderr[:800]}")

    print(f"== containerlab deploy: {topo['lab_name']} ({topo['file']})")
    r = ssh(target, f"cd {rdir} && containerlab deploy -t {topo['file']} --reconfigure 2>&1 | tail -5",
            check=False)
    print((r.stdout or "").strip())
    if r.returncode != 0:
        sys.exit(f"containerlab deploy 失敗 rc={r.returncode}")

    print(f"== healthy 待ち (最大 {a.wait}s・vJunos EVO ブートは6〜8分)")
    t0 = time.time()
    while True:
        conts = lab_containers(target, topo["lab_name"])
        unhealthy = {n: s for n, s in conts.items() if "(healthy)" not in s}
        if conts and not unhealthy:
            print(f"全 {len(conts)} ノード healthy ({int(time.time()-t0)}s)")
            break
        if time.time() - t0 > a.wait:
            sys.exit(f"★healthy 待ちタイムアウト: {json.dumps(unhealthy, ensure_ascii=False)}")
        time.sleep(15)
    for name, ip in (topo["clab_nodes"] or {}).items():
        # 再デプロイでノードのホスト鍵が変わる → 制御ホストの古い known_hosts を掃除
        # (残っていると ansible network_cli が host key mismatch で採点不能になる)
        subprocess.run(["ssh-keygen", "-R", str(ip)], capture_output=True)
        print(f"  node {name}: mgmt {ip} (制御ホストから直達・known_hosts 掃除済)")


def cmd_destroy(a):
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        print(f"{a.problem}: clab_topology 未定義 → containerlab はスキップ")
        return
    target, labs_dir = clab_conn(a.repo)
    rdir = f"{labs_dir}/ccnp/{a.problem}"
    r = ssh(target, f"cd {rdir} 2>/dev/null && containerlab destroy -t {topo['file']} --cleanup 2>&1 | tail -3",
            check=False)
    print((r.stdout or r.stderr or "").strip() or "(既に無し)")
    # ラボ定義ディレクトリも掃除(資材の正本はリポジトリ側)
    ssh(target, f"rm -rf {rdir}", check=False)
    print(f"destroy 完了: {topo['lab_name']}")


def cmd_status(a):
    target, _ = clab_conn(a.repo)
    r = ssh(target, "containerlab inspect --all 2>/dev/null | grep -vE '^.[─╭╰┼┬┴]' ; free -h | head -2",
            check=False)
    print((r.stdout or "").strip() or "(clab ラボ無し)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("deploy", cmd_deploy), ("destroy", cmd_destroy), ("status", cmd_status)):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True)
        if name != "status":
            p.add_argument("--problem", required=True)
        if name == "deploy":
            p.add_argument("--wait", type=int, default=900)
            p.add_argument("--force", action="store_true")
            p.add_argument("--reconfigure", action="store_true")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
