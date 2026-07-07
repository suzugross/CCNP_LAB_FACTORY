#!/usr/bin/env python3
"""値ランダム化生成器（パラメータ化 Stage 1）。

problems/<id>/params/_gen.yml（各 param の種別スキーマ）と seed から、制約を満たす
ランダムな params/<variant>.yml を生成する。seed が同じなら同じ問題＝再現可能。
既存の initial/*.cfg.j2・grading.yml.j2・task.md.j2 がそのまま消費する。

種別(kind):
  asn        : 私用AS 64512-65534（全体で重複なし）
  loopback   : n.n.n.n 形式の /32（n は 1-99 で 10 を除外・重複なし）
  seg30      : "10.x.y"（A.B.C を返す。実体は A.B.C.0/30, .1/.2 がホスト）。
               mgmt 10.1.10.0/26 を避け、全体で重複なし
  net24      : "203.0.x.0"（外部/公開風の /24 ネットワークアドレス。重複なし）
  pid        : 1-100 の整数（重複可）
  police_bps : CoPP police 用の bps。8000 の倍数 (8000-128000)・重複なし
  {const: V} : 固定値 V（例 area: 0）
  {fmt: S}   : 派生値。他 param を {name} で参照する format 文字列
               （例 comm_a: {fmt: "{as_cust}:100"} → ランダム化した AS に追従）

_gen.yml に無いキーは params/base.yml の値をそのまま引き継ぐ（variant は自己完結
ファイルとして出力される＝ build/grade 側にマージ機構は不要）。

使い方:
  gen_params.py --repo <repo> --problem <id> --seed <int> [--variant <name>]
    省略時 variant = "s<seed>"。出力: problems/<id>/params/<variant>.yml
"""
import argparse
import random
import sys

import yaml


class Pools:
    """全 param 間で重複しないよう値を払い出す。"""
    def __init__(self, rnd):
        self.rnd = rnd
        self.asn = set()
        self.lo = set()
        self.seg = set()
        self.net = set()
        self.rate = set()

    def make_asn(self):
        while True:
            v = self.rnd.randint(64512, 65534)
            if v not in self.asn:
                self.asn.add(v)
                return v

    def make_loopback(self):
        while True:
            n = self.rnd.randint(1, 99)
            if n == 10 or n in self.lo:
                continue
            self.lo.add(n)
            return f"{n}.{n}.{n}.{n}"

    def make_seg30(self):
        while True:
            x = self.rnd.randint(0, 254)
            y = self.rnd.randint(0, 254)
            if (x, y) == (1, 10):       # mgmt 10.1.10.0/26 を避ける
                continue
            if (x, y) in self.seg:
                continue
            self.seg.add((x, y))
            return f"10.{x}.{y}"

    def make_net24(self):
        # 外部/公開風の /24（203.0.x.0）。seg30 等の 10.x と重ならない空間。
        while True:
            x = self.rnd.randint(0, 255)
            if x in self.net:
                continue
            self.net.add(x)
            return f"203.0.{x}.0"

    def make_police(self):
        # CoPP police cir は 8000 bps 単位。8000-128000 から重複なしで払い出す。
        while True:
            v = self.rnd.randint(1, 16) * 8000
            if v in self.rate:
                continue
            self.rate.add(v)
            return v


def generate(schema, seed, base=None):
    rnd = random.Random(seed)
    pools = Pools(rnd)
    out = dict(base or {})   # _gen.yml に無いキーは base.yml の値を引き継ぐ
    fmts = {}
    # 決定論のためキー順に処理（fmt は他キー確定後に評価）
    for name, kind in schema.items():
        if isinstance(kind, dict) and "const" in kind:
            out[name] = kind["const"]
        elif isinstance(kind, dict) and "fmt" in kind:
            fmts[name] = kind["fmt"]
        elif kind == "asn":
            out[name] = pools.make_asn()
        elif kind == "loopback":
            out[name] = pools.make_loopback()
        elif kind == "seg30":
            out[name] = pools.make_seg30()
        elif kind == "net24":
            out[name] = pools.make_net24()
        elif kind == "pid":
            out[name] = rnd.randint(1, 100)
        elif kind == "police_bps":
            out[name] = pools.make_police()
        else:
            raise ValueError(f"unknown kind for {name}: {kind}")
    for name, fmt in fmts.items():
        out[name] = fmt.format(**out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--variant")
    a = ap.parse_args()

    schema_path = f"{a.repo}/problems/{a.problem}/params/_gen.yml"
    with open(schema_path, encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    base = {}
    base_path = f"{a.repo}/problems/{a.problem}/params/base.yml"
    try:
        with open(base_path, encoding="utf-8") as f:
            base = yaml.safe_load(f) or {}
    except FileNotFoundError:
        pass

    values = generate(schema, a.seed, base=base)
    variant = a.variant or f"s{a.seed}"
    out_path = f"{a.repo}/problems/{a.problem}/params/{variant}.yml"
    header = (f"# 自動生成 (gen_params.py) problem={a.problem} seed={a.seed}\n"
              f"# 同じ seed なら同じ値＝再現可能。手で編集せず seed で再生成すること。\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(values, f, sort_keys=False, default_flow_style=False)

    print(f"wrote {out_path} (variant={variant}, seed={a.seed})")
    for k, v in values.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
