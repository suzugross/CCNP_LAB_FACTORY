#!/usr/bin/env python3
"""GEN-S2SVPN (BL-063) 運用ツール: build / status / solve / grade / teardown / exec。

採点は「clear → 試験トラフィック → カウンタ読取」の順序制御が必要な
逐次効果ベースのため、ansible 採点パイプラインではなく本ツールが自前で行う
(evpn_ops/sda_ops/um2_ops と同系の自己完結 ops)。全ノード CML コンソール経由
(pexpect・MGMTリース不使用)。alpine は root シェル。

使い方:
  python3 topologies/s2svpn_ops.py build    --problem GEN-S2SVPN-4126
  python3 topologies/s2svpn_ops.py solve    --problem GEN-S2SVPN-4126 [--mode svti|cmap]
  python3 topologies/s2svpn_ops.py grade    --problem GEN-S2SVPN-4126 [--report <report.yaml>]
  python3 topologies/s2svpn_ops.py teardown --problem GEN-S2SVPN-4126
  python3 topologies/s2svpn_ops.py exec     --problem ... --node HQ --exec "show ip route"
                                            [--config "..."] [--sh "..."]  (区切り ';;')
"""
import argparse
import json
import os
import re
import sys
import time

import pexpect
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

P_NET = r"(\r\n|\r|\n)([\w/-]+)(\([\w./-]+\))?([>#]) ?"
P_ALP = r"(\r\n|\r|\n)[\w-]+:[^\r\n]*[#$] ?"


def cml_creds():
    c = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    return c["cml_host"], c["cml_username"], c["cml_password"]


def cml_client():
    import urllib3
    urllib3.disable_warnings()
    from virl2_client import ClientLibrary
    host, user, pw = cml_creds()
    return ClientLibrary(f"https://{host}", user, pw, ssl_verify=False)


def load_params(problem):
    p = os.path.join(REPO, "problems", problem, "params.json")
    return json.load(open(p))


def find_lab(client, title):
    for lab in client.all_labs():
        if lab.title == title:
            return lab
    return None


# ----------------------------------------------------------------------------
# コンソールプール
# ----------------------------------------------------------------------------
class Console:
    def __init__(self, title, node, is_alpine):
        self.node = node
        self.is_alpine = is_alpine
        host, user, pw = cml_creds()
        c = pexpect.spawn(
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
            f"{user}@{host}",
            encoding="utf-8", codec_errors="replace", timeout=30)
        c.expect("assword:")
        c.sendline(pw)
        c.expect("consoles>")
        c.sendline(f"open /{title}/{node}/0")
        c.expect("Escape character")
        time.sleep(2)
        self.c = c
        self.prompt = P_ALP if is_alpine else P_NET
        self._login()

    def _login(self):
        c = self.c
        if self.is_alpine:
            c.send("\r")
            for _ in range(10):
                idx = c.expect([r"login:", r"assword:", P_ALP, pexpect.TIMEOUT],
                               timeout=12)
                if idx == 0:
                    c.send("root\r")
                elif idx == 1:
                    c.send("cisco\r")
                elif idx == 2:
                    return
                else:
                    c.send("\r")
            raise RuntimeError(f"{self.node}: alpine シェル不達")
        c.send("\r")
        for _ in range(15):
            idx = c.expect([P_NET, r"assword:", r"sername:",
                            r"initial configuration dialog", pexpect.TIMEOUT],
                           timeout=15)
            if idx == 0:
                if c.match.group(4) == "#":
                    self.run("terminal length 0", timeout=15)
                    return
                c.send("enable\r")
            elif idx == 1:
                c.send("CCNP\r")
            elif idx == 2:
                c.send("SUZUKI\r")
            elif idx == 3:
                c.send("no\r")
            else:
                c.send("\r")
        raise RuntimeError(f"{self.node}: priv exec 不達")

    def _drain(self):
        time.sleep(0.3)
        try:
            while True:
                self.c.read_nonblocking(size=4096, timeout=0.5)
        except Exception:
            pass

    def run(self, cmd, timeout=60):
        self._drain()
        self.c.send(cmd + "\r")
        out = []
        while True:
            idx = self.c.expect([self.prompt, r" --More-- ", pexpect.TIMEOUT],
                                timeout=timeout)
            out.append(self.c.before or "")
            if idx == 0:
                return "".join(out)
            if idx == 1:
                self.c.send(" ")
            else:
                return "".join(out)

    def config(self, lines, timeout=60):
        self.run("configure terminal", timeout)
        for ln in lines:
            if ln.strip():
                out = self.run(ln.rstrip(), timeout)
                if "%" in out or "Invalid" in out:
                    print(f"  [{self.node}] config 警告: {ln.strip()!r} → "
                          f"{[l for l in out.splitlines() if '%' in l or 'Invalid' in l][:2]}")
        self.run("end", timeout)

    def close(self):
        try:
            self.c.close(force=True)
        except Exception:
            pass


class Pool:
    def __init__(self, params):
        self.title = params["title"]
        self.alpine = set(params["alpine"])
        self.pool = {}

    def get(self, node):
        if node not in self.pool:
            self.pool[node] = Console(self.title, node, node in self.alpine)
        return self.pool[node]

    def close(self):
        for c in self.pool.values():
            c.close()


# ----------------------------------------------------------------------------
# build / status / teardown
# ----------------------------------------------------------------------------
def cmd_build(args, params):
    client = cml_client()
    lab = find_lab(client, params["title"])
    if lab is None:
        path = os.path.join(REPO, "problems", args.problem, "lab.yaml")
        lab = client.import_lab(open(path).read(), title=params["title"])
        print(f"imported: {lab.id}")
    lab.start(wait=True)
    for n in lab.nodes():
        print(f"  {n.label:6s} {n.state}")
    # コンソール到達確認(IOSv ブート待ちを吸収)
    pool = Pool(params)
    deadline = time.time() + 900
    routers = ["INET", "HQ", "BR1", "BR2"] + (["BR3", "BR4"] if "day2" in params else [])
    pending = routers + params["alpine"]
    while pending and time.time() < deadline:
        node = pending[0]
        try:
            pool.get(node)
            print(f"  console OK: {node}")
            pending.pop(0)
        except Exception:
            pool.pool.pop(node, None)
            time.sleep(20)
    pool.close()
    if pending:
        print(f"★コンソール未達: {pending}")
        sys.exit(1)
    print("build 完了(全コンソール到達)")


def cmd_status(args, params):
    client = cml_client()
    lab = find_lab(client, params["title"])
    if lab is None:
        print("ラボ未作成")
        return
    print(f"{lab.title}: {lab.state()}")
    for n in lab.nodes():
        print(f"  {n.label:6s} {n.state}")


def cmd_teardown(args, params):
    client = cml_client()
    lab = find_lab(client, params["title"])
    if lab is None:
        print("ラボ未作成")
        return
    lab.stop()
    lab.wipe()
    lab.remove()
    print(f"teardown 完了: {params['title']}")


def cmd_solve(args, params):
    path = os.path.join(REPO, "problems", args.problem, "solution",
                        f"solve_{args.mode}.json")
    if not os.path.exists(path):
        print(f"模範解答がありません: {path}")
        sys.exit(1)
    cfgs = json.load(open(path))
    pool = Pool(params)
    try:
        for node, lines in cfgs.items():
            print(f"== solve({args.mode}) → {node} ({len(lines)} 行)")
            pool.get(node).config(lines, timeout=90)
        print("solve 完了")
    finally:
        pool.close()


def cmd_exec(args, params):
    pool = Pool(params)
    try:
        con = pool.get(args.node)
        if args.config_lines:
            con.config(args.config_lines.replace("\\n", "\n").split("\n"))
        for blob in (args.exec_cmds, args.sh_cmds):
            if blob:
                for cmd in blob.split(";;"):
                    print(f"===== [{args.node}] {cmd.strip()} =====")
                    print(con.run(cmd.strip(), timeout=args.timeout))
    finally:
        pool.close()


# ----------------------------------------------------------------------------
# grade (逐次効果採点)
# ----------------------------------------------------------------------------
def parse_acl_counts(text):
    """show access-lists 出力 → {seq: matches}。matches 表記なしは 0。"""
    counts = {}
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(\d+)\s+(?:permit|deny)\b", line)
        if not m:
            continue
        hits = re.search(r"\((\d+) match", line)
        counts[int(m.group(1))] = int(hits.group(1)) if hits else 0
    return counts


def sum_encaps(text):
    return sum(int(m) for m in re.findall(r"#pkts encaps: (\d+)", text))


def received(text):
    m = re.search(r"(\d+) packets received", text)
    return int(m.group(1)) if m else -1


class Grader:
    def __init__(self, params, report_path):
        self.p = params
        self.report_path = report_path
        self.pool = Pool(params)
        self.results = []

    def add(self, name, points, ok, note=""):
        self.results.append({"name": name, "points": points, "ok": bool(ok),
                             "note": note})
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] (+{points:>3} 点) {name}" + (f"  ← {note}" if (note and not ok) else ""))

    def run(self):
        p = self.p
        ax = p["axes"]
        hosts = p["lan_hosts"]
        hqh, b1h, b2h = hosts["HQ"], hosts["BR1"], hosts["BR2"]
        srv = p["srv"]["ip"]
        edges = ["HQ", "BR1", "BR2"]
        inet = self.pool.get("INET")

        # ---- P0: クリア＆ベースライン ----
        print("-- P0: counters clear / encaps baseline")
        inet.run("clear access-list counters")
        base = {}
        for e in edges:
            con = self.pool.get(e)
            con.run("clear crypto sa counters")
            base[e] = sum_encaps(con.run("show crypto ipsec sa | include encaps"))

        # ---- ウォームアップ (SA/NAT セッション確立・採点前の温め) ----
        print("-- warmup")
        for node, dst in (("H-B1", hqh), ("H-B2", hqh), ("H-B1", b2h),
                          ("H-HQ", srv), ("H-B1", srv), ("H-B2", srv)):
            self.pool.get(node).run(f"ping -c 2 -W 2 {dst}", timeout=30)
        time.sleep(3)

        # ---- P1: 拠点間到達性 ----
        print("-- P1: reachability")
        reach_b1 = (received(self.pool.get("H-B1").run(f"ping -c 5 -W 2 {hqh}", 40)) >= 3
                    and received(self.pool.get("H-HQ").run(f"ping -c 5 -W 2 {b1h}", 40)) >= 3)
        self.add("本社⇔支店1: LAN 間相互疎通", 10, reach_b1)
        reach_b2 = (received(self.pool.get("H-B2").run(f"ping -c 5 -W 2 {hqh}", 40)) >= 3
                    and received(self.pool.get("H-HQ").run(f"ping -c 5 -W 2 {b2h}", 40)) >= 3)
        self.add("本社⇔支店2: LAN 間相互疎通", 10, reach_b2)
        # ★0点発射ガード: 負の要件(遮断)は「土台の疎通が立っている」時のみ得点
        #   (broken 状態で deny 系チェックが空振り合格しないための前提ゲート)
        gate_reach = reach_b1 and reach_b2

        # ---- P1b: 支店間ポリシー (正+負のセット採点) ----
        b2b = ax["b2b"]
        p12 = self.pool.get("H-B1").run(f"ping -c 5 -W 2 {b2h}", 40)
        p21 = self.pool.get("H-B2").run(f"ping -c 5 -W 2 {b1h}", 40)
        w12 = self.pool.get("H-B1").run(f"wget -qO- -T 5 http://{b2h}/", 30)
        w21 = self.pool.get("H-B2").run(f"wget -qO- -T 5 http://{b1h}/", 30)
        if b2b == "allow_all":
            ok = (received(p12) >= 3 and received(p21) >= 3
                  and "H-B2-OK" in w12 and "H-B1-OK" in w21)
            note = "全許可: ping/HTTP とも成立が必要"
        elif b2b == "deny_all":
            ok = (received(p12) == 0 and received(p21) == 0
                  and "H-B2-OK" not in w12 and "H-B1-OK" not in w21)
            note = "全遮断: ping/HTTP とも不達が必要"
        elif b2b == "icmp_only":
            ok = (received(p12) >= 3 and received(p21) >= 3
                  and "H-B2-OK" not in w12 and "H-B1-OK" not in w21)
            note = "ICMPのみ: ping成立＋HTTP遮断が必要"
        else:  # http_only
            ok = (received(p12) == 0 and received(p21) == 0
                  and "H-B2-OK" in w12 and "H-B1-OK" in w21)
            note = "HTTPのみ: HTTP成立＋ping遮断が必要"
        self.add(f"支店間ポリシー ({b2b})", 15, ok and gate_reach,
                 note + ("" if gate_reach else " / 前提の本社⇔支店疎通が未成立"))

        # ---- P2: NAPT 出口検証 (ホストごとに逐次) ----
        print("-- P2: NAPT egress attribution")
        judge_line = {"HQ": 10, "BR1": 20, "BR2": 30}
        expect_exit = {"HQ": "HQ",
                       "BR1": "HQ" if ax["tun"]["BR1"] == "full" else "BR1",
                       "BR2": "HQ" if ax["tun"]["BR2"] == "full" else "BR2"}
        host_of = {"HQ": "H-HQ", "BR1": "H-B1", "BR2": "H-B2"}
        napt_pass = []
        for site in ("HQ", "BR1", "BR2"):
            inet.run("clear access-list counters JUDGE-SRV")
            w = self.pool.get(host_of[site]).run(f"wget -qO- -T 5 http://{srv}/", 30)
            self.pool.get(host_of[site]).run(f"ping -c 3 -W 2 {srv}", 30)
            counts = parse_acl_counts(inet.run("show access-lists JUDGE-SRV"))
            exp = expect_exit[site]
            good = counts.get(judge_line[exp], 0) > 0
            others = [s for s in ("HQ", "BR1", "BR2") if s != exp]
            clean = all(counts.get(judge_line[o], 0) == 0 for o in others)
            content = "SRV-OK" in w
            pts = 5 if site == "HQ" else 10
            mode = ax["tun"].get(site, "-")
            napt_pass.append(content and good and clean)
            self.add(f"{site} 発インターネット: NAPT 出口={exp} 公開IP"
                     f"{'(full=本社集約)' if mode == 'full' else ''}",
                     pts, content and good and clean,
                     f"HTTP={'OK' if content else 'NG'} 期待線={counts.get(judge_line[exp], 0)} "
                     f"他線={[counts.get(judge_line[o], 0) for o in others]}")

        # ---- P3: 公開サーバ (軸C) ----
        if ax["pubsrv"]:
            w = self.pool.get("SRV").run(
                f"wget -qO- -T 5 http://{self.p['pub']['HQ']['rtr']}:8080/", 30)
            self.add("公開サーバ: INET→HQ公開IP:8080 で H-HQ に到達", 5, "H-HQ-OK" in w)

        # ---- P4: 大容量転送 (MTU/MSS 効果) ----
        print("-- P4: large transfer")
        t1 = self.pool.get("H-B1").run(
            f"wget -qO- -T 10 http://{hqh}/big.bin | wc -c", 60)
        t2 = self.pool.get("H-B2").run(
            f"wget -qO- -T 10 http://{srv}/big.bin | wc -c", 60)
        ok1 = re.search(rf"^{self.p['bigbin']}\s*$", t1, re.M) is not None
        ok2 = re.search(rf"^{self.p['bigbin']}\s*$", t2, re.M) is not None
        self.add("大容量転送: 支店1→本社 200KB / 支店2→INET 200KB", 10, ok1 and ok2,
                 f"tunnel={'OK' if ok1 else 'NG'} internet={'OK' if ok2 else 'NG'}")

        # ---- P5: 暗号化・漏えい・監査 ----
        print("-- P5: encryption / leak / audit")
        for e in edges:
            con = self.pool.get(e)
            delta = sum_encaps(con.run("show crypto ipsec sa | include encaps")) - base[e]
            self.add(f"{e}: IPsec encaps がテストトラフィックで増加", 3, delta >= 5,
                     f"delta={delta}")
        # ★0点発射ガード: 「漏れていない」「壊していない」系は、正の要件が
        #   一つも成立していない broken 状態では得点させない
        gate_any = gate_reach or any(napt_pass)
        leak = parse_acl_counts(inet.run("show access-lists CATCH-LEAK"))
        bad = {k: v for k, v in leak.items() if k <= 60 and v > 0}
        self.add("社内アドレスの平文流出なし (INET CATCH-LEAK = 0)", 6,
                 (not bad) and gate_any,
                 f"hits={bad}" + ("" if gate_any else " / 正の要件が未成立"))
        a1 = inet.run("show running-config interface Ethernet0/3 | include access-group")
        a2 = inet.run("show running-config | include ^ip route")
        tamper_free = ("JUDGE-SRV out" in a1
                       and not re.search(r"^ip route ", a2, re.M))
        self.add("INET 無改変 (採点 ACL 健在・静的経路の追加なし)", 5,
                 tamper_free and gate_any,
                 "" if gate_any else "正の要件が未成立")

        # ---- P6: 設計レポート ----
        rep_pts = 5 if ax["pubsrv"] else 10
        ok, note = False, "report.yaml 不在"
        if self.report_path and os.path.exists(self.report_path):
            try:
                rep = yaml.safe_load(open(self.report_path)) or {}
                ok = bool(str(rep.get("vpn_technology") or "").strip()) and \
                    bool(str(rep.get("reason") or "").strip())
                note = "" if ok else "vpn_technology / reason が未記載"
            except Exception as e:
                note = f"YAML 解析失敗: {e}"
        self.add("設計レポート report.yaml (方式と選定理由)", rep_pts, ok, note)

        # ---- 集計 ----
        got = sum(r["points"] for r in self.results if r["ok"])
        total = sum(r["points"] for r in self.results)
        print("=" * 70)
        print(f"  合計: {got} / {total} 点")
        print("=" * 70)
        return {"score": got, "total": total, "checks": self.results}


# ----------------------------------------------------------------------------
# Day2 (BL-064): チケット別採点
# ----------------------------------------------------------------------------
HOST_OF = {"HQ": "H-HQ", "BR1": "H-B1", "BR2": "H-B2", "BR3": "H-B3", "BR4": "H-B4"}


class Day2Grader(Grader):
    """チケット t1/t2/t3 の採点。base 稼働中が前提(build→solve base→day2init 済)。
    ★0点発射ガード: 回帰(既存網の無事)得点はチケット中核の成立時のみ。"""

    def __init__(self, params, ticket, report_path):
        super().__init__(params, report_path)
        self.ticket = ticket

    def expect_exit(self):
        ax = self.p["axes"]
        d2 = self.p["day2"]
        tun = dict(ax["tun"])
        if self.ticket in ("t2", "t3"):
            tun[d2["migrate_target"]] = "split"          # #2 完了後の期待
        exp = {"HQ": "HQ"}
        for br in ("BR1", "BR2"):
            exp[br] = "HQ" if tun[br] == "full" else br
        exp["BR3"] = "HQ" if d2["br3"]["policy"] == "full" else "BR3"
        if self.ticket == "t3":
            exp["BR4"] = "BR4"
        return exp

    def _reach(self, site_a, site_b):
        a, b = self.p["lan_hosts"][site_a], self.p["lan_hosts"][site_b]
        r1 = received(self.pool.get(HOST_OF[site_a]).run(f"ping -c 5 -W 2 {b}", 40))
        r2 = received(self.pool.get(HOST_OF[site_b]).run(f"ping -c 5 -W 2 {a}", 40))
        return r1 >= 3 and r2 >= 3

    def _napt(self, site, exp):
        inet = self.pool.get("INET")
        seq = self.p["judge_seq"]
        srv = self.p["srv"]["ip"]
        inet.run("clear access-list counters JUDGE-SRV")
        w = self.pool.get(HOST_OF[site]).run(f"wget -qO- -T 5 http://{srv}/", 30)
        self.pool.get(HOST_OF[site]).run(f"ping -c 3 -W 2 {srv}", 30)
        counts = parse_acl_counts(inet.run("show access-lists JUDGE-SRV"))
        good = counts.get(seq[exp], 0) > 0
        clean = all(counts.get(v, 0) == 0 for k, v in seq.items() if k != exp)
        return ("SRV-OK" in w) and good and clean, counts

    def _b2b(self):
        ax = self.p["axes"]
        b1h, b2h = self.p["lan_hosts"]["BR1"], self.p["lan_hosts"]["BR2"]
        p12 = received(self.pool.get("H-B1").run(f"ping -c 5 -W 2 {b2h}", 40))
        w12 = self.pool.get("H-B1").run(f"wget -qO- -T 5 http://{b2h}/", 30)
        b2b = ax["b2b"]
        if b2b == "allow_all":
            return p12 >= 3 and "H-B2-OK" in w12
        if b2b == "deny_all":
            return p12 == 0 and "H-B2-OK" not in w12
        if b2b == "icmp_only":
            return p12 >= 3 and "H-B2-OK" not in w12
        return p12 == 0 and "H-B2-OK" in w12          # http_only

    def _encaps_delta(self, node, base):
        con = self.pool.get(node)
        return sum_encaps(con.run("show crypto ipsec sa | include encaps")) - base

    def run_day2(self):
        p = self.p
        d2 = p["day2"]
        exp = self.expect_exit()
        hqh = p["lan_hosts"]["HQ"]
        inet = self.pool.get("INET")
        print(f"-- day2 grade: ticket {self.ticket} (expect_exit={exp})")
        inet.run("clear access-list counters")
        edges = {"t1": "BR3", "t2": d2["migrate_target"], "t3": "BR4"}[self.ticket]
        enc_base = sum_encaps(self.pool.get(edges).run(
            "show crypto ipsec sa | include encaps"))

        if self.ticket == "t1":
            tgt = "BR3"
            self.pool.get("H-B3").run(f"ping -c 2 -W 2 {hqh}", 30)  # warmup
            core1 = self._reach("BR3", "HQ")
            self.add("BR3⇔本社: LAN 間相互疎通", 15, core1)
            core2, cnt = self._napt("BR3", exp["BR3"])
            self.add(f"BR3 発インターネット: NAPT 出口={exp['BR3']}", 15, core2,
                     f"counts={cnt}")
            core = core1 and core2
            self.add("BR3: IPsec encaps 増加", 5,
                     self._encaps_delta("BR3", enc_base) >= 5)
            # 食い違い報告
            ok, note = False, "report_d2.yaml 不在"
            truth = d2["br3"]["disc"]
            if self.report_path and os.path.exists(self.report_path):
                try:
                    rep = yaml.safe_load(open(self.report_path)) or {}
                    items = rep.get("t1_discrepancies") or []
                    got = {str(i.get("item", "")).strip() for i in items}
                    vals_ok = all(
                        str(truth["truth"][i.get("item")]) in str(i.get("actual", ""))
                        for i in items if i.get("item") in truth["truth"])
                    ok = got == set(truth["items"]) and vals_ok
                    note = "" if ok else (f"期待項目={sorted(truth['items'])} "
                                          f"報告={sorted(got)} 値一致={vals_ok}")
                except Exception as e:
                    note = f"YAML 解析失敗: {e}"
            self.add("食い違い報告 (仕様書 vs 実機)", 20, ok, note)
        elif self.ticket == "t2":
            tgt = d2["migrate_target"]
            core2, cnt = self._napt(tgt, exp[tgt])
            self.add(f"{tgt} 発インターネット: 出口={exp[tgt]} 公開IP"
                     "(ローカルブレイクアウト化)", 30, core2, f"counts={cnt}")
            # ★維持系は移行(出口flip)成立時のみ得点(未着手 broken での先行加点を防ぐ)
            core1 = self._reach(tgt, "HQ")
            self.add(f"{tgt}⇔本社: LAN 間相互疎通の維持", 15, core1 and core2,
                     "" if core2 else "移行が未成立")
            core = core1 and core2
        else:  # t3
            tgt = "BR4"
            d4 = d2["br4"]
            alias_host = f"{d4['alias']}.{d4['host_oct']}"
            self.pool.get("H-B4").run(f"ping -c 2 -W 2 {hqh}", 30)  # warmup
            r1 = received(self.pool.get("H-B4").run(f"ping -c 5 -W 2 {hqh}", 40))
            w1 = self.pool.get("H-B4").run(f"wget -qO- -T 5 http://{hqh}/", 30)
            c1 = r1 >= 3 and "H-HQ-OK" in w1
            self.add("BR4→本社: 実アドレス宛の疎通 (ping+HTTP)", 15, c1)
            r2 = received(self.pool.get("H-HQ").run(
                f"ping -c 5 -W 2 {alias_host}", 40))
            self.add(f"本社→BR4: エイリアス({alias_host})宛の疎通", 10, r2 >= 3)
            c3, cnt = self._napt("BR4", "BR4")
            self.add("BR4 発インターネット: NAPT 出口=BR4 公開IP", 15, c3,
                     f"counts={cnt}")
            core = c1 and r2 >= 3 and c3
            leak = parse_acl_counts(inet.run("show access-lists CATCH-LEAK"))
            bad = {k: v for k, v in leak.items() if k <= 60 and v > 0}
            self.add("平文流出なし (CATCH-LEAK=0)", 10, (not bad) and core,
                     f"hits={bad}")
            # ★素朴設定でもトンネルは UP で encaps は増える → core 成立時のみ得点
            self.add("BR4: IPsec encaps 増加", 5,
                     core and self._encaps_delta("BR4", enc_base) >= 5)

        # ---- 回帰 (既存網の無事・core 成立時のみ得点) ----
        gate_note = "" if core else "チケット中核が未成立"
        regs = []
        if self.ticket == "t1":
            regs = [("本社⇔支店1 疎通維持", 10, lambda: self._reach("BR1", "HQ")),
                    ("本社⇔支店2 疎通維持", 10, lambda: self._reach("BR2", "HQ")),
                    (f"支店間ポリシー維持 ({p['axes']['b2b']})", 10, self._b2b),
                    ("HQ NAPT 維持", 5, lambda: self._napt("HQ", "HQ")[0]),
                    ("BR1 NAPT 維持", 5, lambda: self._napt("BR1", exp["BR1"])[0]),
                    ("BR2 NAPT 維持", 5, lambda: self._napt("BR2", exp["BR2"])[0])]
        elif self.ticket == "t2":
            other = "BR2" if tgt == "BR1" else "BR1"
            srv = p["srv"]["ip"]
            regs = [(f"本社⇔{other} 疎通維持", 10, lambda: self._reach(other, "HQ")),
                    (f"支店間ポリシー維持 ({p['axes']['b2b']})", 10, self._b2b),
                    ("HQ NAPT 維持", 5, lambda: self._napt("HQ", "HQ")[0]),
                    (f"{other} NAPT 維持", 10,
                     lambda: self._napt(other, exp[other])[0]),
                    ("BR3 NAPT 維持", 10, lambda: self._napt("BR3", exp["BR3"])[0]),
                    ("大容量転送維持 (支店1→本社/支店2→INET)", 10, lambda: (
                        re.search(rf"^{p['bigbin']}\s*$", self.pool.get("H-B1").run(
                            f"wget -qO- -T 10 http://{hqh}/big.bin | wc -c", 60),
                            re.M) is not None and
                        re.search(rf"^{p['bigbin']}\s*$", self.pool.get("H-B2").run(
                            f"wget -qO- -T 10 http://{srv}/big.bin | wc -c", 60),
                            re.M) is not None))]
        else:
            ovof = d2["br4"]["overlap_of"]
            regs = [(f"重複相手 {ovof} の NAPT 無影響", 10,
                     lambda: self._napt(ovof, exp[ovof])[0]),
                    ("本社⇔支店1 疎通維持", 5, lambda: self._reach("BR1", "HQ")),
                    ("本社⇔支店2 疎通維持", 5, lambda: self._reach("BR2", "HQ")),
                    (f"支店間ポリシー維持 ({p['axes']['b2b']})", 10, self._b2b),
                    ("BR3 NAPT 維持", 10, lambda: self._napt("BR3", exp["BR3"])[0]),
                    ("HQ NAPT 維持", 5, lambda: self._napt("HQ", "HQ")[0])]
        for name, pts, fn in regs:
            ok = fn() if core else False
            self.add(f"[回帰] {name}", pts, ok, gate_note if not core else "")

        got = sum(r["points"] for r in self.results if r["ok"])
        total = sum(r["points"] for r in self.results)
        print("=" * 70)
        print(f"  合計 (ticket {self.ticket}): {got} / {total} 点")
        print("=" * 70)
        return {"ticket": self.ticket, "score": got, "total": total,
                "checks": self.results}


def cmd_day2init(args, params):
    path = os.path.join(REPO, "problems", args.problem, "solution", "day2init.json")
    cfgs = json.load(open(path))
    pool = Pool(params)
    try:
        for node, lines in cfgs.items():
            print(f"== day2init → {node} ({len(lines)} 行)")
            pool.get(node).config(lines, timeout=90)
        print("day2init 完了(吸収拠点担当の素朴設定を HQ に投入済み)")
    finally:
        pool.close()


def cmd_grade(args, params):
    if args.ticket:
        if "day2" not in params:
            print("--ticket は Day2 パック専用です")
            sys.exit(1)
        report = args.report or os.path.join(REPO, "lab", params["id"],
                                             "report_d2.yaml")
        g = Day2Grader(params, args.ticket, report)
        try:
            res = g.run_day2()
        finally:
            g.pool.close()
    else:
        report = args.report or os.path.join(REPO, "lab", params["id"], "report.yaml")
        g = Grader(params, report)
        try:
            res = g.run()
        finally:
            g.pool.close()
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "status", "solve", "grade",
                                    "teardown", "exec", "day2init"])
    ap.add_argument("--problem", required=True)
    ap.add_argument("--mode", default="svti")
    ap.add_argument("--ticket", choices=["t1", "t2", "t3"], default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--node")
    ap.add_argument("--exec", dest="exec_cmds")
    ap.add_argument("--config", dest="config_lines")
    ap.add_argument("--sh", dest="sh_cmds")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    params = load_params(args.problem)
    {"build": cmd_build, "status": cmd_status, "solve": cmd_solve,
     "grade": cmd_grade, "teardown": cmd_teardown, "exec": cmd_exec,
     "day2init": cmd_day2init}[args.cmd](args, params)


if __name__ == "__main__":
    main()
