# 採点者専用 (GEN-BGPRING-63224)

- shape: **no_transit** / layout: four_as
- faults: ['no_transit:aspath']
- meta: {'company': 'RT01', 'isp': ['RT02', 'RT04'], 'far': 'RT03', 'solution': 'aspath'}
- AS: {'RT01': 64553, 'RT02': 64694, 'RT03': 65079, 'RT04': 65190}
- prefix: {'RT01': '172.16.177.0', 'RT02': '172.16.106.0', 'RT03': '172.16.47.0', 'RT04': '172.16.134.0'}
- 囮: [('unused_prefix_list', 'RT01')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
