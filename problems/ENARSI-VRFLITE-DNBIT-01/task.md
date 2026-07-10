# 問題 ENARSI-VRFLITE-DNBIT-01 : VRF-Lite で対向サイトに届かない（難易度4）

## シナリオ
ある企業は、社内の隔離セグメント **RED** を VRF-Lite（マルチVRF）で WAN 越しに延ばしています。
経路は次の流れで運ばれます。

```
 [Site A サーバ網]                                         [Site B サーバ網]
  172.20.20.0/24                                            172.30.30.0/24
      │                                                          │
     RT01 ──(RED / eBGP)── RT02 ──(RED / OSPF area0)── RT03 ─────┘
   (RED境界・起点)      (RED中継・eBGP受信を          (Site B 収容・VRF RED OSPF)
                         OSPFへ再配布)
```

- **RT01** は Site A 網 172.20.20.0/24 を **eBGP** で RT02 へ渡す。
- **RT02** はそれを受け、**VRF RED の OSPF に再配布**して RED ドメインへ流す。
  併せて Site B 網 172.30.30.0/24 を OSPF→eBGP で RT01 へ返している。
- **RT03** は Site B(172.30.30.0/24) を収容し、VRF RED の OSPF で RT02 と隣接している。

## 申告（NOC チケット）

> **Site B から Site A のサーバ(172.20.20.0/24)へ全く到達できない。**
> ただし：
> - RT03 と RT02 の **OSPF 隣接は FULL** で正常。
> - Site B 網は他拠点からは到達できている（＝ RT03 の広告は生きている）。
> - RT02 では Site A 網 172.20.20.0/24 は**ちゃんと見えている**。
>
> **RT03 側で是正し、Site B から Site A へ到達できるようにせよ。**

## 是正の要件（この状態にすること）

1. **RT03 の VRF RED ルーティングテーブルに 172.20.20.0/24 が載る**こと。
2. **RT03 から Site A へ疎通**すること（`ping vrf RED 172.20.20.20 source 172.30.30.30` 成功）。
3. Site B の広告・RT02 との OSPF 隣接など、既存の正常部分を壊さないこと。

## 診断のヒント
- OSPF 隣接は FULL、RT02 には経路がある、なのに RT03 に届かない。
  → RT03 で **172.20.20.0/24 が「OSPF データベースには在るのに、ルーティングテーブルには無い」**
    状態になっていないか確認せよ（`show ip ospf 10 database external ...` と
    `show ip route vrf RED ...` を見比べる）。データベースに在るのに RIB に載らないのには理由がある。

## 制約
- **操作してよいのは RT03 のみ**。RT01 / RT02 は変更禁止。
- **スタティックルートは使用しないこと**（172.20.20.0/24 は OSPF 経路として載せること）。
- 管理用 VRF `MGMT` と Ethernet0/3 には触れないこと。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-VRFLITE-DNBIT-01 \
  --vault-password-file <(printf 'CCNP\n')
```
