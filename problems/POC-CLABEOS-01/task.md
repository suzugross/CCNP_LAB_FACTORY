# [PoC] containerlab 単独 Arista cEOS × FRR OSPF

> containerlab だけで回す問題の基盤(cEOS の取り込み)の確かめ用です(出題用ではありません)。

## トポロジ

```
EOS1 Ethernet1 ── eth1 FRR1
        10.0.14.0/30
```

FRR1 は設定済みです。変更しないでください。

## 接続

```
scripts/lab.sh connect POC-CLABEOS-01 EOS1   # = ssh admin@172.20.20.21(パスワード admin・ログイン後に enable)
scripts/lab.sh connect POC-CLABEOS-01 FRR1   # vtysh(確認用・ssh admin@172.20.20.22 でも可。パスワード admin)
```

## 要件

1. EOS1 の Ethernet1 をルーテッド ポートにし、10.0.14.1/30 を設定してください。Loopback0 に 192.168.0.4/32 を設定してください。
2. EOS1 で IP ルーティングを有効にし、OSPF を router-id 192.168.0.4 で設定して、Ethernet1 と Loopback0 を area 0 に収容してください。Loopback0 は passive にしてください。
3. EOS1 の Loopback0 から FRR1 の lo(192.168.0.3)へ ping が通ることを確認してください。
