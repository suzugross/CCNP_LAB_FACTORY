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
- 提示時のおすすめ= B を A の先頭として作り A へ進む(D は各単元の 1 課題として混ぜる・C は後回し)。
  **2026-11-14 ユーザ決定= おすすめどおり**。並び= J0 作法 → J1 ルーティング ポリシー → J2 firewall filter → J3 運用と保守 → SP の本線(IS-IS → BGP → MPLS → L3VPN)。
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

## 8. J1 ルーティング ポリシー(2026-11-14 着手・PoC・執筆・E2E)

2026-11-14 ユーザ決定。J0 の 2.5 節(既定のポリシー)の続き。JNCIA-Junos の「Routing policy and firewall filters」のうちポリシーの側。
firewall filter は J2。比べる相手= IOS の route-map／prefix-list と XR の RPL(M5・済み)。

### 8.1 盤面 JNT-02(PoC の盤面をそのまま使う・`problems/JNT-02/`)

```
SRV1 eth1 ── et-0/0/1 JUN01 et-0/0/0 ── et-0/0/0 JUN02 et-0/0/1 ── eth1 FRR1(ISP・AS 64500)
  172.16.10.0/24(.10)    (.1)  10.0.12.0/30            10.0.23.0/30(eBGP)
  lo 172.16.20.1/24      lo0 192.168.0.1  lo0 192.168.0.2       lo 203.0.113.1
                         AS 65000(JUN01・JUN02・OSPF area 0)
```

- JUN01: 静的経路 172.16.20.0/24 → 172.16.10.10(SRV1 の奥のサーバの網)・172.16.99.0/24 discard(検証用・外へ出さない)。
  サーバの網のインターフェース(et-0/0/1)は OSPF に入れない(direct の経路を export する理由を作る)。
- FRR1(ISP)が送る経路= 0/0(default-originate)・203.0.113.0/24・198.51.100.0/24・198.51.100.128/25・192.0.2.0/24・
  198.18.0.0/15・10.200.0.0/16・192.168.50.0/24・100.64.0.0/10・172.31.0.0/16(172.16/12 の内側。PoC の後に足した)。
- RAM= vJunos EVO ×2+FRR ×2 ≈ 15.2GB。

### 8.2 課題(案)

初めの状態= J0 の範囲は組んである(アドレス・OSPF・静的経路・JUN02 と FRR1 の eBGP のセッション。ポリシーは何も無い)。

| 課題 | 求めること | 学ぶ要 | 罠(書かない・ヒントの 3 段目まで) | 確かめ |
|---|---|---|---|---|
| J1-1 | JUN01 から OSPF へサーバの網 2 つ(direct の 172.16.10.0/24・静的の 172.16.20.0/24)だけ。後者は metric 20。172.16.99.0/24 は出さない | export・from の AND・term・metric | from の無い orlonger 1 本だと 172.16.99.0/24 が漏れる | JUN02 の外部 LSA が 2 つちょうど・metric |
| J1-2 | JUN02 から OSPF へ既定経路を、ISP から受け取っている間だけ。ほかの BGP の経路は入れない | from protocol bgp・既定経路の exact | `from protocol bgp` だけだと全部入る・静的の 0/0 では条件にならない | JUN01 の 0/0(OSPF/150・JUN02 から)・JUN02 の外部 LSA は 0/0 だけ・JUN02 の inet.0 の 0/0 は BGP だけ |
| J1-3 | JUN02 の ISP からの受け入れ= 既定経路と、/8〜/24 の公のアドレスだけ(私的・共有・検査用・/24 より長いものは拒む) | route-filter の型・最長一致・連鎖の終わりの既定(BGP は受け入れ) | 受け入れる term だけでは全部入る・/8-/24 の範囲は /0 を含まない(J1-2 が壊れる)・同じ term の route-filter は最長一致の 1 本で決まる | 受け入れ 4 つちょうど・残りは hidden(Rejected by import policy)・J1-2 が保たれる |
| J1-4 | JUN02 から ISP へは集約 172.16.0.0/16 だけを、自分の AS を 2 回足して(FRR1 で 65000 65000 65000) | aggregate・export・as-path-prepend・term の順 | 既定の export は BGP の経路しか出さない・後から足した term は reject の後ろ(insert)・寄与する経路が無いと集約は出ない | FRR1 が 10.0.23.1 から 172.16.0.0/16 だけ・AS パス・SRV1(172.16.20.1)から 203.0.113.1 へ ping |
| J1-5 | ISP からの 203.0.113.0/24 にだけ community 65000:100 と local-preference 200。ほかは今のまま | 属性を変える term・終端の動作なし・連鎖 | 連鎖の後ろに置くと前の accept で止まって届かない・隣の階層に書くと group の import が置き換わる | 203.0.113.0/24 だけ LP 200・community・J1-3 の結果が保たれる |

### 8.3 読み物(案。ファイル名の頭は 1x)

| ファイル | 中身 |
|---|---|
| 10-j1-map | 見取り図: ポリシーの効く場所(import= プロトコル → 経路表・export= 経路表 → プロトコル)・既定のポリシー(J0 の表＋BGP)・部品(policy-statement・term・from・then・終端の動作・流れの制御・属性の変更)・1 つの経路が連鎖 [A B] → 既定へ流れる :::walk・用語の表とたとえ・取り違えやすい点・盤面の分担 |
| 11-j1-policy-statement | 評価の順(term は上から・from の中は同じ種類 OR・違う種類 AND・終端の動作で止まる・終端が無ければ次の term → 次のポリシー → 既定)・policy の then(名前の無い最後の term)・insert・`test policy`(既定は accept と数える)・commit check の誤り・IOS の route-map(暗黙の deny)と XR の RPL(pass/drop・既定で drop)との対照・OSPF への export の設定例 |
| 12 実践 | J1-1・J1-2 |
| 13-j1-route-filter | 一致の型(exact・orlonger・longer・upto・prefix-length-range・through)・最長一致で 1 本に決まる(型が外れても他を見ない・walkup)・route-filter ごとの動作・prefix-list(exact だけ)と prefix-list-filter・IOS の ge/le と XR の prefix-set との対照 |
| 14 実践 | J1-3 |
| 15-j1-ospf-bgp | OSPF へ(外部 type 2・metric 0 が既定・type 1・BGP の既定経路を条件つきで)・BGP の最小の設定(autonomous-system・group・type external・peer-as・neighbor。BGP の単元の前なので行の意味だけ)・BGP の既定(`Default eBGP mode`・PTX の注記)・拒んだ経路は hidden・group と neighbor の階層(下が置き換える)・属性の変更・集約(preference 130・次ホップ Reject・寄与する経路)と prepend |
| 16 実践 | J1-4・J1-5 |
| 17-j1-appendix | 一致の型の早見表・test policy の注意・walkup・確かめのコマンドの早見表・調べる場所 |

### 8.4 実機で確かめたこと(26.2R1.7-EVO・記録 `poc/junos/expJ1-*.log`・2026-11-14)

| 論点 | 結果 | 公式 |
|---|---|---|
| ポリシーなしの eBGP | 受け取り 9 本すべて active・FIB にも入る(forwarding-table)・広告 0。`show bgp summary` に `Default eBGP mode: advertise - accept, receive - accept` | 表 4(BGP の既定)＝一致。★PTX の既定(BGP User Guide 2026-07 版 p.500〜502= 旧い頁と同文)= `junos-ptx-series-default`(term t1/t2= BGP の inet.0・inet6.0 に `no-install-to-fib`・t3= `load-balance per-packet`)を `routing-options forwarding-table default-export` で当て、BGP の経路を FIB に入れない。**実機(26.2R1.7-EVO・ptx10001-36mr)では食い違う**: 同じ名前のポリシーは `default-export` で当たっているが中身は `term t1 then load-balance per-flow` だけ・BGP の経路 10 本が forwarding table に user で入る・JUN02 から ping も通る(記録 expJ1-ptx.log)。文書が旧い PTX(Junos OS)の記述のままか、Evolved／仮想機の差かは文書から決められない → 2026-11-14 ユーザに報告 → **同日ユーザ決定= 注記だけ**(出題に使わない・読み物の付録に文書と実機を並べ、版を書く。手で文書どおりの状態を作る「やってみる」も載せない。J1 の課題は FIB の入り方に依らない) |
| BGP のライセンス | commit と show で `requires 'BGP' license` の警告・動く | (OSPF と同じ扱い) |
| OSPF への export の既定 | 外部 LSA type 2・metric 0・tag 0。JUN02 で OSPF/150 | OSPF User Guide(未入手) |
| `then metric 20`＋`external type 1` | type 1・metric 20 | 同上 |
| from の無い `then accept` を OSPF へ | direct・static の 3 本が外部に(OSPF の IF の経路・Local・別の表の経路は出ない) | — |
| export の並び | `set protocols ospf export X` は並びの後ろへ足す(`export [ A X ]`) | — |
| 終端の動作が無い term | 次の term へ(metric 77 を付けて次の term で accept) | p.318〜319 |
| term の順 | 後から足した term は末尾。`insert … before` で前へ | — |
| 未定義のポリシー・prefix-list | commit check で `Policy NO-SUCH-POLICY referenced but not defined`・`… prefix-list referenced (in term t) but not defined` | — |
| BGP の既定経路を OSPF へ | ISP の group を deactivate すると JUN01 の 0/0 が消える(LSA の age 3600)・戻すと 40 秒以内に戻る | 「Example: Configuring a Conditional Default Route Policy」(p.43) |
| `test policy` | どの term にも当たらない経路も accepted に数える・inet.2・inet.3・mgmt_junos の表まで数える | p.764「always uses accept as the default policy」 |
| 一致の型 | exact・orlonger・longer・upto /16・prefix-length-range /16-/24・prefix-list・prefix-list-filter orlonger を受け取った経路で照合(期待どおり) | p.318 前後 |
| 最長一致 | `198.51.100.0/24 exact`＋`0.0.0.0/0 upto /25` で 198.51.100.128/25 は拒まれる(型が外れても 0/0 を見ない)・192.0.2.0/24 は受け入れ | p.318〜319「stops evaluating other prefixes, even if the match type fails」・walkup |
| import で拒んだ経路 | hidden・`Hidden reason: Rejected by import policy`・`receive-protocol bgp … hidden` で見える | — |
| 隣の階層の import | group の import を置き換える(足し算でない)。ONLY-DOC(受け入れ 1 term だけ)で 9 本すべて active に戻った | p.28「A peer-level import or export statement overrides a group import or export statement」(global → group → peer の順に下が置き換える)＝一致 |
| 属性の変更 | from の無い term で community add・local-preference 200 → 既定で受け入れ(Preference 170/-201) | — |
| export と term の順 | REST(reject)の後ろに足した AGG は効かない → insert で前へ → 出る | — |
| 集約 | Aggregate/130・次ホップ Reject・寄与する経路(OSPF の 2 本)・広告の AS パス `65000 65000 [65000] I`・FRR1 で `65000 65000 65000`・aggregated by | — |
| 連鎖 | `import [ A B2 ]` で A の最後の `then accept` があると B2 の reject は効かない・消すと効く。`next policy` は次のポリシーへ | — |
| from の中 | `protocol [ static aggregate ]`(OR)と route-filter(AND) | — |
| route-filter ごとの動作 | `198.51.100.0/24 exact accept`＋`198.51.100.0/24 longer reject` で /24 を受け入れ /25 を拒む(同じプレフィックスは上から) | p.319「the action specified with the prefix is taken」 |
| through | `198.51.100.0/24 through 198.51.100.128/25` で /24 と /25 の 2 本 | — |
| walkup | `set policy-options defaults route-filter walkup` を入れると、最長一致の罠の例(LM)で 198.51.100.128/25 も受け入れる(入れないと拒む・PoC 3) | p.319 の注記・p.333 |
| 同じ term の route-filter・prefix-list・prefix-list-filter(2026-11-15) | 3 つは AND でも別々の OR でもなく、1 つの並びとして最長一致で引かれる(いちばん長い行の型と行の動作で決まる・型が外れたら term は外れ)。MIX1 `route-filter 198.51.100.0/24 exact`＋`prefix-list-filter {0/0} orlonger`= /25 だけ拒む・ほかは受け入れ(AND なら全部外れ・OR なら /25 も入る)。MIX2(逆の組)・MIX3(prefix-list＋route-filter。192.0.2.0/24 を受け入れ= AND でない)も同じ。MIX4 `route-filter 0/0 prefix-length-range /8-/24`＋`prefix-list-filter {10/8} orlonger reject`= 10.200.0.0/16 拒む・192.0.2.0/24 受け入れ。MIX5(動作を route-filter 側へ)も同じ。test policy と実際の import の両方・walkup なし。JNT-02 のユーザ解答(5 つの範囲の並びで同じ形)も受け入れ 4・hidden 6(記録 `poc/junos/expJ1-rf-mix*.log`・`expJ1-jnt02-answer.log`) | p.61「If you configure a policy that includes some combination of route filters, prefix lists, and source address filters, they are evaluated according to a logical OR operation or a longest-route match lookup」= AND でないことは文書どおり。OR か最長一致かは文書に無く、実機は最長一致(MIX1 で /25 を拒む= 単純な OR でない)。p.318 は route-filter どうし・p.399 は prefix-list の中・Day One にも記述なし。当初「文書に記述なし」としたのは p.61 の見落とし(2026-11-15 ユーザの依頼で KB を探した際に見つけて訂正。KB に該当記事なし) |
| test policy の範囲 | 経路表で使われている経路だけを評価する。import で拒んだ(hidden の)経路は評価しない → 試すときは import を外す(`deactivate`)| — |
| 模範解の E2E(2026-11-14) | 初めの設定(startup-config)から 5 課題とも誤答で FAIL → 模範解で PASS・本採点 100/100。誤答= J1-1 from の無い orlonger・J1-2 from protocol bgp だけ・J1-3 受け入れる term だけ／既定経路の term 抜け・J1-4 reject の後ろの term・J1-5 連鎖の後ろ／隣の階層／from 抜け(記録 `poc/junos/e2e/`) | — |
| 端から端 | SRV1 の 172.16.20.1 から 203.0.113.1 へ ping 3/3 | — |

### 8.5 残り

- 資料: 2026-11-14 受領(bgp.pdf 2026-07・ospf.pdf 2026-06・PTX の例の頁・Day One の policy/filter 本)。裏どり= OSPF の既定の export は reject(ospf p.596)・連鎖は accept/reject で終わる(同)・export で from を省くと思わぬ結果(同 p.597)・RFC 8212 の振る舞いは既定で入れない(bgp p.536 付近・`defaults ebgp no-policy`)・受け取った経路を同じ AS の eBGP へ返さない(advertise-peer-as)。
- PTX の既定の食い違い(8.4)= 2026-11-14 ユーザ決定で注記(付録)。
- 盤面の資材= 初めの設定 jun01/jun02.startup.cfg・task.md/task.en.md・grading.j1t1〜5.yml(下書き・E2E 前)。
- 2026-11-14 執筆済み= 読み物 10〜17(日英・見取り図に :::walk・設定例はすべて課題と値を変えて実機で入れたもの= `poc/junos/expJ1-examples*.log`)・
  learn.yml(5 課題・ヒント 3 段・確かめ方の例・模範解)・用語集 junos.yml に 14 語(community は SNMP の語と表記が重なるので scope を J1 のページに)。
  実践ページの前置きから「コマンド例は意図して示していません」を外した(CLAUDE.md の規定・J0 の実践ページにも効く)。
- SRV1 は FRR のイメージのサーバ役 → ワークスペースのコンソールが vtysh になり、送信元つきの ping が打てない →
  clab のノードのラベル `ccnp-role: host` を足した(lab_console.py・clab_ops.py の node_is_host。図ではホスト・コンソールは bash。採点の exec と起動の判定は FRR のまま)。
  サードパーティのイメージ(network-multitool)の取り込みは自動モードの判定で止められたので使わない。
- 実機の注意: 作り直し(deploy --reconfigure)で JUN01 が vrnetlab の `starting` のまま 10 分以上 unhealthy になったことが 1 回(同じ初めの設定で前後は 95 秒で上がる)→ 作り直しで回復。
- 実機の注意(2026-11-15): ホストの再起動の後に作り直した JNT-02 で、JUN02 だけが起動から約 50 分、仮想機ごと詰まった(ホストの qemu が 3〜4 コア分を使い続け・中の負荷平均 128・その間 messages に何も出ない・BGP は 00:20 に Hold Timer Expired で落ち Connect のまま・コンソールは使い物にならない遅さ)。JUN01 は同じ像・同じ時刻の起動で平常。何もせず 00:55 ごろに収まり、負荷・応答とも JUN01 並みに戻った(BGP も張り直し)。原因は不明。再発したら、まず中から `request system reboot`(JUN01 と結線はそのまま)、だめなら作り直し。続いて 00:58 に szk-cl01 の VM ごと止まった(VMware Workstation の vmx が記録なしで終了)。vmware.log では VMware は自前の VMM で動作(VBS 0・Monitor Mode CPL0)= Hyper-V 経由の遅さではない。ゲストの記録には OOM・I/O エラー・lockup は無く、`workqueue … hogged CPU` の警告だけ(vCPU が回されない時間があった)。ホスト側の原因は未確定(Windows のイベント ログ待ち)。
