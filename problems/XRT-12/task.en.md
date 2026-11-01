# XR Track 12 — E-LAN, Multihoming and Ethernet OAM (IOS XE)

This lab is the practice part of the supplement to unit **M11 L2VPN and Carrier Ethernet** of the XR track. The
IOS XR platforms of this track run only point-to-point Layer 2 services and have no CFM, so the provider edges of this
lab are **Catalyst 8000V** routers running IOS XE. What you learn here, the EVPN route types, Ethernet segments and
CFM, works the same way on IOS XR; the reading pages show the IOS XR form next to the IOS XE one. The supplement has
three pages: *E-LAN* (tasks M11-6 and M11-7), *EVPN multihoming* (task M11-8) and *Ethernet OAM* (task M11-9). Read
each page before its tasks, and work through the tasks here, in order. Each task builds on the previous one.

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

Before the provider moved to EVPN, a colleague built customer C's E-LAN on VPLS (VPN ID 210, VLAN 210 at sites 1, 2
and 3). The customer says that site 3 has never reached any other site. Sites 1 and 2 reach each other.

- Make all three sites reach each other over this E-LAN (172.31.210.0/24).
- XE2's part of the E-LAN is correct; do not change it.

### Task M11-7

Customer C's new E-LAN runs on EVPN, in EVPN instance **200**, between sites 1, 2 and 3.

- Carry the customer's frames among sites 1, 2 and 3 as one LAN (172.31.200.0/24). At sites 1 and 2 the customer
  uses VLAN 200. At site 3 this E-LAN uses the customer's port without a VLAN tag; the other services on that port
  stay tagged.
- The provider edges learn each other's customer MAC addresses through BGP, and exchange their EVPN routes only
  through the route reflector P1. There must be no BGP session between two provider edges. The BGP router ID of each
  provider edge is its Loopback0 address.
- The core carries no multicast: the provider edge that receives a broadcast frame from a customer sends one copy to
  each other provider edge of the E-LAN.

### Task M11-8

Site 4 is a switch, SW1, attached to both XE1 and XE2 for resilience. SW1 bundles its two links with LACP (active) and
uses VLAN 200 on the bundle (172.31.200.4).

- Connect site 4 to the E-LAN of Task M11-7.
- Both links of SW1 forward traffic at the same time. SW1 must see XE1 and XE2 as one LACP partner and bundle both
  links.
- The Ethernet segment of site 4 has the identifier **0000.0000.0000.0000.0401** (type 0).
- XE3 must be able to send site 4's traffic to either XE1 or XE2.

### Task M11-9

The provider wants to monitor E-Line 130 (site 1 ⇔ site 3) itself, apart from the customer's traffic, with CFM.

- Use the maintenance domain **PROV** at level **4**, and the maintenance association (service) **E130** for the
  E-Line, whose EVC is `E130`. Put a MEP at each end of the E-Line, on the provider edge's attachment circuit, facing
  the pseudowire. The MEP ID of an end is the number of its site.
- When the E-Line breaks anywhere between XE1 and XE3, both ends must notice within **5 seconds**, even if no
  interface goes down.
- XE1 measures the two-way frame delay of the E-Line to the other end without stopping, with IP SLA operation
  **130** (Y.1731).
