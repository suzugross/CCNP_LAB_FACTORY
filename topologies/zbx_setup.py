#!/usr/bin/env python3
"""problem.yml の monitoring セクションに従い、Zabbix に監視ホストを登録する。

lab_up.yml から呼ばれる（monitoring がある問題のみ）。冪等：登録済みホストは
スキップ。Zabbix API が応答するまで（cloud-init での自動構築完了まで）待つ。

problem.yml 例:
  monitoring:
    server: ZBX01            # 監視サーバのノード名（mgmt_map で IP 解決）
    web_port: 8080
    group: CCNP-LAB
    hosts:
      - host: RT01
        ip: 1.1.1.1          # ポーリング先（インバンド推奨: 経路障害も監視断として見える）
        snmpv3: {user: MONUSER, auth_protocol: SHA, auth_pass: X, priv_protocol: AES, priv_pass: Y}
        templates: [Cisco IOS by SNMP]

usage: zbx_setup.py --problem-yml <path> --mgmt-map <path> [--wait 600]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

import yaml

AUTH_PROTO = {"MD5": 0, "SHA": 1, "SHA224": 2, "SHA256": 3, "SHA384": 4, "SHA512": 5}
PRIV_PROTO = {"DES": 0, "AES": 1, "AES128": 1, "AES192": 2, "AES256": 3}
_id = [0]


def rpc(url, method, params, token=None):
    _id[0] += 1
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": _id[0]}
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json-rpc"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    # 構築直後の API は応答が遅くタイムアウトしがち→一過性エラーはリトライ
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=45))
            break
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
            time.sleep(10)
    if "error" in r:
        raise RuntimeError(f"{method}: {r['error']}")
    return r["result"]


def wait_api(url, deadline):
    """Zabbix が使える状態になるまで待つ。
    ★frontend はスキーマ投入完了前から apiinfo.version に応答するため、
    ログイン＋テンプレートが読める（=スキーマ・初期データ投入済み）まで見る。"""
    tok = None
    while True:
        try:
            rpc(url, "apiinfo.version", {})
            tok = rpc(url, "user.login",
                      {"username": "Admin", "password": "zabbix"})
            tpl = rpc(url, "template.get",
                      {"filter": {"host": ["Cisco IOS by SNMP"]}, "limit": 1}, tok)
            if tpl:
                return tok
            reason = "テンプレート未投入"
        except (urllib.error.URLError, RuntimeError, OSError) as e:
            reason = f"{e.__class__.__name__}"
        if time.time() > deadline:
            sys.exit(f"Zabbix API 待ちタイムアウト: {reason}")
        print(f"  ... Zabbix API 待ち ({reason})", flush=True)
        time.sleep(15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem-yml", required=True)
    ap.add_argument("--mgmt-map", required=True)
    ap.add_argument("--wait", type=int, default=600)
    ap.add_argument("--monitoring-yml",
                    help="monitoring セクションを problem.yml でなくこのファイルから読む"
                         "（build 問題の模範解答 solution/monitoring.yml 投入用）")
    a = ap.parse_args()

    if a.monitoring_yml:
        doc = yaml.safe_load(open(a.monitoring_yml, encoding="utf-8"))
        mon = doc.get("monitoring", doc)
    else:
        pmeta = yaml.safe_load(open(a.problem_yml, encoding="utf-8"))
        mon = pmeta.get("monitoring")
    if not mon:
        print("monitoring セクション無し: 何もしない")
        return
    mgmt_map = yaml.safe_load(open(a.mgmt_map, encoding="utf-8"))
    server_ip = mgmt_map[mon["server"]]
    url = f"http://{server_ip}:{mon.get('web_port', 8080)}/api_jsonrpc.php"

    print(f"Zabbix API: {url}")
    tok = wait_api(url, time.time() + a.wait)

    gname = mon.get("group", "CCNP-LAB")
    gs = rpc(url, "hostgroup.get", {"filter": {"name": [gname]}}, tok)
    gid = gs[0]["groupid"] if gs else \
        rpc(url, "hostgroup.create", {"name": gname}, tok)["groupids"][0]

    for h in mon["hosts"]:
        if rpc(url, "host.get", {"filter": {"host": [h["host"]]}}, tok):
            print(f"  {h['host']}: 登録済み(スキップ)")
            continue
        tpl_names = h.get("templates", ["Cisco IOS by SNMP"])
        tpls = rpc(url, "template.get", {"filter": {"host": tpl_names}}, tok)
        if len(tpls) != len(tpl_names):
            sys.exit(f"テンプレート未解決: {tpl_names} -> {[t['host'] for t in tpls]}")
        v3 = h["snmpv3"]
        _host_create(url, tok, h, gid, tpls, v3, tpl_names)
        print(f"  {h['host']}: 登録 (poll {h['ip']}, templates={tpl_names})")
    print("Zabbix 監視登録 完了")


def _host_create(url, tok, h, gid, tpls, v3, tpl_names):
    """host.create。構築直後は 'Database error occurred' が出うるのでリトライ。"""
    for attempt in range(6):
        try:
            return rpc(url, "host.create", _host_params(h, gid, tpls, v3), tok)
        except RuntimeError as e:
            # 'Database error' 応答でも行が入っていることがある→リトライで
            # 'already exists' になったら成功扱い（冪等）。
            if "already exists" in str(e):
                print(f"  ... {h['host']}: 既に存在(前回試行で作成済み)", flush=True)
                return None
            if "Database error" not in str(e) or attempt == 5:
                raise
            print(f"  ... {h['host']}: DBウォームアップ待ちリトライ", flush=True)
            time.sleep(15)


def _host_params(h, gid, tpls, v3):
    return {
            "host": h["host"],
            "groups": [{"groupid": gid}],
            "templates": [{"templateid": t["templateid"]} for t in tpls],
            "interfaces": [{
                "type": 2, "main": 1, "useip": 1,
                "ip": h["ip"], "dns": "", "port": "161",
                "details": {
                    "version": 3, "bulk": 1,
                    "securityname": v3["user"],
                    "securitylevel": 2,  # authPriv 固定（問題側の要求水準）
                    "authprotocol": AUTH_PROTO[v3.get("auth_protocol", "SHA").upper()],
                    "authpassphrase": v3["auth_pass"],
                    "privprotocol": PRIV_PROTO[v3.get("priv_protocol", "AES").upper()],
                    "privpassphrase": v3["priv_pass"],
                    "contextname": "",
                },
            }],
        }


if __name__ == "__main__":
    main()
