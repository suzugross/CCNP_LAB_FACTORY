# 模範解答 : ENCOR-OSPF-AUTH-01

両端のインタフェースに `ip ospf authentication message-digest` と
`ip ospf message-digest-key 1 md5 ENCOR2026` を入れる。インタフェース単位なので
4 か所 (RT01 Eth0/0、RT02 Eth0/0、RT02 Eth0/1、RT03 Eth0/0) すべてに必要。

## RT01
```
interface Ethernet0/0
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 ENCOR2026
!
```

## RT02
```
interface Ethernet0/0
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 ENCOR2026
!
interface Ethernet0/1
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 ENCOR2026
!
```

## RT03
```
interface Ethernet0/0
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 ENCOR2026
!
```

## 確認
```
show ip ospf neighbor                          ! 全隣接 FULL
show ip ospf interface Ethernet0/0 | include authentication
show running-config interface Ethernet0/0 | section ospf
```

### ポイント（落とし穴の解説）
- **両端で 3 つすべて一致が必要**: 認証タイプ (message-digest)、Key ID (1)、Key string (ENCOR2026)。
  どれか一つでもズレると Hello 認証で弾かれ、隣接は INIT/EXSTART で止まる。
- **インタフェース vs area**: area 0 全体に `area 0 authentication message-digest` を
  入れる手もあるが、本問は「インタフェース単位」を要件で指定。両者は同じ効果でも
  設定スコープが異なる（インタフェース指定の方が後勝ち / 細粒度）。
- **Key ID が一致しないと FULL にならない**: 両端で Key ID をうっかり別の数字に
  すると、たとえ key string が同じでも認証失敗。
- **MD5 鍵は running-config では暗号化表示**: `show run` で `message-digest-key 1 md5 7 <hex>`
  と表示される（実値は隠蔽）。プレーン文字列で grep しても見つからないので注意。
- **片側だけ先に入れたら隣接が一時的に落ちる**: 段取り上、両端を同じセッションで
  素早く投入するか、認証→隣接再構築の数秒のフラップを許容する。

> 採点: RT02 の 2 つのリンク IF に `ip ospf authentication message-digest` と
> `message-digest-key 1 md5` が存在し、両隣接が FULL であることを判定。
> RT01 / RT03 側も同じ設定が無いと隣接が落ちるので、間接的に検証される。

## 変種 "bfd"（-e variant=bfd）の追加解答
MD5 認証に加え、両リンクの IF に BFD を設定し OSPF と連動させる。

```
! RT02（両リンク。RT01/RT03 は自リンク側 IF のみ）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
 ip ospf bfd
interface Ethernet0/1
 bfd interval 500 min_rx 500 multiplier 3
 ip ospf bfd
```

> `router ospf 1` 配下 `bfd all-interfaces` でも可（採点は効果ベース）。
> 確認: `show bfd neighbors details`（State Up / Registered protocols: OSPF）
