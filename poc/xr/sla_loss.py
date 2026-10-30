#!/usr/bin/env python3
"""PoC: 向きごとの欠落を 10 ms の粒度で測る(BL-246 M10 TI-LFA)。

FROM(IOS)で IP SLA の udp-jitter を 1 回だけ回し、途中で CML のリンクにリンク条件 loss 100 を入れる。
終わったら `show ip sla statistics <op> details` の欠落(行き= Source to Destination・帰り= Destination to Source)を出し、
リンク条件を外して SLA の設定を消す。宛先には `ip sla responder` が要る(PoC の手順で入れる)。

usage: sla_loss.py <PID> <FROM> <DST> <SRC> [--fail A:B] [--how loss|stop] [--at 3] [--packets 1500] [--interval 10] [--port 5000] [--op 10]
  --fail を付けないと故障なしで測る(基準)。--how stop はリンク条件でなく CML のリンクそのものを切る(キャリア断。終わったらつなぎ直す)。出力の `== LOSS SD n DS m` の n×interval ≒ 行きの止まった時間(ms)。
資格情報は環境変数 NODE_USER / NODE_PASS(`source poc/xr/env.sh`)。
"""
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "topologies"))
from login_probe import Shell, cml_link, connect, mgmt_ip  # noqa: E402


def link_obj(pid, a, b):
    """CML のリンク a-b(virl2_client の Link)。"""
    import warnings
    import yaml
    warnings.filterwarnings("ignore")
    from virl2_client import ClientLibrary
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    title = yaml.safe_load(open(f"{repo}/topologies/_generated/{pid}/lab.yaml"))["lab"]["title"]
    cfg = yaml.safe_load(open(f"{repo}/group_vars/all/local.yml"))
    cl = ClientLibrary(f"https://{cfg['cml_host']}", cfg["cml_username"], cfg["cml_password"], ssl_verify=False)
    lab = next(lb for lb in cl.all_labs(show_all=True) if lb.title == title)
    return next(lk for lk in lab.links() if {lk.node_a.label, lk.node_b.label} == {a, b})


def opt(args, name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def main():
    args = sys.argv[1:]
    fail = opt(args, "--fail", None)
    how = opt(args, "--how", "loss")
    at = float(opt(args, "--at", 3))
    packets = int(opt(args, "--packets", 1500))
    interval = int(opt(args, "--interval", 10))
    port = int(opt(args, "--port", 5000))
    op = int(opt(args, "--op", 10))
    pid, frm, dst, src = args[:4]
    user, pw = os.environ["NODE_USER"], os.environ["NODE_PASS"]
    c = connect(mgmt_ip(pid, frm), user, pw)
    sh = Shell(c)
    for ln in ["configure terminal", f"no ip sla {op}", f"ip sla {op}",
               f"udp-jitter {dst} {port} source-ip {src} num-packets {packets} interval {interval}",
               "exit", f"ip sla schedule {op} life 120 start-time now", "end"]:
        out = sh.send(ln, timeout=30)
        if "%" in out:
            print(out.strip())
    t0, mark = time.time(), {}
    th = None
    if fail:
        a, b = fail.split(":")

        def inject():
            time.sleep(at)
            try:
                if how == "stop":
                    link_obj(pid, a, b).stop(wait=False)
                    print(f"== LINK {a}-{b} stopped", flush=True)
                else:
                    cml_link(pid, a, b, 100)
                mark["t"] = time.time() - t0
            except Exception as e:
                print(f"== LINK FAILED: {type(e).__name__}: {e}", flush=True)
        th = threading.Thread(target=inject, daemon=True)
        th.start()
    run_s = packets * interval / 1000.0
    time.sleep(run_s + 8)
    if th:
        th.join(timeout=30)
    out = sh.send(f"show ip sla statistics {op} details", timeout=30)
    keep = [ln for ln in out.splitlines()
            if re.search(r"Loss|Number of|Return Code|Latest operation|RTT Values|Out Of Seq|Late|Skipped|Successes|Failures", ln)]
    print("\n".join(keep))
    sd = re.search(r"Loss Source to Destination:\s*(\d+)", out)
    ds = re.search(r"Loss Destination to Source:\s*(\d+)", out)
    if fail:
        try:
            if how == "stop":
                link_obj(pid, a, b).start(wait=False)
                print(f"== LINK {a}-{b} started", flush=True)
            else:
                cml_link(pid, a, b, None)
        except Exception as e:
            print(f"== LINK CLEAR FAILED: {type(e).__name__}: {e}", flush=True)
        if "t" in mark:
            print(f"== FAULT APPLIED at +{mark['t']:.1f}s (run {run_s:.1f}s)")
    for ln in ["configure terminal", f"no ip sla {op}", "end"]:
        sh.send(ln, timeout=30)
    c.close()
    sdv = int(sd.group(1)) if sd else -1
    dsv = int(ds.group(1)) if ds else -1
    print(f"== LOSS SD {sdv} DS {dsv} (x{interval} ms: SD ~{sdv * interval} ms, DS ~{dsv * interval} ms)")


if __name__ == "__main__":
    main()
