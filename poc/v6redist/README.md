# BL-098 PoC: OSPFv3 ⇄ EIGRPv6 相互再配送のエッジ挙動 (2026-08-08)

- 盤面: `problems/_POC-V6REDIST`(5× iol-xe 17.15)。
  ユーザ手組みラボ **「IPv6redistribute01」の忠実な複製**。**ユーザラボは読み取りのみ・不触**。
- 実行: `scripts/lab.sh provision _POC-V6REDIST` → `.venv/bin/python3 poc/v6redist/sweep.py`
- 生ログ: [results-raw.md](results-raw.md) / 設計: `problems/_drafts/IPV6-REDIST-PAPER.design.md`

```
      OSPFv3 544 area 0                            EIGRP named AS 5400
 C1 ────────── RA ────────────── RT-C ────────────── RB ────────── C2
 2001:DB8:2:1::/64  2001:DB8:1:1::/64  ASBR  2001:DB8:A:A::/64  2001:DB8:1A:A::/64
   (C1 LAN)          (Oトランジット)          (Eトランジット)       (C2 LAN)
```

RT-C は**単独 ASBR**。双方向に `route-map` + `include-connected` 付きの相互再配送。
`af-interface Ethernet0/0 shutdown` で OSPF 側リンクでは EIGRP を喋らない
(named mode の IPv6 AF は `network` 文を使わず全 IPv6 IF が既定参加するため明示 shutdown が要る)。

## 基線 (B0) — ✅ ユーザラボ実測と完全一致

| ノード | C1 LAN | C2 LAN | O トランジット | E トランジット |
|---|---|---|---|---|
| C1 / RA | (connected/O) | **—** | (connected/O) | `OE2 [110/20]` |
| RB / C2 | **—** | (connected) | `EX [170/1536000]` / `EX [170/2048000]` | (connected) |

`ping C1→C2` `ping C2→C1` とも **`% No valid route for destination`**。

★**核心**: 両方向とも「再配送は動いていて経路も1本ずつ渡っている」が、渡っているのは
`include-connected` が拾った **ASBR 自身の足元のリンク**だけ。届けたい客先 LAN は
prefix-list に落ちている。`show ipv6 protocols` には両方向の Redistribution 行が正常に出る
ため、**壊れているように見えない**。

## 確定表(実測)

| # | 操作 | ★実測(確定) |
|---|---|---|
| E16 | `route-map` 節を書かずに `redistribute` を**再発行** | ★**route-map は外れない**(行がマージされる)。経路・到達性とも基線から不変 |
| E1 | `no redistribute` を前置して route-map 無しで再発行 | **両方向とも全開通**。C1←C2LAN `OE2 [110/20]` / RB←C1LAN `EX [170/1536000]` / C2←C1LAN `EX [170/2048000]`・**ping 100%/100%** |
| E2 | prefix-list に客先 LAN を**追記**(トランジットも残す) | 全開通・トランジットも残る・**ping 100%/100%** |
| E3 | prefix-list を客先 LAN のみに**置換** | ★**客先 LAN は通り、トランジットは消える**(C1 の Etran=—・RB の Otran=—)・**ping 100%/100%**。→ **`include-connected` 由来の経路も route-map の適用を受ける** |
| E4 | `include-connected` を外す(prefix-list は基線=トランジットのみ許可) | ★**両ドメインとも受信ゼロ**・ping NOROUTE/NOROUTE。→ 基線で通っていた1本ずつが `include-connected` 由来だったことの決定的証明 |
| E5 | EIGRP 側 `redistribute ospf` から **metric を落とす** | ★**RB/C2 は何も受け取らない**(トランジットすら消える)。named mode でも **metric 無しの再配送は広告されない** |
| E6 | E5 に `topology base` の `default-metric` を追加 | **救われる**(RB/C2 が EX で受信)。→ metric は inline か `default-metric` のどちらかが必須 |
| E7 | 参照 prefix-list を**未定義**にする(route-map は在る) | ★**全許可**。両方向とも全経路が通り **ping 100%/100%**。→「絞るための道具を消したら全開通した」= 危険な偶然の成功 |
| E8 | **未定義の route-map** を参照させる | ★**全拒否**。両ドメインとも受信ゼロ・ping NOROUTE/NOROUTE |
| E9 | EIGRP `af-interface Ethernet0/0` の `shutdown` を解除 | ★O トランジットが **`EX [170]` → `D [90]`** に化ける(RB `D [90/1536000]` / C2 `D [90/2048000]`)。EIGRP がその IF で有効になると connected がネイティブ内部経路として広告され、再配送 EX を AD で上書きする。**単独では C1↔C2 は開通しない**(客先 LAN は依然 PL で落ちる) |
| E10 | RA で static を OSPF へ再配送し(RT-C から見て `OE2`)、EIGRP 側の `match internal` を検証 | ★`match internal` のままでは RB に**届かない**。`match internal external` に変えると **`EX [170/1536000]`** で届く。→ **`match internal` は OSPF 外部を落とす** |
| E11 | OSPFv3 `default-information originate` の `always` 要否 | ★`always` **無しでは配布されない**(RT-C 自身が `::/0` を持たないため C1 は `—`)。`always` 付きで C1/RA が **`::/0 = OE2 [110/1]`**(★metric は **1**。`redistribute` 既定の 20 ではない)。この時 `ping C1→C2` は **`0%`**(NOROUTE ではない)= 往路のみ開通の指紋 |
| E12 | OSPF 側 `default-information originate always` **＋** EIGRP `af-interface Ethernet0/1` の `summary-address ::/0` | ★★**フィルタを一切触らずに C1↔C2 が 100%/100% で開通**。C1/RA `::/0 = OE2 [110/1]` / RB/C2 `::/0 = D [90/…]`。★副作用2点=(1) `summary-address ::/0` が E0/1 出しの more-specific を**全て抑止**し RB/C2 の O トランジットが**消える** (2) RT-C 自身に **`::/0 = D [5/1024000]`**(EIGRP 集約の自動 Null0・**AD 5**)が入る。→ 明細ゼロで到達する `default_only` / フィルタ無改変の `filter_frozen` 両世界の正解 |
| E13 | RA / RB に相手 LAN 向けの**静的のみ**(IGP へ再配送しない) | ★**開通しない**(ping NOROUTE/NOROUTE)。RA `C2LAN = S [1/0]` / RB `C1LAN = S [1/0]` と**中継は知る**が、**C1 / C2 は依然 `—`**。→「静的を置いた=直った」ではない。**広告と到達は別**という半正解の実証 |
| E14 | E13 **＋** C1 / C2 に既定ゲートウェイ(`ipv6 route ::/0`) | **開通(100%/100%)**。フィルタ無改変の静的解。ただし **4 台(RA/RB/C1/C2)を触る**ため `rtc_only` 世界では死ぬ |
| E15 | OSPF 側を `metric 500 metric-type 1` で再配送 | C1 `OE1 [110/520]` / RA `OE1 [110/510]`。★**E1 は内部コストを累積する**(500 → RA 510 → C1 520)。基線の E2 は全ノードで `[110/20]` 固定で**累積しない**。→ `e1_type` 世界と `read` 形の識別材料 |

### ★最重要の非対称 1 — 「外したつもりが外れていない」(E16 vs E1)

```
(基線)  redistribute eigrp 5400 route-map EMAP01 include-connected
(A)     redistribute eigrp 5400 include-connected          を投入
        → redistribute eigrp 5400 route-map EMAP01 include-connected   ← 変化なし
(B)     no redistribute eigrp 5400
        redistribute eigrp 5400 include-connected          を投入
        → redistribute eigrp 5400 include-connected                     ← 外れる
```

`metric` / `match internal` も同様に `no` を前置しない限り残る。
→ **fix(CLI) 形の最有力ディストラクタ**(route-map 節を省いた再発行=見た目は正しいが効かない)。
PoC 手順自体がこの罠を踏み、初回スイープの E1 が「変化なし」となって発覚した。

### ★最重要の非対称 2 — 「器が無い」vs「中身が空振り」(E8 vs E7)

| 状態 | 結果 |
|---|---|
| `route-map` **ごと未定義** | **全拒否**(何も再配送されない) |
| `route-map` は在るが参照 `prefix-list` が**未定義** | **全許可**(全部再配送される) |

**絞る道具を「まるごと消す」と全部止まり、「中身だけ消す」と全部通る。**
BL-095(EIGRP leak-map)で確定した非対称と**完全に同型**。IOS の route-map 参照における
一般則として扱ってよい(2つの独立した文脈で実測一致)。

### ★最重要の非対称 3 — 「片方向だけ直した」指紋(E6 で実証)

E6 は EIGRP 側だけを開通させた状態(OSPF 側は route-map が残存)。このとき:

| ping | 結果 | 意味 |
|---|---|---|
| C1 → C2 | `% No valid route for destination` | **直っていない側**: 経路そのものが無い |
| C2 → C1 | `..`(0%) | **直った側**: 往路はある・復路が無い |

→ **NOROUTE / タイムアウト / `!!` の3値が「どちら方向が未修理か」を一意に指す。**
紙面の trace 形(S4)の中核素材。

### ★症状が消える罠 — `source` 指定

| コマンド | 出力 |
|---|---|
| `ping 2001:DB8:1A:A::2`(経路なし) | `% No valid route for destination` |
| `ping 2001:DB8:1A:A::2 source 2001:DB8:2:1::2`(経路なし) | `..`(単なるタイムアウトに見える) |
| 経路あり・復路なし | `..` |

→ **source を付けた瞬間に「経路欠落」の証拠が消え、復路障害と区別できなくなる。**

### ★最重要の非対称 4 — 「広告」と「到達」は別(E13)

RA / RB に静的を入れると**その 2 台は相手 LAN を知る**が、**C1 / C2 は何も変わらない**
(静的は IGP へ再配送しない限り伝播しない)。ping は NOROUTE のまま。
→ 「静的ルートを設定する」という**言葉としては正しい**解答が、**置き場所を誤ると効かない**。
`filter_frozen` 世界の最有力ディストラクタ(E13 = 半正解 / E14 = 正解)。

### デフォルト経路解のブラックホール懸念(E12 の含意)

`af-interface ... summary-address ::/0` は **RT-C 自身に `::/0 → Null0` (AD 5) を作る**。
この盤面では RT-C が両ドメインの明細を全て持つため実害はないが、**RT-C が上流を持たない構成で
同じ操作をすると、未知宛先が静かに Null0 へ落ちる**。採点・解説で必ず触れる論点。

なお E12 の順序では `summary-address ::/0` が RT-C の RIB に `::/0` を作るため、
その後なら `default-information originate` は `always` 無しでも成立する。
`always` が必須なのは **RT-C が `::/0` を持たない状態**(E11)である点に注意。

## PoC 実施上の注意(手順の罠)

- **`no router ospfv3 <pid>` はインタフェースの `ipv6 ospf <pid> area <n>` も道連れに消す。**
  プロセスを作り直したら IF 側も焼き直すこと(`restore()` で対処済)。
- `redistribute` の delta は必ず `no redistribute <proto> <id>` を前置する(上記 E16)。
  スイープは毎シナリオで `show run | include redistribute` を記録し、
  **意図した delta が本当に効いたか**を経路表と一緒に残す。
- `clear ipv6 ospf process` は `[yes/no]` 確認を出す(`clear_ospf()` で応答)。
