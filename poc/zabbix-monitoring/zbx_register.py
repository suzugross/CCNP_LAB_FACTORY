#!/usr/bin/env python3
"""Zabbix API で RT01 を SNMPv3 ホスト登録する PoC。
将来は mgmt_map.yml / problem.yml から対象を流し込む想定（コントローラ側から実行）。
usage: zbx_register.py <zabbix_url>   (例 http://10.1.10.20:8080)"""
import json
import sys
import urllib.request

URL = sys.argv[1].rstrip("/") + "/api_jsonrpc.php"
_id = [0]


def rpc(method, params, token=None):
    _id[0] += 1
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": _id[0]}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json-rpc"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if "error" in r:
        raise SystemExit(f"API error {method}: {r['error']}")
    return r["result"]


tok = rpc("user.login", {"username": "Admin", "password": "zabbix"})
print("login OK")

# ホストグループ
gs = rpc("hostgroup.get", {"filter": {"name": ["CCNP-LAB"]}}, tok)
gid = gs[0]["groupid"] if gs else rpc("hostgroup.create", {"name": "CCNP-LAB"}, tok)["groupids"][0]

# テンプレート (Cisco IOS by SNMP は ICMP ping 監視も内包するので単独でよい)
tpl = rpc("template.get", {"filter": {"host": ["Cisco IOS by SNMP"]}}, tok)
tpl_ids = [{"templateid": t["templateid"]} for t in tpl]
print("templates:", [t["host"] for t in tpl])

# RT01 登録 (SNMPv3 authPriv SHA/AES128, in-band 10.99.0.1)
existing = rpc("host.get", {"filter": {"host": ["RT01"]}}, tok)
if existing:
    print("RT01 already registered:", existing[0]["hostid"])
else:
    h = rpc("host.create", {
        "host": "RT01",
        "groups": [{"groupid": gid}],
        "templates": tpl_ids,
        "interfaces": [{
            "type": 2, "main": 1, "useip": 1,
            "ip": "10.99.0.1", "dns": "", "port": "161",
            "details": {
                "version": 3, "bulk": 1,
                "securityname": "POCUSER",
                "securitylevel": 2,
                "authprotocol": 1,
                "authpassphrase": "AuthPass123",
                "privprotocol": 1,
                "privpassphrase": "PrivPass123",
                "contextname": "",
            },
        }],
    }, tok)
    print("RT01 created:", h["hostids"])
