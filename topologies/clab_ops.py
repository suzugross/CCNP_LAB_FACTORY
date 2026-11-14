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

containerlab だけで回す問題(problem.yml の `platform: clab`・BL-274)も同じ道具で扱う。
CML を使わない問題では lab.sh が CML の手順を飛ばし、これだけを呼ぶ(CLAB-SOLO.design.md)。

使い方:
  clab_ops.py deploy  --repo REPO --problem ID [--wait 900] [--force] [--reconfigure]
  clab_ops.py destroy --repo REPO --problem ID
  clab_ops.py verify  --repo REPO --problem ID   # 採点の前: その問題のラボが動き、clab_nodes のアドレスと合うか
  clab_ops.py exec    --repo REPO --problem ID --node FRR1 -- vtysh -c "show ip route"   # ノードの中で実行(採点の口)
  clab_ops.py connect --repo REPO --problem ID --node FRR1   # 解く時の入り口(FRR は vtysh・Junos/EOS は ssh)
  clab_ops.py status  --repo REPO
  clab_ops.py import-ceos --repo REPO --file ~/images/cEOS64-lab-4.xx.yF.tar.xz [--tag 4.xx.yF]
      # arista.com(利用者登録が要る)から落とした cEOS-lab を szk-cl01 に取り込む → イメージ ceos:<版>

ノードの種類(node_family): トポロジの kind と image から junos / eos / frr / linux を決める。
  - FRR は `kind: frr`(containerlab 0.80 から・szk-cl01 は 2026-11-14 に 0.83)+ quay.io/frrouting/frr:containerlab-<版>。
    startup-config と daemons を書けば containerlab が /etc/frr を用意する。SSH admin/admin → vtysh もあるが、
    採点と connect はパスワードの要らない szk-cl01 の docker exec で vtysh に入る。
    旧い形(`kind: linux` + 公式イメージ・/etc/frr をフォルダごと bind)も同じ扱いで動く。
  - healthcheck の無いコンテナ(FRR・cEOS)は、CLI が応答したら起動済みとみなす(READY_PROBE)。

clab_nodes のキー(例 JUN01)は、トポロジのノード名(例 jun01)と大文字小文字を無視して一致させる。
"""
import argparse
import builtins
import json
import os
import re
import shlex
import subprocess
import sys
import time

import yaml


def print(*args, **kw):  # noqa: A001 — tee/パイプ越しでも進捗が即時に見えるように
    kw.setdefault("flush", True)
    builtins.print(*args, **kw)

# 1 ノードあたりの RAM の見積もり(MB)。実測(docker stats)に余裕を足した値: junos= vJunos EVO ≈7.3GiB(2026-07-28)・
# eos= cEOS 4.37.0F ≈1.56GiB・frr= FRR 10.7.1 ≈19MiB(2026-11-14)。
FAMILY_RAM_MB = {"junos": 7500, "eos": 2000, "frr": 150, "linux": 100}
RAM_FLOOR_MB = 700         # デプロイ後にホストへ残すべき最低 available
# healthcheck の無いコンテナの起動確認(コンテナの中で打って rc=0 なら起動済み)
# ★EOS は Cli が応答してもまだ SSH で入れない(作り直しの直後に Cli は即応答・SSH+enable は十数秒後・2026-11-14 実測)
#   → コンテナの中で 22 番が受け付けるかも見る(管理 IF は既定の VRF なので docker exec の名前空間から届く)。
READY_PROBE = {"frr": "vtysh -c 'show version'",
               "eos": "bash -c \"Cli -p 15 -c 'show version' >/dev/null && exec 3<>/dev/tcp/127.0.0.1/22\""}


def node_family(nd):
    """トポロジのノード定義 → junos / eos / frr / linux / None(bridge など)。"""
    nd = nd if isinstance(nd, dict) else {}
    kind = str(nd.get("kind", "")).lower()
    image = str(nd.get("image", "")).lower()
    if "vjunos" in kind or "junos" in kind:
        return "junos"
    if kind in ("ceos", "arista_ceos"):
        return "eos"
    if kind in ("frr", "frrouting") or (kind == "linux" and "frrouting/frr" in image):
        return "frr"
    if kind == "linux":
        return "linux"
    return None

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


def container_name(topo, node):
    """containerlab のコンテナ名(既定の接頭辞 clab-<ラボ名>-<ノード名>)。"""
    return f"clab-{topo['lab_name']}-{str(node).lower()}"


def node_of(topo, cname):
    pre = f"clab-{topo['lab_name']}-"
    return cname[len(pre):] if cname.startswith(pre) else cname


def not_ready(target, topo, conts):
    """起動を終えていないノード {コンテナ名: 状態}。healthcheck があればそれに従い、
    無いもの(FRR・cEOS)は CLI が応答するかで見る。"""
    bad = {}
    for cname, status in conts.items():
        if "(healthy)" in status:
            continue
        if "(health" in status or "(unhealthy)" in status or not status.startswith("Up"):
            bad[cname] = status
            continue
        probe = READY_PROBE.get(node_family(topo["nodes"].get(node_of(topo, cname))))
        if probe and ssh(target, f"docker exec {cname} {probe} >/dev/null 2>&1", check=False).returncode != 0:
            bad[cname] = f"{status} / CLI 未応答"
    return bad


def lab_nodes(target, lab_name):
    """該当ラボのノード {トポロジのノード名(小文字): {"ips": [...], "state": healthy/starting/running…}}。
    ssh が通らなければ None。"""
    fmt = ('{{index .Config.Labels "clab-node-name"}}\t'
           '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}\t'
           '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}')
    r = ssh(target, f"ids=$(docker ps -q --filter label=containerlab={lab_name}); "
                    f"[ -z \"$ids\" ] || docker inspect --format '{fmt}' $ids", check=False)
    if r.returncode == 255:
        return None
    out = {}
    for line in (r.stdout or "").strip().splitlines():
        name, ips, state = (line.split("\t") + ["", "", ""])[:3]
        out[name.strip().lower()] = {"ips": ips.split(), "state": state.strip()}
    return out


def preflight_ram(target, topo, force):
    """ノードの種類ごとの見積もり(FAMILY_RAM_MB)の合計をホストの available と突き合わせる。"""
    fams = [node_family(n) for n in topo["nodes"].values()]
    fams = [f for f in fams if f in FAMILY_RAM_MB]
    if not fams:
        return
    # 同名ラボの再デプロイ(reconfigure)は現行分が解放されるので、その分を差し引く
    running = [node_family(topo["nodes"].get(node_of(topo, c)))
               for c in lab_containers(target, topo["lab_name"])]
    need = RAM_FLOOR_MB
    for f in set(fams):
        need += max(0, fams.count(f) - running.count(f)) * FAMILY_RAM_MB[f]
    avail = int(ssh(target, "free -m | awk '/^Mem:/{print $7}'").stdout.strip() or 0)
    plan = "・".join(f"{f} {fams.count(f)}台" for f in sorted(set(fams)))
    print(f"RAM プリフライト: {plan}(稼働中 {len(running)}) 必要≈{need}MB / available={avail}MB")
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
        unhealthy = not_ready(target, topo, conts)
        if not unhealthy:
            print(f"ラボ {topo['lab_name']} は既に全 {len(conts)} ノード healthy → スキップ"
                  f"(作り直しは --reconfigure)")
            return
        sys.exit(f"★ラボ {topo['lab_name']} は存在するが未 healthy: "
                 f"{json.dumps(unhealthy, ensure_ascii=False)}\n"
                 f"ブート中なら待つ / 壊れているなら --reconfigure で作り直し")

    preflight_ram(target, topo, a.force)

    print(f"== clab 資材同期: {topo['local_dir']}/ → {target}:{rdir}/")
    # ★送る前に、リポから送るもの(トポロジ・startup-config・FRR の設定フォルダ)を先に消す。FRR は write memory で
    #   frr.conf を frr ユーザ(uid 100)・モード 600 で書き直すので、そのままでは上書き(scp)が拒否され、
    #   reset が前の設定のまま進む(2026-11-14 実測)。フォルダは suzuki の持ち物なので消すことはできる。
    #   containerlab のラボのフォルダ(clab-<name>/)には触らない。
    names = " ".join(shlex.quote(f) for f in os.listdir(topo["local_dir"]))
    ssh(target, f"mkdir -p {rdir} && cd {rdir} && rm -rf -- {names}")
    r = subprocess.run(["scp", *SSH_OPTS, "-r", *(
        [os.path.join(topo["local_dir"], f) for f in os.listdir(topo["local_dir"])]),
        f"{target}:{rdir}/"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"scp 失敗: {r.stderr[:800]}")

    print(f"== containerlab deploy: {topo['lab_name']} ({topo['file']})")
    # pipefail: tail の終了コードでなく containerlab の失敗を拾う(リモートは bash)
    r = ssh(target, f"set -o pipefail; cd {rdir} && containerlab deploy -t {topo['file']} --reconfigure 2>&1 | tail -5",
            check=False)
    print((r.stdout or "").strip())
    if r.returncode != 0:
        sys.exit(f"containerlab deploy 失敗 rc={r.returncode}")

    print(f"== healthy 待ち (最大 {a.wait}s・vJunos EVO は 2 分前後)")
    t0 = time.time()
    while True:
        conts = lab_containers(target, topo["lab_name"])
        unhealthy = not_ready(target, topo, conts)
        if conts and not unhealthy:
            print(f"全 {len(conts)} ノード healthy ({int(time.time()-t0)}s)")
            break
        if time.time() - t0 > a.wait:
            sys.exit(f"★healthy 待ちタイムアウト: {json.dumps(unhealthy, ensure_ascii=False)}")
        time.sleep(15)
    jump = (load_yaml(f"{a.repo}/group_vars/all/local.yml") or {}).get("clab_mgmt_jump") or ""
    via = f"踏み台 {jump} 経由" if jump else "制御ホストから直達"
    for name, ip in (topo["clab_nodes"] or {}).items():
        # 再デプロイでノードのホスト鍵が変わる → 制御ホストの古い known_hosts を掃除
        # (残っていると ansible network_cli が host key mismatch で採点不能になる)
        subprocess.run(["ssh-keygen", "-R", str(ip)], capture_output=True)
        print(f"  node {name}: mgmt {ip} ({via}・known_hosts 掃除済)")


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


def cmd_verify(a):
    """採点の前の照合(誤ったラボの採点の防止)。CML の labid の代わり。

    Junos を白紙から組ませる問題では設定に指紋を置けず、管理網(docker の clab ネットワーク)は全ラボ共通なので、
    別のラボが同じアドレスを使っていることがありうる。docker のラベルで「その問題のラボが動いていて、
    clab_nodes の各ノードがそのラボのコンテナで、管理アドレスが一致し、起動を終えている」ことを確かめる。
    外れたら rc=2(grade.yml が採点を中止する)。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        print(f"{a.problem}: clab_topology 未定義 → 照合なし")
        return
    target, _ = clab_conn(a.repo)
    nodes = lab_nodes(target, topo["lab_name"])
    if nodes is None:
        sys.exit(f"★clab ホスト {target} に届きません(止まっている?)。採点を中止します")
    if not nodes:
        print(f"★ラボ {topo['lab_name']} が動いていません(provision していないか、撤収済み)。採点を中止します")
        sys.exit(2)
    errs = []
    for name, ip in (topo["clab_nodes"] or {}).items():
        ent = nodes.get(str(name).lower())
        if ent is None:
            errs.append(f"{name}: ラボ {topo['lab_name']} にノード {str(name).lower()} がありません")
        elif str(ip) not in ent["ips"]:
            errs.append(f"{name}: 管理アドレスが違います(problem.yml {ip} / 実際 {' '.join(ent['ips']) or 'なし'})")
        elif ent["state"] not in ("healthy", "running"):
            errs.append(f"{name}: まだ起動中か異常です(状態 {ent['state']})")
    if errs:
        print(f"★ラボの照合に失敗({topo['lab_name']})。採点を中止します:")
        for e in errs:
            print(f"  - {e}")
        sys.exit(2)
    print(f"clab 照合 OK: ラボ {topo['lab_name']} / "
          + ", ".join(f"{n}={ip}" for n, ip in (topo["clab_nodes"] or {}).items()))


def cmd_exec(a):
    """ノードの中でコマンドを実行(szk-cl01 の docker exec)。stdout/stderr/rc をそのまま返す。採点の exec: frr の口。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    target, _ = clab_conn(a.repo)
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        sys.exit("実行するコマンドを -- の後に書いてください")
    r = subprocess.run(["ssh", *SSH_OPTS, target,
                        f"docker exec {container_name(topo, a.node)} {shlex.join(cmd)}"],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    sys.exit(r.returncode)


def cmd_connect(a):
    """解く時の入り口。FRR は szk-cl01 の docker exec で vtysh、Junos・EOS は管理アドレスへ ssh
    (管理網へは ~/.ssh/config の踏み台経由)。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    nd = topo["nodes"].get(str(a.node).lower())
    if nd is None:
        sys.exit(f"ノード {a.node} はトポロジにありません: {', '.join(topo['nodes'])}")
    fam = node_family(nd)
    target, _ = clab_conn(a.repo)
    if fam in ("frr", "linux"):
        shell = "vtysh" if fam == "frr" else "bash"
        os.execvp("ssh", ["ssh", "-t", *SSH_OPTS, target, f"docker exec -it {container_name(topo, a.node)} {shell}"])
    ips = {str(k).lower(): v for k, v in (topo["clab_nodes"] or {}).items()}
    ip = ips.get(str(a.node).lower()) or nd.get("mgmt-ipv4")
    if not ip:
        sys.exit(f"{a.node} の管理アドレスが分かりません(problem.yml の clab_nodes)")
    lv = load_yaml(f"{a.repo}/group_vars/all/local.yml") or {}
    user = (lv.get("clab_eos_username") or "admin") if fam == "eos" else (lv.get("clab_node_username") or "admin")
    os.execvp("ssh", ["ssh", f"{user}@{ip}"])


def cmd_import_ceos(a):
    """arista.com から落とした cEOS-lab のアーカイブを szk-cl01 へ送り、docker import で ceos:<版> にする。
    版はファイル名(cEOS64-lab-<版>.tar.xz)から取る。cgroup v2 のホストでは 4.32.0F 以降が要る(containerlab の文書)。"""
    path = os.path.expanduser(a.file)
    if not os.path.isfile(path):
        sys.exit(f"ファイルがありません: {path}")
    base = os.path.basename(path)
    m = re.match(r"cEOS(?:64)?-lab-(.+?)\.tar(?:\.xz)?$", base)
    tag = a.tag or (m.group(1) if m else "")
    if not tag:
        sys.exit("版が分かりません。--tag 4.xx.yF で指定してください")
    target, _ = clab_conn(a.repo)
    remote = f"/tmp/{base}"
    print(f"== 送る: {path} → {target}:{remote}")
    r = subprocess.run(["scp", *SSH_OPTS, path, f"{target}:{remote}"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"scp 失敗: {r.stderr[:800]}")
    print(f"== docker import → ceos:{tag}")
    r = ssh(target, f"docker import {shlex.quote(remote)} ceos:{shlex.quote(tag)}; rc=$?; rm -f {shlex.quote(remote)}; exit $rc",
            check=False)
    if r.returncode != 0:
        sys.exit(f"docker import 失敗: {(r.stderr or r.stdout or '')[:800]}")
    print(ssh(target, "docker images ceos --format '{{.Repository}}:{{.Tag}} {{.Size}}'", check=False).stdout.strip())


def cmd_status(a):
    target, _ = clab_conn(a.repo)
    r = ssh(target, "containerlab inspect --all 2>/dev/null | grep -vE '^.[─╭╰┼┬┴]'; echo '@@MEM@@'; free -h | head -2",
            check=False)
    if r.returncode == 255:
        print(f"(clab ホスト {target} に届きません。止まっていれば問題ありません)")
        return
    labs, _, mem = (r.stdout or "").partition("@@MEM@@")
    print(labs.strip() or "(clab ラボ無し)")
    print(mem.strip())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("deploy", cmd_deploy), ("destroy", cmd_destroy), ("verify", cmd_verify),
                     ("exec", cmd_exec), ("connect", cmd_connect), ("status", cmd_status),
                     ("import-ceos", cmd_import_ceos)):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True)
        if name == "import-ceos":
            p.add_argument("--file", required=True)
            p.add_argument("--tag", default="")
        elif name != "status":
            p.add_argument("--problem", required=True)
        if name in ("exec", "connect"):
            p.add_argument("--node", required=True)
        if name == "exec":
            p.add_argument("command", nargs=argparse.REMAINDER)
        if name == "deploy":
            p.add_argument("--wait", type=int, default=900)
            p.add_argument("--force", action="store_true")
            p.add_argument("--reconfigure", action="store_true")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
