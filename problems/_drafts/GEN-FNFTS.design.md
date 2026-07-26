# GEN-FNFTS 設計メモ — Flexible NetFlow TS 生成器 (BL-065)

2026-07-25 起案・即実装。ENARSI シミュレーションで FNF が頻出との観測に対し、
既設 ENCOR-FNF-01（構築問・難2）には TS 形式が無く、exporter の source/version が
未採点という2つの空白を埋める。

## 形式

「監視標準仕様書 (Flow Monitoring Standard) が提示され、昨日導入された RT02 の FNF が
仕様どおり動かない」という**仕様書突き合わせ型 TS**。ENARSI シムの実際の出方
（仕様提示→設定/修正）に寄せる。トポロジは ENCOR-FNF-01 の3台一直線を値ランダム化して流用:

```
RT01(送信元) ─ seg12/30 ─ RT02(FNF・被疑) ─ seg23/30 ─ RT03(宛先)   OSPF area0 既設
RT02: Et0/0 = RT01向け(仕様の監視点: ingress) / Et0/1 = RT03向け
```

## 仕様書（採点固定値・seed でランダム化）

- flow record `REC-<TAG>`: match = ipv4 src/dst addr + ipv4 protocol + L4 src/dst port、
  collect = counter bytes/packets
- flow exporter `EXP-<TAG>`: destination `<collector>`、**source Loopback0**、
  transport udp `<port>`、**export-protocol `<ver>`**（netflow-v9 / ipfix を seed 抽選）
- flow monitor `MON-<TAG>`: record/exporter を束ねる
- 適用: RT02 の RT01 向け IF **ingress**

## 故障カタログ（レイヤ直交・--faults 2 で別レイヤから複合）

| fault | レイヤ | 難 | 症状チケット |
|---|---|---|---|
| apply_direction_output | apply | 3 | コレクタに逆方向(RT03→RT01)のフローしか出ない |
| apply_wrong_if | apply | 3 | 同上（E0/1 ingress 適用） |
| monitor_not_applied | apply | 3 | フローが一切採れない・cache 空 |
| monitor_no_exporter | monitor | 3 | cache には見えるのにコレクタへ届かない |
| monitor_wrong_record | monitor | 4 | 届くレコードのフィールドが標準と違う（旧 REC-OLD 参照） |
| record_missing_key | record | 4 | 特定フィールド（proto/L4port のどれか）が欠落 |
| exporter_wrong_dest | exporter | 3 | コレクタ未着（宛先 IP 誤り） |
| exporter_wrong_port | exporter | 3 | コレクタ未着（UDP ポート誤り） |
| exporter_wrong_source | exporter | 4 | NMS が「未登録ソースから受信・破棄」警告（source IF 誤り） |
| exporter_wrong_version | exporter | 4 | コレクタが「パース不能バージョン」記録（v9 のまま/仕様 ipfix） |

## 採点（100点）

record match/collect 15・exporter dest/port 10・source 10・version 10・
monitor→record 10・monitor→exporter 10・IF ingress 適用 15・発射 ping 5・
**cache 実効 15 = `show flow monitor <MON> cache format table` の同一行 `src\s+dst` regex**。

★既設 FNF-01 の cache 判定（contains 2連）は**逆向きフローで偽陽性**
（src/dst が別フロー行でもマッチ）→ TS では同一行 regex が必須。
apply_direction_output の検出はこれが効く（cache には戻りフローだけ載る）。

## fix.json の構造方針（IOS の「使用中 record は編集不可」対策）

fix は常に「①現適用点から monitor を外す → ②構造修正 → ③正位置 (E0/0 input) へ適用」
の3段で生成（適用系故障の現在地は fault から計算）。exporter パラメータは
ライブ変更可のはずだが一律この順で安全側に倒す。

## 実機検証結果（2026-07-25 iol-xe 17.15・seed 4102）

- [x] `export-protocol ipfix` **受理**（表示 `Export protocol: IPFIX (Version 10)`・day0 焼きも通る）
- [x] `show flow exporter` 書式確定: `Destination IP address:` / `Destination Port:` /
      `Source Interface:` / `Export protocol:` 行 → 採点 regex 確定済み
- [x] `cache format table` は **SRC/DST が先頭2列で隣接**（表示は正規順で、record の
      定義順とは無関係。protocol は ports の後に出た）→ 同一行 `src\s+dst` regex 成立
- [x] 方向誤り適用時、cache には**逆向きフローのみ**載る → contains 2連は偽陽性の実証
- IOL は `cache timeout active` 不可（既知）→ 故障カタログ・仕様から除外済み
- エクスポート実配送はコレクタ非実在のため採点しない（config/状態＋cache 実効まで）

### ★fix 機構で踏んだ実機罠3点（スイープ1回目で発見・是正済み）

1. **flow monitor の record は上書き不可**: `record <新>` は
   `% Flow Monitor: Failed to set record: Already there is an existing record configured`
   で拒否 → **`no record` → `record <正>` の2段**が必須。
2. **flow record のフィールド編集は IF から外しても解錠されない**:
   参照する monitor が存在する限り `% Flow Record: Failed to field add: Object is in use`
   → **monitor 側 `no record`（参照解除）→ 編集 → `record <正>` で戻す**。
   （detach だけで足りるという通説は 17.15 では不成立）
3. **ios_config は上記 % エラーを握りつぶして changed を返す**（MPLS 問で確立した
   「ios_config 属性神隠し」の FNF 版）。さらに**同一行の detach→attach をひとつの
   ループタスクで流すと attach 側が stale diff で no-op** になる →
   fix_generated.yml に `match: none` パススルーを追加し、本生成器の fix は全エントリ
   無条件投入で発行する。
   exporter のパラメータ（destination/source/udp/export-protocol）はライブ変更可。

## 併せて実施（同 BL）

ENCOR-FNF-01 の task/params/grading に exporter source（既に params 有・未採点）と
export-protocol の要件・採点を追加（v9 既定なので base は netflow-v9 指定で無害、
v2 は ipfix にして差を出す — ipfix の実機確認後に）。
