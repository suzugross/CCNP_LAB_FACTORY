#!/usr/bin/env python3
"""STEP 3: RESTCONF の PUT で Loopback100 を「作る」（初めての書き込み）。

PUT = URL が指すリソースを payload の内容で丸ごと作成/置換する。
URL 末尾の interface=Loopback100 が対象リソース（リストのキー指定）。
書き込みには Content-Type ヘッダが必須（サーバに payload の形式を伝える）。
"""
import requests
import urllib3

urllib3.disable_warnings()

RT01 = "10.1.10.11"
AUTH = ("SUZUKI", "CCNP")
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

url = f"https://{RT01}/restconf/data/ietf-interfaces:interfaces/interface=Loopback100"

payload = {
    "ietf-interfaces:interface": {
        "name": "Loopback100",
        "type": "iana-if-type:softwareLoopback",
        "description": "CONFIGURED-BY-RESTCONF",
        "enabled": True,
        "ietf-ip:ipv4": {
            "address": [
                {"ip": "172.16.100.1", "netmask": "255.255.255.255"}
            ]
        },
    }
}

resp = requests.put(url, auth=AUTH, headers=HEADERS, json=payload, verify=False)
print(f"HTTP {resp.status_code}  (201=新規作成 / 204=既存を更新)")
resp.raise_for_status()
