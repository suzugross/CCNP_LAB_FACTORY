# 模範解答 : ENARSI-BGP-NHSELF-01

設定するのは **RT01 (AS65001)** のみ。

```
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.1.13.2 remote-as 65003
 neighbor 10.1.12.2 remote-as 65001
 neighbor 10.1.12.2 next-hop-self
```

## 確認
```
! RT01
show ip bgp 203.0.113.0/24       ! eBGP で学習、next-hop 10.1.13.2
! RT02 (next-hop-self 無しの場合)
show ip bgp 203.0.113.0/24       ! next-hop 10.1.13.2, "(inaccessible)" → RIB に入らない
! RT02 (next-hop-self 有り)
show ip route bgp                ! 203.0.113.0/24 via 10.1.12.1
```

## ポイント（落とし穴の解説）
- **iBGP は next-hop を書き換えない**: eBGP で受け取った経路を iBGP ピアに渡すとき、
  next-hop は元の eBGP ピアのアドレス (10.1.13.2) のまま伝わる。
- RT02 は `10.1.13.0/30` への経路を持たないため、next-hop が **inaccessible** となり、
  iBGP で広告は届くのに **RIB にはインストールされない**（`show ip bgp` には出るが
  `show ip route` には出ない）。これが iBGP の典型的な落とし穴。
- **`neighbor <iBGP peer> next-hop-self`**: RT01 が iBGP で広告するとき、next-hop を
  自分のアドレス (iBGP セッションの送信元 = 10.1.12.1) に書き換える。RT02 は 10.1.12.1 へ
  直結で到達できるため、経路が有効になり RIB に入る。
- 別解として「外部リンク 10.1.13.0/30 を IGP で AS 内に広告する」方法もあるが、本問は
  next-hop-self で解くよう指定（外部リンクを内部に晒さないのがベストプラクティス）。
