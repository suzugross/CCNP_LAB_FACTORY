# 解答・解説 ENCOR-PBR-01 (送信元別の経路振り分け)

## 核心
通常のルーティングは「宛先」だけで経路を決めるため、同じ宛先 `3.3.3.3` への通信を
「送信元」で振り分けることはできない。**PBR (Policy-Based Routing)** を使うと宛先以外の
条件（ここでは送信元アドレス）でネクストホップを上書きできる。

RT01 自身が生成するトラフィック（Lo1/Lo2 を送信元とする ping/traceroute 等）に
ポリシーを効かせるには **`ip local policy route-map`** を使う（インタフェース通過の
中継トラフィックなら `ip policy route-map` を入力 IF に適用）。本問は送信元が RT01 上の
Loopback なので **local policy** が正解。

## RT01 設定例
```
ip access-list extended DEV-TRAFFIC
 permit ip host 10.2.2.1 host 3.3.3.3
!
route-map PBR-DEV permit 10
 match ip address DEV-TRAFFIC
 set ip next-hop 10.0.12.2
!
ip local policy route-map PBR-DEV
```

- `match ip address DEV-TRAFFIC` … 開発部(10.2.2.1)発・DC(3.3.3.3)宛だけを分類。
  `permit ip host 10.2.2.1 any` でも可（採点は 10.2.2.x を対象にしていれば許容）。
- `set ip next-hop 10.0.12.2` … RT02 の直結 IP。これにより最短(直結 RT03=10.0.13.2)を
  上書きして RT02 経由に。
- route-map に該当しないトラフィック（営業部 10.1.1.1 発など）は通常ルーティング＝
  最短の RT03 直結のまま流れる。route-map の末尾は暗黙の deny だが、PBR では
  「マッチしない＝通常ルーティング」になるので営業部は影響を受けない。

## 動作確認
```
RT01# traceroute 3.3.3.3 source Loopback2 numeric   ! 開発部 → hop1 = 10.0.12.2 (RT02経由)
RT01# traceroute 3.3.3.3 source Loopback1 numeric   ! 営業部 → hop1 = 10.0.13.2 (RT03直結)
RT01# show route-map                                ! Policy routing matches がカウントされる
RT01# show ip policy                                ! local policy の適用先 route-map を表示
```

## 落とし穴
- **`set ip next-hop` のネクストホップは直結(連続している)アドレス**にする。10.0.12.2 は
  RT01-RT02 の直結なので有効。到達不能な next-hop を指定すると PBR が不発で通常経路に落ちる。
- ACL の宛先を `any` にすると 3.3.3.3 以外の開発部通信もすべて RT02 経由になる。本問は
  到達目標を満たせば可だが、要件に忠実なら `host 3.3.3.3` 限定が綺麗。
- `ip policy`(IF 入力用) と `ip local policy`(自装置生成用) を取り違えると、RT01 自身の
  traceroute には効かない。本問は送信元が RT01 上の Loopback なので **local policy**。
- スタティックで `ip route 3.3.3.3 ... 10.0.12.2` のように最短路自体を書き換えるのは
  制約違反（営業部も巻き込まれ、PBR の学習意図からも外れる）。

## 採点 (計100)
| 配点 | 確認 |
|------|------|
| 30 | 開発部(Lo2)発 traceroute の hop1 が 10.0.12.2・10.0.13.2 を通らない（実経路で RT02 経由） |
| 15 | 営業部(Lo1)発 traceroute が 10.0.13.2 直結のまま・10.0.12.2 を通らない |
| 20 | route-map が ACL マッチ + `set ip next-hop 10.0.12.2` |
| 15 | `ip local policy route-map` 適用 |
| 10 | マッチ ACL が 10.2.2.x を対象 |
| 10 | 3.3.3.3/32 を OSPF で学習（到達性維持） |
