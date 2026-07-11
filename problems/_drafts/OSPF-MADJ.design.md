# ENARSI-OSPF-MADJ-01 設計メモ — OSPF マルチエリア隣接（RFC 5185）

状態: **完了**（BL-028, 2026-07-09）— 問題本体 `problems/ENARSI-OSPF-MADJ-01/` 実機フルサイクル済
（未解答20 / サイレント故障誤答20 / エリア移動チート60 / 模範解答100 収束）/ 起案 2026-07-09
PoC 結果詳細: [poc/ospf-madj/README.md](../../poc/ospf-madj/README.md)

## ねらい

`ip ospf multi-area` の存在理由＝「**ABR はバックボーン経由の Type-3 しか
インターエリア計算に使わない**（RFC 3509）ことによる迂回を、リンクのエリア割当を
変えずに解消する」を体感させる。virtual-link との対比も学習点。

## 本番トポロジ（案B・6台 IOL・難易度4）

```
              area 1              area 0 (低速・cost 100)           area 2
  RT05 ─────── RT01 ────── RT03 ────────── RT04 ────── RT02 ─────── RT06
 (5.5.5.5)      │                                        │         (6.6.6.6)
                └───────────── RT01–RT02 直結 ────────────┘
                        area 100 (高速・cost 10)
                     ※監視系収容・エリア割当変更禁止(ストーリー)
```

- RT01/RT02 = ABR（area 0 + area 100 + 各リーフエリア）
- 初期状態: 全隣接UP・全到達可。ただし RT05↔RT06 は area0 チェーン経由の遠回り
  （5ホップ）。area 100 には両ABRの監視用 Loopback（172.31.100.x/32）を収容し
  「変更禁止」の実在感を出す。
- 課題: RT05↔RT06 の通信を直結リンク経由（3ホップ）に最適化。
- **制約（消去法で解を MADJ に一意化）**: virtual-link 禁止 / 既存IFのエリア割当
  変更禁止 / スタティック・PBR 禁止。
- **正解**: 直結リンク両端を `ip ospf network point-to-point` 化＋
  `ip ospf multi-area 0`（cost 調整は PoC 結果次第で要件化）。
- **仕込み罠（難易度4の源泉・PoCで実挙動確定）**: multi-area は P2P 限定だが、
  IOL 17.15 では broadcast IF でも**エラーなく受容され、syslog も出ず MA0 が
  DOWN のまま**（サイレント故障）。受験者は `show ip ospf interface brief` の
  `MA0 ... DOWN 0/0` から network type に思い至る必要がある。両端
  `ip ospf network point-to-point` 化（area100 の既存隣接を壊さない判断込み）が
  正解の一部。ヒント控えめ方針（[[ccnp-problem-hint-policy]]）。

### アドレス（conventions 準拠）

- Lo0: RTxx → x.x.x.x/32（RT05=5.5.5.5 area1 / RT06=6.6.6.6 area2）
- リンク: RT01-RT02=10.1.12.0/30(area100) / RT01-RT03=10.1.13.0/30,
  RT03-RT04=10.1.34.0/30, RT02-RT04=10.1.24.0/30(以上 area0 cost100) /
  RT01-RT05=10.1.15.0/30(area1) / RT02-RT06=10.1.26.0/30(area2)
- area100 監視Lo: RT01=172.31.100.1/32, RT02=172.31.100.2/32

## 採点設計（案）

1. **MADJ シグネチャ**: RT01–RT02 間に同一物理リンク上の2隣接
   （物理IF=area100 / `OSPF_MA0`=area0）が FULL。Genie 構造化可否は PoC-D で確認。
2. **経路最適性**: RT01 の 6.6.6.6/32 next-hop=10.1.12.2（O IA）＋
   RT05→RT06 traceroute 3ホップ以内（**往復両方向**）。
3. **負の要件はペア採点**（QoS教訓）: 「area100 隣接維持 AND 直結経由」
   「virtual-link 不在 AND 最適経路」のように効果チェックと統合。
4. フェイルオーバ（直結断→area0 チェーンへ自動切替）は verify_failover 方式
   （grade 外）または変種で。BFD 変種軸（[[ccnp-bfd-variants]]）も後付け可能。

## Phase 0 PoC（4台・poc/ospf-madj/）— 完了・全項目成立 (2026-07-09)

結果サマリ（詳細は poc/ospf-madj/README.md）:
- A ✅ IOL 受容（オプション= cost/delay のみ・認証オプション無し）
- B ⚠️ broadcast ではサイレント故障（エラー/ログ無し・MA0 DOWN）＝想定より良い罠
- C ✅ P2P化で OSPF_MA0 FULL・metric 301→11 で直結へ・area100 無傷・traceroute 1hop
- C2 ✅ cost オプション実効（500→迂回に戻る / 5→metric 6）
- C3 ✅ 直結断→即チェーンへフェイルバック→復旧
- D ⚠️ Genie: `show ip ospf neighbor` は OSPF_MA0 完全構造化可 /
  `show ip ospf interface brief` は MA0 行を黙って落とす→raw regex 代替
- E 未（netmodel.py の MADJ 対応はオフラインで確認。非ブロッカー）
- ★day0 の IF description 日本語は IOL で文字化け→本番 initial は英語で

--- 以下は PoC 計画（記録として保持） ---

リーフルータを省き、ABR の Lo0 をリーフエリア所属にして同じ ABR 挙動を再現:

```
RT01(Lo0=1.1.1.1 area1) ──area0 cost100── RT03 ── RT04 ──cost100── RT02(Lo0=2.2.2.2 area2)
        └──────────── 直結 10.1.12.0/30 area100 (cost10) ────────────┘
```

検証項目:
- A: IOL(iol-xe-17-15) が `ip ospf multi-area` を受容するか（★成立しないと企画中止）
- B: broadcast IF での投入エラー（P2P 限定制約）の実メッセージ確認
- C: MADJ 形成（OSPF_MA0）→ RT01 の 2.2.2.2/32 が RT03経由→直結へ切替わること
   ＋ area100 隣接・intra-area 経路が無傷なこと
- C2: `ip ospf multi-area 0 cost <n>` の効きとオプション体系（`?` で列挙記録）
- C3: 直結 shutdown → area0 チェーンへフェイルバック
- D: Genie パーサが `show ip ospf neighbor` / `show ip ospf interface brief` の
   OSPF_MA0 を構造化できるか（不可なら raw regex 代替を確定）
- E: netmodel.py が MADJ リンクを扱えるか（PoC 後にオフライン検討。不可でも
   traceroute/next-hop 採点で代替可＝ブロッカーではない）

## リスク / 未確認

- IOL の multi-area 対応（PoC-A）。不可なら IOSv / cat8000v 比較へ。
- MA インタフェースへの認証設定の挙動（変種向け。PoC では `?` 列挙まで）。
- Genie OSPF_MA0（PoC-D）。VPNv4 ネイバー同様 raw フォールバック覚悟。

## 発展（別BL候補）

- TS 変種: 片側 multi-area 欠落 / 片側のみ P2P / MA cost 誤設定で迂回のまま、等。
- 案C: 直結リンク2本＋MA cost で主従設計（変種 or 生成器軸）。
