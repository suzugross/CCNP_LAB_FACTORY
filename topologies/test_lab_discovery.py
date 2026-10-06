#!/usr/bin/env python3
"""発掘枠(BL-233)のオフライン自己テスト。

CML にもリポの台帳にも触らず、合成カタログと合成履歴で選定の性質を検証する:
一巡の保証(古い順)・種別の日替わり・台数予算・対象外の判定・単元ローテーションとの住み分け。

実行: .venv/bin/python3 topologies/test_lab_discovery.py
"""
import datetime
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pack as gp  # noqa: E402
import lab_rotation  # noqa: E402

D0 = datetime.date(2026, 10, 5)          # 月曜


def gen_row(script, prefix, desc="TS(4台・難4)", note=""):
    return {"script": script, "prefix": prefix, "desc": desc, "note": note,
            "diff": gp._diff_from_text(desc + " " + note), "kind": "generator", "pvt": False}


def static_row(pid, diff=4, tags=("ospf",), nodes=3, access="ssh", kind="normal"):
    return {"id": pid, "diff": diff, "tags": list(tags), "nodes": nodes, "access": access,
            "variant": "", "note": "", "kind": kind}


def catalog():
    return {
        "normal": [static_row("ENCOR-A-01"), static_row("ENCOR-B-01"), static_row("ENCOR-C-01"),
                   static_row("ENCOR-EASY-01", diff=2),
                   static_row("ENARSI-IPSEC-VTI-01", tags=("ipsec",)),      # ローテーション側(vpnbuild)
                   static_row("PVT-PAPER-01", nodes=0, access="紙面(機器なし)")],
        "auto": [static_row("ANSIBLE-01-INVENTORY", diff=3, tags=("automation", "ansible"), kind="auto")],
        "special": [{"id": "CAMPUS-TS-01", "diff": 5, "tags": ["ospf"], "nodes": 11,
                     "ops": "campus_ops.py", "note": "", "kind": "special"}],
        "gen": [],
        "generator": [
            gen_row("gen_alpha_ts.py", "GEN-ALPHA"),
            gen_row("gen_beta_ts.py", "GEN-BETA"),
            gen_row("gen_big_ts.py", "GEN-BIG", desc="大型 TS(12台・難5)"),
            gen_row("gen_held.py", "GEN-HELD"),
            gen_row("gen_old_ts.py", "GEN-OLD", note="新規出題はそちら推奨"),
            gen_row("gen_radius_build.py", "GEN-RADIUS", desc="FreeRADIUS 構築(3台・難4)"),
            gen_row("gen_dmvpn_ts.py", "GEN-DMVPN"),                       # ローテーション側(dmvpn)
            gen_row("gen_paper_mcq.py", "PVT-PAPERGEN"),
        ],
    }


def mode(slots=1, kinds=("generator", "static")):
    return {"name": "t", "slots": 3, "catchup_ratio": 2.0, "max_catchup": 1, "week": {},
            "units": {"vpn": {"label": "VPN", "per_week": 1, "genres": ["dmvpn", "vpnbuild"], "also": []}},
            "discovery": {"slots": slots, "min_diff": 3, "kinds": list(kinds),
                          "hold": {"GEN-HELD": "テスト用の保留"}, "args": {"GEN-ALPHA": ["--faults", "2"]}}}


def pick(cat, hist, day, repo, budget=40, used=0, m=None, count=1, seed=0):
    labs, notes, total = gp.select_discovery_labs(
        cat, hist, mode=m or mode(), count=count, budget=budget, used=used,
        rnd=random.Random(seed), today=day, repo=repo)
    return labs, notes, total


def test_pool_and_skips(repo):
    pool, skipped = gp.discovery_pool(catalog(), mode())
    ids = sorted(c["id"] for c in pool)
    assert ids == ["ENCOR-A-01", "ENCOR-B-01", "ENCOR-C-01", "GEN-ALPHA", "GEN-BETA", "GEN-BIG"], ids
    why = dict(skipped)
    assert "保留" in why["GEN-HELD"] and "後継" in why["GEN-OLD"] and why["GEN-RADIUS"] == "非 Cisco"
    assert why["ANSIBLE-01-INVENTORY"] == "自動化" and "専用 CLI" in why["CAMPUS-TS-01"]
    assert "難2" in why["ENCOR-EASY-01"]
    # ローテーション側の資産と紙面は、対象にも対象外の一覧にも出ない(発掘枠の管轄外)
    for pid in ("GEN-DMVPN", "ENARSI-IPSEC-VTI-01", "PVT-PAPER-01", "PVT-PAPERGEN"):
        assert pid not in ids and pid not in why, pid
    # 除外方針の解除フラグ
    pool2, _ = gp.discovery_pool(catalog(), mode(), allow_non_cisco=True, allow_automation=True)
    assert {"GEN-RADIUS", "ANSIBLE-01-INVENTORY"} <= {c["id"] for c in pool2}


def test_cycle_guarantee(repo):
    """毎日 1 本で回すと、候補 6 件が「種別ごとの件数 × 種別数」日以内に必ず全部出る。"""
    cat, hist, seen_days = catalog(), [], {}
    kinds_by_day = []
    for i in range(12):
        day = D0 + datetime.timedelta(days=i)
        labs, _, _ = pick(cat, hist, day, repo, seed=i)
        assert len(labs) == 1
        lb = labs[0]
        kinds_by_day.append(lb["source"])
        seen_days.setdefault(lb["id"], []).append(i)
        # 生成器は新 seed の ID で履歴に載る・静的は ID そのまま
        hist.append((day.isoformat(), f"{lb['id']}-{1000 + i}" if lb["source"] == "generator" else lb["id"]))
    assert len(seen_days) == 6, seen_days                       # 全件が出た
    assert all(d[0] < 6 for d in seen_days.values()), seen_days  # 最初の 6 日で一巡
    assert all(a != b for a, b in zip(kinds_by_day, kinds_by_day[1:])), kinds_by_day   # 日替わりで交互
    for pid, days in seen_days.items():                         # 2 周目は同じ間隔(= 古い順が保たれている)
        assert len(days) == 2 and days[1] - days[0] == 6, (pid, days)


def test_oldest_first_not_random(repo):
    """乱数の種を変えても、出題記録が最も古い候補が必ず先に出る。"""
    cat = catalog()
    hist = [("2026-09-01", "GEN-ALPHA-1"), ("2026-08-01", "GEN-BETA-2"), ("2026-09-20", "GEN-BIG-3")]
    day = next(D0 + datetime.timedelta(days=i) for i in range(2)
               if (D0 + datetime.timedelta(days=i)).toordinal() % 2 == 0)       # 生成器の日
    for seed in range(20):
        labs, _, _ = pick(cat, hist, day, repo, seed=seed)
        assert labs[0]["id"] == "GEN-BETA", (seed, labs[0]["id"])
    hist.append((day.isoformat(), "GEN-BETA-9"))
    labs, _, _ = pick(cat, hist, day + datetime.timedelta(days=2), repo)
    assert labs[0]["id"] == "GEN-ALPHA" and labs[0]["args"] == ["--faults", "2"]   # mode の args が付く


def test_args_variants(repo):
    """args に組を並べたら、その中の 1 組だけが付く。"""
    m = mode()
    m["discovery"]["args"]["GEN-ALPHA"] = [["--fault", "a"], ["--fault", "b"]]
    day = next(D0 + datetime.timedelta(days=i) for i in range(2)
               if (D0 + datetime.timedelta(days=i)).toordinal() % 2 == 0)
    hist = [("2026-09-01", "GEN-BETA-2"), ("2026-09-02", "GEN-BIG-3")]
    got = {tuple(pick(catalog(), hist, day, repo, m=m, seed=s)[0][0]["args"]) for s in range(30)}
    assert got == {("--fault", "a"), ("--fault", "b")}, got


def test_prefix_boundary(repo):
    """`GEN-ALPHA` の出題が `GEN-ALPHAX-…` と混同されない。多段の接頭辞も拾う。"""
    a = {"id": "GEN-ALPHA", "source": "generator"}
    assert gp._issued_as("GEN-ALPHA-12", a) and gp._issued_as("GEN-ALPHA-SUB-12", a)
    assert not gp._issued_as("GEN-ALPHAX-12", a)
    assert gp._issued_as("ENCOR-A-01", {"id": "ENCOR-A-01", "source": "static"})
    assert not gp._issued_as("ENCOR-A-01-X", {"id": "ENCOR-A-01", "source": "static"})


def test_budget_defers_not_drops(repo):
    """台数予算に入らない大型は飛ばすが、待ち行列の先頭に残り、入る日に出る。"""
    cat = catalog()
    hist = [("2026-09-01", "GEN-ALPHA-1"), ("2026-09-02", "GEN-BETA-2")]      # GEN-BIG が最古(記録なし)
    day = next(D0 + datetime.timedelta(days=i) for i in range(2)
               if (D0 + datetime.timedelta(days=i)).toordinal() % 2 == 0)
    labs, notes, total = pick(cat, hist, day, repo, budget=20, used=10)
    assert labs[0]["id"] == "GEN-ALPHA" and total == 4
    assert any("GEN-BIG" in n and "次回へ" in n for n in notes), notes
    labs, _, _ = pick(cat, hist, day, repo, budget=40, used=10)
    assert labs[0]["id"] == "GEN-BIG" and labs[0]["nodes"] == 12
    # その種別が 1 つも入らなければ、もう一方の種別から出す
    labs, _, _ = pick({**cat, "generator": [g for g in cat["generator"] if g["prefix"] == "GEN-BIG"]},
                      hist, day, repo, budget=20, used=10)
    assert labs[0]["source"] == "static"


def test_manifest_key_tracks_mismatched_ids(repo):
    """生成器が接頭辞と違う ID を書いても、発掘枠が控えたキー(manifest の pool)で古い順が進む。"""
    cat = catalog()
    day = next(D0 + datetime.timedelta(days=i) for i in range(2)
               if (D0 + datetime.timedelta(days=i)).toordinal() % 2 == 0)
    hist = [("2026-09-01", "GEN-BETA-2"), ("2026-09-02", "GEN-BIG-3")]
    labs, _, _ = pick(cat, hist, day, repo)
    assert labs[0]["id"] == "GEN-ALPHA"                       # 記録なしが最優先
    pdir = os.path.join(repo, "packs", "PACK-T1")
    os.makedirs(pdir)
    item = {"no": 1, "kind": "lab", "ref": "GEN-RENAMED-777", "nodes": 4, "state": "未着手",
            "genre": "discovery", "pool": "GEN-ALPHA"}
    gp.write_manifest(pdir, {"pack_id": "PACK-T1", "created": day.isoformat(), "dry_run": False,
                             "seed": 1, "items": [item], "notes": []})
    hist.append((day.isoformat(), "GEN-RENAMED-777"))        # 履歴の ID は接頭辞と突き合わない
    labs, _, _ = pick(cat, hist, day + datetime.timedelta(days=2), repo)
    assert labs[0]["id"] == "GEN-BETA", labs[0]["id"]
    # dry-run と構築失敗は「出した」に数えない
    for name, extra in (("PACK-T2", {"dry_run": True}), ("PACK-T3", {"error": "x"})):
        pdir = os.path.join(repo, "packs", name)
        os.makedirs(pdir)
        it = dict(item, pool="GEN-BETA", **({"error": "構築失敗"} if "error" in extra else {}))
        gp.write_manifest(pdir, {"pack_id": name, "created": (day + datetime.timedelta(days=1)).isoformat(),
                                 "dry_run": bool(extra.get("dry_run")), "seed": 1, "items": [it], "notes": []})
    assert "GEN-BETA" not in gp.discovery_last_issued(repo)


def test_rotation_slots_and_exclude(repo):
    m = lab_rotation.load_mode(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "default")
    n = lab_rotation.rotation_slots(m)
    assert n == m["slots"] - m["discovery"]["slots"] >= 1
    # 曜日表は毎日ちょうど単元枠の本数・週回数の合計と一致(表が不動点になる条件)
    assert all(len(v) == n for v in m["week"].values()), m["week"]
    per = {u: sum(u in v for v in m["week"].values()) for u in m["units"]}
    assert per == {u: s["per_week"] for u, s in m["units"].items()}, per
    for a, b in zip(list(m["week"].values()), list(m["week"].values())[1:] + list(m["week"].values())[:1]):
        assert not set(a) & set(b), (a, b)                      # 同じ単元が 2 日続かない
    seen = {u: (D0 - datetime.timedelta(days=3), "採点") for u in m["units"]}
    picks, fallback, info = lab_rotation.plan_units(m, D0, seen)
    assert picks == m["week"]["mon"] or set(picks) == set(m["week"]["mon"])
    ex = picks[0]
    picks2, fallback2, info2 = lab_rotation.plan_units(m, D0, seen, exclude=[ex])
    assert ex not in picks2 and ex not in fallback2 and len(picks2) == n
    assert "発掘枠" in info2["why"][ex]


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "packs"))
            t(repo)
        print(f"ok  {t.__name__}")
    print(f"全 {len(tests)} 件 PASS")


if __name__ == "__main__":
    main()
