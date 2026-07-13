# EVPN-VXLAN-01 — 模範解答と考察の答え（出題者用）

模範解答の完全形は `topologies/evpn_ops.py` の SOLVE（実機検証済み）。
ここでは要点と、task.md の 🤔考察の「答え」を伴走用にまとめる。

## 解答の骨子（Phase 順）

1. **Phase 1（RR）**: SPINE=IOS-XE `router bgp 65100` + `address-family l2vpn evpn` で
   3 leaf を `route-reflector-client`・`send-community both`。leaf 側は `feature bgp` +
   RR (10.254.0.254) と l2vpn evpn ピア（send-community / send-community extended）。
   ★IOS-XE RR は RT フィルタ既定で無効化不要（PoC 検証済み）。
2. **Phase 2（L2VNI）**: LEAF1/2 で features 4種 + `nv overlay evpn`、
   vlan100 `vn-segment 10100`、`evpn vni 10100 l2 (rd/rt auto)`、
   `interface nve1 (host-reachability protocol bgp / source-interface lo0 /
   member vni 10100 ingress-replication protocol bgp)`、Eth1/2 access 100。
3. **Phase 3（IRB・意図的失敗込み）**: `feature fabric forwarding` +
   anycast-gateway-mac 0000.2222.3333、vlan500 `vn-segment 50000`、
   `vrf context TENANT-A (vni 50000 / rd auto / rt both auto + rt both auto evpn)`、
   SVI100（両leaf・anycast-gateway）/ SVI200（★LEAF2のみ）/ SVI500（ip forward）、
   BGP `vrf TENANT-A → advertise l2vpn evpn`。
   **是正= `interface nve1 → member vni 50000 associate-vrf`（両leaf）**。
4. **Phase 4（border/Type-5）**: LEAF3 は L2VNI なし。vrf+L3VNI+SVI500+
   Eth1/2 routed(vrf)+静的 198.51.100.0/24→192.168.100.2 +
   `redistribute static route-map RM-EXT`（★NX-OS は route-map 必須）+
   nve1 に `member vni 50000 associate-vrf` のみ。

## ★意図的失敗（Phase 3）の指紋 — 伴走時はここを焦らず読ませる

| 観察 | 未是正時の出力（★実機確認済み） |
|---|---|
| H1→H3 ping | 0%（H2→H3 は LEAF2 ローカル IRB で通る） |
| LEAF1 `show nve vni` | 10100 のみ・**50000 の行が無い** |
| LEAF1 `show bgp l2vpn evpn 172.16.200.13` | **空**（記事が回覧されていない） |
| LEAF2 `show ip arp vrf TENANT-A` | H3 あり（**ローカルは知っている**） |
| LEAF2 `show bgp l2vpn evpn 172.16.200.13` | **空**（★知っているのに記事を書かない） |

★真の因果: associate-vrf が無いと**送信側が MAC+IP Type-2 に L3 の荷札
（ラベル 50000・RT 65100:50000・RMAC）を貼れない＝記事自体を生成しない**。
「届いているのに降りない」ではない点に注意（受信側 RT フィルタ以前の問題）。

是正後: LEAF1 `show bgp l2vpn evpn 172.16.200.13` に
`Received label 10200 50000`・`RT:65100:10200 RT:65100:50000`・`Router MAC:` が現れ、
`show ip route 172.16.200.13 vrf TENANT-A` に
`/32 ... segid: 50000 tunnelid ... encap: VXLAN`（Symmetric IRB の指紋）。
★`show ip route <addr> vrf <v>` の語順に注意（`vrf` が先だと Invalid）。

## 考察の答え（要点）

- **考察0（なぜ spine-leaf）**: leaf 追加時の配線が spine 本数分で済む（フルメッシュは
  leaf 数に比例して爆発）。任意の leaf 間が等距離2ホップ＝ECMP で East-West が伸びる。
- **考察1（PfxRcd 0）**: EVPN の経路は「VNI に紐づく MAC/IP の記事」。VNI を
  作るまで広告すべき NLRI が存在しない。
- **考察2（1発 vs 2発）**: EVPN は Type-2 を**先回り配布**（push）済みなので、
  落ちるのはローカル ARP 解決の1発のみ。LISP は初回パケットが Map-Request の
  トリガ（pull）なので往復待ちで2発。
- **考察3-1（何が足りない）**: NVE に L3VNI が未接続。leaf は「VRF の経路を
  どのトンネルで運ぶか」を `member vni 50000 associate-vrf` で知る。無いと
  **送信側が L3 の荷札（ラベル/RT/RMAC）を貼れず MAC+IP の記事を書かない**
  （電話帳にルーティング記事が存在しない — 上の指紋表参照）。
- **考察3-2（スケール）**: リモートホストは /32 が L3VNI を直接指すため、
  leaf は自分が収容しないサブネットを持つ必要がない。LISP の「EID を IGP に
  入れない」と同じ「トポロジと端末情報の分離」。
- **考察4（border の対比）**: pull 型(PXTR)は「どの宛先で Map-Request を発火するか」の
  トリガ（静的 map-cache）が要る。push 型(Type-5)は配布で完結しトリガ不要。
- **最終考察（端末移動）**: 新 leaf が MAC/IP 学習 → Type-2 更新（MAC mobility
  sequence 付き）→ 全 leaf の転送先が新 VTEP へ。GW は anycast なので端末は無感。

## 採点前の注意

- grade の ping はすべて repeat 10 で初回 ARP ドロップ(1発)を吸収（80%〜で PASS）。
- ★**チェック順序を変えないこと**: P2a（H2→H3）が H3/GW の ARP を温めてから
  P2（H1→H3）が走る設計。H3 はサイレントホストのため、温め無しだと LEAF2 が
  MAC+IP Type-2 を生成せず P2/R2/A2 が落ちる（solve 直後の実機で 80/100 を実測
  → P2a 追加で解消）。教材側は 考察3-3 で silent host 問題として回収済み。
- EXT→H1 は**必ず source Loopback1**（EXT の /30 側を送信元にすると、LEAF1 の
  VRF が 192.168.100.0/30 を知らず戻りが落ちる。/30 を advertise しないのは意図
  — 触れたければ「redistribute direct を足すとどうなる？」の発展問答に使える）。
- NX-OS の `show ip arp suppression-cache` 系は本問スコープ外（TCAM carving が
  必要 — poc/evpn-vxlan/README.md 罠1）。task.md 終章コラムで言及のみ。
