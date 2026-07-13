# MPLS L3VPN シリーズ — 拡張設計メモ

現状 (2026-07-08 時点・すべて実機検証済):
- **ENARSI-MPLS-L3VPN-01**: 基礎構築 (7台, マルチカスタマー重複prefix, PE-CE static)
- **ENARSI-MPLS-L3VPN-02**: 応用 (PE-CE OSPF 化 + route-map 広告制御 + MSS 1452)
- **gen_mpls_ts.py**: 12台 TS 生成器 (3PE×Pリング×2顧客3サイト, 故障14種+decoy2種)

土台になっている知見 (memory: ccnp-mpls-l3vpn-labs):
- iol-xe 17.15 は redistribute の subnets 暗黙定 / `no redistribute ospf N route-map X`
  はオプションだけ外れる / VRF付きOSPF の parents は `router ospf N vrf X` まで /
  VPNv4 ネイバーは Genie 不可→raw / RD は decoy になり得るため採点で断言しない。

以下、拡張候補の設計詳細。番号は BACKLOG.md の BL-ID に対応。

---

## BL-015 PE-CE eBGP 化（gen `--pece ebgp` 軸 + 応用問 04）— 2026-07-12 検討で具体化

手順書「次に試す実験メニュー」3 の残り半分。ユーザ学習手順書のレイヤ L5 を eBGP に差替。
★番号訂正: 03 は sham-link 問（BL-022）で使用済み → 手組み問は **ENARSI-MPLS-L3VPN-04**。

### ★前半完了（2026-07-12）: ENARSI-MPLS-L3VPN-04 実機フルサイクル済・出題可

未解答 28点（複合化改修前・負の要件の自明PASS分）→ 模範解答 **100/100 一発収束**。
実機 PoC 採取: ①ループ検知指紋 = CE の debug ip bgp updates in に
`rcv UPDATE about 172.16.2.0/24 -- DENIED due to: AS-PATH contains our own AS;`
（merged path 65000 65200）②as-override 後の CE 受信 AS_PATH = `65000 65000`（採点拘束済）。
採点改修: 「10.99 不在」3チェックを「LAN 受信成功 AND 10.99 不在」の複合チェックへ
（負の要件を単独採点しない教訓の適用・未解答ベースライン 28→17点相当）。
成果物= problems/ENARSI-MPLS-L3VPN-04/（initial×7・task・grading 100点・solution）。
ラボ撤収済（scripts/lab.sh provision で再構築可）。**残= 下記 gen 軸移植（後半）**。

### 手組み問 ENARSI-MPLS-L3VPN-04（難4・7台・02 と同トポロジ/チケット形式）— 設計記録

- **初期状態**: 01 完成形からPE-CE ルーティングと AF ipv4 vrf を撤去（02 と同じ
  0点発射形）。CE は顧客管理・変更禁止で **BGP 設定済み**を焼き込み:
  - **CUST_A = サイト毎 AS**（RT04=65101 / RT05=65102）→ 基礎形
  - **CUST_B = 全サイト同一 AS 65200**（RT06/RT07 とも）→ **as-override 必修形**
  - ★2顧客トポロジで基礎形と同一AS形を1問に同居させるのが本問の核。
    CUST_B は AF/neighbor を正しく組んでも**経路が CE で AS_PATH ループ検知され
    届かない**（PE の advertised-routes には在るのに CE の BGP table に無い）
    → 「CE 変更禁止」制約が allowas-in を封じ **as-override が SP 側の唯一解**
    になる（設計判断まで含めて ENARSI 頻出論点を回収）
- **受講者作業（PE のみ）**: ①AF ipv4 vrf ×2 で CE と eBGP（remote-as/activate）
  ②**再配布ゼロで疎通**（eBGP→VPNv4 直行 = 02 の redistribute 方式との対比が
  学習核心。task の考察に「02 で必要だった redistribute はどこへ行ったか」）
  ③広告制御: 10.99.0.0/16 管理 /32 遮断の仕様を継承。ただし実装点が
  redistribute route-map → **neighbor in の prefix-list/route-map** に移る対比
  ④CUST_B に as-override。MSS チケットは 02 で履修済みのため出さない
- **採点**: E2E ping（両顧客）/ CE の `show ip bgp` に対向 LAN（AS_PATH 込み raw
  regex・CUST_B は as-override 指紋 `65000 65000` を拘束）/ 10.99 の対向不在
  （`% Network not in table` 反転）/ PE の advertised-routes / 顧客分離維持。
  VPNv4 ネイバーは Genie 不可→raw（既知）
- **PoC 項目（軽・手組みの中で消化可）**: IOL-XE 17.15 の ①vrf 内 eBGP 基本動作
  ②as-override 動作と AS_PATH 表示 ③CE 側ループ検知の指紋
  （debug ip bgp updates in の DENIED 行 — 解説用に採取）

### gen_mpls_ts `--pece ebgp` 軸 — ★完了（2026-07-12・実機検証済）

- CLI `--pece ebgp`・問題ID `GEN-MPLSEB-<seed>`（従来と衝突しない）。
  render_pe/render_ce/write_grading/write_task の L5 部を軸分岐。
  L1-L4 故障・decoy・乱数消費は無改変 =
  **既存 OSPF seed（7100/100）のバイト単位再現性を diff で確認済み**
- **L5 eBGP 故障 5種（全て実機スイープ済: 症状✓/復旧✓）**:
  `l5e_remote_as_wrong`（Idle 指紋）/ `l5e_activate_missing`（AF 経路交換なし・
  復旧は BGP 再収束にやや時間）/ `l5e_infilter_overbroad`（le 23・★収容 PE の
  VRF からも LAN が消える=再配布方式との差分指紋）/ `l5e_infilter_leak`
  （10.99 混入・監査指摘型）/ `l5e_asoverride_missing`（CUST_B のみ・
  PE は広告しているのに CE table に無い）
- **実機検証**: ベースライン seed 8300 = 100/100 / 全5故障スイープ /
  故障 seed 8302（L3+L5e）= 70点 → fix_generated 単発 → **100点収束**。
  検証 seed は掃除済（出題時は新 seed）
- ★**実機知見（重要・再発防止）**: IOS-XE 17.15 は **eBGP neighbor の remote-as
  直接付け替えが可能**（activate/as-override/route-map は保持・セッションのみ
  再形成）。`no neighbor <ip> remote-as <as>` を使う break/fix は**ネイバーごと
  消え、ios_config の running 比較で既在の属性行がスキップ=神隠し**になる
  （vrf forwarding 復旧と同型の罠）→ **付け替え1行方式**で根絶した

### 工数実績

1. 手組み 04: 半日（PoC 込み・実機フルサイクル）✓ 2026-07-12
2. gen 軸移植 + 実機検証: 半日 ✓ 2026-07-12

## BL-016 フルメッシュ × ハブ&スポーク組み分け（手組み 05 + gen `--vpntopo` 軸）— 2026-07-12 拡張具体化

手順書メニュー 4 の発展形。当初案（ハブ&スポーク単独）を「**要件文から RT 設計を
選ぶ**」問題へ拡張。既存シリーズは RT を与えられたとおり打つだけで、export/import
の独立性を**設計判断**として使う問題が不足している — ここが学習核心。

### ★手組み 05 完了（2026-07-12 実機フルサイクル済・出題可）

- **ENARSI-MPLS-L3VPN-05**: 未解答 **26/100**（環境保存20＋CUST_A健全性6・判別点は全て0）
  → 模範解答 **100/100 一発収束**（max_attempts 6×15s 内）。ラボ撤収済（provision で再構築可）。
- 実機確認: 初期状態=B2↔B3 が P コア直行で疎通（違反状態の traceroute 採取）/
  中間状態（仕様どおり・allowas-in 欠落）= CUST_B_UP に本社 LAN のみ・spoke↔spoke 0%・
  本社↔拠点は生存 = 設計どおりの詰まりポイント / allowas-in 1 投入で復旧。
- 採点の要点: 判別は「hub 経由経路あり(next-hop 1.1.1.1)+AS_PATH 指紋 AND
  直接経路なし(not_regex 対向PE next-hop)」の複合 / traceroute は
  192.168.112.1(本社CE)+192.168.111.2(PE1再入)+着信CE の3点拘束 /
  仕様遵守チェックは進捗マーカ（CUST_B_UP 新設・RT 210/220・旧200撤去）と複合し
  未解答での自明 PASS を防止。
- 初期状態の建付け: 本社 CE(RT08) に移行用 VLAN10/20 サブIF+BGP ネイバーを day0 で
  焼き込み（never/Idle で待機）→「顧客準備済み・SP 側を対応させよ」の現実的な移行シナリオ。
  main IF untagged + サブIF の同居は IOL 実機で問題なし。

### 手組み問 ENARSI-MPLS-L3VPN-05（難4・12台・監査是正チケット形）— 当初設計

- **トポロジ**: gen_mpls_ts の 12台（3PE リング × 2顧客3サイト）を流用。
  20 ノード上限内。hub = site1（RT01 収容）、spoke = site2/3。
- **2顧客同居で対比**（04 の CUST_A/B 同居手法の踏襲）:
  - **CUST_A**: 「全拠点対等・any-to-any」→ 対称 RT 65000:100（フルメッシュ）
  - **CUST_B**: 「本社(site1)集約。拠点間の直接通信はポリシーで禁止・必ず本社経由」
    → 非対称 RT: hub VRF = export **65000:210(RT-HUB)** / import **65000:220(RT-SPOKE)**、
    spoke VRF = export 220 / import 210
- **出題形式**: CUST_B を**全対称 RT で焼いた状態**から「セキュリティ監査で
  spoke 間直接通信が検出された。本社経由に是正せよ」の監査是正チケット。
  「対称 RT のままだと何がまずいか」を直接問える。CUST_A は要件確認のみ（正常）。
- **PE-CE**: eBGP（04 の資産継承）。ただし**サイト毎 AS（65201-65203 等）の基礎形**
  に留め as-override は絡めない — 本問の焦点は RT 設計に絞る。

### spoke↔spoke の扱い — ★PoC 完了（2026-07-12・実機6台・詳細= poc/mpls-hubspoke/README.md）

- **結論: dot1q subif 2セッション + 2VRF half-duplex + allowas-in で完全成立**
  （E2E 100%・折返し traceroute 採取済）。**05 は via-hub 形で実装可**。
- ❌案1（単一セッション折返し）は**不成立**: IOS の送信側ループ抑止は
  「学習元ピアへ送り返さない」= **ピア単位**。CEH の BGP table に spoke 経路が
  在っても学習元セッションへの advertised-routes に載らない → PE 側 allowas-in
  では救えない。ただし抑止は **AS 単位ではない** = 同 AS の別ピア（別 subif
  セッション）へは AS_PATH に 65000 を含む経路も広告する → 2セッション形が成立。
- hub PE 完成形: VRF CUST_B(DOWN)=import 220 のみ / VRF CUST_B_UP=export 210 のみ、
  Et0/2.10(DOWN)/.20(UP)、UP 側 neighbor に **`allowas-in 1`**（無いと DENIED）。
- ★実機指紋: ①PE の DENIED は **`debug bgp all updates in`** でないと出ない
  （`debug ip bgp updates in` 不可）②DENIED 経路は soft-reconfig の
  received-routes にも**現れない**（格納前破棄）③spoke CE の対向 spoke AS_PATH =
  `65000 65201 65000 65203`（hub AS 挟み込み）④traceroute 折返しホップ
  `192.168.1.5 → 192.168.1.6 → 192.168.1.1`。
- IOL は subif ライブ追加可（wipe 不要）→ 初期状態「単一リンク・全対称 RT」から
  是正チケットで PE 側 subif 分割まで受験者にやらせる構成が可能。
  CE 側 2セッションは「顧客が用意済み」として day0 に焼く（CE 変更禁止の建付け・
  04 と整合）。

### 採点（負の要件複合化の教訓を適用）

- CUST_A: 3 ペア any-to-any E2E ping。
- CUST_B: spoke↔hub E2E ✓ / spoke PE の VRF に「hub LAN が**在る** AND
  対向 spoke LAN が**無い**」の複合チェック（not in table 反転を単独採点しない）。
  via-hub 形なら spoke↔spoke E2E ✓ + traceroute の hub CE ホップを raw 拘束。
- 顧客分離維持（A↔B 不通）。

### gen `--vpntopo hubspoke` 軸（問題ID: GEN-MPLSHS-<seed>）

- CUST_B のみ hub&spoke 化。--pece 軸で確立した手法を踏襲し
  **既存 seed（fullmesh 既定）のバイト単位再現性を diff で確認**すること。
- 故障候補: `l4h_spoke_import_missing`（spoke 孤立）/ `l4h_hub_export_wrong`
  （全 spoke が hub 経路喪失）/ `l4h_direct_import_violation`
  （spoke 同士が直接 import = **疎通は「できてしまう」監査指摘型**・
  l5e_infilter_leak と同系）/ （via-hub 形なら）`l4h_allowasin_missing`
  （spoke 間のみ不通・hub 疎通は正常）。
- 既存 l4_rt_export/import 故障は RT 配置が変わるため hubspoke 時の値分岐が要る。

### 工数見積

1. PoC（折返し方式決定）: 半日
2. 手組み 05 実機フルサイクル: 半日〜1日
3. gen 軸移植 + 実機検証: 半日〜1日

## BL-051 Extranet / 共有サービス VRF（手組み 06）— ★完了（2026-07-12 実機フルサイクル済・出題可）

- **ENARSI-MPLS-L3VPN-06 完成**: 未解答 **28/100**（環境保存のみ・判別 16 項目全て 0）→
  模範解答 **100/100 収束**。中間状態（additive 欠落）も実機確認 =
  共有到達は成功するのに自顧客の利用セグメント間だけ 0%・指紋 =
  `Extended Community: RT:65000:301`（既定 RT:100 消失）。ラボ撤収済（provision で再構築可）。
- PoC 全✓ = poc/mpls-extranet/README.md（additive 置換/併記・素朴解の重複衝突
  `imported path from 65000:200:...`・export map 非マッチ経路は既定 RT で正常 export）。
- 以下は当初設計（実装と一致）。

05 の直系続編 = RT 設計の完成形。「1顧客内の非対称（05）」→「**顧客間の選択的共有**」。
実務最頻出の extranet を、シリーズの DNA（重複 prefix）を逆手に取って出題する。

### トポロジ: 9台（04 の 7台 + SVC-PE + SVC-CE・インフラ無改造）

- 04 トポロジの P(RT02) の空きポート 0/2 に **RT08 = SVC-PE**（Lo0 8.8.8.8,
  コアリンク 10.1.28.0/30）をぶら下げ、RT08 の 0/1 に **RT09 = SVC-CE**
  （AS 65300, LAN 172.30.0.0/24 = Lo1, PE-CE 192.168.30.0/30, CE=.1/PE=.2）。
- **初期状態 = 04 の完成形**（PE-CE eBGP・CUST_B は同一 AS 65200 + as-override 済・
  RM-CE-IN = 172.16.0.0/16 le 24 のみ許可・10.99 遮断）。RT08 のコア
  （OSPF/LDP/VPNv4 フルメッシュ参加）も焼き込み済み。SVCS の VRF と PE-CE は未構成。
- CE に**共有サービス利用セグメント Lo2 を day0 焼き込み**（network 文で広告済み・
  CE 変更禁止）: A1=10.65.1.1/24, A2=10.65.2.1/24, B1=10.66.1.1/24, B2=10.66.2.1/24。
  ★A/B の 172.16 は重複のまま、利用セグメントは非重複 — ここが設計の鍵。

### シナリオ（新サービス契約チケット）

SP が共有サービス基盤（DNS/NTP/監視 172.30.0.0/24）の提供を開始。両顧客が契約。
1. 両顧客の全サイト（利用セグメント）↔ 共有サービスの相互到達。
2. **顧客間（A↔B）は引き続き完全分離**（破れは重大事故）。
3. **共有 VRF に顧客の 172.16（重複 prefix）を持ち込まない** — 収容してよいのは
   非重複の利用セグメント 10.65/10.66 のみ（重複 prefix は共有 VRF 内で衝突し
   片顧客が silently 不達になるため。extranet は非重複アドレスが前提、の実務教訓）。
4. 顧客の 10.99 機器管理は引き続き SP 網に受け入れない（04 の仕様継続）。

### 受験者作業（設計仕様・RT 値は与えて配置/実装は設計させる）

- SVC-PE: VRF **SVCS**（rd 65000:300）新設 + SVC-CE と eBGP。
- RT 値: **65000:300 = 共有サービス発** / **65000:301 = 顧客の利用セグメント発**。
- 顧客 VRF（PE1/PE2 の A/B ×4 インスタンス）: import に 300 を追加＋
  **export map で利用セグメントにのみ RT 301 を追加付与**（SP 標準設計として
  export map 方式を仕様で指定。★additive は明かさない）。
- RM-CE-IN の**受信許可の拡張**（明示仕様）: 利用セグメントを通す。
  ★手抜き（permit any 化）は 10.99 が漏れて 04 継承の環境保存チェックで自壊。

### ★隠しひねり（本問の allowas-in 相当）= `set extcommunity rt ... additive` 忘れ

export map で `set extcommunity rt 65000:301` のみ書くと**既定 RT (100/200) が
置換されて消える** → マッチした利用セグメントが自顧客の他サイトから消える =
「共有サービスを繋いだら顧客自身のサイト間（10.65.1↔10.65.2）が壊れた」。
172.16 LAN は map 非マッチで無傷 → 部分故障で気づきにくい。採点は
「アクセスセグメント間 E2E」で拘束。（★additive の正確な挙動は PoC で要確認）

### 採点方針（概算 100 点・0点発射 ≈ env 28）

- 環境保存: 172.16 E2E ×2 / 10.99 不在複合 ×2（04 継承）/ A-B 分離 / SVC-PE コア。
- 判別: SVC PE-CE Established / 4 CE→172.30 ping（source 利用セグメント）×4 /
  SVC-CE→利用セグメント ping ×2 / **SVCS VRF 複合**（10.65.1/2+10.66.1/2 在 AND
  172.16 不在）/ **顧客 VRF 複合**（172.30 在 AND 対向顧客の 10.6x 不在）/
  **additive 拘束** = 10.65.1↔10.65.2・10.66.1↔10.66.2 の E2E / 制約+進捗マーカ。
- 分離の構造: A は RT300 しか import しない → B の経路が入りようがない。
  SVC-CE 経由の A→B transit も A 側に 10.66 の経路が無く不成立（solution で解説）。

### PoC 項目（半日・実装前）

1. IOL/17.15 の vrf af `export map` 構文と挙動（非マッチ経路は既定 RT 維持か）。
2. `set extcommunity rt X additive` の有無での RT 置換/追加の実挙動（罠の指紋採取）。
3. 素朴解（SVCS が RT 100/200 を直接 import）での重複 prefix 衝突の実挙動
   （どちらが勝つか・show の見え方 — solution の解説素材）。
4. RM-CE-IN 拡張と extranet の相互作用（in-filter が利用セグメントを堰き止める確認）。

### 工数見積: PoC 半日 + 実装・実機フルサイクル 1日。問題 ID = ENARSI-MPLS-L3VPN-06（難5）。

## BL-017 意図的 RT 混線 TS（l4_rt_cross_import 故障の追加）

手順書メニュー 2。gen_mpls_ts 初版で見送った故障。

- 見送り理由: 重複 prefix 設計では「B が A の RT を import」しても同一 prefix の
  best path 選択次第で症状が出ない/不安定 (非決定的)。
- 設計案: 混線検出を prefix でなく **PE-CE リンク (192.168.x/30, 顧客毎に非重複)**
  で行う。redistribute connected を base に追加すれば、A の RT を import した
  B の VRF に A の 192.168.x/30 が決定的に現れる → `not in table` 反転チェックで
  採点可能。ただし base への redistribute connected 追加は
  01/02/既存 seed の VPNv4 経路集合を変える → **gen のバージョン軸として追加**
  (`--base v2`) し、既存 seed の再現性を壊さないこと。
- 症状: 「顧客から『他社の経路が見える』」+ B の E2E が経路奪合いで断続。

## BL-018 RR 導入軸（gen `--ibgp rr`）

チェーンTS の rr/fullmesh 軸の MPLS 版。VPNv4 RR。

- 案: 専用 RR ノード RT13 を P1/P2 に接続 (13台, 20上限内・IOL slot 3 以内に
  収まるか配線設計要)。または P1 を RR 兼務 (P の BGP フリー原則を崩すため
  task の設計仕様も変える)。専用ノード案を推す。
- PE は RR とだけ iBGP (フルメッシュ廃止)。故障候補: route-reflector-client
  欠落 / RR の vpnv4 activate 忘れ / cluster-id 二重化。
- チェーンTS の教訓 (client 旗 1 つ外しても壊れない) は VPNv4 でも同様のはず
  → victim 選定は要実機確認。

## BL-019 gen_chain_ts swap モード l3_subnets_missing の再検証

今回の発見 (subnets 暗黙定) の波及確認。chain の swap(eigrp-ospf) モードの
`l3_subnets_missing` は「BGP→OSPF2 再配送に subnets が無い」故障で、
同じ理由で**故障として成立していない可能性**がある (当時の実機検証は
スイープの再配布再スキャン窓を拾っただけかもしれない)。
- 手順: swap モード seed を 1 つ生成 → 実機で当該故障のみ注入 → 90 秒以上
  待って採点 → 成立しないなら redistribute 全欠落系へ差替え (今回と同じ手筋)。

## BL-020 3重故障 seed の実機1サイクル（gen_mpls_ts --faults 3）

運用ルール「新 seed は出題前に実機1サイクル」の適用。単体故障は 14 種全て
検証済みだが、3 層同時 (下位が上位を隠す連鎖) の組合せは未検証。
- seed 例: 7200 (L1 area + L5 routemap_strict + L2 ldp_missing, decoy 2)。
- 確認点: 修理順が下→上でないと切り分け困難なこと / fix.json 一括投入で
  100 点に戻ること / チケット症状文が過剰に答えを割らないこと。

## BL-021 小粒バリエーション（優先低・順不同）

- **LDP MD5 認証**: 02 変種 or gen 故障 (`mpls ldp neighbor <ip> password` 片側)。
- **01/02 の params 化**: LAN オクテット・RD/RT 値・AS を variant で量産
  (gen_params.py 方式)。
- **MSS の効果ベース採点**: CE 間で `telnet <ip> /source-interface` を張り
  `show tcp brief` の MSS を読む案。IOL の telnet 挙動要 PoC。
  現状は config 存在チェックで妥協中。
- **遠期 (基礎逸脱のため保留)**: Inter-AS Option A/B, CSC, 6PE/6VPE, sham-link。
