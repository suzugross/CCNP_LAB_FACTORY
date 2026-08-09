# 出題履歴 — いつ何を出題し何点だったか

出題フロー(`.claude/skills/quiz/SKILL.md`)が更新する台帳。**新しい行を表の一番上に追記**する。

- **状態**: `出題中` → `採点済` → `撤収済`。provision 時に `出題中` で1行追加し、以後は同じ行を更新。
- GEN 系は seed まで書く(例: `GEN-CHAIN-9812`)。variant があれば ID の後ろに `(bfd)` 等。
- 得点は最終得点。途中採点の経過はメモに(例: `81→100`)。
- 用途: 重複出題の回避・難易度調整・チャットまたぎでの「いま出題中の問題」の復元。

## 履歴

| 出題日 | 問題ID (variant/seed) | 難 | 状態 | 得点 | メモ |
|--------|----------------------|----|------|------|------|
| 2026-08-08 | GEN-REDISTRO-11153 (stale_filter) | 4 | 撤収済 | 100 | ★**BL-099 問題パック PACK-20260808 の Q4**(パック機構の実機E2E初回)。基線65→**100を一発**。RT02 `router rip` の `distribute-list 10 out`(参照先 `access-list 10 deny any`)撤去の最小手。既存の設計側機構(両境界 `distance ospf external 180`・タグ衛生route-map)は正しく温存。指摘= **`access-list 10` の定義が残骸として残置**(現在は無参照で無害だが、番号ACLは再利用されやすく後日の無言全遮断の地雷。採点は静的経路の残置しか見ないため通る) |
| 2026-08-08 | 紙面 20260808-009 (pbr・pack seed 543958915) | 4 | 採点済 | 正解(A) | パック Q3。7択(A〜G)。route-map に match が無く全吸引→`match ip address ACL-A` に戻す解を選択。**PBRのmatchにprefix-listを書くとmatch節が無視される**罠(B)を回避・ワイルドカードの被覆(0.0.6.255=32/34/36/38・0.0.16.255={32,48}・0.0.2.255は38に届かず)も正しく処理。★**出題事故**= レンダラが選択肢をA-F決め打ちで**Gが枠外・選択不能のまま出題**(修正済) |
| 2026-08-08 | 紙面 20260808-008 (urpf・pack seed 543958915) | 4 | 採点済 | 正解(D) | パック Q2。検証モード any(loose)=着信IF一致は見ない、を選択。除外根拠も的確(**参照ACLが未定義**でA/Fを落とす・経路表のOSPF学習でCを落とす) |
| 2026-08-08 | 紙面 20260808-007 (ring・pack seed 543958915) | 4 | 採点済 | 正解(C) | パック Q1。cause形=再配送リングの定常ループ。**一周して戻ったD EX(170)がiBGP(200)に勝つ**機構をAD比較で明示。A/E(遠回りでも到達する)・B/F(経路表に存在=広告は成立)の消去も設計意図どおり。指摘=Fの反証に「OSPF再配送の既定metric20」を持ち出したのは軸違い(正しくは経路表に載っている事実) |
| 2026-08-08 | GEN-BGPRR-80424 | 4 | 撤収済 | 100 | ★**BL-099 パック PACK-20260808 の Q5(差し替え後)**。当初 GEN-RADIUS-82368(FreeRADIUS構築)を選定してしまい、**ユーザ指示で「純粋なCisco問題のみ・TS中心」に方針確定**→`pack.sh replace` で入替(RADIUSは未出題のまま撤収)。基線55→**100を一発**。故障=**RT02 の OSPF に RT04 向けリンク `10.243.254.0/30` の network 文欠落**(BGP設定は初めから全て正しい=アンダーレイ障害が Lo0 ピアの iBGP を落とす型・RT04が孤立し5.5.5.5も伝播せず被害が広がる)。対処は当該1行追加のみ・既存のnetwork文流儀に合わせた・残骸ゼロ。補足=iBGPが上がらない時は `ping <peer Lo0> source <own Lo0>` を最初に撃つ |
| 2026-08-08 | GEN-DMVPN-20443 (i6_mode_tunnel) | 4 | 撤収済 | 90→100 | **i6初出**。監査型チケットからtransform-setのmode是正は自力一発(config完治)。90の残り10点=**稼働SAが旧Tunnelモードのまま**(transform変更は確立済みSAに遡及しない)→実機SA実測(hub側 {Tunnel,} 残存)を提示後、SA張り直しで満点。教訓=「configの復旧」と「稼働状態の復旧」は別チェック項目。※DMVPN未消化=u1/i4/i7/i8 |
| 2026-08-08 | 紙面 20260808-006 (v6redist・seed 20260808913) | 4 | 採点済 | 正解(B) | ★BL-098 初出題(shape=v6redist)。read形・kind=pl_one_side/world=hide_transit。**生きている参照チェーンの特定(MAP-IN→PL-EIGRP)＋ include-connected が拾う connected の識別＋常在の外部ルート**の3点を同時に要求する盤面を一発正答。デコイ O544(客先LAN両方を許可するが未参照)・PL-CORE(::/0 le 64 を EMAP01 経由で許可するが未参照)を回避。ping の非対称(NOROUTE / `.....`)から o2e 開通・e2o 閉塞も整合。★出題時ユーザ要望= トポロジ図を再配送系と同じ mermaid+リンク表へ(対応済) |
| 2026-08-08 | 紙面 20260808-005 (ospfv3pl・seed 806803756) | 4 | 採点済 | 正解(B) | read形・kind=none/dual_select=**「定義済み≠適用済み」罠**(AF空でghost3枚が無作用→基線が正解)。願望テーブルD・ghost自己適用A(8::/45がB..E包含の読み込み)・C を排除。3問連続正答(通算3勝2敗)。未参照=無作用/未定義参照=全許可 の対を解説済 |
| 2026-08-08 | 紙面 20260808-004 (ospfv3pl・seed 626297906) | 5 | 採点済 | 正解(D) | ★patch形(両掛けTS)初出題を正答。kind=le_off/dual_select。R3健全→in側PL-COREへ切り分け→`le 63` の長さレンジ欠陥を**能動検出**し `ge 64 le 64` 修理を選択(健全側を触るC・適用削除Bを排除)。**le弱点は受動(003)→能動(004)両通過=回復判定**・間隔を空けて定着確認継続。※出題直前にle_off盤面の錯乱肢重複バグ(le63再投入)を検分で発見→修正済 |
| 2026-08-08 | 紙面 20260808-021 (aaa・seed 6011) | 4 | 採点済 | 正解(D) | cause形・kind=src_iface_missing。無応答(約20秒)＋横浜側だけ全滅＋local口のみ生存から送信元の誤りと特定。★ユーザ指摘2件=①`show run`出力に**「(該当する行はない)」という説明文**を書いていた=道標そのもの(BL-088違反)②**ログイン不可の利用者に「昇格可」の行**を出していた=論理矛盾(昇格をログイン可否と独立に計算していた)→両方修正 |
| 2026-08-08 | 紙面 20260808-020 (aaa・seed 6011) | 4 | 採点済 | 正解(B) | ★**P1b fix 形の初出題を正答**。kind=enable_via_radius/world=server_frozen。昇格だけが失敗する症状＋千葉側にのみある `aaa authentication enable default group RADGRP enable` を特定し、サーバ台帳への登録(=サーバ側変更禁止に抵触)を排除して機器側の削除を選択 |
| 2026-08-08 | 紙面 20260808-019 (aaa・seed 6011) | 4 | 採点済 | **問題不備(解答A=妥当)** | ★**P1b patch 形の初出題＝出題側の欠陥をユーザが指摘**。要件は「作業の途中で**運用者の接続**が切れないこと」＋シナリオ「作業は**遠隔から**」だけだったのに、正解(B)の根拠は**緊急用ローカル口のコンソール経路**の保全にあった=**問題文に無い制約**。実測でも A 投入後に**VTY は全て維持**され失われるのは console のみ→**A は書かれた要件を全て満たす**。→修正= patch 形の要件に**守るべき経路を漏れなく明記**(「運用者の遠隔からの接続」＋「緊急時にコンソールから操作できる経路」の2本)。教訓= **モデルの保護対象と問題文の要件が一致していなければ設問は成立しない**。★出題前検分でも2件修正= 移行途中の構成に**存在しないリストへの参照**／選択肢に**プレースホルダ文字列** |
| 2026-08-08 | 紙面 20260808-018 (aaa・seed 4804) | 4 | 出題中 |  | 第3回(3問中3)。★新形 dbgread の初出題 |
| 2026-08-08 | 紙面 20260808-017 (aaa・seed 4804) | 4 | 出題中 |  | 第3回(3問中2)。★evidence 3つ巴(debug差替後)の初出題 |
| 2026-08-08 | 紙面 20260808-016 (aaa・seed 4804) | 4 | 出題中 |  | 第3回(3問中1)。cause形 |
| 2026-08-08 | 紙面 20260808-015 (aaa・seed 1201) | 4 | 採点済 | 正解(B) | cause形・kind=user_not_registered/world=default_frozen(scope=both)。両拠点とも**即時 Reject**＋両ルータの構成が同一で健全→機器側でなくサーバ台帳が原因、と正しく判断(無応答系のA/Dと構成側のCを排除) |
| 2026-08-08 | 紙面 20260808-014 (aaa・seed 1201) | 4 | 採点済 | 正解(A) | ★**console観測の初出題を正答**。read形・kind=console_forgotten/world=default_frozen。RT-千2 に `CONSOLE` リストが無い→console は default に従う→**サーバ生存下では Reject で緊急用ローカル管理者が入れない**を正しく読んだ。console 拡張は狙いどおり機能 |
| 2026-08-08 | 紙面 20260808-013 (aaa・seed 1201) | 4 | 採点済 | 不正解(D→正C) | ★**evidence 3つ巴の初出題**。kind=src_iface_missing/world=console_survives。**`show aaa servers`(D)を選択=2通りまでしか割れない惜しい肢**に掛かった(正解=サーバログ Cで3通りに割れる)。★**3つ巴化は狙いどおり機能**(前回の2択版は消去法で正答されたが、今回は部分的に有効な肢に誘導できた)。弱点=**観測を「候補が何通りに割れるか」で順位付けする発想**。今後も分割数の異なる肢を並べる |
| 2026-08-08 | 紙面 20260808-012 (aaa・seed 7505) | 4 | 採点済 | 正解(A) | ★BL-101 P1a 初出題・**新形 evidence の初出題を正答**。kind=key_mismatch/world=console_survives。「共有鍵不一致 vs 送信元誤り」は機器側で区別不能→サーバ側ログか送信元設定でしか割れない、を正しく選択(aaa servers/test aaa/line vty の3錯乱肢=両原因で同一 を排除) |
| 2026-08-08 | 紙面 20260808-011 (aaa・seed 7505) | 4 | 採点済 | 正解(D) | read形・kind=authz_no_fallback/world=no_lockout。RT-松2 の `aaa authorization exec default group AAA-SRV`(local 無し)を読み、SRV01 停止下でも SRV02 が応答するため**全員正常**と判断(=昇格不可のC・exec拒否のB・local生存のA を排除)。潜在故障の読み分けが正確 |
| 2026-08-08 | 紙面 20260808-051 (aaa・seed 71119) | 4 | 採点済 | 不正解(B→正A) | ★BL-103 ④ ACL 遮断の初出題= evidence 形・kind=acl_block_request/world=no_lockout。**`show aaa servers` を選択**したが、ACL 遮断でもサーバ停止でも DEAD 表示は同一で1通りも絞れない(実測 X4)。正解 `show ip access-lists` は ACL 無し/out 方向/in 方向の3通りに割れる。★debug は選択肢に出していない(ACL の2種は debug 上で完全同一=2通りまでしか割れず最良でない)。**弱点=「観測が原因ごとに割れるか」の評価軸** |
| 2026-08-08 | 紙面 20260808-056 (aaa・seed 71119) | 4 | 採点済 | 正解(C) | ★BL-103 ⑤ vty 範囲違いの初出題= cause 形・kind=vty_range_partial/world=console_survives。`line vty 0 4` にのみ REMOTE を適用・`5 15` は default(local) を読み取れている |
| 2026-08-08 | 紙面 20260808-048 (aaa・seed 71119) | 4 | 採点済 | 正解(A) | ★BL-103 ② コンソール認可の初出題= patch 形・kind=authz_console_missing/world=no_lockout。2/3。★出題後ユーザ指摘= **複数行のコマンド列がコードブロックに入らず一列に潰れる**(patch 形。CLI 行配列を持たない選択肢が render_options の整形から漏れていた)→本文に改行があれば必ずフェンスに入れるよう修正・全 shape で畳まれ0件を確認 |
| 2026-08-08 | 紙面 20260808-022 (aaa・seed 60813) | 4 | 採点済 | 正解(B) | ★BL-103 ① 新形 dbgconf 初出題(debug の逆問題)。kind=list_undefined/world=server_frozen。決め手= Fail-over 行の2台目アドレス・最初の Send 行のサーバ順序・再送回数 |
| 2026-08-08 | 紙面 20260808-030 (aaa・seed 60813) | 4 | 採点済 | 正解(C) | dbgconf。kind=authz_no_fallback/world=no_lockout。決め手= `Started 5 sec timeout`・`cfg_addr` が Lo0 か(source-interface 欠落)・Fail-over 行のポート |
| 2026-08-08 | 紙面 20260808-032 (aaa・seed 60813) | 4 | 採点済 | 正解(C) | dbgconf。kind=list_undefined/world=server_frozen。3/3 満点。★出題後の所見= **dbgconf は故障種を問うていない**(list_undefined/authz_no_fallback は方式リスト層でありRADIUS 送受信に現れない)→ BL-103 に「方式リスト層 debug」を追加(ユーザ提示の他社題材と同型) |
| 2026-08-08 | 紙面 20260808-010 (aaa・seed 7505) | 4 | 採点済 | 不正解(A→正C) | trace形・kind=list_not_applied/world=console_survives。**`test aaa group` は方式リストを通らずグループへ直接問い合わせる**(PoC E1 で実証)ことを見落とし、ログイン不可の症状から「サーバ到達不能(20秒)」を選択。★弱点=「利用者がログインできない」と「サーバに到達できない」の混同。`test aaa` の意味論は今後も混ぜる |
| 2026-08-08 | 紙面 20260808-003 (ospfv3pl・seed 360697548) | 4 | 採点済 | 正解(A) | ★dual_select(両掛け=手組ラボ主題)初出題を正答。fix形・kind=none(構築)。in=配布限定(permit E::/47 le 64+リンク網)×out=全域停止(deny F:F)の役割分担を正しく選択(B=in単独/C=役割逆転/D=out単独を排除)。正解側の `le 64` は通過=②長さレンジは受動形なら通る。→ le系の能動検出(le欠落/le63)は継続して混ぜる |
| 2026-08-08 | 紙面 20260808-002 (ospfv3pl・seed 406468398) | 4 | 採点済 | 不正解(A→正B) | read形・kind=le_missing/world=area10_only。`permit /47`(le欠落)=当該長のみ一致→Lo全滅を見落とし(被覆読みは正)。**長さレンジ照合の失点2連続=弱点確定**→ドリル対象。★出題後ユーザ指摘=主題は in/out 両掛けの経路選別(単発分解は主題外し)→dual_select 実装へ・リンクアドレスの毎回抽選も要望 |
| 2026-08-08 | 紙面 20260808-001 (ospfv3pl・seed 752439189) | 4 | 採点済 | 不正解(B→正A) | ★BL-097 P1 初出題=read形・kind=le_off/world=area10_only。**A::/47 の被覆(A,Bのみ)は正読・`le 63` の1-off(64>63で全滅)を見落とし**=①ビット包含は通し②長さレンジで失点。教訓=ge/le と実ルート長の突き合わせを必ず2チェック目に。次回は le 系(le欠落/ge 64 le 64)の変化球で定着確認 |
| 2026-08-07 | 紙面 20260807-005 (leakmap・seed 46802) | 4 | 採点済 | 正解(B) | fix形・kind=pl_undefined(参照PL未定義→全リーク)×世界no_redist。3問連続一発正解でBL-095初日3形(cause/read/fix)完走 |
| 2026-08-07 | 紙面 20260807-004 (leakmap・seed 71503) | 4 | 採点済 | 正解(D) | read形・kind=not_injected(リーク鎖健全×対象Lo未投入)。理由記述も正確(「EIGRPに取り込まれていない」)。健全テーブルAの罠を回避 |
| 2026-08-07 | 紙面 20260807-003 (leakmap・seed 60817) | 4 | 採点済 | 正解(F) | ★BL-095初出題。cause形・kind=pl_wrong_prefix(ACL10が別Lo許可・経路表のD .1/32が物証)。「ACLだから動かない」錯乱肢Cを回避 |
| 2026-08-06 | GEN-EGVRF-5528 (faults2) | 5 | 撤収済 | 100 | EIGRP×VRF TS 6回目を一発満点=**この生成器も全9故障コンプリート(6連覇)**。fault=**af_passive_a1(最後の未消化・af-interfaceのpassive-interfaceでsite1無言死)**+summary_wrong_if(集約が誤IFで明細漏れ+site1に不要集約)。passive除去+summary-addressをEt0/1へ移設・認証温存・最終形は収容標準と完全一致 |
| 2026-08-06 | GEN-FNFTS-6640 (faults2) | 5 | 撤収済 | 100 | FNF TS 4回目を一発満点。fault=**monitor_no_exporter(初出)**+**exporter_wrong_source(初出)**。チケット1:1対応(キャッシュ有×レコード不達=monitor参照欠け / 未登録ソース破棄=source誤り)を正しく写像・monitorへのexporter追記+source Loopback0是正の最小手2点。export-protocol netflow-v9はデフォルト非表示の理解も維持。※FNF未出fault残り2=apply_wrong_if/exporter_wrong_port |
| 2026-08-06 | GEN-DHCPTS-7710 (faults2) | 5 | 撤収済 | 90→100 | DHCP TS 3回目。fault=**acl_src_narrow(目玉・初出)**+**relay_service_off(初出)**。90×4回の足踏みのうち後半は**採点側の書式regex過剰厳格が原因**(ユーザ解=セグメント絞り+rebind broadcast行の意味的等価・むしろ最小権限)→acl_vectors意味評価へ差し替えて救済(BL-094)。前半2回は実穴あり(segB renew欠け→rebind欠け)で正当なFAIL。relay_service_off側は序盤で自力完治 |
| 2026-08-06 | GEN-BGPRING-63224 | 4 | 撤収済 | 90→100 | 同日2本目。shape=no_transit(--solution aspath)。初回90=route-map(match as-path)適用で**機能等価だが監査要件(filter-list指定)違反**→`^$` filter-list×2へ差し替えて満点。学習点=実装方式指定の監査文を仕様として読む。残骸=旧route-map ASMAP定義が未撤去(採点対象外・レビューで指摘済) |
| 2026-08-06 | GEN-BGPRING-57104 | 4 | 撤収済 | 100 | BL-093初出題を一発満点。shape=path_select(med盤面)・fault=prepend_missing@RT04。★参照解(prepend復元)でなく**MED合意の対称拡張**(RT01/RT03のRM-MED-OUTをRT02向けにも適用+RT02にacm)の別解で満点=異AS間MED非比較の理解を実証。採点後に「RT02だけ大回りパスが見えない理由」の機構質問→ベスト広告×自ASループ検知×最小RID吸引点をdebug実証付きで解説(良問化) |
| 2026-08-05 | GEN-DMVPN-31010 (faults2) | 5 | 撤収済 | 100 | ★**BL-091複合(--faults 2)初出題**を一発満点。fault=**g1_spoke_p2p_gre@RT03(初出)**+**n1_nhs_nbma_wrong@RT02(初出)**。2チケット(RT03の直行不成立×RT02全断)を別層(GREモード×NHRP宛先)へ正しく写像・両Tunnel0とも仕様書どおりの最終形・残骸ゼロ。これでDMVPN未消化はu1/i4/i6/i7/i8の5種 |
| 2026-08-05 | GEN-DMVPN-3702 | 4 | 撤収済 | 100 | 同日2本目も一発満点。fault=**i2_transform_mismatch@RT02(初出)**。IKEv2 READY×Child SAのみ失敗からESP層(esp-aes+hmac→esp-gcm 256)を特定・実SAもesp-gcm/Transport確認。g2(GRE層)との連続対比が効いた回。※未出題残り=u1/g1/n1/i4/i6/i7/i8 |
| 2026-08-05 | GEN-DMVPN-2415 | 4 | 撤収済 | 100 | BL-089完了後(16故障体制)の初出題を一発満点。fault=**g2_tunnel_key_mismatch@RT02(初出)**。IKEv2 READY×NHRP固着からGRE層(tunnel key 335)を特定・1行差し替えの最小手・残骸ゼロ。※未出題残り=u1/g1/n1/i1/i2/i4/i6/i7/i8 |
| 2026-08-05 | ENARSI-BGP-IPV6-01 | 4 | 撤収済 | 100 | 初出題を一発満点。v6 activate欠落/network欠落/ipv6 unicast-routing欠落の3点を全て是正・unicast-routing是正後のセッション再確立(clear要の罠)も突破。最終形は3台とも設計書どおりのMP-BGP形・IPv4無傷 |
| 2026-08-04 | GEN-URPF-5903 | 4 | 撤収済 | 100 | fault=strict_on_asym。★ユーザ解は想定解(非対称側をlooseへ緩和)より厳格な**strict維持+uRPF例外ACL**(rx 10)=ポリシー「可能な限り厳格」への上位解。指摘=ACL 10のワイルドカード0.0.0.5が非連続(.0/.1/.4/.5のみ許可・要件明記の.1はカバーで減点なし・/24全体なら0.0.0.255) |
| 2026-08-04 | ENARSI-BGP-SYNC-01 | 5 | 撤収済 | 100 | BL-059完成問の初出題を一発満点。①RT02/RT04のレガシーsynchronization除去(clear込み・no synchronizationだけではベストパス再計算されない罠を突破)②RT03を非BGP中継ブラックホールと特定→iBGPフルメッシュ組み込み(borders側にnh-self付き・再配布禁止の制約下で正攻法)。模範解と構造同型 |
| 2026-08-04 | GEN-OSPFX-6318 (stub+redist static・faults3+decoy1) | 5 | 撤収済 | 100 | OSPF複合TS 2回目を一発満点(採点1回目は収束待ちリトライ数回→全PASS)。fault=distribute_list_in@RT03+**router_id_collision@RT04×RT06(初出・難5)**+missing_loopback@RT05。RID重複は明示router-id+プロセス再起動の正攻法・フィルタ除去・Lo広告復旧いずれも最小手 |
| 2026-07-31 | GEN-EGVRF-8072 (faults2) | 5 | 採点済 | 100 | 未出2種狙い撃ち(fault=stub_rt02+key_string_mismatch)を一発満点(10連続・EIGRP×VRF 5連覇)。目玉stub_rt02(隣接UPのまま経路消失)×認証typoの2段はがし=認証是正→隣接UP→なお経路ゼロ→stub行除去の最小手2点。※この生成器の未出fault残り1=af_passive_a1 |
| 2026-07-31 | GEN-DMVPN-9174 (i3_keyring_perpeer) | 5 | 撤収済 | 100 | i3再挑戦(新seed)を一発満点(9連続)。両スポークのkeyringをpeer ANY(0.0.0.0)へ復旧=両側修理の必須性(responder側PSK)も正しく処理。監査型チケット(疎通正常×要件違反)からIX/DX固着→spoke間IKE不在→keyring照合の切り分け定着 |
| 2026-07-31 | GEN-DMVPN-6521 (n2_nhrp_auth_mismatch) | 5 | 撤収済 | 100 | n2再挑戦(新seed)を一発満点(8連続)。victim=RT03のNHRP認証キー同長typoを1行差し替えの最小手で復旧(nhs detailのrepl-recv回復まで確認)。完全サイレント故障の切り分け(IKEv2 READY×登録ゼロ→NHRP層×config突合)が定着 |
| 2026-07-31 | DMVPN-PHASE3-01 (再) | 5 | 撤収済 | 100 | 再演を一発満点(7連続)。Phase3作り分け完璧=hub redirect+af-interfaceはno split-horizonのみ(next-hop-self既定温存)・spoke shortcutは15.9暗黙既定の理解・前日Phase2(BGP-01)との対比が正確。IPsec自主実装が強化(aes256/sha256/g21/PFS/transport mode)・残骸ゼロ |
| 2026-07-31 | GEN-RDFIELD-7719 (ring) | 5 | 撤収済 | 100 | ring(inject_ospf×想定解distance)を一発満点(6連続)。ユーザ解は想定解と別のタグ方式=TAG01(set tag 200)@BGP→OSPF注入+TAG02(deny tag)@EIGRP distribute-list in=4977/8351と同型の3回目転用だが今回は注入OSPF/遮断EIGRPの新ペア(タグのLSA→D EX伝搬理解込み)。残骸ゼロ(4977の-5教訓定着)。効果採点で満点 |
| 2026-07-30 | ENCOR-DHCP-01 (再) | 3 | 採点済 | 100 | 再演を一発満点(本日5連続)=前回80点のACL要件を今回は最初から完走。ACLはBL-069教訓の汎用形(permit udp any eq bootpc any eq bootps)でrenew実効PASS・CL1はclient-id一行形の正攻法再現・自主lease 0 11 59付き(減点なし) |
| 2026-07-30 | GEN-EGVRF-8841 (faults2) | 4 | 撤収済 | 100 | EIGRP×VRF TS新seed一発満点(4連覇・本日4連続)。fault=vrf_missing_on_if+wrong_as_b(両方テナントB集中=チケット矛盾なし型)。IP剥がれ罠を実戦で自力突破(BL-070①開示済みの罠を初の実地検証)+named mode AF作り直しのAS是正。※未出fault残り3=af_passive_a1/stub_rt02/key_string_mismatch |
| 2026-07-30 | ENCOR-FNF-01 (v2) | 3 | 撤収済 | 100 | v2変種初出(サンプラー/longカウンタ/タイムスタンプ/ToSキー)を一発満点=FNF 4連続満点。record過不足ゼロ・sampler併記適用(ip flow monitor+sampler一行形)も正確。構築→TS両輪完成でFNF卒業レベル |
| 2026-07-30 | GEN-FNFTS-3907 (faults2) | 5 | 撤収済 | 100 | FNF TS新seed一発満点(3連続)。fault=exporter_wrong_version+monitor_wrong_record(チケット1:1対応の2点)。編集ロック非対称(export-protocolは参照解除要/monitor record差替はIF detach要)を突破し最終状態は仕様完全一致。※未出fault残り=apply_wrong_if/monitor_no_exporter/exporter_wrong_port/exporter_wrong_source |
| 2026-07-30 | ENARSI-DMVPN-BGP-01 (再) | 5 | 撤収済 | 100 | 再演を一発満点=前回7/19の弱点(next-hop-self)完全克服。named mode af-interface正実装・EIGRP→BGPはprefix-list選択再配送(Lo限定)・BGP→EIGRP seed metric明示・IPsec自主実装(esp-gcm・全台整合)。※採点1回目はコンソール収集10分timeout→max_attempts=1再実行(毎回の運用) |
| 2026-07-29 | GEN-RDFIELD-4471 (hard) | 5 | 撤収済 | 100 | ★--hardモード初出題(K=3・5台・EIGRP768/OSPF12/OSPF66・fault=wrong_id×2=両BRの参照ID誤り)を一発満点。config完備に見えて経路ゼロの型×2箇所・チケット範囲重複の解きほぐし込み。★wrong_id機構はこの回で実機フルサイクル検証完了(4故障型すべて実機済に)。※9418(3台missing×2)は較正不適合で引き直し・--hard実装(K=3固定+subtle保証) |
| 2026-07-29 | GEN-RDFIELD-6083 | 4 | 撤収済 | 100 | ★フィールド初出題(抽選=全EIGRP 3ドメインAS180/189/329・7台・fault=RT01のAS329→189方向missing)を一発満点。解=欠落方向のredistribute復旧(seed metric仕様値込み)・健全BR(RT05)は無変更の最小手。曖昧チケット(「全滅」申告)の裏取り→実範囲特定も自力 |
| 2026-07-29 | GEN-RDARENA-8351 | 5 | 撤収済 | 100 | アリーナ初出題(7台・inject_eigrp×filter)を一発満点。解=出自タグ方式(TAG01 set tag 200@BGP→EIGRP + TAG02 deny tag@OSPF distribute-list in)=4977と同型の1:1転用。★ユーザ指摘「全然違いなくない?」=正当(タイトル/チケット/ヒントがモチーフと診断手順をバラしている+単一モチーフ)→提示改修とPhase2(症状クラス抽選)へ |
| 2026-07-29 | GEN-REDISTLOOP-4977 (filter_ospf) | 5 | 撤収済 | 95→100 | distance禁止変種を出自タグ方式で完答: TAG01(set tag 110)をBGP→EIGRP再配送に付与+OSPFに`distribute-list route-map TAG02 in`(deny tag 110)=戻り経路のRIB搭載だけ拒否・RBのO E2は温存(LSAフラッディング非停止の理解が正確)。95の-5は試行残骸のdistance行(監査検知が機能)→除去で100。★弱点メモ「タグの位置づけ定着途上(7/19)」は完全克服と判定 |
| 2026-07-29 | GEN-FNFTS-8402 (faults2) | 4 | 撤収済 | 100 | FNF新seed TS一発満点(本日4連続)。fault=exporter_wrong_dest+apply_direction_output(エクスポート空振り×逆方向計測の2チケット)。解=destination是正+Et0/0をinput適用へ=最小手2点・模範解同型。※未出fault残り=apply_wrong_if/monitor_no_exporter/exporter_wrong_port/exporter_wrong_source/exporter_wrong_version/monitor_wrong_record |
| 2026-07-29 | GEN-DHCPTS-5741 (faults2) | 5 | 撤収済 | 100 | DHCP TS新seed一発満点(本日3連続)。fault=helper_missing(segB)+acl_no_dhcp_permit(両リモート)の2層交錯。解=Et0/2 helper復旧+ACLへseq5行挿入(permit udp any eq bootpc any eq bootps)=最小手。★BL-069の弱点(host 0.0.0.0限定形でrenew死)を自力回避=汎用形で初回からrenew実効PASS(学習ループ完結の実証) |
| 2026-07-29 | GEN-EGVRF-9153 (faults2) | 5 | 撤収済 | 100 | 新seed TS一発満点(EIGRP×VRF 3連覇)。fault=summary_wrong_if+auth_missing_a1(症状=site2に明細/site1不通の2チケット交錯)。解=summary-addressをaf-interface Et0/1へ移設+Et0/0へMD5認証投入=最小手2点・模範解同型。認証はmode md5+key-chainの2行構成も正確 |
| 2026-07-29 | DMVPN-POC-01 (再) | 5 | 撤収済 | 100 | 同値再演(ユーザ選択)を再び一発満点=完全定着。前回と同型(named mode・af-interfaceのno next-hop-self/no split-horizonはハブのみ・スポーク旧来3行NHRP・MTU/MSS先回り・IPsec自主実装tunnel key込み全台整合)。レビュー=hub map multicast dynamicの15.9暗黙デフォルト裏話を補足 |
| 2026-07-27 | ENARSI-VRFLITE-DNBIT-01 | 4 | 撤収済 | - | **en**(task.en.md新規作成・CML Notes英語差替の初適用)。未解答のままCMLサーバ停止のため中断→撤収。**再出題可**(問題パック・task.en.mdキャッシュ保持・ネタバレなし) |
| 2026-07-27 | ENARSI-OSPF-MADJ-01 | 4 | 撤収済 | 100 | **en**(英語出題初回・task.en.md新規作成・BL-071)。一発満点(全12チェックPASS)。P2P化+multi-area 0の2行×2台=模範解同型・broadcastサイレント罠を自力回避 |
| 2026-07-27 | ENARSI-BGP-AGGREGATE-01 | 3 | 撤収済 | 100 | BGP集約初出題を一発満点。as-set summary-onlyの1行最小解＋旧問に自主AF方式適用(規約定着)。レビューでAS_SETループ防止/atomic-aggregate/suppress-map3段構えを補足 |
| 2026-07-27 | GEN-EGVRF-4276 (faults2) | 5 | 撤収済 | 100 | VRF-aware EIGRP収容標準TS初出題を一発満点。fault=vrf_if_swap+missing_network_a2(3リンク全滅の初期状態)。★af-interface無言破棄のカスケード(VRF復旧後も隣接不成立→認証再投入)を初見で自力突破。運営反省=症状域重複時のチケット相互矛盾→生成器に注記追加 |
| 2026-07-27 | ENARSI-EIGRP-VRF-01 | 4 | 撤収済 | 100 | BL-070①初出題を一発満点(全11チェックPASS)。模範解答と構造同型・network文精密絞り・af-interface認証/集約の書き分け完璧。※IP剥がれ罠は完成報告時に開示済みだったため初見切り分けは未検証(再演か②TSで確認) |
| 2026-07-27 | ENCOR-FNF-01 (base) | 3 | 撤収済 | 100 | FNF構築問初出題を一発満点(全8チェックPASS)。仕様過不足ゼロの最小解。レビュー補足=export-protocol v9はデフォルトでconfig非表示/record編集ロックは既知(7842で経験済) |
| 2026-07-26 | ENARSI-DMVPN-IPSEC-01 (再) | 5 | 撤収済 | 100 | DMVPN+IPsec完全版の再出題→一発満点(定着確認OK)。Phase3をredirect+next-hop-self既定維持で正しく構成・MTU/MSS先回り・EIGRP named mode採用。※採点1回目はコンソール収集10分timeout→max_attempts=1で再実行(毎回の運用) |
| 2026-07-26 | DMVPN-POC-01 | 5 | 撤収済 | 100 | Phase2構築を一発満点。EIGRP named mode採用・af-interfaceでno next-hop-self/no split-horizon正実装(BGP-01の80点弱点が完全定着)。IPsec+tunnel key+MTU/MSSを仕様外で自主追加(全台整合・減点なし)。スポークNHRPは旧来3行構文 |
| 2026-07-26 | GEN-DMVPN-3194 | 4 | 撤収済 | 100 | DMVPN+IPsec TS(fault=p1_redirect_missing)。一発満点(5冠目)。解=hub Tunnel0にip nhrp redirect復旧の最小手1行・模範解同型。※初回採点は収束待ちで10分timeout→max_attempts=1で再実行 |
| 2026-07-26 | GEN-DHCPTS-8127 (faults2) | 5 | 撤収済 | 100 | DHCP TS初出題を一発満点。fault=helper_wrong_ip+excluded_swallows(両方segment B=片方直しても症状不変の2段重ね)。helper正常化+excluded .1-.9復元の最小手×2 |
| 2026-07-26 | ENCOR-DHCP-01 | 3 | 撤収済 | 80→100 | BL-066初出題。80=ACL未着手→自力完成。CL1固定割当は client-id 一行形(ip address dhcp client-id)で正攻法突破。★レビュー発見=ACLのDHCP permitがhost 0.0.0.0限定形でunicast renewがdeny落ち(採点盲点→BL-069)/CL1-FIXEDのdns typo 198.50/NET30 default-router行に余分な255.255.255.0 |
| 2026-07-26 | ENARSI-REDIST-POLICY-01 (s6127) | 4 | 撤収済 | 100 | BL-068初出題を一発満点。deny(tag)→deny(lab)→permit(個別色)→permit(包括色)の順序設計完璧・set metricのプレフィックス毎出し分けも模範同型。DENY01共用prefix-list・明示type-2は本人流 |
| 2026-07-25 | GEN-FNFTS-7842 (faults2) | 5 | 撤収済 | 100 | FNF監視標準TS初出題を一発満点。fault=record_missing_key(transport source-port)+monitor_not_applied。record編集ロック(要参照解除)を自力突破・キー追記順から編集パス採用と推定 |
| 2026-07-25 | ENCOR-IPSLA-01 | 4 | 撤収済 | 100 | 一発満点(全7チェックPASS)。仕様超えの丁寧解=SLA source-interface固定/timeout3000/frequency5/track delay down10 up5のダンピングまで実装。mgmt=.20/.31-.33 |
| 2026-07-23 | GEN-BGPCX-5926 (faults1+policy2) | 5 | 撤収済 | 76→100 | BGP複合TS(policy軸初)。3故障=prepend_wrong_side@be+weight_override@RR+missing_update_source@RT01。76時点で残ったのはweight_override(LPの上位で上書き)→自力是正。★チケット乖離を発見(シミュレータ「到達不能」予測vs実機到達可)→BL-061登録(update-source片側欠落の非対称成立仮説) |
| 2026-07-23 | GEN-BGPPATH-6152 (faults2+decoy1) | 5 | 撤収済 | 100 | BGP経路選択TS一発満点。fault=fwd_lp_wrong_nbr+ret_prepend_wrong_nbr。★ユーザ解は想定解(LP張り直し)と異なりAS_PATH操作で両方向制御の別解(効果採点で満点)。※私が修正内容をfault名から推測で誤断定→ユーザ訂正(レビューは実機の解を確認してから書く教訓) |
| 2026-07-23 | ENARSI-MPLS-L3VPN-03 (再) | 5 | 撤収済 | 100 | +採点後にsham-link端点の再配送遮断(両PE対称route-map)の設計問答→ユーザは片側では消えない事を実測して対称化(模範解答超えの完成形) | sham-link再演を一発満点(全15PASS・定着確認成功)。今回はcost100で主経路化(前回20・500未満なら可の理解が本物)。端点/32のBGP限定広告も再現 |
| 2026-07-23 | GEN-DMVPN-8817 (n4_multicast_map_tunnelip) | 4 | 撤収済 | 100 | DMVPN TS一発満点(4冠目)。multicast mapがトンネルIP指し→片方向hello周期フラップを範囲と層から特定。残骸行の掃除のみレビュー指摘 |
| 2026-07-22 | FGT-IPSEC-01 (伴走学習) | 3 | 撤収済 | 95→73→100 | マルチベンダIPsec完走。★ユーザ発案でPhase 0(管理IF自己設定)を正式課題化・S0一発PASS。踏んだ体験=DES罠(LENC)/GUI一括作成のPhase2デフォルトAESで-61/no policy configured(FW思想)/RBR側NO_PROPOSAL_CHOSEN誤診/staticルートtypo193→区間切り分けStep2で自力発見/phase1⇔2名前入れ替え→参照逆順削除・正名再作成の実務手順。機能は終始完動(G/E全PASS維持) |
| 2026-07-22 | FGT-FW-BASIC-01 (再×2:CLI伴走学習) | 2 | 撤収済 | 100 | ★2回目=FGT素人前提のCLI伴走学習モードで全Phase解説しながら再構築→100点。★前回2回とも指摘のID3 NAT不要を今回は NAT=off で正しく実装(学習効果=送信元保持を理解)。学んだ道具=show/get/grep -f(ブロック抽出)/session filter/debug flow。SNAT/DNAT/暗黙deny(policy0)を実機で目撃 |
| 2026-07-22 | ENCOR-PBR-01 | 3 | 採点済 | 100 | PBR基礎を一発満点。★02(通過=ip policy)直後の対比出題で ip local policy を正しく選択(自ルータ生成トラフィックの勘所を即座に把握)。Policy routing matches 29pktで実効確認 |
| 2026-07-22 | ENCOR-PBR-02 | 4 | 採点済 | 50→100 | PBR送信元別振り分け。1st50=IF適用/ACLは正だがroute-mapのset next-hop欠落→2nd100。名前付きACL PBR01+route-map PMAP・ip policy入口IF適用。Policy routing matches 85packetsで実効確認 |
| 2026-07-22 | ENARSI-IPSEC-IKEV2-01 | 4 | 撤収済 | 100 | sVTI×IKEv2構築を一発満点(全13PASS)。IKEv2 4点セット(proposal/policy/keyring peer別PSK/profile)・GCM=esp-gcm 256のみ(整合性内包)・DPD on-demand。P2P VTI×2なのでsplit-horizon不要(DMVPN単一mGREとの対比)を理解 |
| 2026-07-22 | ENARSI-IPSEC-VTI-01 | 3 | 撤収済 | 100 | sVTI×IKEv1構築を一発満点(全13チェックPASS)。仕様完全準拠(ISAKMP policy/transform-set/PFS/DPD/MTU/MSS)。tunnel mode ipsec ipv4・P2P型で/24保持。IPsec構築系デビュー戦 |
| 2026-07-21 | ENARSI-MPLS-L3VPN-05 | 4 | 撤収済 | 44→100 | フルメッシュ×H&S組み分け。1st44=折り返し半分(拠点発220受けのみ)→2nd100=上りCUST_B_UP export210×spoke import210で折返し完成。★ユーザはUP側peerにallowas-in設定で自AS重複の折返し経路を受理(置き場所=受信in方向で正解・04のas-overrideと送信/受信で対比)。RD補足=CUST_B_UPを65200:210(仕様65000:210)にしたが動作影響なし・慣習は管理AS |
| 2026-07-21 | GEN-DMVPN-6402 (r2_underlay_in_eigrp) | 4 | 撤収済 | 100 | DMVPN再帰ルーティングTS。★真因=restoreで入った広域network `10.0.0.0`(クラスフル)がunderlay/30まで巻き込む→mGRE再帰でフラップ。解=その1行を仕様どおり`network 10.255.106.0 0.0.0.255`(overlayのみ)に差替=最小手・一発満点。RECURDOWN非発出を状態フラップ観察で特定。※当初レビューで私が「Lo0広告が犯人」と誤読→ユーザ訂正(犯人は広域network文) |
| 2026-07-20 | FGT-FW-BASIC-01 | 2 | 撤収済 | 100 | FortiGate初出題を一発満点(全13チェックPASS)。仕様完全準拠。レビュー指摘=ポリシー3に不要なnat enable(LAN→DMZがSNATされDMZログから発信元が消える)・role未設定(採点外)。共用ラボFGT-LAB(stopのみ) |
| 2026-07-20 | ENARSI-MPLS-L3VPN-01 | 3 | 撤収済 | 100 | MPLS L3VPN一から構築を一発満点。全17チェックPASS(VRF/VPNv4/RT分離/顧客間分離/E2E)。ラベルスイッチング(Label17)・VPNv4セッションPfxRcd4も確認。重複172.16をRD/RTで正しく隔離 |
| 2026-07-20 | GEN-REDISTLOOP-3357 (ad_eigrp) | 5 | 撤収済 | 100 | 再配送リング定常ループ(逆回り変種・戻りD EX 170×iBGP 200)。解=distance bgp 20 80 20(効果完全・一発満点)。レビューで「勝ちたい相手だけに勝つ最小調整(165)」を補足 |
| 2026-07-20 | GEN-REDIST-8871 | 4 | 撤収済 | 100 | 相互再配送TS(fault=missing_e2o)。E→O再配送欠落を最小手(redistribute eigrp+metric20明示)で復旧・既設タグ機構は正しく温存・一発満点 |
| 2026-07-20 | DMVPN-PHASE3-01 | 5 | 撤収済 | 100 | Phase3構築一発満点。hub redirect＋next-hop-self温存の正しい作り分け(spoke shortcutはIOSv15.9暗黙既定で非表示)。MTU/MSS先回り・IPsec自主実装(不要だが整合・減点なし) |
| 2026-07-20 | GEN-SNMPTS-7605 | 5 | 撤収済 | 100 | SNMPv3×Zabbix監視TS。2故障(RT03 group ACLがポーラdeny/RT01 認証パス不一致=不可視の難5)を満点。RT03はACL参照撤去・RT01はuser再作成(鍵不可視→上書きの正攻法) |
| 2026-07-19 | ENARSI-MPLS-L3VPN-04 | 4 | 撤収済 | 100 | MPLS旗艦04一発満点。as-overrideをCUST_Bのみに精密適用・受信制御はホワイトリスト形(permit 172.16/16 le 24+暗黙deny)・顧客別にRM/PL分離の丁寧な実装 |
| 2026-07-19 | ENARSI-DMVPN-BGP-01 | 5 | 撤収済 | 80→100 | DMVPN Phase2構築+ハブ橋渡し。Phase3思い込み(next-hop-self残り)でスポーク間直接のみ未達→自己診断で是正。EIGRP named mode採用・MTU/MSS先回り設定・IPsecも自主実装(不要だが減点なし) |
| 2026-07-19 | GEN-REDISTMP-4515 (routemap) | 5 | 撤収済 | 80→100 | タグ基本形ドリル。効果は初回から完璧・80点の原因は set tag 側の prefix-list 絞り(監査違反=名指しアンチパターン)→指摘後**自力是正**(共用route-map 1枚のdeny/permit 2節に整理)。リセット1回 |
| 2026-07-18 | GEN-CHAIN-3661 (chain-depth3+decoy1) | 5 | 撤収済 | 100 | 12台連鎖TS。3段連鎖＋decoyを一発満点(4連続)。L3是正はIFモードospf+passive。採点後に再配送タグ講義→実機でRT07の陥落状態(clear起因のアンカー外れ)を発見→clear ip eigrp neighborsで復旧実験まで実施 |
| 2026-07-18 | GEN-OSPFX-7924 (vlink+redist static・faults2+decoy1) | 5 | 撤収済 | 100 | OSPF複合TS。distribute_list_in@RT06＋cost_suboptimal@RT03 を一発満点(本日3連続)。cost是正は明示100設定の別解(効果完全・最小形はno ip ospf cost) |
| 2026-07-18 | GEN-DMVPN-5177 (i3_keyring_perpeer) | 5 | 撤収済 | 100 | DMVPN Phase3+IKEv2 TS。keyring per-peer 絞りでスポーク間 IKE のみ不成立(ハブ経由疎通は正常)→peer ANY 復旧で一発満点。採点1回はコンソール収集10分timeout→max_attempts=1 で再実行(運用メモ) |
| 2026-07-18 | GEN-BGPRR-8442 (faults2+decoy1) | 5 | 撤収済 | 100 | RR伝播TS。2故障連鎖(missing_rr_client×transit_ospf_break)を一発満点。OSPF修正はhost-wildcard形の精密解。※seed6318は生成出力に故障名露出のため未出題破棄 |
| 2026-07-17 | ENARSI-DHCPV6-01 | 5 | 撤収済 | 73→88→100 | stateless/stateful/リレー。罠=O flag/statelessも relay要/no-autoconfig(A flag)/ipv6 nd autoconfig default-route/link-address プール選択 |
| 2026-07-17 | GEN-L2TS-8420 | 4 | 撤収済 | 100 | EtherChannel TS。3故障(member欠落/on↔active非互換/vlan不一致)全是正。一発満点 |
| 2026-07-16 | ENARSI-MPLS-L3VPN-03 | 5 | 撤収済 | 100 | バックドアintra vs コアinter→area0 sham-link(cost20)で主経路化。一発満点 |
| 2026-07-16 | ENCOR-IPSLA-02 | 5 | 撤収済 | 65→100 | 奥ビーコン監視IP SLA+track+固定/32+フローティングdefault。初回SLA source/ビーコン固定漏れ→是正で満点 |
| 2026-07-16 | ENCOR-VRF-NAT-01 | 6 | 撤収済 | 100 | VRF対応PAT(重複10.0.0.1を1グローバルIP共有・ポート分離)+vrf default global。一発満点 |
| 2026-07-16 | GEN-DMVPN-8305 | 3 | 撤収済 | 100 | DMVPN TS。fault=r1_split_horizon_on→ハブTunnel0のno ip split-horizon eigrpで解決。一発満点 |
| 2026-07-15 | GEN-BGPCX-7213 | 5 | 撤収済 | 100 | 4AS7台複合TS。3故障(send-community/default-originate/update-source)全是正。一発満点 |
| 2026-07-15 | ENCOR-OSPFV3-AREA-01 | 6 | 撤収済 | 100 | OSPFv3集約(area range/48)+Totally Stubby+手動RID。一発満点 |
| 2026-07-15 | ENCOR-VRF-LEAK-01 | 6 | 撤収済 | 100 | MP-BGP import/export RTでハブ&スポーク型共有サービス。一発満点 |
| 2026-07-15 | ENARSI-EIGRP-SIA-01 | 5 | 撤収済 | 100 | E0/1受信ACLがEIGRPユニキャスト遮断→access-group外して解決 |

## 記録開始前の既知出題(2026-07-14 以前・メモリからの復元)

| 時期 | 問題ID | 得点 | メモ |
|------|--------|------|------|
| 2026-07 | UM2-BUILD-01 | 96→100 | ユーザ解答。減点はトラック要件まわり |
| 2026-07 | ENARSI-DMVPN-IPSEC-01 | 100 | ユーザ解答(構築問) |
| 2026-07 | GEN-DMVPN(n2・難5) | 100 | ユーザ解答(TS)。seed 記録なし |
