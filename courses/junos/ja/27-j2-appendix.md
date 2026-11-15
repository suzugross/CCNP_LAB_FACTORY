# J2 — 付録

## 1. 評価の順の早見表

1 つのパケットが firewall filter を通る順です。

1. 入ってきたインターフェースの入力フィルタ。
2. 経路表を引く。ほかへ送るなら、出ていくインターフェースの出力フィルタ。自分宛てなら、lo0 の入力フィルタを通って RE へ。
   RE が送るパケットも、出ていくインターフェースの出力フィルタを通る。
3. フィルタを並べていれば、左から 1 つずつ。フィルタの中は term を上から 1 つずつ。
4. term の `from` は、違う種類の条件がすべて当たり(AND)、同じ種類の値はどれか 1 つ当たれば(OR)当たる。
   アドレスの並びは、パケットのアドレスをいちばん長く含むもので決まり、それが `except` なら当たらない。
   `source-address` と `source-prefix-list` は同じ種類(送信元のアドレス)として 1 つの並びにまとまる(宛先も同じ)。
   `except` の行しかない並びは何にも当たらない。
5. 当たった term の `then` を実行する。
   - `accept`・`discard`・`reject`: ここで終わり。並べた後ろのフィルタも見ない。
   - `count`・`log`・`syslog`・`policer` だけ: 実行してから通す(暗黙の accept)。
   - `next term`: 次の term へ(Junos OS Evolved では最後の term に置けない)。
6. どの term にも当たらなければ、次のフィルタへ。最後のフィルタの末尾は暗黙の discard。

## 2. 動作の早見表

| 動作 | 種類 | 何をするか | IOS・IOS XR の ACL では |
|---|---|---|---|
| `accept` | 終端 | 通す | permit |
| `discard` | 終端 | 黙って捨てる | deny |
| `reject` | 終端 | 捨てて ICMP の到達不能(既定は code 13)を返す | deny(ICMP の扱いは機器の設定次第) |
| `count 名前` | 修飾 | 数える | 行ごとのカウンタ |
| `log` | 修飾 | PFE のバッファに残す(`show firewall log`) | `log` |
| `syslog` | 修飾 | syslog のメッセージにする(firewall の facility) | `log` |
| `policer 名前` | 修飾 | 量を制限する | `police`(CoPP・QoS) |
| `next term` | 流れ | 次の term へ | — |

## 3. この仮想ルータの事情

この単元のルータは vJunos-Evolved(Junos OS Evolved 26.2R1.7、PTX10001-36MR をまねた仮想ルータ)です。
パケットを中継する部分は、本物の ASIC の代わりにソフトウェアのシミュレーター(2 kpps まで)が受け持ちます。

### 3.1 reject tcp-reset は RST を返さない

`reject` の種類には `tcp-reset`(TCP なら RST を返す)がありますが、PTX のフィルタの動作の表には「tcp-reset は扱わない」と
書かれています。このルータでは commit は通り、TCP のパケットに対して RST ではなく ICMP の到達不能の code 0
(network unreachable)が返りました。`reject` は種類を付けずに使います。

### 3.2 policer は量を制限しない

policer は commit でき、`show firewall` の Policers の欄も出ますが、量を制限しません。64 kbps の上限に、1000 バイトの ping を
毎秒 100 個(約 0.8 Mbps)送っても、中継でも RE 行きでも 1 つも捨てず、捨てた数は 0 のままでした。
vJunosEvolved のデプロイ ガイドは、同じ系列の vJunosEvolved-BX について「firewall policer を扱わない」と書いています。
policer を使う設計は、本物の機器で確かめます。

### 3.3 出力フィルタと、RE が送るパケット

このルータでは、インターフェースの出力フィルタが RE の送るパケットにも効きました(2 ページ目の 2.8 節)。Juniper の文書には、
EX・QFX のスイッチの章に「出口のフィルタは RE が作る制御のパケットには効かない」という注記があります。機種によって
振る舞いが違うので、出力フィルタを当てたら、ルータ自身の通信(SSH の応答・ping の応答など)も確かめます。

### 3.4 カウンタと記録の遅れと残り方

- カウンタは、通信の直後に読むと増えていないことがあります。数秒待って読み直します。
- `show firewall log` のバッファは、古いものから消えます。この盤面では数分前の記録が見えなくなっていました。
- 設定を元に戻しても、カウンタの数・`show firewall log` の記録・syslog のファイルは、ルータの中に残ります。
  消すのは `clear firewall all`・`clear firewall log`・`file delete /var/log/名前` です(ラボの「最初からやり直す」はこれも消します)。

### 3.5 管理ポートのフィルタと 0.0.0.0/8

Junos OS Evolved 26.2R1 のリリース ノートには、既知の問題として「管理インターフェースのフィルタか、RE 行きの通信のポリシーに
予約のプレフィックス 0.0.0.0/8 を書くと、SSH を含む管理の通信を失う」(PR1910579)が載っています。送信元の検査の並びに
0.0.0.0/8 を入れたくなる場面があるので、このルータの管理ポートの周りでは使いません。

:::note
出典: Juniper Networks『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の評価の順の表
(term に動作が無いときの暗黙の accept・並べたフィルタの評価)、PTX の動作の表(`reject` の既定は administratively prohibited・
tcp-reset は扱わない)、EX シリーズの章の出口のフィルタの注記。『vJunosEvolved Deployment Guide』(2025-11-11)の制約の節
(転送は 2 kpps まで・vJunosEvolved-BX は firewall policer を扱わない)。『Junos OS Evolved Release 26.2R1 Release Notes』
(2026-10-22)の既知の問題 PR1910579。振る舞いは containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)で確かめたものです
(reject の返り方は FRR のコンテナでパケットを観て確かめた)。
:::
