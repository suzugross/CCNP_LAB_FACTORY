#!/usr/bin/env python3
"""CML 2.x ラボ(topology YAML, version 0.3.0)を組み立てる。

Vault やテンプレート描画は Ansible 側で済ませ（day0 config を --day0-dir に出力済み）、
本スクリプトは平文の問題定義/変数を読んで構造を組み立てるだけに専念する。

読むもの:
  problems/<problem>/problem.yml   … target_nodes, lab.links
  group_vars/all/main.yml          … device_profiles（平文）
  <day0-dir>/<node>.cfg            … Ansible が描画した day0 config

ノードの role は名前接頭辞で判定（SW*→switch, それ以外→router）。
イメージは既定 --image-family で統一（family 内で role 別のイメージを使う）。
problem.yml に `node_image_families: {SW01: iosv, RT01: iol, ...}` があれば
**ノード単位でイメージを上書き**できる（例: VACL用に SW01 だけ iosvl2、RT は軽量 iol-xe）。
"""
import argparse
import hashlib
import json
import math
import random
import os
import yaml

from mgmt_alloc import lease_description  # 同ディレクトリ(リース情報の埋め込み用)


def lab_title(problem):
    """CML に表示するラボ名。問題ID(技術名を含む)を md5 で不透明化し、
    受験者に解法がバレないようにする。lab_up.yml の lab_name と一致させること
    (= 'CCNP-LAB-' + md5(problem)[:8])。problem ID 自体は内部管理用に温存。"""
    h = hashlib.md5(problem.encode()).hexdigest()[:8]
    return f"CCNP-LAB-{h}"


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def role_of(name):
    n = name.upper()
    if n.startswith("SW"):
        return "switch"
    if n.startswith("ZBX") or n.startswith("SRV") or n.startswith("PC"):
        return "server"   # PC* はクライアント端末（実体は ubuntu＝server 扱い）
    return "router"


def iface(node, slot, label, itype="physical"):
    o = {"id": f"{node}-i{slot}", "label": label, "type": itype}
    if itype == "physical":
        o["slot"] = slot
    return o


def layout(nodes_in, positions, data_links):
    """ノード座標を決める。problem.yml の lab.positions({node:[x,y]}) を最優先。
    無いノードは fallback: 3台以下=横一列 / **連結グラフ(木でも閉路ありでも)=BFS階層
    レイアウト**(直径端点を根に左→右へ層・層内はバリセンタ順で交差低減=役割ベースの
    横流れ配置) / 非連結のみ円形。※座標は純粋な見た目で、出題内容には一切影響しない。"""
    coords = {}
    rest = [n for n in nodes_in if n not in positions]
    for n, xy in positions.items():
        if n in nodes_in:
            coords[n] = (int(xy[0]), int(xy[1]))
    if not rest:
        return coords
    adj = {n: [] for n in rest}
    for lk in data_links:
        if lk["a"] in adj and lk["b"] in adj:
            adj[lk["a"]].append(lk["b"]); adj[lk["b"]].append(lk["a"])
    if len(rest) <= 3:
        x = -350
        for n in rest:
            coords[n] = (x, -200); x += 220
        return coords

    # --- BFS 階層レイアウト（木/閉路を問わず連結グラフに適用） ---
    def bfs_layers(start):
        seen, cur, layers = {start}, [start], []
        while cur:
            layers.append(cur)
            nxt = []
            for u in cur:
                for v in adj[u]:
                    if v not in seen:
                        seen.add(v); nxt.append(v)
            cur = nxt
        return layers, seen

    def farthest(start):
        layers, _ = bfs_layers(start)
        return layers[-1][0] if layers else start

    root = farthest(farthest(rest[0]))       # 直径の端点(周辺ノード)を根に
    layers, seen = bfs_layers(root)
    if len(seen) != len(rest):
        # 非連結: 従来どおり円形フォールバック
        r = max(260, int(110 * len(rest) / math.pi))
        for i, n in enumerate(rest):
            th = 2 * math.pi * i / len(rest) - math.pi / 2
            coords[n] = (int(r * math.cos(th)), int(r * math.sin(th)) - 120)
        return coords

    # 左→右へ層を並べ、層内は「前層で確定した隣接ノードの y 重心」順に並べて交差を減らす。
    DX, DY, CY = 240, 170, -120
    yset = {}
    for li, layer in enumerate(layers):
        if li == 0:
            order = layer
        else:
            def bary(n):
                ys = [yset[v] for v in adj[n] if v in yset]
                return sum(ys) / len(ys) if ys else 0.0
            order = sorted(layer, key=bary)
        for i, n in enumerate(order):
            y = int((i - (len(order) - 1) / 2) * DY)
            yset[n] = y
            coords[n] = (-450 + li * DX, y + CY)
    return coords


def task_annotation(task_text, x1, y1):
    """タイトル＋チケットの簡易注釈(全文は Lab Notes 側)。CML 0.3.0 text注釈。"""
    lines = task_text.splitlines()
    title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), "")
    ticket = next((ln.lstrip("> ").strip().replace("**", "")
                   for ln in lines if ln.startswith(">")), "")
    content = f"{title}\n\n{ticket}\n\n(問題文の全文はメニューの Lab Notes を参照)"
    return {
        "border_color": "#80808000", "border_style": "", "color": "#FFFFFFFF",
        "rotation": 0, "text_bold": True, "text_content": content,
        "text_font": "monospace", "text_italic": False, "text_size": 14,
        "text_unit": "pt", "thickness": 1, "type": "text",
        "x1": float(x1), "y1": float(y1), "z_index": 0,
    }


def random_macs(spec, rng):
    """problem.yml の lab.mac_random から、その回のスイッチの MAC を決める(BL-249)。

    spec = {slot: 0, nodes: [SW1, ...], collide: {pair: [SW4, SW5], prob: 0.05}}
    - 対象ノードの slot 番ポートへ 52:54:00:XX:YY:ZZ を振る。XX はノード間で重ならない無作為な値、YY・ZZ も無作為。
      → MAC の大小(＝STP の同点時の比較)とノード名の順が連動しない。
    - collide の確率に当たった回だけ、pair の 2 台の XX をそろえる(YY・ZZ は別)。IOSvL2 は PAgP の装置 ID を
      「slot 0 の MAC の XX＋8000」で作るので PAgP の ID だけが衝突し、STP のブリッジ ID は衝突しない。
    - 検証用: 環境変数 LAB_MAC_COLLIDE=1/0 で当たり外れを強制できる。
    """
    nodes = list(spec["nodes"])
    slot = int(spec.get("slot", 0))
    first = rng.sample(range(0x10, 0xF0), len(nodes))
    plan = {n: [first[i], rng.randrange(256), rng.randrange(256)] for i, n in enumerate(nodes)}
    col = spec.get("collide") or {}
    force = os.environ.get("LAB_MAC_COLLIDE", "")
    hit = bool(col) and (force == "1" or (force != "0" and rng.random() < float(col.get("prob", 0))))
    if hit:
        a, b = col["pair"]
        plan[b][0] = plan[a][0]
        while plan[b][1:] == plan[a][1:]:
            plan[b][1:] = [rng.randrange(256), rng.randrange(256)]
    macs = {n: {slot: "52:54:00:%02x:%02x:%02x" % tuple(v)} for n, v in plan.items()}
    return macs, {"collide": hit, "pair": col.get("pair"), "macs": {n: m[slot] for n, m in macs.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--image-family", required=True)
    ap.add_argument("--day0-dir", required=True)
    ap.add_argument("--out", required=True)
    # off= キャンバスに問題の要約注釈を貼らない(全文は Lab Notes に残る)。
    # パックのラボは盤面を開いただけで題材が割れないよう off で組む。
    ap.add_argument("--task-annotation", choices=("on", "off"), default="on")
    # XR のノード(family=iosxr)を別の XR 機種へ差し替える(例: iosxrd= XRd。BL-250)。
    ap.add_argument("--xr-platform", default="iosxr")
    a = ap.parse_args()

    pmeta = load(f"{a.repo}/problems/{a.problem}/problem.yml")
    all_profiles = load(f"{a.repo}/group_vars/all/main.yml")["device_profiles"]

    nodes_in = pmeta["target_nodes"]
    data_links = pmeta.get("lab", {}).get("links", [])
    # 外部L2接続(ext_links): データIFを external connector へ直結する。
    # 例(containerlab 複合ラボ・BL-061): CML の LAN-IX(bridge1) ⇔ szk-cl01 br-cml。
    #   lab:
    #     ext_links:
    #       - { node: RT01, if: 1, connector: "LAN-IX" }   # connector はラベル or デバイス名
    ext_links = pmeta.get("lab", {}).get("ext_links", [])
    # データ面の非管理スイッチ(多アクセス LAN 用): target_nodes に含めない＝
    # mgmt/day0/採点の対象外。lab.links の端点として名前で参照できる。
    #   lab:
    #     switches: [SWB]                     # 非管理スイッチのノード名リスト
    #     links: [{a: RT02, a_if: 2, b: SWB, b_if: 0}, {a: CLB, a_if: 0, b: SWB, b_if: 1}, ...]
    switches = list(pmeta.get("lab", {}).get("switches", []) or [])
    switch_set = set(switches)

    # ノード単位イメージ上書き（無ければ全ノード --image-family）。
    node_fam = pmeta.get("node_image_families", {}) or {}
    if a.xr_platform != "iosxr":
        node_fam = {n: (a.xr_platform if f == "iosxr" else f) for n, f in node_fam.items()}
        if a.image_family == "iosxr":
            a.image_family = a.xr_platform
    # problem.yml の node_xr_platforms: {XRD01: iosxrd} でノード単位に XR 機種を差し替える
    # (同じ盤面に XRv9000 と XRd を並べて挙動を比べる等。採点・履歴の仕込みは family=iosxr のまま扱う)。
    for n, plat in (pmeta.get("node_xr_platforms", {}) or {}).items():
        node_fam[n] = plat
    # problem.yml の node_images: {XRV01: iosxrv9000-26-1-1} でノード単位にイメージ(版)を差し替える。
    node_img = pmeta.get("node_images", {}) or {}

    def prof_of(name):
        """そのノードのイメージ family × role からプロファイルを引く。"""
        fam = node_fam.get(name, a.image_family)
        return all_profiles[fam][role_of(name)]

    # プロファイルの slot_map で problem.yml の slot 番号を機種の slot に読み替える
    # (XRd: XRv9000 基準の 3 → 1。problem.yml は機種をまたいで同じ番号で書ける・BL-250)。
    def remap(n, slot):
        if n in switch_set:
            return slot
        return (prof_of(n).get("slot_map") or {}).get(slot, slot)
    data_links = [{**lk, "a_if": remap(lk["a"], lk["a_if"]), "b_if": remap(lk["b"], lk["b_if"])}
                  for lk in data_links]
    ext_links = [{**ex, "if": remap(ex["node"], ex["if"])} for ex in ext_links]

    # 各ノードが使う物理スロット（リンク参加分 + MGMT）。スイッチはポートを別集計。
    used = {n: set() for n in nodes_in}
    sw_used = {s: set() for s in switches}
    for lk in data_links:
        for end, ifk in (("a", "a_if"), ("b", "b_if")):
            n = lk[end]
            (sw_used[n] if n in switch_set else used[n]).add(lk[ifk])
    for ex in ext_links:
        used[ex["node"]].add(ex["if"])
    # problem.yml の console_nodes= 管理 IF を持たないノード（管理スイッチへ結線しない・BL-225）
    console_nodes = set(pmeta.get("console_nodes", []) or [])
    for n in nodes_in:
        if n not in console_nodes:
            used[n].add(prof_of(n)["mgmt_slot"])
    # lab.mac_random があれば、その回の MAC を決めて lab.macs に足す(BL-249。当たり外れは生成物の mac_plan.json に残す)
    mr = (pmeta.get("lab", {}) or {}).get("mac_random")
    if mr:
        rmacs, mplan = random_macs(mr, random.Random(os.environ.get("LAB_SEED") or None))
        lab_meta = pmeta.setdefault("lab", {})
        merged = dict(lab_meta.get("macs") or {})
        for n, m in rmacs.items():
            merged[n] = {**(merged.get(n) or {}), **m}
        lab_meta["macs"] = merged
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "mac_plan.json"), "w", encoding="utf-8") as fh:
            json.dump(mplan, fh, ensure_ascii=False, indent=1)
    # lab.macs で MAC を固定するスロットは、未配線でもインタフェースとして定義する。
    # (IOSvL2 は 1 番目のポートの MAC から装置 ID を作る。CML の乱数が重なると PAgP の相手 ID が衝突する)
    for n, m in (pmeta.get("lab", {}).get("macs", {}) or {}).items():
        if n in used:
            used[n].update(int(s) for s in m)
    # contiguous_slots: 渡された IF を順に名付ける機種(XRd)は、間の slot も定義して番号ずれを防ぐ
    for n in nodes_in:
        if prof_of(n).get("contiguous_slots") and used[n]:
            used[n].update(range(max(used[n]) + 1))

    # 座標: problem.yml の lab.positions 優先(役割ベースの正準配置を生成器が埋める)
    coords = layout(nodes_in, pmeta.get("lab", {}).get("positions", {}) or {},
                    data_links)
    nodes, links = [], []
    node_ram = pmeta.get("node_ram", {}) or {}
    for name in nodes_in:
        role = role_of(name)
        prof = prof_of(name)
        day0 = open(f"{a.day0_dir}/{name}.cfg", encoding="utf-8").read()
        # server(Linux) は day0 が cloud-init の user-data と network-config の
        # 2 部構成（マーカー区切り）の場合のみ分割。※現行 baseline_server は
        # user-data 1 枚（cisco.cml モジュールが list 形式 config を壊すため）。
        # この分岐は REST 直 import 用に温存。
        # CML には名前付きファイルのリストとして渡す。
        if "---CCNP-NETWORK-CONFIG---" in day0:
            user_data, net_cfg = day0.split("---CCNP-NETWORK-CONFIG---", 1)
            configuration = [
                {"name": "user-data", "content": user_data.strip() + "\n"},
                {"name": "network-config", "content": net_cfg.strip() + "\n"},
            ]
        else:
            configuration = day0
        ifaces = []
        # problem.yml の lab.macs: {PC06: {1: "52:54:00:..."}} でインタフェースの MAC を固定
        # (DHCP 予約の client-id 用・BL-225)。★CML は起動済みノードの MAC を変更できない
        # (物理構成ロック)ため、トポロジ作成時に書くしかない。
        macs = (pmeta.get("lab", {}).get("macs", {}) or {}).get(name, {}) or {}
        for slot in sorted(used[name]):
            label = prof["mgmt"] if slot == prof["mgmt_slot"] else prof["links"][slot]
            ifc = iface(name, slot, label)
            if slot in macs or str(slot) in macs:
                ifc["mac_address"] = macs.get(slot, macs.get(str(slot)))
            ifaces.append(ifc)
        cx, cy = coords[name]
        node = {
            "id": name, "label": name,
            "node_definition": prof["node_definition"],
            "image_definition": node_img.get(name, prof["image_definition"]),
            "configuration": configuration,
            "x": cx, "y": cy,
            "tags": [role + "s"],
            "interfaces": ifaces,
        }
        # problem.yml の node_ram: {ZBX01: 3072} でノード単位に RAM 上書き
        # （ubuntu 既定 2048MB では Zabbix 等が窮屈な場合に使う）。
        if name in node_ram:
            node["ram"] = int(node_ram[name])
        nodes.append(node)

    # データ面の非管理スイッチを配置（接続先ノードの重心近くに置く）。
    for s in switches:
        neigh = []
        for lk in data_links:
            if lk["a"] == s and lk["b"] in coords:
                neigh.append(coords[lk["b"]])
            elif lk["b"] == s and lk["a"] in coords:
                neigh.append(coords[lk["a"]])
        if neigh:
            sx = sum(c[0] for c in neigh) // len(neigh)
            sy = sum(c[1] for c in neigh) // len(neigh)
        else:
            sx, sy = 0, 0
        nodes.append({
            "id": s, "label": s,
            "node_definition": "unmanaged_switch", "image_definition": None,
            "configuration": "", "x": sx, "y": sy, "tags": [],
            "interfaces": [iface(s, p, f"port{p}") for p in sorted(sw_used[s])],
        })

    # 管理スイッチ(unmanaged) + 外部接続(System Bridge) — トポロジの下に置く
    min_x = min(c[0] for c in coords.values())
    min_y = min(c[1] for c in coords.values())
    max_y = max(c[1] for c in coords.values())
    sw_ports = len(nodes_in) + 1
    nodes.append({
        "id": "MGMTSW", "label": "MGMT-SW",
        "node_definition": "unmanaged_switch", "image_definition": None,
        "configuration": "", "x": min_x, "y": max_y + 250, "tags": [],
        "interfaces": [iface("MGMTSW", p, f"port{p}") for p in range(sw_ports)],
    })
    nodes.append({
        "id": "EXTC", "label": "to-MGMT-net",
        "node_definition": "external_connector", "image_definition": None,
        "configuration": "System Bridge", "x": min_x + 200, "y": max_y + 250,
        "tags": [],
        "interfaces": [iface("EXTC", 0, "port")],
    })

    def add_link(na, ia, nb, ib, lab):
        links.append({
            "id": f"l{len(links)}",
            "n1": na, "i1": ia, "n2": nb, "i2": ib,
            "conditioning": {}, "label": lab,
        })

    # 問題のデータリンク
    for lk in data_links:
        add_link(lk["a"], f"{lk['a']}-i{lk['a_if']}",
                 lk["b"], f"{lk['b']}-i{lk['b_if']}", f"{lk['a']}<->{lk['b']}")
    # 外部L2接続(データ面): ノードの真上に ext-conn を置いて直結
    for i, ex in enumerate(ext_links):
        exid = f"EXTX{i}"
        ex_x, ex_y = coords[ex["node"]]
        nodes.append({
            "id": exid, "label": ex.get("label", f"to-{ex['connector']}"),
            "node_definition": "external_connector", "image_definition": None,
            "configuration": ex["connector"], "x": ex_x, "y": ex_y - 160,
            "tags": [],
            "interfaces": [iface(exid, 0, "port")],
        })
        add_link(ex["node"], f"{ex['node']}-i{ex['if']}", exid, f"{exid}-i0",
                 f"{ex['node']}<->{ex['connector']}")
    # 各ノードの MGMT → 管理スイッチ → 外部接続
    for idx, name in enumerate(nodes_in):
        if name in console_nodes:
            continue
        mslot = prof_of(name)["mgmt_slot"]
        add_link(name, f"{name}-i{mslot}", "MGMTSW", f"MGMTSW-i{idx}", f"{name}-mgmt")
    add_link("MGMTSW", f"MGMTSW-i{len(nodes_in)}", "EXTC", "EXTC-i0", "mgmt-uplink")

    # 問題文: _generated/<id>/task.md (variant描画版) → problems/<id>/task.md の順で探す。
    # 全文は Lab Notes(CMLワークベンチでMarkdown表示)へ、要約をキャンバス注釈へ。
    task_text = None
    for cand in (os.path.join(os.path.dirname(a.out), "task.md"),
                 f"{a.repo}/problems/{a.problem}/task.md"):
        if os.path.exists(cand):
            task_text = open(cand, encoding="utf-8").read()
            break
    notes = task_text if task_text else "generated by gen_cml_lab.py"
    annotations = []
    if task_text and a.task_annotation == "on":
        annotations.append(task_annotation(task_text, min_x - 620, min_y))

    # description に MGMT リース情報を JSON で埋め込む(problem は base64 で不透明化)。
    # → 台帳(topologies/_state/mgmt_leases.json)が失われても mgmt_alloc.py gc が
    #   CML 上の稼働ラボから割当を完全復元できる(CML サーバ自体が真実の源)。
    desc = ""
    mm_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "mgmt_map.yml")
    if os.path.exists(mm_path):
        desc = lease_description(a.problem, load(mm_path))

    topology = {
        "lab": {"title": lab_title(a.problem), "description": desc,
                "notes": notes, "version": "0.3.0"},
        "nodes": nodes, "links": links,
        "annotations": annotations, "smart_annotations": [],
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        yaml.safe_dump(topology, f, allow_unicode=True, sort_keys=False, width=4096)
    print(f"wrote {a.out}: {len(nodes)} nodes, {len(links)} links "
          f"(family={a.image_family})")


if __name__ == "__main__":
    main()
