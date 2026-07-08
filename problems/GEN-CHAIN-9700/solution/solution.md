# GEN-CHAIN-9700 解答（採点者用）

連鎖: L1:l1_eigrp_passive_west → L2:l2_activate_missing → L3:l3_e2b_filter_gone

## L1: l1_eigrp_passive_west
RT01 の West アクセスIF が EIGRP passive (隣接不成立)

## L2: l2_activate_missing
RT01 の急所ピア(RT07/RT09)が address-family ipv4 で activate されていない(セッションUPなのに経路ゼロ)

## L3: l3_e2b_filter_gone
両境界の PL-EAST から 172.21.1.0/24 が漏れている(East LAN2 が BGP に乗らない)

## おとり（無害・修正不要）
- RT02: dc_quarantine_pl（未適用/無影響の残骸。削除しなくても減点なし）
- RT11: dc_snmp_note（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
