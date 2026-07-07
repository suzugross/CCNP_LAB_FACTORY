# 模範解答 : ENCOR-WANHA-01（デュアルGRE + IP SLA/Track フェイルオーバ）

設定するのは **RT01 (HQ) / RT04 (Branch)**。RT02/RT03（トランジット）は変更しない。
iol インタフェース: HQ/Branch とも Ethernet0/0=Transit-A側, Ethernet0/1=Transit-B側。

## RT01 (HQ)
```
interface Tunnel1
 ip address 172.16.1.1 255.255.255.252
 tunnel source Ethernet0/0
 tunnel destination 10.0.24.2
 tunnel mode gre ip
!
interface Tunnel2
 ip address 172.16.2.1 255.255.255.252
 tunnel source Ethernet0/1
 tunnel destination 10.0.34.2
 tunnel mode gre ip
!
ip sla 1
 icmp-echo 172.16.1.2
 frequency 5
ip sla schedule 1 life forever start-time now
!
track 1 ip sla 1 reachability
!
ip route 10.10.4.1 255.255.255.255 172.16.1.2 track 1
ip route 10.10.4.1 255.255.255.255 172.16.2.2 200
```

## RT04 (Branch)
```
interface Tunnel1
 ip address 172.16.1.2 255.255.255.252
 tunnel source Ethernet0/0
 tunnel destination 10.0.12.1
 tunnel mode gre ip
!
interface Tunnel2
 ip address 172.16.2.2 255.255.255.252
 tunnel source Ethernet0/1
 tunnel destination 10.0.13.1
 tunnel mode gre ip
!
ip sla 1
 icmp-echo 172.16.1.1
 frequency 5
ip sla schedule 1 life forever start-time now
!
track 1 ip sla 1 reachability
!
ip route 10.10.1.1 255.255.255.255 172.16.1.1 track 1
ip route 10.10.1.1 255.255.255.255 172.16.2.1 200
```

> ★**両端に IP SLA/Track を置くのが要点**。HQ だけに置くと、HQ は Tunnel2 へ切替わっても
> Branch の戻りが Tunnel1 のまま（Branch 側 Tunnel1 は source が生きていて落ちない）→
> 戻りがブラックホールし非対称で疎通断。Branch も相手(HQ)の Tunnel1 IP `172.16.1.1` を
> SLA 監視し、Track Down で同時に Tunnel2 へ切替えること。

## 確認
```
show interfaces tunnel 1            ! up/up, Tunnel protocol/transport GRE
show track 1                        ! Reachability is Up
show ip route 10.10.4.1             ! via 172.16.1.2, Tunnel1 (primary)
ping 10.10.4.1 source 10.10.1.1     ! overlay 疎通

! --- フェイルオーバ確認（primary=Transit-A 障害をシミュレート）---
configure terminal
 interface Ethernet0/0              ! HQ の Transit-A 向け
  shutdown
!
show track 1                        ! Reachability is Down
show ip route 10.10.4.1             ! via 172.16.2.2, Tunnel2 (backup) に切替
ping 10.10.4.1 source 10.10.1.1     ! backup 経由で疎通継続
! 復旧: no shutdown → 数秒後 track Up → primary(Tunnel1) へ自動復帰
```

## ポイント（落とし穴の解説）
- **トンネルは各トランジット向け物理IFを source に**して経路を固定（Tunnel1=Eth0/0=Transit-A,
  Tunnel2=Eth0/1=Transit-B）。tunnel destination は対向のトランジット側終端IP。
- **IP SLA の target は primary でしか到達できない先(`172.16.1.2`＝Branch の Tunnel1 IP)**にする。
  Transit-A 障害で Tunnel1 が落ちると 172.16.1.2 へ到達不能 → SLA Down → Track Down →
  primary 経路が外れ、フローティング backup(AD 200, Tunnel2)が活性化。
  - もし target を Branch LAN(10.10.4.1) にすると、障害後に backup 経由で到達できてしまい
    Track が Up に戻り primary を張り直す → flap の原因。**primary 専用の宛先**を狙うこと。
- **`ip sla schedule 1 life forever start-time now` を忘れない**（無いと SLA が走らず Track Unknown）。
- **primary に `track 1`、backup は AD 200 のフローティング**。これで通常時 primary のみ、
  Track Down 時だけ backup が入る。
- Branch 側は戻り経路を primary(Tunnel1)＋フローティング(Tunnel2 AD200)で対称に。Tunnel1 が落ちれば
  connected の 172.16.1.0/30 が消え、primary 戻り経路が外れて backup に切替わる。
- 採点は効果ベース: Tunnel up/up&GRE、SLA/Track 構成と Up、primary 経路が **Tunnel1** で RIB、
  フローティング backup の設定、Branch 戻り経路、そして HQ→Branch LAN の実 ping 成功。
