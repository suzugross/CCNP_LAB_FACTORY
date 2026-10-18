#!/usr/bin/env python3
"""ラボのノードを「機器交換」する(BL-249)。

使い方(直接は呼ばない): scripts/lab.sh rma <問題ID> <ノード名>
  ↳ playbooks/lab_rma.yml が CML と機器の認証情報を環境変数で渡して、このスクリプトを呼ぶ。

手順(本物の交換と同じく「保存してあった設定だけが新しい機体に戻る」):
  1. 対象ノードの startup-config をコンソールで退避する(保存が無ければ、出題開始時の初期構成を使う)。
  2. 停止 → 初期化(wipe) → 1 番目のポートの MAC を差し替える。
     ★CML は起動中・停止しただけのノードの MAC を変えられない(物理構成のロック)。初期化後なら変えられる(2026-10-15 実測)。
     新しい MAC の 4 バイト目は、同じラボの他ノードと重ならない値にする(IOSvL2 は PAgP の装置 ID をここから作る)。
  3. 退避した設定を初期構成として起動する。初期化で VLAN データベース(vlan.dat)も消えるので、
     startup-config に無い VLAN(VTP サーバ/クライアントで作ったもの)は戻らない= 本物の交換と同じ。
  4. 交換の記録を topologies/_generated/<問題ID>/rma.log に追記し、mac_plan.json の MAC を更新する。
"""
import datetime, json, os, random, re, sys, time, warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from virl2_client import ClientLibrary  # noqa: E402
from pyats.topology import loader  # noqa: E402
from collect_console import _patch_testbed, restore_console  # noqa: E402

E = os.environ


def log(msg):
    print(f"[rma] {msg}", flush=True)


def startup_config(tb, name):
    """startup-config の本文を返す。保存が無ければ None。"""
    d = tb.devices[name]
    d.connect(via="a", log_stdout=False, connection_timeout=120, learn_hostname=True)
    try:
        out = d.execute("show startup-config", timeout=120, error_pattern=[]).replace("\r", "")
    finally:
        try:
            restore_console(d)
            d.disconnect()
        except Exception:
            pass
    if "not present" in out or "startup-config is not" in out:
        return None
    lines = out.split("\n")
    i = next((k for k, l in enumerate(lines) if l.startswith(("version ", "!"))), 0)
    body = "\n".join(lines[i:]).strip()
    return body + "\n" if body else None


def wait_state(lab, node, want, limit=900):
    t = time.time()
    while time.time() - t < limit:
        lab.sync_states()
        if node.state == want:
            return time.time() - t
        time.sleep(10)
    raise RuntimeError(f"{node.label} が {want} にならない(現在 {node.state})")


def main():
    repo, prob, name = E["REPO"], E["PROBLEM"], E["NODE"]
    gen = os.path.join(repo, "topologies", "_generated", prob)
    host = E["CML_HOST"] if E["CML_HOST"].startswith("http") else "https://" + E["CML_HOST"]
    c = ClientLibrary(host, E["CML_USER"], E["CML_PASS"], ssl_verify=False)
    labs = c.find_labs_by_title(E["LAB_TITLE"])
    if not labs:
        sys.exit(f"ラボが見つからない: {E['LAB_TITLE']}")
    lab = labs[0]
    node = next((n for n in lab.nodes() if n.label == name), None)
    if node is None:
        sys.exit(f"ノードが見つからない: {name}")

    # 1. 保存してあった設定を退避
    tb = loader.load(_patch_testbed(lab.get_pyats_testbed(), E["CML_USER"], E["CML_PASS"],
                                    E["NODE_USER"], E["NODE_PASS"], E.get("NODE_ENABLE", E["NODE_PASS"])))
    cfg = startup_config(tb, name)
    if cfg is None:
        day0 = os.path.join(gen, "day0", f"{name}.cfg")
        cfg = open(day0, encoding="utf-8").read()
        log(f"{name} に保存された設定が無い → 出題開始時の初期構成で交換機を起動する")
    else:
        log(f"{name} の startup-config を退避した({len(cfg.splitlines())} 行)")

    # 2. 停止 → 初期化 → MAC の差し替え
    used = set()
    for n in lab.nodes():
        if n.id == node.id:
            continue
        for i in n.interfaces():
            if i.mac_address:
                used.add(i.mac_address.split(":")[3])
    iface = next((i for i in node.interfaces() if getattr(i, "slot", None) == 0), None)
    if iface is None:
        sys.exit(f"{name} に 1 番目のポートの定義が無い(problem.yml の lab.mac_random / lab.macs を確認)")
    old = iface.mac_address
    rng = random.Random()
    b4 = rng.choice([f"{x:02x}" for x in range(0x10, 0xF0) if f"{x:02x}" not in used and (old is None or f"{x:02x}" != old.split(":")[3])])
    new = f"52:54:00:{b4}:{rng.randrange(256):02x}:{rng.randrange(256):02x}"
    log(f"{name} を停止・初期化する(コンソールは切れる)")
    node.stop(wait=True)
    node.wipe(wait=True)
    iface.mac_address = new
    node.configuration = cfg
    log(f"MAC を差し替えた: {old} → {new}")

    # 3. 起動
    node.start(wait=False)
    sec = wait_state(lab, node, "BOOTED")
    log(f"{name} の交換機が起動した({sec:.0f} 秒)")

    # 4. 記録
    os.makedirs(gen, exist_ok=True)
    with open(os.path.join(gen, "rma.log"), "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {name} {old} -> {new} "
                 f"config={'startup' if not cfg.startswith('!') or 'hostname' in cfg else 'day0'}\n")
    mp = os.path.join(gen, "mac_plan.json")
    if os.path.exists(mp):
        plan = json.load(open(mp, encoding="utf-8"))
        plan.setdefault("macs", {})[name] = new
        plan.setdefault("rma", []).append({"node": name, "old": old, "new": new})
        json.dump(plan, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
