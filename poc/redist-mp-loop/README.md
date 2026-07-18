# 多点相互再配送×seed metric 定常ループ PoC (BL-058) — 結果 (2026-07-16)

Ping-t #26308（多点相互再配送によるルーティングループ→distribute-list で防止）の
忠実再現 Phase 0。**全項目成立 → 出題化可**。実装形は手組み単問が素直
（gen_redist_loop_ts.py とはトポロジ・機序が異なる）。

## 検証環境（poc-redist26308-iol-lab.yaml, iol-xe-17-15-01 ×6・コンソールのみ／MGMTリース不使用）

```
   [OSPF]          [EIGRP AS1]                  [RIPv2]
        RB ---- 172.16.11.0/24 ----+
  .1.0/24 |                        |
   RA     |                        RD -- .31.0/24 -- RE -- .41.0/24 -- RF -- Lo0 192.168.1.6/24
  .2.0/24 |                        |                                   (rip network 192.168.1.0)
        RC ---- 172.16.12.0/24 ----+
```

- 各ルータのホスト部オクテット = A:1 / B:2 / C:3 / D:4 / E:5 / F:6（PDF と同一）
- RB/RC = OSPF⇄EIGRP **2点相互再配送**（タグ/フィルタ無し＝故障状態を day0 焼込み）
- RF = RIP→EIGRP 片方向再配送。seed は全て `metric 1000000 1 255 1 1500`

## 検証結果

### 1. 定常ループ成立（PDF の鏡像・★BL-056 知見②の振動は起きない）

- RD: `D EX 192.168.1.0/24 [170/281856] via 172.16.11.2(RB)` — **再注入経路
  （topology で External protocol is OSPF）が正規経路（via RE 307456・External
  protocol is RIP）にメトリックで勝つ**。AD は両者 170 のまま＝AD 無操作で成立。
- RA traceroute 192.168.1.6: `RA→RC→RD→RB→RA` の 4 ホップ周期で無限循環
  （PDF は RA→RB→RD→RC→RA。鏡像はどちらでも病理同一）。
- 平衡の構造（自己無矛盾で固定される理由）:
  - **RC = EIGRP 勝ち側**: RIB が D EX(170) → `redistribute eigrp→ospf` が発火し
    Type-5 起点になる（自分の LSA からは経路を作らないので D EX のまま安定）
  - **RB = OSPF 勝ち側**: RC 発の O E2(110) が D EX(170) に勝つ → E→O は止まるが
    **O→E 再注入源**になる（`show ip route` に `Advertised by eigrp 1 metric ...` が出る）
  - 2 境界が役割分担するため互いの RIB 勝者が固定 → **age 10分19秒まで無振動**。
    単一境界の自己制限振動（BL-056 知見②）はこの 2 点構成では発生しない。

### 2. メトリック再現性

| 経路 | IOL Ethernet (BW10000/delay1000µs) | PDF (GigE BW1000000/delay10µs) |
|------|-----------------------------------|-------------------------------|
| 再注入（境界経由・RD から 1 ホップ） | **281856** | 3072 |
| 正規（RF 起点・RD から 2 ホップ） | 307456 | 3328 |

式は同一（256×(10^7/BW_min + Σdelay/10)）。**不等号の構造は「再注入点の方が
RD に 1 ホップ近い」ことから来る＝IF 種別非依存**。PDF の字面どおりの
3072/3328 が欲しければ IOSv（GigE）で組めば再現する（出題は IOL で問題なし）。

### 3. 修正（PDF 正解）の完全動作

RB/RC **両方**に:

```
access-list 1 deny 192.168.1.0 0.0.0.255
access-list 1 permit any
router eigrp 1
 distribute-list 1 out ospf 1
```

- RD が正規 `[170/307456] via 172.16.31.5(RE)` に復帰・topology 単一エントリ化
- RA traceroute 4 ホップ完走（LAN を Lo0 で模擬しているため PDF の 5 ホップ目
  表示は出ない・cosmetic）・ping **20/20 (100%)**
- **負の要件も安全**: 172.16.1.0/24・172.16.2.0/24 の D EX ECMP は無傷
  （ACL が victim prefix だけを deny するため）
- ★採点信号: `show ip protocols | section eigrp` に
  **`Redistributed ospf 1 filtered by 1`** が立つ（fix 存在の raw チェックに最適）

### 4. 再現性（provision 耐性）

- `clear ip route *`（RB/RC/RD 同時）→ 同一平衡に再収束しループ再形成
- コールドブート 2 回とも同一鏡像（RC=E→O 側）で再現・修正未 write mem なら
  stop/start で day0 故障状態に完全復帰
- ★ただし**鏡像の向きはプロトコル保証ではない**（収束レース）→ 採点は向き非依存
  （netmodel loop_free / reachability）で設計すること。task.md の出力例も
  「繰り返しパターン」の読み方を教える形にし、特定の向きを断定しない。

### 5. 前提の確認

- `redistribute rip` は rip `network` 配下の **connected**（Lo0 192.168.1.0/24）を
  拾う（RIP ネイバー不在でも成立・17.15 実証）— PDF 構成が 6 台で済む根拠。

## 追加 probe（2026-07-16・解法モードランダム化の実装前検証）

同一ラボで解法プール3種を追加検証（acl 版は本編 PoC で検証済）。全て効果◎＋revert でループ復元確認。

| 解法 | 実機結果 | 採点指紋（実機採取） |
|------|---------|---------------------|
| prefix-list 版 `distribute-list prefix <名> out ospf 1` | RD 正規復帰・traceroute 完走 | `Redistributed ospf 1 filtered by (prefix-list) PL-NOFB` |
| 経路タグ版（E→O `route-map SET-TAG`(set tag) / O→E `route-map DENY-TAG`(match tag deny)） | RD 正規復帰。OSPF勝ち側境界は O E2 遠回りが正常残留（5ホップ到達・ループ無し） | RA `show ip route <victim>` に **`Tag 110, type extern 2`** と **`Route tag 110`** の2行 |
| distance 版 `distance ospf external 180`（両境界） | 両境界とも D EX 直行・RD 正規・ping 100% | `show ip protocols` に `Distance: intra-area 110 inter-area 110 external 180` |

- ★**distance は clear 不要**: 撤去→ループ復元→再投入のクリーン測定で**16秒で自然収束**
  （`distance bgp` が clear 必須だった BL-056 知見③とは別挙動。OSPF は distance 変更で
  RIB 再調停が即時に走る）。
- distance 版の機序: 境界の RIB が EIGRP になると `redistribute ospf` が victim を
  拾わなくなり**再注入そのものが止まる**（火元の消火）。`distance eigrp 90 100` 形
  （EIGRP 外部を 110 未満へ下げる）でも同効果=別解。

## 本実装（gen_redist_mp_ts.py・2026-07-16 完成）

**`--solution acl|prefix|routemap|distance`（既定 seed 抽選）で要求解法がランダムに変わる**。
初期 config（故障状態）は全モード共通・task.md の監査ポリシーと grading だけが変わる。
採点= netmodel(reach 25/loop_free 25/optimal 10)＋RD 正規経路 10＋RA O E2 維持 5＋
RB/RC「指定解法の指紋 regex ＋ 他解法禁止 not_regex」複合 各10＋静的 ban 5。

- **optimal は RB/RC→RF を除外**: フィルタ系解法（acl/prefix/routemap）では OSPF 勝ち側
  境界の O E2 遠回り（到達可・ループ無し）が正常な最終状態のため。除外は鏡像の向きに
  依存しない（両方除外）。
- 実機フルサイクル（seed 9101-9104・掃除済）: broken 5〜20（値は起動直後の過渡サンプル
  タイミング依存・定常は 10）→ 模範解答 → **4モードとも 100/100 収束**。
- 誤解法クロスチェック実証: acl モードに distance 混入→90 / distance モードに
  distribute-list 混入→90（禁止 not_regex 層が監査違反を検出）。
- ★実装で踏んだ実機罠2点:
  1. `show ip route <pfx>`（詳細ビュー）の next-hop 行は `* <ip>, from <ip>, ... via <IF名>`
     — **`via <IP>` はテーブルビュー専用**。next-hop 判定 regex は `\* <ip>,` を使う。
  2. iol-xe 17.15 は `redistribute eigrp N subnets route-map X` の **subnets を
     running-config 表示から暗黙化**（BL-019 の subnets 暗黙定と同種）→ 指紋 regex は
     `(subnets )?` の両対応が必須。

## 出題化に向けた設計メモ

- 差別化: 既存の REDIST-LOOP-01/MUTUAL-01（AD95 操作・次善止まり）、
  REDIST-BGP-LOOP-01（AD 逆転・iBGP）に対し、本問は **AD 標準のまま
  seed metric だけでループが立つ最古典形**＋**`distribute-list <ACL> out <protocol>`
  （再配送点フィルタ・リポ初の out 方向）**。
- 採点案: netmodel loop_free + reachability(RA→192.168.1.6) + raw
  （`Redistributed ospf 1 filtered by 1` を **RB/RC 両方**に要求）+
  負の要件（172.16.1.0/24・172.16.2.0/24 到達性維持＝過剰フィルタ検出）。
- **片側のみ修正**の誤答は逆向きループが残る（PDF 解説どおり・2つ選択の題意）
  → 部分点/誤答検証の設計に使える。
- 変種候補: prefix-list/route-map 版、タグ解法許可版、`in` 方向との対比問。
- ヒントは控えめに（ccnp-problem-hint-policy）: 「distribute-list を使え」を
  最初から明かすかは難度設定次第（PDF 設問は明かしている＝難度下げ）。
