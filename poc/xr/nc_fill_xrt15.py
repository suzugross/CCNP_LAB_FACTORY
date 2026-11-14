#!/usr/bin/env python3
"""E2E 用: XRT-15 の NETCONF の雛形(~/m13/nc_edit.py)を模範解(learn.yml の solution)で埋めて標準出力へ。usage: nc_fill_xrt15.py <雛形> <ユーザ> <パスワード>"""
import sys, re
p, user, pw = sys.argv[1:4]
s = open(p).read()
s = re.sub(r'#\s*__FILL__', '#', s).replace('HOST = "__FILL__"', 'HOST = "10.0.50.1"').replace('PORT = 0 ', 'PORT = 830 ')
s = s.replace('USER = "__FILL__"', f'USER = "{user}"').replace('PASS = "__FILL__"', f'PASS = "{pw}"')
s = s.replace('FILTER = """\n__FILL__\n"""', 'FILTER = """<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg"><interface><interface-name>Loopback100</interface-name></interface></interfaces>"""')
s = s.replace('<config>\n__FILL__\n</config>', '''<config><interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg"><interface>
 <interface-name>Loopback100</interface-name><description>NMS-MANAGED</description>
 <ipv4><addresses xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-if-ip-address-cfg"><address><address>10.255.100.1</address><netmask>255.255.255.255</netmask></address></addresses></ipv4>
</interface></interfaces></config>''')
s = s.replace('edit_config(target="__FILL__"', 'edit_config(target="candidate"').replace('m.__FILL__()', 'm.commit()')
assert "__FILL__" not in s.split('"""', 2)[2], "unfilled"
print(s)
