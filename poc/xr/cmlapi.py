"""PoC 用の CML REST 小道具(BL-246)。from cmlapi import api, lab_id, node_id"""
import hashlib, json, ssl, urllib.request, urllib.error, yaml
_c = yaml.safe_load(open("group_vars/all/local.yml"))
_b = f"https://{_c['cml_host']}/api/v0"
_x = ssl.create_default_context(); _x.check_hostname = False; _x.verify_mode = ssl.CERT_NONE
_t = None
def api(m, p, body=None):
    global _t
    if _t is None and p != "/authenticate":
        _t = api("POST", "/authenticate", {"username": _c["cml_username"], "password": _c["cml_password"]})
    r = urllib.request.Request(_b + p, method=m); r.add_header("Content-Type", "application/json")
    if _t: r.add_header("Authorization", f"Bearer {_t}")
    d = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, d, timeout=60, context=_x) as x: raw = x.read()
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode()[:600]}
    try: return json.loads(raw)
    except Exception: return raw.decode()
def lab_id(problem):
    t = "CCNP-LAB-" + hashlib.md5(problem.encode()).hexdigest()[:8]
    return next(l for l in api("GET", "/labs") if api("GET", f"/labs/{l}")["lab_title"] == t)
def node_id(lid, label):
    return next(n["id"] for n in api("GET", f"/labs/{lid}/nodes?data=true") if n["label"] == label)
