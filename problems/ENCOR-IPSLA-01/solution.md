# 模範解答 : ENCOR-IPSLA-01

RT01 のみ設定する（RT02/RT03/RT04 は ISP/Internet 機器で変更禁止）。

## RT01
```
ip sla 1
 icmp-echo 10.0.12.2
 frequency 5
ip sla schedule 1 life forever start-time now
!
track 1 ip sla 1 reachability
!
ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1
ip route 0.0.0.0 0.0.0.0 10.0.13.2 200
!
```

## 確認
```
show ip sla configuration 1
show ip sla statistics 1
show track 1
show ip route 0.0.0.0
ping 8.8.8.8 source Loopback0                ! 通常時 → primary(RT02→RT04) 経由
!
! primary 障害シミュレーション:
configure terminal
 interface Ethernet0/0                        ! RT02向き(primary) リンク
  shutdown
!
show track 1                                  ! Reachability is Down
show ip route 0.0.0.0                          ! nexthop が 10.0.13.2 に切替
ping 8.8.8.8 source Loopback0                  ! backup(RT03→RT04) 経由で疎通（往復成立）
!
 interface Ethernet0/0
  no shutdown                                  ! 復旧 → track Up → primary 復帰
```
※ 自動実証は `ansible-playbook playbooks/verify_failover.yml -e problem=ENCOR-IPSLA-01`。

### トポロジ上のポイント（今回の改修）
- **8.8.8.8 は ISP 上ではなく独立した Internet コア (RT04) 上**にあり、primary(RT02) /
  backup(RT03) の **両方から到達可能**。よって RT02 がダウンしても backup 経由で 8.8.8.8 に届く
  ＝ 真の冗長。
- **戻り経路（ISP/Internet 側は事前設定）**: 各 ISP は顧客 RT01(Lo0=1.1.1.1) への戻りを
  「直結顧客リンク優先 + 障害時フローティング」で構成。primary リンクが落ちると RT02 の
  `1.1.1.1 via 10.0.12.1` は next-hop が解決不能になって取り下げられ、`1.1.1.1 via 10.0.23.2 (RT03) 200`
  が活性化 → 戻りも RT03 経由に迂回する。これで「切替後に戻りパケットが落ちる」事故を防ぐ。

### 設定上のポイント（落とし穴の解説）
- **`ip sla schedule 1 life forever start-time now` を忘れない**:
  `ip sla 1` だけだと SLA は定義されるが実行されない。schedule で初めてプローブが
  走り、track の状態が確定する。これを忘れると track の状態が Unknown のままで、
  primary 経路が一切インストールされない。
- **probe target は「primary 経路でしか到達できない先」にする**:
  ここでは RT02 の primary 側 IF (10.0.12.2) を狙う。primary リンクが落ちると
  この相手は直接到達不能となり、SLA が確実に失敗する。
  もし `8.8.8.8` 自体を target にすると、primary 障害時に経路が backup に切替わって
  プローブが backup 経由で成功してしまい、track が再度 Up → primary 再インストール
  → flap という事故が起きる。
- **track をスタティックに付ける位置**:
  `ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1` のように **行末** に書く。
  track が Down のときだけ、この経路が RIB から落ち、フローティング backup
  (AD=200) が活性化する。
- **backup の AD は必ず primary より大きく**:
  primary は static で AD=1。backup は `200` を指定してフローティングに。
  AD を指定しないと両方 AD=1 になり ECMP になってしまう。

> 採点: IP SLA 1 / Track 1 / Track 状態 Up / RIB に primary tracked static /
> フローティング backup 設定 / **RT01→8.8.8.8 の実疎通** / **RT03(backup ISP)→8.8.8.8 の実疎通**。
