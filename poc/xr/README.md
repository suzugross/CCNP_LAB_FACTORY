# PoC: IOS XR(XRv9000 24.3.1)をラボの構築・採点の流れに載せる(BL-246)

2026-10-12 実施。盤面= `problems/_POC-XR`(XR01 Gi0/0/0/0 ── Et0/0 RT01(IOL))。
生ログ= `provision.log`・`grade1.log`/`grade2.log`・`help.log`・`expB.log`〜`expF.log`。
道具= `xrcon.py`(コンソールからコマンドを流す)・`cmlapi.py`(REST)・`env.sh`(機器ログインを環境変数へ)。

## 1. 基盤(§8 の 1〜5)

| 項目 | 結果 |
|---|---|
| 初期設定の自動投入 | **可**。ただし CML のノード定義 `iosxrv9000` の設定ファイルが `editable: true` であることが前提。`false` だとラボ YAML の `configuration` も API での差し替えも**エラーなしで捨てられ**、定義の既定設定(ユーザ cisco/admin/lab・全 IF shutdown・hostname は仮の文字列)で起動する。当初 `false` だったのをユーザが定義側で直した |
| 投入のされ方 | 起動時に 3 回のコミットとして入る(CVAC 1 回+ZTP 2 回)。`no shutdown` は表示から消える(up が既定の表示)。日本語のコメント行(`!!`)が混ざっていても通る |
| SSH | **可**。ホスト鍵(`the_default`・RSA 2048)は起動時に自動生成。`ssh server v2`+`ssh server vrf MGMT` で管理 IF から入れる |
| 採点経路 | **既存の SSH 経路(`cisco.ios.ios_command`)がそのまま通る**。ただし become(enable)したままだと接続直後に `show privilege` を打って失敗し、その回の出力がエラー文になる → XR ノードは `ansible_become: false`(grade.yml に追加) |
| Genie | **可**。`genie_os: iosxr` で `show ospf neighbor` を構造化できた(`vrfs.*.neighbors.*` の `state`) |
| ラボ指紋 | `alias exec labid …` が XR でも running-config に残る。既存の照合コマンドがそのまま使える |
| 起動時間 | 投入から BOOTED まで **471〜483 秒(約 8 分)**(3 回とも同程度)。採点 1 回は約 10 秒 |
| 貼り付け | コンソールへ 10KB(320 行)を一括で流しても取りこぼしなし(流量制御なし・行間 10ms のどちらも 80/80) |
| IF の並び | slot0 = 管理 IF・slot3 から `Gi0/0/0/0`。slot1〜2 を定義しなくても取り込みは通る |
| IOL との相互接続 | OSPF(point-to-point)で FULL・疎通可 |

## 2. 設定の管理まわりの挙動(§8 の 6)

| 論点 | 実機の挙動 |
|---|---|
| 履歴 | `show configuration commit list`(ラベル/ID・ユーザ・回線・時刻)。`show configuration commit changes <ID か ラベル>`／`last N` で各回の差分。`show configuration history` は出来事の一覧 |
| ラベルとコメント | `commit label <名前> comment <文>`。以後はラベルで参照できる |
| 先の変更だけ取り消す | 設定モードで `load rollback changes <ID か ラベル>` → その 1 回ぶんの逆の変更が編集中の設定に入る → `commit`。後の変更は残る。事前に `show configuration rollback changes <ID>` で中身を見られる |
| まとめて戻す | `rollback configuration last N`／`to <ID>`(その回を含む)／`to-exclude <ID>`(含まない) |
| 確認つきコミット | `commit confirmed <30-65535 秒>`(または `minutes`)。**設定モードに留まったまま**期限が来ると自動で戻る(履歴に Rollback が 1 件増える)。期限内に `commit` で確定 |
| ★確認つきコミットの落とし穴 | **設定モードを抜けると(`end`)その場で取り消される**(4 秒後に Rollback が記録された)。期限切れで戻った後は編集中の設定も空になる |
| 失敗するコミット | 未定義のポリシーを BGP の隣接に付けると `commit` は失敗し、**全部が取り消される**(擬似アトミック)。編集中の設定は残る。原因は `show configuration failed`(「Policy [NOPE] must be defined before it can be attached」) |
| 通るものだけ入れる | `commit best-effort` は誤りのある行だけを落として残りを入れる(Loopback と BGP の隣接は入り、ポリシーの行だけ入らない) |
| 確定前の差分 | `show configuration`(編集中の分)／`show commit changes diff`(+/− の差分)／`show configuration merge`(確定後の全体) |
| 全体の差し替え | `commit replace`(確認を求められる)。入れる前に `show configuration changes` で**消えるもの**が `no …` として見える(管理 IF・ユーザ・SSH も消える) |
| 複数セッション | 他のセッションが編集中だと、`configure` した時点でその一覧が出る。他で確定があった後に自分が `commit` すると「他のセッションで確定があった。続けるか」と聞かれる |
| 排他 | `configure exclusive` 中は、他のセッションは設定モードに入れて編集もできるが `commit` が失敗する(「Another configuration session had a lock」)。`show configuration sessions [detail]`・`show configuration lock` で見える |

## 3. 公式資料との関係

- 現行の ASR 9000 のコマンドリファレンス(System Setup 巻)に `commit`・`rollback`・`load rollback changes` の項目は無い
  (Action Commands／Show Commands の両章を確認)。上の表は実機のヘルプと実測が根拠。
- 旧版の入門ガイド(3.x 系)と解説記事の記述(確認つきコミットは設定モードを抜けると取り消される 等)と実測は一致した。

## 4. 第一弾(XRT-01)を作る過程で追加で分かったこと(同日)

| 論点 | 実機の挙動 |
|---|---|
| SSH の制限 | 既定は `Ratelimit 60`(毎分)・VTY 5 本(vty0〜4)。採点を続けて回すと「Error reading SSH protocol banner」「Failed to authenticate … saw EOF」になる。`ssh server rate-limit 600`(範囲 1〜6000)と `vty-pool default 0 30` で解消 |
| 収集失敗の副作用 | 出力がエラー文になると、`not_regex` だけのチェックが通ってしまう。否定条件は肯定条件と同じチェックに入れる |
| 起動直後の履歴 | 初期設定は CVAC 1 回+ZTP 2 回のコミット。最後の ZTP(`no username ztp-user`)は BOOTED の数秒後に入るので、直後にコミットすると順が混ざる・一時的に失敗する |
| ラベル | 一意。再利用は「the specified label is already assigned to a previous commit」で拒否。失敗したコミットのラベルは消費されない |
| VRF への移動 | アドレスを持つ IF に `vrf X` を入れてコミットすると、**アドレスは残ったまま** VRF に移る(IOS の `vrf forwarding` と逆) |
| ネットワーク種別の不一致 | XR(broadcast)と IOL(point-to-point)で隣接は FULL(XR 側は FULL/DR)になるが、そのリンク経由のルートは入らない |
| `include` の正規表現 | `| include a|b` は不可(2 つ目の `|` が次の絞り込みと解釈される)。`| include "a|b"` |
| `show ip …` | `show ip interface brief`・`show ip route` は通る。CLI の説明は `ip  Deprecated, use ipv4 instead` |
| パイプ | `begin`・`exclude`・`include`・`file`・`utility`(cut/egrep/fgrep/head/less/more/sort/tail/uniq/wc ほか)・`json`・`xml` |
| `end` | 未コミットの行があると `Uncommitted changes found, commit them before exiting(yes/no/cancel)? [cancel]:` |
| eBGP とポリシー | 着信ポリシーだけだと `show bgp summary` がネイバーに `!` を付け、「both inbound and outbound policies」が無いと送受信しない旨を表示 |
| IOL → XR の SSH | `ssh -l <user> 10.0.12.1` は「Connection … aborted: error status 0」で不可。Telnet(`telnet vrf default ipv4 server max-servers 5`)は可 |
| 起動時間 | XRT-01 の provision 全体(構築→起動→履歴の仕込み)で 約 9.5 分 |
