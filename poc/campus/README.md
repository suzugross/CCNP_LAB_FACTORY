# キャンパスTS Phase 0 プローブ (BL-040) — 結果 (2026-07-10)

超大作3層キャンパスLAN障害演習ラボ（CAMPUS-TS.design.md）の golden 実装前に、
「成立が疑わしい要素」を最小構成で実機確定した。**全プローブ成功 → golden 実装へ進める**。

## 検証環境（poc-campus-phase0-lab.yaml・3台・console専用・MGMT/リース無し）

```
DIST1(iosvl2) --10.254.1.0/30-- CORE1(iosv) --10.254.2.0/30-- FW01(asav)
 Lo0 3.3.3.3    ルーテッドポート p2p              outside      inside 10.20.0.0/24
                                                              (DIST1 Gi1/0 をダミーL2に)
OSPF area0 全域 / FW01 は BL-038 方式の console bootstrap（day0不発のため）
```

## プローブ結果（全✅）

| # | 検証項目 | 結果 |
|---|----------|------|
| P1 | **IOSvL2 ルーテッドポートで OSPF p2p 隣接**（`no switchport`+`ip ospf network point-to-point`） | ✅ FULL/- 安定。指示書が懸念した「IOSvL2 OSPF の癖」は routed port + p2p 構成では未発現 |
| P2 | **ASAv の OSPF 参加**（unlicensed） | ✅ FULL/BDR。`router ospf`+`network <net> <mask> area 0` 構文。inside 網 10.20.0.0/24 が DIST1 の RIB に O で載り end-to-end ping 100% |
| P3 | **F2: MTU 不一致で EXSTART 固着** | ✅ CORE1 側 `ip mtu 1400` で当該隣接のみ `EXSTART/-` 固着・他隣接は FULL のまま（指示書の症状を完全再現）。`no ip mtu` で自然復旧 |
| P4 | **F5: PMTUD ブラックホール**のメカニクス | ✅ 2段階で確定（下記） |
| P5 | golden⇔fault 往復の復旧性 | ✅ 全戻しで全隣接 FULL・DF 1400 ping 100% に復帰 |

## ★実機知見（fault カタログ設計に直結）

1. **F2/F5 の MTU 注入ポイント**: IOSvL2 は物理 `mtu` コマンドを**受け付けない**
   （`% Invalid input`）。**`ip mtu`（L3 MTU）は iosv/iosvl2 双方で有効** →
   カタログの仕込みは `ip mtu` で統一するのが安全。
2. **F5 の完全な故障レシピ**（2部品構成・両方実証済み）:
   - 部品A = 経路中の egress に `ip mtu 1300`: DF 大パケットは落ち **ICMP
     frag-needed が返る**（ping に `M` 表示）→ この状態は「PMTUD が正しく働く」状態
   - 部品B = **`no ip unreachables` を「ingress 側」IF に投入**すると frag-needed が
     抑止され **無言タイムアウト化**（真のブラックホール）。
     ★**IOS は「パケットを受信した IF」の ip unreachables 設定で抑止判定**する
     （egress 側に入れても M は消えない — 本プローブで実測）。
     出題では「どの IF に no ip unreachables があるか」も切り分けポイントになる
3. ASAv OSPF は BL-038 の bootstrap 方式でそのまま設定可（day0 不発の制約は
   OSPF 有無に関係なし）。`icmp permit any <if>` で自 IF への ping 許可
4. IOSvL2 の `spanning-tree portfast` は day0 で素直に入る。ダミー L2 ポートで
   ASA inside を up にするパターンは有効（本番では実セグメントに置換）
5. コンソール自動化: 初回 ASA は hostname=ciscoasa のため**プロンプト正規表現は
   ホスト名可変にする**こと（campus_tools.py で対処済み）。IOS プロンプトは
   `#` 後に空白無し・ASA は空白ありの差も吸収済み

## F4（非対称×ステートフル）について

Phase 0 では未実施（コア2台+復路が要るため golden トポロジで実施が効率的）。
メカニズムは OSPF コスト操作のみで既知リスク低。ASA 側シグネチャ
（`show conn`・`show asp drop`）は BL-038 で採取経路確立済み。

## 成果物

- [poc-campus-phase0-lab.yaml](poc-campus-phase0-lab.yaml) — 3台プローブトポロジ
  （FW01 config は console bootstrap 用の正準ソースとして yaml に保持）
- [campus_tools.py](campus_tools.py) — up/wait/down/bootstrap/cmd の PoC ツール
  （本実装で provision 統合の下敷きにする）

## 次フェーズ（golden 実装）

1. problems/CAMPUS-TS-01 骨格（10 VM トポロジ yaml・day0 テンプレ・BIND9+ISC DHCP の svr1）
2. ASA bootstrap の provision 統合（BL-039）
3. golden 全 green（grade.py: OSPF full×N / HSRP×4 / STP root×4 / DHCP×4VLAN / TCP / 大転送）
4. F1〜F5 を day0 差し替え+該当ノード再起動方式で 1 つずつ実装・実機往復
