# 解答 ENCOR-LAG-TS-01

仕込まれた故障は **3 層**（独立に切り分け可能）。

## 故障① passive/passive（束が形成されない）
SW01・SW02 とも channel-group の mode が `passive`。passive は相手からの LACP を待つだけなので
**両側 passive では永遠に束が組まれない**。
- 修正：少なくとも片側を `active` にする（推奨は両側 active）。
```
! SW01
interface range Ethernet0/0 - 1
 channel-group 1 mode active
! SW02
interface Ethernet0/0
 channel-group 1 mode active
```

## 故障② メンバ欠落（束ねが 1 本だけ）
SW02 の `Ethernet0/1` が **channel-group 未投入**＝束に参加していない。
- 修正：
```
! SW02
interface Ethernet0/1
 channel-group 1 mode active
```

## 故障③ access VLAN 不一致（束はできても疎通しない）
SW02 の Port-channel1（および物理メンバ）が **access VLAN 40** に入っている。SW01 側は VLAN30。
束ねが完成しても L2 のブロードキャストドメインが食い違い、SVI 間 ping が通らない。
- 修正：
```
! SW02
interface Port-channel1
 switchport access vlan 30
```
> ※ メンバ物理 IF の access vlan は channel-group 投入時に Po 設定へ追従するが、
>   念のため `Et0/0`・`Et0/1` も `switchport access vlan 30` に揃えておくと確実。

## 確認
```
show etherchannel summary      ! Po1(SU)・Et0/0(P) Et0/1(P)・Protocol LACP
show lacp neighbor
ping 10.30.30.2 source Vlan30   ! 成功
```
