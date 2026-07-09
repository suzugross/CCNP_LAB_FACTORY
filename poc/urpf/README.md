# uRPF 実効性 PoC (BL-027) — 結果 (2026-07-09)

ENARSI-URPF-01（URPF-01.design.md）の Phase 0。IOL 上で uRPF strict/loose が
**実際に効くか・採点信号が取れるか**を実機測定。**全項目成立 → 設計は実装可**。
ただしトポロジ設計に机上版からの重要修正が2点ある（下記★）。

## 検証環境（poc-urpf-iol-lab.yaml, iol-xe-17-15-01）

```
        RT01 (edge・被験, Lo0 1.1.1.1)
   e0/0 |         | e0/1
  10.1.12.0/30   10.1.13.0/30
        |         |
  RT02(ISP-A) --- RT03(ISP-B + 顧客ホスト群)
        10.1.23.0/30 (★OSPF 外)
```

- OSPF area 0: 各リンク+Lo0（**RT02-RT03 リンクは意図的に OSPF 外**）
- 顧客B 192.168.100.0/24 = RT03 Lo1 が実体保持（**OSPF 未広告**）。広告は
  RT02 の `ip route 192.168.100.0 ... 10.1.23.2` + `redistribute static subnets` のみ
  → RT01 の経路は e0/0 向き・実トラフィックは e0/1 着信 = **非対称**
- 顧客C 192.168.201.0/24 = RT03 Lo3（OSPF 広告・対称）
- スプーフ源: RT03 Lo2 203.0.113.1（完全未広告）/ RT02 Lo2 192.168.201.99
  （実体は顧客C側 → e0/0 着信で RPF IF 不一致）

## ★トポロジ設計の修正2点（机上設計からの変更・実装時必須）

1. **`ip ospf cost 100` 方式は机上却下**: RT02 の対RT01 出力コストを上げると
   RT02 発の「全」トラフィック（対称であるべき 2.2.2.2 発も）が RT03 経由になり、
   strict を置く e0/0 に着信が無くなる。→ 「デュアルホーム顧客の出口非対称」
   方式（プレフィックス単位の非対称）に変更した。
2. **OSPF forwarding address (FA) 罠を実機で踏んだ**: static の次ホップ IF
   (10.1.23.0/30) が OSPF 有効だと Type-5 LSA に FA=10.1.23.2 が立ち、FA への
   経路が ECMP（両IF）→ **E2 経路が両IF ECMP になり非対称が消える**
   （ECMP だと strict でも RPF 一致＝罠が不成立）。
   → RT02-RT03 リンクを OSPF から外すと FA=0.0.0.0 になり ASBR 経由の
   e0/0 単一路に収束。**実装時はこの網羅（FA 条件）を initial に焼き込むこと**。
   ※この FA 挙動自体が将来の OSPF TS 問ネタになる（BACKLOG 候補）。

## 測定結果マトリクス

5フロー（宛先は全て RT01 自身の 1.1.1.1）× 3状態。数値は ping 成功率と
RT01 の per-IF `verification drops` 増分（repeat 10 に対して）。

| フロー | 着信IF | uRPFなし | 両IF strict（想定誤答） | e0/0=strict, e0/1=loose（模範） |
|--------|--------|----------|------------------------|--------------------------------|
| RT02発 src 2.2.2.2（対称） | e0/0 | 100% | 100% | 100% |
| RT03発 src 3.3.3.3（対称） | e0/1 | 100% | 100% | 100% |
| RT03発 src 192.168.100.1（★正規・非対称） | e0/1 | 100% | **0%・drops+10** | **100%（suppressed+10）** |
| RT03発 src 203.0.113.1（完全スプーフ） | e0/1 | **0%**(反射経路なし) | 0%・drops+10 | 0%・**drops+10** |
| RT02発 src 192.168.201.99（RPF IF不一致スプーフ） | e0/0 | **0%**(応答が迷子) | 0%・drops+10 | 0%・**drops+10** |

- **設計どおりの完全成立**: strict 過剰→正規非対称断（罠が機能）、loose で復旧、
  スプーフは模範状態でも両IFで落ち続ける。
- ★design.md の最重要知見の実証: スプーフ2フローは **uRPF なしでも 0%**
  （echo-reply が戻れない）。ping 成否での「ドロップ採点」は偽陽性確定
  → **採点信号は verification drops カウンタ一択**。

## 個別確認事項

| # | 項目 | 結果 |
|---|------|------|
| 1 | `ip verify unicast source reachable-via rx / any` 受理 | ✅（CEF 既定有効） |
| 2 | `allow-default` オプション | ✅ 受理（allow-default 変種に使える） |
| 3 | ACL 例外オプション | ⚠️ **番号ACLのみ**（`rx 10` は入るが `rx RPF-EXEMPT` は Invalid input。ACL変種は番号ACL前提で設計） |
| 4 | **自宛(receive path) ICMP への実効** | ✅ **効く**（PoC 最重要項目。1.1.1.1 宛 ping が入力IFで drop・カウンタ 1:1 増分）→ 透過トラフィック用の RT04 追加は不要 |
| 5 | per-IF 統計の書式 | `IP verify source reachable-via RX\|ANY` ＋ `N verification drops` / `N suppressed verification drops` / `N verification drop-rate` |
| 6 | suppressed の意味 | loose 通過した「RPF IF 不一致」パケットが計上される（strict なら drop だったもの）。採点 regex `[1-9]\d* verification drops` は数字直前置なので suppressed 行に誤マッチしない（安全確認済） |
| 7 | カウンタのクリア | ✅ `clear counters <IF>` で 0 に戻る（確認プロンプトあり）。ただし採点は「非0」型なのでクリア不要でも成立 |
| 8 | Genie `show ip interface` | パース自体は成功するが **uRPF 行は非構造化**（verification/RPF キーなし）→ 構成チェックも効果チェックも **raw regex で確定** |
| 9 | `show ip traffic` の集計 | `N unicast RPF` が全IF合計として増分（補助信号に使える） |

## 採点チェック実装への確定事項

- 構成: `show ip interface Ethernet0/x`（または `show run interface`）に raw regex
  - strict: `reachable-via RX` / loose許容: `reachable-via (RX|ANY)`
- 効果(ドロップ): 発射→ `show ip interface Ethernet0/x` に
  raw regex `[1-9]\d* verification drops`（2試行収束パターン・QoS 規約準拠）
- 効果(正規維持): RT03発 `ping 1.1.1.1 source 192.168.100.1` の Success 100%
  raw regex（strict 過剰の検出。これが 25点の主戦チェック）
- 得点分布（design.md 想定を実機で裏取り）: 未解答=対称疎通のみ /
  両strict=非対称正規断で減点 / 両loose=e0/0 strict構成+strict実証で減点 / 模範=100

## 再現手順

1. リース: `python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-URPF --nodes RT01,RT02,RT03`
   （YAML は .11-.13 決め打ちなので、異なる IP が出たら YAML 側を合わせる）
2. 投入: virl2_client で `import_lab(poc-urpf-iol-lab.yaml)` → `lab.start(wait=True)`
   → SSH 開通まで約2分
3. フロー実行: 上記マトリクスの 5 ping（全て `repeat 10`・宛先 1.1.1.1）
4. 撤収: stop/wipe/remove → `mgmt_alloc.py release --repo . --problem POC-URPF`
