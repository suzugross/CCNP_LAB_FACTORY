#!/usr/bin/env python3
"""STP 選択問ファミリ (BL-216・単元 U-A3 の P2) — gen_paper_mcq.py の shape=stp 素材。

設計= problems/_drafts/STP-P2.design.md。知識項目表= curriculum/U-A3-stp.md。
裏どり(CLAUDE.md「作問の裏どり」)= curriculum/U-A3-stp.sources.md(Cisco 公式・解説サイト・実機の照合表)と
poc/stp/README.md 第2回(ioll2-xe 17.15.1 の実測)。**事実はこの 2 つで「確定」になったものだけを使う**。
ユーザ決定(2026-09-22): U1 既定モードは版を示して問う / U2 BPDU 宛先は IEEE のみ / U3 UDLD は Cisco 公式の見解どおり /
U4 1 問の中でパスコスト方式をそろえる(混在は出さない)。

kinds:
  瞬発(事実ベース): s_basic(802.1D 基礎)/ s_rstp / s_modes(PVST+・Rapid PVST+・MST の知識)
  思考: s_elect(盤面を抽選→ stp_model で選出)/ s_read(show の読解)/ s_mst(MST リージョン設定の比較)/
        s_tuning(root primary/secondary の結果・経路を寄せる最小変更)/ s_guard(要件→保護機能)/ s_ts(症状→原因・是正)

公開 API は gen_paper_svc.py と同じ(KINDS/kind_forms/draw/build_choices_*/build_match/question_body/answer_body/pick_count/selftest)。
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stp_model as sm  # noqa: E402

KINDS = ["s_basic", "s_rstp", "s_modes", "s_elect", "s_read", "s_mst", "s_tuning", "s_guard", "s_ts"]
SPEED_KINDS = ["s_basic", "s_rstp", "s_modes"]
THINK_KINDS = ["s_elect", "s_read", "s_mst", "s_tuning", "s_guard", "s_ts"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {
    "s_basic": {"select", "select2", "allthat", "match"},
    "s_rstp": {"select", "select2", "allthat", "match"},
    "s_modes": {"select", "select2", "allthat", "match"},
    "s_elect": {"select", "select2", "allthat", "read"},
    "s_read": {"read", "select2", "allthat"},
    "s_mst": {"read", "select2", "allthat"},
    "s_tuning": {"select", "select2", "allthat", "fix"},
    "s_guard": {"select", "select2", "allthat"},
    "s_ts": {"cause", "fix", "read"},
}
SPEED_FORMS = {"s_basic": ["select", "select2", "allthat", "match"],
               "s_rstp": ["select", "select2", "allthat", "match"],
               "s_modes": ["select", "select2", "allthat", "match"]}
DIFF = {"s_basic": 2, "s_rstp": 2, "s_modes": 2, "s_elect": 4, "s_read": 3, "s_mst": 3,
        "s_tuning": 4, "s_guard": 3, "s_ts": 4}
TITLES = {
    "s_basic": "スパニング ツリーの基本動作", "s_rstp": "Rapid Spanning Tree Protocol", "s_modes": "スパニング ツリーのモード",
    "s_elect": "ルート ブリッジとポートの役割", "s_read": "スパニング ツリーの状態の確認", "s_mst": "MST リージョンの構成",
    "s_tuning": "スパニング ツリーのチューニング", "s_guard": "スパニング ツリーの保護機能", "s_ts": "スパニング ツリーのトラブルシューティング",
}
LET = "ABCDEFG"


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# 事実ベース(1 設問= ask + 正しい記述群 t + 誤った記述群 f(理由付き))
#   出典の記号: [C]= Cisco 公式 / [J]= 解説サイト / [M]= 実機(poc/stp 第2回の M 番号)
# ==========================================================================
FACTS = {
    "s_basic": [
        {"ask": "IEEE 802.1D のスパニング ツリーのポートの状態", "t": [
            "ブロッキング状態のポートは BPDU を受信する",
            "リスニング状態のポートは MAC アドレスを学習しない",
            "ラーニング状態のポートは MAC アドレスを学習するが、データ フレームは転送しない",
            "フォワーディング状態のポートはデータ フレームを転送し、MAC アドレスも学習する"], "f": [
            ("ブロッキング状態のポートは BPDU も受信しない", "ブロッキングでも BPDU は受信し続ける(上位の変化を知るため)。"),
            ("リスニング状態のポートは MAC アドレスを学習する", "学習を始めるのはラーニング状態から。"),
            ("ラーニング状態のポートはデータ フレームを転送する", "データ フレームを転送するのはフォワーディング状態だけ。"),
            ("ポートはブロッキングからラーニングを経てリスニングに移る", "順序はブロッキング → リスニング → ラーニング → フォワーディング。")],
         "note": "802.1D の 5 状態= ディセーブル/ブロッキング/リスニング/ラーニング/フォワーディング[C][J]。"},
        {"ask": "ブリッジ ID", "t": [
            "ブリッジ ID はブリッジ プライオリティと MAC アドレスから構成される",
            "拡張システム ID が有効な場合、ブリッジ プライオリティのフィールドに VLAN ID が含まれる",
            "ブリッジ プライオリティは 4096 の倍数で設定する",
            "ブリッジ プライオリティの既定値は 32768 である"], "f": [
            ("ブリッジ ID はブリッジ プライオリティと IP アドレスから構成される", "IP アドレスは使わない。MAC アドレスを使う。"),
            ("ブリッジ プライオリティには 0 から 65535 の任意の値を設定できる", "拡張システム ID が有効なら 0〜61440 の 4096 刻み。実機も 4096 の倍数以外を `% Bridge Priority must be in increments of 4096.` で拒否する[M20]。"),
            ("ブリッジ プライオリティの既定値は 4096 である", "既定は 32768。"),
            ("ブリッジ ID が最も大きいスイッチがルート ブリッジになる", "最も小さいスイッチがルート ブリッジになる。")],
         "note": "BID= priority(4 bit)+拡張システム ID(12 bit= VLAN ID)+MAC[C][J]。`show spanning-tree` の priority 表示は設定値+VLAN ID(例 32768+10=32778)[M]。"},
        {"ask": "ルート ブリッジとポートの役割の決定", "t": [
            "ブリッジ ID が最も小さいスイッチがルート ブリッジになる",
            "ルート ブリッジは、ルート ポートを持たない",
            "ルート ブリッジ以外のスイッチは、ルート ポートを 1 つ持つ",
            "セグメントごとに指定ポートが 1 つ選ばれる"], "f": [
            ("ルート ブリッジは、ルート ポートを 1 つ持つ", "ルート ポートはルート ブリッジ以外のスイッチが持つ。"),
            ("ルート パス コストが最も大きいポートがルート ポートになる", "最も小さいポートがルート ポートになる。"),
            ("ルート パス コストが同じ場合は、自分のポート ID の小さいポートがルート ポートになる", "コストの次に比べるのは送信元のブリッジ ID、その次に送信元のポート ID。"),
            ("非指定ポートはフォワーディング状態になる", "非指定ポートはブロッキング(RSTP では代替)になる。")],
         "note": "ルート ポートの選出順= ルート パス コスト → 送信元ブリッジ ID → 送信元ポート ID[C][J]。port-priority は送信元(上流)側の値が効く[M4]。"},
        {"ask": "スパニング ツリーのタイマの既定値", "t": [
            "hello タイムの既定値は 2 秒である",
            "転送遅延(forward delay)の既定値は 15 秒である",
            "最大エージ(max age)の既定値は 20 秒である",
            "タイマの値は、ルート ブリッジの設定が BPDU で配布される"], "f": [
            ("hello タイムの既定値は 10 秒である", "既定は 2 秒。"),
            ("転送遅延(forward delay)の既定値は 30 秒である", "既定は 15 秒(リスニングとラーニングにそれぞれかかる)。"),
            ("タイマの値は、各スイッチが自分の設定値で動作する", "効くのはルート ブリッジの値で、BPDU で配布される。"),
            ("最大エージ(max age)の既定値は 6 秒である", "既定は 20 秒。")],
         "note": "既定= hello 2 秒・転送遅延 15 秒・最大エージ 20 秒(実機の show も同値)[C][M]。"},
        {"ask": "ショート方式のパス コストの既定値", "t": [
            "1 Gbps のポートの既定のパス コストは 4 である",
            "10 Gbps のポートの既定のパス コストは 2 である",
            "100 Mbps のポートの既定のパス コストは 19 である",
            "パス コストはポートの帯域幅から決まる"], "f": [
            ("1 Gbps のポートの既定のパス コストは 1 である", "ショート方式では 4。"),
            ("パス コストはホップ数から決まる", "帯域幅から決まる。"),
            ("1 Gbps のポートの既定のパス コストは 20000 である", "20000 はロング方式の値。"),
            ("100 Mbps のポートの既定のパス コストは 10 である", "ショート方式では 19。")],
         "note": "short: 10G=2・1G=4・100M=19・10M=100 / long: 10G=2000・1G=20000・100M=200000[C][J]。"},
        {"ask": "スパニング ツリーの目的と BPDU", "t": [
            "スパニング ツリーは、レイヤ 2 のループによるブロードキャスト ストームを防ぐ",
            "スイッチは起動直後、自分をルート ブリッジとみなして BPDU を送信する",
            "IEEE 形式の BPDU の宛先 MAC アドレスは 0180.C200.0000 である",
            "EtherChannel は、スパニング ツリーから 1 本の論理リンクとして扱われる"], "f": [
            ("BPDU の宛先 MAC アドレスは FFFF.FFFF.FFFF である", "IEEE 形式の BPDU はマルチキャスト 0180.C200.0000 宛て。"),
            ("スイッチは起動直後、BPDU を受信するまで BPDU を送信しない", "起動直後は自分をルートとみなして BPDU を送る。"),
            ("スパニング ツリーは、レイヤ 3 のルーティング ループを防ぐ", "防ぐのはレイヤ 2 のループ。"),
            ("EtherChannel を構成する物理リンクは、1 本を残してブロックされる", "EtherChannel は論理 1 本として扱われ、メンバは全部使われる。")],
         "note": "ループが残るとブロードキャスト ストームと MAC アドレス テーブルの不安定(フラッピング)が起きる[C][J]。"},
    ],
    "s_rstp": [
        {"ask": "RSTP のポートの状態", "t": [
            "RSTP のポートの状態は、ディスカーディング・ラーニング・フォワーディングの 3 つである",
            "ディスカーディング状態のポートはデータ フレームを転送しない",
            "ラーニング状態のポートは MAC アドレスを学習するが、データ フレームは転送しない",
            "802.1D のディセーブル・ブロッキング・リスニングは、RSTP ではディスカーディングにまとめられている"], "f": [
            ("RSTP のポートの状態は、ブロッキング・リスニング・ラーニング・フォワーディング・ディセーブルの 5 つである", "5 状態は 802.1D。RSTP は 3 状態。"),
            ("ラーニング状態のポートはデータ フレームを転送する", "転送するのはフォワーディング状態だけ。"),
            ("代替ポートはフォワーディング状態で待機する", "代替ポートはディスカーディング(転送しない)。"),
            ("ディスカーディング状態のポートは MAC アドレスを学習する", "学習はラーニング状態から。")],
         "note": "`show spanning-tree` の Sts 列では、ディスカーディングは BLK と表示される[M]。"},
        {"ask": "RSTP のポートの役割", "t": [
            "ルート ブリッジは、ルート ポートを持たない",
            "代替ポートは、ルート ポートがダウンしたときにルート ポートを引き継ぐ",
            "バックアップ ポートは、同じスイッチの指定ポートがダウンしたときに指定ポートを引き継ぐ",
            "代替ポートとバックアップ ポートはデータ フレームを転送しない",
            "指定ポートを 1 つも持たないスイッチもある"], "f": [
            ("代替ポートは、同じスイッチの指定ポートのバックアップとして動作する", "それはバックアップ ポート。代替ポートはルート ポートの代わり。"),
            ("バックアップ ポートは、ルート ポートがダウンしたときにルート ポートを引き継ぐ", "それは代替ポート。"),
            ("指定ポートを持つのはルート ブリッジだけである", "ルート ブリッジ以外のスイッチも指定ポートを持つ。"),
            ("ルート ブリッジ以外のスイッチは、必ず指定ポートを 1 つ以上持つ", "末端のスイッチは指定ポートを持たないことがある。"),
            ("代替ポートはデータ フレームを転送する", "代替ポートは転送しない(ディスカーディング)。")],
         "note": "4 役割= ルート/指定/代替/バックアップ。バックアップは同じスイッチの 2 ポートが共有セグメント(ハブ等)に出るときに生じる[C][J]。"},
        {"ask": "RSTP のリンク タイプとエッジ ポート", "t": [
            "全二重のポートは、ポイントツーポイント リンクとして扱われる",
            "半二重のポートは、共有リンクとして扱われる",
            "提案と合意(proposal/agreement)による高速な遷移は、ポイントツーポイント リンクで行われる",
            "エッジ ポートは、BPDU を受信するとエッジ ポートではなくなる",
            "PortFast を設定したポートは、RSTP のエッジ ポートとして扱われる"], "f": [
            ("半二重のポートは、ポイントツーポイント リンクとして扱われる", "半二重は共有リンク。"),
            ("共有リンクでも、提案と合意による高速な遷移が行われる", "高速な遷移はポイントツーポイントとエッジだけ。"),
            ("エッジ ポートは、BPDU を受信してもエッジ ポートのまま動作する", "BPDU を受信した時点でエッジではなくなる。"),
            ("リンク タイプは、常に手動で設定する必要がある", "リンク タイプは duplex から自動で判定される。")],
         "note": "link type は duplex から自動判定[C]。PortFast のポートは `show spanning-tree` の Type に Edge と出る(`P2p Edge`)[M17]。"},
        {"ask": "RSTP の BPDU とトポロジ変更", "t": [
            "RSTP では、ルート ブリッジ以外のスイッチも hello タイムごとに BPDU を送信する",
            "hello を 3 回続けて受信しないと、そのポートで受け取っていた情報は失効する",
            "RSTP のトポロジ変更は、エッジでないポートがフォワーディングに移るときに発生する",
            "エッジ ポートのリンク アップやリンク ダウンでは、トポロジ変更は発生しない",
            "RSTP は IEEE 802.1w で規定されている"], "f": [
            ("RSTP でも、BPDU を生成するのはルート ブリッジだけである", "RSTP では各スイッチが hello ごとに BPDU を出す。"),
            ("RSTP のトポロジ変更は、ポートがディスカーディングに移るときに発生する", "発生するのはエッジでないポートがフォワーディングに移るとき。"),
            ("RSTP は IEEE 802.1s で規定されている", "802.1s は MST。RSTP は 802.1w。"),
            ("hello を 1 回受信しないだけで、そのポートの情報は失効する", "3 回続けて受信しないと失効する。")],
         "note": "RSTP の TC は非エッジ ポートのフォワーディング移行時のみ[C]。IOL では対向のリンク断が伝わらず、hello 3 回の失効(約 5 秒)で切り替わった[M13]。"},
        {"ask": "RSTP と 802.1D のスイッチの相互接続", "t": [
            "RSTP のスイッチは、802.1D の BPDU を受信したポートで 802.1D の動作に切り替える",
            "802.1D のスイッチと接続したポートは、`show spanning-tree` の Type に Peer(STP) と表示される",
            "`clear spanning-tree detected-protocols` は、実行したスイッチのポートの検出結果をリセットする"], "f": [
            ("RSTP のスイッチは、802.1D のスイッチを検出するとスイッチ全体を 802.1D の動作に切り替える", "切り替えはポート単位。"),
            ("802.1D の検出結果は、相手が RSTP に戻ると必ず自動で元に戻る", "自動では戻らない場合がある(実機でも残った)[M14]。"),
            ("RSTP のスイッチと 802.1D のスイッチは相互に接続できない", "ポート単位で 802.1D に合わせて互換動作する。"),
            ("`clear spanning-tree detected-protocols` を一方で実行すると、対向のスイッチの検出結果もリセットされる", "リセットされるのは実行したスイッチ側だけ(対向には残る)[M14]。")],
         "note": "実機: rapid 側に `P2p Peer(STP)`・detail に `Peer is STP`。clear は打った側だけ消えた[M14]。"},
    ],
    "s_modes": [
        {"ask": "PVST+ / Rapid PVST+ / MST", "t": [
            "PVST+ は、VLAN ごとにスパニング ツリーのインスタンスを作る Cisco 独自の方式である",
            "Rapid PVST+ は、VLAN ごとに RSTP のインスタンスを作る",
            "MST は、複数の VLAN を 1 つのインスタンスにまとめられる",
            "PVST+ では、VLAN ごとに異なるルート ブリッジを置いて負荷を分散できる",
            "MST は、Rapid PVST+ に比べてスイッチが処理するインスタンスの数を少なくできる"], "f": [
            ("PVST+ は、すべての VLAN で 1 つのインスタンスを共有する", "PVST+ は VLAN ごとにインスタンスを作る。"),
            ("Rapid PVST+ は、VLAN ごとに IEEE 802.1D のインスタンスを作る", "Rapid PVST+ のインスタンスは RSTP。"),
            ("MST は、VLAN ごとに必ず 1 つのインスタンスを作る", "MST は複数の VLAN を 1 つのインスタンスにまとめる。"),
            ("MST は Cisco 独自の方式である", "MST は IEEE 802.1s。")],
         "note": "`show spanning-tree` の protocol 行= PVST+ は `ieee`・Rapid PVST+ は `rstp`[J][M14]。"},
        {"ask": "MST リージョン", "t": [
            "同じ MST リージョンにするには、リージョン名・リビジョン番号・VLAN とインスタンスの対応の 3 つを一致させる",
            "インスタンスに割り当てていない VLAN は、インスタンス 0(IST)に属する",
            "MST は IEEE 802.1s で規定されている",
            "MST モードでは、パス コストにロング方式の値が使われる"], "f": [
            ("リージョン名が一致していれば、VLAN とインスタンスの対応が異なっても同じリージョンになる", "3 つすべての一致が必要。"),
            ("インスタンスに割り当てていない VLAN では、スパニング ツリーが動作しない", "未割り当ての VLAN は IST(インスタンス 0)に属する。"),
            ("IST はインスタンス 1 である", "IST はインスタンス 0。"),
            ("リビジョン番号はリージョンの判定に使われない", "リビジョン番号も判定に使われる。")],
         "note": "不一致の境界ポートは `Bound(RSTP)` と表示される(poc/stp 第1回 P4)。MST モードの Et のコストは 2000000(ロング)[M15]。"},
        {"ask": "スパニング ツリーのモードの設定コマンド", "t": [
            "`spanning-tree mode rapid-pvst` で Rapid PVST+ を有効にする",
            "`spanning-tree mst 1 priority 4096` で、インスタンス 1 のブリッジ プライオリティを設定する",
            "`spanning-tree mst 1 root primary` で、インスタンス 1 のルート ブリッジになるように設定する",
            "リージョン名・リビジョン番号・対応は `spanning-tree mst configuration` のモードで設定する"], "f": [
            ("`spanning-tree mode rstp` で Rapid PVST+ を有効にする", "モードのキーワードは mst / pvst / rapid-pvst。"),
            ("`spanning-tree mode mstp` で MST を有効にする", "キーワードは mst。"),
            ("`spanning-tree vlan 1 mst priority 4096` で、インスタンス 1 のブリッジ プライオリティを設定する", "インスタンスの指定は `spanning-tree mst <番号> priority`。"),
            ("`spanning-tree mst instance 1 priority 4096` で、インスタンス 1 のブリッジ プライオリティを設定する", "instance というキーワードは入らない。")],
         "note": "`show spanning-tree mst configuration` で Name / Revision / Instance ごとの VLAN を確認できる[M15]。"},
    ],
    "s_guard": [
        {"ask": "BPDU ガードと BPDU フィルタ", "t": [
            "BPDU ガードを有効にしたポートが BPDU を受信すると、そのポートは err-disabled になる",
            "`spanning-tree portfast bpduguard default` は、PortFast が動作しているポートにだけ作用する",
            "インターフェイスで `spanning-tree bpduguard enable` を設定すると、PortFast の有無にかかわらず作用する",
            "インターフェイスで BPDU フィルタを設定すると、そのポートは BPDU の送信も受信も行わない",
            "同じポートに BPDU ガードと BPDU フィルタを設定すると、BPDU フィルタの動作が優先される"], "f": [
            ("BPDU ガードを有効にしたポートが BPDU を受信すると、そのポートは root-inconsistent になる", "BPDU ガードは err-disabled にする。root-inconsistent はルート ガード。"),
            ("`spanning-tree portfast bpduguard default` は、すべてのアクセス ポートに作用する", "作用するのは PortFast が動作しているポートだけ。"),
            ("インターフェイスで BPDU フィルタを設定しても、BPDU の受信は続ける", "送信も受信も止まる(実質そのポートの STP を止める)。"),
            ("同じポートに BPDU ガードと BPDU フィルタを設定すると、BPDU ガードが優先されてポートは err-disabled になる", "実機では BPDU フィルタが勝ち、err-disabled にならなかった[M8]。")],
         "note": "BPDU ガードの発火ログ= `%SPANTREE-2-BLOCK_BPDUGUARD` と `%PM-4-ERR_DISABLE`[J][M8]。"},
        {"ask": "ルート ガードとループ ガード", "t": [
            "ルート ガードは、上位の BPDU を受信したポートを root-inconsistent にし、上位の BPDU が止まると自動で回復する",
            "ループ ガードは、BPDU が届かなくなったルート ポートや代替ポートを loop-inconsistent にする",
            "ルート ガードとループ ガードは、同じポートで同時に有効にできない",
            "ルート ガードは、そのポートが属するすべての VLAN に作用する"], "f": [
            ("root-inconsistent になったポートは、shutdown と no shutdown を実行するまで回復しない", "上位の BPDU が止まれば自動で回復する(実機で約 2 秒)[M9]。"),
            ("ループ ガードは、指定ポートで BPDU が届かなくなったときに作用する", "作用するのは非指定(ルート/代替)ポート。指定ポートの VLAN は影響を受けなかった[M10]。"),
            ("ルート ガードとループ ガードは、同じポートで同時に有効にできる", "排他。インターフェイスの `spanning-tree guard` は後から入れた方に置き換わる[M10c]。"),
            ("ルート ガードは、上位の BPDU を受信した VLAN にだけ作用する", "ポート上のすべての VLAN に作用し、正当なルートの VLAN まで止めた[M9]。")],
         "note": "ログ= `%SPANTREE-2-ROOTGUARD_BLOCK` / `%SPANTREE-2-LOOPGUARD_BLOCK`[J][M9][M10]。"},
        {"ask": "PortFast と err-disabled からの復旧", "t": [
            "PortFast を設定したポートは、リスニングとラーニングを経ずにフォワーディングになる",
            "`spanning-tree portfast trunk` を設定すると、トランク ポートでも PortFast が動作する",
            "err-disabled からの自動復旧は既定で無効である",
            "`errdisable recovery` の間隔の既定値は 300 秒である"], "f": [
            ("`spanning-tree portfast default` は、トランク ポートにも PortFast を有効にする", "作用するのは非トランク(アクセス)ポートだけ。"),
            ("PortFast を設定したポートは、BPDU を送信しない", "PortFast でも BPDU は送信される(止めるのは BPDU フィルタ)。"),
            ("err-disabled からの自動復旧は既定で有効であり、300 秒後に回復する", "自動復旧は既定で無効(全 cause が Disabled)[M12]。"),
            ("`errdisable recovery interval` を変更すると、既に err-disabled のポートにも新しい間隔がすぐ適用される", "実機では既存のポートは変更前の 300 秒のタイマのままだった[M12]。")],
         "note": "trunk への `spanning-tree portfast` は `will only have effect when the interface is in a non-trunking mode` の警告だけで効かない[M17]。"},
        {"ask": "UDLD", "t": [
            "UDLD は、片方向リンクを検出するレイヤ 2 のプロトコルである",
            "UDLD には通常モードとアグレッシブ モードがある",
            "アグレッシブ モードでは、近隣との再確立に失敗するとポートを err-disabled にする",
            "通常モードでは、近隣の情報がタイムアウトしてもポートを無効にしない"], "f": [
            ("通常モードでは、近隣の情報がタイムアウトするとポートを err-disabled にする", "通常モードはタイムアウトでは無効にしない(undetermined として扱う)。"),
            ("UDLD は、スパニング ツリーの BPDU を使って片方向リンクを検出する", "UDLD は独自のメッセージを使うレイヤ 2 のプロトコル。"),
            ("UDLD には通常モードしかない", "通常モードとアグレッシブ モードがある。"),
            ("インターフェイスでアグレッシブ モードを有効にするコマンドは `spanning-tree udld aggressive` である", "`udld port aggressive`。")],
         "note": "Cisco の見解: 通常モードは片方向でも undetermined としてポートを無効にしない・アグレッシブは 1 秒ごと 8 回の再確立に失敗すると err-disable[C]。ioll2 にも UDLD はある(片方向は再現不可)[M11]。"},
    ],
}

# 用途を問う選択(要件 → 機能)
GUARD_REQ = [
    ("アクセス ポートに無許可のスイッチが接続されたら、そのポートを直ちに停止したい。", "BPDU ガード",
     "BPDU を受信したポートを err-disabled にするのは BPDU ガード。"),
    ("ディストリビューション スイッチのアクセス層に向けたポートで、下位のスイッチがルート ブリッジにならないようにしたい。", "ルート ガード",
     "上位の BPDU を受信したポートを root-inconsistent にしてルートの位置を守るのはルート ガード。"),
    ("片方向の障害で BPDU が届かなくなったときに、代替ポートがフォワーディングに移ってループが起きるのを、スパニング ツリーの機能で防ぎたい。", "ループ ガード",
     "BPDU が途絶えた非指定ポートを loop-inconsistent にするのはループ ガード。"),
    ("光ファイバの片方向リンクを検出し、そのポートを err-disabled にしたい。", "UDLD のアグレッシブ モード",
     "片方向を検出して err-disabled にするのは UDLD のアグレッシブ モード(通常モードは無効にしない)。"),
    ("PC を接続するポートで、リンク アップ後すぐにデータを送受信できるようにしたい。", "PortFast",
     "リスニングとラーニングを省いてすぐフォワーディングにするのは PortFast。"),
]
GUARD_ALL = ["BPDU ガード", "ルート ガード", "ループ ガード", "UDLD のアグレッシブ モード", "PortFast", "BPDU フィルタ", "UDLD の通常モード"]

MATCH = {
    "s_basic": [("ブロッキング", "BPDU は受信するが、MAC アドレスの学習もデータの転送もしない"),
                ("リスニング", "ポートの役割を決める段階で、MAC アドレスはまだ学習しない"),
                ("ラーニング", "MAC アドレスを学習するが、データ フレームはまだ転送しない"),
                ("フォワーディング", "データ フレームを転送し、MAC アドレスも学習する"),
                ("ディセーブル", "管理的に停止しており、スパニング ツリーに参加しない")],
    "s_rstp": [("ルート ポート", "ルート ブリッジへ向かう最良のポート(ルート ブリッジ以外が 1 つ持つ)"),
               ("指定ポート", "セグメントごとに 1 つ選ばれ、そのセグメントへ BPDU を送る"),
               ("代替ポート", "ルート ポートの代わりになる(別のスイッチからの BPDU を受ける)"),
               ("バックアップ ポート", "同じスイッチの指定ポートの代わりになる(共有セグメントで生じる)"),
               ("エッジ ポート", "端末を接続し、すぐにフォワーディングになる(PortFast)")],
    "s_modes": [("PVST+", "VLAN ごとに 802.1D のインスタンスを作る Cisco 独自の方式"),
                ("Rapid PVST+", "VLAN ごとに RSTP のインスタンスを作る"),
                ("MST", "複数の VLAN を 1 つのインスタンスにまとめる IEEE 802.1s"),
                ("RSTP", "IEEE 802.1w で規定される高速な収束の方式"),
                ("IST", "MST リージョンのインスタンス 0")],
}

CORE = {
    "s_basic": "802.1D の基本= ルート ブリッジ(最小 BID)→ 各スイッチのルート ポート(最小ルート パス コスト→送信元 BID→送信元ポート ID)→ セグメントごとの指定ポート → 残りがブロッキング。",
    "s_rstp": "RSTP(802.1w)= 状態 3 つ(ディスカーディング/ラーニング/フォワーディング)・役割 4 つ(ルート/指定/代替/バックアップ)・各スイッチが hello ごとに BPDU・p2p とエッジで提案/合意による高速遷移。",
    "s_modes": "PVST+(VLAN ごとに 802.1D)・Rapid PVST+(VLAN ごとに RSTP)・MST(802.1s・VLAN を束ねたインスタンス・リージョン= 名前/リビジョン/対応表の一致)。",
    "s_elect": "選出順= ルート ブリッジ(最小 BID)→ ルート ポート(最小ルート パス コスト→送信元 BID→送信元ポート ID)→ 各リンクの指定ポート(ルート パス コスト→BID→ポート ID が小さい端)→ 残りが代替(ブロッキング)。",
    "s_read": "`show spanning-tree vlan N`: Root ID= ルート ブリッジ(Cost/Port は自分のルート パス コストとルート ポート・ルートなら This bridge is the root)。Bridge ID= 自分(priority 表示= 設定値+sys-id-ext)。protocol rstp= Rapid PVST+・ieee= PVST+。",
    "s_mst": "MST リージョン= リージョン名・リビジョン番号・VLAN とインスタンスの対応の 3 つがすべて一致するスイッチの集まり。1 つでも違えば別リージョンになり、間のポートは境界ポート(`Bound`)になる。未割り当ての VLAN はインスタンス 0(IST)。",
    "s_tuning": "root primary= 24576 でルートになれるなら 24576、なれなければ現ルートより 4096 小さい値(1 未満が必要なら失敗)。一度だけ計算して数値を書き込む。secondary= 常に 28672。port-priority は送信元(上流)側で効き、cost は自分のルート ポート選択に効く。",
    "s_guard": "BPDU ガード= BPDU 受信で err-disabled / BPDU フィルタ= BPDU を送受信しない / ルート ガード= 上位 BPDU で root-inconsistent / ループ ガード= BPDU 途絶で loop-inconsistent / UDLD アグレッシブ= 片方向で err-disabled。",
    "s_ts": "指紋→原因: err-disabled bpduguard= BPDU ガード / Root Inconsistent= ルート ガード / Loop Inconsistent= ループ ガード(BPDU 途絶) / Bound(PVST) *PVST_Inc= MST と PVST+ の境界で PVST 側に優位なルート / Bound(RSTP)= MST リージョンの不一致 / Peer(STP)= 相手が 802.1D。",
}


def _no_cause(t):
    return t.replace("ので、", "。").replace("ため、", "。")


# ==========================================================================
# 盤面(s_elect / s_read / s_tuning 共通)
# ==========================================================================
OUIS = ["0019.e8", "001a.a1", "5c50.15", "7c21.0e", "0023.04", "a0cf.5b"]
PRIOS = [4096, 8192, 24576, 28672, 32768, 32768, 32768]


def _mac(rnd, used):
    while True:
        o = rnd.choice(OUIS)
        m = f"{o}{rnd.randint(0x10, 0xff):02x}.{rnd.randint(0x1000, 0xffff):04x}"
        if m not in used:
            used.add(m)
            return m


def _ifc(kind, n):
    return {"name": f"Gi1/0/{n}", "num": n} if kind == "1G" else {"name": f"Te1/1/{n}", "num": 48 + n}


def _draw_board(rnd, shape=None, allow_par=True):
    shape = shape or rnd.choice(["tri", "tri", "sq", "sqd"] + (["tripar"] if allow_par else []))
    n = 3 if shape in ("tri", "tripar") else 4
    names = [f"SW{i + 1}" for i in range(n)]
    if rnd.random() < 0.35:
        names = ["DSW1", "DSW2", "ASW1", "ASW2"][:n]
    used = set()
    sw = {s: {"prio": rnd.choice(PRIOS), "mac": _mac(rnd, used)} for s in names}
    method = "long" if rnd.random() < 0.35 else "short"
    pairs = {"tri": [(0, 1), (0, 2), (1, 2)], "tripar": [(0, 1), (0, 2), (1, 2), (1, 2)],
             "sq": [(0, 1), (1, 2), (2, 3), (3, 0)], "sqd": [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]}[shape]
    nxt = {s: 1 for s in names}
    links = []
    for i, j in pairs:
        a, b = names[i], names[j]
        sp = "10G" if rnd.random() < 0.3 else "1G"
        if shape == "tripar" and (i, j) == (1, 2):
            sp = "1G"
        links.append((a, _ifc(sp, nxt[a]), b, _ifc(sp, nxt[b]), sp))
        nxt[a] += 1
        nxt[b] += 1
    return {"shape": shape, "names": names, "sw": sw, "links": links, "method": method,
            "port_prio": {}, "cost_ovr": {}, "vlan": rnd.choice([10, 20, 30, 100, 110])}


def _solve(b):
    return sm.Topo(b["sw"], b["links"], b["method"], b["port_prio"], b["cost_ovr"], b["vlan"]).solve()


def _spd_ja(sp):
    return {"1G": "1 Gbps", "10G": "10 Gbps"}[sp]


def _mm(name):
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", name)


def board_md(b, show_prio=True):
    L = ["```mermaid", "graph TD" if len(b["names"]) == 3 else "graph LR"]
    for s in b["names"]:
        L.append(f'  {_mm(s)}["{s}"]')
    for a, ia, bb, ib, sp in b["links"]:
        L.append(f'  {_mm(a)} ---|"{ia["name"]} — {ib["name"]}"| {_mm(bb)}')
    L.append("```")
    L += ["", "| スイッチ | ブリッジ プライオリティ(VLAN %d) | MAC アドレス |" % b["vlan"], "|---|---|---|"]
    for s in b["names"]:
        L.append(f"| {s} | {b['sw'][s]['prio'] if show_prio else '(非表示)'} | {b['sw'][s]['mac']} |")
    L += ["", "| リンク | 帯域幅 |", "|---|---|"]
    for a, ia, bb, ib, sp in b["links"]:
        L.append(f"| {a} {ia['name']} — {bb} {ib['name']} | {_spd_ja(sp)} |")
    extra = []
    for (s, ifn), v in sorted(b["cost_ovr"].items()):
        extra.append(f"{s}(config)# interface {ifn}\n{s}(config-if)# spanning-tree vlan {b['vlan']} cost {v}")
    for (s, ifn), v in sorted(b["port_prio"].items()):
        extra.append(f"{s}(config)# interface {ifn}\n{s}(config-if)# spanning-tree vlan {b['vlan']} port-priority {v}")
    if extra:
        L += ["", "既定値から変更している設定は次のとおりです。", "", "```", "\n".join(extra), "```"]
    L += ["", f"全スイッチで Rapid PVST+ を使用し、パス コストは{'ロング' if b['method'] == 'long' else 'ショート'}方式にそろえています。"
          "リンクはすべて全二重のトランクで、記載のない設定は既定値です。"]
    return "\n".join(L)


# ---- show spanning-tree vlan N の描画(ioll2 実測の書式・IF 名は Gi/Te) ------------------
def _long_if(n):
    return n.replace("Gi", "GigabitEthernet").replace("Te", "TenGigabitEthernet")


def show_vlan(b, t, s, proto="rstp"):
    v = b["vlan"]
    r = t.root
    rp = b["sw"][r]["prio"] + v
    me = b["sw"][s]["prio"] + v
    L = [f"VLAN{v:04d}", f"  Spanning tree enabled protocol {proto}",
         f"  Root ID    Priority    {rp}", f"             Address     {b['sw'][r]['mac']}"]
    if s == r:
        L.append("             This bridge is the root")
    else:
        rpn = t.rp[s]
        num = next(ifc["num"] for ifc, _n, _ni, _sp in t.ports(s) if ifc["name"] == rpn)
        L += [f"             Cost        {t.rpc[s]}", f"             Port        {num} ({_long_if(rpn)})"]
    L += ["             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec", "",
          f"  Bridge ID  Priority    {me:<7}(priority {b['sw'][s]['prio']} sys-id-ext {v})",
          f"             Address     {b['sw'][s]['mac']}",
          "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec",
          "             Aging Time  300 sec", "",
          "Interface           Role Sts Cost      Prio.Nbr Type",
          "------------------- ---- --- --------- -------- --------------------------------"]
    rows = []
    for ifc, _n, _ni, sp in t.ports(s):
        ifn = ifc["name"]
        pr = b["port_prio"].get((s, ifn), 128)
        rows.append((ifc["num"], f"{ifn:<20}{t.role[(s, ifn)]:<5}{t.state(s, ifn):<4}{t.cost_of(s, ifn):<10}{str(pr) + '.' + str(ifc['num']):<9}P2p "))
    L += [r_ for _k, r_ in sorted(rows)]
    return "\n".join(L)


# ==========================================================================
# draw
# ==========================================================================
def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    if kind in FACTS:
        d["q"] = rnd.randrange(len(FACTS[kind]))
    if kind == "s_modes":
        d["dm"] = rnd.random() < 0.3          # 既定モードを版つきで問う(U1)
        d["ver"] = rnd.choice(["old", "new", "xe"])
    if kind == "s_guard":
        d["req"] = rnd.random() < 0.5
        d["rq"] = rnd.randrange(len(GUARD_REQ))
    if kind in ("s_elect", "s_read"):
        for _ in range(60):
            b = _draw_board(rnd)
            try:
                t = _solve(b)
            except ValueError:
                continue
            d["b"], d["t"] = b, t
            break
        else:
            raise ValueError("盤面が作れない")
        if kind == "s_read":
            d["who"] = rnd.choice([s for s in b["names"]])
            d["proto"] = "rstp" if rnd.random() < 0.7 else "ieee"
    if kind == "s_mst":
        _draw_mst(d, rnd)
    if kind == "s_tuning":
        d["tt"] = rnd.choice(["primary", "primary", "secondary", "steer", "steer", "facts"])
        _draw_tuning(d, rnd)
    if kind == "s_ts":
        d["sc"] = rnd.choice(list(TS))
        TS[d["sc"]]["draw"](d, rnd)
    return d


# ==========================================================================
# 事実形の選択肢
# ==========================================================================
def _fact_q(d):
    return FACTS[d["kind"]][d["q"]]


def _pick(rnd, trues, falses, n_true, n_total, grp=None):
    """grp= {記述: グループ名}。同じグループ(裏返しの関係にある記述)は 1 問に 1 つまで(消去法の封じ・BL-201 と同じ考え方)。"""
    if len(trues) < n_true or len(falses) < n_total - n_true:
        raise ValueError("肢が足りない")
    grp = grp or {}
    for _ in range(60):
        tt = rnd.sample(trues, n_true)
        ff = rnd.sample(falses, n_total - n_true)
        gs = [grp[x] for x in tt + [f for f, _w in ff] if x in grp]
        if len(gs) == len(set(gs)):
            break
    else:
        raise ValueError("排他グループを満たせない")
    c = [(t, True, "") for t in tt] + [(f, False, w) for f, w in ff]
    rnd.shuffle(c)
    return c


def _facts_choices(d, rnd, form):
    q = _fact_q(d)
    if form == "select":
        return _pick(rnd, q["t"], q["f"], 1, 4)
    if form == "select2":
        return _pick(rnd, q["t"], q["f"], 2, 5)
    k = rnd.choice([1, 2, 2, 3])
    k = min(k, len(q["t"]), 5 - 1)
    if 5 - k > len(q["f"]):
        k = 5 - len(q["f"])
    return _pick(rnd, q["t"], q["f"], k, 5)


# ---- 既定モード(U1: 版を示して問う) ----------------------------------------
VER = {"old": ("Cisco IOS 15.2(4)E より前のリリースを実行する Catalyst スイッチ", "PVST+"),
       "new": ("Cisco IOS 15.2(4)E 以降のリリースを実行する Catalyst スイッチ", "Rapid PVST+"),
       "xe": ("Cisco IOS XE を実行する Catalyst 9000 シリーズ スイッチ", "Rapid PVST+")}


def _default_mode_choices(d, rnd):
    ctx, ans = VER[d["ver"]]
    opts = ["PVST+", "Rapid PVST+", "MST", "IEEE 802.1D(CST)"]
    why = {"PVST+": "15.2(4)E より前の IOS の既定。", "Rapid PVST+": "15.2(4)E 以降と Catalyst 9000(IOS XE)の既定。",
           "MST": "MST は明示的に `spanning-tree mode mst` を設定したときだけ。", "IEEE 802.1D(CST)": "Cisco の既定は VLAN ごとのインスタンス(PVST+ 系)。"}
    rnd.shuffle(opts)
    return [(o, o == ans, "" if o == ans else why[o]) for o in opts]


def build_choices_select(d, rnd):
    k = d["kind"]
    if k == "s_modes" and d.get("dm"):
        return _default_mode_choices(d, rnd)
    if k in FACTS and not (k == "s_guard" and d.get("req")):
        return _facts_choices(d, rnd, "select")
    if k == "s_guard":
        req, ans, why = GUARD_REQ[d["rq"]]
        others = [x for x in GUARD_ALL if x != ans]
        if ans == "UDLD のアグレッシブ モード":
            others = ["UDLD の通常モード"] + [x for x in others if x != "UDLD の通常モード"]
            picks = [ans] + others[:1] + rnd.sample(others[1:], 2)
        else:
            picks = [ans] + rnd.sample(others, 3)
        rnd.shuffle(picks)
        wrong = {"BPDU ガード": "BPDU を受信したポートを err-disabled にする機能。", "ルート ガード": "上位の BPDU を受けたポートを止めてルートの位置を守る機能。",
                 "ループ ガード": "BPDU が途絶えた非指定ポートを止める機能。", "UDLD のアグレッシブ モード": "片方向リンクを検出して err-disabled にする機能。",
                 "PortFast": "端末ポートをすぐフォワーディングにする機能。", "BPDU フィルタ": "BPDU を送受信しない機能(ループの危険)。",
                 "UDLD の通常モード": "通常モードは片方向でもポートを無効にしない。"}
        return [(p, p == ans, "" if p == ans else wrong[p]) for p in picks]
    if k == "s_elect":
        return _elect_ports(d, rnd, "select")
    if k == "s_tuning":
        return _tuning_select(d, rnd)
    raise ValueError(f"{k} に select は無い")


def build_choices_select2(d, rnd):
    k = d["kind"]
    if k in FACTS:
        if k == "s_modes" and d.get("dm"):
            raise ValueError("既定モードは select のみ")
        return _facts_choices(d, rnd, "select2")
    if k in ("s_elect", "s_read", "s_mst"):
        return _statements(d, rnd, 2, 5)
    if k == "s_tuning":
        return _tuning_facts(d, rnd, "select2")
    raise ValueError(f"{k} に select2 は無い")


def build_choices_allthat(d, rnd):
    k = d["kind"]
    if k in FACTS:
        if k == "s_modes" and d.get("dm"):
            raise ValueError("既定モードは select のみ")
        return _facts_choices(d, rnd, "allthat")
    if k == "s_elect":
        return _elect_ports(d, rnd, "allthat")
    if k in ("s_read", "s_mst"):
        return _statements(d, rnd, rnd.choice([1, 2, 2, 3]), 5)
    if k == "s_tuning":
        return _tuning_facts(d, rnd, "allthat")
    raise ValueError(f"{k} に allthat は無い")


def build_choices_read(d, rnd):
    k = d["kind"]
    if k == "s_elect":
        return _elect_path(d, rnd)
    if k in ("s_read", "s_mst"):
        return _statements(d, rnd, 1, 4)
    if k == "s_ts":
        return _ts_choices(d, rnd, "read")
    raise ValueError(f"{k} に read は無い")


def build_choices_cause(d, rnd):
    if d["kind"] != "s_ts":
        raise ValueError("cause は s_ts のみ")
    return _ts_choices(d, rnd, "cause")


def build_choices_fix(d, rnd):
    if d["kind"] == "s_ts":
        return _ts_choices(d, rnd, "fix")
    if d["kind"] == "s_tuning":
        if d["tt"] != "steer":
            raise ValueError("fix は steer のみ")
        return _steer_choices(d, rnd)
    raise ValueError("fix は s_ts/s_tuning のみ")


def build_match(d, rnd):
    k = d["kind"]
    if k not in MATCH:
        raise ValueError("match 無し")
    picks = rnd.sample(MATCH[k], 4)
    terms = [("①②③④"[i], t) for i, (t, _) in enumerate(picks)]
    descs = list(enumerate(picks))
    rnd.shuffle(descs)
    choices = [(LET[j], picks[i][1]) for j, (i, _) in enumerate(descs)]
    ans = {"①②③④"[i]: LET[j] for j, (i, _) in enumerate(descs)}
    d["_match"] = picks
    return terms, choices, dict(sorted(ans.items()))


# ==========================================================================
# s_elect: 盤面からポート / 経路 / 記述
# ==========================================================================
def _role_ja(r):
    return {"Root": "ルート ポート", "Desg": "指定ポート", "Altn": "代替ポート(ブロッキング)"}[r]


def _elect_ports(d, rnd, form):
    b, t = d["b"], d["t"]
    blocked = t.blocked()
    allp = sorted(t.role)
    if form == "select":
        if len(blocked) != 1:
            raise ValueError("ブロック 1 つの盤面ではない")
        d["ask_role"] = "Altn"
        cands = [p for p in allp if p not in blocked and p[0] != t.root]
        if len(cands) < 3:
            raise ValueError("肢不足")
        picks = blocked + rnd.sample(cands, 3)
    else:
        d["ask_role"] = rnd.choice(["Altn", "Root"])
        want = [p for p in allp if t.role[p] == d["ask_role"]]
        others = [p for p in allp if t.role[p] != d["ask_role"]]
        k = min(len(want), rnd.choice([1, 2, 3]))
        if len(others) < 5 - k:
            raise ValueError("肢不足")
        picks = rnd.sample(want, k) + rnd.sample(others, 5 - k)
    rnd.shuffle(picks)
    out = []
    for s, ifn in picks:
        r = t.role[(s, ifn)]
        ok = r == d["ask_role"]
        out.append((f"{s} の {ifn}", ok, "" if ok else f"{s} の {ifn} は{_role_ja(r)}。{_why_port(d, s, ifn)}"))
    return out


def _why_port(d, s, ifn):
    b, t = d["b"], d["t"]
    if s == t.root:
        return f"{s} はルート ブリッジで、全ポートが指定ポート。"
    peer = next((n, ni) for ifc, n, ni, sp in t.ports(s) if ifc["name"] == ifn)
    return f"このリンクの対向は {peer[0]} の {peer[1]['name']}({_role_ja(t.role[(peer[0], peer[1]['name'])])})。{s} のルート パス コストは {t.rpc[s]}。"


def _simple_paths(adj, a, bb, limit=12):
    out = []

    def dfs(x, path):
        if len(out) >= limit:
            return
        if x == bb:
            out.append(path)
            return
        for y in adj[x]:
            if y not in path:
                dfs(y, path + [y])
    dfs(a, [a])
    return out


def _elect_path(d, rnd):
    b, t = d["b"], d["t"]
    names = b["names"]
    adj = {s: sorted({n for _i, n, _ni, _sp in t.ports(s)}) for s in names}
    # 木の上の経路が「隣接しているのに遠回り」になる組を優先する(直結 1 ホップだけの問題を避ける)
    pairs = [(a, z) for a in names for z in names if a != z]
    rnd.shuffle(pairs)
    pairs.sort(key=lambda p: 0 if (p[1] in adj[p[0]] and len(t.path(*p)) > 2) else 1 if len(t.path(*p)) > 2 else 2)
    for a, z in pairs[:6]:
        good = t.path(a, z)
        paths = [p for p in _simple_paths(adj, a, z) if p != good]
        if len(paths) >= 3:
            break
    else:
        raise ValueError("経路の肢が作れない")
    d["pa"], d["pz"] = a, z
    wrong = []
    for p in paths:
        s = " → ".join(p)
        if s not in wrong:
            wrong.append(s)
    extra = [" → ".join([a] + [x for x in names if x not in (a, z)] + [z]),
             " → ".join([a, z]), " → ".join([a] + [x for x in reversed(names) if x not in (a, z)] + [z])]
    for s in extra:
        if s not in wrong and s != " → ".join(good):
            wrong.append(s)
    real_adj = {x: set(adj[x]) for x in names}

    def valid(s):
        hops = s.split(" → ")
        return all(hops[i + 1] in real_adj[hops[i]] for i in range(len(hops) - 1))
    wrong = [w for w in wrong if valid(w)]
    if len(wrong) < 3:
        raise ValueError("経路の肢不足")
    wrong = wrong[:3]
    c = [(" → ".join(good), True, "")]
    for w in wrong:
        c.append((w, False, "この経路はブロックされた(代替ポートを含む)リンクを通る。"))
    rnd.shuffle(c)
    return c


# ---- 盤面・出力に関する記述(s_elect / s_read / s_mst) ----------------------------
def _stmt_elect(d):
    b, t = d["b"], d["t"]
    T, F = [], []
    r = t.root
    others = [s for s in b["names"] if s != r]
    T.append(f"{r} がルート ブリッジになる")
    for s in others:
        F.append((f"{s} がルート ブリッジになる", f"ルート ブリッジは BID が最小の {r}。"))
    for s in others:
        T.append(f"{s} のルート ポートは {t.rp[s]} である")
        for ifc, n, ni, sp in t.ports(s):
            if ifc["name"] != t.rp[s]:
                F.append((f"{s} のルート ポートは {ifc['name']} である", f"{s} のルート ポートは {t.rp[s]}。"))
        T.append(f"{s} のルート パス コストは {t.rpc[s]} である")
        F.append((f"{s} のルート パス コストは {t.rpc[s] + sm.COST[b['method']]['1G']} である", f"{s} のルート パス コストは {t.rpc[s]}。"))
    bl = t.blocked()
    T.append(f"ブロッキング(代替)になるポートは {len(bl)} つである")
    F.append((f"ブロッキング(代替)になるポートは {len(bl) + 1} つである", f"代替ポートは {len(bl)} つ。"))
    return T, F


def _stmt_read(d):
    b, t, s = d["b"], d["t"], d["who"]
    v = b["vlan"]
    T, F = [], []
    rp_set = b["sw"][t.root]["prio"]
    if s == t.root:
        T.append(f"{s} はこの VLAN のルート ブリッジである")
    else:
        F.append((f"{s} はこの VLAN のルート ブリッジである", "Root ID と Bridge ID の Address が異なる(This bridge is the root が無い)。"))
        T.append(f"ルート ブリッジに設定されているブリッジ プライオリティは {rp_set} である")
        F.append((f"ルート ブリッジに設定されているブリッジ プライオリティは {rp_set + v} である", f"表示の {rp_set + v} は設定値 {rp_set} に VLAN ID {v}(sys-id-ext)を足した値。"))
        T.append(f"{s} からルート ブリッジまでのルート パス コストは {t.rpc[s]} である")
        T.append(f"{s} のルート ポートは {t.rp[s]} である")
    me = b["sw"][s]["prio"]
    T.append(f"{s} に設定されているブリッジ プライオリティは {me} である")
    F.append((f"{s} に設定されているブリッジ プライオリティは {me + v} である", f"{me + v} は表示値(設定値 {me}+VLAN ID {v})。"))
    for ifc, _n, _ni, sp in t.ports(s):
        ifn = ifc["name"]
        if t.role[(s, ifn)] == "Altn":
            T.append(f"{ifn} はデータ フレームを転送しない")
            F.append((f"{ifn} は指定ポートとしてデータ フレームを転送する", f"{ifn} は Altn BLK(代替・転送しない)。"))
        else:
            F.append((f"{ifn} はデータ フレームを転送しない", f"{ifn} は {t.role[(s, ifn)]} FWD(転送する)。"))
    if d["proto"] == "rstp":
        T.append("スパニング ツリーのモードは Rapid PVST+ である")
        F.append(("スパニング ツリーのモードは PVST+ である", "protocol rstp は Rapid PVST+(PVST+ は ieee)。"))
    else:
        T.append("スパニング ツリーのモードは PVST+ である")
        F.append(("スパニング ツリーのモードは Rapid PVST+ である", "protocol ieee は PVST+(Rapid PVST+ は rstp)。"))
    if b["method"] == "long":
        T.append("パス コストはロング方式で計算されている")
        F.append(("パス コストはショート方式で計算されている", "1 Gbps が 20000・10 Gbps が 2000 はロング方式の値。"))
    else:
        T.append("パス コストはショート方式で計算されている")
        F.append(("パス コストはロング方式で計算されている", "1 Gbps が 4・10 Gbps が 2 はショート方式の値。"))
    return T, F


BIN_GRP = [("スパニング ツリーのモードは", "mode"), ("パス コストは", "method"), ("同じ MST リージョン", "region"),
           ("異なる MST リージョン", "region"), ("境界ポート", "region"), ("この VLAN のルート ブリッジである", "isroot")]


def _grp_of(text):
    for key, g in BIN_GRP:
        if key in text:
            return g
    return None


def _statements(d, rnd, n_true, n_total):
    fn = {"s_elect": _stmt_elect, "s_read": _stmt_read, "s_mst": _stmt_mst}[d["kind"]]
    T, F = fn(d)
    T = list(dict.fromkeys(T))
    seen, F2 = set(T), []
    for f, w in F:
        if f not in seen:
            seen.add(f)
            F2.append((f, w))
    F = F2
    grp = {x: _grp_of(x) for x in T + [f for f, _w in F] if _grp_of(x)}
    return _pick(rnd, T, F, n_true, n_total, grp)


# ==========================================================================
# s_mst: 2 台の MST 設定の比較
# ==========================================================================
def _vl(vs):
    vs = sorted(set(vs))
    out, i = [], 0
    while i < len(vs):
        j = i
        while j + 1 < len(vs) and vs[j + 1] == vs[j] + 1:
            j += 1
        out.append(str(vs[i]) if i == j else f"{vs[i]}-{vs[j]}")
        i = j + 1
    return ",".join(out)


def _mst_show(name, rev, mp):
    inst = sorted(mp)
    used = {v for i in inst for v in mp[i]}
    rest = [v for v in range(1, 4095) if v not in used]
    L = [f"Name      [{name}]", f"Revision  {rev:<6}Instances configured {len(inst) + 1}", "",
         "Instance  Vlans mapped", "--------  ---------------------------------------------------------------------",
         f"{'0':<10}{_vl(rest)}"]
    for i in inst:
        L.append(f"{str(i):<10}{_vl(mp[i])}")
    L.append("-------------------------------------------------------------------------------")
    return "\n".join(L)


def _draw_mst(d, rnd):
    name = rnd.choice(["REGION1", "CAMPUS", "HQ-MST", "BLDG-A"])
    rev = rnd.randint(1, 9)
    vl = rnd.sample([10, 20, 30, 40, 50, 60, 100, 110, 200, 210], 6)
    mp = {1: sorted(vl[:3]), 2: sorted(vl[3:5])}
    d["loose"] = vl[5]           # どのインスタンスにも入れない VLAN(= IST)
    diff = rnd.choice(["same", "name", "rev", "map"])
    name2, rev2, mp2 = name, rev, {k: list(v) for k, v in mp.items()}
    if diff == "name":
        name2 = name.lower() if rnd.random() < 0.5 else name + "2"
    elif diff == "rev":
        rev2 = rev + 1
    elif diff == "map":
        v = mp2[1].pop(0)
        mp2[2] = sorted(mp2[2] + [v])
        d["moved"] = v
    d.update(mst_a=(name, rev, mp), mst_b=(name2, rev2, mp2), mst_diff=diff, pa="DSW1", pb="DSW2")


def _stmt_mst(d):
    (n1, r1, m1), (n2, r2, m2), diff = d["mst_a"], d["mst_b"], d["mst_diff"]
    a, b = d["pa"], d["pb"]
    T, F = [], []
    why_diff = {"name": f"リージョン名が {n1} と {n2} で異なる(大文字と小文字も区別される)。",
                "rev": f"リビジョン番号が {r1} と {r2} で異なる。",
                "map": f"VLAN {d.get('moved')} のインスタンスの割り当てが異なる。"}.get(diff, "")
    if diff == "same":
        T.append(f"{a} と {b} は同じ MST リージョンに属する")
        F.append((f"{a} と {b} は異なる MST リージョンに属する", "名前・リビジョン・対応がすべて一致している。"))
        F.append((f"{a} と {b} の間のポートは、リージョンの境界ポートになる", "同じリージョン内なので境界にならない。"))
    else:
        T.append(f"{a} と {b} は異なる MST リージョンに属する")
        T.append(f"{a} と {b} の間のポートは、リージョンの境界ポートになる")
        F.append((f"{a} と {b} は同じ MST リージョンに属する", why_diff))
    lo = d["loose"]
    T.append(f"{a} では、VLAN {lo} はインスタンス 0(IST)に属する")
    F.append((f"{a} では、VLAN {lo} のスパニング ツリーは動作しない", "未割り当ての VLAN はインスタンス 0(IST)に属する。"))
    v1 = m1[1][-1]
    T.append(f"{a} では、VLAN {v1} はインスタンス 1 に属する")
    F.append((f"{a} では、VLAN {v1} はインスタンス 2 に属する", f"{a} の対応では VLAN {v1} はインスタンス 1。"))
    if diff != "same":
        F.append((f"{a} と {b} は、VLAN とインスタンスの対応が同じなら同じリージョンになる", "名前とリビジョンも一致が必要。") if diff != "map"
                 else (f"{a} と {b} は、リージョン名とリビジョン番号が同じなので同じリージョンになる", why_diff))
    return T, F


# ==========================================================================
# s_tuning
# ==========================================================================
def _primary_result(cur, cur_mac_lower_than_me):
    """root primary の結果(Cisco 公式+実測 M2)。None= 失敗。"""
    if cur > 24576 or (cur == 24576 and not cur_mac_lower_than_me):
        return 24576
    need = cur - 4096
    return need if need >= 1 else None


def _draw_tuning(d, rnd):
    tt = d["tt"]
    d["v"] = rnd.choice([10, 20, 30, 100])
    if tt == "primary":
        d["cur"], d["lose"] = rnd.choice([(32768, False), (16384, False), (24576, True), (24576, False), (8192, False), (4096, False), (0, False)])
        d["res"] = _primary_result(d["cur"], d["lose"])
    elif tt == "secondary":
        d["sec_world"] = rnd.choice(["alldef", "rootset"])
    elif tt == "steer":
        _draw_steer(d, rnd)


def _tuning_exhibit(d, used=None):
    v = d["v"]
    used = set()
    rnd = random.Random(d["cur"] * 7 + v + (1 if d["lose"] else 0))
    mr, mm = _mac(rnd, used), _mac(rnd, used)
    if d["lose"]:
        mr, mm = sorted([mr, mm], key=sm.mac_key)
    else:
        mr, mm = sorted([mr, mm], key=sm.mac_key, reverse=True)
    d["mac_root"], d["mac_me"] = mr, mm
    cost = 4
    return "\n".join([f"DSW2# show spanning-tree vlan {v}", "", f"VLAN{v:04d}", "  Spanning tree enabled protocol rstp",
                      f"  Root ID    Priority    {d['cur'] + v}", f"             Address     {mr}",
                      f"             Cost        {cost}", "             Port        1 (GigabitEthernet1/0/1)",
                      "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec", "",
                      f"  Bridge ID  Priority    {32768 + v:<7}(priority 32768 sys-id-ext {v})",
                      f"             Address     {mm}",
                      "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec",
                      "             Aging Time  300 sec"])


def _tuning_select(d, rnd):
    tt = d["tt"]
    if tt == "primary":
        r = d["res"]
        opts = []
        for val in (24576, 20480, 12288, 4096, 0):
            ok = r == val
            opts.append((f"ブリッジ プライオリティが {val} に設定され、DSW2 がルート ブリッジになる", ok,
                         "" if ok else _primary_why(d, val)))
        fail_ok = r is None
        opts.append(("コマンドはエラーになり、ブリッジ プライオリティは変わらない", fail_ok, "" if fail_ok else _primary_why(d, "fail")))
        correct = [o for o in opts if o[1]]
        wrong = [o for o in opts if not o[1]]
        c = correct + rnd.sample(wrong, 3)
        rnd.shuffle(c)
        return c
    if tt == "secondary":
        return _secondary_choices(d, rnd)
    raise ValueError("select は primary/secondary")


def _primary_why(d, val):
    r = d["res"]
    base = ("root primary は、24576 でルートになれるなら 24576、なれなければ現在のルートより 4096 小さい値を設定し、"
            "必要な値が 1 未満なら失敗する(実機: `% Failed to make the bridge root`)。")
    if r is None:
        return base + f"現在のルートは {d['cur']} なので、必要な値が 1 未満になり失敗する。"
    return base + f"この盤面では {r} になる。"


def _secondary_choices(d, rnd):
    w = d["sec_world"]
    v = d["v"]
    # alldef: DSW1/DSW2/ASW1 全員既定。ASW1 で secondary → 28672 で ASW1 がルートになる(実測 M3)
    # rootset: DSW1 が priority 24576。DSW2 で secondary → 28672・ルートは DSW1 のまま
    if w == "alldef":
        ans = "ASW1"
        why = {"DSW1": "全員が既定の 32768 の VLAN で ASW1 だけが 28672 になるので、ASW1 の方が小さい。",
               "DSW2": "DSW2 は既定の 32768 のまま。", "ASW2": "ASW2 は既定の 32768 のまま。"}
    else:
        ans = "DSW1"
        why = {"ASW1": "ASW1 は既定の 32768 のまま。", "DSW2": "secondary は 28672 で、DSW1 の 24576 より大きい。",
               "ASW2": "ASW2 は既定の 32768 のまま。"}
    opts = ["DSW1", "DSW2", "ASW1", "ASW2"]
    rnd.shuffle(opts)
    return [(o, o == ans, "" if o == ans else why[o]) for o in opts]


TUNING_FACTS = {"ask": "ブリッジ プライオリティとパス コストのチューニング", "t": [
    "`spanning-tree vlan 10 root primary` は、実行した時点の値から計算したブリッジ プライオリティを設定として書き込む",
    "`spanning-tree vlan 10 root secondary` は、ブリッジ プライオリティを 28672 に設定する",
    "`spanning-tree port-priority` の値は、そのポートから BPDU を受け取る対向のスイッチのルート ポート選択に影響する",
    "`spanning-tree cost` の値は、そのスイッチ自身のルート ポート選択に影響する",
    "ポート プライオリティは 16 の倍数で設定し、既定値は 128 である",
    "`spanning-tree pathcost method long` はグローバル コンフィギュレーション モードで設定する"], "f": [
    ("`spanning-tree vlan 10 root primary` を設定したスイッチは、後から他のスイッチのプライオリティが下がっても自動で追従してルートを保つ", "一度だけ計算して数値を書き込む。後から追従しない[M2]。"),
    ("`spanning-tree vlan 10 root secondary` は、現在のルートより 4096 大きい値を設定する", "secondary は常に 28672[M3]。"),
    ("自分のポートの port-priority を下げると、自分のルート ポートがそのポートに変わる", "port-priority は送信元(上流)側の値が効く。下流で変えても変わらない[M4]。"),
    ("ポート プライオリティは 1 刻みで任意の値を設定できる", "16 の倍数(実機: `% Port Priority in increments of 16 is required`)[M4]。"),
    ("`spanning-tree pathcost method long` はインターフェイス コンフィギュレーション モードで設定する", "グローバル コンフィギュレーション モードで設定する。"),
    ("ロング方式のパス コストは 16 ビットの値である", "ロング方式は 32 ビット(ショートが 16 ビット)。")]}


def _tuning_facts(d, rnd, form):
    q = TUNING_FACTS
    if form == "select2":
        return _pick(rnd, q["t"], q["f"], 2, 5)
    k = rnd.choice([1, 2, 3])
    return _pick(rnd, q["t"], q["f"], k, 5)


# ---- steer: 並列 2 本で DSW2 のルート ポートを寄せる ------------------------------------
def _draw_steer(d, rnd):
    v = d["v"]
    used = set()
    sw = {"DSW1": {"prio": 4096, "mac": _mac(rnd, used)}, "DSW2": {"prio": 32768, "mac": _mac(rnd, used)}}
    a1, a2 = rnd.sample(range(1, 9), 2)
    a1, a2 = sorted((a1, a2))
    b1, b2 = sorted(rnd.sample(range(1, 9), 2))
    links = [("DSW1", _ifc("1G", a1), "DSW2", _ifc("1G", b1), "1G"), ("DSW1", _ifc("1G", a2), "DSW2", _ifc("1G", b2), "1G")]
    d["steer"] = {"sw": sw, "links": links, "v": v, "side": rnd.choice(["up", "down"])}
    t = sm.Topo(sw, links, "short", vlan=v).solve()
    d["steer"]["now"] = t.rp["DSW2"]
    d["steer"]["want"] = [ib["name"] for _a, _ia, _b, ib, _sp in links if ib["name"] != t.rp["DSW2"]][0]


def _steer_eval(st, change):
    """change= (sw, ifname, 'prio'|'cost', value)。DSW2 のルート ポート。"""
    pp, co = {}, {}
    s, ifn, what, val = change
    (pp if what == "prio" else co)[(s, ifn)] = val
    return sm.Topo(st["sw"], st["links"], "short", pp, co, st["v"]).solve().rp["DSW2"]


def _steer_choices(d, rnd):
    st = d["steer"]
    v = st["v"]
    (a, ia, b, ib, _), (a2, ia2, b2, ib2, _) = st["links"]
    now, want = st["now"], st["want"]
    up_now = ia["name"] if ib["name"] == now else ia2["name"]
    up_want = ia2["name"] if ib2["name"] == want else ia["name"]
    cands = [
        (("DSW1", up_want, "prio", 64), f"DSW1 の {up_want} で `spanning-tree vlan {v} port-priority 64` を設定する"),
        (("DSW2", want, "prio", 64), f"DSW2 の {want} で `spanning-tree vlan {v} port-priority 64` を設定する"),
        (("DSW1", up_now, "prio", 64), f"DSW1 の {up_now} で `spanning-tree vlan {v} port-priority 64` を設定する"),
        (("DSW2", now, "cost", 10), f"DSW2 の {now} で `spanning-tree vlan {v} cost 10` を設定する"),
        (("DSW2", want, "cost", 2), f"DSW2 の {want} で `spanning-tree vlan {v} cost 2` を設定する"),
        (("DSW1", up_want, "cost", 2), f"DSW1 の {up_want} で `spanning-tree vlan {v} cost 2` を設定する"),
    ]
    side_sw = "DSW1" if st["side"] == "up" else "DSW2"
    # 下流(DSW2)側は cost の 2 通り(使用中を上げる/使いたい方を下げる)がどちらも成立するので、片方だけ肢に出す
    drop = rnd.choice([3, 4])
    cands = [c for i, c in enumerate(cands) if i != drop]
    out = []
    for ch, text in cands:
        res = _steer_eval(st, ch)
        ok_path = res == want
        ok = ok_path and ch[0] == side_sw
        if ok:
            why = ""
        elif not ok_path:
            why = ("port-priority は送信元(上流)側の値が効く。下流で変えてもルート ポートは変わらない[M4]。" if (ch[0] == "DSW2" and ch[2] == "prio")
                   else "cost は自分(受信側)のルート ポート選択に効く。上流のコストを変えても DSW2 の計算は変わらない。" if (ch[0] == "DSW1" and ch[2] == "cost")
                   else f"この変更では DSW2 のルート ポートは {res} のまま。")
        else:
            why = f"経路は {want} に移るが、要件は {side_sw} の設定だけを変更すること。"
        out.append((text, ok, why))
    right = [o for o in out if o[1]]
    wrong = [o for o in out if not o[1]]
    if len(right) != 1:
        raise ValueError(f"steer 正解 {len(right)}")
    c = right + rnd.sample(wrong, 3)
    rnd.shuffle(c)
    return c


# ==========================================================================
# s_ts: 症状(実機の書式)→ 原因・是正・読解
# ==========================================================================
def _ts_bpduguard(d, rnd):
    p = rnd.randint(5, 24)
    mac = _mac(rnd, set())
    d["ts"] = {"if": f"Gi1/0/{p}", "mac": mac,
               "ex": "\n".join([
                   f"*Sep 22 05:10:42.525: %SPANTREE-2-BLOCK_BPDUGUARD: Received BPDU from bridge {mac} on port Gi1/0/{p} with BPDU Guard enabled. Disabling port.",
                   f"*Sep 22 05:10:42.525: %PM-4-ERR_DISABLE: bpduguard error detected on Gi1/0/{p}, putting Gi1/0/{p} in err-disable state",
                   "", "ASW1# show interfaces status err-disabled", "",
                   "Port         Name         Status       Reason               Err-disabled Vlans", "",
                   f"Gi1/0/{p:<6}              err-disabled bpduguard"])}


def _ts_rootguard(d, rnd):
    d["ts"] = {"ex": "\n".join([
        "DSW1# show spanning-tree inconsistentports", "",
        "Name                 Interface                      Inconsistency",
        "-------------------- ------------------------------ ------------------",
        "VLAN0010             GigabitEthernet1/0/1           Root Inconsistent",
        "VLAN0020             GigabitEthernet1/0/1           Root Inconsistent", "",
        "Number of inconsistent ports (segments) in the system : 2", "",
        "DSW1# show running-config interface GigabitEthernet1/0/1",
        "interface GigabitEthernet1/0/1", " description to DSW2", " switchport mode trunk", " spanning-tree guard root"])}


def _ts_loopguard(d, rnd):
    d["ts"] = {"ex": "\n".join([
        "*Sep 22 05:09:59.068: %SPANTREE-2-LOOPGUARD_BLOCK: Loop guard blocking port GigabitEthernet1/0/2 on VLAN0010.",
        "", "ASW1# show spanning-tree vlan 10 | include Gi1/0",
        "Gi1/0/1             Root FWD 4         128.1    P2p ",
        "Gi1/0/2             Desg BKN*4         128.2    P2p *LOOP_Inc ", "",
        "DSW2# show running-config interface GigabitEthernet1/0/3",
        "interface GigabitEthernet1/0/3", " description to ASW1", " switchport mode trunk", " spanning-tree bpdufilter enable"])}


def _ts_pvstsim(d, rnd):
    d["ts"] = {"ex": "\n".join([
        "*Sep 22 05:14:49.470: %SPANTREE-2-PVSTSIM_FAIL: Blocking designated port Gi1/0/1: Inconsitent superior PVST BPDU received on VLAN 10, claiming root 4106:0019.e8a1.4000",
        "", "SW3# show spanning-tree mst 0 | include Gi1/0",
        "Gi1/0/1                          Desg BKN*20000     128.1    P2p Bound(PVST) *PVST_Inc ",
        "Gi1/0/2                          Desg BKN*20000     128.2    P2p Bound(PVST) *PVST_Inc "])}


def _ts_region(d, rnd):
    d["ts"] = {"ex": "\n".join([
        "DSW1# show spanning-tree mst configuration", _mst_show("CAMPUS", 2, {1: [10, 20], 2: [30, 40]}), "",
        "DSW2# show spanning-tree mst configuration", _mst_show("CAMPUS", 3, {1: [10, 20], 2: [30, 40]}), "",
        "DSW1# show spanning-tree mst 0 | include Gi1/0/1",
        "Gi1/0/1                          Desg FWD 20000     128.1    P2p Bound(RSTP) "])}


def _ts_peerstp(d, rnd):
    d["ts"] = {"ex": "\n".join([
        "DSW1# show spanning-tree vlan 10 | include Gi1/0",
        "Gi1/0/1             Desg FWD 4         128.1    P2p ",
        "Gi1/0/2             Desg FWD 4         128.2    P2p Peer(STP) "])}


TS = {
    "bpduguard": {"draw": _ts_bpduguard,
                  "before": "ASW1 のアクセス ポートに利用者がハブを接続したと申告があった後、そのポートの通信ができなくなりました。ASW1 では次のログと出力を確認しました。",
                  "cause": ("ポートで BPDU ガードが有効になっており、接続された機器から BPDU を受信した", [
                      ("ポートでループ ガードが有効になっており、BPDU が届かなくなった", "ループ ガードなら loop-inconsistent になり、err-disabled にはならない。"),
                      ("ポートでルート ガードが有効になっており、上位の BPDU を受信した", "ルート ガードなら root-inconsistent になり、err-disabled にはならない。"),
                      ("UDLD が片方向リンクを検出した", "Reason が udld ではなく bpduguard。")]),
                  "fix_req": "要件: スイッチを接続させない方針は維持します。",
                  "fix": ("BPDU を送信している機器を取り外してから、そのポートで shutdown と no shutdown を実行する", [
                      ("そのポートに `spanning-tree bpdufilter enable` を追加する", "BPDU フィルタは BPDU ガードより優先され[M8]、スイッチの接続を許してしまう(要件違反・ループの危険)。"),
                      ("そのポートの `spanning-tree bpduguard enable` を削除する", "スイッチの接続を許してしまう(要件違反)。"),
                      ("グローバルで `spanning-tree loopguard default` を設定する", "ループ ガードは err-disabled の復旧とは関係しない。")]),
                  "read": ("このポートは BPDU を受信したことで err-disabled になった", [
                      ("このポートは root-inconsistent 状態になっている", "Status は err-disabled・Reason は bpduguard。"),
                      ("このポートは既定で 300 秒後に自動で回復する", "err-disabled からの自動復旧は既定で無効[M12]。"),
                      ("このポートはブロッキング状態で BPDU の受信だけは続けている", "err-disabled はポート自体が停止している。")])},
    "rootguard": {"draw": _ts_rootguard,
                  "before": "設計では VLAN 10 のルート ブリッジは DSW1、VLAN 20 のルート ブリッジは DSW2 です。DSW2 の VLAN 20 の利用者が DSW1 の先と通信できなくなりました。",
                  "cause": ("DSW1 の Gi1/0/1 のルート ガードはポート上のすべての VLAN に作用し、VLAN 20 の正当なルートである DSW2 の BPDU を上位の BPDU として扱った", [
                      ("DSW2 の VLAN 20 のブリッジ プライオリティが DSW1 より大きい", "設計どおり DSW2 が VLAN 20 のルート。問題は DSW1 のルート ガード。"),
                      ("DSW1 の Gi1/0/1 で BPDU ガードが BPDU を受信した", "BPDU ガードなら err-disabled になる。表示は Root Inconsistent。"),
                      ("DSW1 と DSW2 の間で片方向リンクが発生した", "片方向ならループ ガード/UDLD の指紋になる。")]),
                  "fix_req": "要件: VLAN 20 のルート ブリッジは DSW2 のままにします。",
                  "fix": ("DSW1 の Gi1/0/1 から `spanning-tree guard root` を削除する", [
                      ("DSW2 で `spanning-tree vlan 20 priority 61440` を設定する", "VLAN 20 のルートが DSW2 でなくなる(要件違反)。"),
                      ("DSW1 の Gi1/0/1 のルート ガードを、VLAN 10 だけに作用するように設定し直す", "ルート ガードはポートのすべての VLAN に作用し、VLAN を限定する設定は無い[C][M9]。"),
                      ("DSW1 の Gi1/0/1 で shutdown と no shutdown を実行する", "上位 BPDU を受け続ける限り root-inconsistent に戻る。")]),
                  "read": ("DSW1 の Gi1/0/1 は、VLAN 10 と VLAN 20 の両方でフレームを転送していない", [
                      ("DSW1 の Gi1/0/1 は err-disabled になっている", "Root Inconsistent はポート単位の STP の状態で、err-disabled ではない。"),
                      ("VLAN 10 だけがブロックされ、VLAN 20 は転送されている", "両方の VLAN が Root Inconsistent。"),
                      ("Gi1/0/1 のルート ガードは、上位の BPDU が止まっても shutdown/no shutdown まで回復しない", "上位の BPDU が止まれば自動で回復する[M9]。")])},
    "loopguard": {"draw": _ts_loopguard,
                  "before": "ASW1 は Gi1/0/1 で DSW1 に、Gi1/0/2 で DSW2 の Gi1/0/3 に接続しています。ASW1 で次のログと出力を確認しました。",
                  "cause": ("DSW2 の Gi1/0/3 の BPDU フィルタにより、ASW1 の Gi1/0/2 に BPDU が届かなくなり、ループ ガードが作用した", [
                      ("ASW1 の Gi1/0/2 で上位の BPDU を受信し、ルート ガードが作用した", "表示は LOOP_Inc(ループ ガード)。"),
                      ("ASW1 の Gi1/0/2 で BPDU ガードが作用した", "BPDU ガードなら err-disabled になる。"),
                      ("DSW2 の Gi1/0/3 が err-disabled になっている", "DSW2 の Gi1/0/3 は BPDU を送らないだけで、リンクは動いている。")]),
                  "fix_req": "",
                  "fix": ("DSW2 の Gi1/0/3 から `spanning-tree bpdufilter enable` を削除する", [
                      ("ASW1 の Gi1/0/2 から `spanning-tree guard loop` を削除する", "BPDU が届かないまま Gi1/0/2 がフォワーディングになり、ループの危険がある。"),
                      ("ASW1 の Gi1/0/2 で shutdown と no shutdown を実行する", "BPDU が届かない限り再び loop-inconsistent になる。"),
                      ("ASW1 の Gi1/0/2 に `spanning-tree bpduguard enable` を追加する", "BPDU が届かない問題は解消しない。")]),
                  "read": ("ASW1 の Gi1/0/2 は、BPDU を再び受信すると自動でブロックが解除される", [
                      ("ASW1 の Gi1/0/2 は err-disabled になっている", "loop-inconsistent は STP の状態で err-disabled ではない。"),
                      ("ASW1 の Gi1/0/2 は、BPDU を受信しても shutdown/no shutdown まで回復しない", "受信を再開すると自動で回復する[M10]。"),
                      ("ASW1 の Gi1/0/2 は、上位の BPDU を受信したためにブロックされている", "上位の BPDU ではなく、BPDU が届かないことが原因。")])},
    "pvstsim": {"draw": _ts_pvstsim,
                "before": "Rapid PVST+ で運用しているネットワークに、MST で構成した SW3 を接続しました。SW3 で次のログと出力を確認しました。",
                "cause": ("PVST+ 側に、MST の CIST のルートより優位なルート ブリッジを持つ VLAN があり、境界で PVST シミュレーションの整合性が取れない", [
                    ("SW3 と隣接スイッチの MST リージョンの名前が一致していない", "隣接は Rapid PVST+ で MST リージョンではない。リージョン不一致の指紋は Bound(RSTP)。"),
                    ("SW3 のポートで BPDU ガードが BPDU を受信した", "BPDU ガードなら err-disabled になる。"),
                    ("SW3 のパス コストの方式がロングになっている", "MST はロングの値を使う。コストの方式は PVST シミュレーションの不整合の原因ではない。")]),
                "fix_req": "", "fix": None,
                "read": ("SW3 の Gi1/0/1 と Gi1/0/2 は、MST リージョンと PVST+ の境界のポートである", [
                    ("SW3 の Gi1/0/1 は err-disabled になっている", "BKN* は STP の不整合によるブロックで、err-disabled ではない。"),
                    ("SW3 の Gi1/0/1 と Gi1/0/2 はフレームを転送している", "Desg BKN*(broken)で転送していない。"),
                    ("SW3 は PVST+ で動作している", "show spanning-tree mst の出力で、SW3 は MST で動作している。")])},
    "region": {"draw": _ts_region,
               "before": "DSW1 と DSW2 を同じ MST リージョンとして構成したつもりですが、DSW1 の Gi1/0/1(DSW2 向け)が境界ポートになっています。",
               "cause": ("DSW1 と DSW2 のリビジョン番号が一致していない", [
                   ("DSW1 と DSW2 のリージョン名が一致していない", "Name はどちらも CAMPUS。"),
                   ("DSW1 と DSW2 の VLAN とインスタンスの対応が一致していない", "インスタンス 1・2 の VLAN は同じ。"),
                   ("DSW2 が Rapid PVST+ で動作している", "DSW2 も show spanning-tree mst configuration を出しており MST で動作している。")]),
               "fix_req": "",
               "fix": ("DSW2 の `spanning-tree mst configuration` で `revision 2` を設定する", [
                   ("DSW2 の `spanning-tree mst configuration` で `name campus` を設定する", "名前は既に一致している(しかも大文字と小文字は区別される)。"),
                   ("DSW1 と DSW2 で `spanning-tree mode rapid-pvst` を設定する", "MST リージョンを作る要件をやめてしまう。"),
                   ("DSW1 の Gi1/0/1 で `spanning-tree guard root` を設定する", "境界の原因(リビジョンの不一致)は解消しない。")]),
               "read": ("DSW1 と DSW2 は異なる MST リージョンに属している", [
                   ("DSW1 と DSW2 は同じ MST リージョンに属している", "リビジョン番号が 2 と 3 で異なる。"),
                   ("DSW1 の Gi1/0/1 はフレームを転送していない", "Desg FWD で転送している(境界ポートでも転送はする)。"),
                   ("VLAN 50 はどちらのスイッチでもスパニング ツリーが動作していない", "未割り当ての VLAN はインスタンス 0(IST)に属する。")])},
    "peerstp": {"draw": _ts_peerstp,
                "before": "DSW1 と DSW2 を Rapid PVST+ で運用しています。DSW1 の Gi1/0/2 は ASW1 に接続しています。",
                "cause": ("ASW1 が PVST+(IEEE 802.1D)で動作しており、DSW1 の Gi1/0/2 は 802.1D の動作に切り替わっている", [
                    ("ASW1 が MST で動作している", "MST との境界なら Bound の表示になる。"),
                    ("DSW1 の Gi1/0/2 で BPDU フィルタが有効になっている", "BPDU フィルタでは Peer(STP) は表示されない。"),
                    ("DSW1 の Gi1/0/2 が半二重で動作している", "半二重なら Type が Shr になる。")]),
                "fix_req": "",
                "fix": ("ASW1 で `spanning-tree mode rapid-pvst` を設定し、DSW1 と ASW1 の両方で `clear spanning-tree detected-protocols` を実行する", [
                    ("DSW1 で `spanning-tree mode pvst` を設定する", "全体を 802.1D に落としてしまい、高速収束を失う。"),
                    ("ASW1 で `spanning-tree mode rapid-pvst` を設定するだけでよい(Peer(STP) は必ず自動で消える)", "自動では戻らない場合がある。実機でも残った[M14]。"),
                    ("DSW1 だけで `clear spanning-tree detected-protocols` を実行する", "clear は実行した側だけに効く。対向の検出結果は残る[M14]。")]),
                "read": ("DSW1 の Gi1/0/2 の対向は IEEE 802.1D の BPDU を送っている", [
                    ("DSW1 の Gi1/0/2 は代替ポートとしてブロックされている", "Desg FWD(指定・転送)。"),
                    ("DSW1 の Gi1/0/2 は共有リンクとして扱われている", "Type は P2p。"),
                    ("DSW1 の Gi1/0/2 はエッジ ポートとして動作している", "Edge の表示は無い。")])},
}


def _ts_choices(d, rnd, form):
    sc = TS[d["sc"]]
    ent = sc[form]
    if ent is None:
        raise ValueError(f"{d['sc']} に {form} は無い")
    right, wrongs = ent
    c = [(right, True, "")] + [(w, False, why) for w, why in wrongs]
    rnd.shuffle(c)
    return c


# ==========================================================================
# Markdown
# ==========================================================================
def _ch_md(choices):
    return "\n\n".join(f"{LET[i]}. {t}" for i, (t, _, _) in enumerate(choices))


def _suffix(form, n=None):
    return {"select": "(1つを選択してください)", "read": "(1つを選択してください)", "cause": "(1つを選択してください)",
            "fix": "(1つを選択してください)", "select2": "(2つを選択してください)", "allthat": "すべて選んでください。"}[form]


def question_body(d, choices, form):
    k = d["kind"]
    if form == "match":
        terms, ch, _ = choices
        head = {"s_basic": "ポートの状態", "s_rstp": "ポートの役割", "s_modes": "方式"}[k]
        terms_md = f"### 対応させる項目\n\n| # | {head} |\n|---|------|\n" + "\n".join(f"| {a} | {t} |" for a, t in terms)
        ch_md = "\n\n".join(f"{a}. {t}" for a, t in ch)
        return "", f"左側の①〜④の{head}の説明として正しいものを、右側の A〜D から選択してください。", ch_md, terms_md
    if k in FACTS and not (k == "s_guard" and d.get("req")) and not (k == "s_modes" and d.get("dm")):
        q = _fact_q(d)
        if form == "allthat":
            ask = f"{q['ask']}について正しい記述を、すべて選んでください。"
        else:
            ask = f"{q['ask']}について正しい記述はどれですか。{_suffix(form)}"
        return "", ask, _ch_md(choices), ""
    if k == "s_modes":
        ctx, _ = VER[d["ver"]]
        return "", f"{ctx}で、スパニング ツリーのモードを何も設定していない場合に動作するモードはどれですか。{_suffix('select')}", _ch_md(choices), ""
    if k == "s_guard":
        req = GUARD_REQ[d["rq"]][0]
        return f"要件: {req}", f"この要件を満たすためにポートで有効にする機能はどれですか。{_suffix('select')}", _ch_md(choices), ""
    if k == "s_elect":
        before = board_md(d["b"])
        if form == "select":
            ask = f"VLAN {d['b']['vlan']} でフレームを転送しない(代替ポートになる)ポートはどれですか。{_suffix(form)}"
        elif form == "allthat":
            what = "フレームを転送しない(代替ポートになる)" if d["ask_role"] == "Altn" else "ルート ポートになる"
            ask = f"VLAN {d['b']['vlan']} で{what}ポートを、すべて選んでください。"
        elif form == "read":
            ask = (f"{d['pa']} に接続した PC から {d['pz']} に接続した PC へ VLAN {d['b']['vlan']} のフレームを送信します。"
                   f"フレームが経由するスイッチの順序として正しいものはどれですか。{_suffix(form)}")
        else:
            ask = f"VLAN {d['b']['vlan']} のスパニング ツリーについて正しい記述はどれですか。{_suffix(form)}"
        return before, ask, _ch_md(choices), ""
    if k == "s_read":
        s = d["who"]
        ex = show_vlan(d["b"], d["t"], s, d["proto"])
        before = f"{s} で次の出力を確認しました。\n\n```\n{s}# show spanning-tree vlan {d['b']['vlan']}\n\n{ex}\n```"
        ask = (f"この出力から読み取れることを、すべて選んでください。" if form == "allthat"
               else f"この出力から読み取れることとして正しいものはどれですか。{_suffix(form)}")
        return before, ask, _ch_md(choices), ""
    if k == "s_mst":
        (n1, r1, m1), (n2, r2, m2) = d["mst_a"], d["mst_b"]
        before = (f"{d['pa']} と {d['pb']} を直結し、どちらも `spanning-tree mode mst` で動作させています。\n\n```\n"
                  f"{d['pa']}# show spanning-tree mst configuration\n{_mst_show(n1, r1, m1)}\n\n"
                  f"{d['pb']}# show spanning-tree mst configuration\n{_mst_show(n2, r2, m2)}\n```")
        ask = ("この構成について正しい記述を、すべて選んでください。" if form == "allthat"
               else f"この構成について正しい記述はどれですか。{_suffix(form)}")
        return before, ask, _ch_md(choices), ""
    if k == "s_tuning":
        tt = d["tt"]
        if tt == "primary":
            ex = _tuning_exhibit(d)
            before = f"DSW2 で次の出力を確認しました。\n\n```\n{ex}\n```"
            ask = (f"DSW2 で `spanning-tree vlan {d['v']} root primary` を実行したときの結果として正しいものはどれですか。{_suffix('select')}")
            return before, ask, _ch_md(choices), ""
        if tt == "secondary":
            v = d["v"]
            if d["sec_world"] == "alldef":
                before = (f"DSW1・DSW2・ASW1・ASW2 の 4 台で Rapid PVST+ を使用しています。VLAN {v} のブリッジ プライオリティはどのスイッチも既定値のままです。"
                          f"ASW1 で `spanning-tree vlan {v} root secondary` を実行しました。")
            else:
                before = (f"DSW1・DSW2・ASW1・ASW2 の 4 台で Rapid PVST+ を使用しています。DSW1 には `spanning-tree vlan {v} priority 24576` を設定しており、"
                          f"ほかのスイッチの VLAN {v} のブリッジ プライオリティは既定値のままです。DSW2 で `spanning-tree vlan {v} root secondary` を実行しました。")
            return before, f"実行後、VLAN {v} のルート ブリッジになるスイッチはどれですか。{_suffix('select')}", _ch_md(choices), ""
        if tt == "steer":
            st = d["steer"]
            v = st["v"]
            (a, ia, b, ib, _), (a2, ia2, b2, ib2, _) = st["links"]
            side = "DSW1" if st["side"] == "up" else "DSW2"
            mm = "\n".join(["```mermaid", "graph LR", '  n_DSW1["DSW1<br/>VLAN %d ルート"]' % v, '  n_DSW2["DSW2"]',
                            f'  n_DSW1 ---|"{ia["name"]} — {ib["name"]}"| n_DSW2', f'  n_DSW1 ---|"{ia2["name"]} — {ib2["name"]}"| n_DSW2', "```"])
            before = (f"{mm}\n\nDSW1 と DSW2 を 1 Gbps のトランク 2 本で接続し、Rapid PVST+(ショート方式)で運用しています。"
                      f"DSW1 は VLAN {v} のルート ブリッジで、現在 DSW2 の VLAN {v} のルート ポートは {st['now']} です。記載のない設定は既定値です。")
            ask = (f"DSW2 の VLAN {v} のルート ポートを {st['want']} に変更したい。{side} の設定だけを変更して要件を満たす方法はどれですか。{_suffix('fix')}")
            return before, ask, _ch_md(choices), ""
        q = TUNING_FACTS
        ask = (f"{q['ask']}について正しい記述を、すべて選んでください。" if form == "allthat"
               else f"{q['ask']}について正しい記述はどれですか。{_suffix(form)}")
        return "", ask, _ch_md(choices), ""
    if k == "s_ts":
        sc = TS[d["sc"]]
        before = f"{sc['before']}\n\n```\n{d['ts']['ex']}\n```"
        if form == "cause":
            ask = f"この事象の原因として最も適切なものはどれですか。{_suffix(form)}"
        elif form == "fix":
            req = sc.get("fix_req") or ""
            ask = (req + ("\n\n" if req else "")) + f"この事象を解消する方法として最も適切なものはどれですか。{_suffix(form)}"
        else:
            ask = f"この出力から読み取れることとして正しいものはどれですか。{_suffix(form)}"
        return before, ask, _ch_md(choices), ""
    raise ValueError(k)


def explain_board(b, t):
    """各スイッチのルート ポートが何で決まったか・代替ポートの理由を 1 行ずつ(stp_model の比較をそのまま文章化)。"""
    L = [f"- ルート ブリッジ= {t.root}(ブリッジ ID(priority, MAC)が最小: priority {b['sw'][t.root]['prio']}・{b['sw'][t.root]['mac']})。"]
    for s in b["names"]:
        if s == t.root:
            continue
        cands = []
        for ifc, n, nif, sp in t.ports(s):
            cands.append(((t.rpc[n] + t.pcost(s, ifc, sp), t.bid(n), t.pid(n, nif)), ifc["name"], n, nif["name"], t.rpc[n], t.pcost(s, ifc, sp)))
        cands.sort()
        best = cands[0]
        why = "ルート パス コストが最小"
        if len(cands) > 1 and cands[1][0][0] == best[0][0]:
            why = ("コストが同じで、送信元のブリッジ ID が小さい" if cands[1][0][1] != best[0][1]
                   else "コストと送信元のブリッジ ID が同じで、送信元のポート ID が小さい")
        detail = "、".join(f"{c[1]}(対向 {c[2]} {c[3]}: {c[4]}+{c[5]}={c[0][0]})" for c in cands)
        L.append(f"- {s}: ルート ポート= {best[1]}({why})。候補 {detail}。")
    for s, ifn in t.blocked():
        n, nif = next((n, ni["name"]) for ifc, n, ni, sp in t.ports(s) if ifc["name"] == ifn)
        L.append(f"- {s} {ifn} は代替: このリンクの指定ポートは {n} {nif}"
                 f"(ルート パス コスト {t.rpc[n]} 対 {t.rpc[s]}"
                 + ("・同点なのでブリッジ ID が小さい側" if t.rpc[n] == t.rpc[s] else "") + ")。")
    return "\n".join(L)


def _note(d, form):
    k = d["kind"]
    if k in FACTS and not (k == "s_guard" and d.get("req")) and not (k == "s_modes" and d.get("dm")) and form != "match":
        return _fact_q(d).get("note", "")
    if k == "s_modes" and d.get("dm"):
        return "既定のモードは版で異なる: 15.2(4)E より前の IOS= PVST+ / 15.2(4)E 以降・Catalyst 9000(IOS XE)= Rapid PVST+[C]。ioll2-xe 17.15 でも既定は Rapid PVST+ だった[M1]。"
    if k == "s_guard":
        return GUARD_REQ[d["rq"]][2]
    if k == "s_tuning" and d["tt"] == "primary":
        r = d["res"]
        return (f"現在のルートの priority は表示 {d['cur'] + d['v']} − VLAN {d['v']} = {d['cur']}。"
                + (f"結果は {r}。" if r is not None else "必要な値が 1 未満なので失敗する。")
                + "実測: 32768→24576・16384→12288・24576(MAC 負け)→20480・4096/0→失敗[M2]。")
    if k == "s_tuning" and d["tt"] == "secondary":
        return "secondary は常に 28672。ほかが全員既定の 32768 の VLAN では、secondary を入れたスイッチがルートになってしまう[M3]。"
    if k == "s_tuning" and d["tt"] == "steer":
        return "port-priority は送信元(上流)側で効く・cost は受信側(自分)のルート ポート選択に効く。stp_model で各肢を計算して判定[M4]。"
    if k in ("s_elect", "s_read"):
        pre = ("この出力は次の盤面から作った(解答者には出力だけを示している)。\n\n" if k == "s_read" else "")
        return pre + explain_board(d["b"], d["t"])
    if k == "s_ts":
        return {"bpduguard": "指紋= Reason bpduguard・`%SPANTREE-2-BLOCK_BPDUGUARD`[M8]。",
                "rootguard": "ルート ガードはポートの全 VLAN に作用する(実機で正当なルートの VLAN も Root Inconsistent)[M9]。",
                "loopguard": "対向の BPDU フィルタで BPDU を止めると約 5 秒で loop-inconsistent・受信再開で即回復[M10]。",
                "pvstsim": "MST と PVST+ の境界で PVST 側に優位なルートがあると `Bound(PVST) *PVST_Inc`・`PVSTSIM_FAIL`(ログの綴りは原文のまま)[M15]。",
                "region": "リージョン不一致の境界は `Bound(RSTP)`(poc/stp 第1回 P4)。",
                "peerstp": "`P2p Peer(STP)` と clear の片側性[M14]。"}[d["sc"]]
    return ""


def answer_body(d, choices, form):
    if form == "match":
        terms, ch, ans = choices
        rows = "\n".join(f"- {t}: {desc}" for t, desc in d.get("_match") or [])
        return "\n".join(["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "", rows, "", CORE[d["kind"]]])
    keys = [k for k, (t, ok, w) in zip(LET, choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip(LET, choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    note = _note(d, form)
    lines += ["", "## 解説", "", (note + "\n\n" if note else "") + CORE[d["kind"]], "",
              "- 根拠の記号: [C]= Cisco 公式 / [J]= 解説サイト / [M]= 実機(poc/stp/README.md 第2回の番号)。照合表= curriculum/U-A3-stp.sources.md"]
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
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "select2": build_choices_select2, "allthat": build_choices_allthat,
                "read": build_choices_read, "cause": build_choices_cause, "fix": build_choices_fix}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = None
                    for k in range(80):
                        try:
                            dd = draw(_r.Random((hash((kind, form, s)) + k * 13) & 0xFFFFFFFF), kind)
                            choices = build_match(dd, rnd) if form == "match" else builders[form](dd, rnd)
                            d = dd
                            break
                        except ValueError:
                            continue
                    assert d is not None, "不成立"
                    if form == "match":
                        terms, ch, ans = choices
                        assert len(ans) == 4 and len(set(ans.values())) == 4
                    else:
                        n_true = sum(1 for x in choices if x[1])
                        if form == "allthat":
                            assert 1 <= n_true <= 4, f"allthat 正解数 {n_true}"
                            assert len(choices) == 5
                        else:
                            assert n_true == (2 if form == "select2" else 1), f"{form} 正解数 {n_true}"
                        texts = [x[0] for x in choices]
                        assert len(set(texts)) == len(texts), "選択肢の重複"
                        assert not any(re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                        assert all(x[1] or x[2] for x in choices), "誤答の理由が空"
                    before, ask, ch_md, _ = question_body(d, choices, form)
                    body = "\n".join([before, ask, ch_md])
                    if kind in ("s_elect", "s_read"):
                        # U4: 1 問の中で方式をそろえる= 表示コストがその方式の値だけ
                        allowed = set(sm.COST[d["b"]["method"]].values()) | set(d["b"]["cost_ovr"].values())
                        if kind == "s_read":
                            for m_ in re.finditer(r"^\S+\s+(?:Root|Desg|Altn)\s+\S+\s+(\d+)\s", before, re.M):
                                assert int(m_.group(1)) in allowed, f"方式混在 {m_.group(1)}"
                    assert "## 正解" in answer_body(d, choices, form)
                    assert "seed" not in body.lower()
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    # 計算器の selftest も通す(盤面の正解は stp_model が出す)
    ng += sm.selftest()
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_stp selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
