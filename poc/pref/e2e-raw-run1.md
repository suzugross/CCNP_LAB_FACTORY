

# E2E 実行 2026-08-16 11:53:52 — cases=['e_fc_strict', 'e_variance_bound', 'e_variance_nonfc', 'e_fs_allthat', 'o_type_e1e2', 'o_e2_fwd', 'o_e1_accum']

## e_fc_strict (kind=fc_strict world=w_variance_cap)
- ① all-links → **一致**
- ① topology(既定) → **一致**
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3'] / モデル ['10.20.12.2', '10.20.13.3'] → 一致

## e_variance_bound (kind=variance_bound world=w_target_only)
- ① all-links → ★**不一致**

  モデル(紙面レンダラ):
```
P 10.99.9.0/24, 1 successors, FD is 448000
        via 10.20.12.2 (448000/409600), Ethernet0/0
        via 10.20.14.4 (729600/409600), Ethernet0/2
        via 10.20.13.3 (934400/409600), Ethernet0/1
```

  実機:
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (448000/409600), Ethernet0/0
        via 10.20.13.3 (934400/409600), Ethernet0/1
        via 10.20.14.4 (755200/435200), Ethernet0/2
```
- ① topology(既定) → ★**不一致**

  モデル(紙面レンダラ):
```
P 10.99.9.0/24, 1 successors, FD is 448000
        via 10.20.12.2 (448000/409600), Ethernet0/0
        via 10.20.14.4 (729600/409600), Ethernet0/2
        via 10.20.13.3 (934400/409600), Ethernet0/1
```

  実機:
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (448000/409600), Ethernet0/0
        via 10.20.13.3 (934400/409600), Ethernet0/1
        via 10.20.14.4 (729600/409600), Ethernet0/2
```
- ③ variance 2 適用後の搭載= 実機 ['10.20.12.2', '10.20.14.4'] / モデル ['10.20.12.2', '10.20.14.4'] → 一致

## e_variance_nonfc (kind=variance_nonfc world=w_target_only)
- ① all-links → ★**不一致**

  モデル(紙面レンダラ):
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (473600/409600), Ethernet0/1
        via 10.20.14.4 (492800/454400), Ethernet0/2
```

  実機:
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.14.4 (448000/409600), Ethernet0/2
        via 10.20.13.3 (473600/409600), Ethernet0/1
```
- ① topology(既定) → **一致**
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3'] / モデル ['10.20.12.2', '10.20.13.3'] → 一致

## e_fs_allthat (kind=fs_allthat world=w_variance_cap)
- ① all-links → ★**不一致**

  モデル(紙面レンダラ):
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.16.6 (473600/448000), Ethernet0/3
        via 10.20.14.4 (491520/414720), Ethernet0/2
        via 10.20.13.3 (499200/409600), Ethernet0/1
```

  実機:
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.16.6 (473600/448000), Ethernet0/3
        via 10.20.13.3 (499200/409600), Ethernet0/1
        via 10.20.14.4 (491520/414720), Ethernet0/2
```
- ① topology(既定) → ★**不一致**

  モデル(紙面レンダラ):
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.14.4 (491520/414720), Ethernet0/2
        via 10.20.13.3 (499200/409600), Ethernet0/1
```

  実機:
```
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (499200/409600), Ethernet0/1
        via 10.20.14.4 (491520/414720), Ethernet0/2
```
- ③ variance 3 適用後の搭載= 実機 ['10.20.12.2', '10.20.13.3', '10.20.14.4'] / モデル ['10.20.12.2', '10.20.13.3', '10.20.14.4'] → 一致

## o_type_e1e2 (kind=type_e1e2 world=w_target_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  - 実機　: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  → 一致
- ② 勝者の next-hop= 実機 10.10.12.2 / モデル 10.10.12.2 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → ★不一致

  モデル:
```
i 2.2.2.2 [10] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [30] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
```

  実機:
```
i 2.2.2.2 [10] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [30] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
i 5.5.5.5 [100] via 10.10.15.5, Ethernet0/2, ASBR, Area 0, SPF <n>
```

## o_e2_fwd (kind=e2_fwd world=w_local_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 50, type extern 2, forward metric 30`
  - 実機　: `  Known via "ospf 1", distance 110, metric 50, type extern 2, forward metric 30`
  → 一致
- ② 勝者の next-hop= 実機 10.10.13.3 / モデル 10.10.13.3 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → ★不一致

  モデル:
```
i 2.2.2.2 [50] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [30] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
```

  実機:
```
i 2.2.2.2 [50] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [30] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
i 5.5.5.5 [100] via 10.10.15.5, Ethernet0/2, ASBR, Area 0, SPF <n>
```

## o_e1_accum (kind=e1_accum world=w_local_only)
- ① detail 行
  - モデル: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  - 実機　: `  Known via "ospf 1", distance 110, metric 60, type extern 1`
  → 一致
- ② 勝者の next-hop= 実機 10.10.12.2 / モデル 10.10.12.2 → 一致
- ③ 外部 LSA の主要欄 → 一致
- ④ border-routers 行 → ★不一致

  モデル:
```
i 2.2.2.2 [40] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [50] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
```

  実機:
```
i 2.2.2.2 [40] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF <n>
i 3.3.3.3 [50] via 10.10.13.3, Ethernet0/1, ASBR, Area 0, SPF <n>
i 5.5.5.5 [100] via 10.10.15.5, Ethernet0/2, ASBR, Area 0, SPF <n>
```
