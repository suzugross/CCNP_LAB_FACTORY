# M11 supplement — Practice 4: E-LAN

These are the tasks of lab **XRT-12**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XE1**, **XE2** and **XE3**. P1, the CEs and SW1 are fixed; do not change them. You may log in to them
  to look. The CEs and SW1 belong to the customer.
- The tasks give no command examples. Each task states the behaviour that is required. The reading pages have
  configuration examples; the ones that have the same form as a task's answer are folded. To solve a task on your own
  first, use the CLI help (`?`), the `show` commands, and the Cisco IOS XE configuration guides and command references
  to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. Give LDP and BGP half a minute to settle after a change.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XE1, XE2 and XE3 run **Catalyst 8000V** 17.15.1a with the boot licence level `network-advantage` (MPLS is
  available). IOS XE has no commit: each line takes effect when you enter it. P1 is an IOS XE 17.15 router.

## Topology

| Link | Ends | Addressing |
|---|---|---|
| CORE-1 | P1 Ethernet0/0 ─ XE1 GigabitEthernet1 | 10.0.41.0/24 (P1 .51, XE1 .41) |
| CORE-2 | P1 Ethernet0/1 ─ XE2 GigabitEthernet1 | 10.0.42.0/24 (P1 .51, XE2 .42) |
| CORE-3 | P1 Ethernet0/2 ─ XE3 GigabitEthernet1 | 10.0.43.0/24 (P1 .51, XE3 .43) |

| Router | Role | Platform | Loopback0 |
|---|---|---|---|
| P1 | Core, route reflector for EVPN | IOS XE 17.15 | 10.255.0.51/32 |
| XE1 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.41/32 |
| XE2 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.42/32 |
| XE3 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.43/32 |

| Customer C site | Attached to | Customer equipment |
|---|---|---|
| Site 1 | XE1 GigabitEthernet2 | CE1 (router) |
| Site 2 | XE2 GigabitEthernet2 | CE2 (router) |
| Site 3 | XE3 GigabitEthernet2 | CE3 (router) |
| Site 4 | XE1 GigabitEthernet3 and XE2 GigabitEthernet3 | SW1 (switch; one LACP bundle over both links) |

| Service | Site 1 | Site 2 | Site 3 | Site 4 | Customer addresses |
|---|---|---|---|---|---|
| E-LAN on VPLS (VPN ID 210) | VLAN 210 | VLAN 210 | VLAN 210 | — | 172.31.210.0/24 |
| E-LAN on EVPN (EVPN instance 200) | VLAN 200 | VLAN 200 | untagged | VLAN 200 | 172.31.200.0/24 |
| E-Line 130 (pseudowire 130) | VLAN 130 | — | VLAN 130 | — | 172.31.130.0/24 |

- The core runs the IS-IS instance `CORE` (level 2, wide metrics) and LDP on every core link. The BGP AS is 65000.
- P1 is the route reflector for the EVPN address family, with XE1, XE2 and XE3 already configured as its clients.
  The provider edges do not run BGP yet.
- The provider's site numbers: site 1 = **1**, site 2 = **2**, site 3 = **3**, site 4 = **4**. The customer's address at
  each site has the site number as its host part (for example 172.31.200.4 is SW1). Where a service needs an identifier
  for each end, the identifier of an end is the number of its site.
- E-Line 130 between site 1 and site 3 is in place and works.

## M11 supplement — E-LAN, multihoming and Ethernet OAM

### Task M11-6
<p class="tolab"><a href="/_learn?id=XRT-12&amp;step=m11t6">Open in the lab workspace</a> — Read: <a href="b7-m11-e-lan.html#s2-1">2.1 Bridge domains joined by a full mesh of pseudowires</a> · <a href="b7-m11-e-lan.html#s2-2">2.2 One frame at a time: CE1's ARP</a> · <a href="b7-m11-e-lan.html#s2-3">2.3 Split horizon: why the mesh must be full</a> · <a href="b7-m11-e-lan.html#s2-4">2.4 Configuring VPLS on IOS XE</a> · <a href="b7-m11-e-lan.html#s2-5">2.5 Reading the outputs, and what goes wrong</a></p>


Before the provider moved to EVPN, a colleague built customer C's E-LAN on VPLS (VPN ID 210, VLAN 210 at sites 1, 2
and 3). The customer says that site 3 has never reached any other site. Sites 1 and 2 reach each other.

- Make all three sites reach each other over this E-LAN (172.31.210.0/24).
- XE2's part of the E-LAN is correct; do not change it.

### Task M11-7
<p class="tolab"><a href="/_learn?id=XRT-12&amp;step=m11t7">Open in the lab workspace</a> — Read: <a href="b7-m11-e-lan.html#s3-1">3.1 MAC addresses in BGP: route type 2</a> · <a href="b7-m11-e-lan.html#s3-2">3.2 Broadcasts: route type 3 and ingress replication</a> · <a href="b7-m11-e-lan.html#s3-3">3.3 One frame at a time: CE1 to CE3</a> · <a href="b7-m11-e-lan.html#s3-4">3.4 Configuring EVPN's E-LAN on IOS XE</a> · <a href="b7-m11-e-lan.html#s3-5">3.5 Reading the outputs</a></p>


Customer C's new E-LAN runs on EVPN, in EVPN instance **200**, between sites 1, 2 and 3.

- Carry the customer's frames among sites 1, 2 and 3 as one LAN (172.31.200.0/24). At sites 1 and 2 the customer
  uses VLAN 200. At site 3 this E-LAN uses the customer's port without a VLAN tag; the other services on that port
  stay tagged.
- The provider edges learn each other's customer MAC addresses through BGP, and exchange their EVPN routes only
  through the route reflector P1. There must be no BGP session between two provider edges. The BGP router ID of each
  provider edge is its Loopback0 address.
- The core carries no multicast: the provider edge that receives a broadcast frame from a customer sends one copy to
  each other provider edge of the E-LAN.
