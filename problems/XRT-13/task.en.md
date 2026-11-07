# XR Track 13 — The MPLS Services Side by Side

This lab is the practice part of *The MPLS services side by side* in the XR track. You build five services for one
customer, from a network that has a core and nothing else: an IP VPN, an E-Line on an LDP pseudowire, an E-LAN on VPLS,
an E-LAN on EVPN, and an E-Line on EVPN-VPWS. The two reading pages, *The services side by side* and *Build order*, use the
same topology with other values. Read them before the tasks, and work through the tasks here, in order.

## Ground rules

- You configure **XE1**, **XE2**, **XE3** and **XR01**. P1, RR1 and the CEs are fixed; do not change them. You may log in to
  them to look. The CEs belong to the customer.
- Each task states the behaviour that is required. The reading pages have configuration examples for the same kinds of
  service with other values. You can also use the CLI help (`?`), the `show` commands, and the Cisco configuration guides
  and command references for IOS XE and IOS XR.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices, and reports each step
  of the service separately, so you can see where it stops. Leave configuration mode before you press it. Give LDP and
  BGP half a minute to settle after a change.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XE1, XE2 and XE3 run **Catalyst 8000V** 17.15.1a with the boot licence level `network-advantage` (MPLS is
  available). IOS XE has no commit: each line takes effect when you enter it. XR01 runs **IOS XRv 9000** 26.1.1:
  a change takes effect when you commit it. P1 and RR1 are IOS XE 17.15 routers.

## Topology

| Link | Ends | Addressing |
|---|---|---|
| CORE-1 | P1 Ethernet0/0 ─ XE1 GigabitEthernet1 | 10.0.41.0/24 (P1 .51, XE1 .41) |
| CORE-2 | P1 Ethernet0/1 ─ XE2 GigabitEthernet1 | 10.0.42.0/24 (P1 .51, XE2 .42) |
| CORE-3 | P1 Ethernet0/2 ─ XE3 GigabitEthernet1 | 10.0.43.0/24 (P1 .51, XE3 .43) |
| CORE-4 | P1 Ethernet1/0 ─ XR01 GigabitEthernet0/0/0/0 | 10.0.1.0/24 (P1 .51, XR01 .1) |
| RR | P1 Ethernet1/1 ─ RR1 Ethernet0/0 | 10.0.52.0/24 (P1 .51, RR1 .52) |

| Router | Role | Platform | Loopback0 |
|---|---|---|---|
| P1 | Core | IOS XE 17.15 | 10.255.0.51/32 |
| RR1 | Route reflector | IOS XE 17.15 | 10.255.0.52/32 |
| XE1 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.41/32 |
| XE2 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.42/32 |
| XE3 | Provider edge | Catalyst 8000V 17.15.1a | 10.255.0.43/32 |
| XR01 | Provider edge | IOS XRv 9000 26.1.1 | 10.255.0.1/32 |

| Customer D site | Attached to | Customer equipment |
|---|---|---|
| Site 1 | XE1 GigabitEthernet2 | CE1 (router) |
| Site 2 | XE2 GigabitEthernet2 | CE2 (router) |
| Site 3 | XE3 GigabitEthernet2 | CE3 (router) |
| Site 4 | XR01 GigabitEthernet0/0/0/1 | CE4 (router) |

| Service | Site 1 | Site 2 | Site 3 | Site 4 | Customer addresses |
|---|---|---|---|---|---|
| IP VPN | — | VLAN 310 | VLAN 310 | VLAN 310 | Site link 172.20.<site>.0/24 (CE .1, provider .254). Site LAN 10.30.<site>.0/24 |
| E-Line on an LDP pseudowire | — | — | VLAN 320 | VLAN 321 | 172.31.32.0/24 |
| E-LAN on VPLS | VLAN 330 | VLAN 330 | VLAN 330 | — | 172.31.33.0/24 |
| E-LAN on EVPN | VLAN 340 | VLAN 340 | VLAN 340 | — | 172.31.34.0/24 |
| E-Line on EVPN-VPWS | VLAN 350 | VLAN 350 | — | — | 172.31.35.0/24 |

- The core runs the IS-IS instance `CORE` (level 2, wide metrics) and LDP on every core link. The link between P1 and
  RR1 runs IS-IS only. P1 does not run BGP. The BGP AS is 65000.
- RR1 is the route reflector. Its clients are already configured on RR1: XE1, XE2, XE3 and XR01 for VPNv4, and XE1, XE2
  and XE3 for L2VPN EVPN. The provider edges do not run BGP yet.
- The provider's site numbers: site 1 = **1**, site 2 = **2**, site 3 = **3**, site 4 = **4**. The customer's address at
  each site has the site number as its host part (for example 172.31.33.2 is CE2). Where a service needs an identifier
  for each end, the identifier of an end is the number of its site.

## The services side by side

### Task S-1

Customer D's IP VPN connects sites 2, 3 and 4 on VLAN 310.

- On the provider edges, the customer is in VRF **CUST-D**. The route distinguisher of each provider edge is its
  Loopback0 address followed by `:310`. The VRF imports and exports route target **65000:310**.
- The provider edges exchange VPN routes only through the route reflector RR1. There must be no BGP session between two
  provider edges. The BGP router ID of each provider edge is its Loopback0 address.
- At sites 2 and 4 the customer runs eBGP with the provider (CE2 in AS 65102, CE4 in AS 65104). The CE at site 3 runs no
  routing protocol; it has a default route to the provider. The provider still carries site 3's LAN (10.30.3.0/24) to
  the other sites.
- Each site reaches the LANs of the other two sites.

### Task S-2

- Carry customer D's frames between site 3 (VLAN 320) and site 4 (VLAN 321) as one point-to-point line
  (172.31.32.0/24), on an LDP-signalled pseudowire with pseudowire ID **320**.
- This line does not use BGP.

### Task S-3

- Carry customer D's frames among sites 1, 2 and 3 (VLAN 330) as one LAN (172.31.33.0/24), on VPLS with VPN ID
  **330** and LDP signalling.
- Every site reaches the other two.

### Task S-4

- Carry customer D's frames among sites 1, 2 and 3 (VLAN 340) as one LAN (172.31.34.0/24), in EVPN instance **340**
  (VLAN-based).
- By the provider's route target plan, this EVPN instance imports and exports route target **65000:3400** and no other.
- The provider edges learn each other's customer MAC addresses through BGP, and exchange their EVPN routes only through
  the route reflector RR1. The BGP router ID of each provider edge is its Loopback0 address.
- The core carries no multicast: the provider edge that receives a broadcast frame from a customer sends one copy to
  each of the other provider edges.

### Task S-5

- Carry customer D's frames between site 1 (VLAN 350) and site 2 (VLAN 350) as one point-to-point line
  (172.31.35.0/24), in EVPN instance **350**. The identifier of each end is the number of its site.
- This line does not use LDP to signal the line.
