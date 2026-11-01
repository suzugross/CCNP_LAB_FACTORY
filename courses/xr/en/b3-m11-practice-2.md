# M11 — Practice 2: EVPN-VPWS

These are the tasks of lab **XRT-11**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M11 — L2VPN and Carrier Ethernet

### Task M11-3
<p class="tolab"><a href="/_learn?id=XRT-11&amp;step=m11t3">Open in the lab workspace</a> — Read: <a href="b2-m11-evpn-vpws.html#s2-1">2.1 The EVI and the AC identifiers</a> · <a href="b2-m11-evpn-vpws.html#s2-2">2.2 The route it carries: type 1</a> · <a href="b2-m11-evpn-vpws.html#s2-4">2.4 The route reflector carries it</a> · <a href="b2-m11-evpn-vpws.html#s3-1">3.1 Where the configuration goes</a> · <a href="b2-m11-evpn-vpws.html#s3-2">3.2 Reading the state</a></p>


Customer B has opened site 3, attached to the new provider edge XR03. XR03 has joined the core and has no other
configuration.

- Build an E-Line between CEB1 on VLAN 400 and CEB3 on VLAN 40. The CEs use 172.31.40.0/24 on it.
- Build it with EVPN (EVPN-VPWS), in EVPN instance **400**. The identifier of each end follows the site numbers.
- XR01 and XR03 exchange their EVPN routes only through the route reflector XR02. There must be no BGP session between
  XR01 and XR03. The BGP router ID of XR03 is its Loopback0 address.

### Task M11-4
<p class="tolab"><a href="/_learn?id=XRT-11&amp;step=m11t4">Open in the lab workspace</a> — Read: <a href="b2-m11-evpn-vpws.html#s2-1">2.1 The EVI and the AC identifiers</a> · <a href="b2-m11-evpn-vpws.html#s2-5">2.5 MTU and the control word</a> · <a href="b2-m11-evpn-vpws.html#s3-3">3.3 Down, or up but not passing traffic</a></p>


With change CHG-1411, the colleague also built two more E-Lines between site 1 and site 3 with EVPN-VPWS, in EVPN
instances 410 and 420. The customer says that neither of them carries any traffic.

- Make both E-Lines work. The CEs use 172.31.41.0/24 (VLAN 410 at site 1, VLAN 41 at site 3) and 172.31.42.0/24
  (VLAN 420 at site 1, VLAN 42 at site 3).
- Where the configuration does not follow the provider's conventions, bring it in line with them.
