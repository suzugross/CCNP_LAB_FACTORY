# ENCOR-QOS-CLASS-01 模範解答

## 解法の考え方

MQC (Modular QoS CLI) の基本 3 点セットをここで習得する:

1. **class-map** — 「どのトラフィックか」を定義（今回は ACL でポート/プロトコル分類）
2. **policy-map** — 「そのクラスに何をするか」（今回は `set dscp`）
3. **service-policy** — 「どのインターフェイスのどの向きに適用するか」

信頼境界の原則: マーキングは**トラフィックの入口（端末に最も近い場所）の入力方向**で
行う。今回は RT01 E0/0 input。ここより内側では各機器はマーキングを信頼して使うだけ。

## 設定 (RT01)

```
ip access-list extended ACL-VOICE
 permit udp any any eq 5201
ip access-list extended ACL-BACKUP
 permit tcp any any eq 5201
ip access-list extended ACL-MON
 permit icmp any any
!
class-map match-all C-VOICE
 match access-group name ACL-VOICE
class-map match-all C-BACKUP
 match access-group name ACL-BACKUP
class-map match-all C-MON
 match access-group name ACL-MON
!
policy-map MARKING
 class C-VOICE
  set dscp ef
 class C-BACKUP
  set dscp af11
 class C-MON
  set dscp cs2
!
interface Ethernet0/0
 service-policy input MARKING
```

※ 名前は任意。`match access-group name` の代わりに番号付き ACL でも可。
※ UDP/TCP の分類は `match protocol`（NBAR）ではなく ACL を使う
  （IOL では NBAR が使えないため。実務でも ACL 分類は最も基本形）。

## 期待される観測

- RT01 `show policy-map interface Ethernet0/0`:
  各クラスの `Packets marked` が流したトラフィック分だけ増える。
  ICMP を流しても C-VOICE は増えない（分類の排他性）。
- RT02 `show policy-map interface Ethernet0/1 input`:
  実装前は OBS-* が全て 0（端末は無マーキング＝DSCP 0 で届いていた）。
  実装後は OBS-EF / OBS-AF11 / OBS-CS2 がそれぞれ増える
  ＝ **DSCP は IP ヘッダに乗って WAN を越えて保持される**ことの実証。

## 補足（採点後レビュー用）

1. **iperf3 の UDP テストは TCP 制御コネクションも張る**ため、UDP を流すと
   OBS-AF11 (TCP5201) も少し増える。カウンタを読むときはこの分を差し引いて考える。
2. `match-all` と `match-any`: 今回は 1 クラス 1 条件なのでどちらでも動くが、
   複数条件を書くときは AND/OR の違いが効いてくる。
3. 次の POLICE-01 / LLQ-01 では、ここで付けたようなマーキングを**前提**に
   帯域制御を行う。マーキングだけでは何も速くならない（それを体感するのが本問の
   RT02 カウンタ）— 活用は次問から。
4. 実務では信頼境界はアクセススイッチ（`mls qos trust` / `trust device`）で
   作ることが多い。ルータの MQC マーキングはその汎用形。
