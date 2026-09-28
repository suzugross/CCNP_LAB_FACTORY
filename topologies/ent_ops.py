#!/usr/bin/env python3
"""GEN-ENT（BL-225・エンタープライズ拠点構築）の運用ツール。

  ent_ops.py <ID>                  採点前フック（grade.yml の pre_grade から呼ばれる。= pregrade）
  ent_ops.py pregrade <ID>         端末の DHCP 取り直し → ピアアドレス配布 → 回線切替の試験
  ent_ops.py renew <ID>            端末の DHCP 取り直しとピアアドレス配布だけ（切替試験なし）
  ent_ops.py solve <ID> [NODE...]  模範解（solution/golden.json）を telnet で投入（検証用）

回線切替の試験（PoC P4/P8 で確定した方式）:
  主回線の払い出しアドレスを SRVINET の iptables で DROP（= ISP 網内の障害。PPPoE は維持）→ 60 秒 →
  端末から `curl http://192.0.2.10/ip`（送信元を返す）→ DROP 解除 → 75 秒 → 再度確認。
  結果は probe_pc の /var/tmp/ccnp-failover.txt に BASE/FAIL/BACK= で書き、grading.yml が読む。
  平常時に外へ出られない（BASE が空）ときは待ちを省く。
認証は env CCNP_USER/CCNP_PASS（grade.yml が渡す）、無ければ group_vars/all/vault.yml（パスワード CCNP）。
"""
import concurrent.futures as cf
import json
import os
import re
import shlex
import sys
import time

import pexpect
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSH = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10"
PROMPT = re.compile(r"\r?\n([A-Za-z][\w-]*(?:\([\w-]+\))?#)")
ISP_DNS = "192.0.2.10"
PCS = ["PC01", "PC02", "PC03", "PC04", "PC05", "PC06"]


def creds():
    if os.environ.get("CCNP_USER") and os.environ.get("CCNP_PASS"):
        return os.environ["CCNP_USER"], os.environ["CCNP_PASS"]
    from ansible.parsing.vault import VaultLib, VaultSecret
    vl = VaultLib([("default", VaultSecret(b"CCNP"))])
    v = yaml.safe_load(vl.decrypt(open(os.path.join(REPO, "group_vars", "all", "vault.yml"), "rb").read()))
    return v["ansible_user"], v["ansible_ssh_pass"]


def hosts(pid):
    return yaml.safe_load(open(os.path.join(REPO, "topologies", "_generated", pid, "mgmt_map.yml")))


def spec(pid):
    return json.load(open(os.path.join(REPO, "problems", pid, "solution", "spec.json"), encoding="utf-8"))


def sh(ip, cmd, timeout=120, sudo=True):
    """Linux ノードで 1 コマンド（既定は sudo -n）。出力を返す（失敗時は空に近い文字列）。"""
    user, pw = creds()
    full = f"sudo -n bash -c {shlex.quote(cmd)}" if sudo else cmd
    c = pexpect.spawn(f"{SSH} {user}@{ip} {shlex.quote(full)}", timeout=timeout, encoding="utf-8",
                      codec_errors="ignore")
    try:
        c.expect("[Pp]assword:")
        c.sendline(pw)
        c.expect(pexpect.EOF)
        return (c.before or "").replace("\r\n", "\n").strip()
    except (pexpect.EOF, pexpect.TIMEOUT):
        return ""
    finally:
        c.close()


def log(msg):
    print(f"[ent_ops {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---- 端末 ---------------------------------------------------------------------
def renew(pid):
    """全端末で DHCP を取り直させ、各端末のアドレスを /var/tmp/ccnp-peers に配る。"""
    h = hosts(pid)
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda pc: sh(h[pc], "networkctl reconfigure ens3"), PCS))
    time.sleep(20)
    addrs = {}
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(zip(PCS, ex.map(lambda pc: sh(h[pc], "ip -4 -o addr show ens3", sudo=False), PCS)))
    for pc, out in res.items():
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", out)
        addrs[pc] = m.group(1) if m else ""
    peers = "\n".join(f"IP_{pc}={ip}" for pc, ip in addrs.items()) + "\n"
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda pc: sh(h[pc], f"printf %s {shlex.quote(peers)} > /var/tmp/ccnp-peers; "
                                         "chmod 644 /var/tmp/ccnp-peers"), PCS))
    log("端末のアドレス: " + ", ".join(f"{pc}={ip or '(なし)'}" for pc, ip in addrs.items()))
    return addrs


def src_ip(ip):
    out = sh(ip, f"curl -s -m5 http://{ISP_DNS}/ip", sudo=False)
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else ""


def pregrade(pid):
    s = spec(pid)
    h = hosts(pid)
    renew(pid)
    pc_ip, inet_ip = h[s["probe_pc"]], h["SRVINET"]
    pri = s["isp"][s["primary"]]["pub"]
    base = src_ip(pc_ip)
    result = {"BASE": base or "NONE", "EXT": "SKIPPED", "FAIL": "SKIPPED", "BACK": "SKIPPED"}
    if base:
        # 外部からの到達試験は「平常時に外へ出られる」=回線が生きているときだけ判定する
        # （PPPoE が無い盤面では応答しないのが当然で、偽の PASS になるため）。
        ext = sh(inet_ip, "/usr/local/bin/ccnp-probe")
        opened = re.findall(r"(?m)^(rt\d+_\w+)=(OPEN|OK)\s*$", ext)
        bras = re.findall(r"(?m)^bras_[ab]=OK\s*$", ext)
        result["EXT"] = ("CLOSED" if not opened and len(bras) == 2
                         else "OPEN:" + ",".join(k for k, _ in opened) if opened else "UNKNOWN")
        log(f"外部からの到達試験: {result['EXT']}")
        log(f"切替試験: 平常時の送信元 {base} → 主回線 {pri} を SRVINET で遮断して 60 秒待つ")
        rule = f"iptables -I INPUT -s {pri} -j DROP"
        try:
            sh(inet_ip, rule)
            time.sleep(60)
            result["FAIL"] = src_ip(pc_ip) or "NONE"
        finally:
            sh(inet_ip, f"while iptables -D INPUT -s {pri} -j DROP 2>/dev/null; do :; done")
        log(f"切替後の送信元 {result['FAIL']} → 遮断を解除して 75 秒待つ")
        time.sleep(75)
        result["BACK"] = src_ip(pc_ip) or "NONE"
        log(f"復旧後の送信元 {result['BACK']}")
    else:
        log("平常時にインターネットへ出られないため切替試験を省略")
    body = "".join(f"{k}={v}\n" for k, v in result.items())
    sh(pc_ip, f"printf %s {shlex.quote(body)} > /var/tmp/ccnp-failover.txt; chmod 644 /var/tmp/ccnp-failover.txt")
    log("結果: " + " ".join(f"{k}={v}" for k, v in result.items()))


# ---- 模範解の投入（検証用） -------------------------------------------------------
def login(ip):
    user, pw = creds()
    for i in range(6):
        try:
            c = pexpect.spawn(f"telnet {ip}", timeout=60, encoding="utf-8", codec_errors="ignore")
            c.expect(["Username:", "login:"])
            c.sendline(user)
            c.expect("Password:")
            c.sendline(pw)
            c.expect([r">", r"#"])
            return c
        except (pexpect.EOF, pexpect.TIMEOUT):
            log(f"{ip}: telnet ログイン再試行 {i + 1}")
            time.sleep(10)
    raise SystemExit(f"telnet ログイン失敗: {ip}")


def push(ip, lines):
    c = login(ip)
    c.sendline("terminal length 0")
    c.expect(PROMPT)
    c.sendline("configure terminal")
    c.expect(PROMPT)
    errs = []
    for line in lines:
        c.sendline(line)
        c.expect(PROMPT)
        if "% " in c.before:
            errs.append(f"{line.strip()} → {c.before.strip().splitlines()[-1]}")
    c.sendline("end")
    c.expect(PROMPT)
    c.sendline("write memory")
    c.expect(PROMPT, timeout=120)
    c.sendline("exit")
    c.close()
    return errs


ORDER = ["DHCP01", "SW03", "SW04", "SW05", "SW01", "SW02", "RT01", "RT02"]


def console_testbed(pid):
    """管理 IF を持たないノード（problem.yml の console_nodes）用の pyATS testbed（CML コンソール経由）。"""
    import hashlib
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import collect_console as CC
    from pyats.topology import loader
    from virl2_client import ClientLibrary
    loc = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    user, pw = creds()
    title = "CCNP-LAB-" + hashlib.md5(pid.encode()).hexdigest()[:8]
    cl = ClientLibrary(f"https://{loc['cml_host']}", loc["cml_username"], loc["cml_password"], ssl_verify=False)
    lab = [x for x in cl.all_labs() if x.title == title][0]
    tb = CC._patch_testbed(lab.get_pyats_testbed(), loc["cml_username"], loc["cml_password"], user, pw, pw)
    return loader.load(tb), CC


def push_console(dev, CC, lines):
    CC.connect_retry(dev)
    errs = []
    try:
        dev.enable()
        try:
            out = dev.configure(lines, timeout=600, error_pattern=[])
        except Exception as e:
            out = str(e)
            errs.append(f"configure 例外: {e}")
        errs += [ln.strip() for ln in str(out).splitlines() if ln.strip().startswith("%")]
        dev.execute("write memory", timeout=120)
    finally:
        CC.restore_console(dev)
        try:
            dev.disconnect()
        except Exception:
            pass
    return errs


def solve(pid, nodes):
    g = json.load(open(os.path.join(REPO, "problems", pid, "solution", "golden.json"), encoding="utf-8"))
    pm = yaml.safe_load(open(os.path.join(REPO, "problems", pid, "problem.yml"), encoding="utf-8"))
    con = set(pm.get("console_nodes", []) or [])
    h = hosts(pid)
    tb = CC = None
    for n in [x for x in ORDER if (not nodes or x in nodes)]:
        if n in con:
            if tb is None:
                tb, CC = console_testbed(pid)
            errs = push_console(tb.devices[n], CC, g[n])
            via = "console"
        else:
            errs = push(h[n], g[n])
            via = "telnet"
        log(f"{n}: {len(g[n])} 行投入 ({via})" + (f" ⚠ {len(errs)} 件のエラー: {errs[:5]}" if errs else ""))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] not in ("pregrade", "renew", "solve"):
        a = ["pregrade"] + a
    cmd, pid = a[0], a[1]
    if cmd == "pregrade":
        pregrade(pid)
    elif cmd == "renew":
        renew(pid)
    else:
        solve(pid, a[2:])


if __name__ == "__main__":
    main()
