# 模範解答 : ENCOR-VACL-02

設定するのは **SW01 のみ**。

```
ip access-list extended MATCH-1-3
 permit ip host 192.168.10.1 host 192.168.10.3
 permit ip host 192.168.10.3 host 192.168.10.1
!
vlan access-map BLOCK-1-3 10
 match ip address MATCH-1-3
 action drop
vlan access-map BLOCK-1-3 20
 action forward
!
vlan filter BLOCK-1-3 vlan-list 10
```

## 確認（受験者の疎通テスト）
```
! RT01
ping 192.168.10.3      → 失敗 (VACL で drop)
ping 192.168.10.2      → 成功
! RT02
ping 192.168.10.3      → 成功 (1-3 ペア以外は forward)
```

## ポイント（落とし穴の解説）
- **双方向**: VACL の match は方向を持つ ACE で評価される。1→3 と 3→1 の両方を ACL に
  入れないと片方向しか落ちない。`permit ip host A host B` と `permit ip host B host A` の
  2 行、または `permit ip host A host B`＋ホスト逆も忘れずに。
- **ACL は分類**: drop したい通信を ACL で **permit**（マッチさせる）→ map の action=drop。
- **末尾 forward**: seq 20 の `action forward`（match 無し=全マッチ）を置かないと、暗黙の
  drop で VLAN10 内の全通信が落ちる（RT01⇔RT02 等も巻き込む）。
- **L2 内なので VACL**: RT01 と RT03 は同一サブネット（同一 VLAN）にいるため、ルータの
  インタフェース ACL では止められない（L3 を経由しない）。VLAN 内に作用する VACL が適切。
- **混在イメージ**: VACL は iosvl2 必須、エンドポイント RT は軽量 iol-xe。
  problem.yml の node_image_families でノード単位にイメージを指定している。
