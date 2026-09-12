# 採点者専用 (GEN-BGPRING-51979)

- shape: **no_transit** / layout: four_as
- faults: ['no_transit:routemap']
- meta: {'company': 'RT02', 'isp': ['RT03', 'RT01'], 'far': 'RT04', 'solution': 'routemap'}
- AS: {'RT01': 64958, 'RT02': 64966, 'RT03': 65333, 'RT04': 64791}
- prefix: {'RT01': '172.16.137.0', 'RT02': '172.16.180.0', 'RT03': '172.16.243.0', 'RT04': '172.16.242.0'}
- 囮: [('unused_prefix_list', 'RT01')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
