# OSPF マルチエリア隣接 PoC (BL-028) — 結果 (2026-07-09)

ENARSI-OSPF-MADJ-01（OSPF-MADJ.design.md）の Phase 0。
IOL 上で `ip ospf multi-area`（RFC 5185）が**実効するか**＋採点可否を検証。
**全項目成立 → IOL 採用で本実装へ進める**。

## 検証環境（poc-madj-iol-lab.yaml・4台）

```
RT01(Lo0=1.1.1.1 area1) ─[area0 cost100]─ RT03 ─ RT04 ─[cost100]─ RT02(Lo0=2.2.2.2 area2)
        └────────── 直結 10.1.12.0/30 area100 (cost10) ──────────┘
MGMT: RT01=.14 RT02=.15 RT03=.16 RT04=.17 (mgmt_alloc 台帳リース)
```

本番トポロジ（6台）のリーフルータを省き、ABR の Lo0 をリーフエリア所属にして
同じ ABR 挙動を再現した最小構成。

## 結果マトリクス（IOL iol-xe-17-15-01）

| # | 項目 | 結果 | 詳細 |
|---|------|------|------|
| 前提 | RFC 3509 迂回の再現 | ✅ | RT01→2.2.2.2/32 = **metric 301・O IA・RT03経由**。area100 直結(cost10)は不使用 |
| A | `ip ospf multi-area 0` 受容 | ✅ | config-if で受容。オプションは `cost <1-65535>` / `delay` / `<cr>` のみ（**認証オプション無し**） |
| B | broadcast IF での挙動 | ⚠️**サイレント故障** | エラーも syslog も出ず running-config に入るが、**MA0 は DOWN のまま隣接不形成**。※「P2P限定エラーが出る」という古典ドキュメントの想定と異なる=より意地悪な罠として使える |
| C | P2P 化で MADJ 形成 | ✅ | 両端 `ip ospf network point-to-point` → **OSPF_MA0 が FULL/P2P**。同一物理リンク上に 2隣接（Et0/0=area100 / MA0=area0）。metric **301→11** で直結へ切替。area100 の intra-area 経路・隣接は無傷。traceroute 1ホップ |
| C2 | `multi-area 0 cost N` | ✅ | cost500→遠回り(301)へ戻り / cost5→直結 metric6。方向性あり（設定側の SPF に効く）。`show ip ospf interface brief` の MA0 行 Cost に反映 |
| C3 | フェイルオーバ | ✅ | 直結 shutdown → 即 area0 チェーン(301)へ。no shut → 直結復帰。自IFダウンなので IOL のリンクダウン非伝播問題の影響なし |
| D | Genie パース | ⚠️条件付き | 下記 |

## D. Genie パースの詳細（採点設計に効く）

- `show ip ospf neighbor`: **OSPF_MA0 を完全構造化可** ✅
  `interfaces.OSPF_MA0.neighbors.2.2.2.2.state = "FULL/  -"`（startswith FULL で判定）。
  同一ネイバーIDが Ethernet0/0（area100）と OSPF_MA0（area0）の両方に出るため
  「同一リンク上の2隣接」シグネチャチェックがそのまま書ける。
- `show ip ospf interface brief`: **MA0 行はパーサが黙って落とす** ❌
  （`Unnumbered Et0/0` が IP/Mask の regex に合わずスキップ。SchemaEmptyParserError
  にはならず他IFは正常構造化＝「MA0が無い」ことに気付きにくいので注意）。
  MA0 の存在/Cost/Area を採点したい場合は raw regex
  （例 `MA0\s+1\s+0\s+Unnumbered Et0/0`）で。
- 経路採点は通常の `show ip route`（O IA / next_hop=10.1.12.2）で従来どおり可。

## 出題設計へ反映すべき実機知見

1. **サイレント故障が本問最大の罠**: broadcast のまま multi-area を入れても
   エラーなし・ログなし・MA0 DOWN。受験者は `show ip ospf interface brief` の
   `MA0 ... DOWN 0/0` を見つけて network type に思い至る必要がある。難易度4の根拠。
2. MADJ は **unnumbered の論理IF（MA0）** として生える。IPは物理IF借用。
3. cost 未指定時は物理IFのコストを継承（PoC では 10）。要件で cost 指定させる場合は
   `ip ospf multi-area <area> cost <n>` が正解コマンド。
4. 認証はMA0専用オプションが無い → 認証変種を作る場合は物理IF/エリア認証の継承挙動を
   別途PoC要（未検証）。
5. day0 config の**IF description に日本語を入れると IOL 上で文字化け**する
   （本PoCで確認。動作には無害だが本番 initial では英語にする）。

## 採点チェック雛形（実機出力ベース）

```yaml
# MADJ シグネチャ: area0 の隣接が MA0 上に FULL
- name: "RT01: MADJ (OSPF_MA0) FULL"
  node: RT01
  command: "show ip ospf neighbor"
  parser: "show ip ospf neighbor"
  find: ["interfaces", "OSPF_MA0", "neighbors", "2.2.2.2"]
  match:
    state: {startswith: "FULL"}
# 既存 area100 隣接維持(負の要件ペア側): 物理IF上にも同一ネイバー FULL
- name: "RT01: area100 隣接維持 (Et0/0)"
  find: ["interfaces", "Ethernet0/0", "neighbors", "2.2.2.2"]
  match:
    state: {startswith: "FULL"}
# 経路最適性: O IA が直結 next-hop
#   (show ip route 全表 → routes.* で 6.6.6.6/32, next_hop=10.1.12.2)
```

## 再現手順

1. リース: `python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-OSPF-MADJ --nodes RT01,RT02,RT03,RT04`
2. 投入: virl2_client で poc-madj-iol-lab.yaml を import+start（scratchpad/cml_madj.py 相当）
3. 正解投入（両端 E0/0）: `ip ospf network point-to-point` → `ip ospf multi-area 0`
4. 確認: `show ip ospf neighbor`（MA0 FULL）/ `show ip route 2.2.2.2`（metric 11）

## 撤去済み

PoC 完了後にラボ削除・リース解放済み（2026-07-09）。
