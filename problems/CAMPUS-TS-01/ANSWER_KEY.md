# CAMPUS-TS-01 ANSWER KEY（受講者非公開）

全5フォールトを実機で往復検証済み（2026-07-10）。golden=100点、
各フォールト注入時は下記「期待スコア」に落ち、reset で 100 点へ回帰する。

| fault | 期待スコア | 落ちるチェック |
|-------|-----------|----------------|
| trunk_allowed_mismatch | 91 | acc2トランク(5) + cli40リース(4) |
| ospf_mtu_mismatch | 80 | core1隣接(12) + dist1経路(8) |
| dhcp_relay_gap | 95 | dist2 SVI30 helper(5) |
| asa_asymmetric_drop | 79 | dist1経路(8) + HTTP小(5) + big.bin(8) |
| pmtud_blackhole | 92 | big.bin(8) |

---

## F1: trunk_allowed_mismatch（acc2 の allowed vlan から 40 が欠落）

- **症状**: acc2 配下の VLAN40 (cli40) だけ DHCP 不可・GW 不達。同じ acc2 の
  VLAN30 (cli30) は正常 ＝「スイッチ全体ではなく特定 VLAN だけ」が核心
- **疑う順序**: cli40 のリンク → acc2 のアクセスポート → **acc2 のトランク** →
  dist の SVI40/HSRP（正常なので上位は無実）
- **確定コマンド**: `show interfaces trunk`（acc2）
  - fault 中: allowed に `10,20,30`（40 が無い）/ golden: `10,20,30,40`
- **修正**: `interface range Gi0/0-1` → `switchport trunk allowed vlan add 40`
  （`add` を忘れて `switchport trunk allowed vlan 40` と上書きすると
  他 VLAN が全部落ちる — 定番の二次災害まで解説すると良い）
- **再検証**: cli40 で `sudo networkctl reconfigure ens3` → 10.10.40.x 取得

## F2: ospf_mtu_mismatch（core1 Gi0/1 の ip mtu 1300 vs dist1 1400）

- **症状**: 監視に core1-dist1 の経路消失。疎通は冗長（core2 経由）で生きて
  いるため「なんとなく動く」。実測: 全クライアント通信は green のまま
- **確定コマンド**: `show ip ospf neighbor`（core1）
  - fault 中: `3.3.3.3 ... EXSTART/-`（他 3 隣接は FULL）
  - `show ip interface Gi0/1 | include MTU` を両端で比較（1300 vs 1400）
- **修正**: core1 `interface Gi0/1` → `ip mtu 1400`
- **教材ポイント**: EXSTART/EXCHANGE 固着 = MTU 不一致の代表シグネチャ。
  DBD 交換で大きい方が詰まる。隣接は Hello では張れてしまう

## F3: dhcp_relay_gap（dist2 SVI30 の helper 欠落）

- **症状**: 「普段は取れるのに、dist1 メンテの晩だけ Guest 全滅」という不定期系
- **★実機で確定した重要知見**: DHCP リレーは **HSRP の Active/Standby と無関係**。
  helper を持つ全 SVI がブロードキャストを中継するため、HSRP を dist2 に
  振っただけでは発症しない（standby の dist1 が中継し続ける）。
  発症条件は「dist1 の SVI30 が down」（実測: shutdown で cli30 が
  NO-IPV4-ADDRESS → no shut で 10.10.30.100 回復）
- **確定コマンド**: `show run interface Vlan30` を dist1/dist2 で比較
- **修正**: dist2 `interface Vlan30` → `ip helper-address 10.20.0.10`
- **採点**: 片肺状態そのものは通常時に機能するため、config 整合チェック(5点)で検出

## F4: asa_asymmetric_drop（core2 予備線の開通ミス→非対称×ステートフル）

- **症状**: ping/DNS は 100% 正常なのに TCP（Web/共有）だけタイムアウト。
  実測: ICMP・DNS(UDP) チェック PASS のまま HTTP 小・大転送だけ FAIL
- **メカニズム**: 往路 = クライアント→core2 予備線→svr1（ASA を通らない）/
  復路 = svr1 の GW が asa1 のため ASA 経由。ASA は SYN を見ていないので
  SYN-ACK を「最初のパケットが SYN でない」として破棄
- **確定コマンド**:
  - `show ip route 10.20.0.0`（dist/core で next-hop が core2 系に変わる）
  - asa1 `show asp drop frame tcp-not-syn` — 実測: curl 1 回で **カウンタ 7 増加**
    （SYN-ACK 再送が全て落ちている動かぬ証拠）
  - asa1 `show conn` に該当 TCP が現れない
- **修正**: core2 `interface Gi0/3` → `shutdown`（運用ルールの予備線閉塞に戻す。
  `ip ospf cost 1000` への復旧も併せて完全解）
- **教材ポイント**: 「ping は通る＝経路正常」ではない。ステートフル FW を挟む
  設計では往復対称性が要件になる

## F5: pmtud_blackhole（MSS クランプ撤去＋ICMP unreachable 抑止）

- **症状**: トップページ(小)は開くのにダウンロード(大)だけ必ず止まる。
  実測: ping・DNS・HTTP 小 PASS / big.bin(200KB) だけ FAIL
- **メカニズム**: core1-dist 間が MTU1400 区間。golden は core1 Gi0/1・Gi0/2 の
  `ip tcp adjust-mss 1360` で TCP を 1400 以内にクランプ。fault はクランプ撤去
  ＋ **Gi0/3（サーバ側 ingress）に `no ip unreachables`** → svr1 の 1500B DF
  パケットが core1 で落ち、frag-needed も返らない = PMTUD 黒穴
- **確定コマンド**:
  - svr1 から `ping -M do -s 1400 10.10.10.X`（1372 は通る/1400 は応答無し）
  - core1 `show run interface`（adjust-mss 無し・no ip unreachables）
- **★切り分けの罠（Phase 0 実証）**: IOS の ICMP unreachable 抑止は
  「パケットを**受信した** IF」の設定で決まる。egress 側だけ見ると見逃す
- **修正（どちらでも可・両方が模範）**:
  1. core1 Gi0/1・Gi0/2 に `ip tcp adjust-mss 1360`（クランプ復活）
  2. core1 Gi0/3 に `ip unreachables`（PMTUD を機能させる）
- **教材ポイント**: 「セキュリティ強化で ICMP を止める」が PMTUD を殺す実運用事故の再現

---

## 運用メモ

- 注入/解除は該当ノードのみ day0 差し替え＋再起動（約4分）。fault→fault の
  直接遷移も可（前 fault の対象ノードは自動で golden に戻る）
- 注入後は OSPF/HSRP 収束に 1〜2 分。クライアントの DHCP は自然回復するが、
  即時確認は `sudo networkctl reconfigure ens3`
- 採点実測値: golden 100 / F1 91 / F2 80 / F3 95 / F4 79 / F5 92（2026-07-10）
