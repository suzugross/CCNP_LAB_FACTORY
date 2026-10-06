# FHRP-PATH — 「この盤面で通信はどう抜けるか」紙面(BL-228・2026-09-27 起票・設計段階)

2026-09-27 ユーザ発案(STP ロール当て s_rolemap の試用後)。
「FHRP も絡めて、この盤面の場合に通信がどのように抜けていくかを問う。ハードモードでは ACL も絡む」。
単元= **U-A6 FHRP(紙面ゼロ)** が主・U-A3 STP / U-H3 ACL が従。

## 1. 何を問うか

盤面(STP の役割が VLAN ごとに決まる L2 ＋ 分配ペアの SVI と FHRP)を見せ、
**PC-A(VLAN X)から PC-B(VLAN Y)へ送ったパケットの往路・復路**を答えさせる。

核になる論点(ENCOR 3.3.c・CCNA 3.5):
1. 送信元の既定ゲートウェイ= VLAN X の **Active**(仮想 MAC 宛てのフレームは L2 の木に沿って Active へ届く)。
2. Active がルーティングし、VLAN Y へは**自分の SVI から直接**出す(VLAN Y の Active かどうかは関係ない)。
3. 復路は PC-B の既定ゲートウェイ= **VLAN Y の Active** から。VLAN ごとに Active が違えば**往路と復路が別の分配を通る(非対称)**。
4. STP の root と FHRP の Active がずれていると、PC→Active のフレームが分配間リンクやコアを余計に回る(定番の「揃えよ」の理由)。

ハードモード:
5. **SVI の ACL(in/out)**。ルーティングされるパケットは「入ってきた VLAN の SVI で in」「出ていく VLAN の SVI で out」。
   非対称経路では**往路と復路が別の機器の ACL を通る**(片方の機器にしか ACL を入れていない、が典型の穴)。
   ACL は状態を持たない(戻りは戻りで評価される)。判定は `acl_model.py`(実機検証済みの意味評価器)に通す。
6. (候補)track による priority 減算・preempt の有無と「どちらが先に起動したか」で Active が決まるケース。

## 2. 盤面

- まずは**ラボと同じ盤面**(`gen_stp.py` 2 層= 分配ペアが FHRP / `gen_stp_3tier.py` 3 層= 分配ペアが FHRP・コアは L2 の中継)。
  s_rolemap の「崩し」までは広げてよい(ゲートウェイのペアが残る崩しに限る)。階層でない形は使わない。
- VLAN は 2 つ(X・Y)。STP の priority は VLAN ごとに提示(s_rolemap と同じ表を 2 列に)。
- FHRP の提示= 分配ごと・VLAN ごとに group・priority・preempt・仮想 IP・実 IP。
  **Active の決まり方が履歴に依存する形(preempt 無し)は、状態(show standby brief)を提示するか、起動順を明記する**
  (提示しないと答えが 1 つに決まらない)。

## 3. 解答形式(案)

- **経路の全記入**: 往路と復路それぞれ「通るスイッチを順に」をプルダウン(スイッチ名)で埋める＋「ルーティングする機器」。
  s_rolemap と同じ穴埋め形の UI・**全空欄一致で正答**。経路長が可変なので「以降は通らない」の選択肢(—)を置く。
- 選択問(記述の正誤・すべて選べ)は瞬発寄りの補助として。
- ハード: 「PC-A→PC-B の通信は成立するか。成立しないなら、どの機器のどの SVI のどの方向で落ちるか」(全記入または選択)。

## 4. 裏どり(作問の裏どりルール)と PoC

3 ソース= Cisco 公式(FHRP Configuration Guide・HSRP/VRRP の選出・preempt・仮想 MAC)/ 解説サイト / 問題集。
実機 PoC(CML・IOSvL2 の SVI+HSRP・2 層盤面で足りる)で先に潰す:
1. 選出= priority → 同値なら実 IP の大きい方。preempt 無しで**後から上がった高 priority は Active を奪わない**。
2. 往路・復路の L2 経路の実測(`show mac address-table`・IF カウンタ・大量 ping で差分)。仮想 MAC の学習先。
3. Standby 側の分配が復路をルーティングすること(実 IP の SVI から出る)。
4. SVI の `ip access-group` in/out が、ルーティングされるパケットにどう効くか(入口 VLAN の in・出口 VLAN の out)。
5. (IOSvL2 固有の差があれば記録・公式と食い違えばユーザ判断まで出題しない)

## 5. 実装の見通し

- 新しい紙面ファミリ(shape 名は未定)。L2 経路= `stp_model.Topo.path()`、選出= 小さな関数、ACL= `acl_model`。
- 盤面・表・プルダウンは s_rolemap の部品を流用。
- ★**ユーザ決定(2026-09-27)**: プロトコルは **HSRP のみ**(VRRP は後から種類を足す)/ 解答形式は **経路の全記入**(全空欄一致で正答)。

## 6. 実装記録(2026-09-27・完了)
- `topologies/gen_paper_fhrp.py`(shape `fhrp`・kinds `h_path`/`h_acl`・思考枠)。gen_paper_mcq の KB ファミリに登録。
  単元 U-A6(`units.yml` の paper kinds= `fhrp/*`)・ジャンル l2(`records/genres.yml`)。
- **盤面**= STP ロール当て(s_rolemap)の盤面から「ラボそのまま」と「崩し」だけを使う(階層でない形は使わない)。
  VLAN X は s_rolemap の priority・cost・port-priority、VLAN Y は 60% で priority を引き直す(MAC は同じ)。
  ゲートウェイ= 2 層は SW01・SW02、3 層は SW03・SW04(コアは L2 の中継)。PC-A/PC-B はアクセスに(同じ機器のこともある)。
- **HSRP**= 分配ごと・VLAN ごとに priority(90〜120・既定 100 は表示しない)と preempt を抽選。経緯= 同時起動(60%)か
  「同時起動 → 片方を再起動して復帰」(40%)。Active は `_active`(PoC の 5 規則= selftest で固定)。
  **起動順が不明で答えが割れる形(同値・preempt 無し・起動順を書かない)は出さない**= 経緯は必ず文で与える。
- **経路**= `stp_model.Topo.path`(VLAN ごとの木)で「送信元アクセス → Active X」＋「Active X → 宛先アクセス(VLAN Y)」、
  復路は Y/X を入れ替え。枠の数= 長い方の経路 + 1〜2(経路長が枠の数から割れないように)・「—(ここで終わり)」で埋める。
  空欄= 往路・復路の枠＋ルーティングする機器 2(＋ハードは結果・破棄する機器)で 20 以下。
- **ハード(h_acl)**= SVI の ACL を 1〜3 か所(分配 × VLAN × in/out)。テンプレ 8 種(echo-reply の deny・host 指定・
  応答が暗黙 deny になる permit echo だけ・サブネット指定など)。評価は `acl_model`(実機検証済み)で、往路= Active X の
  X in → Y out、復路= Active Y の Y in → X out。結果(成功/往路で破棄/復路で破棄)を均等に抽選し、**経路外の ACL
  (評価されない罠)を必ず 1 つ含む**。経路は「ACL に関係なく転送の仕組みで決まる経路」を答えさせる(往路で落ちても復路を問う)。
- **検査**= selftest 805 件 NG0(経路の端点・Active を含む・余白・空欄数・漏えい語・正解行の形・選出の 5 規則)。
  非対称は約 4 割・再起動の経緯は約 4 割・ハードの結果はほぼ均等。試用= PACK-TEST-FHRP(4 問)で表内プルダウン数と
  採点の全一致判定を確認。
- **接続表(2026-09-29 追加)**= 図の直後に「スイッチ / インタフェース(ポート番号) / 対向スイッチ / 対向インタフェース(ポート番号)」の表を置く。
  2026-09-27 の試用時点では「図の見辛さも難易度のうち」として付けなかったが、ユーザ要望で追加(線の取り違えで落とすのは狙いではない)。
  s_rolemap はもとから「ポートの一覧」表に接続先を持つので変更なし。
- 残(未着手・BL-228 の続き)= VRRP(preempt 既定オン・所有者 255)を種類として足す / track による priority 減算。
