#!/usr/bin/env python3
"""PoC(SRV01 の上で動かす): NETCONF で XR を調べる。usage: nc_probe.py <host> <user> <pass> <段…>
段= caps(hello の能力の要約)・getcfg(running の Loopback0)・edit(candidate に説明を入れて commit)・
    confirmed(confirmed-commit を出して確定しない)・lock(candidate を lock したまま待つ 秒)・oper(IF の oper の一部)"""
import sys
import time

from ncclient import manager

host, user, pw, *steps = sys.argv[1:]
m = manager.connect(host=host, port=830, username=user, password=pw, hostkey_verify=False,
                    allow_agent=False, look_for_keys=False, timeout=60, device_params={"name": "iosxr"})
print(f"== session-id {m.session_id}")

UM_IF = """<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg">
 <interface><interface-name>Loopback0</interface-name></interface></interfaces>"""


def caps():
    cs = list(m.server_capabilities)
    base = [c for c in cs if c.startswith("urn:ietf:params:netconf")]
    print(f"capabilities: {len(cs)}")
    for c in base:
        print("  " + c)
    mods = [c.split("?")[0] for c in cs if "module=" in c or c.startswith("http")]
    for key in ("Cisco-IOS-XR-um-", "Cisco-IOS-XR-", "openconfig-", "ietf-"):
        n = [c for c in mods if key in c]
        print(f"  {key}*: {len(n)}")
    for want in ("Cisco-IOS-XR-um-interface-cfg", "Cisco-IOS-XR-ifmgr-cfg", "Cisco-IOS-XR-ifmgr-oper",
                 "openconfig-interfaces", "Cisco-IOS-XR-telemetry-model-driven-cfg", "Cisco-IOS-XR-um-telemetry-model-driven-cfg",
                 "ietf-netconf-monitoring", "ietf-restconf", "Cisco-IOS-XR-man-netconf-cfg", "Cisco-IOS-XR-um-netconf-yang-cfg"):
        hit = [c for c in cs if f"/{want}?" in c or f"module={want}&" in c or c.endswith(f"/{want}")]
        print(f"  has {want}: {bool(hit)}")


def getcfg():
    r = m.get_config(source="running", filter=("subtree", UM_IF))
    print(r.xml[:2000])


def edit():
    cfg = f"""<config><interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg">
 <interface><interface-name>Loopback0</interface-name><description>set-by-netconf {time.strftime('%H%M%S')}</description></interface>
</interfaces></config>"""
    print(m.edit_config(target="candidate", config=cfg).xml[:500])
    print(m.commit().xml[:500])


def confirmed():
    cfg = """<config><interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg">
 <interface><interface-name>Loopback0</interface-name><description>confirmed-test</description></interface>
</interfaces></config>"""
    m.edit_config(target="candidate", config=cfg)
    print(m.commit(confirmed=True, timeout="60").xml[:500])
    print("confirmed-commit を出した(確定しない)。60 秒で戻るはず")


def lock(sec="30"):
    with m.locked("candidate"):
        print(f"candidate を lock した。{sec} 秒待つ")
        time.sleep(int(sec))


def oper():
    flt = """<interfaces xmlns="http://openconfig.net/yang/interfaces"><interface><name>Loopback0</name><state/></interface></interfaces>"""
    try:
        print(m.get(filter=("subtree", flt)).xml[:1500])
    except Exception as e:
        print(f"openconfig get failed: {e}")


for s in steps:
    name, *a = s.split("=")
    print(f"---- {name}")
    try:
        globals()[name](*a)
    except Exception as e:
        print(f"!! {name}: {type(e).__name__}: {e}")
m.close_session()
