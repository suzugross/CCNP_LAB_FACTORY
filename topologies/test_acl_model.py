#!/usr/bin/env python3
"""acl_model（ACL 意味評価器）のオフライン自己テスト。

CML を起動せずにパーサ＋評価器の正しさを検証する（test_netmodel.py の流儀）。
実行: .venv/bin/python3 topologies/test_acl_model.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl_model as am  # noqa: E402

PASSED = []


def check(cond, name):
    PASSED.append(bool(cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")


def tcp(src, sport, dst, dport, est=False):
    return {"proto": "tcp", "src": src, "sport": sport,
            "dst": dst, "dport": dport, "established": est}


def udp(src, sport, dst, dport):
    return {"proto": "udp", "src": src, "sport": sport,
            "dst": dst, "dport": dport}


def icmp(src, dst, t):
    return {"proto": "icmp", "src": src, "dst": dst, "icmp_type": t}


SHOW = """\
Standard IP access list 13
    10 deny   10.30.1.99 (3 matches)
    20 permit 10.30.1.0, wildcard bits 0.0.0.255
Standard IP access list ODD-SRC
    10 permit 10.40.1.0, wildcard bits 0.0.254.255
Extended IP access list 113
    10 permit tcp 10.30.1.0 0.0.0.255 host 172.22.5.10 eq www (12 matches)
    20 deny ip any any
Extended IP access list DOJO-5
    10 deny tcp any 10.30.2.0 0.0.0.255 eq telnet
    20 permit tcp any any established
    30 permit udp any eq domain any
    40 deny icmp any any echo
    50 permit icmp any any echo-reply
    60 permit tcp any host 172.22.5.10 range 8000 8080 log
    70 deny udp any 10.30.2.0 0.0.0.255 neq domain
    80 permit ip any any
"""


def test_parse():
    print("== パース ==")
    acls = am.parse_show_access_lists(SHOW)
    check(set(acls) == {"13", "ODD-SRC", "113", "DOJO-5"}, "4 ACL を認識")
    check(len(acls["DOJO-5"]) == 8, "DOJO-5 は 8 エントリ")
    e = acls["13"][0]
    check(e["action"] == "deny" and e["src_wild"] == 0, "標準: 裸ホスト表示 (matches 除去)")
    e = acls["ODD-SRC"][0]
    check(e["src_wild"] == am._ip("0.0.254.255"), "標準: wildcard bits 形式（非連続）")
    e = acls["113"][0]
    check(e["dport"] == ("eq", [80]), "拡張: ポート名 www→80")
    e = acls["DOJO-5"][2]
    check(e["sport"] == ("eq", [53]) and e["dport"] is None, "拡張: 送信元ポート eq domain")
    e = acls["DOJO-5"][5]
    check(e["dport"] == ("range", [8000, 8080]), "拡張: range＋log 末尾無視")
    check(acls["DOJO-5"][3]["icmp_type"] == 8, "icmp echo=8")
    check(acls["DOJO-5"][4]["icmp_type"] == 0, "icmp echo-reply=0")


def test_standard():
    print("== 標準 ACL（送信元のみ・first-match） ==")
    acls = am.parse_show_access_lists(SHOW)
    ent = acls["13"]
    check(not am.evaluate(ent, tcp("10.30.1.99", 1, "9.9.9.9", 80)), "deny host が先勝ち")
    check(am.evaluate(ent, udp("10.30.1.10", 1, "9.9.9.9", 53)), "subnet permit")
    check(not am.evaluate(ent, icmp("10.30.2.1", "9.9.9.9", 8)), "暗黙deny")


def test_noncontiguous_wildcard():
    print("== 非連続ワイルドカード（第3オクテット奇数） ==")
    ent = am.parse_show_access_lists(SHOW)["ODD-SRC"]
    check(am.evaluate(ent, tcp("10.40.1.5", 1, "9.9.9.9", 80)), "10.40.1.x 奇数=permit")
    check(am.evaluate(ent, tcp("10.40.255.7", 1, "9.9.9.9", 80)), "10.40.255.x 奇数=permit")
    check(not am.evaluate(ent, tcp("10.40.2.5", 1, "9.9.9.9", 80)), "10.40.2.x 偶数=deny")
    check(not am.evaluate(ent, tcp("10.41.1.5", 1, "9.9.9.9", 80)), "10.41.x は範囲外")


def test_extended():
    print("== 拡張 ACL（プロトコル/ポート/established/icmp） ==")
    acls = am.parse_show_access_lists(SHOW)
    e113 = acls["113"]
    check(am.evaluate(e113, tcp("10.30.1.10", 1, "172.22.5.10", 80)), "http permit")
    check(not am.evaluate(e113, tcp("10.30.1.10", 1, "172.22.5.10", 443)), "443 は deny")
    check(not am.evaluate(e113, udp("10.30.1.10", 1, "172.22.5.10", 80)), "udp/80 は deny")
    d5 = acls["DOJO-5"]
    check(not am.evaluate(d5, tcp("9.9.9.9", 1, "10.30.2.20", 23)), "telnet deny 先勝ち")
    check(am.evaluate(d5, tcp("9.9.9.9", 80, "10.30.1.10", 33000, est=True)),
          "established のみ permit")
    check(am.evaluate(d5, tcp("9.9.9.9", 1, "10.30.9.9", 23)),
          "LAN-B 以外の telnet は最後の permit ip")
    check(am.evaluate(d5, udp("8.8.8.8", 53, "10.30.1.10", 5353)), "src eq domain")
    check(not am.evaluate(d5, icmp("1.1.1.1", "2.2.2.2", 8)), "echo deny")
    check(am.evaluate(d5, icmp("1.1.1.1", "2.2.2.2", 0)), "echo-reply permit")
    check(am.evaluate(d5, icmp("1.1.1.1", "2.2.2.2", 3)), "他 icmp は permit ip")
    check(am.evaluate(d5, tcp("9.9.9.9", 1, "172.22.5.10", 8041)), "range 内 permit")
    check(not am.evaluate(d5, udp("9.9.9.9", 1, "10.30.2.20", 69)), "neq domain deny")
    check(am.evaluate(d5, udp("9.9.9.9", 1, "10.30.2.20", 53)), "domain は neq 不一致→permit")


def test_eval_acl_vectors():
    print("== grade.py 連携 (eval_acl_vectors) ==")
    spec = {"acl": "113",
            "vectors": [
                {"id": "v1", **tcp("10.30.1.10", 1, "172.22.5.10", 80),
                 "expect": "permit"},
                {"id": "v2", **tcp("10.30.1.10", 1, "172.22.5.10", 443),
                 "expect": "deny"}]}
    ok, detail = am.eval_acl_vectors(spec, SHOW)
    check(ok and not detail, "全ベクタ一致で PASS")
    spec["vectors"][1]["expect"] = "permit"
    ok, detail = am.eval_acl_vectors(spec, SHOW)
    check(not ok and detail["acl_mismatch"][0]["vector"] == "v2", "不一致ベクタを列挙")
    ok, detail = am.eval_acl_vectors({"acl": "NOEXIST", "vectors": []}, SHOW)
    check(not ok and "存在しない" in detail["reason"], "未定義 ACL は FAIL")
    ok, detail = am.eval_acl_vectors({"acl": "113", "vectors": []}, "")
    check(not ok, "空出力（未定義）は FAIL")


def main():
    for t in [test_parse, test_standard, test_noncontiguous_wildcard,
              test_extended, test_eval_acl_vectors]:
        t()
    print("=" * 60)
    n_ok, n = sum(1 for x in PASSED if x), len(PASSED)
    print(f"  {n_ok}/{n} アサート PASS")
    print("=" * 60)
    sys.exit(0 if n_ok == n else 1)


if __name__ == "__main__":
    main()
