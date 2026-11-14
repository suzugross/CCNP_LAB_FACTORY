# PoC: static route の実挙動と計算器の照合(BL-271・2026-11-12)

ルーティング経路づくり(BL-271)の計算器 [topologies/route_model.py](../../topologies/route_model.py) が IOS の実際の挙動と
合っているかを、IOL で確かめた。設計= [ROUTE-PATH.design.md](../../problems/_drafts/ROUTE-PATH.design.md) §4 の PoC 表・§11。

- ラボ: `problems/_POC-ROUTE`(IOL iol-xe 17.15.1 × 4・再利用可)。盤面は `route_model.build_net` の四角＋対角線
  (R1–R2・R1–R3・R2–R4・R3–R4・R2–R3)、各ルータに LAN 1 つ(10.N.1.0/24・1 ポートだけの非管理スイッチにつなぐ)と
  ループバック 10.255.0.N/32。RT0N = 計算器の RN。day0 は `route_model.ios_config` から作った。
  計算器の Gi0/0 → Ethernet0/0、Gi0/1 → Ethernet0/1、Gi0/2 → Ethernet0/2、Gi0/3 → Ethernet1/0。
- 操作と照合: [drive.py](drive.py)(SSH)。`drive.py all` は CASES の各件で「static を入れる → 4 台の `show ip route` と
  `show ip cef <宛先>` を取る → 計算器(`tables`・`decide`)と自動で突き合わせる → 元に戻す」。`drive.py case connected`
  などの STEPS は生の手順。`cmp_format.py logs/all-2.log` は記録した `show ip route` を `route_model.show_ip_route` と行ごとに比べる。
- 手順: `scripts/lab.sh provision _POC-ROUTE` → `.venv/bin/python3 poc/route/drive.py all` → `… case connected rec_default_long`
  → `scripts/lab.sh teardown _POC-ROUTE`。生ログ= [logs/](logs/)(`all-2.log` が照合の本番・`all-1.log` は照合器の不具合で読み替え前)。

## 結果

| # | 論点 | 計算器の予測 | 実機 | 結果 |
|---|---|---|---|---|
| 1a | connected と local | IF ごとに C と L、/32 のループバックは C だけ | 同じ(`C 10.255.0.1/32 is directly connected, Loopback0`・L なし) | 一致 |
| 1b | ロンゲストマッチ・AD は同じ宛先の中だけ | R1: /16 AD 1(→R2)と /24 AD 250(→R3)が両方表に入り、10.4.1.1 は /24 → R3、10.4.2.9 は /16 → R2 | 同じ(`show ip cef` も traceroute も) | 一致 |
| 1c | 同じ宛先の connected と static | static は表に出ない | 出ない | 一致 |
| 1d | /32 の static は connected の /24 に勝つ | R4: 10.4.1.77 は /32 の static → R3、10.4.1.66 は attached | 同じ | 一致 |
| 2a | フローティング(AD 1 と AD 5)平常時 | AD 1 だけ表に入る | 同じ(`show ip static route` で AD 1 が `[A]`、AD 5 が `[N]`) | 一致 |
| 2b | リンク断(両端を shutdown) | AD 5 が入る・落ちたリンクの C/L が消える | 6 秒以内に同じ | 一致 |
| 2c | 相手側だけ shutdown(R2 側) | (計算器はリンク断= 両端 down しか持たない) | R1 の Et0/1 は up/up のまま・AD 1 の static が残り、R1 から 10.4.1.1 への ping は 0%(ブラックホール) | 記録(IOL の伝わらない挙動。ゲームのリンク断は両端 down で正しい) |
| 2d | 自分側だけ shutdown(R1 側) | — | R1 は AD 5 に切り替わる。R2 は 172.16.12.0/30 の C/L を持ったまま | 記録 |
| 3a | 再帰(ループバック宛ての next-hop を /32 の static で解決) | 入る・R1 → R3 → R4 | 同じ | 一致 |
| 3b | **デフォルト経路だけで next-hop を解決するか** | 解決する(VIA_DEFAULT = True) | **解決しない**。`show ip static route` で `10.4.0.0/16 [1/0] via 10.255.0.4 [N]`(non-active)。70 秒待っても、`ip route static install-routes-recurse-via-nexthop` を入れても `[N]` のまま。10.4.1.1 はデフォルトで転送 | **不一致** |
| 3c | 自分の宛先で自分を解決する static(`ip route 10.255.0.0 255.255.0.0 10.255.0.4` だけ) | 入らない | 入らない | 一致 |
| 3d | **Null0 の行を通る再帰**(`10.255.0.0/16 Null0` ＋ `10.4.0.0/16 via 10.255.0.4`) | 解決できない → 入らない → 10.4.1.1 は経路なし | **入る**(`S 10.4.0.0/16 [1/0] via 10.255.0.4`)。CEF は `nexthop 10.255.0.4 Null0` で捨てる | **不一致** |
| 3e | 再帰の 2 段(next-hop をデフォルトでない /16 の static で解決) | 入る | 入る | 一致 |
| 4 | ECMP(同じ宛先・同じ AD・別の next-hop) | 両方入る | 両方入る。2 行目は `                     [1/0] via …`(計算器の書式と同じ) | 一致(並び順だけ違う・下) |
| 5 | connected の段 | — | 下の「connected の段」 | 記録 |
| 6a | デフォルトどうしの向け合い(R1 ⇄ R2) | ループ R1 → R2 → R1 | traceroute が `172.16.12.2` と `172.16.12.1` を交互に 8 ホップ | 一致 |
| 6b | Null0 の集約で止める | R2 で null0 | traceroute `1 172.16.12.2` / `2 172.16.12.2 !H`(R2 が到達不能を返す) | 一致 |
| 7 | show ip route の書式 | — | 72 表のうち書式の違いは 2 種類(下) | 2 か所直す |

照合の件数: `all-2.log` の 18 件のうち、計算器と違ったのは 3b(2 件)・3d・2c/2d(片側 shutdown= 計算器で表せない状況)だけ。
経路表 72 表・`show ip cef` の判断はそれ以外すべて一致。

## 計算器の直し方(報告。route_model.py はこの PoC では触っていない)

1. **VIA_DEFAULT = False**(3b)。IPv4 の static の next-hop は、デフォルト経路(0.0.0.0/0)だけでは解決されない。
   デフォルトでない、もっと長い経路(3e の /16 の static など)では解決される。表には入らず、`show ip static route` では `[N]`。
2. **Null0 の行を通る再帰は「解決する・転送は Null0 で捨てる」**(3d)。`_resolve` で当たった行が Null0 なら
   `[(None, "Null0", None)]` を返して表に入れ、`decide` は null0 にする。表示は設定どおり `S 10.4.0.0/16 [1/0] via 10.255.0.4`
   (「is directly connected, Null0」ではない)。
3. **「is subnetted」の段の行にはマスクを書かない**(7)。マスクが 1 種類の段は見出しにマスクがあり、行は網の番号だけ:
   ```
         192.168.60.0/26 is subnetted, 1 subnets
   S        192.168.60.0 [1/0] via 172.16.24.2
         10.0.0.0/32 is subnetted, 1 subnets
   C        10.255.0.4 is directly connected, Loopback0
   ```
   (variably subnetted の段と、見出しの無いクラスフルちょうどの行 `S     192.168.50.0/24 [1/0] via …` はマスクを書く= 今の計算器どおり)
4. **ECMP の via の並び順は設定した順ではない**(7)。3 例とも next-hop の IP の降順に並んだ
   (`.13.2` → `.12.2` は 2 通りの設定順どちらでも・`.24.2` → `.23.2`)。例が 3 つだけなので、表示は「降順」にそろえるか、
   並び順に意味を持たせない(お題・解説で順番を使わない)。
5. リンク断は両端 down のままでよい(2b は一致)。IOL では片側の shutdown が相手に伝わらない(2c)ので、実機での裏どりや
   ラボでは両端を落とす(メモ ccnp-phase1-pipeline の「IOL のリンクダウン非伝播」と同じ)。
   実機(物理)では片側を落とせば相手もリンクが落ちるので、ゲームの「リンクが切れた」は両端 down が正しい。

## connected の段(ステージ 1 の材料・RT04 の Ethernet0/0= 10.4.1.1/24)

| 操作 | 結果 |
|---|---|
| IP 付きで `shutdown` | 3 秒後に `C 10.4.1.0/24` と `L 10.4.1.1/32` が消える。`show ip interface brief` は `administratively down down` |
| `no shutdown` | 5 秒以内に C と L が戻る |
| `no ip address` | C と L が消える。brief は `unassigned … up up` |
| 別のサブネットの IP(10.4.2.1/24) | `C 10.4.2.0/24`・`L 10.4.2.1/32` に入れ替わる |
| 重なるサブネット(up の Ethernet0/0 と同じ 10.4.1.0/24 を Loopback9 に) | **`% 10.4.1.0 overlaps with Ethernet0/0`**。IP は付かない(brief は `unassigned`) |
| 重なるサブネット(リンクの Ethernet0/1 に 10.4.1.9/24) | 同じ文で拒否。元の 172.16.24.2 のまま |
| 重なるサブネット(shutdown 中の Loopback9 に付けてから no shutdown) | 付けるときに同じ文が出るが IP は**入る**。`no shutdown` で `% 10.4.1.0 overlaps with Ethernet0/0` と **`Loopback9: incorrect IP address assignment`** が出て、`administratively down down` のまま上がらない |

ほかの小さな事実: ループバックの /32 だけが残った 10.0.0.0/8 は `10.0.0.0/32 is subnetted, 1 subnets` になる(上の 3 の書式)。

## 公式の裏どり

- IP Routing Configuration Guide, Cisco IOS XE 17.x — IPv6 Routing: Static Routing:
  再帰の static は next-hop が直接または間接に有効な出口インタフェースへ解決でき、自分で自分を解決せず、再帰の深さが上限以内のときだけ
  表の候補になる。AD の大きい static(フローティング)はよりよい経路が消えたときだけ入り、AD 255 は入らない。
  IPv6 は既定で ::/0 による解決をしない(`ipv6 route static resolve default` で以前の動きに戻す)。
  https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-routing/b-ip-routing/m_ip6-route-static-xe.html
- IP Routing Configuration Guide, Cisco IOS XE 17.x — Recursive Static Route: `ip route static install-routes-recurse-via-nexthop` は、
  next-hop や宛先が既に学んだ経路で表にあるときでも再帰の static を RIB に入れる機能(デフォルト経由の解決を許すものではない= 3b の実測と合う)。
  https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-routing/b-ip-routing/m_iri-recursive-static-route-xe.html
- Configure a Next Hop IP Address for Static Routes(技術文書): static は再帰的で、next-hop への経路がある限り表に残る
  (フローティングが入らない落とし穴の例)。
  https://www.cisco.com/c/en/us/support/docs/dial-access/floating-static-route/118263-technote-nexthop-00.html
- IPv4 でデフォルト経由の解決をしないこと自体を明記した公式の文は今回の検索では見つからなかった。IPv6 の文書の既定と同じ向きで、
  実機(IOL 17.15.1)で確かめた(3b)。出口インタフェースを書いたデフォルトなら解決できるという利用者フォーラムの話があるが、
  ゲームは next-hop 指定だけなので試していない。

---

# 追加 PoC(2026-11-12・next-hop の選び方)

経路を足す操作を「次の行き先の IP を地図で押す」形にするにあたり、正しくない IP を next-hop にしたときの IOS の反応を確かめた
(BL-271・設計 ROUTE-PATH.design.md)。ラボは同じ `problems/_POC-ROUTE`(IOL iol-xe 17.15.1 × 4)を立て直し、R1(RT01)で試した。
手順= [drive.py](drive.py) の STEPS `nh_choice`(`drive.py case nh_choice`)・生ログ= [logs/nh_choice.log](logs/nh_choice.log)。
終わってから `scripts/lab.sh teardown _POC-ROUTE` で撤収した(リースも返却・XRT-15 には触れていない)。

| # | 入れたコマンド(R1) | 設定時の反応(原文) | running-config | 経路表 | 転送(`show ip cef 10.4.1.1`) |
|---|---|---|---|---|---|
| 1 | `ip route 10.4.0.0 255.255.0.0 172.16.12.1`(自分の Et0/1 の IP) | `%Invalid next hop address (it's this router)` | 入らない(`no ip route …` も `%No matching route to delete`) | 出ない | — |
| 2 | `ip route 10.4.0.0 255.255.0.0 172.16.34.2`(R4 の IP。R1 はこのサブネットにつながっていない) | エラーなし | 入る | 出ない。`show ip static route` で `M  10.4.0.0/16 [1/0] via 172.16.34.2 [N]`(non-active) | `0.0.0.0/0  no route` |
| 3 | `ip route 10.4.0.0 255.255.0.0 172.16.12.3`(/30 のブロードキャスト) | エラーなし | 入る | **出る**(`S 10.4.0.0/16 [1/0] via 172.16.12.3`・`[A]`) | `10.4.0.0/16  receive for Ethernet0/1`(転送せず自分宛てとして受け取る)・`show ip arp 172.16.12.3` は空 |
| 4 | `ip route 10.4.0.0 255.255.0.0 172.16.12.0`(ネットワーク アドレス) | エラーなし | 入る | **出る**(`S 10.4.0.0/16 [1/0] via 172.16.12.0`・`[A]`) | `10.4.0.0/16  receive for Ethernet0/1`(同上) |

計算器(route_model)との対応:
- 1: route_model は自分の IP を next-hop にした static を `_resolve` で L の行に当てて「解決できない」(表に入らない)とする。実機は**設定そのものを受け付けない**
  (エラー文は上)。ゲームで自分の IP を選べるようにするなら、IOS と同じく足せない扱い(このエラー文を出す)にするのが実機どおり。
- 2: route_model の「解決できない static は表に入らない(unresolved)」と一致。
- 3・4: route_model は connected のサブネットに入る next-hop なので表に入れ、転送は「その IP の持ち主がいない」(nohost)で落とす。実機も表に入り、
  パケットは先へ送られずに R1 で止まる(CEF が receive= 自分宛て扱い)。落ちる場所(R1)は一致、止まり方の理由の言い方だけが違う。

---

# 追加 PoC(2026-11-12・穴埋めの入れ間違い)

経路を足す操作を「宛先・マスク・ゲートウェイ・管理距離の 4 つの欄を書く」形に変えるにあたり、書き間違えたときの IOS の反応を確かめた
(BL-271・設計 ROUTE-PATH.design.md §14)。ラボは同じ `problems/_POC-ROUTE`(IOL iol-xe 17.15.1 × 4)を立て直し、R1(RT01)で試した。
手順= [drive.py](drive.py) の STEPS `input_form`・`input_form2`・生ログ= [logs/input_form.log](logs/input_form.log)・[logs/input_form2.log](logs/input_form2.log)。
終わってから `scripts/lab.sh teardown _POC-ROUTE` で撤収した(XRT-15 には触れていない)。

| # | 入れたコマンド(R1) | 応答(原文) | 設定 | 経路表 |
|---|---|---|---|---|
| 1 | `ip route 10.4.1.1 255.255.255.0 172.16.12.2`(ホスト部が 0 でない) | `%Inconsistent address and mask` | 入らない | — |
| 2 | `ip route 10.4.0.0 255.0.255.0 172.16.12.2`(1 が続かないマスク) | `%Inconsistent address and mask` | 入らない | — |
| 3 | `ip route 10.4.1.0 /24 172.16.12.2` | `% Invalid input detected at '^' marker.`(^ は `/24` の頭) | 入らない | — |
| 4 | `… 172.16.12.2 0`(AD 0) | `% Invalid input …`(^ は `0`) | 入らない | — |
| 5 | `… 172.16.12.2 256`(AD 256) | `% Invalid input …`(^ は `256` の `6`) | 入らない | — |
| 6 | `… 172.16.12.2 255`(AD 255) | なし | 入る | 出ない(`show ip static route` で `[255/0] … [N]`) |
| 7 | `ip route 10.4.1.0 255.255.255.0 0.0.0.0` | `%Invalid next hop, looping back to the network` | 入らない | — |
| 8 | next-hop `224.0.0.1` | `%Invalid next hop address` | 入らない | — |
| 9 | next-hop `255.255.255.255` | `%Invalid next hop address` | 入らない | — |
| 10 | 同じ宛先・同じ next-hop で `… 172.16.12.2` → `… 172.16.12.2 200` | なし | **置き換わる**(running-config は AD 200 の 1 行) | `distance 200` |
| 10b | 続けて AD を書かずに `… 172.16.12.2` | なし | AD 1 に戻る(1 行のまま) | `distance 1` |
| 10c | `no ip route 10.4.1.0 255.255.255.0 172.16.12.2`(AD を書かない) | なし | 消える | — |
| 11 | `ip route 0.0.0.0 255.255.255.0 172.16.12.2` | なし | 入る | `0.0.0.0/24 [1/0]`(`[A]`) |
| 12 | `ip route 10.4.1.0 0.0.0.0 172.16.12.2` | `%Inconsistent address and mask` | 入らない | — |
| 13 | `ip route 10.4.1 255.255.255.0 …`(数が 3 つ) | `% Invalid input …` | 入らない | — |
| 14 | マスク `255.255.255.256` | `% Invalid input …`(^ は最後の `6`) | 入らない | — |
| 15 | next-hop `127.0.0.1` | `%Invalid next hop address` | 入らない | — |
| 16 | next-hop `240.0.0.1` | `%Invalid next hop address` | 入らない | — |
| 17 | `… 172.16.12.2 1`(AD 1 を書く) | なし | 入る(running-config には `1` が付かない) | `[1/0]` |
| 18 | `ip route 010.4.1.0 …`(頭に 0) | なし | `10.4.1.0` として入る | 入る |
| 19 | `ip route 0.0.0.0 0.0.0.0 172.16.12.2` | なし | 入る | 入る |
| 20 | 宛先が自分の LAN(connected と同じ 10.1.1.0/24) | なし | 入る | 出ない(`[N]`。connected が勝つ= #1c と同じ) |

ゲームでの扱い: 1〜5・7〜9・12〜16 は IOS の応答の文で断る(`% Invalid input` の ^ は、間違えた欄の頭に置く= 実機は 5・14 のように
数の途中を指すこともあるので近似)。6 は計算器(route_model)に「AD 255 は表に入らない(ad255)」を足した。10 は同じ宛先・同じ
ゲートウェイを書き直すと管理距離が置き換わる(手数は 1 行)。ゲームの決まりとして、ステージ 2〜4 は宛先を地図の LAN(ステージ 4 から
デフォルトも)に限る(IOS は 11 のような宛先も受け付けるが、最少手数の探索をその範囲に合わせるため)。この断りには IOS の文を出さない。
