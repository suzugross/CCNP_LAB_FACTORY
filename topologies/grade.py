#!/usr/bin/env python3
"""採点: grade.yml が収集した show 出力を pyATS Genie で構造化し、
フィールド単位のアサートでスコアを出す。

入力 JSON（grade.yml が生成）: チェックの配列。各チェックは 1 コマンド = 配点単位。
[
  {
    "name":   "RT01: HSRP group10 Active ...",
    "points": 30,
    "node":   "RT01",
    "command":"show standby",          # 実機へ送ったコマンド（表示用）
    "parser": "show standby all",       # Genie パーサのコマンドキー
    "genie_os":"iosxe",                 # 省略時 iosxe
    "find":   "*.address_family.*.version.*.groups.*",  # 判定対象オブジェクトの glob
    "match":  {                          # find で選ばれたいずれかのオブジェクトが
       "group_number": 10,               # これら全条件を満たせば PASS（フィールド相関）
       "hsrp_router_state": "active",
       "primary_ipv4_address.address": "192.168.10.1"
    },
    "stdout": "show 出力テキスト"
  },
  ...
]

Genie パーサに穴がある項目（例: iosxe の show standby は "Preemption disabled" でも
preempt=True を返すバグ）は、構造化の代わりに raw（生出力）条件を使う:
  { "name":..., "points":15, "node":"RT01", "command":"show standby",
    "raw": [ {"contains": "Preemption enabled"} ], "stdout": "..." }
raw と match を両方持つチェックは両方を満たす必要がある。

大域不変条件（軸1）: 入力が list でなく dict の場合、ノード単位 checks に加えて
ネットワーク全体の性質（ループ不在/最適性/冗長度 等）を採点する:
  {
    "checks":     [ ...従来のチェック... ],          # 省略可
    "model":      {"loopbacks": {...}, "links": [...]},
    "ribs":       {"RT01": "show ip route 生テキスト", ...},
    "invariants": [ {"type":"loop_free","name":"...","points":30}, ... ],
    "genie_os":   "iosxe"
  }
判定は topologies/netmodel.py（転送グラフ構築 → 不変条件評価）が担当。

判定:
  Genie で stdout を構造化 → find(glob, `*`=任意キー/添字) で候補オブジェクト列挙
  → match の各キー(ドット区切り・`*`可)を相対解決し、全条件を満たすオブジェクトが
    1 つでもあれば PASS。配点は all-or-nothing。
  パース失敗・候補無し・未収束時は FAIL（収束待ちの再試行シグナルになる）。

match の値（条件）の書式:
  scalar                      → 等価（型ゆるく比較: "110"==110, "Active"=="active"）
  {contains: x}               → x を部分文字列として含む
  {startswith: x}             → x で始まる
  {regex: "..."}              → 正規表現マッチ
  {gte/gt/lte/lt: n}          → 数値比較
  {ne: x}                     → 等価でない
  {in: [..]}                  → いずれかに一致
  {exists: true/false}        → 値の有無

CLI:
  grade.py INPUT.json [--gate]
  --gate: 全チェック PASS なら exit 0、未充足があれば exit 3（収束待ちループ用）
"""
import json
import os
import re
import sys

from genie.conf.base import Device

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ----------------------------------------------------------------------------
# Genie パース（オフライン: 既存の show 出力テキストを構造化）
# ----------------------------------------------------------------------------
_DEV_CACHE = {}


def _device(os_name):
    dev = _DEV_CACHE.get(os_name)
    if dev is None:
        dev = Device(name=f"grade-{os_name}", os=os_name)
        dev.custom.setdefault("abstraction", {"order": ["os"]})
        _DEV_CACHE[os_name] = dev
    return dev


def genie_parse(parser, output, os_name="iosxe"):
    """show 出力テキストを Genie で構造化。失敗時は None。"""
    try:
        return _device(os_name).parse(parser, output=output or "")
    except Exception:
        # SchemaEmptyParserError / ParserNotFound / 収束前の空出力など
        return None


# ----------------------------------------------------------------------------
# glob パス解決（`*`=任意の dict キー / list 添字）
# ----------------------------------------------------------------------------
def _children(node):
    """(key, value) を列挙。dict はキー、list は添字。"""
    if isinstance(node, dict):
        return list(node.items())
    if isinstance(node, list):
        return list(enumerate(node))
    return []


def resolve_nodes(obj, tokens):
    """tokens(リスト) を辿り、終端の *オブジェクト* を列挙する。"""
    cur = [obj]
    for tok in tokens:
        nxt = []
        for node in cur:
            for key, val in _children(node):
                if tok == "*" or str(key) == tok:
                    nxt.append(val)
        cur = nxt
    return cur


def _tokens(path):
    """パスをトークン列へ。文字列は "." 区切り。リストは各要素を
    そのまま 1 トークン扱い（IP 等ドットを含む dict キーを表現できる）。"""
    if isinstance(path, (list, tuple)):
        return [str(t) for t in path]
    return [t for t in str(path).split(".") if t != ""]


# ----------------------------------------------------------------------------
# 条件評価
# ----------------------------------------------------------------------------
def _norm(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower()
    return v


def _eq(actual, expected):
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual == expected
    if _norm(actual) == _norm(expected):
        return True
    # 数値文字列のゆるい一致（"110" == 110）
    try:
        return float(actual) == float(expected)
    except (TypeError, ValueError):
        return False


def check_condition(actual, cond):
    """1 つの実値 actual が条件 cond を満たすか。"""
    if not isinstance(cond, dict):
        return _eq(actual, cond)
    (op, val), = cond.items()
    s = "" if actual is None else str(actual)
    if op == "equals":
        return _eq(actual, val)
    if op == "ne":
        return not _eq(actual, val)
    if op == "contains":
        return str(val).lower() in s.lower()
    if op == "startswith":
        return s.lower().startswith(str(val).lower())
    if op == "regex":
        return re.search(val, s) is not None
    if op == "in":
        return any(_eq(actual, v) for v in val)
    if op in ("gte", "gt", "lte", "lt"):
        try:
            a, b = float(actual), float(val)
        except (TypeError, ValueError):
            return False
        return {"gte": a >= b, "gt": a > b, "lte": a <= b, "lt": a < b}[op]
    if op == "exists":
        return (actual is not None) == bool(val)
    raise ValueError(f"unknown operator: {op}")


def field_matches(node, rel_path, cond):
    """node 配下の rel_path(glob可) の実値のいずれかが cond を満たすか。
    戻り値: (ok, observed_values)"""
    values = resolve_nodes(node, _tokens(rel_path))
    if not values:
        return (check_condition(None, cond) if _wants_absence(cond) else False, [])
    ok = any(check_condition(v, cond) for v in values)
    return ok, values


def _wants_absence(cond):
    return isinstance(cond, dict) and cond.get("exists") is False


# ----------------------------------------------------------------------------
# 1 チェックの評価
# ----------------------------------------------------------------------------
def eval_raw(stdout, conditions):
    """生出力に対する条件群。全て満たせば PASS。
    各条件: {contains: s} / {not_contains: s} / {regex: re} / {not_regex: re}"""
    text = stdout or ""
    unmet = []
    for cond in conditions:
        (op, val), = cond.items()
        if op == "contains":
            ok = val in text
        elif op == "not_contains":
            ok = val not in text
        elif op == "regex":
            ok = re.search(val, text) is not None
        elif op == "not_regex":
            ok = re.search(val, text) is None
        else:
            raise ValueError(f"unknown raw operator: {op}")
        if not ok:
            unmet.append(cond)
    return (not unmet), unmet


def eval_genie(check):
    """parser + find + match による構造化判定。戻り値: (ok, detail)"""
    parsed = genie_parse(check["parser"], check.get("stdout", ""),
                         check.get("genie_os", "iosxe"))
    if parsed is None:
        return False, {"reason": "パース失敗/出力空（未収束の可能性）"}

    find = check.get("find")
    candidates = resolve_nodes(parsed, _tokens(find)) if find else [parsed]
    if not candidates:
        return False, {"reason": f"find に一致するオブジェクト無し: {find}"}

    match = check.get("match", {})
    best_unmet = None
    for node in candidates:
        unmet = {}
        for rel, cond in match.items():
            ok, observed = field_matches(node, rel, cond)
            if not ok:
                # 観測値を要約（多すぎる場合は先頭のみ）
                obs = observed[:3] if isinstance(observed, list) else observed
                unmet[rel] = {"expected": cond, "observed": obs or "（値なし）"}
        if not unmet:
            return True, {}
        if best_unmet is None or len(unmet) < len(best_unmet):
            best_unmet = unmet
    return False, {"unmet": best_unmet}


def evaluate(check):
    """genie(match) と raw の両モードを評価。両方ある場合は AND。
    戻り値: (ok: bool, detail: dict)"""
    detail = {}
    ok = True
    if "match" in check or "find" in check:
        g_ok, g_detail = eval_genie(check)
        ok = ok and g_ok
        detail.update(g_detail)
    if "raw" in check:
        r_ok, r_unmet = eval_raw(check.get("stdout", ""), check["raw"])
        ok = ok and r_ok
        if r_unmet:
            detail["raw_unmet"] = r_unmet
    return ok, detail


# ----------------------------------------------------------------------------
def eval_invariants(data):
    """dict 入力の invariants を netmodel で評価。戻り値: [{name,ok,points,detail}]。"""
    invariants = data.get("invariants") or []
    if not invariants:
        return []
    import netmodel
    return netmodel.evaluate_invariants(
        data.get("model", {}), data.get("ribs", {}),
        invariants, data.get("genie_os", "iosxe"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    gate = "--gate" in sys.argv
    data = json.load(open(args[0], encoding="utf-8"))

    # list = 従来（ノード単位 checks のみ） / dict = checks + invariants
    checks = data if isinstance(data, list) else (data.get("checks") or [])

    got = total = 0
    all_pass = True
    print("=" * 70)
    for r in checks:
        ok, detail = evaluate(r)
        total += r["points"]
        if ok:
            got += r["points"]
        else:
            all_pass = False
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] (+{r['points']:>3} 点) {r['name']}")
        if not ok:
            if detail.get("unmet"):
                for field, info in detail["unmet"].items():
                    print(f"        未充足: {field} "
                          f"期待={info['expected']} 実値={info['observed']}")
            if detail.get("raw_unmet"):
                for cond in detail["raw_unmet"]:
                    print(f"        未充足(raw): {cond}")
            if "reason" in detail:
                print(f"        未充足: {detail['reason']}")

    if isinstance(data, dict):
        for r in eval_invariants(data):
            total += r["points"]
            if r["ok"]:
                got += r["points"]
            else:
                all_pass = False
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"[{mark}] (+{r['points']:>3} 点) [大域] {r['name']}")
            if not r["ok"]:
                for f in (r["detail"].get("failures") or [])[:8]:
                    print(f"        未充足: {f}")

    print("=" * 70)
    print(f"  合計: {got} / {total} 点")
    print("=" * 70)

    if gate and not all_pass:
        sys.exit(3)


if __name__ == "__main__":
    main()
