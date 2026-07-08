# GEN-CHAIN-9800 解答（採点者用）

連鎖: L1:l1_eigrp_passive_west → L2:l2_rr_client_break → L3b:br_bgp_password → L3b:br_ospf2_area_mismatch

## L1: l1_eigrp_passive_west
RT01 の West アクセスIF が EIGRP passive (隣接不成立)

## L2: l2_rr_client_break
両RRで RT01/RT07/RT09 の route-reflector-client が外されている(非client同士は反射されず West↔East の経路交換が途絶)

## L3b: br_bgp_password
RT07 の両RRピアにだけ MD5 パスワード(セッション確立不能=RT07系統がBGPから消える)

## L3b: br_ospf2_area_mismatch
RT09 の East リンクが OSPF2 で area 2 に設定(正: area 0。hello の area 不一致で隣接不成立=RT09系統がOSPF2から消える)

## おとり（無害・修正不要）
- RT06: dc_unused_rmap（未適用/無影響の残骸。削除しなくても減点なし）
- RT02: dc_scary_neigh_desc（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
