# MPLS L3VPN シリーズ — 拡張設計メモ

現状 (2026-07-08 時点・すべて実機検証済):
- **ENARSI-MPLS-L3VPN-01**: 基礎構築 (7台, マルチカスタマー重複prefix, PE-CE static)
- **ENARSI-MPLS-L3VPN-02**: 応用 (PE-CE OSPF 化 + route-map 広告制御 + MSS 1452)
- **gen_mpls_ts.py**: 12台 TS 生成器 (3PE×Pリング×2顧客3サイト, 故障14種+decoy2種)

土台になっている知見 (memory: ccnp-mpls-l3vpn-labs):
- iol-xe 17.15 は redistribute の subnets 暗黙定 / `no redistribute ospf N route-map X`
  はオプションだけ外れる / VRF付きOSPF の parents は `router ospf N vrf X` まで /
  VPNv4 ネイバーは Genie 不可→raw / RD は decoy になり得るため採点で断言しない。

以下、拡張候補の設計詳細。番号は BACKLOG.md の BL-ID に対応。

---

## BL-015 PE-CE eBGP 化（gen `--pece ebgp` 軸 + 応用問 03）

手順書「次に試す実験メニュー」3 の残り半分。ユーザ学習手順書のレイヤ L5 を eBGP に差替。

- CE を私設 AS (例 65101〜65106, サイト毎) にして PE と vrf 内 eBGP。
  `address-family ipv4 vrf X / neighbor <ce> remote-as 651xx / activate`。
  再配布が不要になる (eBGP 経路は直接 VPNv4 化) = 02 との対比が学習核心。
- **同一顧客の全サイトを同一 AS にする変種**で as-override / allowas-in を出題
  (ENARSI 頻出)。既定は サイト毎 AS で基礎に留める。
- 広告制御は route-map out (PE→VPNv4 は再配布でなくなるので prefix-list を
  neighbor in に付ける設計へ変更) — 10.99 遮断の仕様は継承。
- 故障候補: remote-as 誤り / activate 忘れ / as-override 欠落 (同一AS変種) /
  neighbor in filter 過剰。
- 手を付ける順: ENARSI-MPLS-L3VPN-03 (手組み・実機100点) → gen へ軸移植。

## BL-016 RT 非対称ハブ&スポーク

手順書メニュー 4。export/import の独立性が学習核心。

- 7台 (01 のトポロジ流用) で CUST_A のみ: hub site が export 65000:100 /
  import 65000:101、spoke が export 65000:101 / import 65000:100。
  spoke↔spoke は hub 経由でしか通れない (直接 import しない)。
- spoke 間直接疎通の「不在」を採点する: spoke PE の VRF に対向 spoke LAN が
  **無い**こと + E2E は hub 経由で成立 (traceroute で hub CE 経由を raw 確認)。
- 注意: hub CE で spoke→spoke を折り返すには hub CE 側に両 spoke 経路が要る
  → hub PE の import を 65000:101 全取り + hub CE との PE-CE で再広告。
  ここが「1 VRF では折返し不可 (同一IFで in/out)」の古典論点 —
  half-duplex VRF (2 VRF 構成) まで踏み込むか、Lo を 2 本持つ簡易折返しで
  基礎に留めるかは PoC で決める。★要実機 PoC (IOL での折返し挙動)。

## BL-017 意図的 RT 混線 TS（l4_rt_cross_import 故障の追加）

手順書メニュー 2。gen_mpls_ts 初版で見送った故障。

- 見送り理由: 重複 prefix 設計では「B が A の RT を import」しても同一 prefix の
  best path 選択次第で症状が出ない/不安定 (非決定的)。
- 設計案: 混線検出を prefix でなく **PE-CE リンク (192.168.x/30, 顧客毎に非重複)**
  で行う。redistribute connected を base に追加すれば、A の RT を import した
  B の VRF に A の 192.168.x/30 が決定的に現れる → `not in table` 反転チェックで
  採点可能。ただし base への redistribute connected 追加は
  01/02/既存 seed の VPNv4 経路集合を変える → **gen のバージョン軸として追加**
  (`--base v2`) し、既存 seed の再現性を壊さないこと。
- 症状: 「顧客から『他社の経路が見える』」+ B の E2E が経路奪合いで断続。

## BL-018 RR 導入軸（gen `--ibgp rr`）

チェーンTS の rr/fullmesh 軸の MPLS 版。VPNv4 RR。

- 案: 専用 RR ノード RT13 を P1/P2 に接続 (13台, 20上限内・IOL slot 3 以内に
  収まるか配線設計要)。または P1 を RR 兼務 (P の BGP フリー原則を崩すため
  task の設計仕様も変える)。専用ノード案を推す。
- PE は RR とだけ iBGP (フルメッシュ廃止)。故障候補: route-reflector-client
  欠落 / RR の vpnv4 activate 忘れ / cluster-id 二重化。
- チェーンTS の教訓 (client 旗 1 つ外しても壊れない) は VPNv4 でも同様のはず
  → victim 選定は要実機確認。

## BL-019 gen_chain_ts swap モード l3_subnets_missing の再検証

今回の発見 (subnets 暗黙定) の波及確認。chain の swap(eigrp-ospf) モードの
`l3_subnets_missing` は「BGP→OSPF2 再配送に subnets が無い」故障で、
同じ理由で**故障として成立していない可能性**がある (当時の実機検証は
スイープの再配布再スキャン窓を拾っただけかもしれない)。
- 手順: swap モード seed を 1 つ生成 → 実機で当該故障のみ注入 → 90 秒以上
  待って採点 → 成立しないなら redistribute 全欠落系へ差替え (今回と同じ手筋)。

## BL-020 3重故障 seed の実機1サイクル（gen_mpls_ts --faults 3）

運用ルール「新 seed は出題前に実機1サイクル」の適用。単体故障は 14 種全て
検証済みだが、3 層同時 (下位が上位を隠す連鎖) の組合せは未検証。
- seed 例: 7200 (L1 area + L5 routemap_strict + L2 ldp_missing, decoy 2)。
- 確認点: 修理順が下→上でないと切り分け困難なこと / fix.json 一括投入で
  100 点に戻ること / チケット症状文が過剰に答えを割らないこと。

## BL-021 小粒バリエーション（優先低・順不同）

- **LDP MD5 認証**: 02 変種 or gen 故障 (`mpls ldp neighbor <ip> password` 片側)。
- **01/02 の params 化**: LAN オクテット・RD/RT 値・AS を variant で量産
  (gen_params.py 方式)。
- **MSS の効果ベース採点**: CE 間で `telnet <ip> /source-interface` を張り
  `show tcp brief` の MSS を読む案。IOL の telnet 挙動要 PoC。
  現状は config 存在チェックで妥協中。
- **遠期 (基礎逸脱のため保留)**: Inter-AS Option A/B, CSC, 6PE/6VPE, sham-link。
