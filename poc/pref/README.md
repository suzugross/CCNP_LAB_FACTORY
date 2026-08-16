# 経路選好 PoC 実測 (BL-127 P0 + E2E・2026-08-16)

盤面= CML `_POC-PREF`(IOL iol-xe ×11・console 直駆動・mgmt/SSH 不使用。
当初 10 台。E2E で 4 経路盤面を再現するため RE6 を追加した)。
探針= `probe.py`(o1〜o7 / e1〜e4)、生ログ= `results-raw.md`。
紙面への写像= `topologies/ospfpref_model.py` / `topologies/eigrpfs_model.py`。
設計= `problems/_drafts/PREF-PAPER.design.md`。

トポロジ:

- **OSPF ブロック**(観測点= RO1・すべて area 0 側から見る)
  `RO2(ASBR/intra源) --[cost10]-- RO1 --[cost10]-- RO3(ABR) --area2-- RO4`
  `RO1 --[cost100]-- RO5(ASBR)`
  10.98.8.0/24= RO2 の Lo98(area0・cost500)と RO4 の Lo98(area2・cost1)の両方
  / 10.97.7.0/24= RO2 が **E1 metric100** ・ RO5 が **E2 metric10**
  / 10.96.6.0/24= 両者 **E2 metric20**(内部コストだけ 10 vs 100)
- **EIGRP ブロック**(観測点= RE1・AS100・宛先= RE5 の Lo99 10.99.9.0/24)
  RE2 経由 RD 409600 / FD 435200 (successor) ・ RE3 経由 RD 409600 / FD 486400 (FS)
  ・ RE4 経由 RD 486400 / FD 512000 (FC 不成立)
  metric = 256×(10^7/10000 + Σdelay[10us]) ・ Lo99 の delay 5000us は全経路共通

## 確定した挙動

### OSPF (1.10.d)

1. **型優先はメトリックに先行する(O2)**: 10.98.8.0/24 は
   **エリア内(コスト 510)がエリア間(コスト 21)に勝つ**。
   `Known via "ospf 1", distance 110, metric 510, type intra area`。
   → 「コストが小さい O IA」は正解にならない= ひっかけの核。
2. **E1 > E2 も型が先(O3)**: 10.97.7.0/24 は E1(累積 110)が E2(10)に勝つ。
   `type extern 1`。**表の数値だけ見ると E2 が小さい**。
3. **E1 は累積・E2 は固定(O5)**: 観測点→ASBR の内部コストを 10→60 に変えると
   **E1 は metric 110→160**、**E2 は metric 20 のまま forward metric だけ 10→60**。
4. **E2 同値は forward metric で決着(O4)**: 10.96.6.0/24 は両方 metric 20 で、
   `forward metric 10` の RO2 経由が勝つ(RO5 経由は 100)。
5. ★**書式**: `show ip route <pfx>` の detail 1行目は型で語尾が変わる。
   - intra: `... metric 510, type intra area`
   - inter: `... metric 21, type inter area`
   - E1: `... metric 110, type extern 1` — **forward metric 句は出ない**
   - E2: `... metric 20, type extern 2, forward metric 10` — **E2 だけ句が付く**
6. **LSA 断片(O6)**: `show ip ospf database external <pfx>` は
   `Metric Type: 1 (Comparable directly to link state metric)` /
   `Metric Type: 2 (Larger than any link state path)` と **括弧の注釈まで型で変わる**。
   `Metric:` `Forward Address: 0.0.0.0` `External Route Tag: 0` はタブ字下げ。
   Type-3 は `show ip ospf database summary <pfx>` の `MTID: 0 \tMetric: 11`(1行)。
7. **ASBR/ABR までの内部コストの証拠(O6)**: `show ip ospf border-routers` が
   `i 2.2.2.2 [10] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF 21` の形で
   **観測点から各 ASBR/ABR までのコストを1行で出す**。
   → 紙面で「E1 の累積」「E2 の forward metric」を計算させるための最良の証拠ブロック。

### EIGRP (1.9.c)

8. ★★**FC は厳密不等号(E2)**: RE4 の RD を **FD(successor) と同値の 435200** に
   合わせると、その経路は **variance 4 でも RIB に載らない**。
   同時に、**FD がより大きい** FS 経路(486400)のほうは載る。
   → `RD < FD(successor)` の **等号は不成立**。モデルは修正不要だった。
   (このとき載る2本は 435200 と 486400 で、載らない経路の FD は 460800=
   「FD の大小では説明できない」= 紙面の最良の題材)
9. **variance が乗せるのは FS だけ(E3)**: `variance 2` で successor(435200)と
   FS(486400)の2本。**非 FC(RD 486400)は倍率 2 でも 8 でも乗らない**。
10. **倍率の境界(E4)**: FS でも FD が範囲外なら乗らない。
    FD 921600・FD_succ 435200 のとき **variance 2 では乗らず(870400 < 921600)**、
    **variance 3 で乗る**(1305600 ≥ 921600)。
11. ★★**スプリット・ホライズンで「非 FC の経路が表から消える」(E1/E4 の失敗録)**:
    RD 486400 の RE4 経路は、収束後(uptime 7分・Q Cnt 0)も
    `show ip eigrp topology all-links` に **現れない**。
    原因は収束待ちではなく、**RE4 自身の最良経路が観測点 RE1 経由に反転**し
    (RE4 直行 486400 > RE1 経由 435200+25600=460800)、RE4 が観測点へ
    広告し返さなくなるため。
    → **非 FC の経路を表に見せる盤面は RD が
    `[FD_succ, FD_succ + 逆向きコスト)` の窓に入っている必要がある**。
    `eigrpfs_model.check_board()` がこの窓を機械検証する(外れた draw は捨てる)。
12. **書式**:
    - `show ip eigrp topology` は **successor と FS だけ**を出す。
      非 FC は `all-links` にしか出ない(= 読解素材の作り分けができる)。
    - 行頭は `P <pfx>, N successors, FD is <FD>` + `, U` `, serno N` `, refcount N`
      `, anchored`(all-links のみ serno 以降が付く)。
    - via 行= `        via 10.20.12.2 (435200/409600), Ethernet0/0` = **(FD/RD)**。
    - **variance を入れると `N successors` の N が「RIB に載った本数」に変わる**
      (1 successors → 2 successors)。
    - `show ip route <pfx>` は unequal-cost 時に
      `  * ` 付き(successor)と 4 字下げ(非 successor)のブロックが並び、
      `traffic share count` が **43/48・113/240 のような非自明な比**になる
      (紙面で再現するなら実測比を写すか、比を問わない形にする)。

## E2E 実機照合 (P2 後・2026-08-16・**24/24 PASS**)

探針= `e2e.py`(生ログ= `e2e-raw.md`、初回の失敗録= `e2e-raw-run1.md`)。
**紙面の盤面をそのままラボへ投入し、レンダラ出力と実機 show を行単位で照合**した
(volatile 欄= LS age/Seq/Checksum/uptime/serno/refcount/SPF 番号/U フラグのみマスク。
数値と語句は素で一致することを要求)。E2E のために EIGRP ブロックへ **RE6 を追加**
(4 経路盤面= `fs_allthat` を再現するため)。

| ケース | 照合項目 | 結果 |
|---|---|---|
| `e_fc_strict` | all-links / topology(既定) / variance 適用後の RIB | 3/3 |
| `e_variance_bound` | 同上 | 3/3 |
| `e_variance_nonfc` | 同上 | 3/3 |
| `e_fs_allthat`(4経路) | 同上 | 3/3 |
| `o_type_e1e2` | detail 1行目 / 勝者 next-hop / 外部LSA / border-routers | 4/4 |
| `o_e2_fwd` | 同上 | 4/4 |
| `o_e1_accum` | 同上 | 4/4 |

確認できたこと:

- **メトリックの算術が実機と完全一致**。E1 の累積(`metric 60` = 外部+内部)も、
  E2 の `type extern 2, forward metric 30` の第2段も、EIGRP の FD/RD も
  レンダラの値と 1 の位まで一致した。
- **`show ip eigrp topology`(既定)は successor と FS しか出さない**ことを
  4 盤面で確認(非 FC は all-links にしか現れない)= 読解素材の作り分けが成立。
- **variance 適用後に RIB へ載る経路の集合**がモデルと一致(非 FC は倍率を
  上げても載らない/FS でも範囲外は載らない を実機で再確認)。
- via 行の並びは **収束後は FD 昇順**(初回実行で見えた並び違いは収束途中の過渡)。

### 13. ★FD は「前回 Active 以降の最小値」で、delay を上げても下がったまま残る

初回実行の失敗録(`e2e-raw-run1.md`)。delay を**上げて**メトリックを増やした直後は、
`P <pfx>, 1 successors, FD is 435200` に対し via 行の successor が `(448000/409600)`
という**表の中で矛盾して見える**状態になる。これは DUAL の仕様どおりで、
FD は「最後に Active になってから既知の最小距離」であり、経路が Passive のまま
距離が増えても FD は引き上げられない。

→ 紙面の盤面は「素で収束した網」の写しなので **FD == successor の距離**でよい。
ただし **E2E で盤面を作り直すときは `clear ip eigrp <AS> neighbors` で
再計算させること**(さもないと前ケースの FD が居座り、照合が偽 NG になる)。
併せて、収束は**経路の本数ではなく出力が 2 回連続で同じになること**で待つ
(本数だけ見ると前ケースの RD が残った表を採る)。

### 運用上の注意(E2E 特有)

- `iol-xe 17.15` は running-config で `redistribute static subnets ...` の
  **`subnets` を暗黙化**するため、完全形の `no redistribute static subnets
  route-map X` は当たらない。**オプション無しの `no redistribute static`** で消す
  (初回実行で RO5 が ASBR のまま残り、border-routers が 1 行多くなった)。
- OSPF ケースは RO3 を **ASBR 専任**にする(area 2 を外す)。ABR 兼務だと
  `show ip ospf border-routers` の役割欄が盤面と別物になる。
- console 接続は落ちることがある。OSPF ケースに必要なノードは
  `connect_all(required=...)` で**必須指定**する(未接続のまま進むと KeyError で
  ケースごと落ちる)。

## 紙面設計への反映

- OSPF の証拠ブロックは **`show ip ospf database external` + `show ip ospf border-routers`**
  の2枚で足りる(RIB を見せると答えが出てしまうため read 形では出さない)。
- EIGRP は **`show ip eigrp topology all-links` 1枚**が主証拠。
  「表に出ている経路」の集合自体が §11 の制約を受けるので、盤面生成では
  `check_board()` を必ず通す。
- ★§8 の「FD 460800 は載らないのに 486400 は載る」は
  `fc_strict` kind の中核。allthat 形(FS をすべて選べ)の錯乱肢もここから作る。

## 運用メモ

- IOL 11台の起動〜console 接続〜base 投入で約 6 分。全探針で約 25 分・E2E は約 20 分。
- 探針は冪等(base は毎回全行投入)。中断しても `probe.py <名前>` で再開できる。
- o7(NSSA の N1/N2)は未実施。N1/N2 を kinds に入れる段になったら追加で回す。
