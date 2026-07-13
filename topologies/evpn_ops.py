#!/usr/bin/env python3
"""EVPN-VXLAN-01 運用 CLI (BL-055)。

  build     … ラボ import（無ければ）→ リース確保(allocate) → プリフライト
              ping → 起動 → 全ノード MGMT 到達まで待機
  status    … ノード状態
  solve     … ★検証用: 模範解答（task.md の全 Phase 最終形）を SSH 投入
  grade     … grading.yml の checks を SSH 収集 → grade.py で採点
  stop      … ラボ停止（状態保持）
  teardown  … 停止 → wipe → ラボ削除 → リース解放

前提: problems/EVPN-VXLAN-01/evpn-lab.yaml（リース .20, .31-.37 焼き込み済み・
学習者 day0=アンダーレイのみ）。受講者は CML コンソールで解く（伴走形式）。
機器ログイン: SUZUKI/CCNP（NX-OS は admin/cisco も可）。
★SDA-LISP-01 (.37-.45) と .37 が重なるため同時リース不可（RAM 的にも同時稼働不可）。
"""
import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request

import paramiko
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEM = "EVPN-VXLAN-01"
# ラボ名は mgmt_alloc.py の規約どおり md5 不透明化（受講者に問題IDを見せない）
LAB_TITLE = "CCNP-LAB-b7590c9b"
LAB_YAML = os.path.join(REPO, "problems", PROBLEM, "evpn-lab.yaml")
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")
if not os.path.exists(PY):
    PY = sys.executable

_local = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
CML_HOST = _local["cml_host"]
CML_USER = _local["cml_username"]
CML_PASS = _local["cml_password"]
BASE = f"https://{CML_HOST}/api/v0"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

MGMT = json.loads(yaml.safe_load(open(LAB_YAML))["lab"]["description"])["ccnp_lease"]["nodes"]
NXOS = {"LEAF1", "LEAF2", "LEAF3"}


# ---------------- CML API ----------------

def _req(method, path, data=None, token=None, ctype="application/json"):
    url = f"{BASE}/{path.lstrip('/')}"
    body = None
    if data is not None:
        body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", ctype)
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(r, context=CTX, timeout=120) as resp:
        t = resp.read().decode()
    try:
        return json.loads(t)
    except Exception:
        return t


def _auth():
    return _req("POST", "authenticate", {"username": CML_USER, "password": CML_PASS})


def find_lab(tok):
    for lid in _req("GET", "labs", token=tok):
        d = _req("GET", f"labs/{lid}", token=tok)
        if d.get("lab_title") in (LAB_TITLE, PROBLEM):
            return lid, d
    return None, None


# ---------------- SSH ----------------

PROMPT = re.compile(r"[\w.-]+(\(config[^)]*\))?[#>]\s*$")


def ssh_run(host, cmds, timeout=45):
    """各コマンドを invoke_shell で順次実行し (cmd, output) のリストを返す。"""
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, username="SUZUKI", password="CCNP", look_for_keys=False,
                allow_agent=False, timeout=20)
    sh = cli.invoke_shell(width=511)
    sh.settimeout(timeout + 5)

    def read_until_prompt(deadline):
        buf = ""
        t0 = time.time()
        while time.time() - t0 < deadline:
            if sh.recv_ready():
                buf += sh.recv(65535).decode("utf-8", "replace")
                if PROMPT.search(buf.rsplit("\n", 1)[-1]):
                    break
            else:
                time.sleep(0.1)
        return buf

    read_until_prompt(10)
    sh.send("terminal length 0\n")
    read_until_prompt(8)
    out = []
    for cmd in cmds:
        sh.send(cmd + "\n")
        time.sleep(0.3)
        out.append((cmd, read_until_prompt(timeout)))
    cli.close()
    return out


def _ping_ok(ip):
    return subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                          capture_output=True).returncode == 0


# ---------------- 模範解答（task.md 全 Phase 最終形・PoC 実機検証済み構文） ----------------
# ★Phase 3 の意図的失敗（associate-vrf 抜き）を経た後の完成形を投入する。

SOLVE = {
    "SPINE": [
        "conf t", "router bgp 65100",
        "bgp router-id 10.254.0.254",
        "no bgp default ipv4-unicast",
        "neighbor 10.254.0.1 remote-as 65100",
        "neighbor 10.254.0.1 update-source Loopback0",
        "neighbor 10.254.0.2 remote-as 65100",
        "neighbor 10.254.0.2 update-source Loopback0",
        "neighbor 10.254.0.3 remote-as 65100",
        "neighbor 10.254.0.3 update-source Loopback0",
        "address-family l2vpn evpn",
        "neighbor 10.254.0.1 activate",
        "neighbor 10.254.0.1 send-community both",
        "neighbor 10.254.0.1 route-reflector-client",
        "neighbor 10.254.0.2 activate",
        "neighbor 10.254.0.2 send-community both",
        "neighbor 10.254.0.2 route-reflector-client",
        "neighbor 10.254.0.3 activate",
        "neighbor 10.254.0.3 send-community both",
        "neighbor 10.254.0.3 route-reflector-client",
        "exit-address-family", "end", "write memory",
    ],
    "LEAF1": [
        "conf t",
        "feature bgp", "feature interface-vlan",
        "feature vn-segment-vlan-based", "feature nv overlay",
        "feature fabric forwarding",
        "nv overlay evpn",
        "fabric forwarding anycast-gateway-mac 0000.2222.3333",
        "vlan 100", "vn-segment 10100", "exit",
        "vlan 500", "vn-segment 50000", "exit",
        "vrf context TENANT-A", "vni 50000", "rd auto",
        "address-family ipv4 unicast",
        "route-target both auto", "route-target both auto evpn", "exit", "exit",
        "interface Vlan100", "no shutdown", "vrf member TENANT-A",
        "ip address 172.16.100.1/24", "fabric forwarding mode anycast-gateway", "exit",
        "interface Vlan500", "no shutdown", "vrf member TENANT-A", "ip forward", "exit",
        "router bgp 65100", "router-id 10.254.0.1",
        "neighbor 10.254.0.254", "remote-as 65100", "update-source loopback0",
        "address-family l2vpn evpn", "send-community", "send-community extended",
        "exit", "exit",
        "vrf TENANT-A", "address-family ipv4 unicast", "advertise l2vpn evpn",
        "exit", "exit", "exit",
        "evpn", "vni 10100 l2", "rd auto",
        "route-target import auto", "route-target export auto", "exit", "exit",
        "interface nve1", "no shutdown", "host-reachability protocol bgp",
        "source-interface loopback0",
        "member vni 10100", "ingress-replication protocol bgp", "exit",
        "member vni 50000 associate-vrf", "exit",
        "interface Ethernet1/2", "switchport", "switchport access vlan 100",
        "no shutdown", "end",
        "copy running-config startup-config",
    ],
    "LEAF2": [
        "conf t",
        "feature bgp", "feature interface-vlan",
        "feature vn-segment-vlan-based", "feature nv overlay",
        "feature fabric forwarding",
        "nv overlay evpn",
        "fabric forwarding anycast-gateway-mac 0000.2222.3333",
        "vlan 100", "vn-segment 10100", "exit",
        "vlan 200", "vn-segment 10200", "exit",
        "vlan 500", "vn-segment 50000", "exit",
        "vrf context TENANT-A", "vni 50000", "rd auto",
        "address-family ipv4 unicast",
        "route-target both auto", "route-target both auto evpn", "exit", "exit",
        "interface Vlan100", "no shutdown", "vrf member TENANT-A",
        "ip address 172.16.100.1/24", "fabric forwarding mode anycast-gateway", "exit",
        "interface Vlan200", "no shutdown", "vrf member TENANT-A",
        "ip address 172.16.200.1/24", "fabric forwarding mode anycast-gateway", "exit",
        "interface Vlan500", "no shutdown", "vrf member TENANT-A", "ip forward", "exit",
        "router bgp 65100", "router-id 10.254.0.2",
        "neighbor 10.254.0.254", "remote-as 65100", "update-source loopback0",
        "address-family l2vpn evpn", "send-community", "send-community extended",
        "exit", "exit",
        "vrf TENANT-A", "address-family ipv4 unicast", "advertise l2vpn evpn",
        "exit", "exit", "exit",
        "evpn",
        "vni 10100 l2", "rd auto",
        "route-target import auto", "route-target export auto", "exit",
        "vni 10200 l2", "rd auto",
        "route-target import auto", "route-target export auto", "exit", "exit",
        "interface nve1", "no shutdown", "host-reachability protocol bgp",
        "source-interface loopback0",
        "member vni 10100", "ingress-replication protocol bgp", "exit",
        "member vni 10200", "ingress-replication protocol bgp", "exit",
        "member vni 50000 associate-vrf", "exit",
        "interface Ethernet1/2", "switchport", "switchport access vlan 100",
        "no shutdown", "exit",
        "interface Ethernet1/3", "switchport", "switchport access vlan 200",
        "no shutdown", "end",
        "copy running-config startup-config",
    ],
    "LEAF3": [
        "conf t",
        "feature bgp", "feature interface-vlan",
        "feature vn-segment-vlan-based", "feature nv overlay",
        "nv overlay evpn",
        "vlan 500", "vn-segment 50000", "exit",
        "vrf context TENANT-A", "vni 50000", "rd auto",
        "address-family ipv4 unicast",
        "route-target both auto", "route-target both auto evpn", "exit",
        "ip route 198.51.100.0/24 192.168.100.2", "exit",
        "interface Vlan500", "no shutdown", "vrf member TENANT-A", "ip forward", "exit",
        "interface Ethernet1/2", "no switchport", "vrf member TENANT-A",
        "ip address 192.168.100.1/30", "no shutdown", "exit",
        "ip prefix-list PL-EXT seq 5 permit 198.51.100.0/24",
        "route-map RM-EXT permit 10",
        "match ip address prefix-list PL-EXT", "exit",
        "router bgp 65100", "router-id 10.254.0.3",
        "neighbor 10.254.0.254", "remote-as 65100", "update-source loopback0",
        "address-family l2vpn evpn", "send-community", "send-community extended",
        "exit", "exit",
        "vrf TENANT-A", "address-family ipv4 unicast", "advertise l2vpn evpn",
        "redistribute static route-map RM-EXT",
        "exit", "exit", "exit",
        "interface nve1", "no shutdown", "host-reachability protocol bgp",
        "source-interface loopback0",
        "member vni 50000 associate-vrf", "end",
        "copy running-config startup-config",
    ],
}


# ---------------- subcommands ----------------

def cmd_build(_):
    tok = _auth()
    lid, d = find_lab(tok)
    if lid is None:
        print(f"[build] import: {LAB_YAML}")
        r = _req("POST", "import", open(LAB_YAML).read(), token=tok, ctype="text/plain")
        lid = r["id"]
    else:
        print(f"[build] 既存ラボを使用: {lid} ({d.get('state')})")
    # リース登録（allocate は同一 problem+同一ノード集合なら再利用・冪等）。
    # ★yaml は .20, .31-.37 焼き込みの静的ラボなので、割当が一致しない場合は中止する。
    env = dict(os.environ, CML_HOST=CML_HOST, CML_USER=CML_USER, CML_PASS=CML_PASS)
    outmap = os.path.join(GEN_DIR, "mgmt_map.yml")
    os.makedirs(GEN_DIR, exist_ok=True)
    rc = subprocess.run([PY, os.path.join(REPO, "topologies", "mgmt_alloc.py"),
                         "allocate", "--repo", REPO, "--problem", PROBLEM,
                         "--nodes", ",".join(MGMT), "--out", outmap], env=env)
    if rc.returncode != 0:
        print("[build] ★中止: リース確保に失敗（mgmt_alloc.py status で確認を）")
        sys.exit(2)
    got = yaml.safe_load(open(outmap))
    got = got.get("mgmt_map", got) if isinstance(got, dict) else got
    diff = {n: (ip, got.get(n)) for n, ip in MGMT.items() if got.get(n) != ip}
    if diff:
        print(f"[build] ★中止: 割当リースが yaml 焼き込み値と不一致: {diff}")
        print("        （プール状況が変わっています。yaml の MGMT を再焼成するか、"
              "衝突リースの解放を検討。SDA-LISP-01 と .37 が重なる点に注意）")
        sys.exit(2)
    # プリフライト: 起動前に MGMT IP が生きていたら別ラボと衝突
    if (d or {}).get("state") != "STARTED":
        alive = [f"{n}={ip}" for n, ip in MGMT.items() if _ping_ok(ip)]
        if alive:
            print(f"[build] ★中止: 起動前なのに応答する MGMT IP があります: {alive}")
            print("        別ラボがリースを使用中の可能性。mgmt_alloc.py status で確認を。")
            sys.exit(2)
        print("[build] プリフライト OK → 起動")
        _req("PUT", f"labs/{lid}/start", token=tok)
    print("[build] 全ノード MGMT 到達待ち（NX-OS×3 は5分前後）…")
    deadline = time.time() + 900
    while time.time() < deadline:
        up = [n for n, ip in MGMT.items() if _ping_ok(ip)]
        print(f"  {len(up)}/{len(MGMT)} up")
        if len(up) == len(MGMT):
            print(f"[build] 完了。task.md を提示して伴走を開始してください。lab_id={lid}")
            return
        time.sleep(20)
    print("[build] ★タイムアウト: 未達ノードあり。evpn_ops.py status で確認を。")
    sys.exit(1)


def cmd_status(_):
    tok = _auth()
    lid, d = find_lab(tok)
    if lid is None:
        print("ラボ未作成（evpn_ops.py build）")
        return
    print(f"lab {lid} state={d.get('state')}")
    for n in _req("GET", f"labs/{lid}/nodes", token=tok):
        nd = _req("GET", f"labs/{lid}/nodes/{n}", token=tok)
        label = nd.get("label")
        mark = ""
        if label in MGMT:
            mark = "ping:OK" if _ping_ok(MGMT[label]) else "ping:NG"
        print(f"  {label:12} {nd.get('state'):10} {MGMT.get(label,''):14} {mark}")


def cmd_solve(_):
    for node, cmds in SOLVE.items():
        print(f"[solve] {node} ({MGMT[node]}) へ模範解答投入")
        out = ssh_run(MGMT[node], cmds, timeout=60)
        for c, o in out:
            if "Invalid" in o or "ERROR" in o or "% " in o:
                print(f"  ★要確認 [{node}] {c}\n{o}")
    print("[solve] 完了（ARP/Type-2 学習は grade の ping が温めます）")


def cmd_grade(a):
    grading = yaml.safe_load(open(os.path.join(REPO, "problems", PROBLEM, "grading.yml")))
    checks = grading["checks"]
    for chk in checks:
        node = chk["node"]
        try:
            out = ssh_run(MGMT[node], [chk["command"]], timeout=90)
            chk["stdout"] = out[0][1]
        except Exception as e:
            chk["stdout"] = f"(execute error: {e})"
        print(f"[grade] {chk['name']} … 収集済")
    os.makedirs(GEN_DIR, exist_ok=True)
    gi = os.path.join(GEN_DIR, "grade_input.json")
    json.dump(checks, open(gi, "w"), ensure_ascii=False, indent=1)
    argv = [PY, os.path.join(REPO, "topologies", "grade.py"), gi]
    if a.gate:
        argv.append("--gate")
    sys.exit(subprocess.run(argv).returncode)


def cmd_stop(_):
    tok = _auth()
    lid, _d = find_lab(tok)
    if lid:
        _req("PUT", f"labs/{lid}/stop", token=tok)
        print(f"[stop] {lid} 停止")


def cmd_teardown(_):
    tok = _auth()
    lid, _d = find_lab(tok)
    if lid:
        _req("PUT", f"labs/{lid}/stop", token=tok)
        _req("PUT", f"labs/{lid}/wipe", token=tok)
        _req("DELETE", f"labs/{lid}", token=tok)
        print(f"[teardown] {lid} 削除")
    env = dict(os.environ, CML_HOST=CML_HOST, CML_USER=CML_USER, CML_PASS=CML_PASS)
    subprocess.run([PY, os.path.join(REPO, "topologies", "mgmt_alloc.py"),
                    "release", "--repo", REPO, "--problem", PROBLEM], env=env)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for v in ("build", "status", "solve", "stop", "teardown"):
        sub.add_parser(v)
    pg = sub.add_parser("grade")
    pg.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    {"build": cmd_build, "status": cmd_status, "solve": cmd_solve,
     "grade": cmd_grade, "stop": cmd_stop, "teardown": cmd_teardown}[a.cmd](a)


if __name__ == "__main__":
    main()
