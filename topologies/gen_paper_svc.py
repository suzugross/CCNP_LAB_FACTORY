#!/usr/bin/env python3
"""Services 即答形 紙面ファミリ (BL-170) — gen_paper_mcq.py の shape=svc 素材。

設計= problems/_drafts/PAPER-SVC.design.md。4.0 Services(25%) の「構成 1 画面を見て
60〜90 秒で即答する軽い形」を埋める(BL-145 速筋レーンの弾)。深い形は既存ラボ
(SNMPv3/IP SLA/NetFlow/DHCP)に任せ、本ファミリは「既定値の罠」と「1 行の欠落」を主題にする。

一意性の担保:
  ・知識形(select/select2/allthat/match)= 事実ベース(タグ排他)。mpls の term 群と同型。
  ・分析形(read/fix/cause)= 小さな真偽関数(§下記 MODEL)＋実測 exhibit(poc/svc-paper)。
実測の正典= poc/svc-paper/README.md(iol-xe 17.15・2026-09-13)。
★2026-09-13 ユーザ決定「不確かな問題は捨てる」(公式文書が誤っている/方針未定/不明瞭の可能性があるもの)=
  hidekeys・鍵長や SSHv1 の数値・「ドメイン名が必須」(label 指定なら不要)・v3 の暗号鍵誤り/プロトコル不一致の応答・
  timestamps の既定有無・DNA Center の警告文(出典未検証)は出題から除外した(裏話にも出さない)。

公開 API(copp/mpls と同じ作法):
  KINDS / WORLDS / KIND_WORLDS / kind_forms(kind) / worlds_for(kind)
  draw(rnd, kind, world=None, form=None) -> d
  build_choices_<form>(d, rnd) -> [(text, is_correct, why)]  (match は build_match)
  question_body(d, choices, form) / answer_body(d, choices, form) -> Markdown 断片
  pick_count(form, choices) / selftest()
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["ssh", "snmp", "log", "ntp", "archive", "cef", "copy", "dnac", "light"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}

FORMS = {
    "ssh":     {"select", "allthat", "fix"},
    "snmp":    {"select", "select2", "read"},
    "log":     {"select", "allthat", "read"},
    "ntp":     {"select", "cause"},
    "archive": {"select", "select2", "allthat"},
    "cef":     {"select", "read", "match"},
    "copy":    {"select", "fix"},
    "dnac":    {"select"},
    "light":   {"fix", "cause"},
}
DIFF = {"ssh": 2, "snmp": 3, "log": 2, "ntp": 3, "archive": 2,
        "cef": 3, "copy": 2, "dnac": 3, "light": 3}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# 事実ベース。tag → [(記述, 真偽, 偽なら反証)]
# ★選択肢に因果を書かない(BL-080): 記述は「〜である」で閉じ、理由を付けない。
# ★実測に基づく既定値は poc/svc-paper/README.md(iol-xe 17.15)を正典とする。
#   「定説と違う」実測(hidekeys 既定 ON・鍵長 2048 下限)はユーザ決定により出題から除外
#   (裏話にも出さない)。詳細は poc/svc-paper/README.md「深掘り」節。
# ==========================================================================
FACTS = {
    "ssh": [
        ("SSH のサーバを有効にするには鍵ペア(RSA または EC)の生成が必要であり、鍵が無いあいだ show ip ssh は SSH Disabled と表示する。", True, ""),
        ("ラベルを指定せずに生成した RSA 鍵の名前は、ホスト名とドメイン名から作られる。", True, ""),
        ("crypto key generate rsa に label を指定すると、鍵はその名前で作られる。", True, ""),
        ("SSH を有効にするには、vty 回線の transport input に ssh を含める必要がある。", True, ""),
        ("login local を構成した vty には、ログインのためのローカル・ユーザ名とパスワードが必要である。", True, ""),
        ("vty の access-class は、SSH で接続できる送信元を制限する。", True, ""),
        ("SSH の認証のタイムアウトと再試行の既定値は、それぞれ 120 秒と 3 回である。", True, ""),
        ("SSH のサーバは、鍵ペアが無くても transport input ssh を設定すれば動作する。", False, "鍵が無いと SSH は Disabled のままであり、鍵の生成が必要である。"),
        ("ip ssh authentication-retries は、認証のタイムアウトを秒で指定する。", False, "authentication-retries は再試行の回数であり、タイムアウトは ip ssh time-out で指定する。"),
        ("vty に transport input telnet だけを構成しても、SSH で接続できる。", False, "transport input に ssh が含まれないと SSH の接続は拒否される。"),
        ("access-class は、SSH のサーバのバージョンを制限する。", False, "access-class は接続元アドレスを制限するものであり、バージョンは ip ssh version で制御する。"),
    ],
    "snmp_comm": [
        ("読み取り専用(RO)のコミュニティでは、SNMP の GET は成功するが SET は拒否される。", True, ""),
        ("読み書き(RW)のコミュニティでは、SNMP の GET と SET の両方が成功する。", True, ""),
        ("コミュニティに付与したアクセス・リストが未定義の場合、すべての送信元からのアクセスが許可される。", True, ""),
        ("コミュニティに付与したアクセス・リストが送信元を許可しない場合、要求は応答されない。", True, ""),
        ("RO のコミュニティに SET を試みると、noAccess のエラーが返る。", True, ""),
        ("読み取り専用(RO)のコミュニティでも、SNMP の SET は成功する。", False, "RO では SET は拒否され、noAccess のエラーが返る。"),
        ("コミュニティに付与したアクセス・リストが未定義の場合、すべての送信元が拒否される。", False, "未定義のアクセス・リストの参照は、すべてを許可する(拒否ではない)。"),
        ("SNMP のコミュニティ名は、show running-config には決して表示されない。", False, "コミュニティ名は running-config に平文で表示される(ユーザの v3 鍵とは異なる)。"),
    ],
    "snmp_v3": [
        ("SNMPv3 のセキュリティ・レベル authPriv は、認証と暗号化の両方を行う。", True, ""),
        ("SNMPv3 のグループが priv を要求する場合、authNoPriv での要求は authorizationError となる。", True, ""),
        ("SNMPv3 のユーザの認証パスワードが誤っている場合、Wrong digest(認証の失敗)として扱われる。", True, ""),
        ("存在しない SNMPv3 のユーザで要求すると、Unknown user name として扱われる。", True, ""),
        ("SNMPv3 のユーザ名と鍵は、show running-config には表示されない。", True, ""),
        ("SNMPv3 のセキュリティ・レベル authNoPriv は、暗号化を行う。", False, "authNoPriv は認証のみで、暗号化は行わない。暗号化は authPriv である。"),
        ("SNMPv3 のユーザは、show running-config に鍵を含めて平文で表示される。", False, "v3 のユーザは running-config に表示されず、show snmp user で確認する(鍵は表示されない)。"),
    ],
    "snmp_notify": [
        ("snmp-server host にバージョンを指定しない場合、通知はバージョン 1 のトラップとして送信される。", True, ""),
        ("通知の宛先の UDP ポートを指定しない場合、既定のポートは 162 である。", True, ""),
        ("inform は、バージョン 1 では送信できない(バージョン 2c 以上が必要である)。", True, ""),
        ("trap は確認応答を必要とせず、inform は受信側からの確認応答を受け取るまで再送される。", True, ""),
        ("snmp-server enable traps を引数なしで構成すると、すべての種類の通知が有効になる。", True, ""),
        ("snmp-server host にバージョンを指定しない場合、既定でバージョン 2c の inform が送信される。", False, "既定はバージョン 1 の trap である。"),
        ("trap は、受信側からの確認応答を受け取るまで再送される。", False, "再送されるのは inform であり、trap は送りっぱなしである。"),
        ("inform は、バージョン 1 でも送信できる。", False, "inform はバージョン 2c 以上が必要で、バージョン 1 では送信できない。"),
    ],
    "log_lvl": [
        ("syslog のシビアリティは 0(emergencies)から 7(debugging)まであり、値が小さいほど深刻である。", True, ""),
        ("宛先に設定したレベル以下(それ以上に深刻)のメッセージだけが、その宛先に送られる。", True, ""),
        ("logging trap の既定のレベルは informational(6)である。", True, ""),
        ("コンソール・モニタ・バッファのロギングの既定のレベルは debugging(7)である。", True, ""),
        ("SSH や Telnet のセッションでログを表示するには、terminal monitor が必要である。", True, ""),
        ("logging trap warnings を構成すると、シビアリティ 4 以下のメッセージだけがサーバへ送られる。", True, ""),
        ("syslog のシビアリティは、値が大きいほど深刻である。", False, "値が小さいほど深刻である(0=emergencies が最も深刻)。"),
        ("logging trap の既定のレベルは debugging(7)である。", False, "logging trap の既定は informational(6)である。"),
        ("SSH のセッションには、terminal monitor なしでログが表示される。", False, "vty セッションには terminal monitor が必要である(コンソールは既定で表示)。"),
    ],
    "log_ts": [
        ("service timestamps log datetime msec は、ミリ秒付きの日時をログに付ける。", True, ""),
        ("localtime を付けないと、タイムスタンプは UTC で表示される。", True, ""),
        ("show-timezone を付けると、タイムスタンプにタイムゾーン名が表示される。", True, ""),
        ("service sequence-numbers は、各ログ・メッセージの先頭に連番を付ける。", True, ""),
        ("service timestamps log uptime は、システムの稼働時間でタイムスタンプを付ける。", True, ""),
        ("localtime を付けなくても、clock timezone を設定すればタイムスタンプは現地時刻になる。", False, "clock timezone だけでは UTC 表示のままで、localtime を付けて初めて現地時刻になる。"),
    ],
    "ntp": [
        ("ntp master は、外部の時刻源が無くても、そのルータを NTP のサーバとして動作させる。", True, ""),
        ("ntp master をストラタム値なしで構成すると、既定のストラタムは 8 である。", True, ""),
        ("NTP の認証を有効にするには、鍵の定義・ntp authenticate・ntp trusted-key の 3 つが必要である。", True, ""),
        ("ntp source は、NTP のパケットの送信元アドレスを指定したインターフェイスのものにする。", True, ""),
        ("クライアントは、ntp server コマンドで参照する時刻源を指定する。", True, ""),
        ("show ntp associations は、参照先の同期の状態を表示する。", True, ""),
        ("ntp authenticate を構成するだけで、NTP の認証は完成する。", False, "鍵の定義と ntp trusted-key も必要である。authenticate だけでは同期しない。"),
        ("ntp master の既定のストラタムは 1 である。", False, "既定のストラタムは 8 である。"),
        ("ntp source は、NTP のサーバを指定するコマンドである。", False, "ntp source は送信元インターフェイスの指定であり、サーバの指定は ntp server である。"),
    ],
    "archive": [
        ("archive の path は、構成のバックアップを保存する場所とファイル名の接頭辞を指定する。", True, ""),
        ("archive の write-memory は、write memory のたびに構成を自動で保存する。", True, ""),
        ("archive の time-period は、指定した分の間隔で構成を自動で保存する。", True, ""),
        ("configure replace は、保存済みの構成へ差分だけを適用してロールバックする。", True, ""),
        ("archive の log config は、投入された構成コマンドの変更ログを記録する。", True, ""),
        ("configure replace は、reload を伴って構成を置き換える。", False, "configure replace は reload なしで差分を適用する。"),
        ("archive の time-period の単位は秒である。", False, "time-period の単位は分である。"),
        ("archive の log config は、show や debug のコマンドも記録する。", False, "log config が記録するのは構成コマンドであり、show/debug は記録しない。"),
    ],
    "cef": [
        ("show ip cef の receive のエントリは、ルータ自身に宛てられたアドレスを示す。", True, ""),
        ("show ip cef の attached のエントリは、直結のインターフェイスで解決されるプレフィックスを示す。", True, ""),
        ("show ip cef の drop のエントリは、そのプレフィックス宛のパケットが破棄されることを示す。", True, ""),
        ("Null0 への静的経路は、show ip cef で attached to Null0 として表示される。", True, ""),
        ("next-hop がまだ解決されていない経路は、show ip cef detail で recursive として表示される。", True, ""),
        ("glean の隣接は、直結のサブネット内でまだ解決されていない宛先を示す。", True, ""),
        ("show ip cef の receive のエントリは、他のルータへ転送される経路を示す。", False, "receive はルータ自身に宛てられたアドレスであり、転送先ではない。"),
        ("CEF を無効にすると、ルータはパケットを一切転送できなくなる。", False, "CEF を無効にしてもプロセス・スイッチングで転送は継続する(性能は落ちる)。"),
        ("attached のエントリは、複数ホップ先のネットワークを示す。", False, "attached は直結で解決されるプレフィックスであり、複数ホップ先ではない。"),
    ],
    "copy": [
        ("ftp のコピーでは、ユーザ名とパスワードを ip ftp username / ip ftp password で与えるか、URL の中に含める。", True, ""),
        ("URL の書式は、プロトコル名・二重スラッシュ・ホスト・パスの順である(例 ftp://host/file)。", True, ""),
        ("ルータを SCP のサーバにするには、ip scp server enable が必要である。", True, ""),
        ("aaa new-model を有効にした状態で SCP のサーバを使うには、authorization exec の構成が必要である。", True, ""),
        ("ftp の受動モードは、ip ftp passive で有効にする。", True, ""),
        ("SCP は SSH のうえで動作し、SSH が有効である必要がある。", True, ""),
        ("URL の書式は、プロトコル名の後に単一のスラッシュを 1 つ置く(例 ftp:/host/file)。", False, "二重スラッシュ(ftp://host/file)である。"),
        ("SCP のサーバには、ip scp server enable は不要である。", False, "SCP のサーバには ip scp server enable が必要である。"),
        ("ftp のパスワードは、URL に含めることができない。", False, "ftp://user:pass@host/file の形で URL に含められる。"),
    ],
    "dnac": [
        ("Cisco DNA Center の Assurance は、ネットワークの健全性を可視化し、問題の根本原因を提示する。", True, ""),
        ("NTP の時刻ずれは、ログの相関やアシュアランスの分析を妨げる。", True, ""),
        ("Assurance は、デバイス・クライアント・アプリケーションの健全性スコアを示す。", True, ""),
        ("Cisco DNA Center は、デバイスとの時刻同期のために NTP を使用する。", True, ""),
        ("Cisco DNA Center の Assurance は、構成の自動バックアップを行う機能である。", False, "Assurance は監視・分析の機能であり、バックアップは別の機能である。"),
        ("Cisco DNA Center の Assurance は、機器の CLI に手動でログインして show コマンドを実行することで健全性を判定する。", False, "Assurance は機器から収集したテレメトリ(SNMP・syslog・NetFlow・ストリーミング)をもとに判定する。"),
        ("Assurance の健全性スコアは、値が低いほど健全である。", False, "スコアは 1〜10 で、値が高いほど健全である(低いほど問題がある)。"),
    ],
}

# kind → (設問の主題語, 主タグ, 「真だが設問外」肢を供給するタグ)
FACT_SCOPE = {
    "ssh":     ("SSH の有効化と vty の構成", ["ssh"], ["log_lvl", "copy"]),
    "snmp":    ("SNMP のコミュニティ・v3・通知", ["snmp_comm", "snmp_v3", "snmp_notify"], ["log_lvl", "ntp"]),
    "log":     ("syslog のレベルとタイムスタンプ", ["log_lvl", "log_ts"], ["ntp", "ssh"]),
    "ntp":     ("NTP の同期と認証", ["ntp"], ["log_ts", "snmp_notify"]),
    "archive": ("archive と構成の管理", ["archive"], ["cef", "copy"]),
    "cef":     ("CEF と show ip cef の読み方", ["cef"], ["copy", "archive"]),
    "copy":    ("ファイル転送(tftp/ftp/scp)", ["copy"], ["archive", "ssh"]),
    "dnac":    ("Cisco DNA Center の Assurance", ["dnac"], ["ntp", "log_lvl"]),
}
MATCH_SETS = {
    "cef": [("receive", "ルータ自身に宛てられたアドレスを示すエントリ"),
            ("attached", "直結のインターフェイスで解決されるプレフィックスのエントリ"),
            ("drop", "そのプレフィックス宛のパケットが破棄されるエントリ"),
            ("glean", "直結のサブネット内でまだ解決されていない宛先のエントリ")],
}

# 主題語(read/analysis 用)
NAMES = [["RT01"], ["R1"], ["CORE1"], ["EDGE-1"]]


# ==========================================================================
# 盤面の抽選
# ==========================================================================
def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    d["host"] = rnd.choice(NAMES)[0]
    # ★分析形の盤面は form に依らず kind で用意する(pick_draw_svc は form を
    #   決める前に draw を呼ぶため)。知識形はこの追加状態を無視する。
    if kind == "snmp":
        _draw_snmp_read(d, rnd)
    elif kind == "cef":
        _draw_cef_read(d, rnd)
    elif kind == "log":
        _draw_log_read(d, rnd)
    elif kind == "ssh":
        _draw_ssh_fix(d, rnd)
    elif kind == "copy":
        _draw_copy_fix(d, rnd)
    elif kind == "ntp":
        _draw_ntp_cause(d, rnd)
    elif kind == "light":
        _draw_light(d, rnd, form)
    return d


# ==========================================================================
# 事実ベースの選択肢(select / select2 / allthat / match)
# ==========================================================================
def _fact_choices(d, rnd, n_true, n_total, offscope=True):
    subject, tags, off_tags = FACT_SCOPE[d["kind"]]
    pool_t = [(t, w) for tag in tags for t, tv, w in FACTS[tag] if tv]
    pool_f = [(t, w) for tag in tags for t, tv, w in FACTS[tag] if not tv]
    if len(pool_t) < n_true:
        raise ValueError(f"{d['kind']}: 真の肢が足りない")
    trues = rnd.sample(pool_t, n_true)
    c = [(t, True, "") for t, _ in trues]
    n_false = n_total - n_true
    if offscope and n_false >= 3:
        off = [(t, w) for tag in off_tags for t, tv, w in FACTS[tag] if tv]
        t, _ = rnd.choice(off)
        c.append((t, False, f"記述そのものは正しいが、設問({subject})についての記述ではない。"))
        n_false -= 1
    if len(pool_f) < n_false:
        raise ValueError(f"{d['kind']}: 偽の肢が足りない")
    for t, w in rnd.sample(pool_f, n_false):
        c.append((t, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select(d, rnd):
    return _fact_choices(d, rnd, n_true=1, n_total=4)


def build_choices_select2(d, rnd):
    return _fact_choices(d, rnd, n_true=2, n_total=5)


def build_choices_allthat(d, rnd):
    """数非明示。正解数は 1〜4 を抽選(選択肢 5)。"""
    n_true = rnd.choice([1, 2, 2, 3, 3, 4])
    return _fact_choices(d, rnd, n_true=n_true, n_total=5, offscope=(n_true <= 2))


def build_match(d, rnd):
    items = list(MATCH_SETS[d["kind"]])
    rnd.shuffle(items)
    terms = [("①②③④"[i], t) for i, (t, _) in enumerate(items)]
    descs = list(enumerate(items))
    rnd.shuffle(descs)
    letters = "ABCD"
    choices = [(letters[j], items[i][1]) for j, (i, _) in enumerate(descs)]
    ans = {}
    for j, (i, _) in enumerate(descs):
        ans["①②③④"[i]] = letters[j]
    return terms, choices, dict(sorted(ans.items()))


CORE = {
    "ssh": "SSH の有効化には ①鍵ペア(RSA または EC)の生成 ②vty の transport input ssh ③認証手段(login local+ユーザ / aaa)が要る。access-class は接続元を絞る。既定のタイムアウト 120 秒・再試行 3 回。鍵名はラベル無しならホスト名.ドメイン名。鍵長やバージョンの数値は版に依存するので問わない。",
    "snmp": "RO は GET のみ(SET は noAccess)・RW は両方。コミュニティの ACL が未定義なら全許可(参照先が無い ACL は拒否しない)・許可しない ACL なら無応答。v3 は authPriv=認証+暗号、priv 要求への authNoPriv は authorizationError、認証鍵誤り=Wrong digest、未定義ユーザ=Unknown user。v3 の鍵は running-config に出ない。",
    "log": "シビアリティ 0(emerg)〜7(debug)、小さいほど深刻。宛先はレベル以下を表示。既定= console/monitor/buffered は debugging、trap は informational。vty は terminal monitor が要る。timestamps は datetime[msec][localtime][show-timezone]/uptime、localtime 無しは UTC。sequence-numbers は連番。",
    "ntp": "ntp master は外部源なしでサーバ化(既定ストラタム 8)。認証は 鍵定義+ntp authenticate+ntp trusted-key の 3 点が揃って初めて成立。ntp source は送信元 IF、ntp server は参照先。show ntp associations/status で同期と認証を読む。",
    "archive": "archive の path/write-memory/time-period(分)で構成を自動保存。configure replace は reload なしで差分ロールバック。log config は構成コマンドの変更ログ(show/debug は記録しない)。",
    "cef": "show ip cef の receive=自分宛、attached=直結解決、drop=破棄、glean=直結内で未解決、recursive=next-hop 未解決。Null0 静的は attached to Null0。CEF 無効でもプロセス・スイッチングで転送は継続。",
    "copy": "URL は proto://host/path。ftp は ip ftp username/password か URL 埋め込み、passive は ip ftp passive。SCP サーバは ip scp server enable が要り、aaa new-model 時は authorization exec も要る。SCP は SSH の上で動く。",
    "dnac": "Cisco DNA Center の Assurance は、機器から集めたテレメトリで健全性を可視化し根本原因を提示する(設定変更やバックアップの機能ではない)。デバイス/クライアント/アプリのスコア(1〜10・高いほど健全)を示す。時刻同期(NTP)がずれると相関・分析が乱れる。",
    "light": "監視・可用性の構成は 1 行の欠落で機能しない: IP SLA は schedule と track、NetFlow は monitor へのエクスポータの参照とインターフェイス適用、DHCP は helper-address と excluded-address が要る。",
}


# ==========================================================================
# 分析形の真偽関数モデル(§4)と exhibit(poc/svc-paper の実測書式)
# ==========================================================================
# ---- SNMP read: コミュニティ + ACL で GET/SET の帰結 ----------------------
def _draw_snmp_read(d, rnd):
    poller = "10.1.10.6"
    d["poller"] = poller
    scenarios = [
        ("ro_ok", "RO", None, "get", "ok"),
        ("ro_set", "RO", None, "set", "noaccess"),
        ("rw_ok", "RW", "permit_poller", "set", "ok"),
        ("rw_blocked", "RW", "deny_poller", "get", "timeout"),
        ("undef_acl", "RO", "undef", "get", "ok"),
    ]
    key, access, acl, op, result = rnd.choice(scenarios)
    d["snmp"] = {"key": key, "access": access, "acl": acl, "op": op, "result": result,
                 "comm": rnd.choice(["NMSRO", "PUBLIC-RO", "MONzbx", "NOCrw", "PRIV-RW"]),
                 "aclnum": rnd.choice([10, 20, 55, 99])}


def _snmp_exhibit(d):
    s = d["snmp"]
    lines = [f"{d['host']}# show running-config | include snmp-server community"]
    tail = f" {s['aclnum']}" if s["acl"] else ""
    lines.append(f"snmp-server community {s['comm']} {s['access']}{tail}")
    body = "\n".join(lines)
    acl = ""
    if s["acl"] == "permit_poller":
        acl = f"\n\n{d['host']}# show access-lists {s['aclnum']}\nStandard IP access list {s['aclnum']}\n    10 permit {d['poller']}"
    elif s["acl"] == "deny_poller":
        acl = f"\n\n{d['host']}# show access-lists {s['aclnum']}\nStandard IP access list {s['aclnum']}\n    10 permit 10.1.10.99"
    elif s["acl"] == "undef":
        acl = f"\n\n{d['host']}# show access-lists {s['aclnum']}\n(アクセス・リスト {s['aclnum']} は定義されていない)"
    return body + acl


SNMP_RESULTS = {
    "ok": "要求は成功する。",
    "noaccess": "要求は失敗し、noAccess のエラーが返る。",
    "timeout": "要求は応答されない(タイムアウトする)。",
}
SNMP_WHY = {
    "ok": "アクセス権と(あれば)アクセス・リストの条件を満たしており、要求は成功する。",
    "noaccess": "読み取り専用のコミュニティに対する SET であり、拒否される。",
    "timeout": "アクセス・リストが送信元を許可しておらず、要求に応答がない。",
}


def build_choices_read(d, rnd):
    if d["kind"] == "snmp":
        return _snmp_read_choices(d, rnd)
    if d["kind"] == "cef":
        return _cef_read_choices(d, rnd)
    if d["kind"] == "log":
        return _log_read_choices(d, rnd)
    raise ValueError(d["kind"])


def _snmp_read_choices(d, rnd):
    truth = d["snmp"]["result"]
    c = [(SNMP_RESULTS[truth], True, "")]
    for r in [x for x in ("ok", "noaccess", "timeout") if x != truth]:
        c.append((SNMP_RESULTS[r], False, SNMP_WHY[r]))
    # 4 肢目: 反対の操作の帰結を混ぜる(近接錯乱)
    extra = "要求は成功するが、値は読み取り専用として扱われる。" if truth != "ok" \
        else "要求は失敗し、認証のエラーが返る。"
    c.append((extra, False, "v2c のコミュニティでは、一致しない要求や許可されない要求に応答は返らず、マネージャにエラーは届かない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- CEF read: プレフィックスの種別 ---------------------------------------
def _draw_cef_read(d, rnd):
    types = ["receive", "attached_conn", "attached_adj", "null0", "recursive", "glean"]
    d["cef"] = {"type": rnd.choice(types),
                "net": f"10.{rnd.randint(1, 250)}.{rnd.randint(0, 250)}.0",
                "nh": f"10.99.{rnd.randint(1, 250)}.{rnd.randint(1, 250)}",
                "oif": rnd.choice(["Ethernet0/0", "Ethernet0/1", "GigabitEthernet0/0"])}


CEF_ANS = {
    "receive": "このエントリは、ルータ自身に宛てられたアドレス(receive)を示している。",
    "attached_conn": "このエントリは、直結のサブネット(attached/connected)を示している。",
    "attached_adj": "このエントリは、直結で解決された隣接(attached)を示している。",
    "null0": "このエントリは、Null0 へ送られて破棄される経路を示している。",
    "recursive": "このエントリは、next-hop がまだ解決されていない(recursive)ことを示している。",
    "glean": "このエントリは、直結のサブネット内でまだ解決されていない宛先(glean)を示している。",
}
CEF_WHY = {
    "receive": "自身宛のエントリなら flags に receive, local が付き、receive for <IF> の行が出る。この出力には無い。",
    "attached_conn": "直結サブネットのエントリなら flags に connected(と cover dependents)が付く。この出力の flags にはそれが無い。",
    "attached_adj": "解決済みの隣接ならホスト /32 のエントリで Adj source: IP adj out of <IF> の行が付く。この出力には無い。",
    "null0": "Null0 宛なら attached to Null0 と表示される。この出力の出口は Null0 ではない。",
    "recursive": "next-hop 未解決なら recursive via <next-hop> の行が出る。この出力には無い。",
    "glean": "glean(直結内で未解決)のエントリは flags が attached だけで Adj source が無く、出口インターフェイスに attached と出る。この出力はそれとは異なる。",
}


def _cef_exhibit(d):
    t = d["cef"]["type"]
    net, nh, oif = d["cef"]["net"], d["cef"]["nh"], d["cef"]["oif"]
    oifs = oif.replace("Ethernet", "Et").replace("GigabitEthernet", "Gi")
    h = f"{d['host']}# show ip cef {net}/24 detail"
    if t == "receive":
        h = f"{d['host']}# show ip cef {net[:-1]}1/32 detail"
        return f"{h}\n{net[:-1]}1/32, epoch 0, flags [receive, local, source eligible]\n  Interface source: {oifs} flags: local, source eligible flags3: none\n  receive for {oifs}"
    if t == "attached_conn":
        return f"{h}\n{net}/24, epoch 0, flags [attached, connected, cover dependents, need deagg]\n  Covered dependent prefixes: 3\n    need deagg: 2\n    notify cover updated: 1\n  attached to {oifs}"
    if t == "attached_adj":
        h = f"{d['host']}# show ip cef {net[:-1]}2/32 detail"
        return f"{h}\n{net[:-1]}2/32, epoch 0, flags [attached]\n  Adj source: IP adj out of {oifs}, addr {net[:-1]}2\n  attached to {oifs}"
    if t == "null0":
        return f"{h}\n{net}/24, epoch 0, flags [attached]\n  attached to Null0"
    if t == "recursive":
        return f"{h}\n{net}/24, epoch 0\n  recursive via {nh}\n    recursive via {nh.rsplit('.', 1)[0]}.0/24\n      attached to {oifs}"
    if t == "glean":
        return f"{h}\n{net}/24, epoch 0, flags [attached]\n  attached to {oifs}"
    return h


def _cef_read_choices(d, rnd):
    truth = d["cef"]["type"]
    c = [(CEF_ANS[truth], True, "")]
    pool = [x for x in CEF_ANS if x != truth]
    # attached_conn と attached_adj は文面が近いので必ず対で混ぜる
    if truth in ("attached_conn", "attached_adj"):
        alt = "attached_adj" if truth == "attached_conn" else "attached_conn"
        pool.remove(alt)
        picks = [alt] + rnd.sample(pool, 2)
    else:
        picks = rnd.sample(pool, 3)
    for r in picks:
        c.append((CEF_ANS[r], False, CEF_WHY[r]))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- LOG read: timestamps の見え方 ----------------------------------------
def _draw_log_read(d, rnd):
    forms = [
        ("datetime_msec", "service timestamps log datetime msec", None, "*Sep 13 09:18:39.349:"),
        ("datetime", "service timestamps log datetime", None, "*Sep 13 09:18:37:"),
        ("localtime_tz", "service timestamps log datetime msec localtime show-timezone", "clock timezone JST 9 0", "*Sep 13 18:18:40.962 JST:"),
        ("localtime", "service timestamps log datetime localtime", "clock timezone JST 9 0", "*Sep 13 18:18:44:"),
        ("year", "service timestamps log datetime year", None, "*Sep 13 2026 09:18:42:"),
        ("uptime", "service timestamps log uptime", None, "00:04:18:"),
        ("none", "no service timestamps log", None, "(タイムスタンプなし)"),
        ("seq", "service sequence-numbers\nservice timestamps log datetime msec", None, "000123: *Sep 13 09:18:45.100:"),
    ]
    d["log"] = dict(zip(("key", "cfg", "clk", "stamp"), rnd.choice(forms)))


def _log_exhibit(d):
    L = [f"{d['host']}# show running-config | include service timestamps|clock timezone"]
    L += d["log"]["cfg"].split("\n")
    if d["log"]["clk"]:
        L.append(d["log"]["clk"])
    return "\n".join(L)


def _log_stamp_desc(stamp):
    if stamp == "(タイムスタンプなし)":
        return "ログ・メッセージにタイムスタンプは付かない。"
    return f"ログ・メッセージの先頭は `{stamp}` の形になる。"


def _log_read_choices(d, rnd):
    truth = d["log"]["stamp"]
    allf = [
        "*Sep 13 09:18:39.349:", "*Sep 13 09:18:37:", "*Sep 13 18:18:40.962 JST:",
        "*Sep 13 18:18:44:", "*Sep 13 2026 09:18:42:", "00:04:18:",
        "(タイムスタンプなし)", "000123: *Sep 13 09:18:45.100:",
    ]
    others = [x for x in allf if x != truth]
    c = [(_log_stamp_desc(truth), True, "")]
    for r in rnd.sample(others, 3):
        c.append((_log_stamp_desc(r), False, "示されている service timestamps の構成では、この形にはならない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- SSH fix: 足りない 1 つを補う候補がちょうど 1 つ -----------------------
SSH_REQS = ["key", "transport", "auth"]
SSH_FIX = {
    "key": ("crypto key generate rsa modulus 2048", "RSA 鍵を生成して SSH のサーバを有効にする。"),
    "transport": ("line vty 0 4\n transport input ssh", "vty の transport input に ssh を含める。"),
    "auth": ("line vty 0 4\n login local", "vty にローカル認証を構成する(ユーザは定義済み)。"),
}
SSH_WRONG = {
    "key": ("ip ssh time-out 60", "タイムアウトの変更であり、欠けている鍵ペアを補わない。"),
    "transport": ("line vty 0 4\n transport output ssh", "output の指定であり、着信(input)に ssh を許可しない。"),
    "auth": ("line vty 0 4\n no login", "認証を無くす構成であり、要件(認証手段の構成)を満たさない。"),
}


def _draw_ssh_fix(d, rnd):
    d["ssh_missing"] = rnd.choice(SSH_REQS)


def build_choices_fix(d, rnd):
    if d["kind"] == "ssh":
        return _ssh_fix_choices(d, rnd)
    if d["kind"] == "copy":
        return _copy_fix_choices(d, rnd)
    if d["kind"] == "light":
        return _light_fix_choices(d, rnd)
    raise ValueError(d["kind"])


def _ssh_exhibit(d):
    miss = d["ssh_missing"]
    L = [f"{d['host']}# show running-config"]
    L.append(f"hostname {d['host']}")
    L.append("ip domain name example.com")
    L.append("!")
    if miss == "key":
        L.append("! (鍵ペアは生成されていない)")
    else:
        L.append("! (RSA 鍵ペアは生成済み)")
    L.append("username admin privilege 15 secret 9 xxxxx")
    L += ["line vty 0 4"]
    if miss == "transport":
        L.append(" transport input telnet")
    else:
        L.append(" transport input ssh")
    if miss == "auth":
        L.append(" no login")
    else:
        L.append(" login local")
    return "\n".join(L)


def _ssh_fix_choices(d, rnd):
    miss = d["ssh_missing"]
    cfg, _ = SSH_FIX[miss]
    c = [(cfg, True, "")]
    others = [r for r in SSH_REQS if r != miss]
    for r in rnd.sample(others, 2):
        # 別の要件を直す候補(この盤面では既に満たされている=無駄)
        cli, _ = SSH_FIX[r]
        c.append((cli, False, "その構成は、この盤面では既に満たされており、SSH が使えない原因を解消しない。"))
    wrong_cli, wrong_why = SSH_WRONG[miss]
    c.append((wrong_cli, False, wrong_why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- COPY fix: 正しい URL/構成の組を選ぶ -----------------------------------
def _draw_copy_fix(d, rnd):
    """ftp= この装置がクライアント(サーバは認証を要求・匿名拒否・ip ftp username/password 未構成)。
    scp= この装置がサーバ(管理端末が取得・aaa new-model 有効・実測 S10-4: authorization exec が要る)。"""
    d["copy"] = {"proto": rnd.choice(["ftp", "scp"]),
                 "srv": f"10.1.10.{rnd.randint(2, 250)}",
                 "user": rnd.choice(["backup", "netops", "svcacct"]),
                 "pw": rnd.choice(["Ftp#2026", "Backup!9", "cisco123"]),
                 "file": rnd.choice(["RT01.cfg", "backup.cfg", "config.txt"])}


def _copy_fix_choices(d, rnd):
    cp = d["copy"]
    srv, user, f = cp["srv"], cp["user"], cp["file"]
    pw = cp["pw"]
    if cp["proto"] == "ftp":
        correct = (f"copy running-config ftp://{user}:{pw}@{srv}/{f}", "")
        wrongs = [
            (f"copy running-config ftp:/{user}:{pw}@{srv}/{f}",
             "スラッシュが 1 つであり、URL の書式(二重スラッシュ)を満たさない。"),
            (f"copy running-config ftp://{srv}/{f}",
             "認証情報が無いので既定の匿名ログインになり、匿名を拒否するサーバには保存できない(ip ftp username/password も構成されていない)。"),
            (f"copy running-config tftp://{user}:{pw}@{srv}/{f}",
             "tftp には認証の仕組みが無く、URL に認証情報を含める形も無い(ftp と混同している)。"),
        ]
    else:
        correct = ("ip scp server enable\naaa authorization exec default local", "")
        wrongs = [
            ("ip scp server enable",
             "aaa new-model が有効な装置では、exec の認可が無いと SCP の取得が Privilege denied で失敗する。"),
            ("aaa authorization exec default local",
             "SCP のサーバ機能(ip scp server enable)が有効になっておらず、取得できない。"),
            (f"ip ftp username {user}\nip ftp password {pw}",
             "ip ftp のユーザ名/パスワードは、この装置が FTP のクライアントになるときの設定であり、SCP のサーバ機能とは関係しない。"),
        ]
    c = [(correct[0], True, "")] + [(t, False, w) for t, w in wrongs]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- NTP cause: 同期しない原因 --------------------------------------------
NTP_CAUSES = {
    "no_trusted": "ntp trusted-key が構成されておらず、認証が完成していない",
    "key_mismatch": "クライアントとサーバで NTP の認証鍵の値が一致していない",
    "no_server_reach": "ntp server で指定した時刻源へ到達できない",
    "no_authenticate": "ntp authenticate が構成されておらず、鍵が照合されない",
    "source_unreach": "ntp source で指定した送信元アドレスへの戻り経路がサーバに無い",
}
NTP_REFUTE = {
    "no_server_reach": "サーバへは到達できており(associations に候補として現れている)、原因ではない。",
    "no_authenticate": "ntp authenticate は構成されており(running-config に現れている)、原因ではない。",
    "source_unreach": "ntp source は構成されておらず、送信元は既定のインターフェイスである。",
}


def _draw_ntp_cause(d, rnd):
    truth = rnd.choice(["no_trusted", "key_mismatch"])
    d["ntp"] = {"cause": truth, "srv": f"10.99.{rnd.randint(1, 250)}.2",
                "keyid": rnd.choice([1, 5, 10])}


def build_choices_cause(d, rnd):
    if d["kind"] == "ntp":
        return _ntp_cause_choices(d, rnd)
    if d["kind"] == "light":
        return _light_cause_choices(d, rnd)
    raise ValueError(d["kind"])


def _ntp_exhibit(d):
    n = d["ntp"]
    L = [f"{d['host']}# show running-config | include ntp"]
    L.append(f"ntp authentication-key {n['keyid']} md5 <hidden>")
    L.append("ntp authenticate")
    if n["cause"] != "no_trusted":
        L.append(f"ntp trusted-key {n['keyid']}")
    L.append(f"ntp server {n['srv']} key {n['keyid']}")
    L.append("")
    L.append(f"{d['host']}# show ntp associations")
    L.append("  address         ref clock       st   when   poll reach  delay  offset   disp")
    # ★実測(poc/svc-paper S6): 認証が完成しないと ref clock 欄が .AUTH.・reach 0 のまま。
    #   trusted-key の欠落(no_trusted)も鍵値の不一致(key_mismatch)も、この指紋で現れる。
    #   どちらかは running-config(ntp trusted-key 行の有無)で切り分ける。
    L.append(f" ~{n['srv']:<14} .AUTH.          16      -     64     0  0.000   0.000 15937.")
    L.append(" * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured")
    return "\n".join(L)


def _ntp_cause_choices(d, rnd):
    truth = d["ntp"]["cause"]
    c = [(NTP_CAUSES[truth], True, "")]
    alt = "key_mismatch" if truth == "no_trusted" else "no_trusted"
    why_alt = ("鍵の値の不一致ではなく、trusted-key の欠落が原因である(鍵の値は照合の前に信頼される必要がある)。"
               if truth == "no_trusted" else
               "trusted-key は構成されており、原因は鍵の値の不一致である。")
    c.append((NTP_CAUSES[alt], False, why_alt))
    for k in rnd.sample(list(NTP_REFUTE), 3):
        c.append((NTP_CAUSES[k], False, NTP_REFUTE[k]))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- LIGHT: 監視・可用性の 1 行欠落(fix / cause) -------------------------
LIGHT_CASES = {
    "ipsla_sched": {
        "topic": "IP SLA",
        "exhibit": ("ip sla 1\n icmp-echo {beacon} source-interface {sif}\ntrack 1 ip sla 1 reachability\n"
                    "ip route 0.0.0.0 0.0.0.0 {nh} track 1"),
        "symptom": "track 1 が Down のままで、既定経路が挿入されない。",
        "cause": "ip sla の動作がスケジュールされていない",
        "fix": ("ip sla schedule 1 life forever start-time now", "SLA の動作をスケジュールして開始する。"),
        "wrong_fix": [("track 1 ip sla 1 state", "track のオブジェクトの種類の変更であり、SLA が動いていないことを解消しない。"),
                      ("ip sla enable reaction-alerts", "反応の通知の設定であり、スケジュールの欠落を補わない。")],
        "refute": {"track_wrong": "track は ip sla 1 を参照しており、番号は一致している。",
                   "no_route": "既定経路は track 付きで構成されており、経路の記述の誤りではない。"},
        "distract": {"track_wrong": "track が参照する SLA の番号が誤っている",
                     "no_route": "既定経路に track が付いていない"},
    },
    "nfe_apply": {
        "topic": "Flexible NetFlow",
        "exhibit": ("flow record REC\n match ipv4 source address\n match ipv4 destination address\n collect counter bytes\n"
                    "flow exporter EXP\n destination {col}\n transport udp 2055\n"
                    "flow monitor MON\n record REC\n exporter EXP"),
        "symptom": "コレクタにフローが届かず、インターフェイスの統計にもフローが現れない。",
        "cause": "flow monitor がインターフェイスに適用されていない",
        "fix": ("interface {sif}\n ip flow monitor MON input", "監視をインターフェイスの input に適用する。"),
        "wrong_fix": [("flow exporter EXP\n transport udp 9996", "エクスポートの UDP ポートの変更であり、監視が適用されていないことを解消しない。"),
                      ("flow monitor MON\n cache timeout active 60", "キャッシュのタイムアウトの調整であり、適用の欠落を補わない。")],
        "refute": {"no_exp": "monitor には exporter EXP が構成されている。",
                   "no_rec": "monitor には record REC が構成されている。"},
        "distract": {"no_exp": "flow monitor にエクスポータが構成されていない",
                     "no_rec": "flow monitor にレコードが構成されていない"},
    },
    "dhcp_helper": {
        "topic": "DHCP リレー",
        "exhibit": ("interface {sif}\n ip address 192.168.20.1 255.255.255.0\n! (クライアントを収容)\n"
                    "! DHCP サーバは {col} に存在する"),
        "symptom": "この LAN のクライアントが IP アドレスを取得できない。",
        "cause": "クライアントを収容するインターフェイスに ip helper-address が構成されていない",
        "fix": ("interface {sif}\n ip helper-address {col}", "収容インターフェイスにサーバ宛の helper-address を構成する。"),
        "wrong_fix": [("ip dhcp excluded-address 192.168.20.1 192.168.20.10", "サーバ側の除外の設定であり、リレーの helper-address の欠落を補わない。"),
                      ("service dhcp", "既定で有効なサービスであり、helper-address の欠落を解消しない。")],
        "refute": {"pool": "この機はリレーであり、ローカルのプールの問題ではない。",
                   "excl": "除外アドレスの設定はサーバ側の話であり、この LAN の未取得の原因ではない。"},
        "distract": {"pool": "この機の DHCP プールのサブネットが誤っている",
                     "excl": "除外アドレスの範囲が広すぎる"},
    },
}


def _draw_light(d, rnd, form):
    key = rnd.choice(list(LIGHT_CASES))
    tmpl = LIGHT_CASES[key]
    subs = {"beacon": f"8.8.{rnd.randint(1,250)}.8", "sif": rnd.choice(["Ethernet0/0", "GigabitEthernet0/1"]),
            "nh": f"203.0.113.{rnd.randint(1,250)}", "col": f"10.1.{rnd.randint(1,250)}.{rnd.randint(2,250)}"}
    d["light"] = {"key": key, "subs": subs, "form": form}


def _light_exhibit(d):
    tmpl = LIGHT_CASES[d["light"]["key"]]
    return f"{d['host']}# show running-config(抜粋)\n" + tmpl["exhibit"].format(**d["light"]["subs"])


def _light_fix_choices(d, rnd):
    tmpl = LIGHT_CASES[d["light"]["key"]]
    subs = d["light"]["subs"]
    fix_cli, _ = tmpl["fix"]
    c = [(fix_cli.format(**subs), True, "")]
    for cli, why in tmpl["wrong_fix"]:
        c.append((cli.format(**subs), False, why))
    # 4 肢目: 別ケースの正解(topic 外)
    other = rnd.choice([k for k in LIGHT_CASES if k != d["light"]["key"]])
    ocli, _ = LIGHT_CASES[other]["fix"]
    c.append((ocli.format(**subs), False, "別の機能の構成であり、この事象には関係しない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _light_cause_choices(d, rnd):
    tmpl = LIGHT_CASES[d["light"]["key"]]
    c = [(tmpl["cause"], True, "")]
    for k, txt in tmpl["distract"].items():
        c.append((txt, False, tmpl["refute"][k]))
    # もう 1 つ topic 外の錯乱
    other = rnd.choice([k for k in LIGHT_CASES if k != d["light"]["key"]])
    c.append((LIGHT_CASES[other]["cause"], False, "別の機能に関する記述であり、示された構成の事象の原因ではない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# Markdown(設問本文と解答本文)
# ==========================================================================
ASK_FACT = {
    "select": "{subject}について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)",
    "select2": "{subject}について、正しく述べられているものを、次のうちから 2 つ選択してください。",
    "allthat": "{subject}について、正しく述べられているものを、すべて選んでください。",
    "match": "{subject}について、左側の①〜④の項目に対応する説明を、右側の A〜D から選択してください。",
}


def question_body(d, choices, form):
    """(before_ask, ask_text, choices_md, terms_md or "") を返す。"""
    kind = d["kind"]
    subject = FACT_SCOPE.get(kind, (CORE[kind],))[0]
    if form in ("select", "select2", "allthat", "match"):
        ask = ASK_FACT[form].format(subject=subject)
        if form == "match":
            terms, ch, _ = choices
            terms_md = "### 対応させる項目\n\n| # | 項目 |\n|---|------|\n" + "\n".join(f"| {k} | {t} |" for k, t in terms)
            ch_md = "\n\n".join(f"{k}. {t}" for k, t in ch)
            return "", ask, ch_md, terms_md
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "", ask, ch_md, ""
    # 分析形
    before, ask = _analysis_body(d, form)
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices)) \
        if form != "fix" else \
        "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def _analysis_body(d, form):
    kind = d["kind"]
    if kind == "snmp":     # read
        ex = _snmp_exhibit(d)
        op = "GET(読み取り)" if d["snmp"]["op"] == "get" else "SET(書き込み)"
        ask = (f"管理ステーション {d['snmp']['comm'] and d['poller']} から、コミュニティ "
               f"`{d['snmp']['comm']}` を用いて {op} を行います。この要求の結果として"
               "最も適切なものは、次のうちどれですか。(1つを選択してください)")
        return f"次の構成が示されています。\n\n```\n{ex}\n```", ask
    if kind == "cef":      # read
        ex = _cef_exhibit(d)
        ask = "次の出力が示すエントリについて、正しく述べているものは、次のうちどれですか。(1つを選択してください)"
        return f"```\n{ex}\n```", ask
    if kind == "log":      # read
        ex = _log_exhibit(d)
        ask = ("この構成のルータで、シビアリティ 4 のログ・メッセージがバッファに記録されるとき、"
               "その行の見え方として最も適切なものは、次のうちどれですか。(1つを選択してください)")
        return f"次の構成が示されています。\n\n```\n{ex}\n```", ask
    if kind == "ssh":      # fix
        ex = _ssh_exhibit(d)
        ask = ("このルータでは、SSH による接続ができません。接続を可能にするために"
               "追加すべき構成として最も適切なものは、次のうちどれですか。(1つを選択してください)")
        return f"次の構成が示されています。\n\n```\n{ex}\n```", ask
    if kind == "copy":     # fix
        cp = d["copy"]
        if cp["proto"] == "ftp":
            before = (f"FTP のサーバ {cp['srv']} は、ユーザ名 `{cp['user']}`・パスワード `{cp['pw']}` での認証を要求し、"
                      "匿名のログインを拒否します。この装置には ip ftp username および ip ftp password は構成されていません。")
            ask = (f"この装置の running-config を、このサーバへファイル名 `{cp['file']}` で保存するコマンドとして"
                   "正しいものは、次のうちどれですか。(1つを選択してください)")
        else:
            before = (f"この装置では aaa new-model が有効で、ログインの認証はローカルのユーザ名データベース(ユーザ `{cp['user']}`・"
                      "特権レベル 15)で構成されています。管理端末から SCP でこの装置の running-config を取得できるようにします。")
            ask = ("この装置に追加すべき構成として最も適切なものは、次のうちどれですか。(1つを選択してください)")
        return before, ask
    if kind == "ntp":      # cause
        ex = _ntp_exhibit(d)
        ask = ("このルータは、指定した NTP のサーバと同期しません。この事象の原因として"
               "最も適切なものは、次のうちどれですか。(1つを選択してください)")
        return f"次の構成と出力が示されています。\n\n```\n{ex}\n```", ask
    if kind == "light":
        ex = _light_exhibit(d)
        tmpl = LIGHT_CASES[d["light"]["key"]]
        if form == "fix":
            ask = (f"{tmpl['symptom']} この事象を解消するために必要な構成として"
                   "最も適切なものは、次のうちどれですか。(1つを選択してください)")
        else:
            ask = (f"{tmpl['symptom']} この事象の原因として最も適切なものは、"
                   "次のうちどれですか。(1つを選択してください)")
        return f"```\n{ex}\n```", ask
    raise ValueError(kind)


def answer_body(d, choices, form):
    if form == "match":
        terms, ch, ans = choices
        lines = ["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "", CORE[d["kind"]]]
        return "\n".join(lines)
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    return "\n".join(lines)


def pick_count(form, choices):
    if form == "allthat":
        return -1
    if form == "select2":
        return 2
    return 1


# ==========================================================================
# selftest
# ==========================================================================
def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = draw(rnd, kind, None, form)
                    if form == "match":
                        terms, ch, ans = build_match(d, rnd)
                        assert len(ans) == 4 and len(set(ans.values())) == 4, "全単射でない"
                        want = dict(MATCH_SETS[kind])
                        got = {t: dict(ch)[ans[k]] for k, t in terms}
                        assert got == want, "対応が壊れた"
                        choices = (terms, ch, ans)
                    else:
                        fn = {"select": build_choices_select, "select2": build_choices_select2,
                              "allthat": build_choices_allthat, "read": build_choices_read,
                              "fix": build_choices_fix, "cause": build_choices_cause}[form]
                        choices = fn(d, rnd)
                        n_true = sum(1 for x in choices if x[1])
                        want = {"select": 1, "select2": 2, "read": 1, "fix": 1, "cause": 1}.get(form)
                        if form == "allthat":
                            assert 1 <= n_true <= 4, f"allthat 正解数 {n_true}"
                        else:
                            assert n_true == want, f"{form} 正解数 {n_true}"
                        texts = [x[0] for x in choices]
                        assert len(set(texts)) == len(texts), "選択肢の重複"
                        assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    before, ask, ch_md, terms_md = question_body(d, choices, form)
                    ab = answer_body(d, choices, form)
                    assert "## 正解" in ab
                    # 決定性
                    rnd2 = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                    d2 = draw(rnd2, kind, None, form)
                    if form == "match":
                        c2 = build_match(d2, rnd2)
                    else:
                        c2 = {"select": build_choices_select, "select2": build_choices_select2,
                              "allthat": build_choices_allthat, "read": build_choices_read,
                              "fix": build_choices_fix, "cause": build_choices_cause}[form](d2, rnd2)
                    assert question_body(d2, c2, form) == (before, ask, ch_md, terms_md), "非決定的"
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    key = (kind, form)
                    bad.setdefault(key, [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_svc selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
