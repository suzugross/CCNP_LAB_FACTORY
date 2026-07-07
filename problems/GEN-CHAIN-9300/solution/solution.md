# GEN-CHAIN-9300 解答（採点者用）

連鎖: L1:l1_area_mismatch → L2:l2_password_mismatch → L3b:br_bgp_password → L3b:br_eigrp_as_mismatch

## L1: l1_area_mismatch
RT01 の West アクセスIF が area 2 で設定されている(正: area 1)

## L2: l2_password_mismatch
RT01 の急所ピア(RT03/RT04)にだけ MD5 パスワード(相手側は無し→セッション不成立)

## L3b: br_bgp_password
RT07 の両RRピアにだけ MD5 パスワード(セッション確立不能=RT07系統がBGPから消える)

## L3b: br_eigrp_as_mismatch
RT09 の EIGRP が AS 65101 で設定(正: 65100。隣接不成立=RT09系統がEIGRPから消える)

## おとり（無害・修正不要）
- RT02: dc_scary_neigh_desc（未適用/無影響の残骸。削除しなくても減点なし）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
