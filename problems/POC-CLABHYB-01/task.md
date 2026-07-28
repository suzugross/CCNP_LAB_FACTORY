# [PoC] CML×containerlab 複合ラボ — OSPF マルチベンダ interop

> これは出題用の問題ではなく、CML(IOL×2)と containerlab(vJunos EVO)を
> LAN-IX 境界で L2 接続し、構築→採点→撤収パイプラインを実証する PoC です。

## 構成

```
RT02 ──── RT01 ──── [LAN-IX] ══ L2 ══ JUN01 (vJunos EVO / containerlab)
2.2.2.2   1.1.1.1              10.0.12.1/30, lo0 192.168.0.1/24
   10.77.12.0/30   10.0.12.0/30        全て OSPF area 0
```

## 確認項目(=採点チェック)

1. RT01 が JUN01 と FULL 隣接(境界越しマルチベンダ隣接)
2. RT02 が JUN01 の lo0 (192.168.0.0/24) を OSPF 学習
3. JUN01 側から見ても RT01 と Full(Junos JSON 採点パスの実証)
4. RT02 lo0 → JUN01 lo0 の E2E ping
