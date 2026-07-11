# 解答例 (ENARSI-DHCPV6-01)

## 設計の骨子

| LAN | アドレス | DNS/ドメイン | RA フラグ | クライアント設定 |
|-----|----------|--------------|-----------|------------------|
| LAN-A | SLAAC（自己生成） | stateless DHCPv6 | **O-flag のみ** | `ipv6 address autoconfig default` |
| LAN-B | stateful DHCPv6 | stateful DHCPv6 | **M-flag ＋ prefix no-autoconfig** | `ipv6 address dhcp` + `ipv6 address autoconfig default` |

サーバは RT01 Et0/0 の1インタフェースで両 LAN のリレー要求を受けるため、
**プール名を固定しない `ipv6 dhcp server`（automatic モード）**を使い、
プール側の情報でリレーの link-address と突き合わせて選択させる:

- stateless プール → **`link-address 2001:DB8:A::/64`**（アドレス払い出しが無いプールの選択キー）
- stateful プール → **`address prefix 2001:DB8:B::/64`** 自体が選択キー

（`ipv6 dhcp server <プール名>` は **1 IF に 1 つしか張れず、2 つ目を入れると置換される**。
v4 の「giaddr でグローバルプールを自動選択」に相当するのが automatic モード）

## RT01（中央サーバ）

```
ipv6 dhcp pool POOL-STATELESS
 link-address 2001:DB8:A::/64
 dns-server 2001:DB8:1::53
 domain-name ccnp.local
!
ipv6 dhcp pool POOL-STATEFUL
 address prefix 2001:DB8:B::/64
 dns-server 2001:DB8:1::53
 domain-name ccnp.local
!
interface Ethernet0/0
 ipv6 dhcp server
```

## RT02（拠点 GW: リレー + RA フラグ）

```
interface Ethernet0/1
 ipv6 nd other-config-flag
 ipv6 dhcp relay destination 2001:DB8:12::1
!
interface Ethernet0/2
 ipv6 nd managed-config-flag
 ipv6 nd prefix 2001:DB8:B::/64 2592000 604800 no-autoconfig
 ipv6 dhcp relay destination 2001:DB8:12::1
```

- LAN-A は **O-flag だけ**（M を立てるとアドレスまで DHCP になり stateless 要件に反する）。
- LAN-B は **M-flag ＋ `no-autoconfig`**。M-flag を立てても **RA prefix の A-flag は既定で
  ON のまま**なので、no-autoconfig にしないとクライアントが SLAAC アドレスを
  **併せ持ってしまう**（「グローバルは払い出しの1個のみ」の要件に反する）。

## RT03（LAN-A クライアント）

```
interface Ethernet0/0
 ipv6 address autoconfig default
```

- SLAAC でアドレス自己生成 ＋ RA からデフォルト経路 (`Known via "ND"`) を取得。
- IOS は **RA の O-flag を見て自動的に INFORMATION-REQUEST を送信**し、
  DNS/ドメインを stateless DHCPv6 で取得する（追加設定不要）。

## RT04（LAN-B クライアント）

```
interface Ethernet0/0
 ipv6 address dhcp
 ipv6 address autoconfig default
```

- ★最大の罠: **`ipv6 address dhcp` を「単体で」設定するとリンクローカルが生成されず、
  SOLICIT がそもそも送信されない**（`debug ipv6 dhcp detail` に
  `SAS retured Null falling to link local` / `No source address`。状態表示は SOLICIT のまま・
  エラーは一切出ないサイレント障害）。IF 上で IPv6 を有効にする何か
  （`ipv6 enable` または本解のように `ipv6 address autoconfig`）が併存すれば LL が生成され解決する。
  dhcp 単体で止まった場合の切り分けが本問の学び（実機検証: 単体=SOLICIT 固着 /
  autoconfig 併存 or ipv6 enable 追加=即 OPEN）。
- ★第2の学び: **stateful DHCPv6 はデフォルト経路を配らない**。
  アドレスは DHCP・経路は RA という分担のため `ipv6 address autoconfig default` を併用する
  （LAN-B は no-autoconfig なので SLAAC アドレスは生成されず、デフォルト経路だけ得る。
  結果としてこの1行が LL 問題も同時に解決している）。

## 検証コマンド

```
RT01# show ipv6 dhcp pool                  ! 2プールと選択キー
RT01# show ipv6 dhcp binding              ! RT04 の IA NA リース
RT02# show ipv6 dhcp interface Ethernet0/1 ! relay mode / 宛先
RT02# show ipv6 interface Ethernet0/1      ! 末尾の "Hosts use ..." 2行(O)
RT02# show ipv6 interface Ethernet0/2      ! "Hosts use DHCP to obtain routable addresses."(M)
RT03# show ipv6 dhcp interface Ethernet0/0 ! Configuration parameters: DNS/Domain
RT04# show ipv6 dhcp interface Ethernet0/0 ! Address State is OPEN / 払い出しアドレス
RT03# show ipv6 route ::/0                 ! Known via "ND"
RT04# show ipv6 interface brief Ethernet0/0 ! GUA が払い出しの1個のみ
```

## トラブルシュートの定石（本問で身につけるもの）

1. クライアントが取得しない → まず**クライアントが送信できているか**
   （LL の有無・`debug ipv6 dhcp detail` の `No source address`）。
2. 次に**リレー**（`show ipv6 dhcp interface` が relay mode か・宛先）。
3. 次に**サーバのプール選択**（automatic か・link-address / address prefix が
   リレーの link-address と一致するか）。`debug ipv6 dhcp detail` をサーバで。
4. 「アドレスが2個ある」→ RA prefix の **A-flag**（no-autoconfig 漏れ）。
5. 「アドレスは付いたが外に出られない」→ stateful はデフォルトを配らない。**RA 由来**か確認。
6. クライアントの再取得は `no ipv6 address dhcp` → 再投入が確実
   （shut/no shut は次の RA まで IDLE のまま・clear はバックオフ中に効かないことがある）。
