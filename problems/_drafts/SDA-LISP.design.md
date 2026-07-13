# SD-Access（LISP / VXLAN ファブリック）再現 — 検討メモ

2026-07-13 検討。ユーザ要望「SD-Access のなかの LISP や VXLAN などの再現が可能か、
教育的に適したものか」への調査結果と、実装候補の設計。

---

## 1. 結論（要約）

- **DNA Center（Catalyst Center）を含むフル SD-Access は再現不可**。
  オーケストレータが専用アプライアンス級（32GB+ RAM）＋ CML Personal の
  同時起動 20 ノード上限で成立しない。ISE（ポリシー配布）も同様に不可。
- **中核技術＝ LISP（コントロールプレーン）と VXLAN（データプレーン）を
  "手動 CLI ファブリック" として再現するのは可能**。むしろ DNAC が隠蔽する
  中身を手で書くことで原理が腑に落ちる、教育価値の高いアプローチ。
- **CCNP（ENCOR 350-401）では SD-Access は "describe" レベル**で configure は
  試験範囲外。位置づけは「試験ドリル」ではなく **「原理理解のエンリッチメント
  ラボ」**（本プロジェクトの FGT / SD-WAN / MPLS 系と同じ路線）。

## 2. 構成要素ごとの CML 再現可否

| SD-Access 要素 | 実体 | 再現 | イメージ | 備考 |
|---|---|---|---|---|
| コントロールプレーン | LISP MS/MR・xTR・PxTR | ✅ 容易 | iol-xe / cat8000v / csr1000v | 軽量。ファブリックの心臓部 |
| データプレーン | VXLAN encap | ⚠️ 条件付き | (A)nxosv9300 EVPN-VXLAN / (B)cat9000v 真SDA | (A)=DC寄り軽量 / (B)=BETA＋超重 |
| ポリシープレーン | CTS/SGT (TrustSec) | △ 限定 | IOS-XE 静的SGT | ISE不在→動的分類不可・インラインタグ止まり |
| アンダーレイ | IS-IS/OSPF | ✅ 容易 | 既存資産流用 | gen 系トポロジ生成器が使える |
| ファブリック境界 | Border（LISP↔BGP）+ Fusion | ✅ 可能 | cat8000v | VRF/L3ハンドオフは MPLS-L3VPN 資産と親和 |
| オーケストレーション | DNA Center | ❌ 不可 | — | アプライアンス過大・Personal 外 |

### 重要な制約（メモリ ccnp-cml-env 由来）
- **cat9000v-q200/uadp は BETA ＋ 1台あたり約 16〜18GB RAM**。ホスト RAM 50GB では
  実質 2 台が上限。真の SDA ファブリック（CP+Border+Edge×2）は現実的に組めない。
- **VXLAN-GPO（SD-Access 固有のデータプレーン encap）は cat9k の ASIC 前提**。
  cat8000v/csr/IOL では **LISP コントロールプレーンは完全再現できるが、
  VXLAN データプレーンのファブリックエッジ役は担えない**。
- 存在しない image_definition ID は無言で起動失敗（DEFINED_ON_CORE 差し戻し）。
  cat9000v を使う時はまず 1 台の起動 PoC から。

---

## 2.5 出題形式の方針（★ユーザ要望 2026-07-13）

**採点する「構築問題」ではなく、一緒に手を動かして組んでいく
「ガイド付き教育ラボ」にする**。FGT-SDWAN-01 等の体験型 task.md と同系統:

- Phase を刻んだハンズオン手順書（各ステップに「なぜこう設定するか」の解説）。
- 📋 観察チェックポイント（`show` で状態を確認し、何が起きているか一緒に読む）。
- 🤔 考察ポイント（EID/RLOC 分離の意味、map-cache がいつ埋まるか 等）。
- 受講者は **CML コンソールで直接コマンドを打つ**（[[ccnp-user-solving-via-console]]）。
  こちらは各ステップで解説・確認・詰まったら一緒にデバッグする伴走スタイル。
- 自動採点は「最終疎通が取れているか」の軽い確認に留め、点数競争の主役にしない。
  （0点発射→100点の厳密グレーディングは Tier1 では前面に出さない）

## 3. 推奨アプローチ（2 段構え）

### Tier 1（推奨・まず作る）: Classic LISP ファブリック

SD-Access コントロールプレーンの本質だけを、軽量イメージで再現する。

- **構成（5〜6 台・iol-xe 軽量・20 ノード制約に余裕）**:
  - MS/MR ×1（Map-Server / Map-Resolver 兼務）
  - xTR ×2（RT-A サイト / RT-B サイト = ITR/ETR 兼務のファブリックエッジ相当）
  - PxTR ×1（非 LISP ドメインへの出口 = Border 相当）
  - 外部 RT ×1（非 LISP の到達先 = インターネット/レガシー相当）
  - 各サイトに EID（loopback または stub セグメント）を配置
- **アンダーレイ**: OSPF で RLOC（各ルータの物理/loopback）到達性を確立。
  既存トポロジ生成の loopback + p2p リンク方式を流用。
- **オーバーレイ（LISP）**: xTR で `router lisp` → EID-prefix を database-mapping、
  MS/MR に登録（`ipv4 itr map-resolver` / `ipv4 etr map-server`）。
  MS 側で `site` 定義 + authentication-key。PxTR で `ipv4 proxy-itr` /
  `ipv4 proxy-etr` により非 LISP ドメインとの相互到達。
- **学べること**: EID/RLOC 分離、Map-Register/Map-Request/Map-Reply、
  map-cache の on-demand 学習、PxTR による境界接続。**これがそのまま
  SD-Access の「LISP コントロールプレーンで宛先を解決し、データは
  カプセル化して RLOC 間を飛ぶ」という動作原理**。
- **採点性（明快・自動化容易）**:
  - `show lisp session`（MS/MR とのセッション UP）
  - `show ip lisp map-cache` / `show lisp instance-id N ipv4 map-cache`
  - MS 側 `show lisp site`（EID 登録状態）
  - EID 間 E2E ping（オーバーレイ疎通）＋ traceroute（RLOC 経由の確認）
  - 0 点発射チェック: 未設定時は map-cache 空・EID 間 ping 不通で自然成立
- **PoC で先に確認すべき事項（半日規模）**:
  1. **iol-xe 17.15 で `router lisp` が動くか**（構文・show コマンド対応）。
     動かない場合は cat8000v へ（RAM 増だが 6 台なら収まる）。
  2. MS/MR 兼務・xTR・PxTR の最小構成での Map-Register 成立。
  3. map-cache の on-demand 学習タイミング（採点前の待ち時間）。
  4. PxTR 経由の非 LISP 到達（proxy 動作の指紋採取）。
- **想定難易度**: 3〜4（概念は新しいが設定量は中程度）。
- **出題形式**: 設定仕様書型（MS/MR・xTR・PxTR の役割と EID を与え、
  受講者が LISP を組む）。task 冒頭に「これは SD-Access が内部で使う
  LISP を手で組む学習ラボ。試験は describe レベルだが原理理解に有効」と明示。

### Tier 2（任意・発展）: VXLAN データプレーンを足す

- **選択肢 A: nxosv9300 で BGP EVPN-VXLAN**（DC 寄りだが VXLAN encap の実像）。
  nxosv9300 は導入済み・比較的軽量。SD-Access そのものではないが
  「VXLAN でオーバーレイを張る」体験としては十分。Spine×1 + Leaf×2 の最小形。
- **選択肢 B: cat9000v ×2 で手動 SDA ファブリック**（真正だが BETA ＋ RAM 的に
  2 台限界・不安定リスク大）。→ **実現性 PoC が必須**（まず 1 台起動確認）。
  cat9000v が安定して 2 台起動できるなら、LISP+VXLAN+CTS の手動ファブリックを
  最小規模で試す価値はある。ただし優先度は低（Tier 1 を固めてから）。

---

## 4. 教育的適合性の評価

- **適している**: SD-Access は概念が抽象的で座学では理解しづらい典型。
  **LISP を手で組む体験が「なぜファブリックが動くか」を最も効率よく伝える**。
  本プロジェクトの既存路線（実機で触って原理を掴む）と完全に合致。
- **留意点**: CCNP 試験の直接得点には結びつきにくい（describe レベル）。
  **「試験対策」ではなく「実務・原理理解のエンリッチメント」と明示**して出題する。
- **既存資産との親和**: アンダーレイ（OSPF/loopback）・Border の VRF/L3 ハンドオフは
  MPLS-L3VPN 系の知見がそのまま効く。採点は grade.py の raw + Genie 段で対応可
  （LISP show は Genie パーサ有無を PoC で確認 → 無ければ raw 判定）。

---

## 5. 次アクション

1. （本メモ＋ BACKLOG 記録 = 完了）
2. ~~Tier 1 の LISP 最小ラボ PoC~~ → **✅ 完了（2026-07-13・下記 §6）**
3. Tier 2A（nxosv9300 EVPN-VXLAN）→ **✅ PoC 完了（同上）**。
   Tier 2B（cat9000v 真SDA）は未検証のまま優先度低（Tier1/2A で教育目的は充足）。
4. ~~残 = ガイド付き教育ラボ（§2.5 形式）の task.md 作問＋ラボ生成物の実装~~
   → **✅ 完成（2026-07-13）= [problems/SDA-LISP-01/](../SDA-LISP-01/)**。
   一体型9台（ユーザ決定: 別々に学び終章で概念合流する2部構成）。
   実機フルサイクル済（未解答 0/100 → 模範解答 100/100・中間観察5点一致）。
   運用= `topologies/sda_ops.py build|solve|grade|teardown`。**出題可**。

## 6. PoC 結果（2026-07-13・実機検証済み → [poc/sda-lisp/README.md](../../poc/sda-lisp/README.md)）

- **iol-xe-17-15-01 で `router lisp` 完全動作**（クラシック構文全受理・cat8000v
  フォールバック不要と確定）。Map-Register／map-cache オンデマンド学習／EID間疎通／
  PxTR 経由の非LISP相互到達まで全✅。
- **★罠（作問素材）: PxTR は proxy-itr/proxy-etr だけでは PITR が発火せず戻り方向 0%**。
  指紋= `ITR local RLOC (last resort): NOT FOUND` ＋ `Could not find EID table instance ID 0`。
  対処= `map-cache 172.16.0.0/16 map-request`（★ `ipv4 map-cache` 形は Invalid・
  新構文 or router-lisp 直下の `map-cache`）。
- **nxosv9300（node定義 nxosv9000・RAM 12GB/台・ブート約4.5分）で EVPN-VXLAN が
  day0 焼き込み一発成立**（boot workaround ブロック保持＋追記方式）。iBGP EVPN
  Type-2/3・NVE CP学習・L2VNI 越しホスト間疎通✅（ホストは iol-xe 代用で可）。
- 教育的目玉: 「初回 ping ドロップ→map-cache が埋まって疎通」の観察、
  traceroute でカプセル化により中間ホップが消える様子、負の map-reply
  （`forward-native / Encapsulating to proxy ETR`）。
- PoC ラボ = [poc/sda-lisp/poc-sdalisp-lab.yaml](../../poc/sda-lisp/poc-sdalisp-lab.yaml)
  （9台: LISP 5台 iol-xe ＋ VXLAN 2台 nxosv9300 ＋ホスト2台。撤収済・再構築可）。
