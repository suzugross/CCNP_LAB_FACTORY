# 新紙面3ファミリ計画 — CoPP / DMVPN / 経路選好(OSPF・EIGRP) (2026-08-16)

発端= 拡張棚卸(BL-111・EXPANSION-INVENTORY-2026-08)の推奨①②③に対するユーザ指示:
**「問われる知識は試験範囲内(若干超え可)。ただし思考力・構造分析・読解・正答の形式は
実試験以上を目指す(正答複数選択・ひっかけ・要件文の曖昧さ)」**。まず調査・計画。

## 0. 共通設計原則(3ファミリ標準・以後の新ファミリにも適用)

1. **知識境界**: v1.1 明示項目＋その実挙動(実測で確定した既定動作)まで。
   「若干超え」は実測既定挙動(例: match access-group の deny=分類除外)に限る。
   範囲外の深掘り(CCIE 級)は解答 md の「裏話」節のみ=選択肢の正誤には使わない。
2. **認知負荷の装置(標準搭載)**:
   - **複数選択**: 「2つ/3つ選択」(数明示)を主形に、各ファミリ1形は
     **「該当するものをすべて選べ」(数非明示)** を持つ。正解集合は selftest で機械検証。
   - **ひっかけ**: ①「真だが設問に答えていない」肢 ②近似値肢(WCトリック型)
     ③ロール/文脈依存の意味論取り違え肢、を各形に最低1つ。
     「選択肢に因果を書かない」恒久規約は維持。
   - **曖昧要件**: BL-113 の3条件(矛盾なし/一意に補完可/一意性維持)下の意図的不完備。
     要件文に多義語・未提示前提を置き、盤面の事実で一意化する。**新ファミリは
     生まれた時からこの規約で作る**(後付け監査でなく)。
3. 曖昧さを入れるほど**一意性の機械検証が生命線**: モデル層(決定リスト/意味評価器)
   または selftest による正解集合検証を必須とする。不親切化・keep_ask・byte 決定性の
   既存規約は全適用。

## 1. ① CoPP 紙面 (BL-125)

- **範囲**: 3.3(明示・完全空白)。知識セット= control-plane input への MQC
  (class-map match access-group/protocol・police conform/exceed action)・
  class-default 道連れ・**ACL の permit=分類対象/deny=分類除外**・
  **CoPP は punt トラフィックのみ対象(transit は対象外)**・bps/pps 単位・
  `show policy-map control-plane` のカウンタ読解。
- **資産**: ENCOR-COPP-01/02/03(実機済・police/control-plane 採点実績)・
  **acl_model.py**(意味評価器。BL-100 設計どおり「分類→police」層を上に載せる)・
  BL-106 実測「CoPP の match access-group は未定義 ACL だと**どれにも一致しない**
  (IF 適用の全許可と逆)」= ひっかけの核。
- **方式**: 紙面専用(合成)。PoC で出力書式を byte 採取し selftest で常時照合。
- **worlds(正解反転レバー)案**: 保護/制限の役割反転・conform/exceed の action 取り違え・
  deny の意味・class 評価順・class-default 道連れ・未定義 ACL 参照。
- **forms**: read(このパケットは police されるか)/cause(SSH 断の理由)/fix/
  select2/★all-that-apply(「この設定で影響を受けるトラフィックをすべて」)。
- **曖昧要件例**: 「運用に必要な管理アクセスは維持すること」(プロトコル未提示→
  盤面の vty transport 設定から一意補完)。
- **PoC 項目(poc/copp/・半日)**: ①IOL の counters/violated 書式 ②deny・未定義 ACL の
  実挙動追試 ③pps/bps 両単位 ④exceed transmit vs drop ⑤transit 非対象の実証。
- **フェーズ**: P0 PoC → P1 モデル+fix/cause+selftest → P2 read/select2/all-that-apply+
  曖昧要件世界 → E2E(書式照合+実機スポット) → mixed 合流。

## 2. ② DMVPN 紙面化 (BL-126)

- **範囲**: 2.3(明示・VPN 20% の紙面ゼロ解消)。知識= NHRP 登録/解決・mGRE・
  tunnel key/auth・multicast map・Phase2/3(split-horizon/next-hop-self vs
  redirect/shortcut)・IPsec profile 連結・`show dmvpn`/`show ip nhrp`/
  `show crypto session` の読解。
- **資産**: gen_dmvpn_ts **16故障・全実機済**+実測知見(NHRP auth 8字上限・Attrb 列拘束・
  mGRE 再帰は RECURDOWN 非発出・i7/i8 は Tunnel bounce 必須)。
- **方式**: **実機収集型(ring 方式)** を推奨 — 状態表(Attrb/NHRP cache/IKE)の合成は
  byte 再現コストが高く、盤面は全故障実測済み。console 収集(paper_collect)は動作実証済。
- **故障→紙面写像(候補12/16)**: u1/g1/g2/n1/n2/n4/i1/i4/i6/r1/p1/r2
  (i3/i7/i8 は crypto 深部で紙面では過剰=ラボ専用に残す)。
- **worlds**: 「spoke-spoke 直行必須(Phase3)」vs「hub 経由容認」・「PSK 変更禁止」・
  「トンネル IF のみ変更可」で正解反転。
- **forms**: cause(状態表読解)/fix/select2(対修正: r1 split-horizon+next-hop 系、
  p1 redirect+shortcut 系=**複数選択が最も自然な題材**)/★read(「spoke1→spoke2 の
  初回パケットと 2 回目はどこを通るか」= Phase 理解の本丸)/impact。
- **ひっかけ核**: Attrb S/D/I の読み違え・「UP なのに通らない」(NHRP/IPsec/routing の
  層分離)・「登録は成功しているのに解決が失敗」。
- **フェーズ**: P0 証拠セット設計(追加実測は最小) → P1 fix/cause+実機収集パイプ →
  P2 read/select2+曖昧要件 → E2E。**3題材中最重量・専用セッション推奨**。

## 3. ③ 経路選好 紙面 — OSPF 1.10.d × EIGRP 1.9.c (BL-127)

- **範囲**: 1.10.d(intra > inter > E1 > E2 の型優先・E1 累積/E2 固定+forward metric・
  N1/N2)・1.9.c(FD/RD/successor/**FC= RD < 現 successor の FD**/FS/variance の適用条件)。
  SIA は cause の裏話寄りに留める。
- **方式**: **bgpbest 方式(決定リストの純関数モデル・紙面専用・実機不要)**。
  `ospfpref_model.py` / `eigrpfs_model.py` — LSDB 断片・topology table を合成し、
  勝者+決め手の段+消去の遍歴を返す。bgpbest の「測定不能盤面の strict 拒否」を踏襲。
- **worlds**: 「E1 化禁止」「エリア構成凍結」「variance 上限指定」「コスト変更は1箇所」
  等の要件レバーで正解反転。
- **forms**: read(どれが選ばれるか)/why(決め手の段)/fix(この経路を選ばせるには)/
  cause/★**all-that-apply の初弾=「FS になり得る経路をすべて選べ」**(FC 判定は
  機械計算可能で正解集合の検証が完全にできる=数非明示形の理想的な導入先)。
- **ひっかけ核**: 「コストが小さい O IA は O に勝てない(型が先)」・「E2 同士は
  metric→forward metric の2段」・「FC は RD と **FD** の比較(RD 同士ではない)」・
  「variance は FS のみを乗せる(FC 不成立の経路は倍率に関係なく不採用)」。
- **PoC(poc/ospfpref/・小)**: 出力書式の byte 採取1回
  (show ip route <prefix>・show ip ospf database router/external・
  show ip eigrp topology all-links)。以後実機不要。
- **フェーズ**: P0 書式採取 → P1 モデル+read/why+selftest → P2 fix/cause/
  all-that-apply+曖昧要件 → 実機5ケース照合(ospfv3pl 方式) → mixed 合流。

## 4. 実装順の推奨と工数感

**① CoPP(PoC 半日+実装1〜2日) → ③ 経路選好(モデル駆動・実機待ちなし・2〜3日)
→ ② DMVPN(最重量・2〜3日・専用セッション)**。
③は実機依存が無いので、①の PoC 待ち時間に並行着手できる。
共通原則(§0)の実装部品(all-that-apply の正解集合検証・曖昧要件の3条件チェック)は
①で作って③②へ流用する。

## 5. 台帳

- BL-125(CoPP)/BL-126(DMVPN)/BL-127(経路選好) を新設・本メモを正典とする。
- 完了時は BL-100 の該当行(④・第二群)にも消化を追記する。
