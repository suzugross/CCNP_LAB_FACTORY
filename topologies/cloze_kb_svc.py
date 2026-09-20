#!/usr/bin/env python3
"""cloze_kb_svc.py — 解説穴埋め形(shape=cloze) の知識ベース: Services の設定構造(SNMPv3・NetFlow/FNF・BL-202)

書式は cloze_kb_mpls.py と同じ(PASSAGES / slots / vars / worlds / n_blanks / exhibit_md)。kind 接頭辞 `s_`(genre= services)。
範囲= ENARSI 3.2 「Troubleshoot SNMP (v2c, v3)」・3.6 「Troubleshoot NetFlow (v5, v9, flexible NetFlow)」。
top-talkers は従来 NetFlow(v5 世代)の機能で ENCOR 側の題材だが、ユーザ要望(2026-09-20)により FNF の cache sort との対比で扱う。

事実の出所:
- poc/svc-paper/README.md(iol-xe 17.15・2026-09-13 実測): RO は GET のみ(SET は noAccess)・コミュニティの ACL 未定義= 全許可・
  ACL が許可しない= 無応答 / `show snmp` の Unknown community name・Illegal operation カウンタ /
  v3 の指紋= 認証パスワード誤り→ Wrong SNMP PDU digest・暗号パスワード誤り→ 無応答・priv グループへ authNoPriv→ authorizationError・
  未定義ユーザ→ Unknown USM user / `show snmp user` に鍵は出ず running-config にも user 行は出ない /
  `snmp-server host X <comm>`(version 省略)= v1 trap・udp-port 162 / `informs version 1`= %Informs not supported in SNMPv1 /
  `snmp-server enable traps`(引数なし)= 全種が running-config に展開。
- gen_snmpv3_ts.py(GEN-SNMPTS・実機全故障済): view/group/user の正規構文・view excluded→ authorizationError・
  group の ACL deny→ タイムアウト・group の未定義 view 参照→ 認証は通るが取得失敗(show snmp group の readview で割れる)。
- 公式 SNMP コマンドリファレンス(snmp-server engineID local): engineID を変えると v3 ユーザのダイジェストが無効になり作り直し。
- ENCOR-FNF-01 / gen_fnf_ts.py(IOL 実測): record(match=キー/collect=非キー)→ exporter(destination/source/transport udp/export-protocol)→
  monitor(record+exporter)→ IF `ip flow monitor <名> input|output`。cache は `show flow monitor <名> cache` で確認(コレクタ不要)。
  編集ロック= 使用中 record のフィールド変更不可(% Object is in use)・IF から外しても解錠されず monitor の `no record` が要る・
  monitor の record 行は上書き不可(no record→record の 2 段)・exporter の export-protocol だけ参照中変更不可(destination/source/transport はライブ変更可)・
  export-protocol の既定は netflow-v9。
- 公式 NetFlow ガイド(Top Talkers): `ip flow-top-talkers` 配下 `top <1-200>` / `sort-by bytes|packets` / `match …` / `cache-timeout <ms>`(既定 5000)・
  前提= IF の `ip flow ingress|egress`・確認= `show ip flow top-talkers`(末尾 "N of M top talkers shown")。
  FNF Top N= `show flow monitor <名> cache sort highest counter bytes top <n>`(sort 対象はレコードにあるフィールドだけ)。
"""

# ---- 共通の可変値 -------------------------------------------------------------
_MGR = ["10.99.0.2", "192.168.100.20", "172.16.50.10"]
_ACL = ["99", "10", "55"]
_TAG = ["CORP", "WAN", "EDGE", "NOC"]

PASSAGES = [
    # ------------------------------------------------------------------ SNMPv3 セキュリティレベル表
    {
        "kind": "s_snmp_levels",
        "title": "SNMPv3 のセキュリティレベルと group/host のキーワード",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            '| セキュリティレベル | 守られるもの | group / host で書くキーワード |\n'
            '|---|---|---|\n'
            '| noAuthNoPriv | «l1_desc» | «kw1» |\n'
            '| authNoPriv | «l2_desc» | «kw2» |\n'
            '| authPriv | «l3_desc» | «kw3» |\n'
        ),
        "exhibit_md": True,
        "text": (
            "SNMPv3 は USM(User-based Security Model)でユーザごとに保護の強さを選ぶ。v1/v2c はコミュニティ文字列を «v2c_plain» で送るので、"
            "v3 で言えば表の最上段と同じ強さしかない。装置では group にレベルのキーワードを書き、それが «grp_role» になる。"
            "その group に属するユーザが、group より «lower» セキュリティレベルで要求を送ると authorizationError で拒否され(実測)、"
            "より強いレベルの要求はそのまま受け付けられる。認証と暗号の鍵はユーザ作成時にパスワードから «localized» で導出されるため、"
            "engineID を変更すると既存ユーザのダイジェストは無効になり作り直しになる。"
            "認証アルゴリズムは MD5 か SHA、暗号は DES/3DES/AES(128/192/256)から選ぶ。"
        ),
        "slots": {
            "l1_desc": {"a": "ユーザ名の一致だけを確認する(合言葉に相当)", "d": ["証明書で相互に認証する", "コミュニティ名を SHA でハッシュして送る", "誰でも読める(ユーザ名も見ない)"], "grp": "desc", "why": "noAuthNoPriv= 認証も暗号化も無し。ユーザ名の照合のみ"},
            "l2_desc": {"a": "HMAC-MD5/HMAC-SHA で認証するが暗号化はしない", "d": ["証明書で相互に認証する", "コミュニティ名を SHA でハッシュして送る", "誰でも読める(ユーザ名も見ない)"], "grp": "desc", "why": "authNoPriv= 認証あり・暗号化なし(盗聴はできるが改ざん・なりすましは防ぐ)"},
            "l3_desc": {"a": "認証に加えて DES/3DES/AES で暗号化する", "d": ["証明書で相互に認証する", "コミュニティ名を SHA でハッシュして送る", "誰でも読める(ユーザ名も見ない)"], "grp": "desc", "why": "authPriv= 認証+暗号化。監視の標準はこれ"},
            "kw1": {"a": "noauth", "d": ["none", "open", "nopriv", "plain"], "grp": "kw", "why": "snmp-server group … v3 noauth"},
            "kw2": {"a": "auth", "d": ["none", "open", "nopriv", "plain"], "grp": "kw", "why": "snmp-server group … v3 auth"},
            "kw3": {"a": "priv", "d": ["none", "open", "nopriv", "plain"], "grp": "kw", "why": "snmp-server group … v3 priv(host 行の version 3 の後ろも同じ 3 語)"},
            "v2c_plain": {"a": "平文", "d": ["ハッシュ化した形", "AES で暗号化した形"], "why": "コミュニティは平文。だから v3 が要る"},
            "grp_role": {"a": "そのグループが受け付ける最低のセキュリティレベル", "d": ["ユーザが使える最高のセキュリティレベル", "通知(trap)を送るときのレベル"], "why": "group の priv は「priv 以上で来い」の意味"},
            "lower": {"a": "低い(弱い)", "d": ["高い(強い)", "同じ"], "why": "priv グループへ authNoPriv 要求= authorizationError(実測)"},
            "localized": {"a": "engineID を混ぜた局所化(localized key)", "d": ["Diffie-Hellman 鍵交換", "サーバ証明書の検証"], "why": "鍵はパスワード+engineID から作る。engineID が変わると鍵が合わなくなる"},
        },
    },
    # ------------------------------------------------------------------ SNMPv3 設定の参照連鎖
    {
        "kind": "s_snmp_cfg",
        "title": "SNMPv3 設定の 4 行(view → group → user → host)の参照関係",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "snmp-server view {view} iso included\n"
            "snmp-server group {grp} v3 priv read «ref_view» access {acl}\n"
            "snmp-server user {user} «ref_grp» v3 auth «auth_alg» {apw} priv «priv_alg» 128 {ppw}\n"
            "snmp-server host {mgr} version 3 priv «ref_user»\n"
            "snmp-server enable traps\n"
            "access-list {acl} permit {mgr}\n"
            "!\n"
            "! NOC 標準: 認証 SHA・暗号 AES-128・authPriv のみ許可・ポーラは {mgr}\n"
        ),
        "text": (
            "SNMPv3 の設定は上から順に «dep» という関係で読む。view は見せる MIB の範囲、group はセキュリティレベルと view の組、"
            "user は group に属する実体で鍵を持ち、host は通知の宛先とそのときに使う user を指定する。"
            "group の `access {acl}` は «acl_role» で、許可されない送信元からの要求には応答しない(タイムアウト・実測)。"
            "user 行は投入しても «hidden» ので、設定の確認は `show snmp user`(鍵は出ない)と `show snmp group` で行う。"
            "group が存在しない view 名を参照していると認証は通るのに値が取れないため、`show snmp group` の readview 欄を疑う(実測)。"
            "エージェントは UDP «agent_port» で要求を受け、通知は管理ステーションの UDP 162 へ送る。`snmp-server enable traps` を引数なしで入れると "
            "«all_traps» が有効になり、running-config には種類ごとの行として展開される。"
        ),
        "slots": {
            "ref_view": {"a": "{view}", "d": ["{grp}", "{user}", "iso"], "why": "group の read は view 名を参照する"},
            "ref_grp": {"a": "{grp}", "d": ["{view}", "{acl}"], "why": "user 行の 2 語目は所属 group 名"},
            "ref_user": {"a": "{user}", "d": ["{grp}", "{view}"], "why": "host の version 3 では community の位置に user 名を書く"},
            "auth_alg": {"a": "sha", "d": ["md5", "aes"], "why": "NOC 標準が SHA(md5 も構文としては通るが標準に反する)"},
            "priv_alg": {"a": "aes", "d": ["des", "sha"], "why": "AES-128= priv aes 128"},
            "dep": {"a": "後の行が前の行で付けた名前を参照する", "d": ["前の行が後の行の名前を参照する", "行ごとに独立していて順序も参照も無い"], "why": "view→group→user→host の名前の鎖"},
            "acl_role": {"a": "要求の送信元アドレスの制限", "d": ["取得できる MIB の範囲の制限", "通知の宛先の制限"], "why": "group(または user)の access は送信元制限。MIB 範囲は view"},
            "hidden": {"a": "running-config に表示されない", "d": ["running-config に平文で表示される", "startup-config にだけ保存される"], "why": "v3 user 行は running-config に出ない仕様(実測)"},
            "agent_port": {"a": "161", "d": ["162", "514", "123"], "why": "エージェント 161 / 通知の受け手 162"},
            "all_traps": {"a": "すべての種類の通知", "d": ["リンク up/down の通知だけ", "認証失敗の通知だけ"], "why": "引数なし= 全種(running-config に多数の行として展開・実測)"},
        },
        "vars": {"view": ["MONVIEW", "NMS-VIEW", "V3VIEW"], "grp": ["MONGRP", "NMS-GRP", "V3GROUP"], "user": ["MONUSER", "nms-poller", "zbx-ro"],
                 "acl": _ACL, "mgr": _MGR, "apw": ["CCNP-Auth-2026", "Auth-N0c-77"], "ppw": ["CCNP-Priv-2026", "Priv-N0c-77"]},
        "var_links": {"view": "grp", "grp": "user", "apw": "ppw"},
    },
    # ------------------------------------------------------------------ v3 の応答指紋(世界)
    {
        "kind": "s_snmp_resp",
        "title": "SNMPv3 の GET が失敗したとき、応答の種類が原因を指す",
        "diagram": None,
        "worlds": ["auth_pw", "priv_pw", "level", "user"],
        "world_desc": {"auth_pw": "管理ステーションの認証パスワードが装置と不一致",
                       "priv_pw": "管理ステーションの暗号(priv)パスワードが装置と不一致",
                       "level": "group は priv なのに管理ステーションが authNoPriv で要求",
                       "user": "管理ステーションのユーザ名が装置に存在しない"},
        "exhibit": {
            "auth_pw": (
                "! ルータ側\n"
                "snmp-server group {grp} v3 priv read {view} access {acl}\n"
                "snmp-server user {user} {grp} v3 auth sha {apw} priv aes 128 {ppw}\n"
                "access-list {acl} permit {mgr}\n"
                "!\n"
                "! 管理ステーション({mgr})のポーリング設定\n"
                "  user  : {user}\n"
                "  level : authPriv\n"
                "  auth  : SHA / {apw_bad}\n"
                "  priv  : AES-128 / {ppw}\n"
            ),
            "priv_pw": (
                "! ルータ側\n"
                "snmp-server group {grp} v3 priv read {view} access {acl}\n"
                "snmp-server user {user} {grp} v3 auth sha {apw} priv aes 128 {ppw}\n"
                "access-list {acl} permit {mgr}\n"
                "!\n"
                "! 管理ステーション({mgr})のポーリング設定\n"
                "  user  : {user}\n"
                "  level : authPriv\n"
                "  auth  : SHA / {apw}\n"
                "  priv  : AES-128 / {ppw_bad}\n"
            ),
            "level": (
                "! ルータ側\n"
                "snmp-server group {grp} v3 priv read {view} access {acl}\n"
                "snmp-server user {user} {grp} v3 auth sha {apw} priv aes 128 {ppw}\n"
                "access-list {acl} permit {mgr}\n"
                "!\n"
                "! 管理ステーション({mgr})のポーリング設定\n"
                "  user  : {user}\n"
                "  level : authNoPriv\n"
                "  auth  : SHA / {apw}\n"
                "  priv  : (未使用)\n"
            ),
            "user": (
                "! ルータ側\n"
                "snmp-server group {grp} v3 priv read {view} access {acl}\n"
                "snmp-server user {user} {grp} v3 auth sha {apw} priv aes 128 {ppw}\n"
                "access-list {acl} permit {mgr}\n"
                "!\n"
                "! 管理ステーション({mgr})のポーリング設定\n"
                "  user  : {user_bad}\n"
                "  level : authPriv\n"
                "  auth  : SHA / {apw}\n"
                "  priv  : AES-128 / {ppw}\n"
            ),
        },
        "text": (
            "この盤面で管理ステーションから GET を送ると、返ってくるのは «resp»。原因は «cause»。"
            "USM は受け取った要求を «order» の順に処理するので、認証鍵の誤りはエラー応答として即座に見えるが、"
            "暗号鍵の誤りは復号に失敗した時点で黙って捨てられ、管理ステーションからは無応答にしか見えない。"
            "装置側では «dev_check» でユーザの認証・暗号プロトコルと所属 group を確認できるが、鍵そのものは表示されないので、"
            "鍵の不一致は装置の表示からは割れない。是正は «fix»。"
            "なお ACL の deny や到達性の問題も無応答になるため、無応答のときは鍵より先に `show access-lists` と ping で切り分ける。"
        ),
        "slots": {
            "resp": {"a": {"auth_pw": "Wrong SNMP PDU digest(認証失敗)", "priv_pw": "無応答(タイムアウト)",
                           "level": "authorizationError", "user": "Unknown USM user"},
                     "d": ["noSuchName", "Unknown community name"],
                     "why": {"auth_pw": "認証ダイジェストの不一致= Wrong digest(実測)", "priv_pw": "復号失敗は黙って破棄(実測)",
                             "level": "group の最低レベル未満= authorizationError(実測)", "user": "USM にユーザが無い= Unknown USM user(実測)"}},
            "cause": {"a": {"auth_pw": "認証パスワードが装置側と一致していない", "priv_pw": "暗号(priv)パスワードが装置側と一致していない",
                            "level": "group が要求する priv より弱い authNoPriv で要求している", "user": "装置に存在しないユーザ名で要求している"},
                      "d": ["ACL {acl} が {mgr} を許可していない"],
                      "why": {"auth_pw": "管理ステーションの auth 欄を見る", "priv_pw": "管理ステーションの priv 欄を見る",
                              "level": "level 欄が authNoPriv", "user": "user 欄の名前が装置の user と違う"}},
            "order": {"a": "ユーザ名の照合 → 認証(ダイジェスト検証) → 復号", "d": ["復号 → 認証 → ユーザ名の照合", "ACL → 復号 → 認証 → ユーザ名の照合"], "why": "だから未定義ユーザ・認証失敗はエラーが返り、暗号失敗だけ無応答"},
            "dev_check": {"a": "show snmp user", "d": ["show running-config | include snmp-server user", "show snmp community"], "why": "user 行は running-config に出ないので include では何も出ない"},
            "fix": {"a": {"auth_pw": "管理ステーション側の認証パスワードを装置の user と一致させる",
                          "priv_pw": "管理ステーション側の暗号パスワードを装置の user と一致させる",
                          "level": "管理ステーション側を authPriv で要求させる(または group を auth に下げる)",
                          "user": "管理ステーション側のユーザ名を装置の user と一致させる"},
                    "d": ["access-list {acl} に {mgr} を追加する"],
                    "why": {"auth_pw": "鍵の片側を合わせる", "priv_pw": "鍵の片側を合わせる", "level": "レベルを group 以上に", "user": "名前を合わせる"}},
            "silent": {"a": "エラー応答を返さず黙って捨てる", "d": ["Report PDU で理由を返す", "ICMP port unreachable を返す"], "why": "復号できないものには何も返せない"},
        },
        "vars": {"view": ["MONVIEW", "NMS-VIEW", "V3VIEW"], "grp": ["MONGRP", "NMS-GRP", "V3GROUP"], "user": ["MONUSER", "nms-poller", "zbx-ro"],
                 "user_bad": ["MONUSR", "nms-poler", "zbx-r0"], "acl": _ACL, "mgr": _MGR,
                 "apw": ["CCNP-Auth-2026", "Auth-N0c-77"], "apw_bad": ["CCNP-Auth-2025", "Auth-N0c-71"],
                 "ppw": ["CCNP-Priv-2026", "Priv-N0c-77"], "ppw_bad": ["CCNP-Priv-2025", "Priv-N0c-71"]},
        "var_links": {"view": "grp", "grp": "user", "user": "user_bad", "apw": "apw_bad", "ppw": "ppw_bad"},
    },
    # ------------------------------------------------------------------ 通知(trap と inform)
    {
        "kind": "s_snmp_notify",
        "title": "SNMP 通知: trap と inform の違いと host 行の既定",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            '| 項目 | trap | inform |\n'
            '|---|---|---|\n'
            '| 受信側の確認応答 | «t_ack» | «i_ack» |\n'
            '| 届かなかったとき | 再送しない(送りっぱなし) | «i_retry» |\n'
            '| 送信側の負担 | 小さい | «i_load» |\n'
            '| 使える SNMP バージョン | v1 / v2c / v3 | «i_ver» |\n'
            '| 宛先ポート(管理ステーション側) | UDP 162 | UDP 162 |\n'
        ),
        "exhibit_md": True,
        "text": (
            "通知の宛先は `snmp-server host` で、何を通知するかは «enable_cmd» で決める。両方が揃って初めて通知が飛ぶ。"
            "`snmp-server host {mgr} {comm}` のように version を省略すると «def_ver» として送られる(実測)。"
            "inform を送るには host 行に «inform_kw» を付け、version は 2c 以上を指定する。v1 を指定すると設定自体が拒否される(実測)。"
            "v3 で通知を送るときは `version 3` の後ろに «v3_after» を書き、通知に使うユーザの鍵で認証・暗号化される。"
            "エージェントが要求を受けるのは UDP 161、通知を受け取る管理ステーション側は UDP «trap_port» である。"
        ),
        "slots": {
            "t_ack": {"a": "なし(受信側は何も返さない)", "d": ["あり(ICMP で確認する)", "TCP の ACK で確認する"], "why": "trap は一方向"},
            "i_ack": {"a": "あり(受信側が Response を返す)", "d": ["なし(受信側は何も返さない)", "SNMP GET で問い合わせて確認する"], "why": "inform は確認応答付き"},
            "i_retry": {"a": "応答が来るまで再送する(回数・間隔は設定可)", "d": ["再送しない(送りっぱなし)", "コレクタが取りに来るまで保存する"], "why": "inform は再送で信頼性を上げる"},
            "i_load": {"a": "応答待ちの間メモリに保持するので大きい", "d": ["小さい", "trap と同じ"], "why": "保持と再送の分だけ負担が増える"},
            "i_ver": {"a": "v2c / v3(v1 では使えない)", "d": ["v1 / v2c / v3", "v3 だけ"], "why": "%Informs not supported in SNMPv1(実測)"},
            "enable_cmd": {"a": "snmp-server enable traps", "d": ["snmp-server host", "snmp-server community"], "why": "enable traps= 通知の種類 / host= 宛先"},
            "def_ver": {"a": "バージョン 1 の trap", "d": ["バージョン 2c の trap", "バージョン 2c の inform"], "why": "version 省略= v1 trap(実測)"},
            "inform_kw": {"a": "informs", "d": ["traps", "notify"], "why": "snmp-server host X informs version 2c <comm>"},
            "v3_after": {"a": "セキュリティレベル(noauth/auth/priv)とユーザ名", "d": ["コミュニティ名", "view 名とグループ名"], "why": "version 3 priv <user>"},
            "trap_port": {"a": "162", "d": ["161", "514", "123"], "why": "通知の受け手は 162"},
        },
        "vars": {"mgr": _MGR, "comm": ["NOC-RO", "public", "mon-ro"]},
    },
    # ------------------------------------------------------------------ v2c コミュニティと ACL
    {
        "kind": "s_snmp_comm",
        "title": "コミュニティ(v1/v2c)の RO/RW と ACL の効き方",
        "diagram": None,
        "exhibit": (
            "snmp-server community {ro} RO {acl}\n"
            "snmp-server community {rw} RW {acl_undef}\n"
            "access-list {acl} permit {mgr}\n"
            "! (access-list {acl_undef} は定義されていない)\n"
        ),
        "text": (
            "コミュニティは RO と RW の 2 種類で、RO では GET は成功するが SET は «ro_set» として拒否され、RW では両方成功する。"
            "コミュニティに付けた ACL が要求の送信元を許可しないとき、装置は «acl_deny»。一方、参照している ACL が定義されていないときは "
            "«undef_effect»(実測)。したがって上の {rw} は送信元を問わず書き込める危険な状態である。"
            "誤ったコミュニティ名での要求は `show snmp` の «bad_comm» カウンタ、RO への SET は «illegal» カウンタに現れる。"
            "コミュニティ名は running-config に «comm_shown» ので、v3 のユーザ(表示されない)とは扱いが違う。"
        ),
        "slots": {
            "ro_set": {"a": "noAccess", "d": ["noSuchName", "authorizationError"], "why": "RO への SET= noAccess(実測)"},
            "acl_deny": {"a": "応答を返さない(タイムアウトになる)", "d": ["authorizationError を返す", "Unknown community name を返す"], "why": "ACL 不許可= 無応答(実測)"},
            "undef_effect": {"a": "全許可になる(拒否しない)", "d": ["全拒否になる", "そのコミュニティが無効になる"], "why": "未定義 ACL 参照= 全許可(実測)。設定ミスが穴になる"},
            "bad_comm": {"a": "Unknown community name", "d": ["Illegal operation", "Encoding errors"], "why": "誤コミュニティのカウンタ(実測)"},
            "illegal": {"a": "Illegal operation", "d": ["Unknown community name", "No such name errors"], "why": "RO への SET のカウンタ(実測)"},
            "comm_shown": {"a": "平文で表示される", "d": ["表示されない", "ハッシュで表示される"], "why": "コミュニティは running-config に平文"},
        },
        "vars": {"ro": ["NOC-RO", "mon-ro", "readonly"], "rw": ["NOC-RW", "cfg-rw", "private"], "acl": _ACL, "acl_undef": ["77", "88", "66"], "mgr": _MGR},
    },
    # ------------------------------------------------------------------ FNF の 4 段構造
    {
        "kind": "s_fnf_parts",
        "title": "Flexible NetFlow の 4 段(record → exporter → monitor → インターフェース)",
        "diagram": None,
        "n_blanks": 5,
        "worlds": ["in", "out"],
        "world_desc": {"in": "隣接ルータから入ってくる通過トラフィックを見たい(input)", "out": "隣接ルータへ出ていく通過トラフィックを見たい(output)"},
        "exhibit": (
            "flow record {rec}\n"
            " «k_match» ipv4 source address\n"
            " «k_match» ipv4 destination address\n"
            " «k_match» ipv4 protocol\n"
            " «k_match» transport source-port\n"
            " «k_match» transport destination-port\n"
            " «k_collect» counter bytes\n"
            " «k_collect» counter packets\n"
            "!\n"
            "flow exporter {exp}\n"
            " «e_dest» {col}\n"
            " «e_src» Loopback0\n"
            " transport udp {port}\n"
            " «e_proto» {ver}\n"
            "!\n"
            "flow monitor {mon}\n"
            " «m_exp» {exp}\n"
            " «m_rec» {rec}\n"
            "!\n"
            "interface {ifn}\n"
            " ip flow monitor {mon} «dir»\n"
        ),
        "text": {
            "in": (
                "FNF は 3 つの部品と 1 つの適用で組む。レコードでは «k_match» で指定したフィールドがキーになり、その値の組が同じパケットは 1 つのフローにまとめられる。"
                "«k_collect» で指定したフィールドは «collect_role» で、フローの識別には使われない。"
                "エクスポータはコレクタの宛先・送信元・UDP ポート・«e_proto»(既定は «def_ver»)を持つ。"
                "モニタは «mon_role» で、レコードとエクスポータを名前で束ねる。"
                "最後にインターフェースへ適用して初めて計測が始まる。{ifn} は隣接ルータ側の IF なので、そこから入ってくる通過トラフィックを見るには «dir» に適用する。"
                "コレクタが無くても «verify» でフローが採取されているかを確認できる。"
            ),
            "out": (
                "FNF は 3 つの部品と 1 つの適用で組む。レコードでは «k_match» で指定したフィールドがキーになり、その値の組が同じパケットは 1 つのフローにまとめられる。"
                "«k_collect» で指定したフィールドは «collect_role» で、フローの識別には使われない。"
                "エクスポータはコレクタの宛先・送信元・UDP ポート・«e_proto»(既定は «def_ver»)を持つ。"
                "モニタは «mon_role» で、レコードとエクスポータを名前で束ねる。"
                "最後にインターフェースへ適用して初めて計測が始まる。{ifn} は隣接ルータ側の IF なので、そこへ出ていく通過トラフィックを見るには «dir» に適用する。"
                "コレクタが無くても «verify» でフローが採取されているかを確認できる。"
            ),
        },
        "slots": {
            "k_match": {"a": "match", "d": ["key", "collect", "classify"], "why": "match= キー(フローの識別子)"},
            "k_collect": {"a": "collect", "d": ["count", "match", "export"], "why": "collect= 非キー(集計・付加情報)"},
            "e_dest": {"a": "destination", "d": ["collector", "target", "remote"], "why": "flow exporter の宛先は destination"},
            "e_src": {"a": "source", "d": ["update-source", "origin"], "why": "エクスポートパケットの送信元 IF"},
            "e_proto": {"a": "export-protocol", "d": ["version", "transport"], "why": "export-protocol netflow-v9 | ipfix"},
            "m_exp": {"a": "exporter", "d": ["destination", "export-to"], "why": "monitor は exporter を名前で参照"},
            "m_rec": {"a": "record", "d": ["template", "flow-record"], "why": "monitor は record を名前で参照"},
            "dir": {"a": {"in": "input", "out": "output"}, "d": ["both"], "why": {"in": "入ってくる方向= input", "out": "出ていく方向= output"}},
            "collect_role": {"a": "集計や付加情報(バイト数・パケット数など)", "d": ["フローを識別するキー", "エクスポート先の指定"], "why": "collect は識別に関与しない"},
            "def_ver": {"a": "netflow-v9", "d": ["ipfix", "netflow-v5"], "why": "export-protocol の既定は netflow-v9(実測)"},
            "mon_role": {"a": "キャッシュを持つ実体", "d": ["コレクタへの通信路", "キーの定義"], "why": "フローを溜めるのは monitor"},
            "verify": {"a": "show flow monitor {mon} cache", "d": ["show flow exporter {exp} statistics", "show ip cache flow"], "why": "コレクタ不要でキャッシュを直接見る。show ip cache flow は従来 NetFlow 用"},
        },
        "vars": {"tag": _TAG,
                 "rec": lambda v, w: f"REC-{v['tag']}", "exp": lambda v, w: f"EXP-{v['tag']}", "mon": lambda v, w: f"MON-{v['tag']}",
                 "col": ["198.51.100.100", "203.0.113.50", "192.0.2.25"], "port": ["2055", "9995", "9996"],
                 "ver": ["netflow-v9", "ipfix"], "ifn": ["Ethernet0/0", "GigabitEthernet0/1", "Ethernet0/2"]},
    },
    # ------------------------------------------------------------------ FNF の変更手順(編集ロック)
    {
        "kind": "s_fnf_change",
        "title": "稼働中の FNF を変更するときの手順(使用中オブジェクトのロック)",
        "diagram": None,
        "exhibit": (
            "RT02(config)# flow record {rec}\n"
            "RT02(config-flow-record)# match ipv4 tos\n"
            "% Object is in use\n"
            "RT02(config-flow-record)# exit\n"
            "RT02(config)# interface {ifn}\n"
            "RT02(config-if)# no ip flow monitor {mon} input\n"
            "RT02(config-if)# flow record {rec}\n"
            "RT02(config-flow-record)# match ipv4 tos\n"
            "% Object is in use\n"
        ),
        "text": (
            "レコードのキーを 1 つ追加しようとして拒否された場面である。使用中のレコードのフィールドは «rec_lock» 変更できない。"
            "上のように IF から外しただけでは足りず(実測)、変更するには «steps» という 3 段が要る。"
            "モニタ側の record 行も «overwrite» ので、レコードを差し替えるときは no record → record の 2 段で書く。"
            "エクスポータは扱いが違い、«live_ok» は参照されたままでも変更できるが、«not_live» だけは参照中は変更できない。"
            "新規に組むときは «build_order» の順に投入すれば、このロックには当たらない。変更後は «verify» でフローが採れているかを確認する。"
        ),
        "slots": {
            "rec_lock": {"a": "参照しているモニタが存在する限り", "d": ["IF に適用されている間だけ", "キャッシュにエントリが残っている間だけ"], "why": "monitor が record を参照している限り % Object is in use(実測)"},
            "steps": {"a": "モニタで no record(参照解除)→ レコードを編集 → モニタに record を戻す", "d": ["IF から外す → レコードを編集 → IF に戻す", "clear flow monitor → レコードを編集 → write memory"], "why": "解錠するのは参照解除。IF の付け外しでは解けない(実測)"},
            "overwrite": {"a": "別名で上書きできない", "d": ["いつでも上書きできる", "IF から外せば上書きできる"], "why": "record X のまま record Y は拒否(実測)"},
            "live_ok": {"a": "destination・source・transport udp", "d": ["export-protocol", "record のキー"], "why": "宛先・送信元・ポートはライブ変更可(実測)"},
            "not_live": {"a": "export-protocol", "d": ["destination", "transport udp"], "why": "netflow-v9⇄ipfix の切替は参照中不可(実測)"},
            "build_order": {"a": "record → exporter → monitor → IF 適用", "d": ["IF 適用 → monitor → exporter → record", "exporter → IF 適用 → record → monitor"], "why": "参照される側を先に作る"},
            "verify": {"a": "show flow monitor {mon} cache", "d": ["show flow exporter {exp}", "show ip flow top-talkers"], "why": "採取の確認はキャッシュ"},
        },
        "vars": {"tag": _TAG,
                 "rec": lambda v, w: f"REC-{v['tag']}", "exp": lambda v, w: f"EXP-{v['tag']}", "mon": lambda v, w: f"MON-{v['tag']}",
                 "ifn": ["Ethernet0/0", "GigabitEthernet0/1", "Ethernet0/2"]},
    },
    # ------------------------------------------------------------------ NetFlow のバージョン比較表
    {
        "kind": "s_nf_versions",
        "title": "NetFlow v5 / v9 / IPFIX の違いと従来 NetFlow の有効化",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            '| 項目 | 従来の NetFlow(v5) | NetFlow v9 | IPFIX(v10) |\n'
            '|---|---|---|---|\n'
            '| レコードの形式 | «v5_fmt» | «v9_fmt» | テンプレートベース |\n'
            '| IPv6 / MPLS などのフロー | «v5_v6» | 可 | 可 |\n'
            '| 標準化 | Cisco 独自 | Cisco 独自(RFC 3954 で公開) | «ipfix_std» |\n'
            '| FNF の export-protocol | netflow-v5(v5 固定分のフィールドだけ) | «fnf_def» | ipfix |\n'
            '| 有効化のしかた | «v5_enable» | flow monitor を IF に適用 | flow monitor を IF に適用 |\n'
        ),
        "exhibit_md": True,
        "text": (
            "従来の NetFlow はフローの定義が固定で、キーは «seven» の 7 項目である。v9 と IPFIX はレコードの構成を «tmpl_why» ため、"
            "コレクタはテンプレートを受け取ってからでないとデータレコードを解釈できない。"
            "従来 NetFlow のキャッシュは «trad_cache» で、FNF のキャッシュは `show flow monitor <名> cache` で見る。"
            "従来 NetFlow のエクスポート先は `ip flow-export destination` と `ip flow-export version` で指定する。"
        ),
        "slots": {
            "v5_fmt": {"a": "固定フォーマット(フィールドを変えられない)", "d": ["JSON 形式", "SNMP MIB 経由で取得", "テキスト形式"], "grp": "tbl", "why": "v5 は固定"},
            "v9_fmt": {"a": "テンプレートベース(フィールドを選べる)", "d": ["JSON 形式", "SNMP MIB 経由で取得", "テキスト形式"], "grp": "tbl", "why": "v9 はテンプレートで可変"},
            "v5_v6": {"a": "不可(IPv4 のみ)", "d": ["可", "IPv6 のみ可"], "grp": "tbl", "why": "v5 は IPv4 の固定フィールド"},
            "ipfix_std": {"a": "IETF 標準(RFC 7011)", "d": ["Cisco 独自", "IEEE 標準", "ITU-T 勧告"], "grp": "tbl", "why": "IPFIX は v9 を基に IETF が標準化"},
            "fnf_def": {"a": "netflow-v9(既定)", "d": ["ipfix(既定)", "指定できない"], "grp": "tbl", "why": "export-protocol の既定は netflow-v9(実測)。netflow-v5 も指定できるが v5 固定分のフィールドしか運べない"},
            "v5_enable": {"a": "IF に ip flow ingress / egress", "d": ["flow monitor を IF に適用", "ip flow-top-talkers を有効化"], "grp": "tbl", "why": "従来 NetFlow は IF 単位で有効化"},
            "seven": {"a": "送信元/宛先 IP・送信元/宛先ポート・プロトコル・ToS・入力 IF", "d": ["送信元/宛先 IP・送信元/宛先 MAC・VLAN・入力 IF・出力 IF", "送信元/宛先 IP・パケット数・バイト数・開始時刻・終了時刻・TCP フラグ"], "why": "7 つのキー。パケット数などは非キーの集計値"},
            "tmpl_why": {"a": "テンプレートで先に通知する", "d": ["コレクタ側の設定ファイルで固定する", "SNMP で問い合わせて決める"], "why": "テンプレート方式= 柔軟だがコレクタはテンプレート待ち"},
            "trad_cache": {"a": "show ip cache flow", "d": ["show flow monitor cache", "show ip flow export"], "why": "従来 NetFlow のキャッシュ表示"},
        },
    },
    # ------------------------------------------------------------------ top-talkers と FNF の cache sort
    {
        "kind": "s_nf_top",
        "title": "top-talkers(従来 NetFlow)と FNF の cache sort で上位フローを見る",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "ip flow-export destination {col} {port}\n"
            "ip flow-export version 5\n"
            "!\n"
            "interface {ifn}\n"
            " «ingress»\n"
            "!\n"
            "ip flow-top-talkers\n"
            " «tt_top» {n}\n"
            " «tt_sort» {crit}\n"
            "!\n"
            "RT02# «show_tt»\n"
            "SrcIf   SrcIPaddress   DstIf   DstIPaddress   Pr SrcP DstP Bytes\n"
            "{ifn_s}   {src1}      Et0/1   {dst1}      06 C1A2 0050  {b1}\n"
            "{ifn_s}   {src2}      Et0/1   {dst2}      11 A3F0 0035  {b2}\n"
            "2 of {n} top talkers shown. 2 flows processed.\n"
        ),
        "text": (
            "従来の NetFlow で上位フローを見るには、まず IF に «ingress» を付けて採取を有効にし、`ip flow-top-talkers` 配下で "
            "«tt_top» に表示件数(1〜200)、«tt_sort» に並べ替えの基準(bytes か packets)を書く。結果は «show_tt» で見る。"
            "これは «tt_where» ので、コレクタへのエクスポートが動いていなくても使える。"
            "FNF で同じことをするには «fnf_sort» のようにキャッシュをその場でソートし、末尾に件数の指定を付けて絞る。ただし並べ替えに使えるのは "
            "«sort_cond» だけなので、バイト数で並べたければレコードに collect counter bytes が要る。"
        ),
        "slots": {
            "ingress": {"a": "ip flow ingress", "d": ["ip flow monitor input", "ip route-cache flow", "ip flow-export enable"], "why": "従来 NetFlow の IF 有効化(egress も可)"},
            "tt_top": {"a": "top", "d": ["limit", "max-entries", "count"], "why": "top <1-200>"},
            "tt_sort": {"a": "sort-by", "d": ["order-by", "sort", "rank"], "why": "sort-by bytes | packets"},
            "show_tt": {"a": "show ip flow top-talkers", "d": ["show ip cache flow top", "show flow top-talkers", "show ip flow export"], "why": "末尾に N of M top talkers shown"},
            "tt_where": {"a": "装置上のキャッシュをソートして表示するだけ", "d": ["コレクタに集計させて結果を取り寄せる", "エクスポートパケットを並べ替えて送る"], "why": "ローカルのキャッシュ操作。エクスポートと独立"},
            "fnf_sort": {"a": "show flow monitor {mon} cache sort highest counter bytes", "d": ["show flow monitor {mon} statistics sort bytes", "show flow exporter {exp} cache sort bytes"], "why": "FNF Top N= cache sort highest <field>(末尾に top <n> で件数を絞る)"},
            "sort_cond": {"a": "そのレコードに含まれるフィールド", "d": ["任意のフィールド", "キーに指定したフィールドだけ"], "why": "キャッシュに無い項目では並べられない"},
        },
        "vars": {"tag": _TAG,
                 "mon": lambda v, w: f"MON-{v['tag']}", "exp": lambda v, w: f"EXP-{v['tag']}",
                 "col": ["198.51.100.100", "203.0.113.50", "192.0.2.25"], "port": ["2055", "9995", "9996"],
                 "n": ["10", "20", "5"], "crit": ["bytes", "packets"],
                 "ifn": ["Ethernet0/0", "Ethernet0/2"], "ifn_s": ["Et0/0", "Et0/2"],
                 "src1": ["10.1.1.10", "172.16.20.5", "192.168.7.30"], "dst1": ["10.3.3.100", "172.16.30.9", "192.168.9.40"],
                 "src2": ["10.1.1.11", "172.16.20.6", "192.168.7.31"], "dst2": ["10.3.3.53", "172.16.30.53", "192.168.9.53"],
                 "b1": ["1843200", "921600", "4608000"], "b2": ["61440", "30720", "122880"]},
        "var_links": {"ifn": "ifn_s", "src1": "dst1", "dst1": "src2", "src2": "dst2", "b1": "b2"},
    },
]
