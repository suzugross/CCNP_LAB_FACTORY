# 採点者専用 (GEN-BGPRING-48328)

- shape: **isp_exchange** / layout: split_company
- faults: ['isp_exchange:allowas_full']
- meta: {'variant': 'allowas_full', 'company': ['RT02', 'RT04'], 'isp': ['RT03', 'RT01']}
- AS: {'RT01': 65349, 'RT02': 65263, 'RT03': 65189, 'RT04': 65263}
- prefix: {'RT01': '172.16.42.0', 'RT02': '172.16.123.0', 'RT03': '172.16.225.0', 'RT04': '172.16.70.0'}
- 囮: [('unused_route_map', 'RT01')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
