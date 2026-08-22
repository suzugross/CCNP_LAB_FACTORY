# 採点者専用 (GEN-BGPRING-40365)

- shape: **path_select** / layout: four_as
- faults: ['path_select:med_acm_missing']
- meta: {'A': 'RT04', 'B': 'RT02', 'P': 'RT01', 'S': 'RT03', 'fwd_mech': 'med'}
- AS: {'RT01': 65440, 'RT02': 64635, 'RT03': 65221, 'RT04': 64576}
- prefix: {'RT01': '172.16.121.0', 'RT02': '172.16.210.0', 'RT03': '172.16.60.0', 'RT04': '172.16.217.0'}
- 囮: [('unused_prefix_list', 'RT02')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
