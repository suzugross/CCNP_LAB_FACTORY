#!/usr/bin/env python3
"""ラボ一括 start 後に BOOTED になっていないノードを個別 start するフォロー。

CML 2.8 で lab start 時に ubuntu 等のノードが DEFINED_ON_CORE のまま
取り残されることがある（2026-07-03 PoC で実証）ための保険。
全ノードが BOOTED になるまで待つ（--timeout 秒）。

usage: cml_fix_stragglers.py --host 10.1.10.10 --user U --password P \
         --lab-title CCNP-LAB-xxxxxxxx [--timeout 300]
認証情報は引数の代わりに環境変数 CML_USER / CML_PASSWORD でも渡せる。
"""
import argparse
import json
import os
import ssl
import sys
import time
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def api(base, method, path, token=None, body=None):
    req = urllib.request.Request(f"{base}{path}", method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data, timeout=30, context=CTX) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--user", default=os.environ.get("CML_USER"))
    ap.add_argument("--password", default=os.environ.get("CML_PASSWORD"))
    ap.add_argument("--lab-title", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    base = f"https://{a.host}/api/v0"
    tok = api(base, "POST", "/authenticate",
              body={"username": a.user, "password": a.password})
    lab_id = None
    for lid in api(base, "GET", "/labs", tok):
        if api(base, "GET", f"/labs/{lid}", tok)["lab_title"] == a.lab_title:
            lab_id = lid
            break
    if not lab_id:
        sys.exit(f"lab not found: {a.lab_title}")

    deadline = time.time() + a.timeout
    kicked = set()
    while True:
        nodes = api(base, "GET", f"/labs/{lab_id}/nodes?data=true", tok)
        # unmanaged_switch / external_connector も BOOTED になるので全ノード一律で見る
        waiting = [n for n in nodes if n["state"] != "BOOTED"]
        if not waiting:
            print(f"all {len(nodes)} nodes BOOTED")
            return
        for n in waiting:
            if n["state"] in ("DEFINED_ON_CORE", "STOPPED") and n["id"] not in kicked:
                print(f"kick start: {n['label']} ({n['state']})")
                api(base, "PUT", f"/labs/{lab_id}/nodes/{n['id']}/state/start", tok)
                kicked.add(n["id"])
        if time.time() > deadline:
            sys.exit("timeout waiting nodes: "
                     + ", ".join(f"{n['label']}={n['state']}" for n in waiting))
        time.sleep(10)


if __name__ == "__main__":
    main()
