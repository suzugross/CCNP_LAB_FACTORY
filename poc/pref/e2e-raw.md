

# E2E 実行 2026-08-16 12:02:24 — cases=['e_fc_strict', 'e_variance_bound', 'e_variance_nonfc', 'e_fs_allthat', 'o_type_e1e2', 'o_e2_fwd', 'o_e1_accum']

## e_fc_strict (kind=fc_strict world=w_variance_cap)
- ① all-links → **一致**
- ① topology(既定) → **一致**
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3'] / モデル ['10.20.12.2', '10.20.13.3'] → 一致

## e_variance_bound (kind=variance_bound world=w_target_only)
- ① all-links → **一致**
- ① topology(既定) → **一致**
- ③ variance 2 適用後の搭載= 実機 ['10.20.12.2', '10.20.14.4'] / モデル ['10.20.12.2', '10.20.14.4'] → 一致

## e_variance_nonfc (kind=variance_nonfc world=w_target_only)
- ① all-links → **一致**
- ① topology(既定) → **一致**
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3'] / モデル ['10.20.12.2', '10.20.13.3'] → 一致

## e_fs_allthat (kind=fs_allthat world=w_variance_cap)
- ① all-links → **一致**
- ① topology(既定) → **一致**
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3', '10.20.14.4'] / モデル ['10.20.12.2', '10.20.13.3', '10.20.14.4'] → 一致

## o_type_e1e2 (kind=type_e1e2 world=w_target_only)
- **失敗**: KeyError: 'RO3'

## o_e2_fwd (kind=e2_fwd world=w_local_only)
- **失敗**: KeyError: 'RO3'

## o_e1_accum (kind=e1_accum world=w_local_only)
- **失敗**: KeyError: 'RO3'


# E2E 実行 2026-08-16 12:10:26 — cases=['o_type_e1e2', 'o_e2_fwd', 'o_e1_accum']

## o_type_e1e2 (kind=type_e1e2 world=w_target_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  - 実機　: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  → 一致
- ② 勝者の next-hop= 実機 10.10.12.2 / モデル 10.10.12.2 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → 一致

## o_e2_fwd (kind=e2_fwd world=w_local_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 50, type extern 2, forward metric 30`
  - 実機　: `  Known via "ospf 1", distance 110, metric 50, type extern 2, forward metric 30`
  → 一致
- ② 勝者の next-hop= 実機 10.10.13.3 / モデル 10.10.13.3 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → 一致

## o_e1_accum (kind=e1_accum world=w_local_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  - 実機　: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  → 一致
- ② 勝者の next-hop= 実機 10.10.12.2 / モデル 10.10.12.2 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → 一致
