# 解答・解説 ENCOR-PBR-02 (拠点エッジでの通過トラフィック経路振り分け)

## 核心 — 「通常の(インタフェース)PBR」
PBR-01 は送信元が RT01 自身の Loopback ＝ ルータ生成トラフィックだったので
`ip local policy route-map` を使った。本問の送信元は **RT01 の背後にいる RT04** であり、
RT01 から見ると **入力インタフェースを通過する中継トラフィック**。よって PBR は
**入力インタフェース配下に `ip policy route-map`** で適用する（＝教科書的な通常の PBR）。

`ip local policy`（自装置生成用）を入れても通過トラフィックには効かないので、本問では不正解。

## RT01 設定例
```
ip access-list extended DEV-TRAFFIC
 permit ip host 10.2.2.1 host 3.3.3.3
!
route-map PBR-DEV permit 10
 match ip address DEV-TRAFFIC
 set ip next-hop 10.0.12.2
!
interface Ethernet0/2          ! RT04(拠点LAN)向けの入力IF。IOSv なら GigabitEthernet0/2
 ip policy route-map PBR-DEV
```

- `match ip address DEV-TRAFFIC` … 開発部(10.2.2.1)発・DC(3.3.3.3)宛だけ分類。
  `permit ip 10.2.2.0 0.0.0.255 any` などでも可（採点は 10.2.2.x を対象にしていれば許容）。
- `set ip next-hop 10.0.12.2` … WAN-A(RT02)の直結 IP。最短(WAN-B/RT03直結)を上書き。
- **適用は RT04 向けの入力 IF (`ip policy`)**。PBR は「入ってきたパケット」に作用する。
- route-map にマッチしないトラフィック(営業部 10.1.1.1 発など)は通常ルーティング＝
  最短の WAN-B(RT03直結)のまま。

## 動作確認（クライアント RT04 から）
```
RT04# traceroute 3.3.3.3 source Loopback2 numeric   ! 開発部 → 2hop目 = 10.0.12.2 (WAN-A経由)
RT04# traceroute 3.3.3.3 source Loopback1 numeric   ! 営業部 → 2hop目 = 10.0.13.2 (WAN-B直結)
RT01# show route-map                                ! Policy routing matches がカウント
RT01# show ip policy                                ! どのIFに route-map が付いているか
```
RT04 からの traceroute は hop1=10.0.14.1(RT01)、hop2 が分岐点になる。

## 落とし穴
- **`ip local policy`(自装置用) と `ip policy`(IF入力用) の取り違え**。本問は通過トラフィック
  なので IF 配下の `ip policy` が正解。local policy だと RT04 発の通信には一切効かない。
- `ip policy` を付ける IF を間違える(WAN側や別IFに付ける)と入力方向が合わず不発。
  **トラフィックが入ってくる IF = RT04 向け(e0/2)** に付ける。
- `set ip next-hop` は直結アドレス(10.0.12.2)を指定。到達不能だと通常経路に落ちる。
- スタティックで最短路自体を書き換えるのは制約違反(営業部も巻き込む)。

## 採点 (計100)
| 配点 | 確認 |
|------|------|
| 30 | RT04: 開発部(Lo2)発 traceroute が 10.0.12.2 経由・10.0.13.2 を通らない(実経路で WAN-A) |
| 15 | RT04: 営業部(Lo1)発 traceroute が 10.0.13.2 のまま・10.0.12.2 を通らない |
| 20 | RT01: route-map が ACL マッチ + `set ip next-hop 10.0.12.2` |
| 15 | RT01: 入力IFに `ip policy route-map`(local policy ではない=通常PBR) |
| 10 | RT01: マッチ ACL が 10.2.2.x を対象 |
| 10 | RT04: 3.3.3.3/32 を OSPF で学習(到達性維持) |
