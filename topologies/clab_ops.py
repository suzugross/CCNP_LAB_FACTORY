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
  clab_ops.py reset   --repo REPO --problem ID [--rebuild]   # やり直し: Junos を構築直後の設定へ戻す(数秒)。だめなら作り直す
  clab_ops.py baseline --repo REPO --problem ID   # いまの Junos の設定を戻り先として控え直す(deploy の最後に自動で行う)
  clab_ops.py cli     --repo REPO --problem ID --node JUN02 -- "show firewall" "show log fw-drops"   # Junos の運用モードに流す(採点の口)
  clab_ops.py revive  --repo REPO --problem ID [--wait 900] [--force]   # ホストごと落ちた後: 止まったコンテナを設定を残したまま起こす
      # deploy も、止まったコンテナが残っていれば作り直さずにこれを行う(作り直しは --reconfigure)
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

def node_is_host(nd):
    """ラベル ccnp-role: host のノード= サーバ役(FRR のイメージで作ったホストなど)。ワークスペースの図ではホストとして描き、
    コンソール(ワークスペース・connect)は vtysh でなく Linux のシェルで開く。採点の exec と起動の判定は種類(node_family)どおり。"""
    lab = (nd or {}).get("labels") or {} if isinstance(nd, dict) else {}
    return str(lab.get("ccnp-role", "")).lower() == "host"


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


def wait_ready(target, topo, wait, expect=0):
    """ラボの全ノードが起動を終えるまで待つ(expect= 動いているべきコンテナの数。0 なら数は見ない)。"""
    print(f"== healthy 待ち (最大 {wait}s・vJunos EVO は 2 分前後)")
    t0 = time.time()
    while True:
        conts = lab_containers(target, topo["lab_name"])
        unhealthy = not_ready(target, topo, conts)
        if conts and not unhealthy and len(conts) >= expect:
            print(f"全 {len(conts)} ノード healthy ({int(time.time()-t0)}s)")
            return
        if time.time() - t0 > wait:
            if len(conts) < expect:
                unhealthy["(動いているコンテナ)"] = f"{len(conts)}/{expect}"
            sys.exit(f"★healthy 待ちタイムアウト: {json.dumps(unhealthy, ensure_ascii=False)}")
        time.sleep(15)


def cmd_deploy(a):
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        print(f"{a.problem}: clab_topology 未定義 → containerlab はスキップ")
        return
    target, labs_dir = clab_conn(a.repo)
    rdir = f"{labs_dir}/ccnp/{a.problem}"

    # 止まったコンテナが残っている(ホストごと落ちた後など・BL-279)→ 作り直さずに起こし直す。作り直すと vJunos の
    # ディスクごと消え、解いた設定が失われる(provision を打ち直した時の事故の防止)。作り直しは --reconfigure で明示。
    if not a.reconfigure and stopped_containers(target, topo["lab_name"]):
        print("== 止まったコンテナが残っています → 作り直さずに起こし直します(解いた設定を残すため・作り直しは --reconfigure)")
        revive(a.repo, topo, target, rdir, a.wait, a.force)
        return

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

    wait_ready(target, topo, a.wait)
    jump =(load_yaml(f"{a.repo}/group_vars/all/local.yml") or {}).get("clab_mgmt_jump") or ""
    via = f"踏み台 {jump} 経由" if jump else "制御ホストから直達"
    for name, ip in (topo["clab_nodes"] or {}).items():
        # 再デプロイでノードのホスト鍵が変わる → 制御ホストの古い known_hosts を掃除
        # (残っていると ansible network_cli が host key mismatch で採点不能になる)
        subprocess.run(["ssh-keygen", "-R", str(ip)], capture_output=True)
        print(f"  node {name}: mgmt {ip} ({via}・known_hosts 掃除済)")
    # 速いやり直しの戻り先(cmd_reset)。控えられなくてもラボは使える(やり直しが作り直しになるだけ)
    if junos_nodes(topo):
        print("== 構築直後の設定を控える(速いやり直しの戻り先)")
        junos_baseline(a.repo, topo)


# --------------------------------------------------------------------------
# 速いやり直し(BL-275・2026-11-15)。学習ラボの Junos を「構築直後の設定」へ戻す(作り直さない・数秒)。
#   控え= deploy が healthy を確かめた直後に、Junos の機器ごとに running の設定をホーム ディレクトリへ save する
#         (/var/tmp は `request system storage cleanup` で消えうるので避ける)。
#   戻す= configure → rollback 0 → load override <控え> → commit and-quit → `show configuration | compare <控え>` が空。
#   ★共有の設定モードにいる解く側のセッションは残る(未 commit の変更は消える)。configure exclusive／private のセッションが
#     あると鍵で拒まれる(2026-11-15 実測)→ そのセッションを request system logout pid で切ってから 1 回だけやり直す。
#   控えが無い・ログインできない・戻した後も控えと食い違う時は、作り直し(deploy --reconfigure)へ切り替える。
#   FRR・ホストは戻さない(課題で変えない約束)。サーバの上も作業する問題は problem.yml の linux_reset_exec を docker exec で流す。
# --------------------------------------------------------------------------
JUNOS_BASELINE = "ccnp-baseline.conf"
_JUNOS_RESET = ["configure", "rollback 0", f"load override {JUNOS_BASELINE}", "commit and-quit",
                # commit が通らなかった時だけ効く(設定モードに残っている)。通っていれば運用モードの構文エラーで無害
                "rollback 0", "exit"]


def junos_nodes(topo):
    """[(ノード名(clab_nodes のキー), 管理アドレス)]= Junos の機器。"""
    ips = {str(k).lower(): (k, v) for k, v in (topo["clab_nodes"] or {}).items()}
    out = []
    for name, nd in topo["nodes"].items():
        if node_family(nd) == "junos":
            key, ip = ips.get(str(name).lower(), (str(name).upper(), (nd or {}).get("mgmt-ipv4")))
            if ip:
                out.append((str(key), str(ip)))
    return out


def _junos_cli(repo, todo):
    """todo= {ノード名: (管理アドレス, [CLI の行])} を並べて流す → {ノード名: 出力}(ログインできなければ「★…」)。
    pty なしのシェルに行を流すと Junos の CLI が 1 行ずつ実行する(2026-11-15 実測)。経路はワークスペースと同じ
    (szk-cl01 を踏み台に管理アドレスへ SSH)。"""
    import asyncio
    import asyncssh
    lv = load_yaml(f"{repo}/group_vars/all/local.yml") or {}
    user, pw = lv.get("clab_node_username") or "admin", lv.get("clab_node_password") or "admin@123"

    async def one(outer, ip, lines):
        try:
            inner = await outer.connect_ssh(ip, username=user, password=pw, known_hosts=None, client_keys=None,
                                            config=[], connect_timeout=15)
        except (OSError, asyncssh.Error) as e:
            return f"★cannot log in to {ip} ({type(e).__name__}: {e})"
        try:
            r = await asyncio.wait_for(inner.run(input="\n".join(lines) + "\n"), 240)
            return (r.stdout or "") + (r.stderr or "")
        except asyncio.TimeoutError:
            return f"★timed out on {ip}"
        finally:
            inner.close()

    async def run():
        outer = await asyncssh.connect(lv["clab_host"], username=lv["clab_username"], known_hosts=None, config=[],
                                       connect_timeout=15)
        try:
            res = await asyncio.gather(*(one(outer, ip, lines) for ip, lines in todo.values()))
        finally:
            outer.close()
        return dict(zip(todo, res))

    return asyncio.run(run())


def _same_as_baseline(out):
    """`show configuration | compare <控え>` の出力 → 差が無ければ True(差分の行・エラーがあれば False)。"""
    body = [ln for ln in out.splitlines() if ln.strip() and not re.match(r"^\S+@\S+[>#]", ln)]
    return not body


def junos_baseline(repo, topo):
    """Junos の機器ごとに、いまの設定を控えに save する。失敗したノードの名前の一覧を返す。"""
    nodes = junos_nodes(topo)
    if not nodes:
        return []
    res = _junos_cli(repo, {n: (ip, [f"show configuration | save {JUNOS_BASELINE}"]) for n, ip in nodes})
    bad = []
    for n, out in res.items():
        m = re.search(r"Wrote (\d+) lines", out)
        print(f"  {n}: 構築直後の設定を控えた({m.group(1)} 行・{JUNOS_BASELINE})" if m else
              f"  ★{n}: 設定を控えられません: {out.strip()[-300:]}")
        if not m:
            bad.append(n)
    return bad


def junos_restore(repo, topo):
    """Junos の機器を控えへ戻す。戻せなかったノード {名前: 理由} を返す(空= 全部戻った)。"""
    nodes = dict(junos_nodes(topo))
    if not nodes:
        return {}
    have = _junos_cli(repo, {n: (ip, [f"file list {JUNOS_BASELINE}"]) for n, ip in nodes.items()})
    bad = {}
    for n, out in have.items():
        if out.startswith("★"):
            bad[n] = out[1:]
        elif "No such file" in out or JUNOS_BASELINE not in out:
            bad[n] = "no saved baseline (the lab was built before the fast reset existed)"
    todo = {n: (ip, _JUNOS_RESET) for n, ip in nodes.items() if n not in bad}
    res = _junos_cli(repo, todo) if todo else {}
    # 鍵で拒まれた(configure exclusive／private のセッションがいる)→ そのセッションを切って 1 回だけやり直す
    retry = {}
    for n, out in res.items():
        if "commit complete" not in out and ("locked by" in out or "private edits in use" in out):
            pids = sorted(set(re.findall(r"\(pid (\d+)\)", out)))
            if pids:
                print(f"  {n}: 設定の鍵を持つセッション(pid {', '.join(pids)})を切ってからやり直します")
                retry[n] = (nodes[n], [f"request system logout pid {p}" for p in pids] + _JUNOS_RESET)
    if retry:
        res.update(_junos_cli(repo, retry))
    chk = _junos_cli(repo, {n: (nodes[n], [f"show configuration | compare {JUNOS_BASELINE}"]) for n in res})
    for n, out in res.items():
        if out.startswith("★"):
            bad[n] = out[1:]
        elif "commit complete" not in out:
            err = re.findall(r"^error: .*$", out, re.M)
            bad[n] = "commit failed: " + (err[0] if err else out.strip()[-300:])
        elif not _same_as_baseline(chk.get(n, "")):
            bad[n] = "the configuration still differs from the saved baseline after the commit"
        else:
            print(f"  {n}: 構築直後の設定へ戻した(load override → commit・控えと同じ)")
    return bad


# 設定を戻しても機器の中に残るもの(2026-11-15 JNT-03 で実測): firewall filter のカウンタ・`show firewall log` の記録・
# syslog のファイル。前の 2 つはどの問題でも消す。ファイルなど問題ごとのものは problem.yml の
# `junos_reset_exec: {<NODE>: [<運用モードの行>, …]}`(例 `file delete /var/log/fw-drops`)。戻した後に流す(syslog は
# 戻した commit でそのファイルを閉じている)。
_JUNOS_AFTER_RESET = ["clear firewall all", "clear firewall log"]


def junos_after_reset(repo, problem, topo):
    extra = (load_yaml(f"{repo}/problems/{problem}/problem.yml") or {}).get("junos_reset_exec") or {}
    extra = {str(k).lower(): v for k, v in extra.items()}
    todo = {n: (ip, _JUNOS_AFTER_RESET + list(extra.get(n.lower(), []))) for n, ip in junos_nodes(topo)}
    for n, out in _junos_cli(repo, todo).items():
        errs = [ln.strip() for ln in out.splitlines() if ln.startswith("error:") and "No such file" not in ln]
        print(f"  {n}: 残り物を消した({len(todo[n][1])} 行)" + (f" ★{errs[0]}" if errs else ""))


def cmd_cli(a):
    """Junos の機器の運用モードに行を流して出力を返す(採点の exec: local から使う・ワークスペースと同じ経路)。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    nodes = {n.lower(): (n, ip) for n, ip in junos_nodes(topo)}
    if str(a.node).lower() not in nodes:
        sys.exit(f"{a.node} は Junos の機器ではありません: {', '.join(n for n, _ in nodes.values())}")
    name, ip = nodes[str(a.node).lower()]
    lines = a.command[1:] if a.command[:1] == ["--"] else a.command
    out = _junos_cli(a.repo, {name: (ip, lines)})[name]
    sys.stdout.write(out)
    sys.exit(1 if out.startswith("★") else 0)


def linux_reset(repo, problem, topo):
    """problem.yml の linux_reset_exec を docker exec で流す(containerlab のノード)。失敗したノードの名前の一覧を返す。"""
    todo = (load_yaml(f"{repo}/problems/{problem}/problem.yml") or {}).get("linux_reset_exec") or {}
    if not todo:
        return []
    target, _ = clab_conn(repo)
    bad = []
    for node, cmds in todo.items():
        for cmd in cmds:
            r = ssh(target, f"docker exec {container_name(topo, node)} sh -lc {shlex.quote(cmd)}", check=False)
            print(f"  [{node}] {cmd}: {'ok' if r.returncode == 0 else f'FAILED (rc={r.returncode})'}")
            if r.returncode != 0:
                bad.append(node)
                break
    return bad


def cmd_baseline(a):
    """いまの Junos の設定を「構築直後の設定」として控え直す(deploy の最後に自動で行う。手で控え直す時だけ使う)。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    if junos_baseline(a.repo, topo):
        sys.exit(1)


def cmd_reset(a):
    """やり直し(lab.sh reset・ワークスペースの「最初からやり直す」)。Junos は控えへ戻し、だめなら作り直す。
    --rebuild は最初から作り直す。最後の行に「RESET fast」か「RESET rebuilt」を出す(呼び出し側が文言を選ぶ)。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    target, _ = clab_conn(a.repo)
    conts = lab_containers(target, topo["lab_name"])
    why = "--rebuild" if a.rebuild else None
    if not why and not conts:
        why = "the lab is not running"
    if not why and not junos_nodes(topo):
        why = "no Junos devices to restore"
    if not why:
        unready = not_ready(target, topo, conts)
        if unready:
            why = "not every node is up: " + ", ".join(f"{node_of(topo, c)} ({s})" for c, s in unready.items())
    if not why:
        t0 = time.time()
        print("== やり直し: Junos の機器を構築直後の設定へ戻します(load override)")
        bad = junos_restore(a.repo, topo)
        if not bad:
            junos_after_reset(a.repo, a.problem, topo)
            if linux_reset(a.repo, a.problem, topo):
                sys.exit("★サーバを戻せませんでした(linux_reset_exec)")
            print(f"RESET fast ({int(time.time() - t0)}s)")
            return
        why = "; ".join(f"{n}: {r}" for n, r in bad.items())
    print(f"== やり直し: 作り直します({why})")
    a.reconfigure, a.force = True, False
    cmd_deploy(a)
    print("RESET rebuilt")


# --------------------------------------------------------------------------
# 起こし直し(BL-279・2026-11-15)。ホスト(szk-cl01 の載る VMware Workstation)ごと落ちると、ラボのコンテナは消えずに
# 止まった状態(Exited (255))で残り、vJunos の設定もコンテナの中のディスク(vrnetlab の overlay)に残る。
# ★作り直す(deploy --reconfigure)とこのディスクごと消える。起こし直しは消さずに次の順で戻す(JNT-03 で手で実証):
#   ① 動いているノードがあれば止める(相手が止まった時点で、その間のリンクの veth は消えている。全部そろえて起こす)
#   ② vJunos の起動用の設定(vrnetlab の init.conf・juniper.conf)を、launch.py がもう一度読める形に整える(revive の中の注)。
#      起動用のディスクは既にあるディスクの設定を変えない(コミット済みの設定がそのまま残る・JNT-03 で確認)
#   ③ docker start → ④ リンクを `containerlab tools veth create` で張り直す(vrnetlab は CLAB_INTFS 本がそろうまで VM を
#      起こさずに待ち、既にある overlay をそのまま使う) → ⑤ ノードの exec:(サーバ役の Web など)を流し直す → ⑥ 起動を待つ
# 張り直すリンクは、コンテナを作ったときのトポロジ(deploy が szk-cl01 に送った写し)から取る。リポの版が後で変わっても合う。
# 扱えないもの(veth 以外のリンク・ethN でない名前のインターフェース)があれば、何も触らずに止める(作り直しは reset --rebuild)。
# Junos の et- は起動から 1 分ほど後に現れ、OSPF・BGP が上がるのはさらに 1〜2 分後(JNT-03 の実測)。
# --------------------------------------------------------------------------
CONTAINERLESS_KINDS = {"bridge", "ovs-bridge"}   # コンテナを作らないノード(リンクの端は bridge:<名前>:<IF>)


def lab_all_containers(target, lab_name):
    """該当ラボのコンテナ {name: (State, Status)}。止まっているものも含む(docker ps -a)。"""
    r = ssh(target, f"docker ps -a --filter label=containerlab={lab_name} "
                    "--format '{{.Names}}\t{{.State}}\t{{.Status}}'", check=False)
    out = {}
    for line in (r.stdout or "").strip().splitlines():
        name, state, status = (line.split("\t") + ["", ""])[:3]
        out[name] = (state, status)
    return out


def stopped_containers(target, lab_name):
    """該当ラボの、動いていないコンテナ {name: Status}。"""
    return {c: s for c, (st, s) in lab_all_containers(target, lab_name).items() if st != "running"}


def _revive_plan(topo, spec):
    """コンテナを作ったときのトポロジ spec → (コンテナのノード [名前], リンク [(端 A, 端 B, mtu)], exec {名前: [行]})。
    張り直せないものがあれば ValueError。"""
    nodes = (spec.get("topology") or {}).get("nodes") or {}
    kinds = {str(n): str((nd or {}).get("kind", "")).lower() for n, nd in nodes.items()}

    def end(n, i):
        n, i = str(n), str(i)
        if n not in kinds:
            raise ValueError(f"リンクの端 {n}:{i} のノードがトポロジにありません")
        if kinds[n] in CONTAINERLESS_KINDS:
            return f"{kinds[n]}:{n}:{i}"
        if not re.fullmatch(r"eth\d+", i):
            raise ValueError(f"{n}:{i} は ethN でない名前(インターフェースの別名)なので張り直せません")
        return f"{container_name(topo, n)}:{i}"

    links = []
    for ln in (spec.get("topology") or {}).get("links") or []:
        typ, eps = ln.get("type", "veth"), ln.get("endpoints") or []
        if typ != "veth" or len(eps) != 2:
            raise ValueError(f"veth 以外のリンク(type: {typ})は張り直せません")
        ends = []
        for e in eps:
            n, i = (e.partition(":")[::2] if isinstance(e, str) else
                    (e.get("node"), e.get("interface")) if isinstance(e, dict) else (None, None))
            if not n or not i:
                raise ValueError(f"リンクの端が読めません: {e}")
            ends.append(end(n, i))
        links.append((ends[0], ends[1], ln.get("mtu")))
    conts = [n for n, k in kinds.items() if k not in CONTAINERLESS_KINDS]
    execs = {n: [str(c) for c in (nodes[n] or {}).get("exec") or []] for n in conts if (nodes[n] or {}).get("exec")}
    return conts, links, execs


def revive(repo, topo, target, rdir, wait, force):
    """止まったコンテナを、中の設定を残したまま起こしてリンクを張り直す。全部動いていれば何もしない。"""
    allc = lab_all_containers(target, topo["lab_name"])
    if not allc:
        sys.exit(f"★ラボ {topo['lab_name']} のコンテナが残っていません → 起こし直せません。provision で作り直してください")
    stopped = {c: s for c, (st, s) in allc.items() if st != "running"}
    if not stopped:
        print(f"ラボ {topo['lab_name']} は全 {len(allc)} ノード動いています → 起こし直しは不要")
        return
    r = ssh(target, f"cat {rdir}/{topo['file']}", check=False)
    if r.returncode == 0 and (r.stdout or "").strip():
        spec, src = yaml.safe_load(r.stdout) or {}, f"{rdir}/{topo['file']}"
    else:
        spec, src = load_yaml(os.path.join(topo["local_dir"], topo["file"])) or {}, "リポの版(szk-cl01 の写しが無い)"
    try:
        nodes, links, execs = _revive_plan(topo, spec)
    except ValueError as e:
        sys.exit(f"★起こし直せません: {e}\n  作り直すなら scripts/lab.sh reset <ID> --rebuild(解いた設定は消えます)")
    if not nodes:
        sys.exit(f"★トポロジ({src})にノードがありません → 起こし直せません")
    want = {container_name(topo, n): n for n in nodes}
    missing = sorted(set(want) - set(allc))
    if missing:
        sys.exit(f"★コンテナが欠けています({', '.join(missing)}) → 起こし直せません。"
                 f"作り直すなら scripts/lab.sh reset <ID> --rebuild(解いた設定は消えます)")
    print(f"== 起こし直し: {topo['lab_name']}(止まっている {len(stopped)}/{len(allc)} ノード・リンク {len(links)} 本"
          f"・トポロジ= {src})")
    preflight_ram(target, topo, force)
    running = [c for c in want if c not in stopped]
    if running:
        print(f"  動いているノードも止めます(リンクを全部張り直すため): {', '.join(want[c] for c in running)}")
        ssh(target, "docker stop -t 30 " + " ".join(running))
    vj = [c for c, n in want.items() if "vjunos" in str((spec["topology"]["nodes"].get(n) or {}).get("kind", "")).lower()]
    for c in vj:
        # vrnetlab の launch.py は起動のたびに init.conf を読む。startup-config があると init.conf を残して
        # juniper.conf に「init.conf＋startup-config」を >> で足し、無いと init.conf を juniper.conf へ名前を変える
        # (2 回目の起動が init.conf 無しで落ちる・2026-11-15 実測)。→ init.conf があれば juniper.conf を空に、
        # 無ければ juniper.conf(置き換え済みの init.conf そのもの)を init.conf に写す。
        r = ssh(target, f"d=$(mktemp -d); if docker cp {c}:/init.conf \"$d/i\" 2>/dev/null; then : > \"$d/e\" && "
                        f"docker cp \"$d/e\" {c}:/juniper.conf && echo emptied; else docker cp {c}:/juniper.conf \"$d/j\" && "
                        f"docker cp \"$d/j\" {c}:/init.conf && echo restored; fi; rc=$?; rm -rf \"$d\"; exit $rc", check=False)
        if r.returncode != 0:
            sys.exit(f"★{want[c]}: vrnetlab の起動用の設定を整えられません: {(r.stderr or r.stdout or '').strip()[-400:]}")
        how = "juniper.conf を空に(二重に足されないように)" if "emptied" in r.stdout else "init.conf を juniper.conf から戻した"
        print(f"  {want[c]}: vJunos の起動用の設定を整えた({how})")
    ssh(target, "docker start " + " ".join(want) + " >/dev/null")
    print(f"  docker start: {', '.join(nodes)}")
    # 起動の直後に落ちるもの(vrnetlab の launch.py の例外など)を見逃さない。落ちていればリンクは張れない
    time.sleep(5)
    dead = stopped_containers(target, topo["lab_name"])
    if dead:
        logs = ssh(target, f"docker logs --tail 6 {next(iter(dead))} 2>&1", check=False).stdout or ""
        sys.exit(f"★起こした直後に止まりました: {json.dumps(dead, ensure_ascii=False)}\n{logs.strip()[-800:]}")
    for a_end, b_end, mtu in links:
        m = f"-m {int(mtu)} " if mtu else ""
        r = ssh(target, f"NO_COLOR=1 timeout 120 containerlab tools veth create {m}-a {shlex.quote(a_end)} "
                        f"-b {shlex.quote(b_end)} 2>&1", check=False)
        if r.returncode != 0:
            sys.exit(f"★リンクを張れません: {a_end} -- {b_end}\n{(r.stdout or '').strip()[-600:]}")
        print(f"  link: {a_end} -- {b_end}" + (f"(mtu {mtu})" if mtu else ""))
    bad = []
    for n, cmds in execs.items():
        for cmd in cmds:
            r = ssh(target, f"timeout 60 docker exec {container_name(topo, n)} {shlex.join(shlex.split(cmd))}", check=False)
            print(f"  [{n}] exec {cmd}: {'ok' if r.returncode == 0 else f'FAILED (rc={r.returncode})'}")
            if r.returncode != 0:
                bad.append(n)
    wait_ready(target, topo, wait, expect=len(want))
    if junos_nodes(topo):
        print("  (Junos の et- は起動から 1 分ほど後に現れます。OSPF・BGP が上がるのはさらに 1〜2 分後)")
    if bad:
        sys.exit(f"★exec に失敗したノードがあります: {', '.join(sorted(set(bad)))}")
    print("REVIVE ok")


def cmd_revive(a):
    """起こし直し(lab.sh revive)。ホストごと落ちた後に、止まったコンテナを解いた設定を残したまま起こす。"""
    topo = pack_topology(a.repo, a.problem)
    if topo is None:
        sys.exit(f"{a.problem}: clab_topology 未定義")
    target, labs_dir = clab_conn(a.repo)
    revive(a.repo, topo, target, f"{labs_dir}/ccnp/{a.problem}", a.wait, a.force)


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
        shell = "vtysh" if fam == "frr" and not node_is_host(nd) else "bash"
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
                     ("import-ceos", cmd_import_ceos), ("baseline", cmd_baseline), ("reset", cmd_reset),
                     ("cli", cmd_cli), ("revive", cmd_revive)):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True)
        if name == "import-ceos":
            p.add_argument("--file", required=True)
            p.add_argument("--tag", default="")
        elif name != "status":
            p.add_argument("--problem", required=True)
        if name in ("exec", "connect", "cli"):
            p.add_argument("--node", required=True)
        if name in ("exec", "cli"):
            p.add_argument("command", nargs=argparse.REMAINDER)
        if name in ("deploy", "reset", "revive"):
            p.add_argument("--wait", type=int, default=900)
        if name in ("deploy", "revive"):
            p.add_argument("--force", action="store_true")
        if name == "deploy":
            p.add_argument("--reconfigure", action="store_true")
        if name == "reset":
            p.add_argument("--rebuild", action="store_true")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
