# 採点者専用 (GEN-BGPRING-34933)

- shape: **path_select** / layout: four_as
- faults: ['path_select:prepend_wrong_nbr']
- meta: {'A': 'RT02', 'B': 'RT04', 'P': 'RT03', 'S': 'RT01', 'fwd_mech': 'lp'}
- AS: {'RT01': 64512, 'RT02': 64990, 'RT03': 65285, 'RT04': 64981}
- prefix: {'RT01': '172.16.225.0', 'RT02': '172.16.138.0', 'RT03': '172.16.130.0', 'RT04': '172.16.72.0'}
- 囮: [('legacy_comment', 'RT02')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
