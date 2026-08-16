#!/usr/bin/env python3
"""IOS AAA(RADIUS) 紙面ファミリ (BL-101 P1a) — gen_paper_mcq.py の shape=aaa 素材。

★紙面専用: 挙動は実機確定表(poc/aaa/README.md)の写像である `aaa_model.py` から
決定的に生成する(実機展開は行わない)。

P1a の出題形は **read / cause / trace / evidence** の 4 形(fix/patch は P1b)。

★この shape の骨格(2026-08-08 レビューで確定):
  1. **Reject は権威で後段へ落ちない / 応答なしのときだけ落ちる** — この 1 本の統一原理が
     authentication / authorization / enable の 3 層すべてを貫く(実測 E1/E6/E16b)。
  2. **機器側の出力が同一で原因が複数ありうるペアが存在する**
     (key_mismatch ↔ src_iface_missing / list_not_applied ↔ list_undefined)。
     → 「次に何を見るか」を問う **evidence 形**を新設した。錯乱肢は
     「その出力では両者が同じ値になる」ものを**機械判定**で選ぶ。
  3. **送信元アドレスは盤面の常設要素**。AAA はトポロジ的思考がほぼ無い題材なので、
     直結拠点と 1 ホップ先で送信元が変わる事実(実測 E3/E3B)を主症状に使い、
     「片方の拠点だけ入れない」を読ませる。
"""
import argparse
import copy
import random
import zlib

try:
    import aaa_model as am
except ImportError:                                   # パッケージ外から読む場合
    from topologies import aaa_model as am

# 現在(壊れている)状態の種別。★いずれも「その1点で症状が説明できる」こと。
#
# ★P1a の自己検査で判明(2026-08-08): 故障には **潜在型** がある。
#   - `port_mismatch` / `authz_no_fallback` は **2 台目のサーバに頼る状況**にならないと現れない
#     (1 台目が応答している限り健全に見える) → 盤面に「SRV01 が計画停止中」を持たせて顕在化させる。
#   - `enable_via_radius` は **特権昇格を観測しないと**現れない → 観測集合に昇格の行を足した。
#   これを怠ると「健全と同じ指紋」の種別が量産され、evidence 形の対立仮説が偽物になる。
#
# ★`src_iface_group_level` は P1a の種別から外した。これは「グローバル側を消しても
#   グループ配下が効き続ける」= **是正が効かない**罠であり、現在状態としては健全そのもの。
#   fix/patch を扱う P1b の錯乱肢・patch 対象として使う(P1B_ONLY_KINDS)。
KINDS = ["user_not_registered", "key_mismatch", "src_iface_missing",
         "port_mismatch", "no_authz_exec", "authz_no_fallback",
         "list_not_applied", "list_undefined", "enable_via_radius",
         "console_forgotten", "authz_console_missing",
         "authz_if_authenticated", "acl_block_request", "acl_block_reply",
         "vty_range_partial", "deadtime_only"]

P1B_ONLY_KINDS = ["src_iface_group_level"]

# 2 台目に頼る状況でしか現れない故障(盤面で SRV01 を停止させる)
NEEDS_OUTAGE = {"port_mismatch", "authz_no_fallback", "deadtime_only"}

# ★健全な既定では console に専用の方式リストを当てる(実測 C3/C4)。
#   これが無いと console は default に従うので、サーバ全断や Reject の巻き添えを食う(C1)。
#   `console_forgotten` はこの専用リストを当て忘れた状態。
CONSOLE_LIST = "CONSOLE"

# 要件世界(P1b の fix/patch で正解手段を反転させる。P1a では要件文として提示する)
WORLDS = ["default_frozen", "console_survives", "server_frozen", "no_lockout"]

GRP_POOL = ["RADGRP", "AAA-SRV", "RAD-GROUP", "NOC-RADIUS", "AUTH-GRP"]
ACL_POOL = ["WAN-IN", "EDGE-FILTER", "MGMT-GUARD", "UPLINK-ACL", "BORDER-IN"]
LIST_POOL = ["VTY-AUTH", "REMOTE", "ADMIN-LOGIN", "MGMT", "NOC-LIST"]
SITE_POOL = ["札幌", "仙台", "千葉", "横浜", "名古屋", "京都", "神戸", "広島",
             "松山", "福岡", "熊本", "那覇"]
ADM_POOL = ["noc-taro", "noc-hanako", "netadmin", "ope-suzuki", "adm-kato"]
DESK_POOL = ["helpdesk", "monitor-op", "desk-01", "watch-op"]
EMG_POOL = ["emg-admin", "local-admin", "break-glass", "backup-adm"]


def _typo(name, rnd):
    """参照タイポ(未定義リスト名の作り方)。"""
    c = []
    if "-" in name:
        c += [name.replace("-", "_"), name.replace("-", "")]
    if name[-1].isdigit():
        c.append(name[:-1] + str((int(name[-1]) + 1) % 10))
    c.append(name + "1")
    return rnd.choice(c)


def draw(rnd, kind=None, world=None):
    d = {"shape": "aaa"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    a, b = rnd.sample(SITE_POOL, 2)
    d["site"] = {"A": a, "B": b}                  # A=サーバ直結 / B=1ホップ先
    d["rt"] = {"A": f"RT-{a[0]}1", "B": f"RT-{b[0]}2"}
    d["grp"] = rnd.choice(GRP_POOL)
    d["aclname"] = rnd.choice(ACL_POOL)
    d["listname"] = rnd.choice(LIST_POOL)
    d["badlist"] = _typo(d["listname"], rnd)
    d["adm"] = rnd.choice(ADM_POOL)
    d["desk"] = rnd.choice(DESK_POOL)
    d["emg"] = rnd.choice(EMG_POOL)
    d["auto"] = "SUZUKI"
    o3 = rnd.randint(1, 240)
    d["net"] = {
        "loA": f"10.{rnd.randint(0, 9)}.0.1", "loB": f"10.{rnd.randint(0, 9)}.0.2",
        "srv1": f"10.99.{o3}.2", "srv2": f"10.99.{o3 + 1}.2",
        "egA": f"10.99.{o3}.1", "egB": f"10.{rnd.randint(10, 99)}.12.2",
    }
    d["port2"] = rnd.choice([1645, 1912, 11812])         # RAD2 の待受(非標準)
    d["timeout"] = rnd.choice([2, 3, 5])
    d["retransmit"] = rnd.choice([1, 2])
    d["key"] = rnd.choice(["Rad-8102", "Ccnp-Aaa-77", "Sh4red-Key", "K-9931"])
    d["scope"] = rnd.choice(["A", "B"])           # 故障を持つ拠点
    if d["kind"] == "user_not_registered":
        d["scope"] = "both"                       # サーバ側事由は両拠点に効く
    # ★2 台目に頼る状況でしか現れない故障は、盤面に計画停止を持たせて顕在化させる。
    #   それ以外の種別でも一定割合で停止させる= **1 台目が落ちている状況では
    #   「鍵不一致 / 送信元誤り / ポート取り違え」の 3 つが同じ症状に化ける**ため、
    #   evidence 形の対立仮説を 2 つでなく 3 つにできる(消去法封じ)。
    d["srv1_down"] = (d["kind"] in NEEDS_OUTAGE) or (rnd.random() < 0.45)
    d["patch_missing"] = rnd.choice(PATCH_MISSING)   # patch 形で使う欠落工程
    if world is None:
        d["world"] = rnd.choice(compatible_worlds(d) or WORLDS)
    return d


def compatible_worlds(d):
    """P1a では要件は提示のみなので広く許すが、明らかに噛み合わない組は外す。"""
    out = []
    for w in WORLDS:
        if w == "server_frozen" and d["kind"] == "user_not_registered":
            continue          # サーバ台帳が不可触では解けない(P1b で fix が立たない)
        if w == "console_survives" and d["kind"] == "enable_via_radius":
            continue          # console の生存と enable 昇格は論点が噛み合わない
        out.append(w)
    return out


# --------------------------------------------------------------------------
# 盤面 → aaa_model の入力(dev/srv)へ
# --------------------------------------------------------------------------
def _users(d):
    return {d["adm"]: 15, d["desk"]: 1, d["auto"]: 15}


def build(d, site, kind=None):
    """拠点 site(A/B)のルータについて (dev, srv) を組み立てる。

    kind を明示すると「もしその故障だったら」の仮定盤面を作れる(evidence 形で使用)。
    """
    kind = d["kind"] if kind is None else kind
    n = d["net"]
    faulted = (d["scope"] in ("both", site))
    k = kind if faulted else None

    lo = n["loA"] if site == "A" else n["loB"]
    eg = n["egA"] if site == "A" else n["egB"]
    src = lo
    if k == "src_iface_missing":
        src = eg                       # 送信元が egress IF になる(E3/E3B)
    elif k == "src_iface_group_level":
        src = lo                       # ★グローバルを消してもグループ配下が効き続ける
    dev = {
        "lists": {"authn": {"default": [f"group:{d['grp']}", "local"]},
                  "authz": {"default": [f"group:{d['grp']}", "local"]},
                  "enable": {}},
        # ★console は既定で専用リストを当てる(実測 C3/C4)。当て忘れが console_forgotten。
        "line": {"vty": {"login": None, "authz": None},
                 # ★`line vty 5 15`。方式リストを 0 4 にだけ当てると
                 #   6 セッション目以降だけ挙動が変わる(vty_range_partial)。
                 "vty_hi": {"login": None, "authz": None},
                 "con": {"login": (None if k == "console_forgotten"
                                   else CONSOLE_LIST), "authz": None}},
        "group": {"name": d["grp"], "members": ["RAD1", "RAD2"]},
        "servers": {"RAD1": {"ip": n["srv1"], "key": d["key"], "auth_port": 1812},
                    "RAD2": {"ip": n["srv2"], "key": d["key"],
                             "auth_port": d["port2"]}},
        "src_addr": src,
        "local": {d["emg"]: 15, d["auto"]: 15},
        "enable_secret": True,
        # ★実測 X5/X6/X11/X12: コンソールの認可はグローバルの
        #   `aaa authorization console` が無ければ**実行されず、権限レベルは 1 になる**。
        #   健全な盤面はこれを持つ(持たないと要件「コンソールから操作できること」を
        #   満たせない)。欠落そのものが故障種 `authz_console_missing`。
        "authz_console": (k != "authz_console_missing"),
        # ★実測(poc/aaa/results-deadstate.md)= `radius-server dead-criteria` は
        #   **既定では入らない**。無いと、応答しないサーバは何回試しても
        #   `show aaa servers` 上 `current UP` のままで、`deadtime` の出番が来ない。
        #   健全な盤面はこれを持つ。落とした盤面が故障種 `deadtime_only`(BL-105)。
        # ★`deadtime_only`(BL-105)= `deadtime` は書いてあるが判定条件が無い。
        #   サーバは DEAD にならず、片系断のとき**毎回**タイムアウトを食う。
        "dead_criteria": (k != "deadtime_only"),
        "timeout": d["timeout"], "retransmit": d["retransmit"],
    }
    if k != "console_forgotten":
        dev["lists"]["authn"][CONSOLE_LIST] = ["local"]
        dev["lists"]["authz"][CONSOLE_LIST] = ["local"]
        dev["line"]["con"]["authz"] = CONSOLE_LIST
    if k == "key_mismatch":
        dev["servers"]["RAD1"]["key"] = dev["servers"]["RAD2"]["key"] = "OLD-KEY"
    elif k == "port_mismatch":
        dev["servers"]["RAD2"]["auth_port"] = 1812
    elif k == "no_authz_exec":
        # ★既定の認可だけを外す。dict ごと消すと console 専用リストまで巻き込み、
        #   「どの是正でも健全に戻らない」盤面になる(P1b 実装時に検出)。
        dev["lists"]["authz"].pop("default", None)
    elif k == "authz_no_fallback":
        dev["lists"]["authz"]["default"] = [f"group:{d['grp']}"]
    elif k == "vty_range_partial":
        # 名前付きリストを作ったが **`line vty 0 4` にしか当てていない**。
        # 5 15 は default に従うため、6 セッション目以降だけ認証経路が変わる。
        dev["lists"]["authn"][d["listname"]] = [f"group:{d['grp']}", "local"]
        dev["lists"]["authn"]["default"] = ["local"]
        dev["line"]["vty"]["login"] = d["listname"]
    elif k == "acl_block_request":
        dev["acl_block"] = "out"        # ★X4: 要求を落とす
    elif k == "acl_block_reply":
        dev["acl_block"] = "in"         # ★X4b: 応答だけを落とす
    elif k == "authz_if_authenticated":
        # ★X1/X2 実測: 代替手段が `local` でなく `if-authenticated`。
        #   サーバが応答する限り健全と同一で、**全断でフォールバックしたときだけ**
        #   権限レベルが 1 に留まる(username の privilege が効かない)。
        dev["lists"]["authz"]["default"] = [f"group:{d['grp']}", "if-authenticated"]
    elif k == "list_not_applied":
        # 名前付きリストを作ったが line に付けていない → default が効く
        dev["lists"]["authn"][d["listname"]] = [f"group:{d['grp']}", "local"]
        dev["lists"]["authn"]["default"] = ["local"]
    elif k == "list_undefined":
        # line が未定義のリストを参照 → ★default へ落ちる(E15)。上と症状が一致する
        dev["lists"]["authn"]["default"] = ["local"]
        dev["line"]["vty"]["login"] = d["badlist"]
    elif k == "enable_via_radius":
        dev["lists"]["enable"] = {"default": [f"group:{d['grp']}", "enable"]}

    users = _users(d)
    if kind == "user_not_registered":
        users.pop(d["adm"], None)      # 管理者がサーバ台帳に無い(サーバ側事由)
    clients = [n["loA"], n["loB"]]     # ★clients は Loopback のみ許可
    # ★`all_down` は authread 形が使う「両系停止」。仕様表の稼働状態と必ず連動する
    #   (伏せると debug の遍歴が導出できない問題になる)。
    _down1 = d.get("srv1_down") or d.get("all_down")
    srv = {"RAD1": {"alive": not _down1, "key": d["key"],
                    "auth_port": 1812,
                    "clients": list(clients), "users": dict(users)},
           "RAD2": {"alive": not d.get("all_down"), "key": d["key"],
                    "auth_port": d["port2"],
                    "clients": list(clients), "users": dict(users)}}
    return dev, srv


def _healthy(d, site):
    dev, srv = build(d, site, kind="__none__")
    return dev, srv


# --------------------------------------------------------------------------
# 観測(紙面に出す出力ブロック)。すべて aaa_model から決定的に描く。
# --------------------------------------------------------------------------
def _res_ja(r):
    if r["result"] == am.OK:
        return f"ログイン可(権限レベル {r['priv']})"
    if r["result"] == am.REJECT:
        return "ログイン不可"
    if r["result"] == am.AUTHZ_FAIL:
        return "ログインは通るが exec 拒否"
    return "ログイン不可(応答なし)"


def dead_criteria_lines(dev, d):
    """`radius-server dead-criteria` の行(健全なら 1 行・落ちていれば 0 行)。

    ★実測 results-deadstate.md: 既定では入らない。無ければサーバは DEAD にならず、
      `deadtime` は永久に出番が来ない(= BL-105 の故障種 `deadtime_only`)。
    """
    if not dev.get("dead_criteria"):
        return []
    return [f"radius-server dead-criteria time {d['timeout']} tries 1"]


def _delay_ja(pair):
    """(1回目, 2回目以降) を日本語にする。★表示と判定で同じ文字列を使う。"""
    first, rep = pair
    if first == 0:
        return "即時"
    r = "即時" if rep == 0 else f"約 {rep} 秒"
    return f"1 回目 約 {first} 秒 / 2 回目以降 {r}"


def site_rows(dev, srv, d):
    """★1 拠点ぶんの観測(ユーザ, 結果)。**提示にも是正の判定にも同じものを使う**。

    紙面に出す行と `fix_works()` が見る行がずれると、**故障が判定側から見えず
    どの候補でも「直った」ことになる**。実際 `authz_no_fallback` でも
    `vty_range_partial` でも同じ事故を起こした(2026-08-08)。
    → **観測の定義をここ 1 箇所に集約する**。
    """
    rows = [(u, _res_ja(am.login(dev, srv, u)))
            for u in (d["adm"], d["desk"], d["emg"])]
    # ★特権昇格は「権限レベル 1 でログインできた利用者」についてのみ載せる。
    #   ログイン不可の利用者では観測できず(ユーザ指摘の論理矛盾)、
    #   priv 15 で入れた利用者では昇格が無意味(監査5)。該当者が居なければ行ごと省く。
    for cand in (d["desk"], d["adm"], d["emg"]):
        r = am.login(dev, srv, cand)
        if r["result"] == am.OK and r["priv"] == 1:
            e = am.enable(dev, srv, cand)
            rows.append((f"{cand} からの特権昇格",
                         "昇格可(15)" if e["result"] == am.OK else "昇格不可"))
            break
    # ★`line vty 5 15` 側(全故障種で一律に出す)。方式リストを
    #   `line vty 0 4` にしか当てていない構成は、ここでだけ症状が出る。
    rows.append((f"{d['adm']}(6 セッション目以降)",
                 _res_ja(am.login(dev, srv, d["adm"], line="vty_hi"))))
    # ★console 行(実測 C1〜C5)。これが無いと要件世界 console_survives を
    #   読者が判定できず、`console_forgotten` も観測に現れない。
    rows.append((f"{d['emg']}(コンソールから)",
                 _res_ja(am.login(dev, srv, d["emg"], line="con"))))
    # ★所要時間の行(全故障種で一律に出す)。これが無いと `deadtime_only` は
    #   「誰が入れるか」に一切現れず、観測からも判定からも見えない
    #   (`authz_no_fallback` / `vty_range_partial` で起こしたのと同じ事故)。
    rows.append((f"{d['adm']}(ログインに要する時間)",
                 _delay_ja(am.delay_pair(dev, srv))))
    return rows


def login_table(d, kind=None):
    """read 形の本体: 誰がどの拠点から入れるか。

    ★最終行に**特権昇格**を入れる。これが無いと `enable_via_radius` が
    観測に現れず「健全と同じ指紋」になってしまう(P1a 自己検査で判明)。
    """
    rows = []
    for site in ("A", "B"):
        dev, srv = build(d, site, kind)
        rows += [(d["site"][site], u, r) for u, r in site_rows(dev, srv, d)]
    return rows


def outage_table(d, kind=None):
    """★「認証サーバがすべて停止した場合」の観測(2026-08-08 追加)。

    平常時だけを見せると、**フォールバック側の故障が観測に一切現れない**。
    実際 `authz_no_fallback` は 60/60 の盤面で健全と同じ表になっており、
    「一部の利用者が操作できない」という設問文と観測が矛盾していた。
    `if-authenticated`(X1/X2 実測)も同じで、**全断でフォールバックしたときだけ**
    権限レベル 1 に留まるという差が出る。

    載せるのは全断でも認証が通りうる利用者に限る(RADIUS 台帳のみの利用者は
    どの故障種でもログイン不可になり、識別に寄与しないため出さない)。
    """
    rows = []
    for site in ("A", "B"):
        dev, srv = build(d, site, kind)
        for s in srv.values():
            s["alive"] = False
        for u in (d["emg"], d["auto"]):
            rows.append((d["site"][site], u, _res_ja(am.login(dev, srv, u))))
        rows.append((d["site"][site], f"{d['emg']}(コンソールから)",
                     _res_ja(am.login(dev, srv, d["emg"], line="con"))))
    return rows


def render_obs(d, kind=None):
    """紙面に出す観測の全体(平常時 ＋ 全断時)。指紋もこれを使う。"""
    return "\n".join([
        render_login_table(d, login_table(d, kind)),
        "",
        "認証サーバがすべて停止した場合:",
        "",
        render_login_table(d, outage_table(d, kind)),
    ])


def render_login_table(d, rows):
    out = ["| 拠点 | ユーザ | 結果 |", "|---|---|---|"]
    for site, u, r in rows:
        out.append(f"| {site} | {u} | {r} |")
    return "\n".join(out)


def test_aaa_text(d, site, kind=None, user=None):
    """`test aaa group ... legacy` の出力(文言は実測に忠実)。"""
    dev, srv = build(d, site, kind)
    u = user or d["adm"]
    res = am.run_methods(dev, srv, [f"group:{d['grp']}"], u)
    head = f"Attempting authentication test to server-group {d['grp']} using radius"
    if res[0] == am.OK:
        body = "User was successfully authenticated."
    elif res[0] == am.REJECT:
        body = "User authentication request was rejected by server."
    else:
        body = "No authoritative response from any server."
    return f"{head}\n{body}"


def trace_row(d, site, kind=None):
    """trace 形の 1 行: 文言 + 所要秒(★秒数は式から出す)。"""
    dev, srv = build(d, site, kind)
    txt = test_aaa_text(d, site, kind).splitlines()[-1]
    sec_s = _delay_ja(am.delay_pair(dev, srv))
    return f"{d['site'][site]}: {txt} ({sec_s})"


def trace_block(d, kind=None):
    return "\n".join(trace_row(d, s, kind) for s in ("A", "B"))


def aaa_servers_block(d, site, kind=None):
    dev, srv = build(d, site, kind)
    why = am.unreachable_reasons(dev, srv)
    out = []
    for i, name in enumerate(("RAD1", "RAD2"), start=1):
        s = dev["servers"][name]
        out.append(f"RADIUS: id {i}, priority {i}, host {s['ip']}, "
                   f"auth-port {s['auth_port']}, acct-port {s['auth_port'] + 1}, "
                   f"hostname {name}")
        # ★到達不能=DEAD ではない。**`dead-criteria` を満たして初めて** DEAD になる
        #   (実測 results-deadstate.md: 判定条件が無いと 4 回連続で失敗しても UP のまま)。
        st = "DEAD" if (why[name] and dev.get("dead_criteria")) else "UP"
        out.append(f"     State: current {st}, duration 4s, previous duration 0s")
    return "\n".join(out)


def server_log_block(d, site, kind=None):
    """サーバ側 radius.log(★ここだけが key_mismatch と src_iface_missing を分ける)。"""
    dev, srv = build(d, site, kind)
    why = am.unreachable_reasons(dev, srv)
    src = dev["src_addr"]
    lines = []
    for name in ("RAD1", "RAD2"):
        w = why[name]
        port = srv[name]["auth_port"]
        if w == "unknown_client":
            lines.append(f"Error: Ignoring request to auth address * port {port} "
                         f"bound to server default from unknown client {src} "
                         f"port 1645 proto udp")
        elif w == "key_mismatch":
            lines.append(f"Auth: Login incorrect (pap: Cleartext password does not "
                         f"match \"known good\" password): [{d['adm']}/"
                         f"\\xb7\\x1f\\xd2\\x8a\\x03] (from client rt-lo port 0)")
        elif w == "port_mismatch":
            pass                                   # そもそも届かない = 記録なし
        elif w is None:
            r = am.query_group(dev, srv, d["grp"], d["adm"])
            if r[0] == "accept":
                lines.append(f"Auth: Login OK: [{d['adm']}] (from client rt-lo port 0)")
            elif r[0] == "reject":
                lines.append(f"Auth: Login incorrect (No Auth-Type found: rejecting "
                             f"the user via Post-Auth-Type = Reject): "
                             f"[{d['adm']}/****] (from client rt-lo port 0)")
            break
    return "\n".join(lines)      # ★記録が無ければ空。説明文は書かない


def debug_block(d, site, kind=None, user=None):
    """`debug radius authentication` の抜粋(★実測 poc/aaa/results-debug.md の写像)。

    ここが evidence 形の正解になる。**サーバ側ログは使わない**
    (ENARSI の範囲外で、解答者が `show aaa servers` との差を判断できないため)。
    """
    dev, srv = build(d, site, kind)
    return debug_render(d, dev, srv, site, user)


def debug_render(d, dev, srv, site, user=None):
    """★dev/srv を直接受け取る描画本体(dbgconf 形の逆問題検証に使う)。

    `debug_block` は「d と故障種から dev を組み立てて描く」入口。こちらは
    **任意の構成 dev** について同じ debug を描くので、候補構成それぞれの出力を
    描き比べて「示された出力を生じさせる構成はどれか」を機械検証できる。
    """
    u = user or d["adm"]
    src = dev["src_addr"]
    lo = d["net"]["loA"] if site == "A" else d["net"]["loB"]
    has_src = (src == lo)
    out = [f"RADIUS: Pick NAS IP for u=0x7605 tableid=0 "
           f"cfg_addr={lo if has_src else '0.0.0.0'}"]
    tid = 119
    for i, name in enumerate(dev["group"]["members"]):
        sd = dev["servers"][name]
        ok, why = am._reachable(dev, srv, name)
        if not has_src:
            out.append(f"RADIUS/ENCODE: Best Local IP-Address {src} "
                       f"for Radius-Server {sd['ip']}")
        if i == 0:
            out.append(f"RADIUS(00000000): Send Access-Request to "
                       f"{sd['ip']}:{sd['auth_port']} id 1645/{tid}, len 60")
            out.append(f"RADIUS:  NAS-IP-Address      [4]   6   {src}")
            out.append(f'RADIUS:  User-Name           [1]   10  "{u}"')
            out.append("RADIUS:  User-Password       [2]   18  *")
        else:
            out.append(f"RADIUS: Fail-over to ({sd['ip']}:{sd['auth_port']},"
                       f"{sd['auth_port'] + 1}) for id 1645/{tid}")
        out.append(f"RADIUS(00000000): Started {dev['timeout']} sec timeout")
        if ok:
            res = am.query_group(dev, srv, d["grp"], u)
            if res[0] == "accept":
                out.append(f"RADIUS: Received from id 1645/{tid} "
                           f"{sd['ip']}:{sd['auth_port']}, Access-Accept, len 69")
                out.append("RADIUS:  Service-Type        [6]   6   NAS Prompt")
                out.append(f'RADIUS:   Cisco AVpair       [1]   19  '
                           f'"shell:priv-lvl={res[1]}"')
            else:
                out.append(f"RADIUS: Received from id 1645/{tid} "
                           f"{sd['ip']}:{sd['auth_port']}, Access-Reject, len 38")
            return "\n".join(out)
        if why == "key_mismatch":
            # ★応答は届いているが復号に失敗して捨てている(実測 D2)
            out.append(f"RADIUS: Received from id 1645/{tid} "
                       f"{sd['ip']}:{sd['auth_port']}, Access-Reject, len 38")
            out.append("RADIUS: response-authenticator decrypt fail, pak len 38")
            out.append("RADIUS: message-authenticator decrypt fail, pak len 38")
            out.append(f"RADIUS: Response ({tid}) failed decrypt")
        for _ in range(dev["retransmit"]):
            out.append("RADIUS(00000000): Request timed out!")
            out.append(f"RADIUS: Retransmit to ({sd['ip']}:{sd['auth_port']},"
                       f"{sd['auth_port'] + 1}) for id 1645/{tid}")
            out.append(f"RADIUS(00000000): Started {dev['timeout']} sec timeout")
            if why == "key_mismatch":
                out.append(f"RADIUS: Received from id 1645/{tid} "
                           f"{sd['ip']}:{sd['auth_port']}, Access-Reject, len 38")
                out.append(f"RADIUS: Response ({tid}) failed decrypt")
        out.append("RADIUS(00000000): Request timed out!")
    out.append("RADIUS: No response from server")
    return "\n".join(out)


# --------------------------------------------------------------------------
# authread 形 — `enable` 時の方式リスト遍歴を読ませる(BL-103 ⑥)
# --------------------------------------------------------------------------
# ★実測 X7〜X10 の要点: 方式リストの遍歴(`Method=` / `status=`)が debug に出るのは
#   **`service=ENABLE` のときだけ**。ログイン認証は SSH でもコンソールでも
#   `Pick method list 'default'` の 1 行しか出ない。→ この形は enable で作る。
ENABLE_SCENARIOS = [
    # (方式リスト有無, パスワード正否)  ※到達可否は盤面(サーバ稼働状態)から決まる
    ("nolist", True), ("nolist", False), ("list", True), ("list", False),
]


def enable_walk(d, site, kind=None, pw_ok=True, with_list=True):
    """`enable` のメソッド遍歴。描画も設問の真偽判定もここから出す。"""
    dev, srv = build(d, site, kind)
    if with_list:
        dev["lists"]["enable"] = {"default": [f"group:{d['grp']}", "enable"]}
    else:
        dev["lists"]["enable"] = {}
    methods = dev["lists"]["enable"].get("default")
    if not methods:
        # 方式リストが無い= 既定で enable secret のみ(実測 X8a/X8b)
        return dev, srv, [("enable", am.PASS if pw_ok else am.FAIL, None)], False
    return dev, srv, am.walk_methods(dev, srv, methods, "$enab15$", pw_ok), True


def enable_debug_block(d, site, kind=None, pw_ok=True, with_list=True,
                       on_console=False):
    """`debug aaa authentication` の抜粋(★実測 poc/aaa/results-ext.md X8/X10/X9c の写像)。

    ★実測から写し取っている点(監査で指摘され訂正・2026-08-09):
      - 2 本目の `Method=` 行の facility は**メソッドで非対称**。
        グループ側は `AAA/AUTHEN (id): Method=<G> (radius)`、
        ENABLE 側は `AAA/AUTHEN/CONT (id): Method=ENABLE`。
      - `continue_login` の利用者名は、グループ側は**実際の利用者名**、
        ENABLE 側は `(undef)`。占位文字列は書かない。
      - `port=` は実測値のみ(コンソール= `tty0` / それ以外= `tty3`)。
      - 遷移後のトランザクション ID は**連番ではない**(実測は無関係な値)。
      - **コンソール × 方式リスト有り は未実測**なので描かない(呼び出し側で禁止)。
    """
    _dev, _srv, steps, has_list = enable_walk(d, site, kind, pw_ok, with_list)
    port = "tty0" if on_console else "tty3"
    user = d["desk"]                       # 権限レベル 1 で入っている利用者が昇格を試みる
    seed = zlib.crc32(f"{d['grp']}|{site}|{with_list}|{pw_ok}".encode())
    ids = [1560798390 + (seed % 900000000), 175242526 + (seed % 700000000)]
    out = [f"AAA/AUTHEN/START ({ids[0]}): port='{port}' list='' "
           f"action=LOGIN service=ENABLE"]
    if has_list:
        out.append(f'AAA/AUTHEN/START ({ids[0]}): using "default" list')
    else:
        out.append(f"AAA/AUTHEN/START ({ids[0]}): "
                   + ("console enable - default to enable password (if any)"
                      if on_console else
                      "non-console enable - default to enable password"))
    for i, (m, res, _v) in enumerate(steps):
        grp_m = m.startswith("group:")
        label = f"{d['grp']} (radius)" if grp_m else "ENABLE"
        cur = ids[min(i, len(ids) - 1)]
        if i:                              # ★2 つ目以降は Restart を挟む(X10 実測)
            out += [f"AAA/AUTHEN/START ({cur}): port='{port}' list='' "
                    f"action=LOGIN service=ENABLE",
                    f"AAA/AUTHEN/START ({cur}): Restart"]
        out += [f"AAA/AUTHEN/START ({cur}): Method={label}",
                f"AAA/AUTHEN ({cur}): status = GETPASS",
                f"AAA/AUTHEN/CONT ({cur}): continue_login "
                + ("(user='(undef)')" if not grp_m else f"(user='{user}')"),
                f"AAA/AUTHEN ({cur}): status = GETPASS",
                # ★facility の非対称(実測): グループ側は /CONT が付かない
                (f"AAA/AUTHEN ({cur}): Method={label}" if grp_m
                 else f"AAA/AUTHEN/CONT ({cur}): Method={label}")]
        if res == am.FAIL and not grp_m:
            out.append(f"AAA/AUTHEN({cur}): password incorrect")
        out.append(f"AAA/AUTHEN ({cur}): status = "
                   + {am.PASS: "PASS", am.FAIL: "FAIL", am.ERROR: "ERROR"}[res])
    return "\n".join(out)


def enable_cfg_block(d, site, kind=None, with_list=True):
    """authread で見せる構成。★見出しが `| section aaa` なので **aaa の塊だけ**
    を出す(`radius-server ...` や `enable secret` は section に入らない=監査指摘)。"""
    out = ["aaa new-model", "!",
           f"aaa group server radius {d['grp']}",
           " server name RAD1", " server name RAD2", " deadtime 5", "!",
           f"aaa authentication login default group {d['grp']} local",
           f"aaa authorization exec default group {d['grp']} local"]
    if with_list:
        out.append(f"aaa authentication enable default group {d['grp']} enable")
    return "\n".join(out)


def authread_facts(d, site):
    """authread の設問文候補と真偽。**すべて遍歴から機械導出する**。

    返り値: [(軸, 文, 真偽)]
    """
    a = d["_auth"]
    _dev, _srv, steps, has_list = enable_walk(
        d, site, pw_ok=a["pw_ok"], with_list=a["with_list"])
    first = steps[0]
    second = steps[1] if len(steps) > 1 else None
    last = steps[-1]
    grp = d["grp"]
    con = a["on_console"]
    f = []

    def add(axis, text, truth):
        f.append((axis, text, bool(truth)))

    add("m1", f"method1 として認証サーバ群 {grp} への問い合わせが行われ、"
             f"応答が得られていない。",
        has_list and first[0].startswith("group:") and first[1] == am.ERROR)
    add("m1", f"method1 として認証サーバ群 {grp} への問い合わせが行われ、"
             f"サーバから拒否されている。",
        has_list and first[0].startswith("group:") and first[1] == am.FAIL)
    # ★軸を "list" に統合(監査指摘)。下の「方式リストが構成されていない」と
    #   **恒等的に同値**なので、別軸にすると 2 本同時に出て消去法で解けてしまう。
    add("list", "method1 として enable パスワードによる認証が行われている。",
        not has_list)
    add("m2", "method2 として enable パスワードによる認証が試行され、"
              "成功している。",
        second is not None and second[0] == "enable" and second[1] == am.PASS)
    add("m2", "method2 として enable パスワードによる認証が試行され、"
              "失敗している。",
        second is not None and second[0] == "enable" and second[1] == am.FAIL)
    # ★`has_list` を条件から外す(監査指摘)。方式リストが無い盤面でも遍歴は
    #   1 本だけで、「method2 は試行されていない」は**出力から明白に真**。
    #   誤って錯乱肢に分類すると正しい記述が 3 本ある問題になっていた。
    add("m2", "method2 は試行されていない。", second is None)
    add("list", "特権レベルへの昇格の認証について、方式リストが構成されていない。",
        not has_list)
    add("line", "この操作は、コンソール以外の回線から行われている。", not con)
    add("line", "この操作は、コンソールから行われている。", con)
    add("res", "特権レベルへの昇格は成功している。", last[1] == am.PASS)
    add("res", "特権レベルへの昇格は失敗している。", last[1] != am.PASS)
    return f


def build_choices_authread(d, rnd):
    """★authread(複数選択): enable の debug から方式リストの遍歴を読ませる。

    正解 2 本・錯乱肢 2 本。**同じ軸の文は 1 本ずつ**にする(同軸の文を 2 本入れると
    片方が他方の否定になり、消去法だけで解けてしまう)。
    """
    site = "B" if d["scope"] == "B" else "A"
    facts = authread_facts(d, site)
    trues = [x for x in facts if x[2]]
    falses = [x for x in facts if not x[2]]
    if len(trues) < 2 or len(falses) < 2:
        raise ValueError("aaa authread: 正解/錯乱肢が足りない")

    def pick(pool, n):
        rnd.shuffle(pool)
        got, used = [], set()
        for axis, text, _t in pool:
            if axis in used:
                continue
            used.add(axis)
            got.append(text)
            if len(got) == n:
                return got, used
        return got, used

    # ★正解 2 本が line 軸(port を見るだけ)＋ res 軸(最終 status を見るだけ)に
    #   偏ると、**遍歴を一切読まずに解ける**(監査指摘)。少なくとも 1 本は
    #   遍歴の軸(m1 / m2 / list)から採る。
    WALK = {"m1", "m2", "list"}
    walk_true = [x for x in trues if x[0] in WALK]
    if not walk_true:
        raise ValueError("aaa authread: 遍歴の軸に正解が無い")
    rnd.shuffle(walk_true)
    head = walk_true[0]
    rest = [x for x in trues if x[0] != head[0]]
    t_txt, t_axes = pick(rest, 1)
    t_txt = [head[1]] + t_txt
    t_axes = set(t_axes) | {head[0]}
    if len(t_txt) < 2:
        raise ValueError("aaa authread: 正解の軸が足りない")
    f_pool = [x for x in falses if x[0] not in t_axes]
    f_txt, _ = pick(f_pool, 2)
    if len(f_txt) < 2:                       # 軸が足りなければ同軸も許す
        f_txt, _ = pick(list(falses), 2)
    if len(f_txt) < 2:
        raise ValueError("aaa authread: 錯乱肢が足りない")
    c = [(t, True, "") for t in t_txt]
    c += [(t, False, "示されている出力からは、そのようには読み取れない。")
          for t in f_txt]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def line_vty_block(d, site, kind=None):
    """`show running-config | section line vty`。

    ★`line vty 0 4` と `line vty 5 15` を**常に両方**描く(片方だけ出すと
    その有無が道標になる)。方式リストがどちらに当たっているかが
    `vty_range_partial` の指紋になる。
    """
    dev, _ = build(d, site, kind)
    out = []
    for key, hdr in (("vty", "line vty 0 4"), ("vty_hi", "line vty 5 15")):
        out += [hdr, " exec-timeout 0 0"]
        if dev["line"][key]["login"]:
            out.append(f" login authentication {dev['line'][key]['login']}")
        out.append(" transport input ssh")
    return "\n".join(out)


def line_con_block(d, site, kind=None):
    """`show running-config | section line con`。
    ★console 専用リストの有無がそのまま `console_forgotten` の指紋になる。"""
    dev, _ = build(d, site, kind)
    out = ["line con 0", " exec-timeout 0 0", " logging synchronous"]
    if dev["line"]["con"]["login"]:
        out.append(f" login authentication {dev['line']['con']['login']}")
    if dev["line"]["con"]["authz"]:
        out.append(f" authorization exec {dev['line']['con']['authz']}")
    return "\n".join(out)


def acl_lines(d, site, kind=None):
    """ACL の定義行(構成にもそのまま載る)。遮断していなければ空。

    ★X4/X4b 実測の写像。out は宛先ポート、in は送信元ポートで落とす。
    どちらも機器側の症状は同一で、**この定義とカウンタだけが決め手**になる。
    """
    dev, _ = build(d, site, kind)
    b = dev.get("acl_block")
    if not b:
        return []
    ports = sorted({1812, d["port2"]})
    if b == "out":
        deny = [f" deny   udp any any eq {p}" for p in ports]
    else:
        deny = [f" deny   udp any eq {p} any" for p in ports]
    return [f"ip access-list extended {d['aclname']}"] + deny + \
           [" permit ip any any"]


def acl_block(d, site, kind=None):
    """`show ip access-lists`(★evidence 形の第3の正解クラス)。

    カウンタは 1 トランザクション分= `retransmit + 1`(サーバ 1 台あたりの送出数)。
    遮断していない機器では**何も出さない**(実機どおり。説明文は書かない)。
    """
    lines = acl_lines(d, site, kind)
    if not lines:
        return ""
    n = d["retransmit"] + 1
    out = [f"Extended IP access list {d['aclname']}"]
    seq = 10
    for ln in lines[1:]:
        body = ln.strip()
        hit = f" ({n} matches)" if body.startswith("deny") else " (2 matches)"
        out.append(f"    {seq} {body}{hit}")
        seq += 10
    return "\n".join(out)


def acl_iface_block(d, site, kind=None):
    """ACL を当てているインタフェース(構成側の表示)。"""
    dev, _ = build(d, site, kind)
    b = dev.get("acl_block")
    if not b:
        return []
    return ["interface Ethernet0/0",
            f" ip access-group {d['aclname']} {'out' if b == 'out' else 'in'}"]


def src_iface_block(d, site, kind=None):
    """`show running-config | include radius source-interface`。

    ★src_iface_group_level は**グループ配下にも**行が出るのが指紋(実測 ⑦)。
    """
    kind = d["kind"] if kind is None else kind
    faulted = (d["scope"] in ("both", site))
    k = kind if faulted else None
    if k == "src_iface_missing":
        return ""            # ★実機は該当行が無ければ何も出さない。
                             #   「(該当する行はない)」等の説明文は**道標**であり書かない
                             #   (BL-088 の不変条件。2026-08-08 ユーザ指摘)
    if k == "src_iface_group_level":
        return " ip radius source-interface Loopback0\nip radius source-interface Loopback0"
    return "ip radius source-interface Loopback0"


def cfg_block(d, site, kind=None):
    """紙面に出す当該ルータの AAA 構成。"""
    dev, _ = build(d, site, kind)
    n = d["net"]
    out = ["aaa new-model", "!"]
    for name in ("RAD1", "RAD2"):
        s = dev["servers"][name]
        out += [f"radius server {name}",
                f" address ipv4 {s['ip']} auth-port {s['auth_port']} "
                f"acct-port {s['auth_port'] + 1}",
                f" key {s['key']}", "!"]
    out += [f"aaa group server radius {d['grp']}",
            " server name RAD1", " server name RAD2", " deadtime 5", "!"]
    for m in dev["lists"]["authn"]:
        out.append(f"aaa authentication login {m} "
                   + " ".join(x.replace("group:", "group ")
                              for x in dev["lists"]["authn"][m]))
    for m in dev["lists"].get("enable", {}):
        out.append(f"aaa authentication enable {m} "
                   + " ".join(x.replace("group:", "group ")
                              for x in dev["lists"]["enable"][m]))
    for m in dev["lists"].get("authz", {}):
        out.append(f"aaa authorization exec {m} "
                   + " ".join(x.replace("group:", "group ")
                              for x in dev["lists"]["authz"][m]))
    if dev.get("authz_console"):
        out.append("aaa authorization console")
    out.append("!")
    sb = src_iface_block(d, site, kind)
    if sb:                       # ★行が無い場合は何も出さない(空行も残さない)
        out.append(sb)
    out += [f"radius-server timeout {d['timeout']}",
            f"radius-server retransmit {d['retransmit']}"]
    out += dead_criteria_lines(build(d, site, kind)[0], d)
    out += ["!",
            f"username {d['emg']} privilege 15 secret 5 $1$xxxx",
            f"username {d['auto']} privilege 15 secret 5 $1$yyyy", "!"]
    al = acl_lines(d, site, kind)
    if al:                       # ★ACL 遮断の盤面では定義と適用も構成に現れる
        out += al + ["!"] + acl_iface_block(d, site, kind) + ["!"]
    out.append(line_con_block(d, site, kind))
    out.append(line_vty_block(d, site, kind))
    _ = n
    return "\n".join(out)


# --------------------------------------------------------------------------
# 出題形の素材
# --------------------------------------------------------------------------
def signature(d, kind):
    """★機器側だけで観測できるものの指紋。
    2 つの故障種の指紋が一致する = 機器側では区別できない(evidence 形の前提)。
    """
    return "\n".join([
        render_obs(d, kind),
        trace_block(d, kind),
        aaa_servers_block(d, "A", kind), aaa_servers_block(d, "B", kind),
    ])


def confusable(d, kind=None):
    """指紋が完全一致する別の故障種(= 機器側で区別できない相手)。"""
    kind = d["kind"] if kind is None else kind
    me = signature(d, kind)
    return [k for k in KINDS if k != kind and signature(d, k) == me]


def shown_signature(d, kind):
    """★evidence 形で**実際に提示するもの**だけの指紋(結果表と test aaa)。

    evidence 形は機器の構成も `show aaa servers` も出さないので、
    「読者から見て見分けがつかない候補」はこの弱い指紋で決まる。
    signature() より粗いぶん候補が増え、**3 つ巴**を作れる。
    """
    return "\n".join([render_obs(d, kind), trace_block(d, kind)])


def confusable_shown(d, kind=None):
    kind = d["kind"] if kind is None else kind
    me = shown_signature(d, kind)
    return [k for k in KINDS if k != kind and shown_signature(d, k) == me]


def read_variants(d):
    """read 形: 現在の結果表と、別の故障種における結果表。"""
    cur = render_obs(d)
    alts = []
    for k in KINDS:
        if k == d["kind"]:
            continue
        alts.append((k, render_obs(d, k)))
    return cur, alts


def trace_variants(d):
    cur = trace_block(d)
    alts = [(k, trace_block(d, k)) for k in KINDS if k != d["kind"]]
    return cur, alts


OBSERVATIONS = [
    # ★サーバログは使わない(ENARSI の範囲外で、解答者が差を判断できない=
    #   2026-08-08 ユーザ指摘)。機器側 debug が同じ切り分けを与えることを実測で確認済み。
    ("dbg", "各ルータでの `debug radius authentication`", debug_block),
    ("linevty", "各ルータの `show running-config | section line vty`", line_vty_block),
    ("linecon", "各ルータの `show running-config | section line con`", line_con_block),
    ("srciface", "各ルータの `show running-config | include radius source-interface`",
     src_iface_block),
    ("aaasrv", "各ルータの `show aaa servers`", aaa_servers_block),
    # ★X4/X4b: ACL 遮断は機器側の他の出力と完全に同一なので、ここだけが決め手になる
    ("acl", "各ルータの `show ip access-lists`", acl_block),
    ("testaaa", "各ルータでの `test aaa group {grp} <利用者> <パスワード> legacy`",
     test_aaa_text),
]


def _render_obs(d, fn, kind):
    return "\n".join(fn(d, s, kind) for s in ("A", "B"))


def _hyp_rng(d):
    """盤面から決まる固定シードの乱数(対立仮説の並べ替え用)。"""
    key = "|".join(str(d[k]) for k in
                   ("kind", "world", "scope", "grp", "aclname", "adm", "emg",
                    "port2", "timeout", "retransmit"))
    return random.Random(zlib.crc32(key.encode()))


def evidence_variants(d):
    """evidence 形: 「次に取得すべき出力」。

    ★仮説は**提示物だけでは見分けがつかない候補**(shown_signature 一致)から採る。
    候補が 3 つ取れる盤面では **3 つ巴**にする(消去法封じ)。設問は
    「**最も多くの候補を絞れる出力はどれか**」となり、各観測を
    「その観測の描画が仮説ごとに何通りに割れるか」で機械採点する。

    返り値: (仮説リスト, [(キー,説明,分割数)...正解候補], [同…錯乱肢候補])
    """
    rivals = confusable_shown(d)
    if not rivals:
        raise ValueError("aaa evidence: 見分けのつかない対立仮説が無い")
    # ★対立仮説は KINDS の並び順で先頭から取っていたため、**同じ観測でしか割れない
    #   組(ACL の要求遮断/応答遮断)が同じ盤面に揃わず**、正解が debug に偏っていた
    #   (debug 71% / 構成 29%・`show ip access-lists` は 0%)。→ 盤面から導いた
    #   決定的な乱数で並べ替える(選択肢生成と設問文で同じ順になる必要があるため、
    #   `random.Random()` でも `hash()` でもなく crc32 由来の固定シードを使う)。
    rivals = list(rivals)
    _hyp_rng(d).shuffle(rivals)
    hyps = [d["kind"]] + rivals[:2]
    scored = []
    for key, label, fn in OBSERVATIONS:
        vals = {_render_obs(d, fn, h) for h in hyps}
        scored.append((key, label, len(vals)))
    best = max(x[2] for x in scored)
    if best < 2:
        raise ValueError("aaa evidence: どの観測でも割れない")
    good = [x for x in scored if x[2] == best]
    bad = [x for x in scored if x[2] < best]
    # ★一意性= 「提示した選択肢の中で最も多く割れるものがただ一つ」。
    #   同点の観測が他にあれば、それは**選択肢に出さない**(出すと 2 正解になる)。
    if len(bad) < 3:
        raise ValueError(f"aaa evidence: 錯乱肢が足りない(best={best} bad={len(bad)})")
    return hyps, good, bad


def build_choices_evidence(d, rnd):
    hyps, good, bad = evidence_variants(d)
    n = len(hyps)
    c = [(rnd.choice(good)[1].format(grp=d["grp"]), True, "")]
    for key, label, split in rnd.sample(bad, 3):
        why = ("この出力は、いずれの原因でも同じ内容になるため、切り分けの材料にならない。"
               if split == 1 else
               f"この出力で絞り込めるのは {split} 通りまでであり、"
               f"{n} つの候補を区別するには足りない。")
        c.append((label.format(grp=d["grp"]), False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def dbg_facts(d, site, kind=None):
    """debug 出力から**読み取れる**構成値(★新形 dbgread の正解の材料)。
    実測で debug に現れることを確認した項目だけを扱う(poc/aaa/README.md §13 の表)。"""
    dev, srv = build(d, site, kind)
    lo = d["net"]["loA"] if site == "A" else d["net"]["loB"]
    src = dev["src_addr"]
    m = dev["group"]["members"]
    s1, s2 = dev["servers"][m[0]], dev["servers"][m[1]]
    return {
        "src": src, "has_src_iface": (src == lo),
        "srv1": s1["ip"], "port1": s1["auth_port"],
        "srv2": s2["ip"], "port2": s2["auth_port"],
        "timeout": d["timeout"], "retransmit": d["retransmit"],
        "user": d["adm"],
    }


def _alt_ip(ip, rnd, forbid=()):
    """★実在の値と衝突しない別アドレスを作る(衝突すると誤答肢が真になる)。"""
    for _ in range(50):
        o = ip.split(".")
        o[2] = str((int(o[2]) + rnd.choice([1, 2, 3, 5, 7])) % 250 + 1)
        cand = ".".join(o)
        if cand != ip and cand not in forbid:
            return cand
    return "10.255.255.255"


def build_choices_dbgread(d, rnd):
    """★dbgread(ユーザ要望): debug の出力から構成値を推測させる。

    正解・錯乱肢とも **debug に実際に現れる項目**からのみ作り、
    真偽は dbg_facts() で機械的に決める(手書きの排他表は作らない)。
    """
    site = "B" if d["scope"] == "B" else "A"
    f = dbg_facts(d, site)
    # ★正解は「出力から読み取れる」事実に限る(監査2)。再送回数は
    #   Retransmit 行が出力に現れない盤面(1台目が即応答)では読み取れない。
    dbg = debug_block(d, site)
    true_pool = [
        (f"認証要求の送信元アドレスは {f['src']} である。", True),
        (f"1 台目の認証サーバとして {f['srv1']} のポート {f['port1']} が"
         f"設定されている。", True),
        (f"要求のタイムアウトは {f['timeout']} 秒に設定されている。", True),
    ]
    if "Retransmit to" in dbg:
        true_pool.append((f"要求の再送は 1 回の送信につき {f['retransmit']} 回"
                          f"行われる。", True))
    if f["has_src_iface"]:
        true_pool.append(("認証要求の送信元となるインタフェースが、"
                          "明示的に指定されている。", True))
    else:
        true_pool.append(("認証要求の送信元となるインタフェースは、"
                          "明示的に指定されていない。", True))
    reals = {f["src"], f["srv1"], f["srv2"],
             d["net"]["loA"], d["net"]["loB"], d["net"]["egA"], d["net"]["egB"]}
    false_pool = [
        (f"認証要求の送信元アドレスは {_alt_ip(f['src'], rnd, reals)} である。", False),
        (f"1 台目の認証サーバとして {f['srv1']} のポート "
         f"{1812 if f['port1'] != 1812 else 1645} が設定されている。", False),
        (f"要求のタイムアウトは {f['timeout'] + rnd.choice([1, 2, 3])} 秒に"
         f"設定されている。", False),
        # (再送の誤答肢も Retransmit 行が見えるときだけ意味を持つ→下で条件付き追加)
        (f"2 台目の認証サーバとして {_alt_ip(f['srv2'], rnd, reals)} が"
         f"設定されている。", False),
        (("認証要求の送信元となるインタフェースは、明示的に指定されていない。"
          if f["has_src_iface"] else
          "認証要求の送信元となるインタフェースが、明示的に指定されている。"), False),
    ]
    if "Retransmit to" in dbg:
        false_pool.append((f"要求の再送は 1 回の送信につき "
                           f"{f['retransmit'] + 2} 回行われる。", False))
    truths = {t for t, _ in true_pool}
    false_pool = [x for x in false_pool if x[0] not in truths]
    if len(false_pool) < 3:
        raise ValueError("aaa dbgread: 錯乱肢が足りない")
    c = [(rnd.choice(true_pool)[0], True, "")]
    for txt, _ in rnd.sample(false_pool, 3):
        c.append((txt, False, "示されている出力の値と一致しない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CLAIMS = {
    "user_not_registered": "認証サーバの利用者台帳に当該利用者が登録されていない。",
    "key_mismatch": "ルータと認証サーバの共有鍵が一致していない。",
    "src_iface_missing": "認証要求の送信元アドレスが、サーバ側で許可された値になっていない。",
    "src_iface_group_level": "送信元の指定がサーバグループ配下に残っている。",
    "port_mismatch": "ルータが指定している待受ポートがサーバの実際の値と異なる。",
    "no_authz_exec": "exec の認可が構成されていない。",
    "deadtime_only": "応答しないサーバを判定する条件が構成されていないため、"
                     "そのサーバが問い合わせ先から外れない。",
    "authz_no_fallback": "exec の認可に代替手段が構成されていない。",
    "list_not_applied": "作成した方式リストが回線に適用されていない。",
    "list_undefined": "回線が参照している方式リストが定義されていない。",
    "enable_via_radius": "特権レベルへの昇格の認証が認証サーバ経由になっている。",
    "console_forgotten": "コンソール回線に専用の方式リストが適用されていない。",
    # ★X5/X6/X11/X12 実測。回線に `authorization exec` を書いても、
    #   グローバルの有効化が無ければ認可は走らず、権限レベルは 1 に留まる。
    "authz_console_missing": "コンソール回線に対する認可が有効化されていない。",
    # ★X1/X2 実測。認可の代替手段が属性を与えないため、フォールバック時に priv 1 になる。
    "authz_if_authenticated": "exec の認可の代替手段が、権限レベルを与えないものになっている。",
    # ★X4/X4b 実測。機器側の症状はサーバ停止と同一で、決め手は ACL のカウンタのみ。
    "vty_range_partial": "方式リストが、一部の vty 回線にしか適用されていない。",
    "acl_block_request": "アクセスリストが、認証要求の送信を遮断している。",
    "acl_block_reply": "アクセスリストが、認証サーバからの応答を遮断している。",
}


# --------------------------------------------------------------------------
# dbgconf 形 — 逆問題「この debug を生じさせる構成はどれか」(BL-103 ①)
# --------------------------------------------------------------------------
# 既存の dbgread が「出力から値を 1 つ読む」形なのに対し、こちらは
# **出力全体と構成の対応**を取らせる。debug_render() が dev の純関数である性質を
# 使い、候補構成それぞれから debug を描き直して「示された出力と一致するものが
# ちょうど 1 つ」であることを機械検証する(被覆エンジン方式の debug 版)。
def transport_cfg(d, dev, site):
    """dbgconf の選択肢本体。**debug が明かす範囲の構成だけ**を描く。

    方式リスト・line・鍵の値そのものは debug から読み取れないので、
    どの候補でも同一にする(差は出力に現れる値だけに限る)。
    """
    lo = d["net"]["loA"] if site == "A" else d["net"]["loB"]
    out = []
    for name in ("RAD1", "RAD2"):
        s = dev["servers"][name]
        out += [f"radius server {name}",
                f" address ipv4 {s['ip']} auth-port {s['auth_port']} "
                f"acct-port {s['auth_port'] + 1}",
                f" key {s['key']}", "!"]
    out.append(f"aaa group server radius {d['grp']}")
    for name in dev["group"]["members"]:
        out.append(f" server name {name}")
    out += [" deadtime 5", "!"]
    if dev["src_addr"] == lo:
        out.append("ip radius source-interface Loopback0")
    out += [f"radius-server timeout {dev['timeout']}",
            f"radius-server retransmit {dev['retransmit']}"]
    out += dead_criteria_lines(dev, d)
    return "\n".join(out)


def _alt_port(cur, rnd):
    return rnd.choice([p for p in (1812, 1645, 1912, 1700) if p != cur])


def _dbgconf_candidates(d, dev, site, rnd):
    """候補構成を作る。**debug に現れうる値だけ**を動かす。

    現れない値(鍵・方式リスト)を動かしても出力が変わらず、解答者が
    反証できない選択肢になるため、軸から外している。
    """
    lo = d["net"]["loA"] if site == "A" else d["net"]["loB"]
    eg = d["net"]["egA"] if site == "A" else d["net"]["egB"]
    out = []

    def mk(tag, fn):
        c = copy.deepcopy(dev)
        fn(c)
        out.append((tag, c))

    def flip_src(c):
        c["src_addr"] = eg if c["src_addr"] == lo else lo

    def bump_timeout(c):
        c["timeout"] = c["timeout"] + rnd.choice([1, 2, 3])

    def bump_retrans(c):
        c["retransmit"] = c["retransmit"] + 1

    def port1(c):
        c["servers"]["RAD1"]["auth_port"] = _alt_port(
            c["servers"]["RAD1"]["auth_port"], rnd)

    def port2(c):
        c["servers"]["RAD2"]["auth_port"] = _alt_port(
            c["servers"]["RAD2"]["auth_port"], rnd)

    def ip2(c):
        c["servers"]["RAD2"]["ip"] = _alt_ip(
            c["servers"]["RAD2"]["ip"], rnd,
            {d["net"]["srv1"], d["net"]["srv2"], lo, eg})

    def swap(c):
        c["group"]["members"] = list(reversed(c["group"]["members"]))

    # ★tag="spec" = サーバ仕様表と食い違う候補。これだけで選択肢を埋めると
    #   「仕様表と一致する構成を選ぶ」だけで解けてしまい、debug を読まなくなる
    #   (仕様表と構成が食い違うこと自体が port_mismatch の正体なので、
    #    その照合は本来この設問の根拠にならない)。→ 呼び出し側で 1 本までに絞る。
    for tag, fn in (("dbg", flip_src), ("dbg", bump_timeout),
                    ("dbg", bump_retrans), ("spec", port1), ("spec", port2),
                    ("spec", ip2), ("dbg", swap)):
        mk(tag, fn)
    return out


def _diff_why(truth, cand):
    """候補構成の出力が示された出力と食い違う理由を機械導出する。

    ★行の中身が同じでも**出現回数**が違うだけのことがある(再送回数など)。
    候補側の行だけを引用すると「示された出力にも在る行」を根拠に挙げてしまい、
    解説が意味を成さない(実装時に検出)。**両者の同じ位置の行を並べて示す**。
    """
    a, b = truth.splitlines(), cand.splitlines()
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else None
        y = b[i] if i < len(b) else None
        if x == y:
            continue
        n = i + 1
        if y is None:
            return f"出力が {n} 行目より前で終わり、示されている出力より短くなる。"
        if x is None:
            return f"{n} 行目以降に `{y}` が続き、示されている出力より長くなる。"
        return (f"{n} 行目が `{y}` になる"
                f"(示されている出力では `{x}`)。")
    return "出力に差が生じない。"


def build_choices_dbgconf(d, rnd):
    """dbgconf 形: 正解 = 実際の構成。錯乱肢 = **描き直すと出力が変わる**構成。"""
    site = "B" if d["scope"] == "B" else "A"
    dev, srv = build(d, site)
    truth_dbg = debug_render(d, dev, srv, site)
    truth_cfg = transport_cfg(d, dev, site)
    pool = {"dbg": [], "spec": []}
    seen = {truth_cfg}
    for tag, cdev in _dbgconf_candidates(d, dev, site, rnd):
        dbg = debug_render(d, cdev, srv, site)
        if dbg == truth_dbg:
            continue                 # 出力が同じ = 解答者が反証できない → 使わない
        txt = transport_cfg(d, cdev, site)
        if txt in seen:
            continue
        seen.add(txt)
        pool[tag].append((txt, False,
                          "この構成では " + _diff_why(truth_dbg, dbg)))
    rnd.shuffle(pool["dbg"])
    rnd.shuffle(pool["spec"])
    cands = pool["dbg"][:3]
    if len(cands) < 3:                   # 足りない分だけ仕様食い違い型で埋める
        cands += pool["spec"][:3 - len(cands)]
    elif pool["spec"]:                   # 1 本だけ混ぜて型を単調にしない
        cands[2] = pool["spec"][0]
    if len(cands) < 3:
        raise ValueError("aaa dbgconf: 錯乱肢が足りない")
    c = [(truth_cfg, True, "")] + cands[:3]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_cause(d, rnd):
    """cause 形: 正解 = 現在の故障種。錯乱肢は**指紋が異なる**種別から採る
    (指紋が同じ相手を混ぜると 2 正解になるため)。"""
    conf = set(confusable(d))
    pool = [k for k in KINDS if k != d["kind"] and k not in conf]
    if len(pool) < 3:
        raise ValueError("aaa cause: 錯乱肢が足りない")
    c = [(CLAIMS[d["kind"]], True, "")]
    for k in rnd.sample(pool, 3):
        c.append((CLAIMS[k], False, "観測されている出力とは両立しない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# P1b: fix 形 — 是正手段の選択(★被覆エンジン方式= 直る候補≥2・要件適合=1)
# --------------------------------------------------------------------------
# 各候補= (説明, CLI 行, 適用関数, サーバ側を触るか, 既定リストを触るか)
# ★CLI は**状態収束形**で出す(上乗せでもモデルの絶対状態に到達すること。BL-095 の教訓)。
# ★AAA は `no` の構文が素直でない(`no ip radius source-interface` 単独は
#   `% Incomplete command.`)ので、CLI 文字列は実機の受理形に合わせる。

def _srv_all(srv, fn):
    for s in srv.values():
        fn(s)


FIXES = {}


def _fix(key, label, cli, apply, srv_side=False, default_side=False):
    FIXES[key] = {"label": label, "cli": cli, "apply": apply,
                  "srv": srv_side, "default": default_side}


_fix("set_key", "ルータ側の共有鍵を、仕様書の値に合わせる。",
     lambda d, site: [f"radius server RAD1", f" key {d['key']}", " exit",
                      f"radius server RAD2", f" key {d['key']}", " exit"],
     lambda dev, srv, d: [dev["servers"][n].update(key=d["key"])
                          for n in dev["servers"]])
_fix("srv_key", "認証サーバ側の共有鍵を、ルータの値に合わせる。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: _srv_all(srv, lambda s: s.update(
         key=list(dev["servers"].values())[0]["key"])), srv_side=True)
_fix("set_dead_criteria",
     "応答しないサーバを「応答不能」と判定する条件を構成する。",
     lambda d, site: [f"radius-server dead-criteria time {d['timeout']} tries 1"],
     lambda dev, srv, d: dev.update(dead_criteria=True))
_fix("set_src", "認証要求の送信元を、Loopback0 に固定する。",
     lambda d, site: ["ip radius source-interface Loopback0"],
     lambda dev, srv, d: dev.update(
         src_addr=(d["net"]["loA"] if dev["_site"] == "A" else d["net"]["loB"])))
_fix("srv_client_add", "認証サーバ側で、物理インタフェースのアドレスを許可する。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: _srv_all(srv, lambda s: s["clients"].append(
         dev["src_addr"])), srv_side=True)
_fix("set_port", "ルータ側の待受ポートの指定を、仕様書の値に合わせる。",
     lambda d, site: [f"radius server RAD2",
                      f" address ipv4 {d['net']['srv2']} auth-port {d['port2']}"
                      f" acct-port {d['port2'] + 1}", " exit"],
     lambda dev, srv, d: dev["servers"]["RAD2"].update(auth_port=d["port2"]))
_fix("srv_port", "認証サーバ側の待受ポートを、ルータの指定に合わせる。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: srv["RAD2"].update(
         auth_port=dev["servers"]["RAD2"]["auth_port"]), srv_side=True)
_fix("add_authz", "既定の方式リストに、exec の認可を構成する。",
     lambda d, site: [f"aaa authorization exec default group {d['grp']} local"],
     lambda dev, srv, d: dev["lists"]["authz"].update(
         default=[f"group:{d['grp']}", "local"]), default_side=True)
_fix("authz_named", "認可の名前付きリストを作成し、回線に適用する。",
     lambda d, site: [f"aaa authorization exec {d['listname']} group {d['grp']} local",
                      "line vty 0 4",
                      f" authorization exec {d['listname']}", " exit"],
     lambda dev, srv, d: (dev["lists"]["authz"].update(
         **{d["listname"]: [f"group:{d['grp']}", "local"]}),
         dev["line"]["vty"].update(authz=d["listname"])))
_fix("apply_list", "作成済みの方式リストを、回線に適用する。",
     lambda d, site: ["line vty 0 4",
                      f" login authentication {d['listname']}", " exit"],
     lambda dev, srv, d: dev["line"]["vty"].update(login=d["listname"]))
_fix("apply_list_all_vty", "作成済みの方式リストを、すべての vty 回線に適用する。",
     lambda d, site: ["line vty 0 15",
                      f" login authentication {d['listname']}", " exit"],
     lambda dev, srv, d: (dev["line"]["vty"].update(login=d["listname"]),
                          dev["line"]["vty_hi"].update(login=d["listname"])))
_fix("define_list", "回線が参照している方式リストを、定義する。",
     lambda d, site: [f"aaa authentication login {d['badlist']} "
                      f"group {d['grp']} local"],
     lambda dev, srv, d: dev["lists"]["authn"].update(
         **{d["badlist"]: [f"group:{d['grp']}", "local"]}))
_fix("default_to_group", "既定の方式リストで、認証サーバ群を用いるようにする。",
     lambda d, site: [f"aaa authentication login default group {d['grp']} local"],
     lambda dev, srv, d: dev["lists"]["authn"].update(
         default=[f"group:{d['grp']}", "local"]), default_side=True)
_fix("srv_add_user", "認証サーバの利用者台帳に、当該利用者を登録する。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: _srv_all(srv, lambda s: s["users"].update(
         {d["adm"]: 15})), srv_side=True)
_fix("local_first_add", "当該利用者をローカルに登録し、"
                        "既定の方式リストでローカルを先に評価する。",
     lambda d, site: [f"username {d['adm']} privilege 15 secret <パスワード>",
                      f"aaa authentication login default local group {d['grp']}"],
     lambda dev, srv, d: (dev["local"].update({d["adm"]: 15}),
                          dev["lists"]["authn"].update(
                              default=["local", f"group:{d['grp']}"])),
     default_side=True)
_fix("authz_add_local", "exec の認可に、ローカルによる代替手段を加える。",
     lambda d, site: [f"aaa authorization exec default group {d['grp']} local"],
     lambda dev, srv, d: dev["lists"]["authz"].update(
         default=[f"group:{d['grp']}", "local"]), default_side=True)
_fix("no_enable_list", "特権レベルへの昇格の認証を、既定の動作に戻す。",
     lambda d, site: [f"no aaa authentication enable default group {d['grp']} enable"],
     lambda dev, srv, d: dev["lists"].update(enable={}),
     default_side=True)      # ★enable の default 方式リストを削除する= 既定リストの変更(監査)
_fix("srv_add_enab", "認証サーバに、昇格用の利用者を登録する。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: _srv_all(srv, lambda s: s["users"].update(
         {"$enab15$": 15})), srv_side=True)
_fix("add_console_list", "コンソール専用の方式リストを作成し、コンソール回線に適用する。",
     lambda d, site: [f"aaa authentication login {CONSOLE_LIST} local",
                      f"aaa authorization exec {CONSOLE_LIST} local",
                      "line con 0",
                      f" login authentication {CONSOLE_LIST}",
                      f" authorization exec {CONSOLE_LIST}", " exit"],
     lambda dev, srv, d: (dev["lists"]["authn"].update(
         **{CONSOLE_LIST: ["local"]}),
         dev["lists"]["authz"].update(**{CONSOLE_LIST: ["local"]}),
         dev["line"]["con"].update(login=CONSOLE_LIST, authz=CONSOLE_LIST)))
_fix("enable_authz_console", "コンソール回線に対する認可を、有効化する。",
     lambda d, site: ["aaa authorization console"],
     lambda dev, srv, d: dev.update(authz_console=True))
_fix("srv_add_emg", "認証サーバの台帳に、緊急用の利用者を登録する。",
     lambda d, site: ["(認証サーバ側の設定変更)"],
     lambda dev, srv, d: _srv_all(srv, lambda s: s["users"].update(
         {d["emg"]: 15})), srv_side=True)
# ★「やっても直らない/要件を満たさない」錯乱肢(P0 実測に基づく)
_fix("add_cmd_acct", "コマンド単位の課金を構成する。",
     lambda d, site: [f"aaa accounting commands 15 default start-stop "
                      f"group {d['grp']}"],
     lambda dev, srv, d: None)
_fix("del_global_src", "送信元インタフェースの指定を削除する。",
     lambda d, site: ["no ip radius source-interface Loopback0"],
     lambda dev, srv, d: dev.update(
         src_addr=(d["net"]["egA"] if dev["_site"] == "A" else d["net"]["egB"])))


def _apply(d, site, key):
    dev, srv = build(d, site)
    dev["_site"] = site
    if key:
        FIXES[key]["apply"](dev, srv, d)
    return dev, srv


def _obs_sig(dev, srv, d):
    """是正の判定に使う観測。

    ★**紙面に出す行と同一の定義**(`site_rows`)を使う。ここが提示とずれると、
    故障が判定側から見えず**どの候補でも「直った」ことになる**
    (`authz_no_fallback` / `vty_range_partial` で実際に起きた)。
    """
    return "|".join(f"{u}={r}" for u, r in site_rows(dev, srv, d))


def _obs_after(d, site, key, all_down=False):
    dev, srv = _apply(d, site, key)
    if all_down:
        for s in srv.values():
            s["alive"] = False
    return _obs_sig(dev, srv, d)


def _obs_healthy(d, site, all_down=False):
    dev, srv = build(d, site, kind="__none__")
    dev["_site"] = site
    if all_down:
        for s in srv.values():
            s["alive"] = False
    return _obs_sig(dev, srv, d)


def fix_works(d, key):
    """★是正後の観測が「健全な基準状態」と一致すること。

    実装当初は「管理者が権限 15 でログインできるか」だけを見ていたが、それでは
    **潜在故障**(authz_no_fallback / console_forgotten / enable_via_radius)を
    直したかどうか判定できず、**あらゆる候補が正解になってしまった**
    (P1b 実装時に検出)。→ vty 3 名 + 特権昇格 + console の観測を、
    **平常時と「サーバ全断」時の両方**で健全盤面と突き合わせる。

    さらに要件「認証は認証サーバ群を用いること」を機械化する: 管理者の認証が
    **ローカルで通ってしまう**手段(ローカル登録で迂回する等)は不適合とする。
    """
    for site in ("A", "B"):
        for down in (False, True):
            if _obs_after(d, site, key, down) != _obs_healthy(d, site, down):
                return False
        dev, srv = _apply(d, site, key)
        r = am.login(dev, srv, d["adm"])
        if r["result"] != am.OK or r["why"] != "radius":
            return False        # ★サーバ群を用いていない = 要件 2 に反する
    return True


def fix_complies(d, key):
    """要件世界(制約)に適合する手段か。"""
    f = FIXES[key]
    w = d["world"]
    if w == "server_frozen" and f["srv"]:
        return False
    if w == "default_frozen" and f["default"]:
        return False
    return True


def fix_candidates(d):
    """(直る候補, 直らない候補) を返す。"""
    ok = [k for k in FIXES if fix_works(d, k)]
    ng = [k for k in FIXES if k not in ok]
    return ok, ng


def verify_fix(d):
    """★被覆エンジン: 直る候補が 2 つ以上あり、そのうち要件に適合するのは 1 つだけ。"""
    ok, ng = fix_candidates(d)
    good = [k for k in ok if fix_complies(d, k)]
    if len(ok) < 2 or len(good) != 1 or len(ng) < 3:
        raise ValueError(f"aaa fix: 成立しない(直る={len(ok)} 適合={len(good)} "
                         f"直らない={len(ng)})")
    return good[0], ok, ng


def fix_world(d):
    """★この盤面で fix 形が一意に立つ要件世界を返す(無ければ None)。

    多くの故障は「ルータ側で直す/サーバ側で直す」の 2 通りが等しく有効なので、
    世界(制約)が無いと正解が決まらない。世界は盤面の一部なので、
    fix 形を出すときは**成立する世界を選び直す**。
    """
    for w in WORLDS:
        if w not in compatible_worlds(d):
            continue
        cand = dict(d, world=w)
        try:
            verify_fix(cand)
            return w
        except ValueError:
            continue
    return None


def _cli_text(d, key):
    """選択肢の本文。★サーバ側の手段は CLI を持たないので**文**で提示する
    (プレースホルダをそのまま出していた初回出題の検分で修正)。"""
    if FIXES[key]["srv"]:
        return FIXES[key]["label"]
    site = "B" if d["scope"] == "B" else "A"
    return "\n".join(FIXES[key]["cli"](d, site))


def _fix_why(d, k, others):
    """錯乱肢の理由文を機械導出する(監査7)。当初は ng を一律「事象は解消しない」と
    説明していたが、**症状は直るのに他の理由で不適合**な候補(ローカル迂回など)が
    多数あり、解説として不正確だった。"""
    if k in others:
        return "この手段では、示されている要件に反する。"
    cured = True
    via_local = False
    for site in ("A", "B"):
        dev, srv = _apply(d, site, k)
        r = am.login(dev, srv, d["adm"])
        if not (r["result"] == am.OK and r["priv"] == 15):
            cured = False
            break
        if r["why"] != "radius":
            via_local = True
    if not cured:
        return "この手段では、報告されている事象は解消しない。"
    if via_local:
        return ("この手段では、当該利用者の認証が認証サーバ群で行われなくなるため、"
                "要件を満たさない。")
    return "この手段では、他の利用者または回線の動作が要求される状態から外れる。"


def build_choices_fix(d, rnd):
    good, ok, ng = verify_fix(d)
    others = [k for k in ok if k != good]          # 直るが要件に反する
    pool = rnd.sample(ng, min(2, len(ng)))
    pool += rnd.sample(others, min(1, len(others)))
    while len(pool) < 3:
        rest = [k for k in ng if k not in pool]
        if not rest:
            break
        pool.append(rnd.choice(rest))
    c = [(_cli_text(d, good), True, "")]
    for k in pool[:3]:
        why = _fix_why(d, k, others)
        c.append((_cli_text(d, k), False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# P1b: patch 形 — ★「切らずに移行する順序」を問う(no_lockout 世界の専用形)
# --------------------------------------------------------------------------
# 盤面= ローカル認証から認証サーバ群への移行の**途中**。前提作業が 1 つ欠けており、
# その状態で既定の方式リストを切り替えると**運用者が締め出される**。
# 正解= 「今すぐ投入しても誰も切れず、かつ**切替を安全にする**コマンド」。
# 一意性は機械判定する(手書きの順序表は作らない)。

PATCH_MISSING = ["srv_user", "console_list"]


def patch_build(d, site):
    """移行途中の状態を作る。"""
    dev, srv = build(d, site, kind="__none__")
    dev["_site"] = site
    dev["lists"]["authn"]["default"] = ["local"]        # まだ移行していない
    dev["lists"]["authz"]["default"] = ["local"]
    dev["local"][d["adm"]] = 15                          # 運用者はローカルに居る
    if d.get("patch_missing") == "srv_user":
        for s in srv.values():
            s["users"].pop(d["adm"], None)               # 台帳へ未登録
    else:
        for t in ("authn", "authz"):                     # console 専用リストが未整備
            dev["lists"][t].pop(CONSOLE_LIST, None)
        dev["line"]["con"].update(login=None, authz=None)
    return dev, srv


def _protected(d):
    """★移行中に失ってはならない経路。

    「今通っている経路が全て残ること」を条件にすると成立しない。移行すれば
    **緊急用のローカル口は VTY からは入れなくなる**(認証サーバが権威になるため)が、
    それは意図した結果であって締め出しではない(P1b 実装時に判明)。
    守るべきは **運用者と自動化の VTY** と **緊急用のコンソール**。
    """
    return [(d["adm"], "vty"), (d["auto"], "vty"),
            (d["emg"], "con"), (d["auto"], "con")]


def _access_map(dev, srv, d):
    """保護対象の経路が通っているか(締め出し判定の基準)。"""
    out = {}
    for u, line in _protected(d):
        r = am.login(dev, srv, u, line=line)
        out[(u, line)] = (r["result"], r["priv"])
    return out


PATCHES = {
    "sw_default": ("既定の方式リストを、認証サーバ群を用いる構成に切り替える。",
                   lambda d: [f"aaa authentication login default group {d['grp']} local",
                              f"aaa authorization exec default group {d['grp']} local"],
                   lambda dev, srv, d: (
                       dev["lists"]["authn"].update(
                           default=[f"group:{d['grp']}", "local"]),
                       dev["lists"]["authz"].update(
                           default=[f"group:{d['grp']}", "local"]))),
    "reg_user": ("認証サーバの利用者台帳に、運用者を登録する。",
                 lambda d: ["(認証サーバ側の設定変更)"],
                 lambda dev, srv, d: _srv_all(srv, lambda s: s["users"].update(
                     {d["adm"]: 15}))),
    "mk_console": ("コンソール専用の方式リストを作成し、コンソール回線に適用する。",
                   lambda d: [f"aaa authentication login {CONSOLE_LIST} local",
                              f"aaa authorization exec {CONSOLE_LIST} local",
                              "line con 0",
                              f" login authentication {CONSOLE_LIST}",
                              f" authorization exec {CONSOLE_LIST}", " exit"],
                   lambda dev, srv, d: (
                       dev["lists"]["authn"].update(**{CONSOLE_LIST: ["local"]}),
                       dev["lists"]["authz"].update(**{CONSOLE_LIST: ["local"]}),
                       dev["line"]["con"].update(login=CONSOLE_LIST,
                                                 authz=CONSOLE_LIST))),
    "authz_only": ("exec の認可を、認証サーバ群のみで行う構成にする。",
                   lambda d: [f"aaa authorization exec default group {d['grp']}"],
                   lambda dev, srv, d: dev["lists"]["authz"].update(
                       default=[f"group:{d['grp']}"])),
    "del_src": ("送信元インタフェースの指定を削除する。",
                lambda d: ["no ip radius source-interface Loopback0"],
                lambda dev, srv, d: dev.update(
                    src_addr=(d["net"]["egA"] if dev["_site"] == "A"
                              else d["net"]["egB"]))),
    "cmd_acct": ("コマンド単位の課金を構成する。",
                 lambda d: [f"aaa accounting commands 15 default start-stop "
                            f"group {d['grp']}"],
                 lambda dev, srv, d: None),
}


def _patch_apply(d, site, keys):
    dev, srv = patch_build(d, site)
    base = _access_map(dev, srv, d)
    for k in keys:
        PATCHES[k][2](dev, srv, d)
    return dev, srv, base


def patch_safe(d, keys):
    """今通っている経路が、投入後も全て通ること(=誰も切れない)。"""
    for site in ("A", "B"):
        dev, srv, base = _patch_apply(d, site, keys)
        after = _access_map(dev, srv, d)
        for k, v in base.items():
            if v[0] == am.OK and after[k][0] != am.OK:
                return False
    return True


def patch_unblocks(d, key):
    """★そのコマンドを入れると、**切替(sw_default)が安全になる**か。

    ★「誰も切れない」だけでは足りない: 認証サーバを**壊して**しまえば、
    切替後も local へ落ちるので誰も切れず、判定を通ってしまう
    (実装当初 `del_src` が全ケースで正解になった)。
    → 切替後に**運用者が実際に認証サーバで認証されている**ことも要求する。
    """
    if not patch_safe(d, [key, "sw_default"]):
        return False
    for site in ("A", "B"):
        dev, srv, _ = _patch_apply(d, site, [key, "sw_default"])
        r = am.login(dev, srv, d["adm"])
        if r["result"] != am.OK or r["why"] != "radius":
            return False
    return True


def verify_patch(d):
    """一意性= 「今入れても切れない」かつ「切替を安全にする」候補がただ 1 つ。"""
    good, bad = [], []
    for k in PATCHES:
        if k == "sw_default":
            bad.append(k)
            continue
        if patch_safe(d, [k]) and patch_unblocks(d, k):
            good.append(k)
        else:
            bad.append(k)
    if len(good) != 1 or len(bad) < 3:
        raise ValueError(f"aaa patch: 成立しない(適合={good} 他={len(bad)})")
    return good[0], bad


def _patch_text(d, key):
    """patch の選択肢本文。★サーバ側の作業は CLI を持たないので文で提示する。"""
    lines = PATCHES[key][1](d)
    if lines == ["(認証サーバ側の設定変更)"]:
        return PATCHES[key][0]
    return "\n".join(lines)


def build_choices_patch(d, rnd):
    good, bad = verify_patch(d)
    c = [(_patch_text(d, good), True, "")]
    for k in rnd.sample(bad, 3):
        why = ("この時点で投入すると、現在通っている経路が失われる。"
               if not patch_safe(d, [k]) else
               "この手段では、切り替えを安全に行えるようにはならない。")
        c.append((_patch_text(d, k), False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_patchseq(d, rnd):
    """★BL-123(2026-08-16 ユーザ指摘): (順番, 操作) ペアの複数選択形。

    patch 形(次の一手)は「暗黙の手順列のどこに現在地があるか」の推定と
    次手選定が混在し、不公平感が出る(20260815-003 で実害)。本形は手順列
    そのものを構築させる= 「①(最初に)」「②(その後に)」を冠した操作から
    正しい2つを選ぶ。正解= {①=欠けている前提作業, ②=切替}。
    ★成立条件= 切替単独が unsafe であること(さもなければ順序が任意になり
    ②切替の一意性が崩れる)。機械判定は patch_safe / patch_unblocks を流用。
    """
    good, bad = verify_patch(d)
    if patch_safe(d, ["sw_default"]):
        raise ValueError("aaa patchseq: 切替単独が安全=順序問題が成立しない")
    sw_label = PATCHES["sw_default"][0]
    noise = [k for k in bad if k != "sw_default"]
    rnd.shuffle(noise)

    def pos(n, txt):
        return (f"①(最初に) {txt}" if n == 1 else f"②(その後に) {txt}")

    c = [
        (pos(1, PATCHES[good][0]), True, ""),
        (pos(2, sw_label), True, ""),
        (pos(1, sw_label), False,
         "①に置くと、前提が欠けたまま認証サーバが権威になり、"
         "現在通っている経路が失われる。"),
        (pos(2, PATCHES[good][0]), False,
         "順序が誤り。前提の作業は、切替よりも前に、完了していなければ"
         "ならない(②に置くと、①に切替が先行し、その時点で締め出される)。"),
        (pos(1, PATCHES[noise[0]][0]), False,
         ("この時点で投入すると、現在通っている経路が失われる。"
          if not patch_safe(d, [noise[0]]) else
          "この操作では、切替を安全に行えるようにはならない。")),
        (pos(2, PATCHES[noise[1]][0]), False,
         ("この時点で投入すると、現在通っている経路が失われる。"
          if not patch_safe(d, [good, noise[1]]) else
          "この操作は、移行の完了に寄与しない(切替が行われないまま残る)。")),
    ]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def patch_state_block(d, site):
    """patch 形で提示する現在の構成。"""
    dev, _ = patch_build(d, site)
    out = ["aaa new-model", "!"]
    for name in ("RAD1", "RAD2"):
        sd = dev["servers"][name]
        out += [f"radius server {name}",
                f" address ipv4 {sd['ip']} auth-port {sd['auth_port']} "
                f"acct-port {sd['auth_port'] + 1}", f" key {sd['key']}", "!"]
    out += [f"aaa group server radius {d['grp']}",
            " server name RAD1", " server name RAD2", " deadtime 5", "!"]
    for t, cmd in (("authn", "aaa authentication login"),
                   ("authz", "aaa authorization exec")):
        for m, meth in dev["lists"][t].items():
            out.append(f"{cmd} {m} "
                       + " ".join(x.replace("group:", "group ") for x in meth))
    out += ["!", "ip radius source-interface Loopback0", "!",
            f"username {d['adm']} privilege 15 secret 5 $1$zzzz",
            f"username {d['emg']} privilege 15 secret 5 $1$xxxx",
            f"username {d['auto']} privilege 15 secret 5 $1$yyyy", "!"]
    # ★line con は**移行途中の状態(dev)から**描く。line_con_block() は元の kind から
    #   描くため、console 専用リストが未整備の枝で「存在しないリストへの参照」だけが
    #   残る不整合が出ていた(初回出題の検分で検出)。
    con = ["line con 0", " exec-timeout 0 0", " logging synchronous"]
    if dev["line"]["con"]["login"]:
        con.append(f" login authentication {dev['line']['con']['login']}")
    if dev["line"]["con"]["authz"]:
        con.append(f" authorization exec {dev['line']['con']['authz']}")
    out.append("\n".join(con))
    # ★vty は 2 レンジとも描く(他の形と揃える。片方だけだと構成の見え方が
    #   形ごとに変わり、`vty_range_partial` の指紋の読み方が定まらない)。
    for hdr in ("line vty 0 4", "line vty 5 15"):
        out.append(f"{hdr}\n exec-timeout 0 0\n transport input ssh")
    return "\n".join(out)


def verify_choices(d):
    """この盤面で P1a の 4 形が成立するかを検査する(成立しなければ ValueError)。"""
    cur, alts = read_variants(d)
    if not [t for _, t in alts if t != cur]:
        raise ValueError("aaa read: 結果表が畳まれる")
    tcur, talts = trace_variants(d)
    if not [t for _, t in talts if t != tcur]:
        raise ValueError("aaa trace: 観測が畳まれる")
    build_choices_cause(d, random.Random(0))
    return d


def requirements(d, form=None):
    w = d["world"]
    base = [f"{d['site']['A']}・{d['site']['B']} の両拠点で、"
            f"利用者 {d['adm']} が権限レベル 15 で機器を操作できること。",
            f"認証は認証サーバ群 {d['grp']} を用いること。"]
    extra = {
        "default_frozen": ["既定の方式リストは変更しないこと。"],
        "console_survives": ["認証サーバが全て停止した場合でも、"
                             "コンソールからは操作できること。"],
        "server_frozen": ["認証サーバ側の設定は変更できない。"],
        # ★no_lockout(patch 形)は**守るべき経路を漏れなく書く**。
        #   「運用者の接続が切れないこと」だけでは遠隔接続しか指さないため、
        #   コンソールの緊急経路を根拠に正解を決めると**問題文に無い制約**になる
        #   (2026-08-08 ユーザ指摘。実際に A も要件を満たす盤面を出してしまった)。
        # ★「移行」という語は patch 形でしか成り立たない(他の形の盤面には
        #   移行という出来事が存在しない)。守る経路は同じまま、時制だけ落とす。
        "no_lockout": (["移行の作業中に、運用者の遠隔からの接続が失われないこと。",
                        "移行の前後にわたり、緊急時にコンソールから操作できる経路を"
                        "失わないこと。"] if form in ("patch", "patchseq") else
                       ["運用者の遠隔からの接続が失われないこと。",
                        "緊急時にコンソールから操作できる経路を失わないこと。"]),
    }[w]
    return base + extra


def topo_block(d):
    return "\n".join([
        "```",
        f"  SRV01 (認証サーバ #1) ──┐",
        f"                          {d['rt']['A']} ({d['site']['A']}) ───── "
        f"{d['rt']['B']} ({d['site']['B']})",
        f"  SRV02 (認証サーバ #2) ──┘",
        "```",
    ])


def addr_table(d):
    """★ルータ側のアドレス表。これが無いと「許可された送信元」と実際の送信元を
    突き合わせられず、解答が推測になる(2026-08-08 ユーザ指摘)。"""
    n = d["net"]
    return "\n".join([
        "| ルータ | Loopback0 | 認証サーバ方向のインタフェース |",
        "|---|---|---|",
        f"| {d['rt']['A']}({d['site']['A']}) | {n['loA']} | Ethernet0/0 = {n['egA']} |",
        f"| {d['rt']['B']}({d['site']['B']}) | {n['loB']} | Ethernet0/0 = {n['egB']} |",
    ])


def server_spec(d):
    n = d["net"]
    return "\n".join([
        "| 項目 | SRV01 | SRV02 |", "|---|---|---|",
        f"| アドレス | {n['srv1']} | {n['srv2']} |",
        f"| 待受ポート | 1812 / 1813 | {d['port2']} / {d['port2'] + 1} |",
        f"| 共有鍵 | {d['key']} | {d['key']} |",
        f"| 受理する送信元 | {n['loA']} ・ {n['loB']} | 同左 |",
        f"| 台帳 | {d['adm']}(15) ・ {d['desk']}(1) ・ {d['auto']}(15) | 同左 |",
        # ★盤面に計画停止を持たせた場合は必ず明示する。伏せると trace 形の
        #   所要時間も read 形の結果も**導出できない問題**になる(出題前検分で検出)。
        f"| 現在の稼働状態 |"
        f" {'保守作業のため停止中' if (d.get('srv1_down') or d.get('all_down')) else '稼働中'}"
        f" | {'保守作業のため停止中' if d.get('all_down') else '稼働中'} |",
    ])


# --------------------------------------------------------------------------
def _authread_selftest(seeds=40):
    """★authread の一意性を機械検証する(監査で欠けていたと指摘された)。

    - 正解がちょうど 2 本 / 選択肢 4 本が相異なる
    - **恒等的に同値な文が同居しない**(軸ラベルではなく真偽ベクトルで判定)
    - 正解 2 本のうち少なくとも 1 本が遍歴の軸(m1/m2/list)
    - 出力ブロックに実機以外の文字列が入らない
    """
    import random as _r
    ok = ng = 0
    msgs = []
    for kind in KINDS:
        for s in range(seeds):
            rnd = _r.Random(s * 37 + 11)
            d = draw(rnd, kind=kind)
            wl = rnd.random() < 0.6
            d["_auth"] = {"with_list": wl, "pw_ok": rnd.random() < 0.5,
                          "on_console": (not wl) and rnd.random() < 0.4}
            if wl and rnd.random() < 0.5:
                d["all_down"] = True
            site = "B" if d["scope"] == "B" else "A"
            try:
                ch = build_choices_authread(d, _r.Random(s))
            except ValueError as e:
                ng += 1
                msgs.append(f"{kind}/{s}: {e}")
                continue
            facts = {t: (a, v) for a, t, v in authread_facts(d, site)}
            bad = None
            if sum(1 for _t, o, _w in ch if o) != 2:
                bad = "正解が2本でない"
            elif len({t for t, _o, _w in ch}) != 4:
                bad = "選択肢が重複"
            elif any(facts[t][1] != o for t, o, _w in ch):
                bad = "選択肢の真偽が facts と食い違う"
            elif len({facts[t][0] for t, _o, _w in ch}) != 4:
                bad = "同じ軸の文が同居"
            elif not ({facts[t][0] for t, o, _w in ch if o} & {"m1", "m2", "list"}):
                bad = "正解が遍歴の軸を含まない"
            else:
                dbg = enable_debug_block(d, site, pw_ok=d["_auth"]["pw_ok"],
                                         with_list=d["_auth"]["with_list"],
                                         on_console=d["_auth"]["on_console"])
                if "<" in dbg or "利用者>" in dbg:
                    bad = "出力に実機以外の文字列がある"
                elif d["_auth"]["on_console"] and d["_auth"]["with_list"]:
                    bad = "未実測の組合せ(console × 方式リスト有り)"
            if bad:
                ng += 1
                msgs.append(f"{kind}/{s}: {bad}")
            else:
                ok += 1
    print(f"authread selftest: {ok}/{ok + ng}")
    for m in msgs[:8]:
        print("  -", m)
    return ng


def _selftest(seeds=60):
    ok = ng = 0
    detail = {}
    for kind in KINDS:
        for w in WORLDS:
            for s in range(seeds):
                d = draw(random.Random(s * 977 + 13), kind=kind, world=w)
                if w not in compatible_worlds(d):
                    continue
                try:
                    verify_choices(d)
                    ok += 1
                except ValueError as e:
                    ng += 1
                    detail.setdefault(f"{kind}/{w}", str(e))
    # evidence 形が成立する盤面がどれだけあるか(全 kind で必要ではない)
    ev_ok = ev_ng = 0
    for kind in KINDS:
        for s in range(seeds):
            d = draw(random.Random(s * 31 + 7), kind=kind)
            try:
                evidence_variants(d)
                ev_ok += 1
            except ValueError:
                ev_ng += 1
    print(f"aaa selftest: 4形の成立 {ok}/{ok + ng}"
          + (f"  NG例: {list(detail.items())[:3]}" if ng else ""))
    print(f"  evidence 形が成立する盤面: {ev_ok}/{ev_ok + ev_ng}")
    # 区別できないペアが実際に存在することの確認(この shape の根拠)
    pairs = set()
    for s in range(seeds):
        for kind in KINDS:
            d = draw(random.Random(s * 17 + 3), kind=kind)
            for r in confusable(d):
                pairs.add(tuple(sorted((kind, r))))
    print(f"  機器側で区別できないペア: {sorted(pairs)}")
    return 0 if ng == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--kind", choices=KINDS)
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest() + _authread_selftest())
    dd = draw(random.Random(a.seed), kind=a.kind)
    print(f"kind={dd['kind']} world={dd['world']} scope={dd['scope']}")
    print(topo_block(dd))
    print(server_spec(dd))
    print("--- cfg ---"); print(cfg_block(dd, dd["scope"] if dd["scope"] != "both" else "A"))
    print("--- login ---"); print(render_login_table(dd, login_table(dd)))
    print("--- trace ---"); print(trace_block(dd))
    print("--- confusable ---"); print(confusable(dd))
