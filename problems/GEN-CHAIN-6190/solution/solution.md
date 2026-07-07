# GEN-CHAIN-6190 解答（採点者用）

連鎖: L1:l1_mtu_mismatch → L2:l2_activate_missing → L3:l3_b2e_metric_missing

## L1: l1_mtu_mismatch
RT01 側 West アクセスIF に ip mtu 1400 (EXSTART 固着)

## L2: l2_activate_missing
RT01 の急所ピア(RT03/RT04)が address-family ipv4 で activate されていない(セッションUPなのに経路ゼロ)

## L3: l3_b2e_metric_missing
両境界の EIGRP に default-metric が無い(BGP→EIGRP 再配送が経路を注入しない=戻り不在)

## おとり（無害・修正不要）
- RT02: dc_quarantine_pl（未適用/無影響の残骸。削除しなくても減点なし）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
