# ACL 単独読解 紙面ファミリ (BL-106) — P0 実測表

設計メモ= [ACL-PAPER.design.md](../../problems/_drafts/ACL-PAPER.design.md) §8。
生ログ= [results-raw.md](results-raw.md)。駆動= [sweep.py](sweep.py)（`sweep.py <チェック名...>`）。

## 環境

- CML ラボ **POC-ACL**（`iol-xe` × 3・コンソール直駆動・mgmt/SSH は使わない）
- 測定日 2026-08-10

```
    RT03 --e0/0---e0/0-- RT01 --e0/1---e0/0-- RT02
         10.0.13.0/24    (DUT)  10.0.12.0/24
```

| ノード | 役割 | 広告するもの |
|---|---|---|
| RT01 | 被験体（ACL を着せ替える） | Lo0 1.1.1.1/32 |
| RT02 | 経路の出し手 | Lo0 2.2.2.2/32・**172.30.16.0/24**・172.30.17.0/26・172.30.18.0/30・172.30.32.0/24 |
| RT03 | トラフィックの出し手 | Lo0 3.3.3.3/32・**172.30.16.0/28**（★RT02 の /24 と**同じネットワークアドレスで長さだけ違う**）・Lo99 203.0.113.5/32（EIGRP 非広告＝uRPF の偽装元） |

EIGRP 100（classic・`no auto-summary`）。RT01 が学ぶ 7 本を基線とする。

---

## ★測定の作法（踏んだ罠・次回もここで転ぶ）

1. **`dev.configure([1行])` を行ごとに呼ぶと config の階層が壊れる**。
   `ip access-list extended X` の次の `permit ...`、`router eigrp` の次の
   `distribute-list ...` が**グローバル config で実行され** `% Invalid input` になる。
   → これを額面どおり読むと「**拡張 ACL は distribute-list に使えない**」という
   **偽の結論**が出る（実際に一度出しかけた）。階層を保ったまま行ごとに応答を
   帰属させる `conf_trace()` を使うこと。
2. **`show ip route` の固定長ブロックは経路行にプレフィックス長が付かない**
   （`1.0.0.0/32 is subnetted` 配下は `D  2.2.2.2 [90/...]`）。長さは直前の見出し行から採る。
   これを取り違えると基線が永久に揃わない。
3. **「1台を見て全台 skip」する冪等判定は危険**。中断した前回実行で RT01 だけ
   設定済みだと、RT02/RT03 が素のままなのに「設定済み」と誤認する。base は毎回全台に流す。
4. **前回の測定が残した ACL が seq 衝突を起こす**（`% Duplicate sequence number` →
   `% Failed to add ace`）。チェックの冒頭で対象 ACL を明示的に消す。
   異常終了すると後片付けが走らないので、次のチェックが汚染される。
5. **時計を動かす測定（time-range）は戻す**。戻し忘れると以後の
   syslog のタイムスタンプが未来日付になる（実際 `Aug 15` のログが残った）。

---

## 1. ★未定義 ACL を参照したときの帰結（ロールごとに違う）

「参照先の ACL が存在しない」ときの挙動は**ロールによって割れる**。対照実験つきで確定。

| ロール | 適用 | 結果 | 根拠 |
|---|---|---|---|
| **interface** | `ip access-group NOEXIST-A in` | **全許可**（通過率 100%） | ARP を温めた基準 100% と同値。★`show ip access-lists NOEXIST-A` は**空**＝参照しても ACL は作られない。ただし `show ip interface` には `Inbound  access list is NOEXIST-A` と**名前だけ表示される** |
| **distribute-list** | `distribute-list NOEXIST-D in` | **全許可**（7/7 経路が残存） | 同じ手順で標準 ACL を使うと実際に絞れる（§3）ので、機構が効いていないのではない |
| **uRPF 例外** | `ip verify unicast source reachable-via rx 178` | **全免除** | 経路の無い 203.0.113.5 発を5発 → `0 verification drops` / **`5 suppressed verification drops`**＝RPF は失敗しているが ACL 許可扱いで見逃されている |
| **CoPP** | `class-map match-all` の `match access-group name NOEXIST-C` | **どれにも一致しない → class-default 行き** | 未定義: CM 側 **0 packets** / class-default **12 packets**。対照（定義済み `permit icmp any any`）: CM 側 **10 packets** ＝観測方法は正しい |
| **NAT** | `ip nat inside source list NOEXIST-N ...` | **変換されない**（`show ip nat translations` が空） | 対照（`access-list 60 permit 3.3.3.3`）では `icmp 10.0.12.1:1024  3.3.3.3:17 ...` が立つ |

★**リポの「未定義参照」類型コレクションに ACL 版が加わった**:
prefix-list 未定義=**全許可** / route-map 未定義=**全拒否** / AAA method list 未定義=**default へ落ちる** /
**ACL 未定義= ロール依存（フィルタ系は全許可・分類系は不一致）**。

## 2. 空の ACL

- **空の named ACL を interface に適用 → 通過率 100%**（`ip access-list extended EMPTYT` を作って中身なし）。
- **空の named 標準 ACL を distribute-list に適用 → 7/7 経路が残存**。

★ つまり**「空＝暗黙 deny だけが残って全断」ではなく、未定義と同じく全許可**。
設計メモの論点27（空＝全断）は**誤りだったので訂正済み**。

## 3. 標準 ACL はプレフィックス長を区別しない

`access-list 20 deny 172.30.16.0` ＋ `permit any` を `distribute-list 20 in`:

- **172.30.16.0/24 も 172.30.16.0/28 も両方消えた**（残ったのは /26・/30・/32 と 172.30.32.0/24）。
- カウンタ= `10 deny 172.30.16.0 (6 matches)` / `20 permit any (5 matches)`。

→ 要件世界 `prefixlen_exact`（長さを厳密に区別せよ）の正解が
**「ACL では表現できない・prefix-list が要る」**になる盤面を作れる（根拠が取れた）。

## 4. ★★拡張 ACL × distribute-list の意味論（定説と違う）

教科書的には「拡張 ACL を distribute-list に使うと **src=ネットワーク・dst=サブネットマスク**」
と説明される。**この機種の EIGRP では成り立たない**。5段階の切り分けで確定した。

### 4-1. 名前付き拡張 ACL は使えない

```
router eigrp 100
 distribute-list DLX in
% The ACL cannot be created or an ACL with the same name but incompatible type already exists.
```

`show ip protocols` は `Incoming update filter list for all interfaces is not set` のまま
＝**コマンドごと拒否されて適用されない**（ACL 自体は正しく作れている）。
IOS は distribute-list の名前を**標準 ACL として作ろうとする**ため、同名の拡張 ACL と衝突する。
→ 番号付き（100〜199）なら受理され、`Incoming update filter list ... is 130` と表示される。

★★**ただしこれは投入の順序に依存する**（C3・2026-08-11 追測）。
**先に `distribute-list NAMEDEXT in` を入れてから、後で
`ip access-list extended NAMEDEXT` を定義すると受理される**:
`Incoming update filter list ... is NAMEDEXT` と表示され、
`permit ip host 10.0.12.2 any` が **7 matches** で機能し、その隣接発の5本だけが残った
（＝**直接指定の意味論**で動く）。
→ 「名前付き拡張は使えない」ではなく「**定義してから参照すると拒否される**」が正確。

### 4-2. src と dst が指すもの（番号付き拡張 ACL）

RT02 発= 2.2.2.2/32・172.30.16.0/24・172.30.17.0/26・172.30.18.0/30・172.30.32.0/24（5本）／
RT03 発= 3.3.3.3/32・172.30.16.0/28（2本）。

| # | ACE | 残存 | カウンタ | 読み取れること |
|---|---|---|---|---|
| E1 | `permit ip any any` | **7/7** | 7 matches | **経路 1本につき 1 回評価**されている（機構は動いている） |
| E2 | `permit ip host 172.30.17.0 any` | **0/7** | 0 | src は**ネットワークではない** |
| E3 | `permit ip host 10.0.12.2 any` | **5/7**（RT02 発と一致） | 7 matches | ★**src = 経路を広告してきた隣接ルータ** |
| E4 | `permit ip host 172.30.17.0 host 255.255.255.192` | **0/7** | 0 | ★**定説の「src=網・dst=マスク」は不成立** |
| E5 | `permit ip 172.30.0.0 0.0.255.255 any` | 0/7 | 0 | 同上 |
| F1 | `permit ip any host 172.30.17.0` | **1/7**（/26 のみ） | 1 match | ★**dst = 広告されたネットワークアドレス** |
| F2 | `permit ip host 10.0.12.2 host 172.30.17.0` | 1/7 | 1 match | src と dst の**両掛けができる** |
| F3 | `permit ip any 172.30.16.0 0.0.15.255` | **4/7** | 4 matches | dst にワイルドカードが効く（16〜31 の4本） |
| F4 | `permit ip any host 172.30.16.0` | **2/7**（/24 と /28 の両方） | 2 matches | ★**拡張 ACL でもプレフィックス長は区別できない** |

### 4-3. 結論

- **src = 広告元の隣接ルータ / dst = 広告されたネットワークアドレス**（マスクは見ない）。
- **標準 ACL でも拡張 ACL でもプレフィックス長は区別できない**（§3 の /24・/28 と F4 が同じ結論）。
  → 要件世界 `prefixlen_exact` の正解が **「ACL では不可能・prefix-list が要る」**で確定。
  しかも「標準では無理だが拡張なら…」という**もっともらしい誤答**が作れる（F4 が反証）。
- 「どの隣接から来た経路か」で絞れるのは**拡張 ACL だけの能力**＝ src 側に意味がある。
  標準 ACL（§3）との対比が、そのまま1問になる。

### 4-4. ★★参照の経路で意味論が切り替わる（C1・2026-08-11）

§4-2 は **`distribute-list <番号> in` の直接指定**での話。
**ルート・マップ経由**（`distribute-list route-map <名前> in` ＋ `match ip address <番号>`）
では、**まったく別の意味論**になる。

| ACE（route-map 経由で参照） | 残存 | 読み取れること |
|---|---|---|
| C1a `permit ip any any`（対照） | **7/7** | 機構は動作している |
| C1b `permit ip host 172.30.17.0 host 255.255.255.192` | **1/7**（/26 のみ） | ★**教科書の「src=網・dst=マスク」がそのまま成立** |
| C1c `permit ip host 10.0.12.2 any`（src=広告元 の読み） | **0/7** | ★route-map 経由には**「広告元」の概念が無い** |
| C1d `permit ip any host 255.255.255.0` | **2/7**（/24 の2本のみ） | ★★**プレフィックス長で絞れる** |
| C1e `permit ip any host 172.30.17.0`（dst=網 の読み） | **0/7** | dst は網ではない |

### 4-5. 結論（両方が正しい）

| 参照の経路 | src | dst | 長さで絞れるか |
|---|---|---|---|
| **直接指定** `distribute-list <番号> in` | **広告元の隣接ルータ**（route source） | **広告されたネットワーク** | **不可** |
| **route-map 経由** `distribute-list route-map <名前> in` | **ネットワーク** | **サブネット・マスク** | **可能** |

★ 教科書の「src=網・dst=マスク」は**間違いではなく、route-map 経由の話**だった。
同じアクセス・リストでも、**どちらから参照されるかで意味が入れ替わる**。

★★ したがって**長さを区別する手段は prefix-list だけではない**。
紙面 shape=acl の要件世界は、この2手段を**「どちらを禁じるか」で反転させる**形に改めた
（`prefixlen_no_rm`= ルート・マップ禁止→prefix-list が正解 /
`prefixlen_via_rm`= プレフィックス・リスト禁止→route-map 経由の拡張 ACL が正解）。

★ 補足= 「広告元」は**直接ルーティング アップデートを送ってきた隣接**であり、
その経路を最初に発信したルータではない。多段構成で「発信元ルータ」を指定する意図で
書くと一致しない。

★ 経緯= この整理は**ユーザから提供された外部レポート2件（Claude / Gemini）を仮説として
受け取り、本ラボで検証して確定**させたもの。
当初は「教科書は不成立」とだけ記録していたが、**参照経路という条件を見落としていた**。

## 5. ★outbound ACL は自機生成トラフィックにも効く（定説と違う）

`ip access-list extended OUTT`（`10 deny icmp any any` / `20 permit ip any any`）を
RT01 の e0/1 に **out** で適用し、5発ずつ撃ってカウンタで帰属させた。

| 送信元 | 通過率 | deny 行のカウンタ |
|---|---|---|
| 適用直後（基点） | — | 0 |
| **RT01 自身 → 10.0.12.2**（直結・既定送信元） | **0%** | 0 → **5** |
| **RT01 自身 → 2.2.2.2**（Lo0 発・1ホップ先） | **0%** | 5 → **10** |
| RT03 → 10.0.12.2（RT01 を通過） | 0% | 10 → **15** |

★ 5発ごとにきっちり 5 ずつ増えており、**自機生成パケットも outbound ACL に当たっている**。

### 5-b. 対照つきの再検証（A1・2026-08-10）

ND の件で「観測が対象を捉えていない」失敗をしたため、**宛先で当たり外れが分かれる ACL**
（`10 deny icmp any host 2.2.2.2` / `20 permit ip any any`）で対照つきに測り直した。

| # | 条件 | 通過率 | deny / permit カウンタ |
|---|---|---|---|
| (i) | **自機生成 × deny に一致**（RT01→2.2.2.2） | **0%** | deny 0→**5** |
| (ii) | 対照= **自機生成 × deny に不一致**（RT01→10.0.12.2） | **100%** | permit +4（**評価はされている**） |
| (iii) | 対照= 転送 × deny に一致（RT03→2.2.2.2） | 0% | deny 5→**10** |

★ **(ii) が決め手**。RT01 自身のトラフィックは ACL を**通過して評価されており**
（permit 行のカウンタが進む）、deny に一致したときだけ落ちている。
= 「自機生成だから素通り」ではない。
→ 「outbound ACL は router 自身が出すトラフィックには適用されない」という一般的な説明は
**この機種（IOL-XE 17.15）では成り立たない**（対照つきで確定）。
→ 設計メモの論点20 は**削除**（この挙動に依存した設問は作れない）。
※ 一般に流布する説明との食い違いの理由は未解明。**紙面はこの実測に従う**。

## 6. 編集規則（seq・resequence・カウンタ）

| 操作 | 結果 |
|---|---|
| named ACL に `15 deny udp any any eq 9999` を**挿入** | 位置は 10 と 20 の間。**他の行のカウンタは保持**（`10 ... (5 matches)` のまま） |
| `ip access-list resequence SEQT 100 100` | 10/15/20/30 → 100/200/300/400。**カウンタは保持** |
| `no ip access-list extended SEQT` → 作り直し | **カウンタは消える**（0 から） |
| `access-list 150 permit ...` を3回 | **末尾に 10/20/30 と付く**（置換ではない） |
| ★`ip access-list extended 150` に入って `15 permit tcp any any eq 22` | **受理され 10 と 20 の間に入る** |

★ 最後の1行が重要: **「番号付き ACL は末尾にしか追記できない」は誤り**。
差は「番号付き/名前付き」ではなく**編集モード**（`access-list ...` のグローバル形式か、
`ip access-list ...` の named モードか）。設計メモの論点10 は訂正済み。
→ 要件世界 `no_delete` は「既存行を消さずに挿入せよ」として**両形式で成立する**が、
正解を named に寄せる仕掛けとしては使えない。

## 7. time-range

`time-range WORKHOURS` / `periodic weekdays 09:00 to 17:00` を
`10 deny icmp any any time-range WORKHOURS` で参照。

| 時計 | time-range | ICMP 通過率 |
|---|---|---|
| 月曜 10:00 | `(active)` | **0%**（deny が効く） |
| 月曜 18:30 | `(inactive)` | **100%** |
| 土曜 10:00 | `(inactive)` | **100%** |

★ **`show ip access-lists` が ACE 行に状態を書く**:
`10 deny icmp any any time-range WORKHOURS (active) (3 matches)`。
`show time-range` も `time-range entry: WORKHOURS (active)`。
→ read 形の材料になる反面、**状態が丸見えなので道標にもなる**。出す/出さないの設計が要る。

## 8. ★CoPP の deny ACE は class-default 行き

`CP-ICMP`= `10 deny icmp host 10.0.13.3 any` / `20 permit icmp any any`、
`CM-ICMP`= `match access-group name CP-ICMP`、class-default にも police を置いて計上先を見た。

- RT03(10.0.13.3) から 10発 → **deny 行に 10 matches**、**class-default に計上**
- RT02 から 10発 → permit 行に 10 matches、**CM-ICMP に conformed 10 packets**
- class-default は 12 packets（上記10発＋EIGRP 等の2発）

→ **deny は「通す」ではなく「このクラスに入れない」**。class-default の police/drop に
巻き込まれる、という QoS シリーズの教訓の ACL 版が成立する。

## 9. ACL ログの書式

| 種別 | 実測の1行 |
|---|---|
| TCP | `Aug 15 10:07:42.465: %SEC-6-IPACCESSLOGP: list LOGT denied tcp 10.0.13.3(19314) -> 10.0.12.2(22), 1 packet` |
| ICMP | `Aug 15 10:15:45.764: %SEC-6-IPACCESSLOGDP: list LOG3 denied icmp 10.0.13.3 -> 10.0.12.2 (8/0), 1 packet` |

★ **ニモニックが違う**（TCP/UDP= `IPACCESSLOGP`、ICMP= `IPACCESSLOGDP`）。
ICMP は `(8/0)`＝type/code が付き、ポートは付かない。

★★ **`log` の無い行で落ちた場合は記録が出ない**:
`10 deny icmp any any echo`（log なし）で3発落として **カウンタは 3 matches・SEC-6 は 0 行**。
→ logread 形で「ログに出ていない＝別の行で落ちた」という**消去推論**が成立する。

## 10. ワイルドカードにサブネットマスクを書いた場合

3本とも**エラーなく受理される**。しかし表示を見ると**別物になっている**。

| 投入した行 | `show ip access-lists` の表示 |
|---|---|
| `access-list 90 permit 10.0.0.0 255.0.0.0` | `permit 0.0.0.0, wildcard bits 255.0.0.0` |
| `access-list 91 permit 192.168.1.0 255.255.255.0` | `permit 0.0.0.0, wildcard bits 255.255.255.0` |
| `access-list 92 permit 10.0.0.0 0.255.255.255` | `permit 10.0.0.0, wildcard bits 0.255.255.255` |

★ **don't care 側のビットがアドレスから落とされる**ため、
`10.0.0.0 255.0.0.0` は「10.x.x.x」ではなく **「第2〜4オクテットが 0.0.0 の全アドレス」**
になる（第1オクテットが自由）。錯乱肢として一級品。
`topologies/acl_cover.py` の `Cube` は同じ正規化（`value &= care`）を実装済みで、実機と一致する。

★ 補足: **numbered ACL も running-config には named 形式で入る**
（`show running-config | include access-list 9` は**空**）。read 形で running-config を
見せるときは `ip access-list standard 90` 形式で描くこと。

## 11. `show ip access-lists` の表示書式（read 形の忠実性）

投入した DISPT に対する実出力:

```
Extended IP access list DISPT
    10 permit tcp 10.0.13.0 0.0.0.255 any eq 22
    20 permit tcp any host 172.30.16.1 eq www log
    30 permit udp any any range 16384 32767
    40 permit icmp any any echo-reply
    50 deny tcp any any established
    60 permit ip 10.0.0.0 0.0.1.255 any
```

- **remark は `show ip access-lists` に出ない**（running-config には出る）。
- ポート番号は **22 は数字のまま・80 は `www`** に化ける（`acl_model.PORT_NAMES` の想定どおり）。
- `range` は数字、ICMP は `echo-reply` の名前、`established` はそのまま。
- ★ running-config では **remark が直後の ACE と同じ seq 番号（10）を持つ**。

---

## 12. 紙面設計への含意（設計メモの改訂点）

| 設計メモ | 実測を受けて |
|---|---|
| 論点20「outbound は自機生成に効かない」 | **削除**（§5・逆だった） |
| 論点27「空 ACL = 全断」 | **訂正**（§2・全許可） |
| 論点10「番号付きは末尾のみ」 | **訂正**（§6・編集モードの差） |
| 論点5「WC とサブネットマスクの取り違え」 | **強化**（§10・アドレスが正規化されて別物になる、まで踏み込める） |
| 論点26「未定義参照はロールで違う」 | **確定**（§1・フィルタ系=全許可／分類系=不一致） |
| §2 routefilter「拡張 ACL は src=網・dst=マスク」 | **全面訂正**（§4・実際は src=広告元ルータ／dst=広告された網。名前付き拡張は使用不可） |
| 要件世界 `prefixlen_exact` | **根拠確定**（§3 と §4-2 F4・標準でも拡張でも長さは区別できない → prefix-list が唯一解） |

## 13. ★「フィルタが実質不在」3種は出力で区別できる（P15・2026-08-10 追測）

§1・§2 で「未定義」「空」「名前付き拡張」がいずれも**全部素通り**になると分かったが、
紙面の evidence 形（「次に取得すべき出力はどれか」）を作るには
**この3つが出力で区別できるのか**を確定する必要があった。
特に未検証だったのは「**未定義の名前を参照したら IOS が空の ACL を自動生成するのか**」。
生成されるなら「未定義」と「空」は同一になり、仮説として並立しない。

| 仮説 | `show ip access-lists` | `show run \| inc distribute-list` | `show ip protocols` |
|---|---|---|---|
| **未定義**（名前・番号とも） | **何も出ない**（★自動生成されない） | `distribute-list <ID> in` が残る | `... is <ID>` |
| **空**（ヘッダのみ） | `Standard IP access list <NAME>` | `distribute-list <NAME> in` が残る | `... is <NAME>` |
| **名前付き拡張** | `Extended IP access list <NAME>` ＋エントリ | **何も出ない**（コマンドごと拒否） | `... is not set` |

★ **未定義参照でも ACL は自動生成されない**ことを確認（これが分岐点だった）。
→ 3つは `show ip access-lists` だけで**3通りに割れる**。
`show running-config` と `show ip protocols` は**2通りまで**（名前付き拡張だけが分離する）。
`show ip route` は3つとも同じ＝**割れない**。

→ evidence 形が成立する。ただし**3仮説の識別子（番号/名前）を揃える**こと。
揃えないと `show running-config` の見え方だけで割れてしまい、「最良の出力」が一意にならない。

## 14. IPv6 traffic-filter（P3 用・V系・2026-08-10）

同じ POC-ACL 上に IPv6 を載せて測定（`sweep.py V1_ipv6_basics V2_implicit_nd
V3_undef_empty V4_seq V6_empty_persist`）。**IPv4 との差分**が紙面の主題になる。

### 14-1. 書式と表記

```
RT01# show ipv6 access-list V6T
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```
```
RT01# show running-config | section ipv6 access-list
ipv6 access-list V6T
 sequence 10 permit tcp 2001:DB8:13::/64 any eq 22
 sequence 20 permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2
```

- ★**`sequence` の位置が show と running-config で逆**（show=行末／config=行頭）。
  read 形で書式を再現するときは必ず出し分けること。
- ★**ワイルドカード表記は拒否される**（`permit ipv6 2001:DB8:13::/64 0.0.0.255 any`
  → `% Invalid input detected`）。IPv4 の癖がそのまま**構文エラー**になる。
- **暗黙のエントリは `show` に一切現れない**（IPv4 の暗黙 deny と同じく不可視）。
- ポート番号は表示で名前化される（`eq 23` → **`eq telnet`**）。

### 14-2. ★★明示 `deny ipv6 any any` を書くと近隣探索が落ちる（定説どおり・V7 で確定）

**先に誤った測定をしたので、その失敗も記録する（§14-2b）。** 正しい測定は以下。

★**指標は ping の成否ではなく `show ipv6 neighbors` の state**。
下の3ケースは ping がすべて 0%（ICMP echo 自体を許可していないため）で、
差は**隣接が解決できているかどうか**にしか出ない。

ACL は `permit ipv6 host 2001:DB8:3::3 any`（**遠端の Loopback だけ**。
オンリンクの `2001:DB8:13::/64` は意図的に許可しない）を土台にし、
`ipv6 traffic-filter V6ND2 in` を e0/0 に適用。各ケースで `clear ipv6 neighbors` 後に測定。

| 構成 | `show ipv6 neighbors 2001:DB8:13::3` | ACL のカウンタ |
|---|---|---|
| (a) 暗黙の拒否のみ | **REACH**（`aabb.cc02.4f00`） | — |
| (b) 末尾に `deny ipv6 any any` | ★**INCMP**（Link-layer Addr が `-`＝**解決できていない**） | `deny ipv6 any any (15 matches)` |
| (c) `permit icmp any any nd-ns` / `nd-na` を明示 deny の手前に追加 | **REACH** | `nd-ns (1 match)` / `nd-na (1 match)` / `deny (5 matches)` |

★ **(b) で隣接が壊れ、(c) で回復する**。(c) の `nd-ns` / `nd-na` にそれぞれ 1 match が
付いていることが機序の直接証拠。
→ 「**IPv6 ACL の末尾には暗黙で `permit icmp any any nd-na` / `nd-ns` があり、
明示的に `deny ipv6 any any` を書くとその暗黙の許可が失われて近隣探索ごと落ちる**」
という定説は、**この機種でもそのとおり**に再現する。

→ 紙面の**最大の考えさせポイント**として使える（実際に試験対策教材でも定番の論点）。

### 14-2b. ★測定の失敗（同じ轍を踏まないために）

最初の測定（V2）は「明示 deny を書いても隣接は壊れない」という**誤った結論**を出した。
原因は2つで、どちらも**測定の設計ミス**である。

1. ★**ACL の先頭に `permit ipv6 2001:DB8:13::/64 any` を置いたまま、
   RT01 から RT03 の“オンリンクのグローバルアドレス” `2001:DB8:13::3` を ping していた**。
   グローバルアドレスを解決するときの **NA の送信元は解決対象のアドレスそのもの**なので、
   NA はこの permit に一致して通っていた。
   = 「暗黙の ND 許可で通った」のではなく「**自分で書いた permit で通していた**」だけ。
   → 近隣探索の可否を見るなら、**オンリンクのプレフィックスを一切 permit しない**こと。
2. ★**判定を ping の成否で行っていた**。正しい指標は `show ipv6 neighbors` の
   **REACH / INCMP**。ICMP echo を許可していない盤面では ping はどのみち 0% になり、
   隣接の生死は ping からは読み取れない。
   （V2 では deny 行のカウンタが Loopback 発の 5 発とちょうど一致していた＝
   **NA が deny 行に当たっていない**という傍証が出ていたのに、読み落としていた。）

**教訓**= 「効いていないように見える」ときは、**その観測が本当に対象を捉えているか**を
カウンタの内訳で必ず裏取りする。

### 14-3. 未定義・空

| 構成 | 通過率 | `show ipv6 access-list` | `show ipv6 interface` |
|---|---|---|---|
| 未定義（`ipv6 traffic-filter NOSUCH6 in`） | **100%** | 現れない | `Inbound access list NOSUCH6` |
| 空（`ipv6 access-list EMPTY6` のみ） | **100%** | **現れない** | `Inbound access list EMPTY6` |

- IPv4 と同じく**未定義も空も全許可**。
- ★★**IPv4 と違い、空の IPv6 ACL はそもそも保持されない**（V6 で確認）。
  `ipv6 access-list EMPTY6B` をエントリ無しで作っても、
  `show ipv6 access-list`（引数なし）にも **`show ipv6 access-list EMPTY6B`（名指し）にも
  running-config にも現れない**。IPv4 は空でも `Standard IP access list <NAME>` の
  ヘッダが出たので、ここは明確な差分。
  → **IPv6 では「未定義」と「空」は同一の状態**であり、別々の仮説として立てられない。
  IPv4 で作れた evidence 形（未定義／空／名前付き拡張の3仮説を切り分ける形）は
  **v6 には移植できない**。

### 14-4. sequence とカウンタ

| 操作 | 結果 |
|---|---|
| `sequence 20 deny tcp any any eq 23` を挿入 | 10 と 30 の間に入る。**他行のカウンタは保持** |
| ★`ipv6 access-list resequence V6SEQ 100 100` | **`% Invalid input`＝コマンドが無い** |

★ IPv4 には `ip access-list resequence` があるが、**IPv6 には無い**。
要件世界「既存行を消さずに詰め直す」は IPv6 では成立しない。

### 14-5. 紙面（shape=aclv6）に使える差分の要約

| # | IPv4 | IPv6 |
|---|---|---|
| 1 | ワイルドカード・マスク | **プレフィックス長**（ワイルドカードは構文エラー） |
| 2 | `ip access-group` | **`ipv6 traffic-filter`** |
| 3 | show は seq が行頭 | **show は行末・config は行頭** |
| 4 | `resequence` あり | **無い** |
| 5 | 空のリストはヘッダが出る | **そもそも保持されない**（未定義と同一の状態） |
| 6 | — | ★**明示 `deny ipv6 any any` で近隣探索が落ちる**（暗黙の `nd-na`/`nd-ns` 許可が失われる。`permit icmp any any nd-ns`/`nd-na` を手前に置けば回復） |

## 15. 他分野の「定説と違う」主張の監査（A系・2026-08-10）

ND の件（§14-2b）を受けて、**リポ全体で「定説と違う」と記録されている主張**のうち
**問題が依存しているもの**を洗い出し、危ういものを本ラボで測り直した。

### 15-1. ★★片側だけ `update-source` を外してもセッションは UP（A2）

iBGP・Loopback ピア（RT01 Lo0 1.1.1.1 ⇄ RT02 Lo0 2.2.2.2・AS 65000）。

| 構成 | RT01 の状態 | RT02 の状態 |
|---|---|---|
| (a) 両側に `update-source Loopback0` | **Established** | **Established** |
| (b) ★**RT02 側だけ外す** | **Established のまま** | **Established のまま** |
| (c) 対照= **両側とも外す** | **Idle** | **Idle** |

★ (c) が Idle になることで、この測定が対象を捉えていることも裏取りできている。
機序= 片側が残っていれば、その側が開いた接続（送信元＝Lo）が相手の `neighbor <Lo>` に
一致して受理される（接続レース）。poc/bgpdbg 発見1 と一致。

★★**影響**= `topologies/gen_bgp_complex_ts.py` の症状シミュレータ `sim_missing()` は
`no_upd_src` を**片側でもセッション断**として扱っており、**実機と食い違う**。
詳細と対処案は BACKLOG の BL-061 を参照。

### 15-2. 監査した主張の一覧

| 主張 | 問題が依存 | 検証 | 判定 |
|---|---|---|---|
| 拡張ACL×distribute-list は src=広告元/dst=網 | ★あり（shape=acl の fix 形） | 5パスで1フィールドずつ＋カウンタで評価回数を確認 | 妥当 |
| outbound ACL は自機生成に効く | なし（論点削除済） | **A1 で対照つき再検証** | 妥当 |
| 片側 update-source 欠けでも UP | ★あり（bgpdbg の `asym_up`） | debug ログの**直接転写**＋**A2 で対照つき確認** | 妥当 |
| 同上 → gen_bgp_complex_ts の症状予測 | ★あり（GEN-BGPCX のチケット文） | **A2 で食い違いを確定** | ★**要修正（BL-061）** |
| ABR の distribute-list in は Type-3 生成ごと止める | ★あり（shape=ospfv3pl の `dl_abr`） | モデル⇔実機を5ケース突き合わせ全一致 | 妥当 |
| IOL は synchronization を受理 | あり（ENARSI-BGP-SYNC-01） | 実機フルサイクル（broken 10→100） | 妥当 |
| forward-protocol では DHCP リレーは止まらない | あり（ENCOR-DHCP-01 / gen_dhcp_ts） | 全8故障で broken→fix→100 | 妥当 |

★**判定の分かれ目**= 「**その観測が対象を捉えているか**を対照で確認しているか」。
実機フルサイクル（broken→fix→100）とモデル⇔実機の突き合わせは、
それ自体が対照になるので強い。単一の proxy 指標（ping の成否など）だけのものが危ない。

## 16. ★★適用点（G系・2026-08-11・BL-109）

紙面 shape=acl は「ACL の**中身**」だけを主題にしており、`ip access-group` 行は
常に正しく・常に `in` で描かれていた（＝読む価値の無い装飾）。
**適用点そのものを主題にする**ために、対照つきで測った。

### 16-1. 適用点はどの show に出るか（★現行紙面の不忠実を1件発見）

★ 現行紙面の `show run | section access-list|access-group|distribute-list|...` は
**適用行だけ**を描いているが、実機は同じ正規表現で **ACL 本体も出す**
（`access-list` が `ip access-list extended 150` に一致するため）。実出力:

```
 ip access-group 150 in
ip access-list extended 150
 10 permit ip any any
```

★★ **番号付き ACL も running-config では named 形式で表示される**。
`access-list 150 permit ip any any` と入れても `ip access-list extended 150` ＋
` 10 permit ip any any` になる（`show ip access-lists` の書式とは別物）。

| 出力 | 適用点の見え方 | 紙面向き |
|---|---|---|
| `show run \| section access-list\|access-group` | **IF 名が出ない**＋ACL 本体が付いてくる | × |
| `show run \| section ^interface` | 全 IF ブロック（**IOL は 32 本**出る） | × 長すぎ |
| **`show run interface Ethernet0/0`** | IF ブロック単体・適用点が読める | **◎** |
| **`show ip interface Ethernet0/0 \| include access list`** | Inbound / Outgoing を明示 | **◎** |
| `show ip interface \| include line protocol\|access list` | 全 IF（32本） | △ |

`show ip interface` の実書式（IOS-XE 17.15 は **Common access list の行が挟まる**）:

```
  Outgoing Common access list is not set
  Outgoing access list is not set
  Inbound  Common access list is not set
  Inbound  access list is 150
```

（`Inbound  access list` は**空白2つ**。行末に空白が付く行がある。
なお本 README 上では先頭行の字下げが `block()` の `.strip()` で落ちている
＝実機では 2 字下がる。）

→ **紙面の 設定抜粋は `show run interface <IF>` を IF ごとに出す形へ変える**。

### 16-2. ★入口 in と出口 out は二段で評価される

e0/0 in に `permit ip any any`、e0/1 out に `deny icmp any any` ＋ `permit ip any any`。

| 構成 | RT03→RT02 | 入口 permit | 出口 deny |
|---|---|---|---|
| 両方 permit | 100% | +5 | — |
| ★出口だけ deny icmp | **0%** | **+5（進む）** | **+5** |

★ 入口で**許可された**パケットが出口で落ちている＝**両方で評価される**。

### 16-3. ★同一 IF の in と out は別のトラフィックに当たる

ping は往復するので in / out の両方が進んでしまう。
**応答が返らない宛先**（同一セグメント上の不在ホスト）へ撃って片道に限定した。

| プローブ | e0/0 **in** | e0/0 **out** |
|---|---|---|
| RT03→10.0.12.99（顧客→サーバ・片道） | **+7** | +4 |
| RT02→10.0.13.99（サーバ→顧客・片道） | +3 | **+8** |

★ 差は付くが**ゼロにはならない**。EIGRP hello が e0/0 の両方向に流れており、
**RT01 自身が出す hello が out のカウンタを進めている**（§5 の再確認）。
→ 紙面でカウンタを出すなら、盤面にルーティング プロトコルを載せないか、
末尾の `permit ip any any` が hello を拾う前提で数を決めること。

### 16-4. ★「定義済みだが効いていない」の見え方（段A の根拠）

| 状態 | 通過率 | `show ip access-lists` | `show ip interface <IF>` |
|---|---|---|---|
| **未適用** | 100% | **エントリあり・カウンタなし** | `Inbound  access list is not set` |
| **無関係な IF に適用** | 100% | 同上（**区別できない**） | 同上 |
| 対照＝正しく適用 | **0%** | `(6 matches)` が付く | `Inbound  access list is 155` |

★ **カウンタが 0 のときは `(0 matches)` ではなく括弧ごと出ない**（紙面の描画規約）。
★ 「未適用」と「別 IF に適用」は**当該 IF の show では区別できない**
（全 IF か running-config を見る必要がある）。

→ §13 の「フィルタが実質不在」3種に**2種が加わって5種**になる:

| 仮説 | 割れる出力 |
|---|---|
| 未定義 | `show ip access-lists` に**何も出ない** |
| 空 | **ヘッダのみ** |
| 名前付き拡張（コマンドごと拒否） | ACL は出るが `show run` に**適用行が無い** |
| **未適用** | **エントリあり・カウンタなし** |
| **無関係な IF に適用** | 同上＋`show run interface` でのみ割れる |

### 16-5. ★★方向を間違えたときの症状（apply 形の一意性に直結）

ACL 156 ＝ `deny ip 10.0.13.0 0.0.0.255 any` / `permit ip any any`（**送信元ベース**）。

| 適用点 | RT03→RT02 | deny のカウンタ | 判定 |
|---|---|---|---|
| (i) e0/0 **in**（顧客側の入口） | **0%** | +6 | 正 |
| (ii) e0/0 **out** | **100%** | **+0** | 誤＝**完全な no-op** |
| (iii) e0/1 **in**（隣の IF） | **100%** | **+0** | 誤＝完全な no-op |
| (iv) ★e0/1 **out**（サーバ側の出口） | **0%** | **+5** | **正（別解）** |

★★ **(iv) が設計上の要**。送信元ベースの ACL は「入口 e0/0 in」でも
「出口 e0/1 out」でも**同じ結果**になる。
→ 「どこにどの向きで付けるか」を問う形は、**素のままでは正解が2つ**。
一意化するには要件で縛る（例:「不要なトラフィックは可能なかぎり早い段階で破棄する」＝入口）。
Cisco の定石「標準 ACL は宛先の近く／拡張 ACL は送信元の近く」がそのまま要件文になる。

**宛先ベース**を顧客側 out に付けた場合:

| 適用点 | RT03→RT02 | deny |
|---|---|---|
| (v) `deny ip any 10.0.13.0 0.0.0.255` を e0/0 **out** | **0%** | +5 |

★ **往路は素通りしているのに ping は失敗する**（復路が落ちている）。
→ **通過率だけでは (i) と (v) を区別できない**。到達可/不可の表しか出さない紙面では
方向の誤りは特定できず、**カウンタか `show ip interface` が要る**。

### 16-6. uRPF の `rx` と `any`

RT01 は 3.3.3.3 を e0/0 経由で学習。RT02 に非広告の Lo98 3.3.3.3/32 を立て、**e0/1 から**撃つ。

| モード | verification drops | suppressed verification drops |
|---|---|---|
| `reachable-via rx` | **5** | 0 |
| `reachable-via any` | **0** | **5** |

★ `any` は経路さえあれば入力 IF を問わない。**通したことは
`suppressed verification drops` に記録される**（§1 の未定義 ACL 例外と同じ欄）。
→ `rx`→`any` は「uRPF を設定しているのに効かない」型として成立し、**出力で割れる**。
★ 応答が戻らないので**通過率では測れない**（drop カウンタで採ること）。

### 16-7. NAT の `ip nat inside/outside` 付け忘れ

| 構成 | `show ip nat translations` | `show ip nat statistics` |
|---|---|---|
| ACL と `ip nat inside source list` のみ | **空** | `Outside interfaces:` / `Inside interfaces:` が**空** |
| 対照＝ inside/outside あり | `icmp 10.0.12.1:1024  10.0.13.3:39 ...` | — |

### 16-8. distribute-list の方向

`access-list 62 deny 172.30.32.0 0.0.0.255` / `permit any` を RT01 に。

| 適用 | RT01 が学ぶ | RT03 が学ぶ | `show ip protocols` |
|---|---|---|---|
| `distribute-list 62 in` | **落ちる** | 落ちる（RT01 が持たないため） | `Incoming update filter list for all interfaces is 62` |
| `distribute-list 62 out` | 持つ | **落ちる** | `Outgoing update filter list for all interfaces is 62` |
| `distribute-list 62 out Ethernet0/0` | 持つ | **落ちる** | `  Ethernet0/0 filtered by 62 (per-user), default is not set` |

★ in と out は「**自分が学ばない**」対「**相手が学ばない**」で**下流の RIB に差が出る**
＝1台の出力だけでは割れず、2台目を見せるか見せないかが出題設計になる。
IF 指定形は `show ip protocols` の字面が変わる（`(per-user)`）ので read 形の材料。

### 16-9. CoPP の `service-policy` 付け忘れ

| 構成 | 自機宛 ICMP | `show policy-map control-plane input` |
|---|---|---|
| policy-map まで作って `service-policy` なし | **100%** | **何も出ない（完全に空）** |
| 対照＝ `service-policy input` あり | **0%** | Class-map と police のカウンタが出る |

★ `service-policy output` も **control-plane 配下で受理される**（誤りとして仕込める）。
★ policy-map class の **`drop` 単独アクションは IOL では拒否された**（`% Invalid input`）。
落とすなら `police <rate> conform-action drop exceed-action drop`。

### 16-10. ★★厳密な ACL（末尾に `permit any` が無い）は**復路**を落とす

§16-5 の (ii)(iii) が「完全な no-op」だったのは、あの ACL に `permit ip any any` が
付いていたため。**要件どおりに書いた ACL には暗黙の拒否がある**ので話が変わる。

`access-list 158 permit ip 10.0.13.0 0.0.0.255 any`（顧客網のみ）を
**サーバ側 IF の in**（e0/1 in）に適用:

| | 結果 |
|---|---|
| RT03（顧客）→ RT02（サーバ） | **0%** |
| permit 行のカウンタ | **0**（＝往路はこの IF の in には来ていない） |
| `show ip eigrp neighbors` | ★**10.0.12.2 の隣接が消える** |
| 対照＝ `permit ip 10.0.12.0 0.0.0.255 any` を追加 | **100%**（その行に 12 matches） |

★ **カウンタが 0 のまま疎通が 0%** という指紋になる。落ちているのは
**復路**（サーバ→顧客・src がサーバ網）と**隣接**（RT02 の hello・src=10.0.12.2）で、
どちらも暗黙の拒否に当たっている。

### 16-11. ★★出口側に付けると「動くが 25 秒後にルーティングが壊れる」

同じ ACL を**サーバ側 IF の out**（e0/1 out）に適用:

| 経過 | RT03→RT02 | EIGRP 隣接 | 経路表 |
|---|---|---|---|
| 直後 | **100%**（permit 行 +5） | 正常 | 正常 |
| **25 秒後** | **0%** | `SRTT 5000 / Q Cnt 1 / Seq 0`（実質断） | ★**RT02 側の経路が全部消える** |
| 対照＝ `permit ip 10.0.12.0 0.0.0.255 any` 追加後 30 秒 | — | **復活** | — |

★★ **フィルタとしては要件どおりに動いている**（往路の顧客網は通り、他は落ちる）のに、
**RT01 自身が e0/1 から出す EIGRP hello（src=10.0.12.1）が暗黙の拒否に食われて**
隣接が落ち、結果として経路ごと消える（§5 の「outbound ACL は自機生成にも効く」の帰結）。
**直後は正しく見えて、hold time を跨いでから壊れる**という時間差がある。

→ 「このアクセス リストをどこにどの向きで適用すべきか」を問う形で、
**`if_up out` を「動くがルーティングを壊す」として落とす根拠**になる（実測に基づく complies）。

### 16-11b. ★顧客側の out（＝紙面の `apply_direction`）— G12・2026-08-11

§16-10 で測ったのは**サーバ側の in**（隣の IF）。紙面の `apply_direction` は
**顧客側の out** なので測り直した。ACL は `permit ip 3.3.3.0 0.0.0.255 any`
＝「ルータの**先にある**顧客網だけを許可」（リンクの 10.0.13.0/24 は含めない。
紙面の `_right_acl` と同じ性質）。これを RT01 の e0/0 **out** に適用。

| 経過 | RT03(3.3.3.3)→RT02 | permit のカウンタ | Et0/0 の EIGRP 隣接 |
|---|---|---|---|
| 直後 | **0%** | **0** | 正常 |
| 25 秒後 | 0% | 0 | ★`SRTT 5000 / Q Cnt 1 / Seq 0`（実質断） |
| 対照(c)＝復路の送信元も許可 | **0%（戻らなかった）** | — | — |
| 対照(d)＝リンク網も許可して 30 秒 | — | — | **復活** |

★ **2つの効果が同時に起きる**:
1. **復路が暗黙の拒否で落ちる**（カウンタ 0 のまま疎通 0% ＝ §16-10 と同じ指紋）
2. **自機が顧客側へ出す hello も落ちる**（許可対象はリンク網を含まないため）→ 隣接断

★★ **対照 (c) が戻らなかった**のは、その時点で既に隣接が落ちており
**RT01 が 3.3.3.3 への経路を失っていた**ため。
= (1) と (2) を分離した対照は取れていない（(d) で隣接復活は確認したが、その後の
疎通は測っていない）。**「復路の暗黙 deny 単独」の効果は §16-10（サーバ側 in）でのみ確定**。

★★★ **紙面モデルへの含意**（この測定の最大の収穫）:
紙面は `apply_direction` / `apply_iface_swap` を「復路が落ちて全断」とだけモデル化しており、
症状表（到達可／不可）としては実機と矛盾しない。しかし実機では**隣接も落ちる**ので、
cause 形の錯乱肢「**ルーティング・プロトコルの隣接関係が確立されていない**」は
**この盤面では真になり得る**。→ 偽の錯乱肢として出してはならない。
`CROSS` の当該エントリに「真になり得る盤面」の述語を付けて除外した
（`in` ではなく `out` に適用されている、を CROSS から外したのと同じ方針）。

### 16-12. ★測定の作法（追加）

6. **仕込みが本当に入ったかを確かめてから観測する**。
   G10/G11 の1回目は `access-list 158 permit 10.0.13.0 0.0.0.255` と書いており、
   **158 は拡張帯の番号なので標準構文は `% Invalid input`**。ACL が作られないまま
   ping を撃ち、**「100%＝no-op を確認した」と読み違えかけた**（作法1 と同型の事故で、
   今度は構文帯の取り違え）。→ `_require_acl()` でカウンタ行の有無を先に見る。

---

## 17. ★`established`（E1・2026-08-11・P2-⑤）

プローブ＝ RT03 から**閉じているポート**へ telnet（`telnet 10.0.12.2 9999`）。
SYN が出て RT02 が **RST+ACK** を返すので、**1回の試行で往路と復路の両方**を観測できる。
通過の成否ではなく**カウンタで帰属**させた。

| 置いた場所 | permit(established) | deny | telnet の応答 |
|---|---|---|---|
| (a) **往路側**（e0/0 in・SYN が通る向き） | **0** | **1** | `% Destination unreachable; gateway or host down` |
| (b) **復路側**（e0/1 in・RST が通る向き） | **1** | 0 | `% Connection refused by remote host` |
| (c) 対照＝復路側で established を**拒否** | — | **2** | `% Connection timed out; remote host not responding` |

★ **SYN は `established` に一致せず、RST+ACK は一致する**（定説どおり）。
(c) が落ちることで、観測が対象を捉えていることも裏取りできている。

★★ **副産物＝ telnet の応答メッセージが3通りに割れる**（この分野で一番使える観測）:

| 応答 | 意味 |
|---|---|
| `% Destination unreachable; gateway or host down` | **往路**が ACL で落ちた |
| `% Connection refused by remote host` | 往復とも通り、相手が RST を返した |
| `% Connection timed out; remote host not responding` | **復路**が落ちた（または相手が無応答） |

→ **「往路で落ちたか復路で落ちたか」が観測で区別できる**。
ping（ICMP）では §16-10／§16-11b のとおり**どちらも 0%** になって区別できなかったので、
往復を主題にする盤面（段B・`established` 系）の症状は
**TCP の応答メッセージで書くほうが情報量が多い**。

### P0 の完了状況

P1〜P15 すべて測定済み（P2 は 5 パスかけて意味論まで確定・P15 は P1c 実装中に必要になった追測）。
**G1〜G12（適用点・§16）と E1（`established`・§17）も測定済み**（2026-08-11・BL-109）。後片付け（P14）で
`show ip access-lists` が空・running-config に `access-group` / `distribute-list` /
`service-policy` / `ip nat` / `verify unicast` の残骸なしを確認済み。
CML ラボ **POC-ACL** は ACL 作業の一区切り（2026-08-11）で **STOPPED**。**ラボ定義は残してある**ので、`sweep.py <チェック名>` を実行すれば `ensure_lab()` が自動で起動し、`push_base()` が毎回 base 設定を流し直すためそのまま追加測定できる。
