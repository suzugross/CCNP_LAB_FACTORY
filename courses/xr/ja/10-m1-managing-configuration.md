# M1 — 設定の管理

M0 で、`commit` するまで何も有効にならないという決まりを見ました。この単元は、その決まりで何が得られるかを扱います。
変更はひとまとまりとして適用され、ひとまとまりとして拒否され、記録され、取り消せます。

掲載した出力は、すべて IOS XRv 9000 のリリース 24.3.1 で採ったものです。

## 1. 2 つのコンフィギュレーション

常に 2 つのコンフィギュレーションがあります。

- **実行コンフィギュレーション**は、ルータがいま動かしている設定です。
- **ターゲット コンフィギュレーション**は、自分の設定セッション専用です。最初は実行コンフィギュレーションの写しで、
  入力した行はターゲットだけを変えます。

`commit` は、2 つの差分を実行コンフィギュレーションに適用します。

コミットの前に状況を確認する表示が 3 つあります。どれもコンフィギュレーション モードで実行します。

| コマンド | 表示するもの |
|---|---|
| `show configuration` | 自分が用意した行だけ |
| `show commit changes diff` | 同じ変更を、実行コンフィギュレーションに対する `+` と `-` の行で |
| `show configuration merge` | コミット後の設定の全体 |

```console
RP/0/RP0/CPU0:XR01(config)#show commit changes diff
!! Building configuration...
!! IOS XR Configuration 24.3.1
-  interface Loopback11
-   ipv4 address 11.11.11.11 255.255.255.255
   !
end
```

## 2. コミットは全か無か

通常の `commit` は、用意した行をすべて適用するか、1 つも適用しないかのどちらかです。
次の例では、BGP のネイバーが未定義のルート ポリシーを参照しており、無関係なループバックと同じコミットに入っています。

```console
RP/0/RP0/CPU0:XR01(config)#commit
% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted.
  Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:XR01(config)#show configuration failed
!! SEMANTIC ERRORS: This configuration was rejected by
!! the system due to semantic errors. The individual
!! errors with each failed configuration command can be
!! found below.
router bgp 65001
 neighbor 10.0.12.2
  address-family ipv4 unicast
   route-policy NOPE in
!!% Could not find entry in list: Policy [NOPE] must be defined before it can be attached.
  !
 !
!
end
```

エラーには 2 種類あります。**構文**エラーは、IOS と同じく Enter を押した時点で検出されます。
**意味上の**エラーは、行の形は正しいが適用できない場合で、コミットの時点で、その部分の設定を受け持つプロセスが
検出します。`show configuration failed` は、拒否された行と、その下に理由を表示します。

コミットが拒否された後の状態は次のとおりです。

- 何も適用されていません。ループバックも入っていません。
- 何も失われていません。`show configuration` には入力した内容がすべて残っています。問題を直して、もう一度コミットします。

別の方法として `commit best-effort` があります。適用できる行をすべて適用し、失敗する行だけを落とします。
意図して使います。誰も全体としては入力していない設定ができあがるからです。

## 3. すべてのコミットが記録される

```console
RP/0/RP0/CPU0:XR01#show configuration commit list
SNo. Label/ID              User      Line                Client      Time Stamp
~~~~ ~~~~~~~~              ~~~~      ~~~~                ~~~~~~      ~~~~~~~~~~
1    undo-first            SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:51 2026
2    second-change         SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:47 2026
3    first-change          SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:45 2026
4    1000000003            ZTP       ZTP                 CLI         Mon Oct 12 13:16:27 2026
5    1000000002            ZTP       ZTP                 CLI         Mon Oct 12 13:16:23 2026
6    1000000001            CVAC      UNKNOWN             CLI         Mon Oct 12 13:16:17 2026
```

コミットには ID が付きます。コミットするときに名前とメモを付けられ(`commit label first-change comment add-lo11`)、
以後はラベルで参照できます。ラベルは一意である必要があり、同じラベルの再利用は拒否されます。

コミットが変更した内容は次のように見ます。

```console
RP/0/RP0/CPU0:XR01#show configuration commit changes first-change
!! Building configuration...
!! IOS XR Configuration 24.3.1
interface Loopback11
 ipv4 address 11.11.11.11 255.255.255.255
!
end
```

`show configuration commit changes last 3` は、直近 3 回分をまとめて表示します。システム ログにも、コミットごとに
ユーザと、その内容を表示するコマンドが記録されます。

これで、おなじみの問いの向きが変わります。IOS で「何が変わったか」を知るには、設定を見比べ、誰かが保存を
残していることを願うしかありません。IOS XR ではルータに聞けば、誰が、いつ、どの回線から、どの行を変えたかが分かります。

## 4. 元に戻す

操作は 2 種類あり、違いが重要です。

**新しい側から、連続したコミットをロールバックする。**

```console
RP/0/RP0/CPU0:XR01#rollback configuration ?
  last        Rollback last <n> commits made
  to          Rollback up to (and including) a specific commit
  to-exclude  Rollback up to (and excluding) a specific commit
```

ルータを以前のある時点に戻します。その時点より後にコミットされたものは、誰のものであっても消えます。

**1 つのコミットだけを取り消し、後のコミットには触れない。** コンフィギュレーション モードで行います。

```console
RP/0/RP0/CPU0:XR01(config)#load rollback changes first-change
Loading.
89 bytes parsed in 1 sec (88)bytes/sec
RP/0/RP0/CPU0:XR01(config)#show configuration
!! Building configuration...
!! IOS XR Configuration 24.3.1
no interface Loopback11
end
RP/0/RP0/CPU0:XR01(config)#commit label undo-first
```

`load rollback changes` はルータを変更しません。そのコミットの**逆**の変更をターゲット コンフィギュレーションに
入れるだけです。入った内容は、他の設定と同じように読み、編集し、コミットできます。
EXEC モードの `show configuration rollback changes <ID>` で事前に確認できます。

ロールバックそのものも、コミットとして記録されます。履歴からは何も消えません。

## 5. 自分で元に戻るコミット

いちばん怖いのは、自分のアクセスを切ってしまうかもしれない変更です。そのために次のコマンドがあります。

```console
RP/0/RP0/CPU0:XR01(config)#commit confirmed 30
```

変更は、仮のものとしてすぐに適用されます。時間内(30〜65535 秒、または `minutes`)に通常の `commit` を実行すると
恒久的になります。実行しなければ、ルータが自分でロールバックし、履歴にそれが残ります。

```console
1    1000000011            SUZUKI    con0_RP0_CPU0       Rollback    Mon Oct 12 13:20:46 2026
2    1000000010            SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:20:12 2026
```

これが役に立つかどうかを分ける点が 2 つあります。どちらもこのリリースで実測したものです。

- **コンフィギュレーション モードに留まる。** モードを抜ける(`end`、`exit`)と、保留中の確認つきコミットは
  その場で取り消されます。ルータはタイマーを待ちません。「確認つきでコミットし、EXEC に戻って試験し、
  戻ってきて確定する」という段取りでは、試験する時点で変更はもう消えています。
- 自動ロールバックの後、ターゲット コンフィギュレーションは空になります。変更はやり直し用には残りません。

## 6. 全体を置き換える

`commit replace` はマージしません。実行コンフィギュレーションをターゲット コンフィギュレーションと同じにします。
つまり、用意しなかったものはすべて削除されます。使う前に、必ず確認します。

```console
RP/0/RP0/CPU0:XR01(config)#hostname REPLACED
RP/0/RP0/CPU0:XR01(config)#show configuration changes
!! Building configuration...
!! IOS XR Configuration 24.3.1
hostname XR01
hostname REPLACED
no username SUZUKI
no vrf MGMT
no interface Loopback0
no interface MgmtEth0/RP0/CPU0/0
no interface GigabitEthernet0/0/0/0
no router ospf 1
no ssh server v2
no ssh server vrf MGMT
end
```

(出力は一部を省いています。)ユーザ アカウント、管理用の VRF とインターフェイス、SSH サーバがすべて一覧に入っています。

## 7. 複数人で作業する

設定セッションはそれぞれ自分のターゲット コンフィギュレーションを持つので、2 人が同時に変更を用意できます。
モードに入るときに、ルータが他のセッションを知らせます。

```console
RP/0/RP0/CPU0:XR01#configure terminal
Current Configuration Session  Line       User     Date                     Lock
00001000-00003a0b-00000000     vty0       SUZUKI   Mon Oct 12 13:21:20 2026
```

自分が編集している間に他の人がコミットすると、自分のコミットは止まって確認を求めます。

```console
One or more commits have occurred from other
configuration sessions since this session started
or since the last commit was made from this session.
You can use the 'show configuration commit changes'
command to browse the changes.
Do you wish to proceed with this commit anyway? [no]:
```

変更の間、他の全員を締め出すには、`configure exclusive` で入ります。
他の人はコンフィギュレーション モードに入って行を用意できますが、コミットは拒否されます。

```console
% Failed to commit .. Another configuration session
had a lock on the running configuration.
```

誰が保持しているかは、`show configuration sessions detail` と `show configuration lock` で分かります。

## 8. 習慣の何が変わるか

| IOS では | IOS XR では |
|---|---|
| 各行がその場で効くので、慎重に入力する | 用意し、`show configuration` で読み、コミットする |
| ブロックを貼り付け、途中の行が通ったことを願う | ブロックは全体が適用されるか、全体が拒否される |
| 危険な変更の前に `reload in 10` | `commit confirmed` |
| 保存した設定を見比べて、変更点を探す | `show configuration commit list`、`show configuration commit changes` |
| 逆のコマンドを打ち直す | `load rollback changes` または `rollback configuration` |
| `configure replace` | `show configuration changes` を見てから `commit replace` |

## 実践

ラボ **XRT-01** に戻り、M1 の課題に取り組みます。先に M0 の課題を終えてください。M1 の一部の課題は LINK1 を使います。

<p class="tolab"><a href="/_learn?id=XRT-01">ワークスペースでラボ XRT-01 を開く</a> — <a href="11-m1-practice.html">課題の一覧</a></p>

:::note
この単元のコミットとロールバックのコマンドは、最初に探すはずの現行の ASR 9000 の System Setup Command Reference には
載っていません(2026 年 10 月に確認。他の巻は調べていません)。ここの説明は、CLI のヘルプと 24.3.1 での実測によるものです。
別のリリースでは、頼る前に挙動を確かめてください。特に 5 節の 2 点です。
:::
