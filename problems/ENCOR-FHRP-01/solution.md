# 模範解答 : ENCOR-FHRP-01

VLAN10 側インタフェース（IOL=Ethernet0/0 / IOSv=GigabitEthernet0/0）で設定。

## RT01（Active）
```
interface Ethernet0/0
 standby version 2
 standby 10 ip 192.168.10.1
 standby 10 priority 110
 standby 10 preempt
```

## RT02（Standby・既定 priority 100）
```
interface Ethernet0/0
 standby version 2
 standby 10 ip 192.168.10.1
```

## 確認コマンド
```
show standby brief
show standby
```
期待: RT01=Active / RT02=Standby、Virtual IP=192.168.10.1、RT01 が Priority 110・Preempt。

> `standby version 2` は両機で揃えること（v1/v2 混在だと相互認識しない）。
