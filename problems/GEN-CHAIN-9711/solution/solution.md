# GEN-CHAIN-9711 解答（採点者用）

連鎖: L1:l1_ospf_auth → L2:l2_rr_client_break → L3:l3_redist_internal_missing

## L1: l1_ospf_auth
RT11 側 West アクセスIF のみ OSPF MD5 認証が有効(RT01側は無し)

## L2: l2_rr_client_break
両RRで RT01/RT07/RT09 の route-reflector-client が外されている(非client同士は反射されず West↔East の経路交換が途絶)

## L3: l3_redist_internal_missing
両境界の BGP に bgp redistribute-internal が無い(IOS既定=iBGP経路はIGPへ再配送されない→East に West の戻り経路が皆無)

## おとり（無害・修正不要）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）
- RT06: dc_unused_rmap（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
