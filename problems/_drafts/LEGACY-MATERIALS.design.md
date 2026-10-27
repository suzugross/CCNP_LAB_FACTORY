# 旧教材の棚卸しと、今の教材の形への載せ替え(BL-259)

状態: **未着手(棚卸しだけ済み・2026-10-27)**。ユーザ依頼「あとで載せ替えられるようにメモしておいて」。

読み物の機能(BL-230・2026-09-29)と書き下ろし教材の日英切替(BL-248・2026-10-13)より前にも、
教材寄りの資産を作っていた。どれも「問題」の形(1 問 1 採点)で作ってあり、今の教材の形には載っていない。
ここはその一覧と、載せ替える時に決めること・つまずきそうな点の控え。

## 1. 載せ替え先(今の教材の形)

正典は CLAUDE.md「読み物」§6 と `courses/README.md`。手本は `courses/xr/`(XR トラック・BL-246)。

| 部品 | 置き場 | 中身 |
|---|---|---|
| 本(2 言語) | `courses/<名前>/book.yml`・`en/`・`ja/` | 英語が原文。日本語版は見出しの並びと段落の数をそろえる。棚= `shelf:`、学習用ラボ= `labs:` |
| 実践ページ | `courses/<名前>/practice.yml` | 課題文は二重に持たない。`scripts/course.sh` が `problems/<ID>/task.en.md`・`task.md` から切り出す |
| 学習用ラボ | `problems/<ID>/learn.yml` | 課題ごとに 確認(`check:` → `grading.<課題>.yml`)・3 段のヒント・模範解・読み物への戻り先(`read:`) |
| 解く場所 | ワークスペース(`topologies/lab_console.py --learn <ID>`) | ブラウザ 1 画面。左= Tasks/トポロジ/Reading、右= 機器のコンソール(CML のコンソールへ中継) |

## 2. 棚卸し

### A. Ansible 道場と Ansible の自動化問(2026-06 下旬・公開初版より前)

| ID | 内容 | 難 |
|---|---|---|
| ANSIBLE-01-INVENTORY | インベントリと接続(network_cli / network_os) | 1 |
| ANSIBLE-02-ADHOC | アドホックコマンドとモジュール | 1 |
| ANSIBLE-03-PLAYBOOK | Playbook の構造 | 2 |
| ANSIBLE-04-VARS | 変数の優先順位 | 2 |
| ANSIBLE-05-IDEMPOTENCY | 冪等性と --check/--diff | 2 |
| ENCOR-AUTO-OSPF-FILL-01 | 穴埋めで OSPF を自動構成(レベル 1) | — |
| ENCOR-AUTO-OSPF-ROLE-01 | リソースモジュール・データ駆動・role(レベル 2) | — |
| ENCOR-AUTO-OSPF-SCRATCH-01 | OSPF の role をゼロから書く(レベル 3) | — |
| ENARSI-AUTO-BGP-01 | リソースモジュールで eBGP | — |

- 考え方= 題材は固定で、変わるのは Ansible の技術だけ(README「Ansible 自動化ラボ」節)。
- 作り= `controller/`(穴あき)・`controller_solution/`(完成形)・`blanks.yml`(`gen_blanks.py` が seed で穴を選ぶ)。
  採点は機器の最終状態だけ(手段を問わない)。
- **解く場所が今のワークスペースと違う**: ユーザは VSCode Remote-SSH でこのホストに入り、`lab/<ID>/` の
  playbook を編集してホストから流す。今のワークスペースの右側は機器のコンソールだけ。
- 続編の痕跡: `NETAUTO-DOJO.design.md` に「Ansible道場 T2(08/09/10)」と一言あるだけ。06〜10 の計画の中身は記録が見つからない。

### B. ネット自動化道場 NETAUTO(2026-07-08 開始)

- 完成は **NETAUTO-03-RESTCONF**(curl → Python requests・cat8000v 1 台)だけ。形は A と同じ(穴埋め・最終状態で採点)。
- 残り 4 本は未着手= BL-008 NETCONF(ncclient)・BL-009 netmiko・BL-010 JSON/YAML/Jinja2(ラボ不要)・BL-011 pyATS/Genie。
  設計は [NETAUTO-DOJO.design.md](NETAUTO-DOJO.design.md)。

### C. 伴走形式の教育ラボ(2026-07-13)

| ID | 内容 | 規模・起動 |
|---|---|---|
| SDA-LISP-01 | SD-Access の中身(LISP/VXLAN)を素手で組む。Phase 0〜8 で 📋観察・🤔考察を対話しながら進める。Phase 4 はわざと失敗させる | 9 台(iol-xe×7＋nxosv9300×2)・約 29GB・`sda_ops.py`・静的 yaml(管理 IP 焼き込み) |
| EVPN-VXLAN-01 | BGP EVPN×VXLAN 正統編(上の続編) | 8 台(iol-xe×5＋nxosv9300×3)・約 40GB・`evpn_ops.py`・静的 yaml |

- README が自分で「試験ドリルではなくエンリッチメント教材」と書いている。**今の形にいちばん近い**
  (段階に分かれ、観察と考察が本文にある)。考察の答えは `ANSWER_KEY.md`。採点は最後の軽い疎通確認だけ。

### D. 体感ラボ(2026-07-10〜12)

| ID | 内容 | 起動 |
|---|---|---|
| FGT-SDWAN-01 | SD-WAN 体感構築(WAN1 に遅延・損失を注入して逃げるのを見る) | `sdwan_ops.py`(inject/restore あり) |
| FGT-FW-BASIC-01 | FW 基本設計(ポリシーと NAT で通る/通らない) | 共用ラボ FGT-LAB |
| FGT-IPSEC-01 | Cisco ⇄ FortiGate の IKEv2 サイト間 VPN | 共用ラボ FGT-LAB |
| FGT-REPLACE-01 | ASA → FortiGate リプレース(FGT シリーズの卒業試験) | 共用ラボ FGT-LAB |
| ENCOR-QOS-CLASS-01 / -POLICE-01 / -LLQ-01 | 分類・マーキング／ポリシング／階層シェーピング＋LLQ。効果を iperf3・ping で実測して採点 | lab.sh |
| UM2-BUILD-01 / -02 | 書籍のネットワークデザインパターン(Untrust ワンアーム)の CML 再現。ASAv HA＋IOSvL2 | `um2_ops.py`。ユーザ持ち込みの下書きが `um2/` |
| CAMPUS-TS-01 | 3 層キャンパス LAN の障害切り分け演習(golden＋故障注入) | 11 VM |

- FGT-LAB は共用で、FGT-SDWAN-01 と FGT-FW-BASIC-01 は fgt1 を共用する(どちらの build も、もう一方の設定を巻き戻す)。
- 解答記録が残っているのは UM2-BUILD-01(96→100)だけ。出題履歴の台帳(2026-07-15〜)より前のものは記録が無い。

### E. 読む系(2026-09-19〜22)

- 解説穴埋めの知識ベース 8 本 `topologies/cloze_kb_{aaa,dmvpn,ipv6fhs,mcast,mpls,order,stp,svc}.py`。
  日本語の解説文に空欄を開けた形で、紙面の穴埋め枠(`--cloze`)で今も出題に使っている。
- 単元シラバス `curriculum/U-A3-stp.md`・`curriculum/U-F-mcast.md`(知識項目表＋出典の照合表 `*.sources.md`)。

### F. 計画だけ・途中のもの

| 番号 | 内容 | 状態 |
|---|---|---|
| BL-008〜011 | NETAUTO の残り 4 レッスン | 未着手 |
| BL-050 | Cisco Catalyst SD-WAN の CML 導入(体感ラボの土台) | 2026-07-12 から PoC 中 |
| BL-026 | QoS の MQC 入門ドリル(手順ガイドつき) | 未着手 |
| (台帳に無し) | Ansible 道場の続き(T2) | A の末尾のとおり痕跡だけ |

## 3. 載せ替えで決めること・つまずきそうな点

1. **言語**: 旧教材は日本語だけ。§6 の標準どおりなら英語を原文として書き起こし、日本語版を並べる。
   問題側も `task.en.md` が要る(`course.sh` が実践ページを切り出す元)。
2. **解く場所(A・B)**: ワークスペースにホストのシェル(`lab/<ID>/` で作業)とファイル編集の手段が無い。
   案= (a) ワークスペースにホストのシェルのタブを足す／(b) 解く場所は VSCode のまま、本と Tasks(確認・ヒント)だけ載せる。要判断。
3. **確認の単位**: 旧教材は 1 問 1 採点(`grading.yml`)。`learn.yml` の課題ごとに `grading.<課題>.yml` へ分ける。
   A・B の穴埋め(`blanks.yml`)と、learn.yml の段階式ヒントは役割が重なるので、どちらで行くか決める。
4. **起動方式(C・D)**: 専用の `*_ops.py` と静的 yaml で、`lab.sh` を通らない。ワークスペースの単発起動
   (`--learn <ID>`)がこれらのラボに繋がるか、やり直し(BL-254)が効くかを先に確かめる。FGT-LAB の共用の巻き戻しにも注意。
5. **CML 2.10.1 移行後の実走記録が無い**。必要なイメージ(asav・cat8000v・fortigate・nxosv9300・iosv・iosvl2・ubuntu)は
   2026-10-18 のスナップショット(`private/cml-backup/2.10.1-*`)に残っている。載せ替え前に白紙→模範解の 1 周を回す。
6. **観察・考察の移し先(C)**: 📋観察・🤔考察と `ANSWER_KEY.md` の答えは、本文と「やってみる」(XR トラック M7 で入れた形)・
   learn.yml のヒント・模範解に振り分ける。わざと失敗させる段(SDA の Phase 4)は「やってみる」と相性がよい。
7. **E は素材として使う**: cloze_kb は紙面の出題に使っているのでコードは触らない。解説文は本文の下書きの素材にはなるが、
   英語の原文は別に書く。シラバス 2 本は章立ての物差しに使える。
8. **公開・非公開**: UM2 の題材は書籍由来。公開側に書名を書かない(今も書いていない)。

## 4. 載せ替えの順の案(未決・着手時にユーザと決める)

| 順 | 対象 | 理由 |
|---|---|---|
| 1 | C(SDA-LISP-01→EVPN-VXLAN-01) | 形がいちばん近い。段階と観察が本文に既にある。ワークスペースは機器コンソールだけで足りる |
| 2 | D の QoS 3 本 | lab.sh で動く。実測の採点を課題ごとの確認に分けやすい |
| 3 | A＋B(自動化コース 1 冊) | 解く場所(§3-2)を決めてから。NETAUTO の残り(BL-008〜011)もこの本の章として書き足せる |
| 4 | D の FGT 4 本・UM2・CAMPUS | 専用 ops と共用ラボの扱いを詰めてから |

## 5. 着手するとき

1. BACKLOG の BL-259 の状態を更新し、対象(どのグループか)をここに追記する。
2. 対象のラボを CML 2.10.1 で白紙→模範解まで 1 周させる(§3-5)。
3. `learn.yml` を作り、確認を課題ごとに分ける(§3-3)。
4. `courses/<名前>/` に英語の原文→日本語版を書く。`scripts/course.sh <名前> build` → `sync`。
5. 1 グループ載せ終えるごとに、ここの表に「載せ替え済み(日付・コース名)」を書く。
