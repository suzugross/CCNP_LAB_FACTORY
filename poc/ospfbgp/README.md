# PoC: OSPF→BGP 再配送の既定範囲と match オプション (BL-163)

実施 2026-09-12・IOL `iol-xe 17.15`・パック `problems/_POC-OSPFBGP`（4 ノード）。
定番題材派生（紙面 shape=ospfbgp の実測台帳）。

## 盤面

```
RT01 (BGP AS65000) ─192.168.1.0/24─ RT02 (iBGP + OSPF 1) ─192.168.2.0/24─ RT03 (OSPF 1 + RIP) ─192.168.3.0/24─ RT04 (RIP)
```
- RT03: Lo1 `192.168.30.0/24`(area 0・p2p) / Lo2 `192.168.31.0/24`(**area 1**・p2p) →
  RT02 から見て **O** と **O IA** の両方が揃う。
- RT03 は RIP を OSPF へ再配送し、route-map で metric-type を振り分け →
  `192.168.40.0/24` = **O E1**、`192.168.41.0/24` = **O E2**。
- RT02 は `redistribute ospf 1` を BGP(AS65000) の AF 配下で出し分け、RT01 で観測。

RT02 の OSPF テーブル（全変種で共通の入力）:
```
O     192.168.30.0/24 [110/11] via 192.168.2.3, Ethernet0/1
O IA  192.168.31.0/24 [110/11] via 192.168.2.3, Ethernet0/1
O E1  192.168.40.0/24 [110/30] via 192.168.2.3, Ethernet0/1
O E2  192.168.41.0/24 [110/20] via 192.168.2.3, Ethernet0/1
```

## 確定表（RT01 の `show ip bgp`）

| RT02 の設定（`show run` の表示形） | RT01 の BGP テーブル |
|---|---|
| `redistribute ospf 1` | `*>i 192.168.2.0` / `*>i 192.168.30.0` / `*>i 192.168.31.0` — **内部(O)＋エリア間(O IA)のみ。E1/E2 は入らない** |
| `redistribute ospf 1 match external 1 external 2` | `* i 192.168.40.0` / `* i 192.168.41.0` — **内部は入らない**。しかも★下記の next-hop 罠で **best にならない** |
| `redistribute ospf 1 match internal external 1` | 内部3本 ＋ `*>i 192.168.40.0`（E2 だけ来ない） |
| `redistribute ospf 1 match external 2` | `* i 192.168.41.0` のみ |

★ **接続セグメント `192.168.2.0/24` も「エリア内ルート」として一緒に入る**
（redistribute の connected 随伴ではなく、OSPF のエリア内経路だから）。

## ★ 実測でしか分からない挙動

1. **既定は `match internal`（表示されない）**。`show run` は素の `redistribute ospf 1`。
2. **`match` は再発行でマージ（置換ではない）**:
   `redistribute ospf 1`（既定）に `... match external 1` を出すと、
   **`redistribute ospf 1 match internal external 1` と表示される**
   （＝暗黙だった internal が明示化され、external が**足される**）。
   さらに `... match internal` を出しても external は消えない。
3. **単独の取り消しはできる**: `no redistribute ospf 1 match external 2` は
   その match だけを外し、行は `redistribute ospf 1` に戻る（行ごと消えはしない）。
4. ★★**next-hop の連鎖**: 外部だけを再配送すると、**next-hop の網（=エリア内の
   `192.168.2.0/24`）も一緒に落ちる**ので、RT01 では
   `192.168.2.3 (inaccessible)` → `Paths: (1 available, no best path)` となり、
   **BGP テーブルには載るがルーティングテーブルには入らない**
   （`show ip route bgp` が空）。「外部だけ入れる」構成は二重に壊れる。
5. OSPF の Loopback は既定で /32 になるので、/24 で見せたい場合は
   `ip ospf network point-to-point` が要る（作問の見た目を教科書図に合わせる時に必要）。
   ★ただし **OSPF の network 文より後に付けると反映されない**ことがあり、
   その場合は同コマンドを再投入すると P2P になる（本 PoC で実発）。

## ★ 遷移表（実測・4 状態 × 8 コマンド = 32 本を全数計測）

| 現状 → 投入コマンド | `redistribute ospf 1` | `... match internal` | `... match external 1` | `... match external 2` | `... match external 1 external 2` | `... match internal external 1 external 2` | `no ... match external 1` | `no ... match external 2` |
|---|---|---|---|---|---|---|---|---|
| `redistribute ospf 1`(=internal) | 変化なし | 変化なし | `int e1` | `int e2` | `int e1 e2` | `int e1 e2` | 変化なし | 変化なし |
| `match external 1 external 2` | **`redistribute ospf 1`** | `int e1 e2` | 変化なし | 変化なし | 変化なし | `int e1 e2` | `match external 2` | `match external 1` |
| `match internal external 1` | **`redistribute ospf 1`** | 変化なし | 変化なし | `int e1 e2` | `int e1 e2` | `int e1 e2` | **`redistribute ospf 1`** | 変化なし |
| `match external 2` | **`redistribute ospf 1`** | `int e2` | `e1 e2` | 変化なし | `e1 e2` | `int e1 e2` | 変化なし | **`redistribute ospf 1`** |

**読み取れる規則（これがモデルの正典）**:
- 状態は集合 S ⊆ {internal, external 1, external 2}（空にはならない）。
- **`match` 付きの再発行 → S ∪ 指定集合（マージ。置換ではない）**。
- ★**`match` 無しの `redistribute ospf P` の再発行 → S を既定 {internal} に「リセット」**
  （マージではない! `match external 1 external 2` の状態でこれを出すと**外部が消える**）。
- `no ... match X` → S − X。空になる場合は {internal} に戻る（表示は素の `redistribute ospf P`）。
- 表示形: S=={internal} のときだけ `redistribute ospf P`。それ以外は
  `match` ＋ `internal` → `external 1` → `external 2` の順で並ぶ（既定だった internal も明示化される）。

## 作問への反映（shape=ospfbgp）

- 既定＝内部のみ、を「結果の表から設定を逆算させる」形が出典系の定番。
  **match 付きコマンドを選ぶと、提示された BGP テーブルと矛盾する**のが消去の鍵。
- 要件世界で正解を反転させられる: 全部届ける / 内部だけ / E1 だけ。
- 罠1 = マージ仕様（「external を足したら internal は消える」と思うと誤る）。
- 罠2 = next-hop 連鎖（「外部だけ」構成は BGP テーブルに載っても経路表に入らない）。
