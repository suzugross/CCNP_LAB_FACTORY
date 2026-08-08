# OSPFv3 Prefix-List 紙面ファミリ (BL-097)

ユーザ手組ラボ「OSPFv3 Prefix-List exam」(CML lab id 9a2b950e-79b0-4927-9aca-5713dcada2ce)
を発端とする、マルチエリアOSPFv3 経路フィルタリングの紙面問題ファミリ。

## handmade/ — 手組ラボの保全コピー

2026-08-07 にコンソール経由で収集した running-config 全文(5台)。
ラボは機器台数節約のため **stop 済み(削除はしていない)**。各機器で wr mem 済みなので
lab start すればこの状態で復帰する。万一失われてもこの .cfg から再構築可能。

- トポロジ: R2 をハブに R1(Area 10)・Ra/Rb/Rc(Area 0) のスター。全て iol-xe。
  - R1:E0/0—R2:E0/0 / R2:E0/1—Ra:E0/0 / R2:E0/2—Rb:E0/0 / R2:E0/3—Rc:E0/0
- R2 が ABR。`area 0 filter-list prefix PL01 out`(C:C::/64 遮断) と
  `area 10 filter-list prefix PL02 in`(2001:DB8:8::/45 le 64 のみ許可) の二重掛け。
- R1 E0/0 のセカンダリ 2001:DB8:2:2::/64 は消し忘れ由来だが、
  「1つのIF設定で複数プレフィックス広告」「filter-list の intra-area 免疫」素材として採用予定。

## 手組ラボの狙い(ユーザ談・設計に引き継ぐ)

- 第3ヘクステットを 9→A→B→C と並べ、16進繰り上がりの読み違いを誘う
  (本来は 9:9/A:A/B:B/C:C の4本構成が意図。手組では A:A/B:B/C:C の3本)。
- /45 等ヘクステット中間のマスク境界で、2進展開しないと包含判定できない層を作る。
- C:C のような第3=第4ヘクステット同値で「/48 以下でないと第4に掛かる」視覚ノイズ。
- prefix-list パターンのレパートリーは可能な限り充実させる。

## PoC 結果 (2026-08-07 全件実測完了・iol-xe 17.15)

PoC ラボ= **POC-OSPFV3PL**(IOL 4台・3エリア・console直駆動・wr mem済で stop 保管)。
R2(ABR)ハブ: e0/0→R1(Area10・セカンダリ2:2持ち) / e0/1→Ra(Area0・Lo 9:9/A:A/B:B/C:C を
/64広告=`ipv6 ospf network point-to-point`) / e0/2→R3(Area20)。
実行= `sweep.py`(シナリオ名引数で個別再実行可)・生ログ= `results-raw.md`。

- [x] **E1 in/out 方向意味論**: `area 0 ... out`=Area0から出る Type-3 を**全他エリアで**遮断
  (R1・R3両方から消えた)。`area 10 ... in`=Area10へ入る分だけ遮断(R1のみ消えR3は残る)。
  **第3エリアがあると in/out は非等価** — 実測で確定。
- [x] **E2 distribute-list の効く層**: AF配下 `distribute-list prefix-list X in` 受理。
  内部ルータ(R1)では **RIBのみ消え LSDB には Type-3 が残る**(古典どおり)。
  ★ただし **ABR(R2)に掛けると Type-3 origination 自体が止まる**(R1・R3からも消えた)
  = ABR の Type-3 生成は RIB 依存。「distribute-list はLSAに効かない」の例外として最良の作問素材。
- [x] **E3 area range**: AF配下 `area 0 range 2001:DB8:8::/45 [not-advertise]` 受理。
  not-advertise=成分4本全滅・advertise=集約 /45 1本のみ+**ABR に O .../45 via Null0 の
  discard 経路**が立つ(v2と同挙動)。
- [x] **E4 intra-area 免疫**: `area 10 filter-list ... out` で 2:2 を遮断しても
  R2(ABR自身・Area10メンバ)の RIB は intra-area O のまま残る。Ra/R3 からは消える。
- [x] **E5 ge/le 構文**: 不正5種(ge<len / **ge=len** / ge>le / le<len / **le=len**)は全て
  `% Invalid prefix range for <prefix>, make sure: len < ge-value <= le-value` で拒否
  (**ge・le とも len と同値は不可**=厳密に len < ge ≤ le / len < le)。
  `::/0 le 128`(全マッチ)・`::/0 ge 1`(**デフォルト以外の全マッチ**=/1〜/128)・
  **`ge 64 le 64`(=ちょうど/64のみ・ge=le は可)**・`le 63`(=/64を拾えない1-off)は受理。
  `::/0 le 0` は受理後 **`permit ::/0` に正規化**(le 0 消滅・2026-08-08 追測)。
- [x] **E6 clear 要否**: filter-list / distribute-list / area range とも**適用・撤去は
  clear 不要で 0〜4秒で全域伝播**(Type-3 の再生成/フラッシュが即時走る)。
- [x] **E7 中間マスク被覆**: /45=8〜F(9ABC全部) → /46=8〜B(**C:Cだけ外れる**)
  → /47(A::/47)=A〜B のみ、と1bit刻みの被覆反転を実測。permit単独リストの暗黙denyで
  リンク網 OI(0:A/3:3)も消える(全滅系の採点素材)。`permit ::/0` 単体=デフォルトのみ
  マッチ→**inter-area 全滅**も実測(E7c)。

### P1 実装時の追加実測 (2026-08-08・spotcheck.py)

- [x] **モデル⇔実機一致**: 生成器の写像モデルが出す R1/R3 経路表と実機を5ケースで突き合わせ
  (dir_swap/mask_off+range/★dl_abr のType-3波及/le_off の全滅/seq_shadow の no-op)→**全一致**。
  ※初回1ケースはラボ起動直後の収束レースで偽不一致→スポット確認は基線待ち必須(教訓)。
- [x] **未定義 prefix-list 参照の filter-list = 全許可(no-op)**(`area 10 filter-list prefix
  PL_GHOST_UNDEF in` で経路変化なし)。leakmap の E1(route-map 未定義=リークなし)とは逆向きの
  デフォルト。P2 の故障種(typo参照=効かない)として使える。

### dual_select 追実装時の実測 (2026-08-08)

- [x] **in/out 両掛けの直列合成**: `area 0 filter-list out`(deny形)+`area <a1> filter-list in`
  (permit形)の同時適用は**両方が独立に直列適用**される(モデルの AND 合成と実機2ケース完全一致
  =mask_off/dual・seq_shadow/dual)。手組ラボの二重掛け(PL01 out+PL02 in)の一般化。
- 同日: リンク網プレフィックスの毎回抽選化(第3ヘクステット 0..7 帯)と、range 被覆の
  実機忠実化(**Area 0 range はリンク網も範囲に畳む**=/44 等でリンクが吸われる系を正しく写像)。

★ハーネス知見: virl2_client の `connect_two_nodes` は**既存の空き e0/x を使わず新規
E1/x を勝手に作って結線する**(populate_interfaces=True でも)。IF ラベル明示の
`create_link` を使うこと(sweep.py 修正済)。IOL は未結線でも up/up なので気づきにくい。
また IOL は一度起動すると IF 削除不可(Physical configuration locked・未結線なら無害)。

## 次工程

設計完了= [OSPFV3-PL-PAPER.design.md](../../problems/_drafts/OSPFV3-PL-PAPER.design.md)
(2026-08-08 le 境界追測込み・未測項目なし)。次= 生成器実装
(gen_paper_ospfv3pl.py + gen_paper_mcq `--shape ospfv3pl`)。
