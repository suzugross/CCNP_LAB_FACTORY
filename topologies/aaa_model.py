#!/usr/bin/env python3
"""IOS AAA(RADIUS) 意味評価器 (BL-101 P1a)。

紙面 `shape=aaa` の一意性検証と、ラボ(GEN-AAAGRP / gen_aaa_ts)の採点期待値を
**同じモデル**から出すための小さな評価器。`acl_model.py` と同じ位置づけ。

★スコープ(2026-08-08 レビューで縮小):
  - 出力は **ok(priv) / reject / no_response(理由) / authz_fail(理由)** の 4 値と理由のみ。
  - **時間(DEAD 判定・deadtime・タイミング)はモデルに持たせない**。
    秒数が要る場面は `delay_seconds()` の式で後から出す
    (実測で `timeout × (retransmit+1) × 到達不能サーバ数` が成立している)。
  - 状態を持たせるとモデルが実機とずれた瞬間に問題が壊れる。**小さいほど安全**。

★各分岐は PoC 実測に紐付く。E 番号は poc/aaa/README.md の実測表を指す。
"""

# ---------------------------------------------------------------- データ形

# dev = {
#   "lists": {"authn": {"default": [...], "<名前>": [...]},
#             "authz": {...}, "enable": {...}},        # メソッド列
#   "line":  {"vty": {"login": None|"<名前>", "authz": None|"<名前>"},   # vty 0 4
#             "vty_hi": {...},                                        # vty 5 15
#             "con": {...}},
#   "group": {"name": "RADGRP", "members": ["RAD1", "RAD2"]},
#   "servers": {"RAD1": {"ip": .., "key": .., "auth_port": ..}},
#   "src_addr": "10.0.0.2",        # 実際に出て行く送信元(生成器が決めて渡す)
#   "local":  {"emg-admin": 15, "SUZUKI": 15},
#   "enable_secret": True,
#   "timeout": 3, "retransmit": 1,
# }
# srv = {"RAD1": {"alive": True, "key": .., "auth_port": ..,
#                 "clients": ["10.0.0.1"], "users": {"noc-taro": 15}}}
#
# メソッドの書き方: "group:<グループ名>" / "local" / "none" / "enable"

OK, REJECT, NO_RESPONSE, AUTHZ_FAIL = "ok", "reject", "no_response", "authz_fail"


def resolve_list(dev, kind, line="vty"):
    """line に適用された方式リストを解決して (リスト名, メソッド列) を返す。

    ★E15 実測: line が**未定義のリスト名**を参照していても拒否にはならず、
    **default 方式リストがそのまま効く**(authn / authz どちらも同じ)。
    → `list_not_applied` と `list_undefined` は症状が完全に一致する。
    """
    tbl = dev["lists"].get(kind, {})
    key = {"authn": "login", "authz": "authz", "enable": "login"}[kind]
    # ★回線は vty(0 4) / vty_hi(5 15) / con を独立に持つ。方式リストを
    #   `line vty 0 4` にだけ当てると、**6 セッション目以降だけ挙動が変わる**。
    name = dev.get("line", {}).get(line, {}).get(key)
    if kind == "enable":
        name = None                      # enable はライン単位で切り替えられない
    if name and name in tbl:
        return name, tbl[name]
    if name:                             # ★未定義参照 → default へ(E15)
        return "default", tbl.get("default")
    return "default", tbl.get("default")


def _reachable(dev, srv, sname):
    """1台の RADIUS サーバに要求が届き、応答が受理できるか。

    返り値: (True, None) か (False, 理由)
      理由= "server_down" / "unknown_client" / "key_mismatch" / "port_mismatch"

    ★E2: キー不一致でもサーバには**届いており Reject を返している**が、ルータ側は
      Response Authenticator を検証できず捨てるため「無応答」に見える。
      → モデルでは「応答なし」に畳む(ルータ視点の観測に一致させる)。
    ★E3: 送信元が clients に無いとサーバは**無言破棄**(Ignoring request ...)。
    ★E10: auth-port 不一致は届かない。
    """
    s = srv.get(sname)
    d = dev["servers"].get(sname)
    # ★X4/X4b 実測: 経路上/自機の ACL で RADIUS を落とすと、機器側の症状は
    #   サーバ停止と**完全に同一**(`No authoritative response` / 同じ秒数 /
    #   `show aaa servers` の DEAD / `%RADIUS-4-RADIUS_DEAD` まで同じ)。
    #   要求を落とす(out)のと応答だけを落とす(in)のも機器側では区別できない。
    #   決め手は `show ip access-lists` のカウンタだけ。
    if dev.get("acl_block"):
        return False, "acl_" + dev["acl_block"]
    if s is None or d is None:
        return False, "server_down"
    if not s.get("alive", True):
        return False, "server_down"
    if d.get("auth_port") != s.get("auth_port"):
        return False, "port_mismatch"
    if dev.get("src_addr") not in s.get("clients", []):
        return False, "unknown_client"
    if d.get("key") != s.get("key"):
        return False, "key_mismatch"
    return True, None


def query_group(dev, srv, gname, user, pw_ok=True):
    """グループへの問い合わせ。

    ★E8 実測: 到達不能なサーバは飛ばして**次のサーバが応答すれば権威**となり、
      1 トランザクション内でフェイルオーバーが成立する。
    ★E1 実測: **最初に応答した 1 台の Reject が権威**。後段メソッドへは落ちない。
    返り値: ("accept", priv) / ("reject", None) / ("silent", [理由,...])
    """
    g = dev.get("group", {})
    members = g.get("members", []) if g.get("name") == gname else []
    whys = []
    for sname in members:
        ok, why = _reachable(dev, srv, sname)
        if not ok:
            whys.append(why)
            continue
        users = srv[sname].get("users", {})
        if user in users and pw_ok:
            return "accept", users[user]
        return "reject", None            # ★応答した時点で権威(E1/E12)
    return "silent", whys


PASS, FAIL, ERROR = "pass", "fail", "error"

# メソッドごとの理由文字列(結果の由来を1語で表す)
_WHY_PASS = {"local": "local", "none": "none",
             "if-authenticated": "if_authenticated", "enable": "enable_secret"}
_WHY_FAIL = {"local": "local_reject", "enable": "enable_reject"}


def walk_methods(dev, srv, methods, user, pw_ok=True):
    """★メソッド列の**遍歴**を返す。`[(メソッド, PASS|FAIL|ERROR, 付随値)]`。

    実測 X8/X10 で確認したとおり、`debug aaa authentication` は
    **`service=ENABLE` のときだけ**この遍歴を字面に出す
    (`Method=...` → `status = PASS|FAIL|ERROR`。ERROR なら次のメソッドへ、
    FAIL ならそこで終了)。紙面 `authread` 形はこの遍歴の写像なので、
    **判定(`run_methods`)と描画が同じ関数から出る**ようにここへ集約する。
    """
    steps = []
    for m in methods or []:
        if m.startswith("group:"):
            res, val = query_group(dev, srv, m.split(":", 1)[1], user, pw_ok)
            if res == "accept":
                steps.append((m, PASS, val))
                return steps
            if res == "reject":
                steps.append((m, FAIL, None))
                return steps
            steps.append((m, ERROR, val))     # silent → 次のメソッドへ
            continue
        if m == "local":
            ok = (user in dev.get("local", {}) and pw_ok)
            steps.append((m, PASS if ok else FAIL,
                          dev["local"][user] if ok else None))
            return steps                      # local も応答=権威
        if m in ("none", "if-authenticated"):
            steps.append((m, PASS, None))
            return steps
        if m == "enable":
            ok = bool(dev.get("enable_secret")) and pw_ok
            steps.append((m, PASS if ok else FAIL, 15 if ok else None))
            return steps
    return steps


def run_methods(dev, srv, methods, user, pw_ok=True):
    """メソッド列を先頭から評価する(遍歴 `walk_methods` の集約)。

    ★統一原理(E1 / E6 / E16b で 3 層とも確認): **Reject は権威であり後段へ落ちない**。
      後段へ進むのは「応答が無い(ERROR)」ときだけ(E2 / E3 / E9 / E10)。
    返り値: (結果, priv or None, 理由)
    """
    if not methods:
        return NO_RESPONSE, None, "no_method"
    steps = walk_methods(dev, srv, methods, user, pw_ok)
    if not steps:
        return NO_RESPONSE, None, "no_method"
    m, out, val = steps[-1]
    if out == PASS:
        return OK, val, ("radius" if m.startswith("group:") else _WHY_PASS[m])
    if out == FAIL:
        return REJECT, None, ("radius_reject" if m.startswith("group:")
                              else _WHY_FAIL[m])
    whys = []
    for _m, _o, v in steps:
        if _o == ERROR and v:
            whys.extend(v)
    return NO_RESPONSE, None, ",".join(sorted(set(whys))) or "unreachable"


def login(dev, srv, user, pw_ok=True, line="vty"):
    """ログインの評価。認証 → 認可(exec)の順。

    ★E4 / E18 実測: **priv は認可が与える**。
      認可の方式リストが無ければ、RADIUS ユーザでも local ユーザ(`username X privilege 15`)でも
      **priv 1** になる。認可 local なら username の privilege がそのまま出る。
    ★E5 / E6 実測: 認可が Reject / 応答なしで落ちると **exec 拒否**(認証が通っていても)。
    返り値: dict(result, priv, why)
    """
    _, authn = resolve_list(dev, "authn", line)
    res, priv, why = run_methods(dev, srv, authn, user, pw_ok)
    if res != OK:
        return {"result": res, "priv": None, "why": why, "stage": "authn"}

    # ★X5/X6/X11/X12 実測(2026-08-08): **コンソールの認可は既定で実行されない**。
    #   `line con 0` に `authorization exec` を書いても、グローバルの
    #   `aaa authorization console` が無ければ認可そのものが走らない。
    #   このとき権限レベルは **1** になる(X11a= RADIUS の AVPair priv-lvl=15 でも priv 1 /
    #   X12a= `username ... privilege 15` の local 利用者でも priv 1)。
    #   グローバルを足すと 15 になる(X11c / X12b)。
    #   → 「認可が走らない = 認証で通った素性の priv がそのまま出る」ではない。
    if line == "con" and not dev.get("authz_console"):
        return {"result": OK, "priv": 1, "why": "authz_console_disabled",
                "stage": "authz"}

    _, authz = resolve_list(dev, "authz", line)
    if not authz:                        # 認可リスト自体が無い → priv 1(E4/E18)
        return {"result": OK, "priv": 1, "why": "no_authz", "stage": "authz"}
    ares, apriv, awhy = run_methods(dev, srv, authz, user, pw_ok=True)
    if ares == OK:
        return {"result": OK, "priv": (apriv if apriv is not None else 1),
                "why": awhy, "stage": "authz"}
    # ★Reject でも応答なしでも exec は通らない(E5/E6)
    return {"result": AUTHZ_FAIL, "priv": None, "why": awhy, "stage": "authz"}


def enable(dev, srv, user, pw_ok=True):
    """enable 昇格の評価。

    ★E16a: `aaa authentication enable default` 未設定なら enable secret で 15 へ。
    ★E16b: `group:<G>` を噛ませると RADIUS 側に `$enab15$` が無く **Reject**、
      後段の `enable` へは**落ちない**(統一原理の 3 層目)。
    """
    methods = dev["lists"].get("enable", {}).get("default")
    if not methods:
        if dev.get("enable_secret") and pw_ok:
            return {"result": OK, "priv": 15, "why": "enable_secret"}
        return {"result": REJECT, "priv": None, "why": "no_enable_secret"}
    res, priv, why = run_methods(dev, srv, methods, "$enab15$", pw_ok)
    if res == OK:
        return {"result": OK, "priv": 15, "why": why}
    return {"result": res, "priv": None, "why": why}


def delay_seconds(dev, srv, gname=None):
    """応答までの秒数(★モデルではなく式で出す)。

    実測: `timeout × (retransmit+1) × 到達不能サーバ数`
      E8 = 3 × 2 × 1 = 6s (6.1s 実測) / E2・E9 = 3 × 2 × 2 = 12s (12.1〜12.4s 実測)
    到達できるサーバに当たった時点で止まるので、それ以降は数えない。
    """
    g = dev.get("group", {})
    members = g.get("members", []) if (gname is None or g.get("name") == gname) else []
    unreachable = 0
    for sname in members:
        ok, _ = _reachable(dev, srv, sname)
        if ok:
            break
        unreachable += 1
    return unreachable * dev.get("timeout", 3) * (dev.get("retransmit", 1) + 1)


def unreachable_reasons(dev, srv):
    """各サーバがなぜ届かないか(evidence 形で「サーバ側ログに何が出るか」を決める)。"""
    out = {}
    for sname in dev.get("group", {}).get("members", []):
        ok, why = _reachable(dev, srv, sname)
        out[sname] = None if ok else why
    return out


# ---------------------------------------------------------------- selftest

def _base():
    """PoC の基線 B0 を再現した dev/srv。"""
    dev = {
        "lists": {"authn": {"default": ["group:RADGRP", "local"]},
                  "authz": {"default": ["group:RADGRP", "local"]},
                  "enable": {}},
        "line": {"vty": {"login": None, "authz": None},
                 "con": {"login": None, "authz": None}},
        "group": {"name": "RADGRP", "members": ["RAD1", "RAD2"]},
        "servers": {"RAD1": {"ip": "10.99.1.2", "key": "K", "auth_port": 1812},
                    "RAD2": {"ip": "10.99.2.2", "key": "K", "auth_port": 1912}},
        "src_addr": "10.0.0.2",
        "local": {"SUZUKI": 15, "emg-admin": 15},
        "enable_secret": True, "timeout": 3, "retransmit": 1,
    }
    users = {"SUZUKI": 15, "noc-taro": 15, "helpdesk": 1}
    srv = {"RAD1": {"alive": True, "key": "K", "auth_port": 1812,
                    "clients": ["10.0.0.1", "10.0.0.2"], "users": dict(users)},
           "RAD2": {"alive": True, "key": "K", "auth_port": 1912,
                    "clients": ["10.0.0.1", "10.0.0.2"], "users": dict(users)}}
    return dev, srv


def _selftest():
    """★全ケースが PoC 実測(poc/aaa/README.md)と一致することを確認する。"""
    import copy
    fails = []

    def chk(label, got, want):
        if got != want:
            fails.append(f"{label}: got={got} want={want}")

    # --- B0 基線
    dev, srv = _base()
    chk("B0 noc-taro", (login(dev, srv, "noc-taro")["result"],
                        login(dev, srv, "noc-taro")["priv"]), (OK, 15))
    chk("B0 helpdesk", (login(dev, srv, "helpdesk")["result"],
                        login(dev, srv, "helpdesk")["priv"]), (OK, 1))
    # E1: local に居るが RADIUS 台帳に無い → Reject。★local へ落ちない
    chk("E1 emg-admin", login(dev, srv, "emg-admin")["result"], REJECT)
    # E12: 誤パスワード → Reject
    chk("E12 wrong-pw", login(dev, srv, "noc-taro", pw_ok=False)["result"], REJECT)

    # --- E2 key_mismatch → 無応答 → local へ
    dev, srv = _base()
    dev["servers"]["RAD1"]["key"] = dev["servers"]["RAD2"]["key"] = "WRONG"
    chk("E2 emg-admin(local へ)", (login(dev, srv, "emg-admin")["result"],
                                   login(dev, srv, "emg-admin")["priv"]), (OK, 15))
    chk("E2 noc-taro(local に無い)", login(dev, srv, "noc-taro")["result"], REJECT)
    chk("E2 delay", delay_seconds(dev, srv), 12)

    # --- E3 src_iface_missing → unknown client → 無応答 → local へ
    dev, srv = _base()
    dev["src_addr"] = "10.1.12.2"
    chk("E3 emg-admin", login(dev, srv, "emg-admin")["result"], OK)
    chk("E3 理由", set(unreachable_reasons(dev, srv).values()), {"unknown_client"})
    chk("E3 delay", delay_seconds(dev, srv), 12)

    # --- E4 認可なし → priv 1
    dev, srv = _base()
    dev["lists"]["authz"] = {}
    chk("E4 noc-taro priv", login(dev, srv, "noc-taro")["priv"], 1)
    chk("E4 helpdesk priv", login(dev, srv, "helpdesk")["priv"], 1)
    # E18: 認証 local / 認可なし → local priv15 ユーザでも priv 1
    dev["lists"]["authn"]["default"] = ["local"]
    chk("E18a emg-admin priv", login(dev, srv, "emg-admin")["priv"], 1)
    # E18: 認可 local → username の privilege がそのまま
    dev["lists"]["authz"] = {"default": ["local"]}
    chk("E18b emg-admin priv", login(dev, srv, "emg-admin")["priv"], 15)

    # --- E5 認可にフォールバック無し × 全断 → 全員 exec 拒否
    dev, srv = _base()
    dev["lists"]["authz"]["default"] = ["group:RADGRP"]
    srv["RAD1"]["alive"] = srv["RAD2"]["alive"] = False
    for u in ("SUZUKI", "emg-admin"):
        chk(f"E5 {u}", login(dev, srv, u)["result"], AUTHZ_FAIL)

    # --- E6 認証 local / 認可 RADIUS → 認証は通るが認可 Reject で exec 拒否
    dev, srv = _base()
    dev["lists"]["authn"]["default"] = ["local"]
    chk("E6 emg-admin", login(dev, srv, "emg-admin")["result"], AUTHZ_FAIL)
    chk("E6 SUZUKI", login(dev, srv, "SUZUKI")["result"], OK)

    # --- E8 片系断 → 次のサーバが応答(1 トランザクション内)
    dev, srv = _base()
    srv["RAD1"]["alive"] = False
    chk("E8 noc-taro", (login(dev, srv, "noc-taro")["result"],
                        login(dev, srv, "noc-taro")["priv"]), (OK, 15))
    chk("E8 delay", delay_seconds(dev, srv), 6)

    # --- E9 全断 → local へ
    dev, srv = _base()
    srv["RAD1"]["alive"] = srv["RAD2"]["alive"] = False
    chk("E9 emg-admin", login(dev, srv, "emg-admin")["result"], OK)
    chk("E9 noc-taro", login(dev, srv, "noc-taro")["result"], REJECT)
    chk("E9 delay", delay_seconds(dev, srv), 12)

    # --- E10 port_mismatch
    dev, srv = _base()
    dev["servers"]["RAD2"]["auth_port"] = 1812
    srv["RAD1"]["alive"] = False
    chk("E10 理由", unreachable_reasons(dev, srv)["RAD2"], "port_mismatch")
    chk("E10 emg-admin", login(dev, srv, "emg-admin")["result"], OK)

    # --- E15 未定義リスト参照 → default へ(= 適用忘れと同一)
    dev, srv = _base()
    dev["line"]["vty"]["login"] = "NOEXIST"
    dev["line"]["vty"]["authz"] = "NOEXIST2"
    for u, want in (("SUZUKI", OK), ("noc-taro", OK), ("emg-admin", REJECT)):
        chk(f"E15 {u}", login(dev, srv, u)["result"], want)
    chk("E15 priv", login(dev, srv, "noc-taro")["priv"], 15)
    base_dev, base_srv = _base()
    chk("E15 == 適用忘れ",
        [login(dev, srv, u)["result"] for u in ("SUZUKI", "noc-taro", "emg-admin")],
        [login(base_dev, base_srv, u)["result"]
         for u in ("SUZUKI", "noc-taro", "emg-admin")])

    # --- E16 enable
    dev, srv = _base()
    chk("E16a 既定", enable(dev, srv, "helpdesk")["result"], OK)
    dev["lists"]["enable"] = {"default": ["group:RADGRP", "enable"]}
    chk("E16b RADIUS 経由", enable(dev, srv, "helpdesk")["result"], REJECT)

    # --- 名前付きリストが定義され適用されている場合(正常系)
    dev, srv = _base()
    dev["lists"]["authn"]["MYLIST"] = ["local"]
    dev["line"]["vty"]["login"] = "MYLIST"
    chk("named list", login(dev, srv, "emg-admin")["result"], AUTHZ_FAIL)

    # --- ★if-authenticated(X1/X2/X2b 実測・2026-08-08)
    # X1: グループが応答する限り AVPair の priv がそのまま乗る(= local と区別できない)
    dev, srv = _base()
    dev["lists"]["authz"]["default"] = ["group:RADGRP", "if-authenticated"]
    chk("X1 if-auth 健全 noc-taro", login(dev, srv, "noc-taro")["priv"], 15)
    chk("X1 if-auth 健全 helpdesk", login(dev, srv, "helpdesk")["priv"], 1)
    # X2: 全断でフォールバックすると **priv 1**(username privilege 15 は効かない)
    for s in srv.values():
        s["alive"] = False
    chk("X2 if-auth 全断 emg-admin",
        (login(dev, srv, "emg-admin")["result"],
         login(dev, srv, "emg-admin")["priv"]), (OK, 1))
    # X2b 対照: 認可が local なら username の privilege が出る
    dev["lists"]["authz"]["default"] = ["group:RADGRP", "local"]
    chk("X2b 対照 全断 emg-admin", login(dev, srv, "emg-admin")["priv"], 15)

    # --- ★コンソールの認可(X5/X6/X11/X12 実測・2026-08-08)
    # X11a: 専用リスト無し(default= group local)・グローバル無し
    #       → RADIUS 台帳の利用者(AVPair priv-lvl=15)でも **priv 1**
    dev, srv = _base()
    chk("X11a con RADIUS priv", (login(dev, srv, "noc-taro", line="con")["result"],
                                 login(dev, srv, "noc-taro", line="con")["priv"]),
        (OK, 1))
    # X11c: グローバル有り → AVPair の 15 が乗る
    dev["authz_console"] = True
    chk("X11c con RADIUS priv", login(dev, srv, "noc-taro", line="con")["priv"], 15)

    # X12a/X12b: コンソール専用リスト(authn/authz とも local)を当てた健全構成
    dev, srv = _base()
    dev["lists"]["authn"]["CONSOLE"] = ["local"]
    dev["lists"]["authz"]["CONSOLE"] = ["local"]
    dev["line"]["con"] = {"login": "CONSOLE", "authz": "CONSOLE"}
    chk("X12a con local priv(グローバル無し)",
        (login(dev, srv, "emg-admin", line="con")["result"],
         login(dev, srv, "emg-admin", line="con")["priv"]), (OK, 1))
    dev["authz_console"] = True
    chk("X12b con local priv(グローバル有り)",
        login(dev, srv, "emg-admin", line="con")["priv"], 15)

    # X5/X6: 認可= group のみ(フォールバック無し)× サーバ全断
    dev, srv = _base()
    dev["lists"]["authn"]["CONSOLE"] = ["local"]
    dev["lists"]["authz"]["CON-AZ"] = ["group:RADGRP"]
    dev["line"]["con"] = {"login": "CONSOLE", "authz": "CON-AZ"}
    for s in srv.values():
        s["alive"] = False
    chk("X5 con(グローバル無し)= 入れる",
        login(dev, srv, "emg-admin", line="con")["result"], OK)
    dev["authz_console"] = True
    chk("X6 con(グローバル有り)= 認可で拒否",
        login(dev, srv, "emg-admin", line="con")["result"], AUTHZ_FAIL)

    _ = copy
    if fails:
        print(f"NG {len(fails)} 件")
        for f in fails:
            print("  -", f)
        return 1
    print("aaa_model selftest: OK (PoC 実測 B0/E1〜E18 と一致)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
