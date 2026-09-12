import sys, hashlib, yaml, pexpect
from virl2_client import ClientLibrary
prob=sys.argv[1]; title="CCNP-LAB-"+hashlib.md5(prob.encode()).hexdigest()[:8]
c=yaml.safe_load(open("group_vars/all/local.yml"))
cl=ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"], ssl_verify=False)
lab=next(l for l in cl.all_labs() if l.title==title)
for n in lab.nodes():
    if n.node_definition in ("external_connector","unmanaged_switch"): continue
    key=n.get_console_key() if hasattr(n,"get_console_key") else None
    # CML console via ssh to the terminal server: ssh -p 22 <cmluser>@host  then 'open /<lab>/<node>/0'
    s=pexpect.spawn(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {c['cml_username']}@{c['cml_host']}", timeout=25, encoding="utf-8", codec_errors="replace")
    try:
        s.expect("[Pp]assword:"); s.sendline(c["cml_password"]); s.expect(r"[>#$] ?$")
        s.sendline(f"open /{lab.title}/{n.label}/0"); s.expect("Escape character", timeout=15)
        import time; time.sleep(2); s.send("\r"); time.sleep(1); s.send("\r")
        try: s.expect(r"[\r\n]([A-Za-z0-9_\-]+(?:\([\w-]+\))?[>#])", timeout=15); prompt=s.match.group(1); tail=s.before[-120:]
        except pexpect.TIMEOUT: prompt="(no prompt)"; tail=(s.before or "")[-400:]
        if prompt!="(no prompt)":
            s.send("show users\r"); s.expect(r"[\r\n][A-Za-z0-9_\-]+[>#]", timeout=10); tail=s.before[-300:]
        print(f"[{n.label}] prompt={prompt!r} tail={tail!r}")
    except Exception as e:
        print(f"[{n.label}] ERROR {e}")
    finally:
        s.close(force=True)
