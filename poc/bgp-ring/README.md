# PoC: 4台リングBGP・AS設計/ポリシー層TS (BL-093) — 2026-08-05

環境: `problems/_POC-BGPRING`（IOL iol-xe 17.15 ×4・物理リング固定・SSH）。
操作は `poc/bgp-ring/drive.py`（paramiko の show/conf 薄ヘルパ・mgmt_map.yml 参照）。
基線 = four_as（RT0n=AS6500n・eBGP×4区間・各機 Lo1=172.16.n.0/24 を network 広告）。
PoC中に SSH 越しの動的組み替えで split_company（RT01/RT03=AS65100）→ one_as（全AS65000
iBGPフルメッシュ×OSPFアンダーレイ）へ layout を遷移させ、P1〜P6 を全消化。

## 結論サマリ

| # | 項目 | 結果 |
|---|------|------|
| P5 | no_transit | ✅ 両解成立（filter-list `^$` / route-map×prefix-list） |
| P4 | med_cross_as | ✅ 症状・復旧とも成立（設計を一部修正） |
| P2 | stale as-override | ⚠️ **素の4ASリングでは完全不発**（機構解明済・shape再設計） |
| P3 | stale allowas-in | ⚠️ 同上（一周戻りの受理は成立・実害なし） |
| P1 | split_company | ✅ 本命成立＋**ISP側as-override残骸の非対称変種も実証** |
| P6 | ibgp_ring | ✅ 成立（全Established・対角のみ欠落） |

## P5: 非トランジット化（成立）

- 基線の対角プレフィックスは AS長2のタイ→ **oldest path 勝ちで自然にトランジット利用が発生**
  （RT02 が 172.16.4.0 を RT01 経由で選んでいた）。broken 状態を作為的に作る必要がない。
- `ip as-path access-list 1 permit ^$` + filter-list out 両隣接、で他AS経路の再広告が止まり、
  自prefixの広告は維持。`clear ip bgp * soft out` で即時反映（8秒以内に対向で消滅確認）。
- route-map 解（match ip address prefix-list PL-SELF）も同等に成立。
- 採点指紋: 送信側 `show ip bgp neighbors <x> advertised-routes` が自prefixのみ
  （`Total number of prefixes 1`）/ 受信側 `show ip bgp neighbors <y> routes`。

## P4: MED×異AS比較（成立・設計修正あり）

- **設計修正**: リングでは起源ASのMEDは非隣接ルータに届かない（MEDは非推移属性）。
  「対角prefixの2経路に、両ISP(RT02/RT04)がそれぞれMEDを付ける」形が正しい盤面。
- 症状実測: RT01 で 172.16.3.0 の2経路（`65002 65003` MED50 / `65004 65003` MED200）が
  **異AS間のため比較されず MED200 側がベスト**のまま =「設定はある・値も正しい・効かない」。
- `bgp always-compare-med` 投入で **clear 不要・15秒以内に自動でベスト再計算**され MED50 側へ反転
  （IOL 17.15。distance bgp の clear必須と対照的）。
- AS長が違う組（172.16.4.0 の 1AS vs 3AS）は MED以前に AS長で決まる=読解の錯乱肢素材。

## P2/P3: as-override / allowas-in 残骸（★最重要知見・shape再設計）

**素の4ASリングでは両者とも完全に不発**（テーブルにも痕跡が出ない）。機構（全て実測）:

1. IOS は学習元ピアに対しても**ベスト経路を送り返す**（同一サブネットでは third-party
   next-hop 付き）。送信側抑止は無い（advertised-routes 表示にも載る）。
2. 受信側が二重チェックで捨てる:
   `DENIED due to: AS-PATH contains our own AS; NEXTHOP is our own address;`
   → as-override が ASパスを綺麗にしても **NEXTHOPチェックで直接折返しは絶対に入らない**。
3. 偽装/戻りパスが実際にテーブルへ現れるのは「**リングを一周した経路が各ホップでベストに
   選ばれて伝播した**」時のみ。健全なリングでは最短AS経路が常に勝つため一周パスは伝播しない。
   今回は LP残骸を2台に仕込んでようやく誘発（ラボTSとしては不自然な多段前提）。
4. 誘発時の指紋:
   - as-override: 受信側で**送信者ASが離れた2箇所に出現**し得る（`65002 65001 65004 65002`）。
     隣接重複（`65002 65002`）とは限らない（直接折返し形は隣接重複になる→P1変種参照）。
   - **advertised-routes 表示は as-override 書き換え前のパスを見せる**（wire と食い違う）
     = 切り分け問題の罠として一級品。
   - allowas-in: 自prefixの代替エントリに自AS入りパス（`65002 65001 65004 65003`）。
     自prefixは local(weight32768) 勝ちで**実害なし=テーブル汚染のみ**。
5. 定常性: 観測した全状態で**安定・振動なし**。2点間の転送ループは NEXTHOPチェックが
   偽装折返しを止めるため構造的に成立しない。

**→ shape 再設計**: stale の主役は **weight/LP 残骸**（正しい設計が「あるのに効かない」・
weight はテーブル非目立ちで実害直撃）。as-override/allowas-in は
①split_company の非対称ミステリー変種（P1参照）②紙面 cause 形
「この残骸は何に影響しているか→実は何も起きていない(不発の機構を説明させる)」に転用。

## P1: split_company 対角同一AS（本命成立）

- RT01/RT03=AS65100・RT02/RT04=ISP。対角の経路交換が両方向とも死ぬ。
- DENIED 指紋の**読み分け**が採れた: 対角経路= `AS-PATH contains our own AS` のみ /
  自prefixの折返し= `AS-PATH ...; NEXTHOP is our own address;` 併記（debug ip bgp updates in）。
- 復旧: 両拠点×両ISP向け `neighbor <ISP> allowas-in` → 対角prefixが**2経路**（`65002 65100`
  / `65004 65100`）で入り ping 100%。冗長性採点は `show ip bgp` の2経路regexで可。
- **変種実証=ISP側 as-override 残骸で片側だけ通る**: RT03 の allowas-in を外し RT02(ISP-A)に
  `neighbor <RT03> as-override` → RT03 は **ISP-A経由のみ** 172.16.1.0 を `65002 65002`
  （隣接重複指紋）で受理・ISP-B経由は無し。「片系だけ疎通・冗長性がない・パスにISPのASが
  2連続」という非対称ミステリーが1故障で成立。fixの方向（allowas-in統一 or 撤去指示）は
  監査要件の書き方で強制できる。

## P6: ibgp_ring フルメッシュ欠落（成立)

- 全AS65000・Lo0ピア12本フルメッシュ×OSPFアンダーレイ。対角1対（RT01-RT03）を削除:
  **残セッション全て Established のまま、対角prefixだけ相互に欠落**・ping 0%。
- 中継 RT02/RT04 は全経路を保持するが反射しない（iBGPスプリットホライズン）=
  「経路を持っている中継が配らない」を読ませる形。診断は `show ip bgp summary` のピア数
  （n-1=3本あるべきが2本）と、中継側テーブルとの突き合わせ。

## 運用知見（生成器・採点設計に直結）

1. **対角prefixのタイは oldest path 勝ちで非決定的**（PoC中も操作順で何度も入れ替わった）。
   生成器は必ず「ポリシーで向きを固定」or `bgp bestpath compare-routerid` を焼くこと。
   path_select 系の採点は固定なしでは再現しない。
2. **BGPプロセスを no router bgp→作り直した直後は read-only モード（update-delay 既定120s）**:
   セッション Established でも PfxRcd 0・ローカル路 `*`(no best) が最大2分続く。
   採点・検証は投入後2分待つか `bgp update-delay` 短縮を検討。
3. **新規に inbound route-map を付けた直後の soft in が不発なことがある**（route refresh が
   ポリシー反映前に走る様子）。確実なのは `clear ip bgp <nbr> in`（ハード）。fix手順は
   ハード clear を標準にする。
4. `bgp always-compare-med` は clear 不要で自動再計算（≦15s）。
5. drive.py（paramiko invoke_shell）で IOL 4台の conf/show が全て安定動作。
   生成器の fix_generated 経路はこの知見の上で従来どおり ios_config でよい。

## 残課題（実装フェーズへ）

- stale shape の故障カタログ確定（weight残骸/LP残骸/med_missing系との複合规則）。
- split_company の as-override 変種を「fix=残骸撤去+allowas-in統一」まで通しで採点する
  grade.yml の regex 設計（`65002 65002` の不在確認は not_regex+正regexペア）。
- one_as で外部経路を模す static+redistribute 軸（next-hop-self 故障の器）は未検証（v1.1 でも可）。
