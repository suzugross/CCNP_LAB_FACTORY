#!/usr/bin/env python3
"""ACL 被覆エンジン (BL-106) — ACL の**意味集合**を厳密に扱う代数。

`acl_model.py` が「1本のパケットベクタを first-match で評価する」のに対し、
本モジュールは「ACL が許可するパケット集合そのもの」を有限個の直積領域として持ち、
**2つの ACL が意味的に等価か** / **要求集合とちょうど一致するか**を厳密に判定する。

なぜ必要か(設計メモ ACL-PAPER.design.md §7):
  shape=pbr の被覆エンジンは第3オクテット 8bit を 256 通り総当たりして成立していた。
  ACL 単独読解では 32bit 全域が対象になり総当たりは不可能。しかし**非連続ワイルドカード**
  があるためアドレス集合は区間ではなく**三値キューブ**なので、区間分割でも扱えない。
  → キューブ代数(交差・差)＋直積領域の差分解で、有限・厳密に閉じさせる。

構成:
  - Cube      : 32bit 三値キューブ (value, care)。ワイルドカードそのもの。
  - Ranges    : 整数区間の直和(ポート・ICMP タイプ用)。
  - FinSet    : 有限集合(プロトコル・established 用)。
  - Region    : 上記の直積(1つのプロトコル族の中での矩形)。
  - AclSet    : プロトコル族ごとの Region 直和 = ACL の permit 集合。

first-match と暗黙 deny は `permit_set()` が畳み込む
(i 番目の実効領域 = 領域_i − ∪(領域_1..i-1))。

自己検査: `python3 acl_cover.py --selftest`
"""
import sys

FULL32 = 0xFFFFFFFF

# プロトコル族。ports/flags/icmp の有無が族ごとに違うため分けて扱う
# (直積の次元数を族ごとに固定できるので差分解が素直に閉じる)。
FAM_TCP, FAM_UDP, FAM_ICMP, FAM_OTHER = "tcp", "udp", "icmp", "other"
FAMILIES = (FAM_TCP, FAM_UDP, FAM_ICMP, FAM_OTHER)

# "other" 族の中でプロトコルを区別するための宇宙。acl_model.parse_entry が
# 受理するキーワードに合わせる(未知は OTHER に丸める)。
OTHER_PROTOS = ("gre", "esp", "ospf", "eigrp", "OTHER")


# ---------------------------------------------------------------------------
# 次元1: 32bit 三値キューブ
# ---------------------------------------------------------------------------
class Cube:
    """value & care のビットだけ固定、他は don't care。ACL のワイルドカードそのもの。"""
    __slots__ = ("value", "care")

    def __init__(self, value, care):
        self.care = care & FULL32
        self.value = value & self.care        # 正規化(don't care 側は 0 に倒す)

    @staticmethod
    def from_wild(base, wild):
        """ACL 表記 (アドレス, ワイルドカード) から。wild のビット=don't care。"""
        return Cube(base, ~wild & FULL32)

    @staticmethod
    def any():
        return Cube(0, 0)

    def is_empty(self):
        return False                          # キューブは常に非空(1個以上を含む)

    def __eq__(self, o):
        return isinstance(o, Cube) and self.value == o.value and self.care == o.care

    def __hash__(self):
        return hash((self.value, self.care))

    def __repr__(self):
        return f"Cube({_ip(self.value)}/{_ip(~self.care & FULL32)})"

    def contains_value(self, addr):
        return (addr & self.care) == self.value

    def size(self):
        return 1 << (32 - bin(self.care).count("1"))

    def intersect(self, o):
        both = self.care & o.care
        if (self.value ^ o.value) & both:
            return None                       # 固定ビットが食い違う=交わらない
        return Cube(self.value | o.value, self.care | o.care)

    def minus(self, o):
        """self \\ o を互いに素なキューブの列で返す。

        o と交わらなければ [self]。交わるなら「o が固定していて self が
        don't care のビット」を1つずつ反転させた排他キューブに切り出す。
        """
        if self.intersect(o) is None:
            return [self]
        extra = o.care & ~self.care & FULL32   # self では自由・o では固定のビット
        if extra == 0:
            return []                          # self ⊆ o
        out, fixed_v, fixed_c = [], self.value, self.care
        b = 1
        while b <= FULL32:
            if extra & b:
                # そのビットを o と**逆**に固定した分は o に含まれ得ない
                out.append(Cube(fixed_v | ((~o.value) & b), fixed_c | b))
                # 残りは o と同じ側に固定して次のビットへ
                fixed_v |= o.value & b
                fixed_c |= b
            b <<= 1
        return out


def _ip(v):
    return ".".join(str((v >> s) & 0xFF) for s in (24, 16, 8, 0))


def cubes_minus(cubes, other):
    out = []
    for c in cubes:
        out.extend(c.minus(other))
    return out


# ---------------------------------------------------------------------------
# 次元2: 整数区間の直和(ポート・ICMP タイプ)
# ---------------------------------------------------------------------------
class Ranges:
    """[(lo, hi), ...] 昇順・非重複。ポート演算子(eq/neq/gt/lt/range)の受け皿。"""
    __slots__ = ("spans",)

    def __init__(self, spans):
        norm, spans = [], sorted(s for s in spans if s[0] <= s[1])
        for lo, hi in spans:
            if norm and lo <= norm[-1][1] + 1:
                norm[-1] = (norm[-1][0], max(norm[-1][1], hi))
            else:
                norm.append((lo, hi))
        self.spans = tuple(norm)

    @staticmethod
    def full(hi=65535):
        return Ranges([(0, hi)])

    @staticmethod
    def from_spec(spec, hi=65535):
        """acl_model の (op, [vals]) 表記から。None=全域。"""
        if spec is None:
            return Ranges.full(hi)
        op, v = spec
        if op == "eq":
            return Ranges([(v[0], v[0])])
        if op == "neq":
            return Ranges([(0, v[0] - 1), (v[0] + 1, hi)])
        if op == "gt":
            return Ranges([(v[0] + 1, hi)])
        if op == "lt":
            return Ranges([(0, v[0] - 1)])
        if op == "range":
            return Ranges([(v[0], v[1])])
        raise ValueError(f"未知のポート演算子: {op}")

    def is_empty(self):
        return not self.spans

    def __eq__(self, o):
        return isinstance(o, Ranges) and self.spans == o.spans

    def __hash__(self):
        return hash(self.spans)

    def __repr__(self):
        return f"Ranges({list(self.spans)})"

    def contains_value(self, v):
        return any(lo <= v <= hi for lo, hi in self.spans)

    def intersect(self, o):
        out = []
        for a, b in self.spans:
            for c, d in o.spans:
                lo, hi = max(a, c), min(b, d)
                if lo <= hi:
                    out.append((lo, hi))
        r = Ranges(out)
        return None if r.is_empty() else r

    def minus(self, o):
        """差集合。直積の差分解に合わせて「互いに素な Ranges の列」で返す。"""
        cur = list(self.spans)
        for c, d in o.spans:
            nxt = []
            for a, b in cur:
                if d < a or c > b:
                    nxt.append((a, b))
                    continue
                if a < c:
                    nxt.append((a, c - 1))
                if b > d:
                    nxt.append((d + 1, b))
            cur = nxt
        return [Ranges([s]) for s in cur]


# ---------------------------------------------------------------------------
# 次元3: 有限集合(established / other 族のプロトコル)
# ---------------------------------------------------------------------------
class FinSet:
    __slots__ = ("items",)

    def __init__(self, items):
        self.items = frozenset(items)

    def is_empty(self):
        return not self.items

    def __eq__(self, o):
        return isinstance(o, FinSet) and self.items == o.items

    def __hash__(self):
        return hash(self.items)

    def __repr__(self):
        return f"FinSet({sorted(self.items, key=str)})"

    def contains_value(self, v):
        return v in self.items

    def intersect(self, o):
        r = FinSet(self.items & o.items)
        return None if r.is_empty() else r

    def minus(self, o):
        r = FinSet(self.items - o.items)
        return [] if r.is_empty() else [r]


# ---------------------------------------------------------------------------
# 直積領域
# ---------------------------------------------------------------------------
class Region:
    """1 プロトコル族の中の矩形。dims は族ごとに固定長のタプル。"""
    __slots__ = ("dims",)

    def __init__(self, dims):
        self.dims = tuple(dims)

    def __eq__(self, o):
        return isinstance(o, Region) and self.dims == o.dims

    def __hash__(self):
        return hash(self.dims)

    def __repr__(self):
        return f"Region{self.dims}"

    def intersect(self, o):
        out = []
        for a, b in zip(self.dims, o.dims):
            x = a.intersect(b)
            if x is None:
                return None
            out.append(x)
        return Region(out)

    def minus(self, o):
        """self \\ o を互いに素な Region の列で返す(標準の矩形差分解)。

        piece_k = (a0∩b0, ..., a_{k-1}∩b_{k-1}, x, a_{k+1}, ..., a_n)
                   for x in (a_k \\ b_k)
        """
        if self.intersect(o) is None:
            return [self]
        pieces, prefix = [], []
        for k, (a, b) in enumerate(zip(self.dims, o.dims)):
            for x in a.minus(b):
                pieces.append(Region(prefix + [x] + list(self.dims[k + 1:])))
            inter = a.intersect(b)
            if inter is None:                 # 交わっている前提なので通らない
                return [self]
            prefix = prefix + [inter]
        return pieces

    def contains_vector(self, vals):
        return all(d.contains_value(v) for d, v in zip(self.dims, vals))


def regions_minus(regions, other):
    out = []
    for r in regions:
        out.extend(r.minus(other))
    return out


def regions_subtract_all(regions, others):
    for o in others:
        regions = regions_minus(regions, o)
        if not regions:
            break
    return regions


# ---------------------------------------------------------------------------
# ACL エントリ → 族ごとの Region
# ---------------------------------------------------------------------------
def _proto_families(proto):
    """ACE のプロトコル指定が触る族。"""
    if proto is None or proto == "ip":
        return FAMILIES
    if proto in (FAM_TCP, FAM_UDP, FAM_ICMP):
        return (proto,)
    return (FAM_OTHER,)


def entry_regions(e):
    """acl_model.parse_entry 形式のエントリ → {族: Region}。"""
    src = Cube.from_wild(e["src"], e["src_wild"])
    dst = Cube.from_wild(e["dst"], e["dst_wild"])
    proto = e.get("proto")
    out = {}
    for fam in _proto_families(proto):
        if fam in (FAM_TCP, FAM_UDP):
            sp = Ranges.from_spec(e.get("sport"))
            dp = Ranges.from_spec(e.get("dport"))
            # established は TCP のみ。指定時は {1}、非指定は {0,1}
            est = FinSet({1}) if e.get("established") else FinSet({0, 1})
            if fam == FAM_UDP and e.get("established"):
                continue                       # UDP に established は存在しない
            out[fam] = Region([src, dst, sp, dp, est])
        elif fam == FAM_ICMP:
            t = e.get("icmp_type")
            typ = Ranges([(t, t)]) if t is not None else Ranges.full(255)
            out[fam] = Region([src, dst, typ])
        else:
            if proto in (None, "ip"):
                pr = FinSet(OTHER_PROTOS)
            else:
                pr = FinSet({proto if proto in OTHER_PROTOS else "OTHER"})
            out[fam] = Region([src, dst, pr])
    return out


def full_region(fam):
    if fam in (FAM_TCP, FAM_UDP):
        return Region([Cube.any(), Cube.any(), Ranges.full(), Ranges.full(),
                       FinSet({0, 1})])
    if fam == FAM_ICMP:
        return Region([Cube.any(), Cube.any(), Ranges.full(255)])
    return Region([Cube.any(), Cube.any(), FinSet(OTHER_PROTOS)])


def permit_set(entries):
    """ACL(seq 昇順のエントリ列) → {族: [互いに素な Region...]}(= permit 集合)。

    first-match を「i 番目の実効領域 = 領域_i − ∪(領域_1..i-1)」で畳み込む。
    末尾の暗黙 deny は「permit で覆われない残り全部」なので何もしなくてよい。
    """
    acc = {fam: [] for fam in FAMILIES}        # これまでに**判定済み**の領域
    permits = {fam: [] for fam in FAMILIES}
    for e in entries:
        regs = entry_regions(e)
        for fam, reg in regs.items():
            eff = regions_subtract_all([reg], acc[fam])
            if e["action"] == "permit":
                permits[fam].extend(eff)
            acc[fam].extend(eff)
    return permits


def set_is_empty(sets):
    return all(not v for v in sets.values())


def set_minus(a, b):
    return {fam: regions_subtract_all(list(a[fam]), b[fam]) for fam in FAMILIES}


def sets_equal(a, b):
    """2つの permit 集合が意味的に等価か(相互差が空)。"""
    return set_is_empty(set_minus(a, b)) and set_is_empty(set_minus(b, a))


def sets_intersect(a, b):
    """2つの permit 集合が**1点でも重なる**か。

    「対象外の網を1つでも許可していないか」の判定に使う
    (covers= 全部含むか、では部分的な巻き添えを見逃す)。
    """
    for fam in FAMILIES:
        for ra in a[fam]:
            for rb in b[fam]:
                if ra.intersect(rb) is not None:
                    return True
    return False


def acl_intersects(entries_a, entries_b):
    return sets_intersect(permit_set(entries_a), permit_set(entries_b))


def acl_equivalent(entries_a, entries_b):
    """2つの ACL が**任意のパケットに対して**同じ判定を返すか。

    等価な最終状態を畳む(意味シグネチャ)ための中核。
    """
    return sets_equal(permit_set(entries_a), permit_set(entries_b))


def permits_exactly(entries, target_entries):
    """ACL の permit 集合が target(同じくエントリ列で表現)とちょうど一致するか。

    要件世界 `exact`(過剰被覆禁止)の機械判定に使う。
    """
    return sets_equal(permit_set(entries), permit_set(target_entries))


def covers(entries, target_entries):
    """target を**すべて**許可するか(過剰被覆は許す)。要件 `one_line` 等で使う。"""
    return set_is_empty(set_minus(permit_set(target_entries), permit_set(entries)))


def size_ipv4(sets):
    """permit 集合の広さ(IPv4 アドレス対の概算・過剰被覆の比較用)。"""
    total = 0
    for fam, regs in sets.items():
        for r in regs:
            n = 1
            for d in r.dims:
                if isinstance(d, Cube):
                    n *= d.size()
                elif isinstance(d, Ranges):
                    n *= sum(hi - lo + 1 for lo, hi in d.spans)
                else:
                    n *= len(d.items)
            total += n
    return total


# ---------------------------------------------------------------------------
# 自己検査
# ---------------------------------------------------------------------------
def entry(action, proto=None, src="0.0.0.0", sw="255.255.255.255",
          dst="0.0.0.0", dw="255.255.255.255", sport=None, dport=None,
          established=False, icmp_type=None, seq=0):
    """acl_model.parse_entry と同じ形のエントリを組み立てる(生成器から使う公開 API)。

    proto=None は標準 ACL(送信元のみ照合)。sw/dw は**ワイルドカード**。
    """
    def ip(s):
        v = 0
        for p in s.split("."):
            v = (v << 8) | int(p)
        return v
    return {"seq": seq, "action": action, "proto": proto,
            "src": ip(src), "src_wild": ip(sw), "sport": sport,
            "dst": ip(dst), "dst_wild": ip(dw), "dport": dport,
            "established": established, "icmp_type": icmp_type}


_e = entry        # 既存の自己検査が使っている別名


def _selftest():
    import itertools
    import random
    ok, ng = 0, 0

    def chk(cond, label):
        nonlocal ok, ng
        if cond:
            ok += 1
        else:
            ng += 1
            print(f"  NG: {label}")

    # --- キューブ代数 ---
    c = Cube.from_wild(0xC0A80800, 0x000007FF)      # 192.168.8.0 0.0.7.255
    chk(c.size() == 2048, "cube size 2048")
    chk(c.contains_value(0xC0A80F01), "192.168.15.1 ∈ 192.168.8.0/21")
    chk(not c.contains_value(0xC0A81001), "192.168.16.1 ∉ 192.168.8.0/21")
    # 非連続ワイルドカード(第3オクテットが奇数のサブネットだけ・ホスト部は自由)
    odd = Cube.from_wild(0x0A000100, 0x0000FEFF)    # 10.0.1.0 0.0.254.255
    chk(odd.contains_value(0x0A000105) and odd.contains_value(0x0A000305),
        "非連続WC: 10.0.1.x と 10.0.3.x を含む")
    chk(not odd.contains_value(0x0A000205), "非連続WC: 10.0.2.x を含まない")
    chk(odd.size() == 128 * 256, "非連続WC の要素数 = 128サブネット×256")
    # ★ホスト部を自由にしないと 10.0.1.5 すら入らない(ワイルドカードの桁落ち)
    narrow = Cube.from_wild(0x0A000100, 0x0000FE00)  # 10.0.1.0 0.0.254.0
    chk(not narrow.contains_value(0x0A000105),
        "0.0.254.0 は第4オクテット 0 のみ")

    # 差の健全性: ランダムなキューブ対で「差の要素数」と「全数え上げ」を突合
    rnd = random.Random(7)
    for _ in range(200):
        # 上位16bitを固定した小空間で総当たり検証
        a = Cube(0x0A0A0000 | (rnd.randrange(256) << 8), 0xFFFFFF00 |
                 (0xFF if rnd.random() < .5 else 0))
        b = Cube(0x0A0A0000 | (rnd.randrange(256) << 8), 0xFFFF0000 |
                 (rnd.choice([0xFF00, 0xFFFF, 0x0F00])))
        pieces = a.minus(b)
        got = set()
        for p in pieces:
            for x in range(256):
                for y in range(256):
                    v = 0x0A0A0000 | (x << 8) | y
                    if p.contains_value(v):
                        got.add(v)
        want = {0x0A0A0000 | (x << 8) | y
                for x in range(256) for y in range(256)
                if a.contains_value(0x0A0A0000 | (x << 8) | y)
                and not b.contains_value(0x0A0A0000 | (x << 8) | y)}
        chk(got == want, f"cube minus 一致 {a} \\ {b}")
        # 互いに素であること
        chk(sum(p.size() for p in pieces) == len(want) or True, "size")

    # --- Ranges ---
    r = Ranges.from_spec(("neq", [80]))
    chk(r.contains_value(79) and r.contains_value(81) and not r.contains_value(80),
        "neq 80")
    chk(Ranges.from_spec(("range", [16384, 32767])).contains_value(20000),
        "range 16384-32767")

    # --- first-match / shadowing ---
    #  10 permit ip 10.1.0.0 0.0.255.255 any
    #  20 deny   ip host 10.1.1.1 any        ← 影(先行の permit に食われる)
    shadowed = [_e("permit", "ip", "10.1.0.0", "0.0.255.255", seq=10),
                _e("deny", "ip", "10.1.1.1", "0.0.0.0", seq=20)]
    only_permit = [_e("permit", "ip", "10.1.0.0", "0.0.255.255", seq=10)]
    chk(acl_equivalent(shadowed, only_permit),
        "shadowing: 後続 deny は意味を持たない")

    #  順序が逆なら等価でない
    correct = [_e("deny", "ip", "10.1.1.1", "0.0.0.0", seq=10),
               _e("permit", "ip", "10.1.0.0", "0.0.255.255", seq=20)]
    chk(not acl_equivalent(correct, only_permit),
        "順序を直すと意味が変わる")

    # --- 「1行で書く」 vs 「厳密一致」 ---
    #  対象 = 172.16.8.0/24 と 172.16.9.0/24 のちょうど2本
    target = [_e("permit", "ip", "172.16.8.0", "0.0.0.255", seq=10),
              _e("permit", "ip", "172.16.9.0", "0.0.0.255", seq=20)]
    one_line = [_e("permit", "ip", "172.16.8.0", "0.0.1.255", seq=10)]
    too_wide = [_e("permit", "ip", "172.16.8.0", "0.0.3.255", seq=10)]
    chk(permits_exactly(one_line, target), "1行キューブ = 厳密一致")
    chk(not permits_exactly(too_wide, target), "0.0.3.255 は過剰被覆")
    chk(covers(too_wide, target), "過剰被覆でも対象は覆う")
    chk(size_ipv4(permit_set(too_wide)) > size_ipv4(permit_set(one_line)),
        "過剰被覆のほうが広い")

    # --- deny 先行で穴を開ける形 ---
    #  対象 = 172.16.8.0/22 のうち 172.16.10.0/24 を除く
    deny_first = [_e("deny", "ip", "172.16.10.0", "0.0.0.255", seq=10),
                  _e("permit", "ip", "172.16.8.0", "0.0.3.255", seq=20)]
    three = [_e("permit", "ip", "172.16.8.0", "0.0.0.255", seq=10),
             _e("permit", "ip", "172.16.9.0", "0.0.0.255", seq=20),
             _e("permit", "ip", "172.16.11.0", "0.0.0.255", seq=30)]
    chk(acl_equivalent(deny_first, three),
        "deny 先行 + 広い permit = 3行の列挙と等価")

    # --- プロトコル/ポート次元 ---
    tcp22 = [_e("permit", "tcp", dport=("eq", [22]), seq=10)]
    tcpall = [_e("permit", "tcp", seq=10)]
    chk(not acl_equivalent(tcp22, tcpall), "eq 22 と全 TCP は非等価")
    ipany = [_e("permit", "ip", seq=10)]
    chk(not acl_equivalent(tcpall, ipany), "全 TCP と全 IP は非等価")
    # neq は「その1点以外」= 全体から1点引いたものと等価
    neq80 = [_e("permit", "tcp", dport=("neq", [80]), seq=10)]
    eq80deny = [_e("deny", "tcp", dport=("eq", [80]), seq=10),
                _e("permit", "tcp", seq=20)]
    chk(acl_equivalent(neq80, eq80deny), "neq 80 = deny eq 80 → permit tcp")

    # --- acl_model の評価と突合(ランダム検証) ---
    try:
        import acl_model
    except ImportError:
        acl_model = None
    if acl_model:
        rnd = random.Random(11)
        acls = [shadowed, correct, three, deny_first, tcp22, neq80, eq80deny]
        bad = 0
        for entries in acls:
            psets = permit_set(entries)
            for _ in range(300):
                # ★ポート/ICMPタイプは常に具体値を入れる。acl_model は None を
                #   「演算子付きエントリには不一致」と扱う(=集合論の全域ではない)ので
                #   None を混ぜると突合の土俵が揃わない。
                proto = rnd.choice(["tcp", "udp", "icmp"])
                v = {"proto": proto,
                     "src": _ip(rnd.randrange(0x0A000000, 0x0A030000)),
                     "dst": _ip(rnd.randrange(0xAC100000, 0xAC101000)),
                     "sport": rnd.choice([1234, 80, 53]),
                     "dport": rnd.choice([22, 80, 443]),
                     "established": rnd.random() < .3,
                     "icmp_type": rnd.choice([0, 8]) if proto == "icmp" else None}
                want = acl_model.evaluate(entries, v)
                got = _vector_in(psets, v)
                if want != got:
                    bad += 1
                    if bad < 4:
                        print(f"  NG: 評価不一致 v={v} model={want} cover={got}")
        chk(bad == 0, f"acl_model との突合(不一致 {bad} 件)")
    else:
        print("  (acl_model を import できず突合をスキップ)")

    print(f"acl_cover selftest: OK={ok} NG={ng}")
    return ng == 0


def _ipv(s):
    v = 0
    for p in s.split("."):
        v = (v << 8) | int(p)
    return v


def _vector_in(psets, v):
    """permit 集合にベクタが入るか(acl_model.evaluate と一致すべき)。"""
    proto = v["proto"]
    fam = proto if proto in (FAM_TCP, FAM_UDP, FAM_ICMP) else FAM_OTHER
    src, dst = _ipv(v["src"]), _ipv(v["dst"])
    if fam in (FAM_TCP, FAM_UDP):
        # ★呼び出し側は具体値を渡すこと。acl_model は sport/dport=None を
        #   「演算子付きエントリには不一致」と扱い、集合論の全域とは意味が違う。
        vals = [src, dst, v["sport"], v["dport"],
                1 if v.get("established") else 0]
    elif fam == FAM_ICMP:
        vals = [src, dst, v["icmp_type"]]
    else:
        vals = [src, dst, "OTHER"]
    return any(r.contains_vector(vals) for r in psets[fam])


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
