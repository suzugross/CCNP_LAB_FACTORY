# 読み物の用語集(BL-260)— 本文の専門用語にカーソル(スマホはタップ)で説明を出す＋用語集ページ

2026-11-01 ユーザ要望。読み物(courses/ の教材・訳文の読み物の両方)の本文に出てくる専門用語を、その場ですぐ引けるようにする。

## 1. 要件(ユーザと確認済み・2026-11-01)

1. 本文の専門用語にカーソルを合わせると、短い説明がふわっと出る。~~CCNA レベルの語は対象外~~ → ★2026-11-08 転換: 単元で使う基礎の語なら CCNA の範囲でも載せる(§13)。
2. **本文には目印を付けない**(下線・色・アイコンなし)。合図はカーソルが乗った時の形(`cursor: help`)だけ。
3. 用語をまとめて引ける**用語集ページ**を別に持つ。
4. 用語は **1 か所のデータ(辞書)** にまとめ、カーソルの説明も用語集ページもそこから作る。
5. **スマホでも読む**(ポータルと Drive の持ち出し) → カーソルが無い端末は語をタップして出す。

## 2. 辞書

- 置き場: **`glossary/*.yml`**(リポ直下・公開側・全教材で共通の 1 つ)。分野ごとにファイルを分けるだけで、中身は 1 つに合わさる。
  本ごとの追加は `<src>/glossary.yml`(任意。非公開の本だけの語を非公開側に置ける)。
- 説明文は自分たちで書く(訳文ではない)ので公開側でよい。書名・章題・出典は書かない(CLAUDE.md 読み物 §4)。
- 書式(正典は `topologies/glossary.py` の docstring):

```yaml
- id: evi                          # 英小文字・数字・ハイフン。全辞書で一意
  term: EVI                        # 見出し語。日英で違えば {en: …, ja: …}
  full: {en: EVPN instance, ja: EVPN インスタンス}   # 略語の正式名(任意)
  aka: [EVPN instances]            # 本文で拾う別の表記(任意)。見出し語と正式名は書かなくても拾う
  def: {en: "…", ja: "…"}          # 1〜3 文。`code` と **太字** が使える
  see: [evpn, vrf]                 # 関連語(任意)
  books: [xr]                      # この本だけで拾う(任意)。同じ略語が本によって別の意味の時
  scope: ["b*-m11-*"]              # このページだけで拾う(任意・ファイル名の glob)。「種類 1」のように単元をまたぐと別物になる表記用
```

- **DB サーバにはしない**: ページは静的 HTML で、Drive に持ち出してスマホで開く。問い合わせ先が要る作りだと持ち出し先で動かない。
  ビルド時に辞書を読み、ページごとに「そのページで使う語」だけを埋め込む。

## 3. 本文から拾う規則(ビルド時・原稿の Markdown には何も書き足さない)

- 拾わない場所: `pre`・`code`(console・config・インラインのコード)・見出し(h1〜h6)・リンク・ボタン・図(svg)・
  囲みのラベル・設定例の見出し・ナビ帯。
- **最長一致**(「EVPN-VPWS」が登録されていれば「EVPN」より優先)。
- 英数字で始まる・終わる表記は、前後が英数字でないこと(「L2VPN」の中の「VPN」は拾わない)。ハイフンでつながった英数字も
  同じ語の一部とみなす(「RR-LINK」の「RR」・「PE-CE」の「PE」は拾わない。拾いたい複合語はその形で登録する)。
- 大文字だけの表記(略語)は大文字小文字を区別する。小文字を含む表記(route target など)は区別しない。
- 英語の複数形(PEs・route targets・communities)も拾う。
- 日本語の表記の空白はあってもなくてもよい(「ルート ターゲット」=「ルートターゲット」)。原稿の行の折り返しも空白として扱い、
  日本語の文字どうしの間に原稿の改行が入っていても拾う(「疑似回線の\nラベル」)。
- 太字などの書式の境目はまたがない(「**種類 1** の経路」の「種類 1 の経路」は拾えない)。
- 同じ語はページ内の全部の出現で引ける(目印が無いので、どこで引いても出る方が自然)。

## 4. 表示

- **PC**(`hover: hover`): 語の上にカーソルを 0.35 秒置くと出る。語と吹き出しから外れて 0.25 秒で消える。
  クリックで固定。スクロールで語がカーソルの下に来ただけでは出さない(読んでいる最中に勝手に出ないように)。
- **スマホ**(`hover: none`): タップで出す。外側をタップ・Esc で閉じる。
- 吹き出しの中身: 見出し語・正式名(日本語版では英語の正式名も添える)・説明・関連語(押すとその語に差し替わる)・「用語集で開く」。
- 吹き出しを出している間だけ、その語に薄い背景を付ける(どの語の説明かを示す。閉じれば消える)。
- 日英切替: 吹き出しは表示中の言語で出す。言語を切り替えたら閉じる。

## 5. 用語集ページ(`reading/<key>/glossary.html`)

- その本に出てくる語(＋その関連語)を、英語の見出し語のアルファベット順に並べる(日英 2 版で並びをそろえる)。
- 絞り込みの入力欄(語・正式名・説明で絞る)と、頭文字への飛び先。
- 語ごとに「出てくるページ」(ページ → 節へのリンク)= 本の巻末索引の逆引き。
- 導線: 目次(index.html)の題の下と、ナビ帯の一覧の先頭(目次の隣)。

## 6. 持ち出し(束ね版)

- 1 枚に辞書と吹き出しの JS を埋め込む(外部参照ゼロを保つ)。用語集は 1 枚の末尾に節として付ける(逆引きは 1 枚の中のページへ)。
- 持ち出し先の閲覧アプリでスクリプトが動かない場合は、吹き出しが出ないだけで本文は読める(末尾の用語集は読める)。

## 7. 載せる語の基準と説明の書き方

- ~~載せない: CCNA レベル(VLAN・トランク・サブネット・MAC アドレス・ARP・ACL・NAT・DHCP・OSPF の基本など)。~~
  ★2026-11-08 転換(ユーザ指示): **単元で使う基礎の語は、CCNA・CCNP Enterprise の範囲でも載せる**(§13)。載せないのは製品名・機器名・ラボ ID。
- 載せる: その本の範囲で、CCNP の読者が引きたくなる語(略語・SP の用語・XR 固有の用語・規格名)と、単元で使う基礎の語。
- 説明は 1〜3 文。日本語版は本文と同じく読みやすい日本語(常体の簡潔な文)、英語版は簡潔な英語。
- 根拠: 本文(PoC と実機で確かめた内容)と Cisco 公式・RFC/IEEE/ITU-T の規定に沿う(作問の裏どりと同じ信頼順)。
  本文の説明と食い違う説明は書かない。確かめられない細部は書かない。

## 8. 段階

| 段階 | 中身 | 状態 |
|---|---|---|
| P1 | 仕組み(拾う・吹き出し・用語集ページ・束ね版)＋ M11 の語で試す | 完了(2026-11-01)・ユーザの試用待ち |
| P2 | XR トラック全体(M0〜M10)の語 | 未着手 |
| M12 | M12(QoS とデータプレーンの保護)の語。P2 より先に作った(ユーザ指示) | 完了(2026-11-08)・Drive 同期はユーザの了承待ち。記録は §12 |
| P3 | 訳文の読み物(非公開の本)の語。本だけの語は `<src>/glossary.yml` | 未着手 |
| 将来 | ポータルに全教材を横断する索引 | 未着手 |

## 9. 道具

- `python3 topologies/gen_reading.py glossary` … 辞書の検査(id の重複・表記の衝突・説明の欠け・関連語の宛先)。
- `python3 topologies/gen_reading.py glossary --src <本> --unknown` … 本文に何度も出るのに辞書に無い略語の一覧(辞書を育てる時の候補)。

## 10. P1 の記録(2026-11-01)

- 辞書: `glossary/l2vpn.yml` 75 語・`glossary/sp-basics.yml` 15 語(計 90 語)。M11 の読み物 7 ページ(日英)から下書きし、
  全語が M11 の本文の日英両方に当たることを確かめた。CCIE の読み物(非公開)では 9 語が当たり、すべて同じ意味(誤爆なし)。
- 裏どり: 製品ごとの記述(EVI からの RD/RT の自動生成・L2 属性の拡張コミュニティの MTU 0・`lacp device-id`/`lacp system mac`・
  `replication-type ingress` と Incomplete・`show l2vpn atom vc`・CC の既定 10 秒・`load-balancing-mode single-active`)は
  M11 の本文(XRT-11/12 の実測)にある。本文に無いのは IRB の「IOS XR は BVI・IOS XE は BDI」だけで、Cisco 公式の設定ガイド
  (ASR 1000 IOS XE 17「Configuring Bridge Domain Interfaces」・NCS 5500 IOS XR 7.9「Configuring Integrated Routing and Bridging」)
  で確認した。規格の数字(ESI 10 オクテット・CFM のレベル割り当て・CCM 3.5 倍・DF の V mod N・PW タイプ 4/5・control word・
  Ethernet tag の MAX-ET・Y.1731=G.8013)は RFC/IEEE/ITU-T の規定どおり。
- 外した語・表記: 裸の「type 1/3/4」(PW タイプ・ESI タイプと衝突)・RPL(XR の route-policy と衝突)・裸の system ID(IS-IS)・
  ES・label・RR(「RR-LINK」に当たった)・delay measurement(SR の性能測定と衝突)・EFI(展開が不確か)。
  単元をまたぐと別物になる表記を持つ語は `scope: ["b*-m11-*"]`(DF は b0 の「DF ビット」を避けて b9 だけ)。
- 本文で気づいた点(2026-11-02 ユーザの依頼で 4 件とも直した): b2 §1.2 と b4 の実践の「付録で E-LAN・マルチホーム」は追補ページ(b7・b9)へ
  移った後の古い参照。bb §2.2「EFP の上の MEP は up」と §3.3「EVPN では EFP に置けるのは down MEP だけ」が食い違って見える
  (up-mep の説明からこの点は外した)。ja の「顧客」(b0〜b4)と「お客さま」(b7〜bb)の揺れ。b6 から b7/b9/bb へのリンクは
  束ね版では行き先が無い。
  直し方: b2・b4 は追補(E-LAN・マルチホーム・OAM)と付録(E-Tree・G.8032・802.1ah)を分けて書いた。bb §2.2 は「このラボ(EFP を LDP の
  疑似回線にクロスコネクトする形)では up MEP」と測った形に限り、EVPN は §3.3 を指した(新しい事実は足していない)。ja の
  「お客さま」は本全体の主流の「顧客」にそろえた(b7・b9・bb)。束ね版のリンクは gen_reading の `_bundle_links` で、同じ 1 枚の
  ページは `#pg<n>` へ付け替え、別の 1 枚のページは文字だけ残すようにした。

## 11. P2 の再開手順(2026-11-02 記録・着手はユーザの指示待ち)

**範囲**: XR トラックの M0〜M10(`courses/xr/{en,ja}/` の 00〜a6 のページ。実践ページも本文として拾われる)。
M11 は P1 で済み。sp-basics の 15 語は M8〜M10 にも当たっているが、M3 OSPF・M5 RPL・M6 BGP・M7 高可用性は当たる語が 0。

**辞書のファイル分け(案)**: 単元のまとまりごとに 1 ファイル。`xr-basics.yml`(M0〜M2: XR の設定の管理・commit・管理プレーン)、
`igp.yml`(M3〜M4)、`bgp-rpl.yml`(M5〜M6)、`ha.yml`(M7)、`mpls.yml`(M8 と Unified MPLS)、`sr.yml`(M10)。
M9 は sp-basics にほぼ入っているので、足りない語だけ sp-basics か mpls に足す。

**手順**
1. 候補を出す: `python3 topologies/gen_reading.py glossary --src courses/xr --unknown`(略語だけ。小文字の用語は本文を読んで拾う)。
2. 単元ごとに下書きする(エージェントに単元ごとに分けて渡すと並行できる)。指示の要点は P1 と同じ:
   - 書式は glossary.py の docstring。id は全辞書で一意。既存の 90 語と表記を重ねない(検査が「表記の衝突」で知らせる)。
   - 拾う規則(最長一致・ハイフンも語の一部・大文字だけは区別・複数形・日本語の空白と改行のゆれ・太字の境目はまたがない)を
     前提に、本文に実際にある形で表記を選ぶ。単元をまたぐと別物になる表記は `scope:`。
   - ★(2026-11-08 転換)単元で使う基礎の語は CCNA の範囲でも載せる(§13)。製品名・機器名・ラボ ID は載せない。一般語(クラス・キューなど)は `scope:` で絞る。
   - 説明は 1〜3 文・日英で同じこと・常体。本文(実測)と食い違わない。本文に無い製品の記述は Cisco 公式で確かめ、
     規格の数字は RFC 等の規定どおり。不確かなものは書かずに報告させる。書名・課題番号・機器名は書かない。
   - 検査: 全語が日英の本文に当たるか(0 回の語は関連語の宛先でなければ外す)。
3. 確認: 製品ごとの記述を本文と突き合わせ、本文に無いものは公式で裏どりして §10 と同じ形で記録する。
4. `scripts/course.sh xr build` → `python3 topologies/gen_reading.py glossary --src courses/xr`(問題なし・全語が本文に出ること)。
   単元をまたいだ誤爆が無いか、ページごとの当たり方を見る(P1 では M0〜M2 の VRF の説明が L3VPN 寄りだったので一般化した)。
5. `scripts/course.sh xr sync`(ユーザの了承を得てから)。CCIE の読み物にも当たる語が増えるので `scripts/read.sh build private/reading/ccie-ei` も。

**衝突に注意する表記(分かっているもの)**
- **LSP**: M4 の IS-IS では link state PDU、M8 以降では label switched path → 別の語にして `scope:` でページを分ける。
- **RPL**: M5 では routing policy language、M11 の付録では G.8032 の ring protection link(P1 では登録を避けた)→ `scope:`。
- **IS**・**DIS**・**NET**・**ATT** など IS-IS の短い略語: 英語の地の文の一般語に当たらないか確かめる(IS は避ける)。
- **SID**・**FEC**: SR と LDP で意味の層が違う(FEC は P1 の「FEC 128」と重ならないように)。

**候補(2026-11-02 の --unknown の上位から、CCNA レベル・製品名・ラボの名前を除いたもの)**: IGP・LSP・SID・BFD・PCE・NET・SPF・TLV・
DIS・ATT・ABR・CEF・EXP・TI-LFA・LDP-IGP(同期)・AFI・TACACS・AAA・HMAC・OAM(P1 で ethernet-oam はある)。ほかに小文字の用語
(commit・rollback・configuration session・SRGB・SRLB・adjacency SID・BGP-LU・NSR・GR など)は本文から拾う。

## 12. M12 の記録(2026-11-08)

ユーザ指示「M12 の辞書も作って」で、P2 より先に M12(`d0`〜`d6`)の語を作った。

- 辞書: `glossary/qos.yml` 44 語・`glossary/dp-security.yml` 14 語・`glossary/mpls.yml` 6 語(計 64 語。全体で 155 語)。
  `mpls.yml` は P2 の「ファイル分け(案)」の `mpls.yml` を先に作ったもの(PHP・explicit null・LSP・TE・RSVP・RSVP-TE)。
  検査= 155 語すべてが xr の本文に出る・新しい 64 語はすべて日英の両方に出る・表記の衝突なし。M12 の 7 ページで 1,199 か所。
- ★CCNA の範囲の例外(ユーザ判断): DSCP・PHB・ポリシング/シェーピング・信頼の境界は CCNA の範囲にも入るが、QoS の単元で
  頻出なので載せた(`qos.yml` の冒頭に記録)。ToS・IP Precedence・ACL・Null0・DDoS・TTL・IGP・CEF・FIB・ECMP は載せていない。
- scope と books:
  - `scope: ["d*-m12-*"]`: uniform/pipe/short pipe のモデル(「pipe」「uniform」は一般語)・RTBH の起点(「trigger」「起点」)・**LSP**。
  - **LSP** は M8・M10 のページで IS-IS の LSP(link state PDU)と混ざって出る(82・a0・a2 は両方の意味)。いまは M12 だけで拾う。
    P2 で IS-IS の LSP を別の項目にするときに、ページごとの分け方(または表記での分け方)を決める。
  - `Bc`(バースト)は `scope: ["d2-*"]`、`BC`(DS-TE の Bandwidth Constraint)は `["d6-*"]`(小文字を含む Bc は大文字小文字を区別しないので、
    同じページにあると BC に当たる)。CT・割り込み(preemption)も `d6` だけ。適合・超過・違反(conform/exceed/violate)は `d2`・`d3` だけ
    (d6 に一般語の「exceed」がある)。
  - EXP の項目は `TC` も拾うが、CCIE の読み物では TC が STP のトポロジ変更(TC BPDU)なので `books: [xr]`。
- 載せなかった表記: `Be`(英語の「be」に当たる)・「整形」(一般語。シェーピングの意味で 7 回出るが、ほかの本で誤爆しうる)・
  `class-default`・`bandwidth remaining`・`priority level`(地の文にはコードとしてしか出ない)。
- M12 以外で新しい語が当たったページ: PHP・explicit null・EXP(M8・M9・M10・C0)、TE(M4 の「Traffic engineering … wide metrics」・M10)、
  RSVP-TE(M10)、ポリシング(M2 の LPTS・CoPP)。どれも同じ意味。ポリシングの説明は「決めた速さ(顧客との契約など)」に一般化した。
  CCIE の読み物では TE(DMVPN の「トラフィックエンジニアリング」)と DSCP が新たに当たり、意味は同じ。
- 裏どり:
  - 製品の挙動(方策が無いときの EXP の写り方・PHP で付け替えが消える・explicit null・qos-group の向き・1 クラスの印の数・
    `priority level 1` とポリサ・階層のポリシー・WRED の要件・uRPF の厳格/緩い/`allow-default`・インフラ ACL の 4 部構成・RTBH・
    IOS XR の uRPF が Null0 への再帰を参照しないこと・`set next-hop discard`・ABF が先に効くこと・FlowSpec の controller/client・
    MACsec の対応がハードウェア依存・CBTS/PBTS・RDM が IOS XR の DS-TE の既定)は M12 の本文(XRT-14 の PoC と公式文書)にある。
  - 規格(エージェントに RFC の本文を読ませて確認): RFC 3270(E-LSP は 8 つまでの BA・L-LSP はラベルで PSC・Short Pipe は Pipe の
    「optional variation」)・RFC 3168(ECN 2 ビット・CE を付けてよい= MAY・端末は 1 つ落ちたときと同じ反応)・RFC 2474 4.2.2(Class
    Selector は xxx000・IP Precedence との部分的な互換)・RFC 3032 2.1(0= IPv4 explicit null・2= IPv6 explicit null・3= implicit null)・
    RFC 5462(EXP → TC)・RFC 2698(trTCM= PIR/CIR・PBS/CBS・3 色)。
  - Cisco 公式(検索で確認): ASR 9000 の Modular QoS Command Reference「Deployment Scenarios Commands」(`random-detect discard-class`)と
    NCS 5500 の QoS Classification Commands(`set discard-class` は入力だけ)・Cisco Wireless MACsec On-Prem Deployment Guide(MKA は
    IEEE 802.1X-2010 で定義・EAPOL の上)・IOS の QoS Congestion Management Overview(LLQ は CBWFQ に 1 つの厳格な優先キューを足す)。
  - 確かめていないので書かなかった: preemption で奪われた LSP がどうなるか(張り直しの手順)。
- 本文で気づいた点(2026-11-08 ユーザの依頼で直した): d0 §2.5 は「RFC 3270 は 3 つのモデルで整理しています」と書くが、RFC 3270 2.6.1 は
  「These two models are the Pipe Model and the Uniform Model」で、Short Pipe は Pipe の optional variation(2.6.2.1)。辞書の説明は
  RFC に合わせて「パイプ モデルの変形」とした。また RFC 5462 は E-LSP の展開形を「Explicitly TC-encoded-PSC LSP」に変えている
  (本文には展開形が無いので影響なし)。
  直し方: d0 §2.5 の一文を日英とも「RFC 3270 は 2 つのモデル(ユニフォームとパイプ)で整理し、パイプの変形としてショート パイプも
  定めている。このページでは 3 つを並べて『3 つのモデル』と呼ぶ。TTL にも同じモデル(RFC 3443)」に変えた。RFC 3443 も 1 節で
  「two models … Pipe and Uniform」「A Short variation of the Pipe Model」と書き、3 節で 3 つの TTL の処理を並べているので、§2.7 の
  「同じ 3 つのモデル」と見出し・§2.8 はそのまま。


## 13. 方針の転換: 基礎の語も載せる(2026-11-08)

- ユーザ指示: 「CCNA や CCNP Enterprise でやったところだから、という理由で内容を省かない」(教材の本文の方針・CLAUDE.md §6)を受けて、
  用語集の「CCNA レベルは載せない」も改めた(ユーザ了承)。**単元で使う基礎の語なら載せる**。
- 最初の適用= M12(`d00`〜`d6`)。16 語: `qos.yml` に クラス(qos-class)・キュー(qos-queue)・スケジューラ(qos-scheduler)・FIFO・輻輳(congestion)・
  ToS・IP Precedence、優先キューに「優先の列」を足した。新しい `basics.yml` に TCP・TTL・ACL・Null0・DDoS・ECMP・FIB・CEF・IGP。計 171 語。
- scope: クラス・キュー・スケジューラ・IP Precedence は `["d*-m12-*"]`(一般語。CCIE の読み物では「クラスタ」「アドレスのクラス」「入力キュー」に当たる。
  英語の `precedence` は AF の drop precedence と「takes precedence」に当たるので aka にしない)。略語の 9 語は絞っていない(どの単元でも同じ意味。
  TTL は M11 の「イーサネットのフレームには TTL が無い」にも当たり、意味は合う)。
- 検査= xr は 171 語すべてが本文に出る・CCIE の読み物は scope の語に当たらない(TCP 52・IGP 43・CEF 22 などは同じ意味)。両方の本をビルドし直した。同日 xr を Drive へ同期(ユーザ了承・CCIE の読み物は手元のビルドだけ)。
- 残り: M0〜M11 の基礎の語は、その単元を書き直す・追記する時(BL-257 の 2 周目と P2)に足す。
