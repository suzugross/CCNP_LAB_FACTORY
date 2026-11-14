# CLAB-SOLO — containerlab を CML なしで回す(BL-274 ①)

2026-11-14 起票。状態= **完了**(2026-11-14)= ① CML なしで回す(§6)・② FRRouting・Arista cEOS の取り込みと採点の口(§7)。

## 1. 目的と方針

ユーザ方針(2026-11-14)= **CML と containerlab は基本切り離して運用する**。Cisco を重点的に検証する時は CML、
Juniper 中心のマルチベンダは containerlab。これまでの containerlab は CML の複合ラボの付け足しで
(BL-061・`CLAB-HYBRID.design.md`)、`lab.sh`・`grade.yml` は CML が作る生成物(`topologies/_generated/<ID>/mgmt_map.yml`)を前提にしていた。
① では containerlab だけの問題を、CML を一度も触らずに **出題 → 採点 → やり直し → 撤収** できるようにする。

範囲外(後で): ② FRRouting・Arista cEOS の取り込み、③ 採点の口の追加(FRR・EOS)、ポータルのワークスペース・パックへの組み込み、
既存の複合問(JUNOS-BUILD-01・POC-CLABHYB-01)の扱い(ユーザ判断)。パックは Junos・マルチベンダの問題を既定で選ばない
(`gen_pack._non_cisco`)ので、containerlab だけの問題が毎日のパックに混ざることはない。

## 2. 問題の宣言

`problem.yml` に `platform: clab` を書く(書かなければ従来どおり `cml`)。あとは複合ラボと同じ:

```yaml
platform: clab
clab_topology: clab/<name>.clab.yml   # パック内の相対パス
clab_nodes:                           # 採点の接続先(mgmt-ipv4 と一致させる)
  JUN01: 172.20.20.2
```

`lab:`・`topology:`・`image_family:` などの CML 用の項目は要らない。

## 3. 変更点

| 場所 | `platform: clab` の時 |
|---|---|
| `scripts/lab.sh provision` | build_topology・lab_up(CML)を飛ばし、`clab_ops.py deploy` → 作業フォルダ `lab/<ID>/`(問題.md)。`_generated/<ID>/` を作る(採点の置き場) |
| `scripts/lab.sh teardown` | CML の absent・MGMT リースの返却を飛ばし、`clab_ops.py destroy` → 生成物と作業フォルダを掃除 |
| `scripts/lab.sh reset` | 機器を startup-config から作り直す(`clab_ops.py deploy --reconfigure`)＋学習モードの記録を退避 |
| `scripts/lab.sh rma`・`learn` | CML 専用と表示して止める |
| `scripts/lab.sh status` | containerlab のラボ一覧を足す(全問題共通。ホストに届かない時はそう表示) |
| `playbooks/grade.yml` | mgmt_map を読まない(接続先は `clab_nodes` だけ)・`_generated/<ID>/` が無ければ作る |
| 誤ったラボの採点の防止 | `clab_ops.py verify`(下)を採点の前に走らせる。`clab_topology` を持つ問題すべて(複合ラボも) |
| `topologies/quota.py` | 得点行が読めない時の再採点で、CML 用の bringup を挟まない |

**誤ったラボの採点の防止**: CML のラボは IOS の設定に焼いた指紋(`alias exec labid`)で照合するが、Junos を白紙から
組ませる問題では設定に指紋を置けない。containerlab の管理網(docker の `clab` ネットワーク)は全ラボで共通なので、
別のラボが同じアドレスを使っていることがありうる。そこで、採点の前に szk-cl01 の docker のラベルで次を確かめる:
その問題のラボ(トポロジの `name`)が動いている・`clab_nodes` の各ノードがそのラボのコンテナで、管理アドレスが一致する・healthy。
外れたら採点を中止する。

## 4. 試験台 POC-CLABSOLO-01

出題用ではなく、この基盤の確かめと雛形。vJunos EVO ×2(RAM 約 15GB。CML を止めている時の szk-cl01 なら足りる)。

```
JUN01(白紙・受験者が設定) et-0/0/0 ── et-0/0/0 JUN02(据え付け)
 lo0 192.168.0.1/32         10.0.12.0/30          lo0 192.168.0.2/32
                         OSPF area 0
```

採点= JUN01 の設定(アドレス)・JUN01 から見た Full 隣接(JSON)・双方の lo0 の経路(JUN02 側から観測を含む)。

## 5. 確かめ(E2E)

| # | 内容 | 期待 |
|---|---|---|
| 1 | `lab.sh provision POC-CLABSOLO-01` | CML に触れずに 2 台 healthy・作業フォルダ |
| 2 | `lab.sh grade`(白紙) | 0 点(チェックはすべて JUN01 の設定が前提) |
| 3 | 模範解を入れて `lab.sh grade` | 100/100 |
| 4 | `lab.sh reset` → `lab.sh grade` | 白紙に戻り、2 と同じ点 |
| 5 | 別ラボの検知 | `clab_nodes` のアドレスを変えた写しで verify が止める |
| 6 | `lab.sh teardown` → `lab.sh status` | ラボ・生成物・作業フォルダが消える |
| 7 | 回帰 | CML の問題の `grade.yml` の構文確認(CML は止まっているので実走は CML を上げた時) |

## 6. 記録

**2026-11-14 E2E(CML は停止・制御ホストは Mac のコンテナ・管理網へは踏み台)**。採点は `lab.sh grade` でなく
`grade.yml` を直接(試験の点をノルマの記録に入れないため)。

| # | 結果 |
|---|---|
| 1 | ✅ `lab.sh provision` 1 分 35 秒(EVO ×2 が 92 秒で healthy)。CML に一度も触れない・作業フォルダ `lab/POC-CLABSOLO-01/問題.md`・接続先の表示 |
| 2 | ✅ 白紙 0/100。集めた出力が本物(白紙の設定・隣接なし・`ping: bind: Cannot assign requested address`)で、接続の失敗ではないことを確認 |
| 3 | ✅ 模範解(solution.md の set 行を採点と同じ接続の `cli_config` で commit)→ 収束を待って 100/100(1 分 20 秒) |
| 4 | ✅ `lab.sh reset` 1 分 35 秒 → 0/100(JUN01 は白紙・JUN02 は startup-config に戻る) |
| 5 | ✅ verify: 管理アドレス違いの写し → rc=2「JUN02: 管理アドレスが違います」・ラボ名違いの写し → rc=2「動いていません」・本物 → OK |
| 6 | ✅ `lab.sh teardown` → ラボ・生成物・作業フォルダが消える。`lab.sh status` に containerlab の欄。撤収後の `lab.sh grade` は照合で中止・ノルマの記録なし・bringup を挟まない |
| 7 | ✅ CML の問題(ENARSI-OSPF-MADJ-01・未構築)は従来どおり mgmt_map が無いところで止まる。複合問(JUNOS-BUILD-01・未構築)は新しい照合で止まる。CML を上げての実走は未確認 |

直したこと(E2E の途中): 照合で止まった採点が空の `_generated/<ID>/` を作っていた → 置き場は照合の後に作る。
`lab.sh status` でラボが無い時にメモリの行しか出なかった → 「ラボ無し」と出す。`clab_ops.py deploy` が
containerlab の失敗を `tail` の終了コードで隠していた → リモートで `set -o pipefail`。

**containerlab だけの問題の作り方**(雛形= POC-CLABSOLO-01): `problems/<ID>/` に `problem.yml`(`platform: clab`・`clab_topology`・
`clab_nodes`)・`clab/<name>.clab.yml`(ノードの `mgmt-ipv4` を固定)・必要なノードの startup-config(Junos は階層形式)・`grading.yml`
(`exec: junos`・`parser: json` 可)・`task.md`。管理アドレスは全ラボ共通の 172.20.20.0/24 なので、同時に動かすラボ同士で重ねない。

**残り**: ポータルのワークスペース(コンソール・学習モード)は CML 専用のまま。containerlab の問題は VS Code の端末から ssh で解く。

## 7. ② FRRouting・Arista cEOS の取り込み(2026-11-14)

### 7.1 調べたこと(裏どり)

| 論点 | 確認先 | 結果 |
|---|---|---|
| FRR のイメージ | quay.io/frrouting/frr のタグ一覧(API)・szk-cl01 で pull | 公式の安定版 `10.7.1`(2026-08-26)。containerlab 向けの `containerlab-10.7.1`(SSH 入り)もある |
| containerlab の FRR の扱い | containerlab の文書(kinds/frr・lab-examples/frr01) | 専用の kind `frr`(設定と daemons を containerlab が用意・SSH で admin/admin → vtysh)。★**szk-cl01 の 0.77.0 には無い**(deploy で「kind "frr" is not supported」を実測)。最新は v0.83.0(2026-11-07) |
| cEOS の入手 | containerlab の文書(kinds/ceos)・Web 検索(Arista の手順を紹介する資料複数) | arista.com の利用者登録が要る(サポート契約なしで作れるという資料が複数)。Support → Software Download → cEOS Lab から `cEOS64-lab-<版>.tar.xz`。`docker import … ceos:<版>` |
| cEOS の要件 | containerlab の文書 | kind `arista_ceos`(0.77.0 は `arista_ceos`・`ceos` の両方を受け付ける)。既定 admin/admin・eth0= Management0・eth1= Ethernet1。**4.32.0F より前は cgroup v1 が要る**(szk-cl01 は cgroup v2 → 4.32.0F 以降)。healthcheck の記述なし |

### 7.2 決めたこと

- ★**2026-11-14 に containerlab 0.83 へ上げ、FRR は `kind: frr` + `quay.io/frrouting/frr:containerlab-10.7.1` に切り替えた**(§7.5)。以下は 0.77 の時に決めた形(今も同じ扱いで動く):
- **FRR は `kind: linux` + 公式イメージ `quay.io/frrouting/frr:10.7.1`**(0.77.0 で動く昔からの形)。`/etc/frr` を**フォルダごと** bind
  (`daemons`・`frr.conf`・`vtysh.conf` をパックの `clab/<node>/` に置く)。ファイル 1 つずつの bind は、FRR が設定を書き戻す時の rename が bind の上で失敗するため避けた。
- **FRR には SSH が無い → 採点も解く時も szk-cl01 の `docker exec` で vtysh**。
  - 採点: `exec: frr`(`clab_ops.py exec … -- vtysh -c "<command>"`)。`show … json` なら `parser: json`。
  - 解く時: `scripts/lab.sh connect <ID> <NODE>`(FRR は vtysh、Junos・EOS は管理アドレスへ ssh)。
  - containerlab を 0.83 に上げて kind `frr` に替えても、採点の口(docker exec)はそのまま使える。上げるかはユーザ判断(sudo でパッケージを更新)。
- **Arista EOS は `exec: eos`**(junos と同じ network_cli・`arista.eos.eos`・踏み台経由・既定 admin/admin。local.yml の `clab_eos_username`/`clab_eos_password` で上書き可)。
- **リンクの MTU は 1500 にそろえる**(拡張形式の `type: veth` + `mtu: 1500`)。containerlab の veth の既定は 9500 で、Junos の et- と EOS の Ethernet は
  IP の MTU 1500。OSPF は DBD で MTU を照合するので、Junos × FRR で両側とも ExStart のまま止まった(実測)。vJunos 同士は詰まらなかった。
- **起動の判定**: healthcheck の無いコンテナ(FRR・cEOS)は、CLI が応答したら起動済み(`clab_ops.READY_PROBE`: FRR= `vtysh -c 'show version'`・EOS= `Cli -p 15 -c 'show version'`)。
- **RAM の見積もり**を種類ごとに(`FAMILY_RAM_MB`: junos 7500・eos 2000・frr 150・linux 100。eos・frr は見込み)。
- **cEOS の取り込み**: `clab_ops.py import-ceos --repo . --file <アーカイブ>`(szk-cl01 へ送り `docker import` → `ceos:<版>`・送ったものは消す)。

### 7.3 確かめ(POC-CLABFRR-01: 白紙の JUN01 × 据え付けの FRR1・OSPF)

| # | 結果 |
|---|---|
| 1 | ✅ provision 1 分 36 秒(FRR は CLI の応答で起動を判定・JUN01 と同じ 93 秒で揃う)。RAM プリフライトに種類ごとの台数 |
| 2 | ★MTU の食い違いで ExStart(FRR の eth1 が 9500・Junos は 1500)→ トポロジで `mtu: 1500` → 解消 |
| 3 | ✅ 白紙 0/100(FRR の出力が `exec: frr` で本物: 隣接 `{}`・経路 `{}`)・模範解で 100/100(収束込み 44 秒)。FRR の JSON(`show ip ospf neighbor json` の `converged`・`ifaceAddress`、`show ip route … json` の `protocol`・`selected`)で採点が通る |
| 4 | ✅ `lab.sh connect … FRR1` で vtysh(疑似端末で確認)。★`write memory` で `frr.conf` が frr(uid 100)・600 に書き直され、reset の上書きが拒否される → 送る前に送るものを消すよう `clab_ops.py deploy` を直した → reset で設定がリポの内容に戻ることを確認・白紙 0/100 |
| 5 | ✅ teardown → szk-cl01 に残り物なし・コンテナなし |

### 7.4 cEOS の確かめ(POC-CLABEOS-01: 白紙の EOS1 × 据え付けの FRR1・OSPF)

イメージ= ユーザが arista.com で入手した `cEOS64-lab-4.37.0F.tar.xz`(約 660MB)→ `import-ceos` で `ceos:4.37.0F`(2.7GB・送って取り込むまで 1 分 54 秒)。
同じ版の `cEOS-lab-4.37.0F.tar`(32 ビット版)は使わない。

| # | 結果 |
|---|---|
| 1 | ✅ provision 18 秒(cEOS は VM でないので速い)。RAM は cEOS 1.56GiB・FRR 19MiB(docker stats) |
| 2 | ★admin でログインすると特権レベル 1(`eos1>`)・`show running-config` が「% Incomplete command」。containerlab の既定の設定は `username admin privilege 15` だけで `aaa authorization exec default local` が無いため → 採点は EOS のノードだけ enable(become)。既定の設定には手を入れない(実機と同じ動き) |
| 3 | 既定の設定(実測): `no ip routing`・`service routing protocols model multi-agent`・Management0 に管理アドレス・既定経路・`management api http-commands/gnmi/netconf`。Ethernet1 は switchport(MTU 9214) |
| 4 | ✅ 白紙 0/100(出力は本物: 既定の running-config・隣接なし・`ping: bind: Cannot assign requested address`)・模範解で 100/100(収束込み 1 分)。EOS の JSON(`show ip ospf neighbor \| json` の `vrfs.default.instList.*.ospfNeighborEntries[*]` の `routerId`・`interfaceAddress`・`adjacencyState: full`)で採点が通る |
| 5 | ★作り直しの直後は Cli が即応答するが SSH+enable は十数秒後に通る → 起動の判定に「コンテナの中で 22 番が受け付ける」を足した → 判定 16 秒・直後の SSH+enable が 1 回目で通る |
| 6 | ✅ reset → 白紙 0/100・`lab.sh connect … EOS1` は踏み台越しにパスワードの入力まで届く・teardown で残り物なし |

### 7.5 containerlab 0.83.0 への更新(2026-11-14)

ユーザが szk-cl01 で `sudo apt update` → `sudo apt install containerlab=0.83.0`(apt のリポジトリ netdevops.fury.site。SUID と clab_admins はそのまま・docker 27.5.1 は変えない)。
リリースノート 0.78〜0.83 の要点: 0.80.0 で kind `frr`・0.81.0 でノードの `extras` 廃止(未使用)・0.78.0 で bind のパスの解決を決定的に・0.83.0 で `deploy` は動いているラボを作り直さず調整(reconcile)。

回帰(3 つの試験台を同時に・7 分 49 秒): provision 94 秒・97 秒・38 秒 → 3 ラボ 7 ノードの同時稼働(ホストの使用 27GiB)→ 模範解で 3 つとも 100/100 →
FRR の bind(`frr1` → `/etc/frr`)は従来どおり → reset(`--reconfigure`)は 0.83 でもノードを作り直す(模範解の後に白紙 0/100)→ teardown で残り物なし。

**kind `frr` の試し**(使い捨てのラボ・`quay.io/frrouting/frr:containerlab-10.7.1`・`startup-config:` と `daemons: [ospfd]`):
containerlab が `clab-<lab>/<node>/config/`(daemons・frr.conf・vtysh.conf)を作って `/etc/frr` に渡す(パックのファイルを直接 bind しない)。
`ssh admin@<管理アドレス>`(パスワード admin)で vtysh に入る(踏み台経由で確認)。`docker exec … vtysh -c` もそのまま使える。
`write memory` の後も持ち主は suzuki のまま・`--reconfigure` で startup-config の内容に戻る。設定の読み込みは起動から数秒遅れる。

**切り替え**(ユーザ了承): POC-CLABFRR-01・POC-CLABEOS-01 の FRR を `kind: frr`・`startup-config: frr1/frr.conf`・`daemons: [ospfd]` に
(パックの `daemons`・`vtysh.conf` は消した。containerlab が作る)。採点(`exec: frr` = docker exec)と `lab.sh connect` は変えない。
一周(6 分 4 秒): provision 96 秒・32 秒 → startup-config が読まれている → 白紙 0/100 ×2 → 模範解 100/100 ×2(MTU 1500 の指定も効く)→
FRR で余計な設定を `write memory` → reset で消えて白紙 0/100 → teardown で残り物なし。

### 7.6 残り(ユーザ判断)

- 既存の複合問(JUNOS-BUILD-01・POC-CLABHYB-01)の扱い。CML を上げた時に、新しい照合が入った複合問の実走を確かめる。
- ポータルのワークスペース(コンソール・学習モード)は CML 専用のまま。containerlab の問題は VS Code の端末から `lab.sh connect` で解く。

**問題の作り方の補足(② の分)**: FRR は `kind: frr`・`image: quay.io/frrouting/frr:containerlab-<版>`・`startup-config: <node>/frr.conf`・
`daemons: [ospfd, bgpd, …]`(書いたものだけ動く)。(0.77 の形= `kind: linux` で `clab/<node>/` に `daemons`・`frr.conf`・`vtysh.conf` を置き `binds: [<node>:/etc/frr]`。)cEOS は startup-config を置かなければ containerlab の既定の設定で白紙起動(版はイメージの `ceos:<版>`)。
Junos・EOS と FRR をつなぐリンクは拡張形式で `mtu: 1500`。採点は `exec: junos`・`exec: eos`・`exec: frr`(`show … json` / `| json` / `| display json` なら `parser: json`)。
