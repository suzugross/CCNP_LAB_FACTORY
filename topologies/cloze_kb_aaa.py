#!/usr/bin/env python3
"""cloze_kb_aaa.py — 解説穴埋め形(shape=cloze) の知識ベース: AAA と認証サーバ(BL-194)

書式は cloze_kb_mpls.py と同じ(PASSAGES / slots / vars / scope)。
範囲= ENARSI 4.1 「Troubleshoot device security using IOS AAA (TACACS+, RADIUS, local database)」。
802.1X(認証サーバの別用途)は範囲外なので扱わない。

事実の出所:
- poc/aaa/README.md(IOL 17.15 + FreeRADIUS 実測・2026-08-08):
  Reject(1.1s)では local に落ちない / 無応答は timeout 3s×2 回×2 台= 約 12.5s 後に local へ落ちる /
  key 不一致と source-interface 欠落は `test aaa` の文言も秒数も同一(決め手はサーバ側ログ:
  「パスワード文字化け」対「unknown client」) / `aaa authorization exec` が無いと priv 1 固着 /
  認可にフォールバック無し×全断= local ユーザも exec 拒否 / 未定義リスト名を line に付けると default と同じ挙動 /
  `radius-server dead-criteria` が無いと `deadtime` は永久に効かず show aaa servers は UP のまま /
  enable を RADIUS 経由にすると `$enab15$` 不在で `% Error in authentication.` / 非標準ポート可。
- 公式 AAA/RADIUS/TACACS+ ガイド: RADIUS= UDP 1812/1813(旧 1645/1646)・パスワードだけ暗号化・認証と認可を一体で返す /
  TACACS+= TCP 49・ボディ全体を暗号化・認証/認可/アカウンティングを分離・コマンド単位の認可。
"""

PASSAGES = [
    # ------------------------------------------------------------------ RADIUS vs TACACS+
    {
        "kind": "a_compare",
        "title": "RADIUS と TACACS+ の違い",
        "diagram": None,
        "exhibit": (
            '| 項目 | RADIUS | TACACS+ |\n'
            '|---|---|---|\n'
            '| トランスポート | «r_proto» | «t_proto» |\n'
            '| 暗号化の範囲 | «r_enc» | «t_enc» |\n'
            '| AAA の分離 | 認証と認可を 1 往復で返す(一体) | «t_sep» |\n'
            '| コマンド単位の認可 | «r_cmd» | 可(コマンドごとにサーバへ照会) |\n'
            '| 標準 | IETF 標準(RFC 2865/2866) | Cisco 発(RFC 8907 として文書化) |\n'
        ),
        "exhibit_md": True,
        "text": (
            "2 つのプロトコルは「装置がサーバに何を聞き、どこまで守るか」が違う。RADIUS は «r_proto» で動き、"
            "パケットのうち «r_enc» ため、ユーザ名や属性は平文で流れる。認証に成功すると Access-Accept の中に権限レベルなどの属性(cisco-avpair の «avpair»)を"
            "同梱して返すので、認証と認可が一体である。TACACS+ は «t_proto» で動き、«t_enc» ので盗聴に強い。認証・認可・アカウンティングを別々のやり取りとして扱うため、"
            "管理者が打つ «cmd_authz» をコマンドごとにサーバで許可・拒否でき、装置管理(device administration)向きとされる。"
            "一方、RADIUS はアカウンティング属性が豊富で 802.1X などのネットワークアクセス制御に広く使われる。"
            "IOS の設定上は、どちらも「サーバ定義 → サーバグループ → メソッドリスト → 回線への適用」という同じ骨格で書く。"
        ),
        "slots": {
            "r_proto": {"a": "UDP 1812(認証)/1813(アカウンティング)", "d": ["TCP 49", "UDP 1645/1646 のみ"], "why": "RADIUS は UDP 1812/1813(旧 1645/1646 も可)"},
            "t_proto": {"a": "TCP 49", "d": ["UDP 1812(認証)/1813(アカウンティング)", "TCP 443"], "why": "TACACS+ は TCP 49"},
            "r_enc": {"a": "パスワードだけを暗号化する", "d": ["ボディ全体を暗号化する", "何も暗号化しない"], "why": "RADIUS は User-Password 属性だけ共有鍵で難読化"},
            "t_enc": {"a": "ボディ全体を暗号化する", "d": ["パスワードだけを暗号化する", "ヘッダも含め全部を暗号化する"], "why": "TACACS+ はヘッダ以外のボディ全体を暗号化"},
            "t_sep": {"a": "認証・認可・アカウンティングを分離", "d": ["認証と認可を 1 往復で返す(一体)", "認可だけ提供"], "why": "TACACS+ は 3 つを別セッションで扱う"},
            "r_cmd": {"a": "不可(exec 認可で権限レベルを渡すのみ)", "d": ["可(コマンドごとにサーバへ照会)", "可(ACL で代替)"], "why": "コマンド単位の認可は TACACS+ の特長"},
            "avpair": {"a": "shell:priv-lvl=15", "d": ["shell:roles=admin", "Service-Type=Framed"], "why": "IOS の exec 権限レベルは shell:priv-lvl"},
            "cmd_authz": {"a": "コマンド認可(aaa authorization commands)", "d": ["exec 認可(aaa authorization exec)", "ログイン認証"], "why": "打つコマンドごとの許可はコマンド認可"},
        },
    },
    # ------------------------------------------------------------------ メソッドリストの意味論
    {
        "kind": "a_methods",
        "title": "メソッドリストの読み方と「次のメソッドへ行く条件」",
        "diagram": None,
        "worlds": ["grp_local", "local_grp", "grp_only"],
        "world_desc": {"grp_local": "group → local の順(サーバ優先・無応答時だけ local)",
                       "local_grp": "local → group の順(local 優先・local に無ければサーバ)",
                       "grp_only": "group だけ(フォールバック無し)"},
        "keep": ["methods"],
        "exhibit": (
            "aaa new-model\n"
            "aaa authentication login default «methods»\n"
            "!\n"
            "username {emg} privilege 15 secret 9 $9$xxxx    ! local だけに存在\n"
            "! 認証サーバの台帳: {noc}(サーバだけに存在)\n"
            "!\n"
            "line vty 0 15\n"
            " transport input ssh\n"
            " ! (login authentication 未指定)\n"
        ),
        "text": (
            "«newmodel» を入れた瞬間に全回線が AAA のメソッドリストで認証されるので、投入前に別のセッションを開いたままにしておく。"
            "上の default のリストは «default_scope» に効く。メソッドは左から順に試され、次へ進むのは前のメソッドが «goto_next» ときだけで、"
            "«reject_end» 場合はそこで確定する(次へは行かない)。"
            "この盤面でサーバが正常に応答しているとき、local だけにいる {emg} は «emg_ok»。サーバだけにいる {noc} は «noc_ok»。"
            "サーバが 2 台とも無応答のとき、{emg} は «emg_out»。"
            "なお、回線に付けたリスト名が «undefined» と、IOS は default と同じ動きをする(実測)。"
        ),
        "slots": {
            "methods": {"a": {"grp_local": "group {grp} local", "local_grp": "local group {grp}", "grp_only": "group {grp}"},
                        "d": [], "why": "世界を決める行(空欄にはしない)"},
            "newmodel": {"a": "aaa new-model", "d": ["aaa authentication login default", "aaa session-id common"], "why": "AAA を有効化するのは aaa new-model。旧 line password は無視される"},
            "default_scope": {"a": "名前付きリストを付けていない全回線", "d": ["コンソールだけ", "vty だけ"], "why": "default は明示指定の無い回線すべてに効く"},
            "goto_next": {"a": "応答しない(タイムアウト/到達不能)", "d": ["認証を拒否した", "ユーザが存在しない"], "why": "ERROR のときだけ次へ。Reject は確定"},
            "reject_end": {"a": "拒否(Reject)した", "d": ["タイムアウトした", "DEAD 判定された"], "why": "Reject で確定・次のメソッドへは落ちない(実測 1.1s で失敗)"},
            "emg_ok": {"a": {"grp_local": "サーバが拒否するので入れない",
                             "local_grp": "local で即座に入れる",
                             "grp_only": "サーバが拒否するので入れない"},
                       "d": ["約 12 秒待ったあと local で入れる"],
                       "why": {"grp_local": "先頭のサーバが Reject= 確定。local に居ても使われない",
                               "local_grp": "先頭が local なのでサーバに聞く前に成功",
                               "grp_only": "サーバが Reject= 確定"}},
            "noc_ok": {"a": {"grp_local": "サーバで即座に入れる",
                             "local_grp": "local に無いので次のサーバへ進み、入れる",
                             "grp_only": "サーバで即座に入れる"},
                       "d": ["local に無いので入れない"],
                       "why": {"grp_local": "先頭のサーバが Accept",
                               "local_grp": "local の「ユーザ不在」は ERROR 扱いで次へ進む(拒否ではない)",
                               "grp_only": "サーバが Accept"}},
            "emg_out": {"a": {"grp_local": "約 12 秒待ったあと local で入れる",
                              "local_grp": "待たされずに local で入れる",
                              "grp_only": "入れない(次のメソッドが無く締め出し)"},
                        "d": ["サーバが拒否するので入れない"],
                        "why": {"grp_local": "無応答は次(local)へ。待ち= timeout×再送×台数",
                                "local_grp": "先頭が local なのでサーバの状態は無関係",
                                "grp_only": "フォールバックが無いと無応答= 失敗"}},
            "undefined": {"a": "定義されていない", "d": ["2 つ以上ある", "default と同名だ"], "why": "未定義名は default 扱い(実測 E15)"},
        },
        "vars": {"grp": ["RADGRP", "AAA-SRV", "TAC-GRP"], "emg": ["emg-admin", "local-admin", "break-glass"], "noc": ["noc-taro", "netadmin", "ope-suzuki"]},
    },
    # ------------------------------------------------------------------ RADIUS 設定例
    {
        "kind": "a_cfg_radius",
        "title": "RADIUS による管理アクセス制御の設定例",
        "diagram": None,
        "exhibit": (
            "aaa new-model\n"
            "!\n"
            "«srvdef» RAD1\n"
            " address ipv4 {srv1} auth-port {aport} acct-port {acct}\n"
            " key {key}\n"
            "radius server RAD2\n"
            " address ipv4 {srv2} auth-port {aport} acct-port {acct}\n"
            " key {key}\n"
            "!\n"
            "aaa group server radius {grp}\n"
            " server name RAD1\n"
            " server name RAD2\n"
            "!\n"
            "«srciface» Loopback0\n"
            "radius-server dead-criteria time 3 tries 1\n"
            "!\n"
            "aaa authentication login default group {grp} «fallback»\n"
            "aaa authorization exec default group {grp} «fallback»\n"
            "«authz_con»\n"
            "!\n"
            "username {emg} privilege 15 secret 9 $9$xxxx\n"
            "line vty 0 15\n"
            " transport input ssh\n"
        ),
        "text": (
            "上の設定を上から読む。サーバは «srvdef» で名前を付けて定義し、アドレス・ポート・共有鍵を持たせる。ポートは既定の {aport}/{acct} 以外も指定でき、"
            "サーバ側の設定と一致していればよい。2 台を «grp_role» にまとめ、メソッドリストからはこのグループ名で参照する。"
            "«srciface» は要求の送信元アドレスを固定するもので、サーバ側の «client_list» に登録したアドレスと一致させるために要る。"
            "これが無いと出力インターフェースのアドレスが送信元になり、サーバは要求を «unknown» として黙って捨てる。"
            "認証と認可の両方に «fallback» を末尾に置き、サーバ無応答時にローカルの {emg} で入れるようにしている。"
            "«authz_con» はコンソールにも exec 認可を効かせるための行で、これが無いとコンソールでは認可が実行されない。"
        ),
        "slots": {
            "srvdef": {"a": "radius server", "d": ["radius-server host", "tacacs server"], "why": "現行構文は radius server <名前>(旧 radius-server host は非推奨)"},
            "srciface": {"a": "ip radius source-interface", "d": ["ip tacacs source-interface", "ip source-route"], "why": "RADIUS の送信元固定"},
            "fallback": {"a": "local", "d": ["none", "enable"], "why": "サーバ無応答時にローカル DB へ"},
            "authz_con": {"a": "aaa authorization console", "d": ["aaa authorization config-commands", "aaa authentication console"], "why": "コンソールの認可は明示が要る"},
            "grp_role": {"a": "サーバグループ(aaa group server radius)", "d": ["メソッドリスト", "回線グループ"], "why": "複数サーバの束がグループ"},
            "client_list": {"a": "クライアント(NAS)一覧", "d": ["ユーザ台帳", "認可プロファイル"], "why": "サーバは登録済み NAS アドレスからの要求だけ受ける"},
            "unknown": {"a": "unknown client", "d": ["invalid password", "duplicate request"], "why": "未登録の送信元はサーバログに unknown client(実測)"},
        },
        "vars": {
            "srv1": ["10.99.1.2", "192.168.100.11", "172.16.10.5"], "srv2": ["10.99.2.2", "192.168.100.12", "172.16.10.6"],
            "aport": ["1812", "1645"], "acct": ["1813", "1646"], "key": ["Rad-Key-2026", "S3cret-Rad", "N0c-Radius"],
            "grp": ["RADGRP", "AAA-SRV", "NOC-RADIUS"], "emg": ["emg-admin", "local-admin", "break-glass"],
        },
        "var_links": {"srv1": "srv2", "aport": "acct"},
    },
    # ------------------------------------------------------------------ TACACS+ 設定例(コマンド認可)
    {
        "kind": "a_cfg_tacacs",
        "title": "TACACS+ によるコマンド認可とアカウンティングの設定例",
        "diagram": None,
        "exhibit": (
            "aaa new-model\n"
            "!\n"
            "tacacs server TAC1\n"
            " address ipv4 {srv1}\n"
            " key {key}\n"
            "aaa group server tacacs+ {grp}\n"
            " server name TAC1\n"
            "ip tacacs source-interface Loopback0\n"
            "!\n"
            "aaa authentication login default group {grp} local\n"
            "aaa authorization exec default group {grp} «ifauth»\n"
            "aaa authorization commands {lvl} default group {grp} local\n"
            "«cfgcmd»\n"
            "aaa accounting exec default «acct_mode» group {grp}\n"
            "aaa accounting commands {lvl} default «acct_mode» group {grp}\n"
        ),
        "text": (
            "TACACS+ の価値はコマンド単位の制御にある。`aaa authorization commands {lvl}` により、権限レベル {lvl} のユーザが打つコマンドは "
            "«per_cmd» サーバに問い合わせて許可・拒否される。ただし既定では «cfg_scope» は認可対象に含まれず、"
            "«cfgcmd» を入れて初めてインターフェース配下などの設定コマンドも照会される。"
            "exec 認可の末尾に置いた «ifauth» は「認証に成功していれば許可」というメソッドで、サーバ無応答時に締め出されないための保険である。"
            "アカウンティングは «acct_mode» にすると開始と終了の両方が記録され、コマンドのアカウンティングでは "
            "「誰がいつ何を打ったか」が残る。TACACS+ はこの照会と記録を «t_conn» の上で行うので、サーバとの間に TCP 49 が通っている必要がある。"
            "なおコマンド認可はサーバが応答している限り厳密に効くため、サーバの障害時に備えて «fail_local» を末尾に置くのが定石である。"
        ),
        "slots": {
            "per_cmd": {"a": "1 コマンドごとに", "d": ["ログイン時に 1 回だけ", "権限レベル変更時だけ"], "why": "commands 認可は打つたびに照会"},
            "cfg_scope": {"a": "設定モードのコマンド", "d": ["show コマンド", "特権 EXEC のコマンド"], "why": "config-commands を入れないと設定モード配下は照会されない"},
            "cfgcmd": {"a": "aaa authorization config-commands", "d": ["aaa authorization console", "aaa authorization network default"], "why": "設定コマンドを認可対象に含めるコマンド"},
            "ifauth": {"a": "if-authenticated", "d": ["none", "enable"], "why": "認証済みなら許可するメソッド"},
            "acct_mode": {"a": "start-stop", "d": ["stop-only", "none"], "why": "開始と終了の両方を記録"},
            "t_conn": {"a": "TCP セッション", "d": ["UDP データグラム", "ICMP"], "why": "TACACS+ は TCP 49"},
            "fail_local": {"a": "local", "d": ["none", "群の 2 台目"], "why": "無応答時にローカル DB で認可"},
        },
        "vars": {"srv1": ["10.99.1.5", "192.168.100.21", "172.16.10.9"], "key": ["Tac-Key-2026", "S3cret-Tac", "N0c-Tacacs"],
                 "grp": ["TACGRP", "TAC-SRV", "NOC-TACACS"], "lvl": ["15", "1"]},
    },
    # ------------------------------------------------------------------ 認可の罠
    {
        "kind": "a_authz",
        "title": "認可(authorization)の構成で変わるログイン後の権限",
        "diagram": None,
        "worlds": ["ok", "no_exec", "no_fb"],
        "world_desc": {"ok": "exec 認可あり・末尾に local(正しい構成)",
                       "no_exec": "exec 認可の行が無い",
                       "no_fb": "exec 認可はあるがフォールバック(local)が無い"},
        "exhibit": {
            "ok": (
                "aaa new-model\n"
                "aaa authentication login default group {grp} local\n"
                "aaa authorization exec default group {grp} local\n"
                "aaa authorization console\n"
                "username {emg} privilege 15 secret 9 $9$xxxx      ! local だけに存在\n"
                "! サーバ台帳: {noc}= shell:priv-lvl=15 / {desk}= shell:priv-lvl=1\n"
            ),
            "no_exec": (
                "aaa new-model\n"
                "aaa authentication login default group {grp} local\n"
                "! (aaa authorization exec の行なし)\n"
                "aaa authorization console\n"
                "username {emg} privilege 15 secret 9 $9$xxxx      ! local だけに存在\n"
                "! サーバ台帳: {noc}= shell:priv-lvl=15 / {desk}= shell:priv-lvl=1\n"
            ),
            "no_fb": (
                "aaa new-model\n"
                "aaa authentication login default group {grp} local\n"
                "aaa authorization exec default group {grp}\n"
                "aaa authorization console\n"
                "username {emg} privilege 15 secret 9 $9$xxxx      ! local だけに存在\n"
                "! サーバ台帳: {noc}= shell:priv-lvl=15 / {desk}= shell:priv-lvl=1\n"
            ),
        },
        "text": (
            "認証が通ってもログイン後の権限は認可が決める。サーバは Access-Accept に «avpair» を付けて返す。"
            "この盤面でサーバが正常なとき、{noc} がログインした直後の権限レベルは «noc_priv»、{desk} は «desk_priv»。"
            "サーバが 2 台とも無応答のとき、local だけにいる {emg} は認証には通り、その後 «emg_out»。"
            "この構成に対する評価は «verdict»。"
            "なお認証は local で通っても、認可がサーバへ照会して «authz_reject» された場合は EXEC が拒否される(拒否は権威の原則)。"
            "コンソールは «console_cmd» が無いと exec 認可自体が実行されない。"
        ),
        "slots": {
            "avpair": {"a": "shell:priv-lvl=15", "d": ["Service-Type=Login", "Framed-Protocol=PPP"], "why": "権限レベルを運ぶ属性"},
            "noc_priv": {"a": {"ok": "15(特権 EXEC)", "no_exec": "1(属性は無視される)", "no_fb": "15(特権 EXEC)"},
                         "d": ["0"],
                         "why": {"ok": "exec 認可が AVPair を適用", "no_exec": "exec 認可が無いと属性は使われず priv 1 固着(実測)", "no_fb": "サーバが応答している限り AVPair は効く"}},
            "desk_priv": {"a": {"ok": "1(ユーザ EXEC)", "no_exec": "1(ユーザ EXEC)", "no_fb": "1(ユーザ EXEC)"},
                          "d": ["15(特権 EXEC)"], "why": "priv-lvl=1 の台帳どおり(認可が無くても 1)"},
            "emg_out": {"a": {"ok": "約 12 秒待って local の認可で priv 15 に入れる",
                              "no_exec": "認可が無いので待たずに入れる(権限は 1)",
                              "no_fb": "EXEC を拒否され入れない(local ユーザも締め出し)"},
                        "d": ["サーバが拒否するので入れない"],
                        "why": {"ok": "認証も認可も無応答→local へ", "no_exec": "認可の段が無い", "no_fb": "認可の無応答に逃げ道が無い(実測 E5)"}},
            "verdict": {"a": {"ok": "意図どおり(是正不要)",
                              "no_exec": "aaa authorization exec default group {grp} local を追加すべき",
                              "no_fb": "exec 認可の末尾に local(または if-authenticated)を追加すべき"},
                        "d": ["aaa authorization console を外すべき"],
                        "why": {"ok": "権限と締め出し保険の両方がある", "no_exec": "権限レベルが配れない", "no_fb": "全断時に全員締め出し"}},
            "authz_reject": {"a": "拒否(Reject)", "d": ["タイムアウト", "DEAD 判定"], "why": "認可の Reject も確定"},
            "console_cmd": {"a": "aaa authorization console", "d": ["aaa authorization config-commands", "line con 0 の privilege level 15"], "why": "コンソール認可の明示"},
        },
        "vars": {"grp": ["RADGRP", "AAA-SRV", "TACGRP"], "emg": ["emg-admin", "local-admin", "break-glass"],
                 "noc": ["noc-taro", "netadmin", "ope-suzuki"], "desk": ["helpdesk", "monitor-op", "desk-01"]},
    },
    # ------------------------------------------------------------------ 拒否と無応答の見分け(所要時間)
    {
        "kind": "a_timing",
        "title": "「入れるか」より「何秒待ったか」が原因を指す",
        "diagram": None,
        "exhibit": (
            "RT01# test aaa group {grp} {user} {pw} legacy\n"
            "Attempting authentication test to server-group {grp} using radius\n"
            "«msg»\n"
            "\n"
            "(参考) radius-server timeout {timeout} / radius-server retransmit {retransmit} / グループ内サーバ 2 台\n"
        ),
        "text": (
            "`test aaa` の応答は 3 種類しかない。即座(0.1 秒)に返る「User was successfully authenticated.」、約 1 秒で返る「User authentication request was rejected by server.」、"
            "そして約 «wait_s» 秒待って返る「«msg»」である。3 つ目の秒数は «formula» から来る。"
            "ログインの見え方も同じ 3 値で、拒否なら local に同じユーザがいても «reject_login»、無応答なら «wait_s» 秒ほど待たされたあと "
            "«timeout_login»。したがって「待たされて入れた」は «cause_wait» を、「すぐ弾かれた」は «cause_fast» を疑う。"
            "厄介なのは共有鍵の不一致で、サーバは実は Reject を返しているのに、装置は鍵が違うため応答の «resp_auth» を検証できず捨てる。"
            "結果として装置側は「無応答」と全く同じ文言・同じ秒数になり、送信元アドレスの誤り(サーバ側で unknown client として破棄)とは "
            "«distinguish» でしか区別できない。"
        ),
        "slots": {
            "msg": {"a": "No authoritative response from any server.", "d": ["User authentication request was rejected by server.", "User was successfully authenticated."], "why": "無応答の文言(実測)"},
            "formula": {"a": "timeout {timeout} 秒 × (1+再送 {retransmit})回 × 2 台", "d": ["timeout {timeout} 秒 × 4 回", "deadtime 5 分の一部"], "why": "{timeout}×{tries}×2= {wait} 秒"},
            "wait_s": {"a": "{wait}", "d": ["{wait_one}", "{wait_x4}"], "why": "timeout {timeout} × (1+再送 {retransmit}) × 2 台= {wait}。1 台分なら {wait_one}"},
            "reject_login": {"a": "入れない", "d": ["local で入れる", "権限レベル 1 で入れる"], "why": "Reject は確定・local に落ちない"},
            "timeout_login": {"a": "local のユーザなら入れる", "d": ["誰も入れない", "サーバ台帳のユーザだけ入れる"], "why": "無応答は次メソッド(local)へ"},
            "cause_wait": {"a": "サーバに届いていない/鍵不一致/ポート違い", "d": ["パスワード誤り", "ユーザ未登録"], "why": "待ち= 無応答系"},
            "cause_fast": {"a": "ユーザ未登録やパスワード誤り(サーバが拒否)", "d": ["鍵不一致", "source-interface 欠落"], "why": "即拒否= サーバは応答している"},
            "resp_auth": {"a": "Response Authenticator", "d": ["Message-Authenticator の有無", "送信元ポート"], "why": "共有鍵で計算する応答の検証値"},
            "distinguish": {"a": "サーバ側のログ", "d": ["show aaa servers", "debug radius の所要時間"], "why": "機器側の出力は同一(実測)"},
        },
        "vars": {"grp": ["RADGRP", "AAA-SRV"], "user": ["noc-taro", "netadmin"], "pw": ["Noc-1234", "Adm-9876"],
                 "timeout": ["3", "5"], "retransmit": ["1", "2"],
                 "tries": lambda v, w: int(v["retransmit"]) + 1,
                 "wait": lambda v, w: int(v["timeout"]) * (int(v["retransmit"]) + 1) * 2,
                 "wait_one": lambda v, w: int(v["timeout"]) * (int(v["retransmit"]) + 1),
                 "wait_x4": lambda v, w: int(v["timeout"]) * 4},
        "var_links": {"user": "pw"},
    },
    # ------------------------------------------------------------------ サーバの死活と冗長
    {
        "kind": "a_servers",
        "title": "サーバの死活判定(dead-criteria と deadtime)と show aaa servers",
        "diagram": None,
        "worlds": ["crit", "nocrit"],
        "world_desc": {"crit": "dead-criteria あり(1 台目が DEAD になり 2 台目へ直行)",
                       "nocrit": "dead-criteria なし(deadtime だけ書いてある・1 台目は UP のまま)"},
        "exhibit": {
            "crit": (
                "radius-server timeout 3\nradius-server retransmit 1\n"
                "radius-server dead-criteria time 3 tries 1\n"
                "aaa group server radius {grp}\n server name RAD1\n server name RAD2\n deadtime 5\n!\n"
                "RT01# show aaa servers\n"
                "RADIUS: id 1, priority 1, host {srv1}, auth-port 1812, acct-port 1813, hostname RAD1\n"
                "     State: current DEAD, duration 312s, previous duration 0s\n"
                "RADIUS: id 2, priority 2, host {srv2}, auth-port {p2}, acct-port {p2a}, hostname RAD2\n"
                "     State: current UP, duration 4021s, previous duration 0s\n"
            ),
            "nocrit": (
                "radius-server timeout 3\nradius-server retransmit 1\n"
                "! (radius-server dead-criteria なし)\n"
                "aaa group server radius {grp}\n server name RAD1\n server name RAD2\n deadtime 5\n!\n"
                "RT01# show aaa servers\n"
                "RADIUS: id 1, priority 1, host {srv1}, auth-port 1812, acct-port 1813, hostname RAD1\n"
                "     State: current UP, duration 4333s, previous duration 0s\n"
                "RADIUS: id 2, priority 2, host {srv2}, auth-port {p2}, acct-port {p2a}, hostname RAD2\n"
                "     State: current UP, duration 4021s, previous duration 0s\n"
            ),
        },
        "text": (
            "RAD1({srv1})が停止して 5 分ほど経っている。«dead_crit» は「何秒応答が無く、何回失敗したら DEAD とみなすか」の条件で、"
            "«deadtime» は DEAD とみなしたサーバを何分間スキップするかである。この 2 つは片方だけでは機能しない。"
            "上の出力で RAD1 の State が «st1» なのは «why_state» ためで、いまログインすると待ち時間は «wait_after»。"
            "この構成に対する評価は «verdict»。RAD2 のポート {p2}/{p2a} のように «nonstd» は許され、サーバ側と一致していれば動く。"
            "なお DEAD は「応答が無かった」の判定であって、UP でも認証できないこと(鍵不一致など)はある。"
        ),
        "slots": {
            "dead_crit": {"a": "radius-server dead-criteria time/tries", "d": ["radius-server deadtime", "radius-server timeout"], "why": "DEAD 判定条件"},
            "deadtime": {"a": "deadtime", "d": ["dead-criteria", "retransmit"], "why": "スキップする時間(分)"},
            "st1": {"a": {"crit": "DEAD(スキップ対象)", "nocrit": "UP(スキップされない)"}, "d": ["DOWN"], "why": {"crit": "条件を満たして DEAD", "nocrit": "条件が無いので UP のまま(実測)"}},
            "why_state": {"a": {"crit": "判定条件(time 3・tries 1)を満たした", "nocrit": "判定条件が無く、何回失敗しても状態が変わらない"},
                          "d": ["deadtime 5 分が経過した"],
                          "why": {"crit": "dead-criteria が DEAD を作る", "nocrit": "deadtime 単独では出番が来ない(実測)"}},
            "wait_after": {"a": {"crit": "6 秒程度(RAD2 の分だけ)", "nocrit": "12 秒のまま(毎回 RAD1 のタイムアウトを待つ)"},
                           "d": ["0 秒"],
                           "why": {"crit": "DEAD のサーバはスキップされる(実測 6.1s)", "nocrit": "UP 扱いなので毎回 RAD1 から試す"}},
            "verdict": {"a": {"crit": "意図どおり(是正不要)", "nocrit": "radius-server dead-criteria time 3 tries 1 を追加すべき"},
                        "d": ["deadtime を 0 にすべき"], "why": {"crit": "死活判定が機能している", "nocrit": "判定条件が無いと deadtime は無意味"}},
            "nonstd": {"a": "非標準ポート", "d": ["非標準の共有鍵", "IPv6 アドレス"], "why": "auth-port/acct-port は任意"},
        },
        "vars": {"srv1": ["10.99.1.2", "192.168.100.11"], "srv2": ["10.99.2.2", "192.168.100.12"], "p2": ["1912", "1645"], "p2a": ["1913", "1646"],
                 "grp": ["RADGRP", "AAA-SRV"]},
        "var_links": {"srv1": "srv2", "p2": "p2a"},
    },
    # ------------------------------------------------------------------ アカウンティング
    {
        "kind": "a_accounting",
        "title": "アカウンティングの種類と記録のタイミング",
        "diagram": None,
        "exhibit": (
            "aaa accounting exec default «mode_ss» group {grp}\n"
            "aaa accounting commands 15 default «mode_so» group {grp}\n"
            "aaa accounting «net_kw» default start-stop group {grp}\n"
            "aaa accounting system default start-stop group {grp}\n"
        ),
        "text": (
            "アカウンティングは「誰が・いつ・何を」をサーバへ送る機能で、認証や認可と違い «no_block»。"
            "種類は、ログインセッションの «exec_type»、打ったコマンドの記録である commands <レベル>、PPP などの «net_kw»、"
            "装置の再起動などの system がある。記録のタイミングは «mode_ss» なら開始と終了の 2 レコード、«mode_so» なら終了時の 1 レコード、"
            "wait-start なら開始レコードがサーバに受理されるまでセッションを始めない。"
            "RADIUS では Accounting-Request が UDP «acct_port» へ送られ、サーバは Accounting-Response で受領を返す。"
            "コマンド単位の記録は «cmd_acct_by» でのみ実用的で、変更履歴の監査に使う。"
        ),
        "slots": {
            "no_block": {"a": "失敗してもログインや操作は妨げない", "d": ["失敗するとログインできない", "サーバが無いと設定できない"], "why": "記録の機能であって許可ではない"},
            "exec_type": {"a": "exec", "d": ["login", "session"], "why": "EXEC セッションの記録は exec"},
            "net_kw": {"a": "network", "d": ["connection", "resource"], "why": "PPP/SLIP などは network"},
            "mode_ss": {"a": "start-stop", "d": ["stop-only", "wait-start"], "why": "開始+終了"},
            "mode_so": {"a": "stop-only", "d": ["start-stop", "none"], "why": "終了のみ"},
            "acct_port": {"a": "1813", "d": ["1812", "49"], "why": "RADIUS アカウンティングは 1813(旧 1646)"},
            "cmd_acct_by": {"a": "TACACS+", "d": ["RADIUS", "syslog"], "why": "コマンドアカウンティングは TACACS+"},
        },
        "vars": {"grp": ["TACGRP", "RADGRP"]},
    },
    # ------------------------------------------------------------------ enable 認証
    {
        "kind": "a_enable",
        "title": "特権昇格(enable)の認証をサーバに任せるとき",
        "diagram": None,
        "exhibit": (
            "aaa authentication enable default group {grp} «fb»\n"
        ),
        "text": (
            "既定では `enable` コマンドは装置の «default_enable» で検証される。上の 1 行を入れると昇格の検証もまずサーバへ行く。"
            "RADIUS の場合、装置はユーザ名として «enab_user» を送るので、サーバ側にその名前の台帳が無いと拒否され、"
            "«fail_msg» と表示されて権限レベルは «stay» のままになる(実測)。"
            "末尾の «fb» はサーバ無応答時にだけ使われ、拒否のときには使われない。これはログイン認証と同じ「«principle»」の原則である。"
            "TACACS+ の場合はユーザごとの enable パスワードや権限レベルをサーバで持てるため、この用途では TACACS+ の方が自然に組める。"
            "なお exec 認可で最初から権限レベル 15 を渡していれば、そもそも enable を打つ必要がない。"
        ),
        "slots": {
            "default_enable": {"a": "enable secret", "d": ["username の secret", "line password"], "why": "既定の enable 認証は enable secret"},
            "enab_user": {"a": "$enab15$", "d": ["ログインしたユーザ名", "enable"], "why": "RADIUS の enable 認証はユーザ名 $enab<level>$"},
            "fail_msg": {"a": "% Error in authentication.", "d": ["% Access denied", "% Bad secrets"], "why": "実測の表示"},
            "stay": {"a": "1", "d": ["15", "0"], "why": "昇格失敗で priv 1 のまま"},
            "fb": {"a": "enable(装置側の特権パスワードで検証)", "d": ["local(username の secret で検証)", "none(検証なし)"], "why": "末尾に enable を置いて無応答時は enable secret へ"},
            "principle": {"a": "拒否は権威・無応答だけが次へ", "d": ["先着優先", "最も強い認証が勝つ"], "why": "全層共通の原則"},
        },
        "vars": {"grp": ["RADGRP", "AAA-SRV"]},
    },
]
