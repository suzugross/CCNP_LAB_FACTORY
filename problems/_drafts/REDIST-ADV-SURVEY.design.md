# 再配送系・高度ラボの素材調査メモ (2026-08-22〜23)

**目的**: 既存の再配送系紙面・ラボ問(純粋IGP系)を拡張するための素材調査。
**ユーザ方針(2026-08-23)**: MPLS-VPN系(sham-link/SoO/DN bit)は**後回し**。純粋ルーティングプロトコル路線を優先。

対応BL: BL-137(summary解法軸) / BL-138(恒久振動) / BL-139(タグ防御の限界) / BL-140(MPLS系・後回し)

---

## 候補1: サマリ化解法軸の追加 → BL-137

- 元ネタ: [INE Advanced Route Redistribution Scenario (IEWB-RS Vol.II Lab2 Task 4.11)](https://ine.com/blog/2008-07-19-advanced-route-redistribution-scenario-iewb-rs-v41-vol-ii-lab-2-task-411)(無料記事・全文読解済)
- シナリオ: 外部EIGRP→OSPF→外部EIGRPの還流(AD 170→110→170)でループ。R3-R5がFR(プライマリ)、R4-R5がシリアル(バックアップ)。
- **3解法の比較**が核:
  1. AD微調整 — OSPF側の該当経路をAD 171にして外部EIGRP(170)に負けさせる(最も細粒度)
  2. distribute-list — 還流経路を除外
  3. **サマリ化 — OSPF側で /23 に集約し、詳細な外部EIGRP経路をロンゲストマッチで勝たせる**
- 実装案: `gen_redist_mp_ts --solution` に `summary` を追加(既存= acl/prefix/routemap/distance)。
  「指紋regex+他解法禁止not_regex」の既存機構に乗る。既存4モードと同じE2E手順で検証可。
- 注意: summary解法の指紋= `area range` / `summary-address` の存在＋RIBに集約経路とロンゲストマッチの共存。
  distance系解法との判別は容易だが、prefix-list解法との排他(not_regex)設計に一考。

## 候補2: 恒久振動の観測診断型TS → BL-138

- 元ネタ: [Understanding Route Redistribution (ICNP'07 Best Paper, Franck Le / Geoffrey Xie / Hui Zhang)](https://www.cs.cmu.edu/~4D/papers/rr-icnp07.pdf) §V Scenario 4 (Fig.10)
- **競合条件に依存せず決定論的に**経路がフラップし続ける最小構成:
  - ルータA: 4ルーティングプロセス(インスタンス1〜4)、カスタムAD **80 / 110 / 90 / 80**。A:4への/からの再配送は無し。
  - 隣接B(A:3とB:4を接続)。A:2→A:3再配送 → Bが4へ広告 → A:4(AD80)が勝つ → A:2→A:3再配送停止 → Bの経路消滅 → A:4喪失 → A:2復活 → 一巡(論文の t=2 と t=6 が同一状態)。
  - 論文はCisco 2600 / IOS 12.2 で**実機観測済み**と明記。
- 出題価値: 「show ip route を叩くたびに出口/経路が変わる」盤面=既存9shapeに無い時間軸診断。AD操作世界(BL-118)と親和。
- **リスク(PoC必須)**: ①regex一発の自動採点と振動盤面の相性 ②IOL(17.15)での振動周期・再現性 ③振動を「観測させてから止めさせる」二段構成にするか。
- 論文の他の収穫: アノマリ分類=持続ループ(§III-A, 既存mp-loop/ringでカバー済)/競合振動(§III-B, 再現困難で不向き)/恒久振動(§V)/**再配送設定のループ収束判定はNP困難**(3-SAT帰着, §VI-A → 紙面解説の裏話ネタ)。
- 全文テキスト抽出済みだったがscratchpad(セッション限り)。必要なら上記URLからPDF再取得(公開・無料)。

## 候補3: タグ防御の限界を突く形 → BL-139

- 元ネタ: [On Guidelines for Safe Route Redistributions (INM'07, Le & Xie)](https://www.cs.cmu.edu/~4d/papers/guidelines-inm07.pdf)(無料PDF)
- 主張: ベンダー推奨(タグでドメイン還流を防ぐ)に**従っていてもループ/恒久振動が残る**トポロジが存在する。
  「短いループ(自ドメイン即還流)」はタグで防げるが、3ドメイン以上を経由する「長い還流」は防げない。
- 出題価値: 既存タグ衛生問題(twoborder / mp-loop)の上位互換。「タグは教科書どおり正しく設定されているのにループする」という新症状。
  解法はAD設計またはフィルタ地点の追加=既存 `--solution` 機構と組み合わせ可。
- 作問時は論文の具体トポロジ(3+ドメインのリング様還流)をIOLで実測してから。

## 後回し: MPLS-VPN系PE-CE再配送ループ族 → BL-140

ユーザ方針(2026-08-23)で後回し。素材は豊富なので将来用にリンクのみ:

- OSPF sham-link × backdoor: [networklessons](https://networklessons.com/mpls/mpls-layer-3-vpn-pe-ce-ospf-sham-link) / [netquirks "Routing loop shambles"](https://netquirks.co.uk/2019/10/04/routing-loop-shambles/)(WebFetchは403・ブラウザなら可) / [Cisco公式 PE-CEループ防止](https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/118800-configure-ospf-00.html)
- domain-id / DN bit / capability vrf-lite: [brbccie blog(一気通貫)](http://brbccie.blogspot.com/2012/12/ospf-pe-downward-bit-super-area-0.html) / [costiser.ro DN bit](https://costiser.ro/2013/04/15/ospf-on-pe-ce-links-and-the-understanding-the-don-bit/) / [NX-OS Down-bit Ignore](https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/117588-technote-dnbit-00.html)
- EIGRP PE-CE × SoO × cost community: [ipspace Multihomed EIGRP Sites in MPLS VPN](https://blog.ipspace.net/2008/07/multihomed-eigrp-sites-in-mpls-vpn/) — **BL-070③(EIGRP PE-CE)と合流先**
- ENARSIブループリント上はVPN 20%のカバー率ゼロ(BL-100)を埋める枠。

## 参照素材の入手性まとめ

- **無料**: INEブログ全記事(Part [I](https://blog.ine.com/2008/02/09/understanding-redistribution-part-i)/[II](https://ine.com/blog/2008-02-19-understanding-redistribution-part-ii)/[III](https://blog.ine.com/2008/03/17/understanding-redistribution-part-iii)・Advanced Scenario)、学術論文2本、Cisco TechNote([8606](https://www.cisco.com/c/en/us/support/docs/ip/enhanced-interior-gateway-routing-protocol-eigrp/8606-redist.html)/[49111](https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/49111-route-map-bestp.html))、[Daniels blog](https://lostintransit.se/2012/01/30/route-redistribution-filtering-and-mitigating-loops/)
- **購入要**: Narbik [CCIE EI Foundation](https://www.ciscopress.com/store/ccie-enterprise-infrastructure-foundation-9780137374243)(Cisco Press書籍・$60前後)。内容は上記無料素材+既存生成器で概ね代替可のため優先度低。INEワークブック/ビデオはサブスク要だが、核心はブログで足りる。
- Cisco Live: 再配送専門セッションは**実在せず**(BRKRST-2336/2337/2338はEIGRP/OSPF/IS-IS Deployment)。期待薄と確認済み。
