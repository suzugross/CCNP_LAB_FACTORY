#!/usr/bin/env python3
"""STEP 2: STEP1 と同じ GET を Python requests で行い、JSON を加工して表にする。

curl は「見る」には便利だが、結果を加工するなら Python。
requests.get() が返す JSON は resp.json() で dict になる。
"""
import requests
import urllib3

urllib3.disable_warnings()  # ラボの自己署名証明書の警告を抑止

RT01 = "10.1.10.11"
AUTH = ("SUZUKI", "CCNP")
HEADERS = {"Accept": "application/yang-data+json"}

url = f"https://{RT01}/restconf/data/ietf-interfaces:interfaces"
resp = requests.get(url, auth=AUTH, headers=HEADERS, verify=False)
resp.raise_for_status()

data = resp.json()
for intf in data["ietf-interfaces:interfaces"]["interface"]:
    ip = ""
    addrs = intf.get("ietf-ip:ipv4", {}).get("address", [])
    if addrs:
        ip = f'{addrs[0]["ip"]} {addrs[0]["netmask"]}'
    print(f'{intf["name"]:20} enabled={str(intf["enabled"]):5} {ip}  {intf.get("description", "")}')
