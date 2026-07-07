# 模範解答 : ENCOR-IPSLA-02 (奥のビーコン + /32ピンで primary 全経路監視)

> RT01 のみ設定。RT02/RT03/RT04 は変更不可。

## RT01
```
! 1) 奥のビーコンを ICMP SLA で監視（送信元は primary IF のアドレス）
ip sla 1
 icmp-echo 100.64.0.1 source-ip 10.0.12.1
 frequency 5
ip sla schedule 1 life forever start-time now
!
! 2) ★ビーコン宛 /32 を primary next-hop に固定（プローブを primary に釘付け）
ip route 100.64.0.1 255.255.255.255 10.0.12.2
!
! 3) Track で SLA reachability を監視
track 1 ip sla 1 reachability
!
! 4) データ用 default：primary(track連動) ＋ backup(AD200 フローティング)
ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1
ip route 0.0.0.0 0.0.0.0 10.0.13.2 200
!
```

## 確認
```
show ip sla statistics 1            ! Return Code = OK
show track 1                        ! Reachability is Up
show ip route 0.0.0.0              ! 既定は 10.0.12.2(primary)
ping 100.64.0.1 source 10.0.12.1   ! ビーコン到達(primary経路)
ping 8.8.8.8 source Loopback0      ! Internet 到達
```

### ポイント（IPSLA-01 との違い・設計の肝）
- **near 監視の限界**: IPSLA-01 は隣の `10.0.12.2` を見るだけ。RT02↔Internet(奥)が切れても
  `10.0.12.2` は生きているので track は Up のまま → primary に張り付きブラックホール。
- **deep 監視**: 監視先を **primary 経路でしか届かない奥のビーコン `100.64.0.1`** にすると、
  primary 経路の *どこが* 切れてもプローブが失敗 → track Down → 切替。access も奥も検知できる。
- ★**/32 ピン (`100.64.0.1/32 → 10.0.12.2`) が必須**な理由は2つ:
  1. **循環参照を断つ**: ビーコン宛を default 任せにすると「track→default→ビーコン経路→SLA→track」
     が循環し、起動時 track Down のままデッドロックする。専用 /32 で経路を確定させる。
  2. **フラップ防止**: /32 で primary に固定し、かつ backup ISP はビーコン経路を持たないので、
     プローブは絶対に backup へ逃げない＝primary が生きてる時だけ成功する（誤復活しない）。
- **source = primary IF (10.0.12.1)**: 応答も primary 限定にして対称・確実にする
  （RT04 は 10.0.12.0/30 への戻りを primary 経由のみで持つ）。`8.8.8.8` は別途 Lo0 送信元で
  通すので、データのフェイルオーバとは独立。
- **ビーコンとデータ宛先は別物**にする: `8.8.8.8` 自体を /32 ピンするとデータまで primary に
  固定され切替が壊れる。監視専用ビーコンを分けるのが定石。
- 結果: primary 健全 → track Up → primary 既定(AD1) が backup(AD200)に優先。
  primary のどこか障害 → ビーコン不達 → track Down → primary 既定が外れ backup が昇格 →
  `8.8.8.8` は backup ISP 経由で継続。

> 採点: SLA(ビーコン/source)、★/32ピン、Track Up、primary既定、AD200 backup、
> ビーコン実到達、8.8.8.8 実到達で判定。奥障害の実証は verify_failover_deep.yml。
