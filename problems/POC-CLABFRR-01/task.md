# [PoC] containerlab 単独 Junos × FRR OSPF

> containerlab だけで回す問題の基盤(FRR の取り込み)の確かめ用です(出題用ではありません)。

## トポロジ

```
JUN01 et-0/0/0 ── eth1 FRR1
        10.0.13.0/30
```

FRR1 は設定済みです。変更しないでください。

## 接続

```
scripts/lab.sh connect POC-CLABFRR-01 JUN01   # = ssh admin@172.20.20.11
scripts/lab.sh connect POC-CLABFRR-01 FRR1    # vtysh(確認用・ssh admin@172.20.20.12 でも可。パスワード admin)
```

## 要件

1. JUN01 の et-0/0/0.0 に 10.0.13.1/30、lo0.0 に 192.168.0.1/32 を設定してください。
2. JUN01 で OSPF area 0 を有効にし、et-0/0/0.0 と lo0.0 を収容してください。lo0.0 は passive にしてください。
3. JUN01 の lo0 から FRR1 の lo(192.168.0.3)へ ping が通ることを確認してください。
