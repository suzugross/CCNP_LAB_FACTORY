# Junos トラック — containerlab で Junos を「読む→ワークスペースで実践」で学ぶ(BL-275)

2026-11-14 ユーザ発案。状態= **未着手**(条件だけ確定・内容は後で決める)。XR トラック(BL-246・`XR-TRACK.design.md`)と同じ雰囲気の
Junos 中心の教材を、containerlab(szk-cl01)の上に作る。

## 1. 確定した条件(2026-11-14 ユーザ指示)

1. **ワークスペースに対応する**(左=課題／右=コンソール・学習モードの確認ボタン・段階式ヒント・確かめ方の例)。
   いまの `lab_console.py` と `lab.sh learn` は CML 専用なので、containerlab 対応が最初の作業になる(§4)。
2. **CML との同時起動はしない**(起動するのは常に片方だけ)。台数の見積もりは「CML を止めた szk-cl01」で行う(§3)。
3. **最初の単元は、IOS・XR との書き方と作法の違いの解説**から始める。実践する内容は CCNA 以上のレベルからでよい(§5)。
4. **XR トラックとの優先順位はユーザがその時々で決める**。→ この教材は XR トラックの残り(BL-257 の 2 周目・SPRI)に依存させない。
   XR との比較に使ってよいのは、XR トラックで済んだ単元(M0〜M13)だけ。

教材の書き方は CLAUDE.md「読み物」§6 の規定どおり(1 冊で日英切替・技術そのものから丁寧に・見取り図・設定例を常に・`:::walk`・
実測の出どころは末尾の出典へ)。ラボには最初から `verify:`(確かめ方の例・BL-266)を付ける。

## 2. 内容の候補(2026-11-14 に提示・未決)

| 案 | 中身 | 主なイメージ | ひとこと |
|---|---|---|---|
| A | XR トラックの Junos 版(SP 本線。JNCIA-Junos → JNCIS-SP、L3VPN 以降は JNCIP-SP の範囲)。J0〜J13 | vJunos EVO(P/PE)・FRR(CE/RR)・MX 系の単元は vJunos-router | XR の要件をそのまま移植課題に使える。量は XR と同じ |
| B | Junos の作法の短期コース(JNCIA-Junos 相当・5 単元前後) | EVO ×2+FRR | 小さい盤面で基盤を固められる。単独だと幅が狭い |
| C | エンタープライズ・DC 寄り(JNCIS-ENT → EVPN-VXLAN。cEOS と組む) | vJunos-switch・cEOS | CCNP EI の延長。XR(SP)と分野がずれる |
| D | マルチベンダ相互接続(Junos 主役・FRR／cEOS が対向) | EVO ×1〜2+軽量コンテナ | 台数を稼げる。版差が多く裏どりしにくい |

- 「Cisco の設定を渡して Junos で同じ挙動にする(移植)」はどの案にも混ぜられる課題の型。
- 提示時のおすすめ= B を A の先頭として作り A へ進む(D は各単元の 1 課題として混ぜる・C は後回し)。**ユーザは未決**。
- 試験の現行の版と番号は着手時に公式で確認する(2026-11-14 の検索では JNCIS-SP の番号が資料によって食い違っていた)。

## 3. 台数の見積もり(条件 2 を前提に)

| イメージ | 1 台のメモリ | 状態 |
|---|---|---|
| vJunos EVO(PTX 相当) | 7.3GiB(docker stats 実測) | 導入済み・実績あり |
| vJunos-router(MX 相当)／vJunos-switch(EX 相当) | 5GB(公式の最小) | 未導入(`~/vrnetlab/juniper/` に雛形)。公式は VM の中の入れ子の仮想化を非サポート→要 PoC |
| cJunosEvolved | 8GB 以上(公式) | 未導入。EVO と同じ重さなので優先度低 |
| cRPD | 軽い | 試用ライセンス 90 日→常設の教材には使わない |
| FRR／cEOS | 19MiB／1.56GiB | 導入済み(BL-274) |

- szk-cl01 は CML を止めた状態で総量 51GiB と見える(2026-11-14)。VMware のバルーンで見かけの総量が動くので、実際の上限は PoC で測る。
  目安= EVO なら 5〜6 台。XRd が担っていた軽い役(RR・CE)は FRR か cEOS に任せる。

## 4. どの案でも最初に要る土台

1. **ワークスペースの containerlab 対応**(`topologies/lab_console.py`)— **2026-11-14 完了**(§4.1)
   - 盤面の図= CML API の代わりに clab.yml(座標はノードのラベルで持たせる)。
   - コンソール= CML のシリアルの代わりに、szk-cl01 を踏み台にした SSH(Junos・cEOS・FRR とも管理アドレスへ)。
     採点とセッションを共有しない利点がある。
   - `lab.sh learn` を `platform: clab` でも通す(中間チェックは grade.yml が既に containerlab に対応)。
2. **やり直し**: 課題ごとの初期状態を Junos の `load override` ＋ commit で入れ直す案(作り直しの数分 → 数秒の見込み・未検証)。
   全体のやり直しは今の `lab.sh reset`(startup-config から作り直し)。
3. **同時起動の排他(案)**: 条件 2 を機械で守るなら、`lab.sh provision` で相手側が動いていたら止める(CML の稼働ラボ／containerlab のラボ)。
   入れるかどうかは着手時に確認。
4. **本と用語集**: `courses/junos/`(日英 1 冊・新しい棚)・`glossary/junos.yml`。

### 4.1 ワークスペースの containerlab 対応(2026-11-14 実装)

`topologies/lab_console.py` に containerlab の口を足した。CML の問題の動きは変えない(問題ごとに `problem.yml` の `platform` で分ける)。

| 部分 | CML の問題 | containerlab の問題(`platform: clab`) |
|---|---|---|
| 繋ぐ先の名前 | CML のラボ題名 `CCNP-LAB-<md5>` | `clab:<問題 ID>`(`target_lab()`)。学習モード・パック・ポータルの `?learn=` のどれでも同じ決め方 |
| 盤面 | CML API の座標・リンク | `clab_topology` の clab.yml(`clab_model()`)。座標= ノードの `labels` の `graph-posX`/`graph-posY`(無ければ円に並べる)。リンクの ethN は機器の名前で描く(vJunos EVO= et-0/0/<N-1>・vJunos-router/switch= ge-0/0/<N-1>・cEOS= Et<N>) |
| 状態(緑の点) | CML の BOOTED | szk-cl01 の docker(`clab_ops.lab_nodes`)の healthy・running |
| コンソール | CML のコンソールサーバ → シリアル(全接続で共有) | szk-cl01 へ SSH(鍵)→ Junos・EOS は管理アドレスへ SSH(踏み台の先)、FRR・Linux は `docker exec -it`。接続ごとに別のセッション・端末の大きさは SSH が運ぶ(Fit device to console は打ち込まない) |
| 確認ボタン | grade.yml の checkpoint | 同じ(grade.yml が containerlab に対応済み・BL-274) |
| やり直し | xr_reset.yml(XR のコミットへ戻す) | `clab_ops.py deploy --reconfigure`(startup-config から作り直し・`lab.sh reset` と同じ)。確認の文に「数分かかり、コンソールが切れる」を足す。速いやり直し(`load override`)は §4 の 2 |

- 起動: `scripts/lab.sh learn <ID>`(containerlab の問題を拒んでいた行を外した)・ポータルの `/_learn?id=<ID>`。learn.yml の無い問題の確かめは `lab_console.py --clab <ID>`。
- 機器のログイン: Junos= local.yml の `clab_node_username`/`clab_node_password`(vrnetlab の既定)、cEOS= `clab_eos_*`(既定 admin/admin)。採点・`lab.sh connect` と同じ値。
- 試験台= **POC-CLABLEARN-01**(白紙の JUN01 × 据え付けの FRR1・課題 2 本・日英・learn.yml の雛形)。
- ついでに直した不具合(XR の学習モードにも効く): 確認ボタンの結果の課題名が 80 字ほどで切れていた(ansible の YAML 出力が
  長い項目を折り返し、ワークスペースが 1 行目しか読んでいなかった)。`_report_items()` で折り返しをつなぎ、`''` を `'` に戻す。
  出す項目の選び方(PASS・FAIL・`未充足:`)は変えていない。

**確かめ(2026-11-14・CML は停止中・szk-cl01 に試験台だけ)**: provision 96 秒(全ノード healthy 94 秒)→ `lab.sh learn`(8896)で
盤面(JUN01・FRR1 の 2 台が緑・リンクの名前は et-0/0/0 と eth1)・課題 2 本と確かめ方の例・JUN01 のコンソール(SSH で
`admin@jun01>`)・FRR1 のコンソール(vtysh)→ 端末を 150×50 に変えると Junos の `show cli` が screen-length 50・screen-width 150 →
白紙で確認 m0t1 が FAIL 2 件(5 秒)→ コンソールから模範解を入れて m0t1 PASS → OSPF を入れて 45 秒後に m0t2 PASS 4 件 →
ポータルの形(パック常駐・`?learn=`・8890)で画面・課題文・盤面の節・盤面・コンソールが同じに動く → 「やり直し」98 秒で
JUN01 は白紙・FRR1 は startup-config のまま・記録は退避 → CML の問題(XRT-14)は従来どおり(CML 停止中は「CML API」のエラー・
やり直しの対象は XR01・RR1)。ブラウザの見た目は確かめていない(ここに画面を撮る道具が無い)。

**実機で分かったこと**:
- vJunos EVO は healthy になってから約 1 分、`et-0/0/0` が無い(`error: device et-0/0/0 not found`)。設定と commit はできる。
  教材で「起動直後は見えない」と書くか、起動の判定に IF の出現を足すかは、単元を作る時に決める。
- vJunos EVO で OSPF を commit すると `warning: requires 'OSPF' license` が出るが、OSPF は動く(隣接 Full・経路交換・ping)。
  最初の単元で触れる。
- containerlab の `kind: frr` は、frr.conf の hostname でなくノード名(`frr1`)をホスト名にする。

### 4.2 裏どりのソース(2026-11-14 ユーザ了承)

- 信頼順= 1: Juniper 公式文書と実機(vJunos)・1.5: Day One 本・ホワイトペーパー・RFC(断定は 1 でも確認)・2: Support Portal の KB・
  コミュニティ(補足どまり)。正典= CLAUDE.md「作問の裏どり」の Junos の段。仮想機の制約は Junos の挙動と分けて書き、版を記録する。
- ★www.juniper.net は robots.txt で全ロボットを拒否(ユーザのブラウザでも同じ)→ 自動で取りに行かない。公式の PDF はユーザが落として
  `private/sources/juniper/` に置く(一覧と URL は同フォルダの README.md)。vJunos EVO の機器内ヘルプは `help apropos` だけ使える。

## 5. 最初の単元(叩き台・条件 3)

IOS・XR と並べて、書き方と作法の違いを解説する。中身の候補:

- CLI のモード(運用モード／設定モード・`configure private`/`exclusive`)と階層(`edit`・`set`・`delete`・`up`・`top`)。
- commit の仕組み(候補設定・`commit check`・`commit confirmed`・`rollback`・`show | compare`)。IOS は即時反映、XR は Junos と同系。
- インターフェースの論理構造(物理 IF・`unit`・`family`)と IOS／XR のサブインターフェースの対応。
- 経路表の分け方(`inet.0`・`inet6.0`・`inet.3`)と `show route` の読み方(preference と AD の値の違い)。
- プロトコルごとの既定のポリシーと policy-statement(route-map・RPL との対比)。
- 表示の作法(`| display set`・`| display json`・`| match`)。

実践= CCNA 以上の題材(アドレッシング・static・OSPF・eBGP とポリシー など)を Junos の作法で組む。盤面は小さく(EVO ×2+FRR 程度)。

## 5.5 決めたこと(2026-11-14 ユーザ回答)

- **番号**: 単元 J0・J1…、課題 J0-1…(learn.yml の ID は j0t1)、ラボ JNT-01…。課題の切り出しの規則(lab_console.py の
  `_TASK_HEAD`・`_UNIT_HEAD`・`_task_sid`、course.sh)を「英大文字 1 字＋番号」に広げた(XR の M・S の課題は従来どおり。回帰= XR の
  実践ページの生成で差分なし・XRT-13/14 の課題の切り分けが同じ)。
- **既定のポリシー**: 0 章では仕組みだけ(プロトコルごとに既定の import/export があり、route-map を書かなくても動きが決まっている・既定の表)。
  policy-statement の書き方はルーティングの単元で。
- **Drive**: 専用フォルダを後で指定してもらう(0 章が書けた時点で rclone のリモート gdrive_junos を作る)。それまで book.yml に drive: を書かない。
- **棚**: 「Juniper」(新設)。本の題名は Junos Track ／ Junos トラック。置き場 `courses/junos/`。

## 6. 未決(後で決める)

- 内容(§2 のどれか・組み合わせ)と単元の並び。
- 試験の範囲にどこまで寄せるか。
- 新しいイメージ(vJunos-router／switch)の PoC をいつ行うか。
- BL-073 ①(Junos の続編問)の扱い(この教材の実践に吸収するか、別に残すか)。

## 7. J0 の実装(2026-11-14)

### 7.1 読み物 `courses/junos/`(日英・book.yml は `lang: en`・`alt_lang: ja`・棚 Juniper)

| ファイル | 中身 |
|---|---|
| 00-j0-map | 見取り図: 変更の流れ(運用モード → 候補設定 → commit check → commit → 動いている設定 → 50 世代・commit confirmed)・用語の表(たとえ・IOS・XR)・取り違えやすい点・盤面の分担・押さえどころ・設定例(fold) |
| 01-j0-config-tree | 木と set/edit/up/top/run・CLI がはじく行と commit で見つかる誤り・`display set`・`?` の `>` と `+`・物理/論理ユニット/ファミリー・既定で有効と disable・terse の読み方・VLAN 2 つと IPv6 の設定例・IOS 対照表 |
| 03-j0-commit | 候補設定と compare・commit check/comment/and-quit・50 世代と rollback(候補へ読むだけ)・commit confirmed(時系列の図・pending・by root via other)・XR との違い 2 点・共有の候補設定と private/exclusive・抜けても変更は残る・対照表 |
| 05-j0-routing-table | inet.0 ほかの表・show route の読み方・preference の表(IOS の AD と並べる)・浮動の静的経路・次ホップは直接接続(無いと hidden にも出ない)と resolve・既定のポリシー(OSPF は export しない・PTX の BGP は別)・設定例・対照表 |
| 07-j0-appendix | Junos OS と Evolved・この仮想ルータの事情(PTX・ライセンスの知らせ・限り・mgmt_junos・ポートの遅れ・内部ユニット・inet.2/3・最初の commit)・早見表・調べる場所 |
| 02/04/06 実践 | `scripts/course.sh junos build` が JNT-01 の task から切り出す(practice.yml。J0-1・J0-2 / J0-3 / J0-4) |

用語集= `glossary/junos.yml`(13 語・books: [junos])＋ basics.yml に OSPF・BGP・VLAN・MTU・CLI。automation.yml の candidate-datastore を
books: [xr, ccie-ei] に絞った(「candidate configuration」を Junos の本では Junos の候補設定として拾うため。XR の本の出力は変わらない)。

### 7.2 ラボ JNT-01(platform: clab・学習モード)

盤面= JUN01 ─ JUN02 ─ FRR1(vJunos-Evolved ×2・FRR 1・RAM 約 15GB)。FRR1 は lo に 198.51.100.1/24 を持つが network 文で 192.168.0.3/32 だけ広告。

| 課題 | 求めること | Junos の作法の要 | 確認(grading.j0tN.yml) |
|---|---|---|---|
| J0-1 | 2 台にアドレス | unit/family・commit | 設定(display set)・リンクの両端の ping |
| J0-2 | 3 台で OSPF・lo は passive | network 文が無い・ユニットを名指し | 設定・JUN02 の 2 隣接 Full・FRR1 の 2 つの lo の経路(JSON)・lo から lo への ping |
| J0-3 | FRR1 向け MTU 9000 を、確定しなければ戻る形で入れ、壊れたら自動で戻させる | commit confirmed・巻き戻しの履歴 | `show system commit` の `by root via other` が `commit confirmed` のすぐ上・mtu 9000 が無い・FRR1 と Full |
| J0-4 | JUN02 に 198.51.100.0/24 の静的経路。次ホップは FRR1 の lo・OSPF の外部経路に譲る | resolve・preference(外部 150) | Static/151 以上で et-0/0/1.0・Protocol next hop 192.168.0.3・ping・OSPF は変えない(export 無し) |

**実機で確かめたこと(記録 `poc/junos/expJ0-*.log`・`expJNT01.log`)**: MTU 9000 で inet の MTU が 8986 になり、FRR1(1500)との隣接は
Exchange/ExStart に留まる → 確定しなければ一斉通知と `by root via other` の行で戻り、40 秒ほどで Full。次ホップが lo の静的経路は resolve が無いと
経路表に出ない(hidden にも出ない)。commit confirmed は設定モードを抜けても予約が残り、別のセッションの `commit check` で確定できる(XR は抜けると
取り消す)。巻き戻しは指定の時間より最大 1 分ほど遅れることがある。起動直後(ポートがまだ無い間)にも設定と commit はでき、ポートが現れると効く。

**E2E(2026-11-14)**: 作り直しで白紙 → 学習モード(lab.sh learn JNT-01)で盤面 3 台(リンク名 et-0/0/0・et-0/0/1・eth1)・課題 4 本と確かめ方と読み物の節 →
白紙で 4 課題とも FAIL → ワークスペースのコンソールから J0-1・J0-2 を入れて PASS → J0-3 は commit confirmed 2 の直後 FAIL・巻き戻しの後 PASS →
J0-4 は「resolve 無し＋preference 120」で 3 項目 FAIL、「resolve 有り＋120」で preference だけ FAIL、160 で PASS → 本採点 100/100 →
ワークスペースの「やり直し」98 秒で白紙(j0t1 が FAIL)。
