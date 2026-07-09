# ENARSI-URPF-01 設計メモ — エッジ Anti-Spoofing (uRPF) 導入問

status: **Phase 0 PoC 完了 (2026-07-09)・実装待ち** / BACKLOG: BL-027
PoC 成果物: [poc/urpf/README.md](../../poc/urpf/README.md)（全項目実機成立・IOL 採用確定）

## 狙い

ENARSI 3.0 (ルータセキュリティ) の未着手技術 uRPF を、「strict/loose の使い分け」を
核心に据えた体感型の構築+TS ハイブリッドで出題する。

- 単なる「コマンド2行入れて終わり」を避ける: **非対称ルーティング環境で strict を
  無思慮に入れると正規通信が死ぬ**、という実務そのままの罠を仕込む。
- 受験者の想定動線: 両IFに strict 投入 → 検証フローの一部が断 → drops カウンタと
  経路を突き合わせて非対称に気づく → 該当IFのみ loose に緩める。
- 実機実証済み: strict 過剰→正規非対称 0%、loose で 100% 復旧、スプーフは落ち続ける。

難易度: 4（ヒント控えめ運用 [[ccnp-problem-hint-policy]]。task には strict/loose の
語を出さず「送信元検証は可能な限り厳格に。ただし正規通信の断は重大障害」とだけ書く）

## ★採点設計の最重要知見（実機実証済み）

**「偽装 ping が失敗すること」を ping 成否で採点してはならない。**
経路の無い送信元で ping すると、uRPF が無くても echo-reply が戻れず 100% 失敗する
（PoC 実測: スプーフ2フローとも uRPF なしで 0%）= uRPF 未設定でも PASS してしまう
偽陽性製造機。QoS の「EF単独採点は偽陽性」教訓の uRPF 版。

証拠は2系統に分離する（両方 PoC で信号取得済み）:

1. **ドロップの証拠 = per-IF の `verification drops` カウンタ**（`show ip interface`）。
   発数と 1:1 で増分。未設定なら統計行自体が無い → 偽陽性なし。
   raw regex `[1-9]\d* verification drops`（`suppressed verification drops` 行には
   数字直前置のため誤マッチしない・確認済）。
2. **strict 過剰設定の検出 = 正規非対称フローの ping 成功**（本物の挙動差:
   loose なら 100% / strict なら 0%）。

補足（実証済み）: uRPF は**自宛（receive path）ICMP にも効く**ため、宛先は
RT01 の Lo0 で良い（透過トラフィック用ノード追加は不要）。Genie は
`show ip interface` の uRPF 行を構造化しない → 構成・効果とも raw regex 確定。

## トポロジ（IOL 3台・PoC 実証済み構成）

```
        RT01 (edge・採点対象, Lo0 1.1.1.1)
   e0/0 |         | e0/1
  10.1.12.0/30   10.1.13.0/30
        |         |
  RT02(ISP-A) --- RT03(ISP-B + 顧客ホスト群)
        10.1.23.0/30 (★OSPF 外・下記 FA 罠参照)
```

- OSPF area 0: RT01-RT02 / RT01-RT03 リンク + 各 Lo0。
  **RT02-RT03 リンク (10.1.23.0/30) は OSPF に入れない**（下記★2）。
- **顧客B 192.168.100.0/24（非対称の主役）**: RT03 Lo1 が実体保持・**OSPF 未広告**。
  広告は RT02 の `ip route 192.168.100.0 255.255.255.0 10.1.23.2` +
  `redistribute static subnets` のみ。
  → RT01 の経路は E2 で e0/0 向き、実トラフィックは e0/1 着信 = プレフィックス
  単位の非対称（「デュアルホーム顧客が出口だけ ISP-B を使う」という実務ストーリー）。
- 顧客C 192.168.201.0/24 = RT3 Lo3（OSPF 広告 `ip ospf network point-to-point`・対称）。
- スプーフ源: RT03 Lo2 203.0.113.1/32（完全未広告）/
  RT02 Lo2 192.168.201.99/32（未広告。実体は顧客C側 → e0/0 着信で RPF IF 不一致）。
- RT01 に default route を置かない（allow-default 論点の混入防止。変種ネタとして温存）。

### ★PoC で判明したトポロジ上の落とし穴2点（実装時必須）

1. **`ip ospf cost` による非対称化は不可**（初版設計は机上却下）: リンクコストだと
   その始点発の「全」トラフィックが迂回し、strict 側 IF に着信が無くなる。
   非対称は上記の「プレフィックス単位」方式で作ること。
2. **OSPF forwarding address (FA) 罠**（実機で踏んだ）: static の次ホップ IF が
   OSPF 有効だと Type-5 に FA が立ち、FA への経路が ECMP → E2 経路が両IF ECMP に
   なって非対称が消える（ECMP は RPF 一致扱い＝罠不成立）。RT02-RT03 リンクを
   OSPF 外にして FA=0.0.0.0 に固定する。
   ※この FA 挙動自体が OSPF TS 問の故障ネタ候補（BACKLOG 化検討）。

## 出題ストーリー / 要件（task.md 骨子・ヒント控えめ）

「SOC 監査指摘: エッジ RT01 で送信元検証（anti-spoofing）が未実装。
両アップリンクで有効化せよ。セキュリティポリシー上、検証は可能な限り厳格な
モードとする。ただし下記の正規フロー断は重大障害としてカウントされる。」

正規フロー（task に明記・検証コマンドとして提示）:

1. RT02 発 `ping 1.1.1.1 source 2.2.2.2`（対称・e0/0 着信）
2. RT03 発 `ping 1.1.1.1 source 3.3.3.3`（対称・e0/1 着信）
3. RT03 発 `ping 1.1.1.1 source 192.168.100.1`（★非対称・e0/1 着信）

模範解答:

```
interface Ethernet0/0          ! ISP-A側（対称のみ着信）
 ip verify unicast source reachable-via rx
interface Ethernet0/1          ! ISP-B側（正規非対称が着信）
 ip verify unicast source reachable-via any
```

## 採点設計（100点・2試行収束パターン・全て raw regex）

カウンタ系は QoS 規約と同じ「試行1でトラフィック発生→試行2で判定」。
発射は collect 時に RT02/RT03 から ping（全フロー PoC 実証済み・下表の増分数値つき）。

| # | チェック | 方式 | 点 |
|---|---------|------|----|
| 1 | RT01 e0/0 に strict（`reachable-via RX`） | raw regex (`show ip interface Ethernet0/0`) | 15 |
| 2 | RT01 e0/1 に uRPF 有効（`reachable-via (RX\|ANY)`） | raw regex | 10 |
| 3 | 正規対称フロー疎通（RT02発 src 2.2.2.2 / RT03発 src 3.3.3.3 成功）＝チーズ対策 | ios ping raw | 10 |
| 4 | ★正規非対称フロー疎通（RT03発 src 192.168.100.1 成功）= strict過剰の検出 | ios ping raw | 25 |
| 5 | 完全スプーフのドロップ実証: RT03発 src 203.0.113.1 発射後、e0/1 の `verification drops` 非0 | raw regex `[1-9]\d* verification drops` | 20 |
| 6 | strict 実証: RT02発 src 192.168.201.99（実体は e0/1 側）発射後、e0/0 の drops 非0 = e0/0 が loose だと 0 のまま | 同上 | 20 |

- #5 は mode 不問の「e0/1 に uRPF が効いている」挙動証拠。#2（構成）とペアで成立
  （負の要件単独採点はしない教訓の順守）。
- #6 が e0/0 の strict/loose を挙動で分離（loose は suppressed に計上され drops は 0）。
- 想定得点分布（PoC の実測挙動から裏取り済み）: 未解答 10点（#3のみ）/
  両IF strict 65点（#4断）/ 両IF loose 65点（#1,#6落ち）/ 模範解答 100点。
- カウンタは `clear counters` でリセット可（確認済）だが「非0」型なのでクリア不要。

## Phase 0 PoC 結果（全項目 ✅・詳細は poc/urpf/README.md）

1. ✅ `rx / any / allow-default` 受理（CEF 既定有効）。
   ⚠️ ACL 例外は**番号ACLのみ**受理（named は Invalid input）→ ACL変種は番号ACL前提
2. ✅ per-IF 統計書式確認（verification drops / suppressed / drop-rate の3行）
3. ✅ 自宛 ICMP に実効（最重要・カウンタ 1:1 増分）→ RT04 不要
4. ✅ 非対称の再現と strict断/loose復旧（上記修正2点込みで成立）
5. ✅ Genie は uRPF 行を非構造化 → raw regex 確定
6. ✅ `clear counters` でリセット可・「非0」設計なら不要

## 変種・拡張（BACKLOG 候補・実装は本体完成後）

- **acl 変種（難4-5）**: `reachable-via rx <番号ACL>` で非対称プレフィックスだけ
  例外許可し strict を維持する別解筋（★番号ACL限定に注意）。
- **allow-default 変種**: RT01 に default route を足し、loose+allow-default の意味論を問う。
- **IPv6 uRPF 変種**: `ipv6 verify unicast source reachable-via`（OSPFv3 土台あり。
  IPv6 traffic filter と合体で「IPv6 ルータセキュリティ問」化 → 未着手の IPv6 ACL を回収）。
- **OSPF FA 罠の TS 問**: PoC で踏んだ forwarding address → ECMP 化の挙動を
  故障ネタとして独立出題（gen_ospf_complex_ts への故障追加 or 単問）。
- 生成器化は不要規模（単問 + params 変種で十分）。

## 教訓の引用元

- 負の要件は単独採点しない（[[ccnp-qos-labs]] EF保護偽陽性）→ #5/#6 のカウンタ設計
- カウンタ系は「>0」型のみ・2試行収束（conventions.md QoS効果採点規約）
- ヒント控えめ（[[ccnp-problem-hint-policy]]）→ strict/loose の語を task に出さない
