# 模範解答 : GEN-REDISTLOOP-6601(variant=filter_ospf)

## なぜ壊れるか(再配送リングのループ)
`192.168.51.0/24` は RE が **BGP** で起点広告し、RC が **iBGP(AD 200)** で学習する。
再配送が **BGP → EIGRP → OSPF** のリングを成すため、この経路の出自がドメインを一周して RC に戻る。
戻ってきた経路は **OSPF 外部(O E2・AD 110)** で、その **AD が iBGP(200)より低い**ため RC はそれを優先し、
`192.168.51.0/24` 宛を OSPF 側へ転送してしまう → **RC → RB → RA → RC** の定常転送ループ。

RC は RIB 勝者プロトコルを再配送源にするので、BGP だけでなく戻り側 IGP も EIGRP へ再配送して
P を常時循環させている(＝振動でなく定常ループに固定)。

## 解(RC・管理距離は使わない)
戻ってきた `192.168.51.0/24`(**OSPF 外部(O E2・AD 110)**)を、**RC の経路表に載らないようフィルタ**する。
プレフィックスリストで当該プレフィックスだけを OSPF 学習(`distribute-list ... in`)で遮断すると、
RC はそれを RIB に入れず **iBGP(起点 RE 方向)** を採用する。OSPF の LSDB は無傷なので **RB 側の
到達性は維持**される(distance には一切触れない)。

```
ip prefix-list DENY_FEEDBACK seq 5 deny 192.168.51.0/24
ip prefix-list DENY_FEEDBACK seq 10 permit 0.0.0.0/0 le 32
!
router ospf 1
 distribute-list prefix DENY_FEEDBACK in
```

### ★変更後は経路の再計算
`distribute-list in` 追加後、`clear ip route *`(RC)で反映する。

## 確認
- RC: `show ip route 192.168.51.0` が **`Known via "bgp 65000"`**(`ospf 1` ではない)。
  `distance` は 200 のまま(変えていない)。
- RC/RB/RA から `traceroute 192.168.51.1` が **RE に一直線**(3台を回らない)。

## 別解(いずれも distance を使わない・効果ベース採点)
- 拡張 ACL ベースの `distribute-list <acl> in`、または OSPF 学習側 `route-map`(match tag)で
  自ドメイン発の戻りを遮断。**経路タグ**方式(BGP→EIGRP 注入時に `set tag`、戻りをタグで遮断)も可だが
  タグが再配送を跨いで伝播することの確認が要る(本問の実機では prefix-list の方が確実)。
- **不可**: `distance` 系の使用(監査ポリシー違反)、いずれかの再配送の丸ごと削除、静的経路での回避。

## 教育核心(Ping-t #28776 型)
- 多点再配送がドメインをまたいで **リング**を成すと、経路の出自が一周して戻る。戻り経路の AD が
  元の学習元より低いとループ/振動する。
- 既定 AD(eBGP 20・EIGRP内部 90・OSPF 110・EIGRP外部 170・**iBGP 200**)の並びは必修。
  **iBGP は最も信用されない(200)** ため、iBGP 経路を IGP へ再配送するとこの罠を踏みやすい。
