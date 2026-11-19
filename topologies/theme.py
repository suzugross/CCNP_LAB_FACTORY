#!/usr/bin/env python3
"""全ページのダークモード(BL-280) — 配信サーバが返す HTML に、暗色の CSS と切替のボタンを差し込む。

ポータル(pack_server.py)とワークスペース(lab_console.py)は、HTML を返す直前に inject() を通す。
生成器が書き出したページ(packs/・reading/)はそのままで、古いパックも作り直さずに暗色になる。

切替の状態:
  - Cookie `ccnp_theme`(dark / light)。**Cookie はポートを区別しない**ので、ポータル(8899)と
    ワークスペース(8897)が 1 つの状態を共有する。どのページのボタンを押しても全部が切り替わる。
  - 開いている他のタブと、ワークスペースの枠(別ポートの iframe)は、1 秒ごとに Cookie を読み直して追いつく。
    枠へは postMessage でもすぐ伝える。Cookie が無い時は明るい地(従来どおり。OS の設定には追随しない)。
  - Cookie が使えない所(file:// で開いたページ)は localStorage に持つ(そのページの中だけの切替)。

暗色の CSS(dark_css): ページの <style> から機械的に作る。手で暗色版を書かない。
  色の役割は宣言の種類で決め、OKLab の明度を折り返す(色相は保ち、はみ出す彩度だけ削る):
    文字(color)             … 暗い色だけ明るくする(白抜きの文字・元から薄い文字はそのまま)
    地(background)          … 明るい色だけ暗くする(端末など元から暗い地はそのまま)
    罫線(border・outline)   … 明度を反転する(黒い罫線は明るい線に・薄い罫線は暗い線に)
    カスタムプロパティ       … 名前で役割を決める(--paper= 地・--ink= 文字・--line= 罫線…・_role)。
                               分からない名前はアクセント(暗すぎる色だけ持ち上げる)
  同じ規則に地と文字の両方があれば、折り返した後も読めるかを確かめ、潰れていれば文字の側を反対へ倒す。
  元の規則は消さず、`:root[data-theme="dark"]` を前に付けた規則を後ろに足す(詳細度が上がるので必ず勝つ)。
  色に関わる宣言は var() や none の物も写すので、元の規則どうしの勝ち負けは暗色でも保たれる。
  印刷(@media print)には効かせない。

図(インラインの SVG): 個々の色は変えず、図ごと反転する(filter: invert + hue-rotate = 色相は保つ)。
  SVG の色は属性や JS で付くものが多く、CSS からは追えないため。SVG の中ではカスタムプロパティを
  明るい地の値に戻す(反転の二重掛けを防ぐ)。

ボタン: ページの帯に置く(data-theme-slot を持つ要素 → 問題用紙の .nav → 読み物の .rnav → ゲームの header.bar)。
  帯の無いページは右下に浮かせる。ワークスペースの枠の中のページには置かない(外側の帯にある)。

★新しいページを作る時: 色は <style> の CSS に書く(暗色はそこから作る)。HTML の style 属性や JS で直接付けた
  色は暗色にならない(SVG の中は図ごと反転するので構わない)。

確かめ方:
  python3 topologies/theme.py --selftest
  python3 topologies/theme.py --demo <in.html> <out.html> [--dark]   # 差し込んだ版を書き出す(スクリーンショット用)
"""
import argparse
import functools
import re
import sys

COOKIE = "ccnp_theme"
DARK = ':root[data-theme="dark"]'

# --------------------------------------------------------------------------
# 色の計算(sRGB ⇄ OKLab)
# --------------------------------------------------------------------------
NAMED = {
    "white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "green": (0, 128, 0),
    "blue": (0, 0, 255), "gray": (128, 128, 128), "grey": (128, 128, 128), "silver": (192, 192, 192),
    "yellow": (255, 255, 0), "orange": (255, 165, 0), "navy": (0, 0, 128), "teal": (0, 128, 128),
    "maroon": (128, 0, 0), "purple": (128, 0, 128), "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211), "darkgray": (169, 169, 169), "darkgrey": (169, 169, 169),
    "whitesmoke": (245, 245, 245), "gainsboro": (220, 220, 220),
}
COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|\b(?:rgba?|hsla?)\([^()]*\)|\b(?:"
    + "|".join(NAMED) + r")\b", re.I)


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _cbrt(x):
    return x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3))


def to_oklab(r, g, b):
    """sRGB(0〜1) → OKLab(L, a, b)。"""
    r, g, b = _lin(r), _lin(g), _lin(b)
    l_ = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def _from_oklab(L, a, b):
    """OKLab → 線形 sRGB(範囲外もそのまま返す)。"""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def _inside(rgb):
    return all(-1e-4 <= c <= 1 + 1e-4 for c in rgb)


def from_oklab(L, a, b):
    """OKLab → sRGB(0〜1)。sRGB に収まらなければ明度と色相を保って彩度だけ削る。"""
    if not _inside(_from_oklab(L, a, b)):
        lo, hi = 0.0, 1.0
        for _ in range(22):
            mid = (lo + hi) / 2
            if _inside(_from_oklab(L, a * mid, b * mid)):
                lo = mid
            else:
                hi = mid
        a, b = a * lo, b * lo
    return tuple(min(1.0, max(0.0, _gam(min(1.0, max(0.0, c))))) for c in _from_oklab(L, a, b))


def parse_color(tok):
    """色の字句 → (r, g, b, alpha)(0〜1)。読めなければ None。"""
    t = tok.strip().lower()
    if t in NAMED:
        return tuple(c / 255 for c in NAMED[t]) + (1.0,)
    if t.startswith("#"):
        h = t[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        v = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return tuple(v[:3]) + ((v[3],) if len(v) == 4 else (1.0,))
    m = re.match(r"(rgba?|hsla?)\((.*)\)$", t)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) < 3:
        return None

    def num(p, scale):
        return float(p[:-1]) / 100 * scale if p.endswith("%") else float(p)
    try:
        alpha = num(parts[3], 1) if len(parts) > 3 else 1.0
        if m.group(1).startswith("rgb"):
            r, g, b = (num(p, 255) / 255 for p in parts[:3])
        else:
            hh = float(re.sub(r"deg$", "", parts[0])) % 360 / 360
            s, li = num(parts[1], 1), num(parts[2], 1)
            q = li * (1 + s) if li < 0.5 else li + s - li * s
            p_ = 2 * li - q

            def hue(t_):
                t_ %= 1
                return (p_ + (q - p_) * 6 * t_ if t_ < 1 / 6 else q if t_ < 1 / 2
                        else p_ + (q - p_) * (2 / 3 - t_) * 6 if t_ < 2 / 3 else p_)
            r, g, b = hue(hh + 1 / 3), hue(hh), hue(hh - 1 / 3)
    except ValueError:
        return None
    return (min(1, max(0, r)), min(1, max(0, g)), min(1, max(0, b)), min(1, max(0, alpha)))


def fmt_color(rgba):
    r, g, b, a = rgba
    if a >= 0.999:
        return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))
    return "rgba(%d,%d,%d,%s)" % (round(r * 255), round(g * 255), round(b * 255), ("%.3f" % a).rstrip("0").rstrip("."))


def lightness(rgba):
    return to_oklab(*rgba[:3])[0]


# --------------------------------------------------------------------------
# 明度の折り返し(役割ごと)
#   T は「折り返しの軸」。文字の側も地の側も T で連続につながる(T の近くの中間色はほぼそのまま)。
#   平方根の曲線で、真っ白/真っ黒に近い所ほど大きく動かし、中間色は控えめに動かす。
# --------------------------------------------------------------------------
T = 0.525
BG_MIN = 0.22          # 真っ白の地 → この明度(#1c1c1c ほど)。紙の色 #eceef1 は 0.24 ほど(#1f2022)
FG_MAX = 0.92          # 真っ黒の文字 → この明度(#e4e4e4 ほど)
BD_BLACK, BD_WHITE = 0.80, 0.32   # 黒の罫線 → / 白の罫線 → この明度
AC_MIN = 0.64          # アクセントの色の明度の下限(暗い地の上で読める明るさ)


def _L_bg(L):
    return L if L <= T else T - (T - BG_MIN) * ((L - T) / (1 - T)) ** 0.5


def _L_fg(L):
    return L if L >= T else T + (FG_MAX - T) * ((T - L) / T) ** 0.4


def _L_bd(L):
    return BD_BLACK - (BD_BLACK - BD_WHITE) * L


def _L_ac(L):
    return AC_MIN if L < AC_MIN else (_L_bg(L) if L > 0.9 else L)


L_MAP = {"fg": _L_fg, "bg": _L_bg, "bd": _L_bd, "ac": _L_ac}
# 文字とアクセントは、暗くした紙の色に対してこの対比(WCAG)を下限にする。明度だけでは、鮮やかな赤
#   (#c62828 など。OKLab の明度は中ほどでも輝度が低い)が暗い地に沈むため
REF_BG = (0.114, 0.122, 0.129)        # 紙の色 #eceef1 を地の側で折り返した色(#1d1f21)
MIN_CONTRAST = {"fg": 4.5, "ac": 3.0}


def _lum(rgb):
    r, g, b = (_lin(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(c1, c2):
    a, b = sorted((_lum(c1), _lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def map_rgba(rgba, role):
    """1 色を役割に合わせて暗色の地向けに変える。shadow は半透明ならそのまま(影は暗いままでよい)。"""
    if role == "shadow":
        if rgba[3] < 0.999:
            return rgba
        role = "bd"
    L, a, b = to_oklab(*rgba[:3])
    if role == "bg" and (a * a + b * b) ** 0.5 >= 0.12:
        return rgba                      # 鮮やかな地(端末の窓の丸・色の見本など)は面でなく印なので、そのまま
    L2 = L_MAP[role](L)
    rgb = rgba[:3] if abs(L2 - L) < 1e-6 else from_oklab(L2, a, b)
    need = MIN_CONTRAST.get(role)
    if need and rgba[3] >= 0.999 and _contrast(rgb, REF_BG) < need:
        lo, hi = L2, 1.0                 # 色相を保ったまま、足りる所まで明るくする
        for _ in range(20):
            mid = (lo + hi) / 2
            if _contrast(from_oklab(mid, a, b), REF_BG) >= need:
                hi = mid
            else:
                lo = mid
        rgb = from_oklab(hi, a, b)
    if rgb == rgba[:3]:
        return rgba
    return tuple(rgb) + (rgba[3],)


def map_colors(value, role):
    """宣言の値の中の色の字句を全部変える(文字列と url() の中は触らない)。"""
    keep = []

    def hide(m):
        keep.append(m.group(0))
        return "\0%d\0" % (len(keep) - 1)
    masked = re.sub(r'url\([^)]*\)|"[^"]*"|\'[^\']*\'', hide, value)

    def sub(m):
        c = parse_color(m.group(0))
        return fmt_color(map_rgba(c, role)) if c else m.group(0)
    out = COLOR_RE.sub(sub, masked)
    return re.sub(r"\0(\d+)\0", lambda m: keep[int(m.group(1))], out)


def has_color(value):
    return bool(COLOR_RE.search(re.sub(r'url\([^)]*\)|"[^"]*"|\'[^\']*\'', "", value)))


# カスタムプロパティの名前 → 役割
_ROLE_BG = re.compile(r"paper|panel|card|surface|canvas|bg|term|hit|win", re.I)
_ROLE_FG = re.compile(r"ink|text|fg|sub|mute|link|fore", re.I)
_ROLE_BD = re.compile(r"line|border|rule|grid|sep", re.I)


def _role(name):
    n = name[2:]
    if _ROLE_BD.search(n):
        return "bd"
    if _ROLE_FG.search(n):
        return "fg"
    if _ROLE_BG.search(n):
        return "bg"
    return "ac"


# --------------------------------------------------------------------------
# CSS の読み取り(このリポの手書きの CSS が読めれば十分な、小さな字句解析)
# --------------------------------------------------------------------------
def _skip_str(s, i):
    q, i = s[i], i + 1
    while i < len(s) and s[i] != q:
        i += 2 if s[i] == "\\" else 1
    return i + 1


def blocks(css):
    """最上位の [(前置き, 中身)]。@import などの文は捨てる。"""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, start, n = [], 0, 0, len(css)
    while i < n:
        c = css[i]
        if c in "\"'":
            i = _skip_str(css, i)
            continue
        if c == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if css[j] in "\"'":
                    j = _skip_str(css, j)
                    continue
                depth += {"{": 1, "}": -1}.get(css[j], 0)
                j += 1
            out.append((css[start:i].strip(), css[i + 1:j - 1]))
            i = start = j
            continue
        if c in ";}":
            start = i + 1
        i += 1
    return out


def _split(s, sep):
    """括弧・角括弧・引用符の外にある sep で区切る。"""
    out, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        if c in "\"'":
            j = _skip_str(s, i)
            cur.append(s[i:j])
            i = j
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


def decls(body):
    """[(プロパティ, 値, !important)]。カスタムプロパティの名前は大小文字を保つ。"""
    out = []
    for part in _split(body, ";"):
        prop, sep, val = part.partition(":")
        prop, val = prop.strip(), val.strip()
        if not sep or not prop or "{" in prop:
            continue
        imp = bool(re.search(r"!\s*important\s*$", val, re.I))
        if imp:
            val = re.sub(r"\s*!\s*important\s*$", "", val, flags=re.I)
        out.append((prop if prop.startswith("--") else prop.lower(), val, imp))
    return out


def prefix(sel):
    """セレクタの前に暗色の条件を付ける。html / :root で始まるものは、その要素自身に条件を付ける。"""
    s = sel.strip()
    m = re.match(r"(html|:root)(?![\w-])(.*)$", s, re.S)
    if m:
        return m.group(1) + '[data-theme="dark"]' + m.group(2)
    return DARK + " " + s


# --------------------------------------------------------------------------
# 暗色の規則を作る
# --------------------------------------------------------------------------
_SKIP = {"fill", "stroke", "stop-color", "flood-color", "lighting-color"}    # SVG は図ごと反転する
_FG = {"color", "caret-color", "accent-color", "-webkit-text-fill-color", "text-decoration-color"}
_BD = re.compile(r"^(?:border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?|outline|column-rule)"
                 r"(-color)?$")
_SHADOW = {"box-shadow", "text-shadow"}
_KW = re.compile(r"^(?:transparent|currentcolor|inherit|initial|unset|revert)$", re.I)
_IMG = re.compile(r"\b(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)


def _color_token(value):
    """ショートハンドの値から色の字句を 1 つ抜く(var() も色とみなす)。無ければ None。"""
    for t in _split(value.replace("/", " "), " "):
        t = t.strip()
        if not t or _IMG.match(t) or t.lower().startswith("url("):
            continue
        if COLOR_RE.fullmatch(t) or _KW.match(t) or t.startswith("var("):
            return t
    return None


class Ctx:
    def __init__(self):
        self.root = {}           # :root のカスタムプロパティ名 → (元の値, 暗色の値)

    def resolve(self, value, dark, role):
        """単独の色・var(--x) を (r,g,b,a) に(dark なら暗色にした値)。読めなければ None。"""
        v = (value or "").strip()
        m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.*))?\)", v, re.S)
        if m and m.group(1) in self.root:
            c = parse_color(self.root[m.group(1)][1 if dark else 0].strip())
            return c                                       # 暗色の値は名前の役割で作ってある
        if m:
            v = m.group(2) or ""
        c = parse_color(v) if COLOR_RE.fullmatch(v.strip()) else None
        return map_rgba(c, role) if c and dark else c


def _rule(sels, body, ctx):
    out, fg, bg = [], None, None
    for prop, val, imp in decls(body):
        bang = " !important" if imp else ""
        if prop.startswith("--"):
            if has_color(val):
                out.append(f"{prop}:{map_colors(val, _role(prop))}{bang}")
            continue
        if prop in _SKIP:
            continue
        if prop == "color-scheme":
            if val.strip().lower() == "light":
                out.append(f"color-scheme:dark{bang}")
            continue
        if prop in _FG:
            out.append(f"{prop}:{map_colors(val, 'fg')}{bang}")
            if prop == "color":
                fg = (val, len(out) - 1, bang)
        elif prop in ("background", "background-color"):
            layers = _split(val, ",")
            col = _color_token(layers[-1]) if prop == "background" else val
            out.append(f"background-color:{map_colors(col, 'bg') if col else 'transparent'}{bang}")
            bg = col
            if prop == "background" and _IMG.search(val):
                out.append(f"background-image:{map_colors(val, 'bg')}{bang}")
        elif prop == "background-image" and has_color(val):
            out.append(f"background-image:{map_colors(val, 'bg')}{bang}")
        elif prop in _SHADOW:
            out.append(f"{prop}:{map_colors(val, 'shadow')}{bang}")
        elif prop == "scrollbar-color":
            out.append(f"{prop}:{map_colors(val, 'bg')}{bang}")
        else:
            m = _BD.match(prop)
            if not m:
                continue
            if m.group(1):
                out.append(f"{prop}:{map_colors(val, 'bd')}{bang}")
            else:
                col = _color_token(val)
                out.append(f"{prop}-color:{map_colors(col, 'bd') if col else 'currentcolor'}{bang}")
    # 同じ規則に地と文字があれば、折り返した後も読めるかを確かめる(例: 濃い地の白抜き文字で、地の色が
    #   カスタムプロパティ経由で明るく反転した時)。潰れていれば文字の側を反対へ倒す
    if fg and bg:
        f0, b0 = ctx.resolve(fg[0], False, "fg"), ctx.resolve(bg, False, "bg")
        f1, b1 = ctx.resolve(fg[0], True, "fg"), ctx.resolve(bg, True, "bg")
        if f0 and b0 and f1 and b1 and b0[3] > 0.6:
            d0 = abs(lightness(f0) - lightness(b0))
            d1 = abs(lightness(f1) - lightness(b1))
            if d1 < min(0.35, 0.7 * d0):
                alt = map_rgba(f0, "bg" if lightness(b1) > 0.5 else "fg")
                if abs(lightness(alt) - lightness(b1)) > d1:
                    out[fg[1]] = f"color:{fmt_color(alt)}{fg[2]}"
    if not out:
        return ""
    return ",".join(prefix(s) for s in sels) + "{" + ";".join(out) + "}"


def _walk(items, ctx):
    out = []
    for pre, body in items:
        if pre.startswith("@"):
            name = pre.split(None, 1)[0].lower()
            if name not in ("@media", "@supports", "@container", "@layer"):
                continue                                       # @keyframes・@font-face・@page は扱わない
            if name == "@media" and re.search(r"\bprint\b", pre, re.I) and not re.search(r"\b(?:screen|all)\b", pre, re.I):
                continue
            inner = _walk(blocks(body), ctx)
            if inner:
                out.append(pre + "{" + inner + "}")
            continue
        r = _rule(_split(pre, ","), body, ctx)
        if r:
            out.append(r)
    return "\n".join(out)


@functools.lru_cache(maxsize=64)
def dark_css(css):
    """ページの CSS(全部の <style> をつないだもの)→ 暗色の規則(@media screen で包む)。"""
    items = blocks(css)
    ctx = Ctx()
    keep = []                    # SVG の中で明るい地の値に戻すカスタムプロパティ
    for pre, body in items:
        if pre.startswith("@"):
            continue
        if any(re.fullmatch(r"\s*(?:html|:root)\s*", s) for s in _split(pre, ",")):
            for prop, val, _imp in decls(body):
                if prop.startswith("--") and has_color(val):
                    ctx.root[prop] = (val, map_colors(val, _role(prop)))
                    keep.append(f"{prop}:{val}")
    svg = f"{DARK} svg{{color:#15171a" + "".join(";" + k for k in keep) + "}"
    return ("@media screen{\n" + STATIC_DARK + svg + "\n" + _walk(items, ctx) + "\n}")


# 生成した規則の前に置く固定の分
STATIC_DARK = f"""{DARK}{{color-scheme:dark}}
{DARK} svg:not(svg svg){{filter:invert(.88) hue-rotate(180deg)}}
{DARK} main img{{filter:brightness(.88)}}
"""

# 切替のボタン(帯に置く時は帯の文字色に合わせる・帯が無い時は右下に浮かせる)
BUTTON_CSS = """
.ccnp-theme{font:inherit;font-size:.85em;line-height:1.35;cursor:pointer;white-space:nowrap;color:inherit;
  background:transparent;border:1px solid currentColor;border-radius:4px;padding:.08rem .55rem;opacity:.8}
.ccnp-theme:hover{opacity:1}
.ccnp-theme.float{position:fixed;right:12px;bottom:12px;z-index:9999;font-size:13px;opacity:1;
  background:#f4f5f7;color:#111;border-color:#999}
:root[data-theme="dark"] .ccnp-theme.float{background:#2a2c30;color:#e4e4e4;border-color:#666}
@media print{.ccnp-theme{display:none}}
"""

# 切替のスクリプト(<head> の終わりで読む= 本文を描く前に地の色が決まる。チラつかない)
THEME_JS = r"""
(function(){
  if(window.ccnpTheme) return;
  var K = '@@COOKIE@@', root = document.documentElement, framed = true, btns = [];
  try{ framed = window.top !== window.self; }catch(e){}
  function saved(){
    var m = document.cookie.match(/(?:^|;\s*)@@COOKIE@@=(dark|light)\b/);
    if(m) return m[1];
    try{ var v = localStorage.getItem(K); if(v === 'dark' || v === 'light') return v; }catch(e){}
    return 'light';
  }
  function cur(){ return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }
  function label(){
    var d = cur() === 'dark';
    btns.forEach(function(b){ b.textContent = d ? '☀ Light' : '☾ Dark'; b.setAttribute('aria-pressed', d ? 'true' : 'false'); });
  }
  function apply(t){
    t = t === 'dark' ? 'dark' : 'light';
    if(root.getAttribute('data-theme') === t) return;
    root.setAttribute('data-theme', t);
    label();
    // 枠(iframe)の中のページへすぐ伝える。別ポートの枠も Cookie の読み直しで追いつくが、待たせない
    for(var i = 0; i < window.frames.length; i++){ try{ window.frames[i].postMessage({ccnpTheme: t}, '*'); }catch(e){} }
    try{ window.dispatchEvent(new CustomEvent('ccnp-theme', {detail: t})); }catch(e){}
  }
  function set(t){
    // Cookie はポートを区別しない= ポータルとワークスペースで共有される。期限 5 年
    document.cookie = K + '=' + t + '; path=/; max-age=157680000; SameSite=Lax';
    try{ localStorage.setItem(K, t); }catch(e){}
    apply(t);
  }
  function toggle(){ set(cur() === 'dark' ? 'light' : 'dark'); }
  function mount(){
    if(framed) return;                 // 枠の中には置かない(外側のワークスペースの帯にある)
    var slot = document.querySelector('[data-theme-slot]') ||
               document.querySelector('body > .nav, .rnav, header.bar');
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'ccnp-theme' + (slot ? '' : ' float');
    b.title = 'Switch every page (portal, packs, reading, games, lab workspace) between light and dark';
    b.addEventListener('click', toggle);
    (slot || document.body).appendChild(b);
    btns.push(b);
    label();
  }
  apply(saved());
  window.ccnpTheme = {get: cur, set: set, toggle: toggle};
  window.addEventListener('message', function(e){
    var t = e.data && e.data.ccnpTheme;
    if((t === 'dark' || t === 'light') && e.source === window.parent) apply(t);
  });
  // 他のタブ・別ポートのページで切り替えた分に追いつく(Cookie を読むだけなので軽い)
  setInterval(function(){ if(!document.hidden) apply(saved()); }, 1000);
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) apply(saved()); });
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
""".replace("@@COOKIE@@", COOKIE)

STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
MARK = 'id="ccnp-theme"'


def inject(text):
    """HTML に暗色の CSS と切替のスクリプトを差し込む(</head> の直前)。二重には入れない。"""
    if MARK in text:
        return text
    css = "\n".join(m.group(1) for m in STYLE_RE.finditer(text))
    try:
        dark = dark_css(css)
    except Exception as e:                 # 暗色が作れなくてもページは出す(明るい地のまま)
        dark = f"/* dark css failed: {type(e).__name__} */"
    block = f"<style {MARK}>{BUTTON_CSS}{dark}</style><script>{THEME_JS}</script>"
    i = text.lower().find("</head>")
    if i < 0:
        m = re.search(r"<body\b[^>]*>", text, re.I)
        i = m.end() if m else 0
    return text[:i] + block + text[i:]


# --------------------------------------------------------------------------
# 自己診断
# --------------------------------------------------------------------------
def selftest():
    import glob
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    ng = 0

    def check(cond, msg):
        nonlocal ng
        if not cond:
            ng += 1
            print("NG:", msg)

    # 1) 色の往復と折り返し
    for hx in ("#000000", "#ffffff", "#eceef1", "#0645ad", "#2e7d32", "#fff3bf", "#12151b"):
        c = parse_color(hx)
        back = from_oklab(*to_oklab(*c[:3]))
        check(fmt_color(back + (1.0,)) == hx, f"往復 {hx} → {fmt_color(back + (1.0,))}")
    paper, ink = parse_color("#eceef1"), parse_color("#000000")
    dp, di = map_rgba(paper, "bg"), map_rgba(ink, "fg")
    check(lightness(dp) < 0.3, f"紙の地が暗くならない {fmt_color(dp)}")
    check(_contrast(dp, di) > 10, f"本文の対比が足りない {_contrast(dp, di):.1f}")
    for hx in ("#0645ad", "#555555", "#1b5e20", "#b71c1c", "#c62828", "#2e7d32", "#5b6676"):
        c = map_rgba(parse_color(hx), "fg")
        check(_contrast(c, dp) >= 4.5, f"文字 {hx} → {fmt_color(c)} の対比 {_contrast(c, dp):.1f} < 4.5")
    term = parse_color("#12151b")
    check(map_rgba(term, "bg") == term, "元から暗い地が動いた")
    check(map_rgba(parse_color("#ffffff"), "fg")[0] == 1.0, "白抜きの文字が動いた")
    check(abs(_L_bg(T + 1e-9) - T) < 1e-3 and abs(_L_fg(T - 1e-9) - T) < 1e-3, "T で不連続")

    # 2) セレクタと宣言
    check(prefix("html") == 'html[data-theme="dark"]', prefix("html"))
    check(prefix("html.framed") == 'html[data-theme="dark"].framed', prefix("html.framed"))
    check(prefix(":root") == ':root[data-theme="dark"]', prefix(":root"))
    check(prefix("body.reading h1") == DARK + " body.reading h1", prefix("body.reading h1"))
    check(prefix("htmlx") == DARK + " htmlx", prefix("htmlx"))
    out = dark_css(".a{border:1px solid #000;color:#000;background:#fff url(x.png)}"
                   ".b{border:0;background:none}.c{fill:#000;stroke:#fff}"
                   "@media print{.d{color:#000}}@media (max-width:640px){.e{color:#111}}"
                   ".f{background:#c8e6c9 !important}.g{border-left:3px solid var(--x)}")
    check('.a{border-color:#' in out and "background-color:#" in out and "url(" not in out, "ショートハンド: " + out)
    check(".b{border-color:currentcolor;background-color:transparent}" in out, "色なしの宣言を写していない")
    check(".c{" not in out, "fill/stroke を写した")
    check(".d{" not in out, "印刷用を写した")
    check("@media (max-width:640px){" in out, "@media を保っていない")
    check(re.search(r"\.f\{background-color:#[0-9a-f]{6} !important\}", out), "!important を保っていない")
    check(".g{border-left-color:var(--x)}" in out, "var() の罫線を写していない")
    # 濃い地(カスタムプロパティ)の白抜き文字: 地が明るく反転したら文字を暗くする
    out = dark_css(":root{--ink:#15171a}.v{background:var(--ink);color:#fff}")
    m = re.search(r"\.v\{background-color:var\(--ink\);color:(#[0-9a-f]{6})\}", out)
    check(m and lightness(parse_color(m.group(1))) < 0.4, "反転した地の上の文字が潰れたまま: " + out)
    check(":root[data-theme=\"dark\"] svg{color:#15171a;--ink:#15171a}" in out, "SVG の中の値を戻していない")
    out = dark_css(":root{--ink:#1c2430}.h{color:var(--ink);background:#d5d9df}")
    check(".h{color:var(--ink);background-color:#" in out, "直書きの地と var() の文字の組を誤って倒した: " + out)

    # 3) 実際の CSS が全部読めて、規則が壊れていない(波括弧の対応)
    import render_html as RH
    import gen_reading as GR
    import pack_home as PH
    import glossary as GL
    srcs = {"render_html": RH.CSS, "reading": GR.READING_CSS + GR.INDEX_CSS + GR.BUNDLE_CSS,
            "pack_home": PH.CSS.replace("@@PAPER@@", RH.PAPER), "glossary": GL.GLOSS_CSS + GL.GLOSS_PAGE_CSS}
    try:
        import gen_pack as GP
        srcs["report"] = GP.REPORT_CSS
    except Exception as e:                    # noqa: BLE001
        print("skip gen_pack:", e)
    import lab_console as LC
    srcs["lab_console"] = STYLE_RE.search(LC.PAGE).group(1).replace("@@PAPER@@", RH.PAPER).replace("@@PANEL@@", RH.PANEL)
    for g in sorted(glob.glob(os.path.join(os.path.dirname(here), "games", "*", "index.html"))):
        with open(g, encoding="utf-8") as fh:
            srcs[os.path.basename(os.path.dirname(g))] = "\n".join(STYLE_RE.findall(fh.read()))
    for name, css in srcs.items():
        d = dark_css(css)
        bal = d.count("{") == d.count("}")
        n_rules = d.count("{") - 2
        n_src = len(COLOR_RE.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)))
        check(bal, f"{name}: 波括弧が合わない")
        check(n_rules > 3, f"{name}: 暗色の規則が少なすぎる({n_rules})")
        print(f"[selftest] {name:12s} 色の字句 {n_src:4d} → 暗色の規則 {n_rules:4d}")
    page = inject("<html><head><style>body{color:#000}</style></head><body></body></html>")
    check(page.count(MARK) == 1 and inject(page) == page, "二重に差し込んだ")
    print("[selftest]", "OK" if not ng else f"NG {ng} 件")
    return 1 if ng else 0


def main():
    ap = argparse.ArgumentParser(description="全ページのダークモード(差し込み)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--demo", nargs=2, metavar=("IN", "OUT"), help="差し込んだ版を書き出す(確認用)")
    ap.add_argument("--dark", action="store_true", help="--demo で最初から暗色にする")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.demo:
        with open(a.demo[0], encoding="utf-8") as fh:
            text = inject(fh.read())
        if a.dark:
            text = re.sub(r"<html\b", '<html data-theme="dark"', text, count=1, flags=re.I)
            text = text.replace("return 'light';", "return 'dark';", 1)     # Cookie の無い file:// でも暗色のまま
        with open(a.demo[1], "w", encoding="utf-8") as fh:
            fh.write(text)
        print(a.demo[1])
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
