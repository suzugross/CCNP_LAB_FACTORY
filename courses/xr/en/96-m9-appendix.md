# M9 — Appendix: label allocation, between providers

This appendix covers the parts of unit M9 that the lab tasks do not use: how a PE allocates VPN labels, a VPN that
spans two providers (blueprint 4.1.b), a customer that is itself a provider (CSC, 4.1.c), and the command names on IOS
and IOS XR. Label allocation has a *Try it* that you can do in lab XRT-09.

## 1. How a PE allocates VPN labels

### 1.1 What changes

A PE allocates labels to the routes of its VRFs and advertises them to the other PEs with the routes (page *How L3VPN
works*, section 2.4). When a packet comes back with one of those labels, the label is all the PE has to decide what to
do with it. How many labels the PE allocates decides how many labels it holds and how much work each packet takes.

| Mode | One label stands for | A packet that arrives with it | Number of labels |
|---|---|---|---|
| per-prefix (the IOS XR default) | one VRF route | goes straight to the CE that gave the route | one per route |
| per-CE | one next hop (CE) | goes straight to that CE | one per CE |
| per-VRF | one VRF | is looked up again in the VRF table | one |

Whatever the mode, a route that the PE did not learn from a CE gets the per-VRF (aggregate) label. The command
reference names connected, aggregate and local routes, and the default route imported from the global table gets it
too. There is no CE to send such a packet to next, so the only way is to look the destination up in the VRF
table again.

### 1.2 In the lab

This is XR01 with all four tasks of the lab done, in the default per-prefix mode.

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
   Network            Next Hop        Rcvd Label      Local Label
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24004
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24005
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  20          10.255.0.21/32     Gi0/0/0/1    10.0.3.13       5123
24001  Pop         10.255.0.13/32     Gi0/0/0/1    10.0.3.13       4106
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       16120
24003  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2986
24004  Unlabelled  10.101.1.0/24[V]   Gi0/0/0/2    172.16.11.2     0
24005  Unlabelled  198.51.100.0/25[V] Gi0/0/0/2    172.16.11.2     0
24006  Unlabelled  10.102.1.0/24[V]   Gi0/0/0/3    172.16.21.2     0
24007  Unlabelled  10.99.1.0/24[V]    Gi0/0/0/4    172.16.91.2     500
24008  Unlabelled  10.99.2.0/24[V]    Gi0/0/0/4    172.16.91.2     0
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2500
```

Each of the two routes learned from CEA1 has its own label (24004 and 24005), and XR01 sends a packet that arrives with
one of them to CEA1 with the label removed (`[V]` marks a VRF prefix). The default route that XR01 imports from the
global table in Task M9-4 was not learned from a CE, so even in per-prefix mode it gets the VRF's aggregate label 24009,
and its outgoing column reads `Aggregate`.

In per-CE mode, the two routes learned from CEA1 came together on one label, 24010. The label leads to CEA1 itself
(172.16.11.2 on Gi0/0/0/2), not to a lookup in the VRF:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
...
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24010
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24010
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
...
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2000
24010  Unlabelled  No ID              Gi0/0/0/2    172.16.11.2     0
       Aggregate   No ID              CUST-A                       0            (!)
```

In the legend of `show route`, `(!)` marks an FRR backup path. It is on the second line of 24010 too, where a lookup
in the VRF stands as the backup. Within 20 seconds RT02 showed `nolabel/24010` for both routes of site 1, and pings from
CEA2 reached both. The default route stays on the aggregate label 24009 in per-CE mode too.

:::config XR01 — one label for customer A's VRF
router bgp 65000
 vrf CUST-A
  address-family ipv4 unicast
   label mode per-vrf          ## one label for the whole VRF; per-ce gives one per CE, nothing gives one per prefix
  !
 !
!
:::

:::config RT02 (IOS XE) — one label for customer B's VRF
mpls label mode vrf CUST-B protocol bgp-vpnv4 per-vrf   ## a global command on IOS XE, naming the VRF and the address family
:::

With this on RT02, the label of CEB2's route became `IPv4 VRF Aggr:27`, and 27 in the label table pointed to
`aggregate/CUST-B` (a lookup in the VRF). Pings from CEB1 went through, and with the line removed the route was back on
24.

:::try
Give CUST-A a single label. Do this after Task M9-2 (the result below is after Task M9-4).

1. On XR01, under `router bgp 65000` → `vrf CUST-A` → `address-family ipv4 unicast`, configure `label mode per-vrf`
   and commit.
2. Run `show bgp vrf CUST-A labels` and `show mpls forwarding` on XR01, `show ip bgp vpnv4 vrf CUST-A labels` on
   RT02, and `ping 10.101.1.1 source Loopback10` on CEA2.
3. Remove `label mode` and commit.

An example result: every route XR01 had learned from CEA1 took the label 24009, which the VRF already had for the
imported default route, and 24004 and 24005 left `show mpls forwarding`. Within 20 seconds RT02 showed `nolabel/24009`
for them, and the ping went through. With `label mode` removed, the routes were back on 24004 and 24005.
:::

The number of labels matters on a large PE with many VRF routes. Per-VRF saves labels, but the egress PE looks every
packet up again in the VRF table. Per-prefix needs no second lookup, and uses as many labels as there are routes.

## 2. Between providers

### 2.1 Three ways to join two ASes

When a VPN spans two providers, section 10 of RFC 4364 gives three ways to join them. The later ones scale better, and
in return each provider hands the other more (the VPN routes, the PE loopbacks).

- **Option A**: the border routers (ASBRs) of the two providers meet as PE and CE, with one VRF and one interface or
  subinterface per VPN, and plain IP between them. Simple, and it scales with the number of VPNs.
- **Option B**: the ASBRs exchange VPNv4 routes in eBGP, with labels, and keep no VRFs. On IOS XR the ASBR needs
  `retain route-target all` (or a policy) to keep VPNv4 routes it has no VRF for, route policies on the eBGP VPNv4
  session, and a static /32 route to the other ASBR so that the labelled traffic is forwarded.
- **Option C**: the ASBRs carry only the PEs' loopbacks, as BGP labeled unicast (unit M8, Unified MPLS), and the route
  reflectors of the two providers exchange VPNv4 routes in multihop eBGP.

| | The ASBR holds | Between the ASBRs | A new VPN on the ASBR |
|---|---|---|---|
| Option A | one VRF per VPN | one interface and plain IP routes per VPN | add a VRF and an interface |
| Option B | every VPNv4 route (no VRFs) | eBGP VPNv4, with labels | nothing |
| Option C | only the other side's PE loopbacks | BGP labeled unicast | nothing |

### 2.2 Carrier Supporting Carrier

In **Carrier Supporting Carrier** (CSC, section 9 of RFC 4364), the customer of a VPN is itself a provider. The VPN
carries only the customer carrier's loopbacks, with labels (labeled unicast towards the CSC-CE, or LDP in the VRF), and
the customer carrier runs its own VPNs on top. The routes of the customer carrier's customers never enter the carrying
provider's VRF. Seen from the carrying provider, the customer carrier's core is a small VPN with as many routes as it has
loopbacks.

## 3. Command names

| On IOS | On IOS XR |
|---|---|
| `vrf definition <name>` with `rd` and `route-target` | `vrf <name>` with `import route-target` / `export route-target`; `rd` under `router bgp` → `vrf <name>` |
| `vrf forwarding <name>` (removes the addresses) | `vrf <name>` under the interface |
| `address-family vpnv4` + `neighbor … activate` | `address-family vpnv4 unicast` at the top of BGP and under the neighbour |
| `address-family ipv4 vrf <name>` | `vrf <name>` → `address-family ipv4 unicast` under `router bgp` |
| `neighbor … as-override` | `as-override` under the neighbour's address family |
| `neighbor … soo <value>` | `site-of-origin <value>` under the neighbour's address family |
| `route-target export` + `export map <route-map>` | `export route-target` + `export route-policy <name>` |
| `bgp default route-target filter` (on by default) | always on; `retain route-target` |
| `mpls label mode vrf <name> protocol bgp-vpnv4 per-vrf` (global) | `label mode per-vrf` under the VRF's address family in BGP |
| `show ip bgp vpnv4 all` / `vrf <name>` | `show bgp vpnv4 unicast` / `show bgp vrf <name>` |
| `show ip route vrf <name>` | `show route vrf <name>` |

:::note
The sources are those of the unit's pages (listed at the end of page *How L3VPN works*). Label allocation follows the
BGP command references for the Cisco 8000 and the NCS 5500 (`label mode`) and the L3VPN configuration guide for the
Cisco 8000 (26.x, 2026); Inter-AS and CSC follow sections 9 and 10 of RFC 4364 and the L3VPN guides for the NCS 5500 and
the ASR 9000 (release 7.11). The label values and the behaviour when the mode changes were measured in lab XRT-09.
:::
