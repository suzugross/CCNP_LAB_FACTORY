# BGP synchronization 実効性 PoC (BL-059) — 結果 (2026-07-18)

ユーザ発案「BGP 同期をトラブルに取り入れる」の Phase 0。**全項目成立 →
ENARSI-BGP-SYNC-01 として出題化済み（同日・実機フルサイクル済）**。

## 検証環境（poc-bgpsync-iol-lab.yaml, iol-xe-17-15-01 ×5・コンソールのみ）

```
 AS65100        |      AS65000 (トランジット)       |        AS65200
  RT01 ─ eBGP ─ RT02 ─ OSPF ─ RT03 ─ OSPF ─ RT04 ─ eBGP ─ RT05
  Lo1:198.51.100.1/24                                Lo1:203.0.113.1/24
```
- RT02/RT04 = 境界。iBGP over Lo0 + next-hop-self。**day0 で `synchronization` ON**
- RT03 = コア。OSPF のみ・**BGP 非参加**

## 事前 probe（2026-07-18・2ノード使い捨て）

**`synchronization` は iosv 15.9 / iol-xe 17.15 の両方でコマンド受理・running-config 残存**。
IOS-XE 系では削除された認識だったが、IOL は classic 由来の実装を保持していた。

## 検証結果（3ステージとも成立）

### Stage A: sync ON の実効（コマンドは飾りではない＝判定ロジック完全動作）
RT02 `show ip bgp 203.0.113.0`:
```
Paths: (1 available, no best path)
  Not advertised to any peer
    ... valid, internal, not synchronized   ← ★診断の決定打
```
- RIB は `% Network not in table`（インストール抑止）
- eBGP ピア RT01 へ**広告もされない**（広告抑止）→ AS 間全断

### Stage B: `no synchronization` → 非BGP中継ブラックホール顕在化
- ★**`no synchronization` だけでは既存経路のベストパス再計算が走らない**
  （40 秒待っても "no best path" のまま張り付く）→ **`clear ip bgp *`（ハード）必須**。
  BL-057 の「inbound route-map は hard clear で確実反映」と同族の本実機の癖。
- clear 後: 経路伝播（RT01 が AS_PATH `65000 65200` で学習）するが **ping 0%**・
  traceroute は hop1(10.0.12.2=RT02) の先で沈黙 = **RT03 がサイレントドロップ**
  （RT03 `% Network not in table`）。「セッションも BGP テーブルも正常なのに
  データプレーンで死ぬ」古典の transit blackhole。

### Stage C: RT03 の iBGP 参加（full-mesh 化）→ 完全復旧
- RT03 が両顧客網を `B` で学習(via 2.2.2.2 / 4.4.4.4=next-hop-self 済)
- 双方向 ping 100%・traceroute 完走（10.0.12.2→10.0.23.3→10.0.34.4→10.0.45.5）

## 採点設計の知見（本実装 ENARSI-BGP-SYNC-01 に反映）

1. **netmodel の RIB ウォークは再帰 next-hop で中継を素通りする**（RT02 の next-hop
   4.4.4.4 → 直接 RT04 へジャンプ）ため、RT01→RT05 ペアではブラックホールを検出できない。
   → **RT03 発の2ペア（→両顧客網）を到達性ペアに含めて代理検出**する設計。
2. **顧客(RT01/RT05)→AS 内部 Loopback は BGP 非広告のため構造的に到達不能（正常）**
   → reachability_all は全ペアでなく「顧客間相互＋AS 内部発の全ペア」14 組に限定。
3. 実機フルサイクル（最終 grading でコールド再検証込み）: **broken 10 → 部分解
   （sync 除去+clear のみ=ブラックホール状態）54 → 模範解答+clear → 100/100**。
   部分解 54 で「外部視点のチェックは通るのに到達性が落ちる」を正しく捕捉。

## 教材面のメモ

- 2 段構えの追体験設計: 「sync を外す→直った気になる→traceroute で死んでいる」が核。
  **synchronization が何を守っていた機能なのか**を故障として学ぶ。
- 現代の正解は full-mesh / RR（＝本問の解）。発展は MPLS の BGP-free core（L3VPN シリーズへ接続）。
- sync は ENARSI ブループリント外のレガシー → task.md は「2004 年設定の使い回し」という
  移行案件ストーリーで出題（明示的なコマンド名ヒントは出さない・理由欄を読ませる）。
