# 模範解答 : ENCOR-ACL-EXTENDED-01

設定するのは **RT02 のみ**。

```
ip access-list extended EDGE-FILTER
 deny   tcp any host 3.3.3.3 eq telnet
 deny   icmp any host 3.3.3.3
 permit ip any any
!
interface Ethernet0/0
 ip access-group EDGE-FILTER in
```

## 確認
```
show ip access-lists EDGE-FILTER     ! 3 ACE。permit ip any any が末尾にあること
show running-config interface Ethernet0/0   ! ip access-group EDGE-FILTER in
show ip route ospf                    ! 3.3.3.3/32 が残っている(=OSPFを壊していない)
```

## ポイント（落とし穴の解説）
- **暗黙の deny**: ACL 末尾には暗黙の `deny ip any any` がある。`permit ip any any` を
  忘れると、RT01→RT02 の **OSPF hello(プロトコル89)** まで落ち、隣接が切れて RT01 が
  3.3.3.3 を学習できなくなる。本問の最後のチェックはこれを検出する。
- **deny の順序**: deny は permit より前に置く。`permit ip any any` を先頭に書くと
  以降の deny が評価されず Telnet/ICMP が通ってしまう（first-match の原則）。
- **方向**: 「RT01 側から来る」トラフィックを止めるので、RT02 の RT01 向け IF に **in**。
  out にすると RT02 が送出する向き(RT03→RT01 方向など)になり意図とずれる。
- **eq telnet / eq 23**: どちらの表記でも可（IOS は telnet=23 を相互変換）。
- `deny icmp any host 3.3.3.3` は echo に限定しても可（`deny icmp any host 3.3.3.3 echo`）。
  本問は ICMP 全体 deny / echo 限定 どちらでも PASS。
