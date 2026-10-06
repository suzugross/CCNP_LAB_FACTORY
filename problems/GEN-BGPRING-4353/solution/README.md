# 採点者専用 (GEN-BGPRING-4353)

- shape: **no_transit** / layout: four_as
- faults: ['no_transit:routemap']
- meta: {'company': 'RT04', 'isp': ['RT01', 'RT03'], 'far': 'RT02', 'solution': 'routemap'}
- AS: {'RT01': 65047, 'RT02': 65029, 'RT03': 64653, 'RT04': 64648}
- prefix: {'RT01': '172.16.23.0', 'RT02': '172.16.190.0', 'RT03': '172.16.123.0', 'RT04': '172.16.24.0'}
- 囮: [('unused_prefix_list', 'RT01')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
