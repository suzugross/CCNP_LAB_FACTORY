# M11 supplement — EVPN multihoming

The previous page joined sites 1, 2 and 3 in one E-LAN with EVPN. This page adds site 4, a switch attached to two PEs
at once, and uses both of its links. The lab is still XRT-12; Task M11-8 belongs to this page.

:::topo
nodes:
  SW1: {at: [0, 1.4], label: "SW1 (site 4)"}
  XE1: {at: [1.9, 0.4], label: "XE1 (PE)"}
  XE2: {at: [1.9, 2.4], label: "XE2 (PE)"}
  P1: {at: [3.8, 1.4], label: "P1 (P, RR)"}
  XE3: {at: [5.7, 1.4], label: "XE3 (PE)"}
  CE3: {at: [7.6, 1.4], label: "CE3 (site 3)"}
links:
  - [SW1, XE1, "Et0/0 — Gi3"]
  - [SW1, XE2, "Et0/1 — Gi3"]
  - [XE1, P1, "CORE-1"]
  - [XE2, P1, "CORE-2"]
  - [P1, XE3, "CORE-3"]
  - [XE3, CE3, "Gi2"]
frames:
  - {label: "one LACP bundle (Po1) on SW1", nodes: [SW1]}
:::

SW1 bundles its two links with LACP into Port-channel1 and uses VLAN 200 on it (172.31.200.4). Sites 1 and 2 are left
out of the drawing; they are on XE1 and XE2 as before.

## 1. What it is good for

### 1.1 One site on two PEs

Site 4 should survive the loss of a PE, or of a link to a PE. So SW1 is attached to two PEs, XE1 and XE2. That raises a
question that one link never did: what stops a frame from going round SW1 → XE1 → XE2 → SW1?

### 1.2 Before: one of the two links waits

Without help from the PEs, a loop through the provider's network is real. In VPLS, a broadcast from SW1 enters XE1,
crosses the pseudowire to XE2 and comes back down XE2's link to SW1. The usual cures keep one link idle:

- **Spanning tree** on SW1 (or across the PEs) blocks one link.
- **Active/standby** attachment: one PE forwards, the other's link or pseudowire stays in standby until the first fails.
- **Multi-chassis link aggregation** (mLACP, vPC and the like) makes two PEs look like one, with a protocol of its own
  between the two PEs, outside the VPN.

Each works, and each leaves half of the bandwidth unused or adds a protocol that only two PEs speak.

### 1.3 The answer: an Ethernet segment

EVPN builds multihoming into the VPN itself. The set of links that join one customer device to several PEs is an
**Ethernet segment** (ES), named by an identifier (ESI) that both PEs configure. With the ESI, the PEs learn about each
other through BGP, and EVPN's rules (section 2) remove the loop and the duplicate frames. Both links can then forward at
the same time (**all-active**), and SW1 sees one bundle.

## 2. How it works

### 2.1 The Ethernet segment identifier

An ESI is 10 octets: one octet of **type**, then nine octets of value. Two types matter here:

- **Type 0**: the nine octets are chosen by the operator. Providers usually derive them from a numbering scheme, as in
  this lab (`0000.0000.0000.0000.0401` = type 00 and the value 00.00.00.00.00.00.00.04.01).
- **Type 3**: built from a MAC address (six octets) and a local number (three octets).

IOS XE displays the whole ESI as five groups of four hex digits, type first; `identifier type 0` takes the nine octets
of the value only, separated by dots. An ESI of all zeros means "a single-homed site", which is why the ESI column was 0
on the previous page.

The IOS XE 17 guide is not consistent here: its multihoming chapter says that only type 3 is supported, while the
example in its chapter on EVPN with IRB is marked as supporting both types 0 and 3. Catalyst 8000V 17.15.1a accepted
type 0 and advertised it as shown below.

### 2.2 Route type 4: the PEs find each other and elect a forwarder

Each PE with an ESI advertises one **type 4** route (Ethernet segment route). Its route target is derived from the ESI,
so only the PEs on the same segment import it. Through it, XE1 and XE2 learn that they share the segment.

They then elect, for each EVPN instance, one **designated forwarder** (DF): the only PE of the segment that sends BUM
frames (broadcast, unknown unicast, multicast) from the core down to SW1. Without a DF, a broadcast from site 3 would
reach SW1 twice, once through each PE. RFC 7432 gives the default rule: order the PEs of the segment by address and
number them from 0 (the **ordinal**); the PE whose number equals the VLAN modulo the number of PEs is the DF. A known
unicast frame is not affected: either PE may deliver it.

```console
XE1#show l2vpn evpn ethernet-segment detail
EVPN Ethernet Segment ID: 0000.0000.0000.0000.0401
  Local Discriminator:    4
  Interface:              Po1
  Redundancy mode:        all-active
  DF election wait time:  3 seconds
  Split Horizon label:    19
  State:                  Ready
  Encapsulation:          mpls
  Ordinal:                0
  Core Isolation:         No
  RD:                     10.255.0.41:1
    Export-RTs:           65000:200
  Forwarder List:         10.255.0.41 10.255.0.42
```

`Forwarder List` shows both PEs of the segment; `Ordinal` is this PE's place in it (XE2 shows 1). The DF election waits
3 seconds after the segment comes up, so that both PEs' type 4 routes have arrived before anyone decides.

### 2.3 Route type 1: aliasing

Each PE of the segment also advertises **type 1** routes (Ethernet auto-discovery): one for the segment as a whole
(Ethernet tag 4294967295) and one per EVPN instance (Ethernet tag 0).

```console
XE1#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.41:1][00000000000000000401][4294967295]/23, version 34
      Extended Community: RT:65000:200 EVPN LABEL:0x0:Label-304
BGP routing table entry for [1][10.255.0.41:200][00000000000000000401][0]/23, version 44
  Local, imported path from [1][10.255.0.42:200][00000000000000000401][0]/23 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.51 (10.255.0.51)
```

For a far PE such as XE3, these routes say "the segment 0401 is reachable through XE1 and through XE2". So when SW1's MAC
arrives in a type 2 route that carries the ESI, XE3 can send frames for it to either PE, even if only one of them has
seen a frame from SW1. That is **aliasing**, and it is what makes all-active load-sharing work from the far end:

```console
XE3#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
-------------- ----- ----- ------------------------ ---------- ---------------
aabb.cc00.6900 200   200   0000.0000.0000.0000.0000 0          10.255.0.41
aabb.cc00.6a00 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.6b00 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc80.6800 200   200   0000.0000.0000.0000.0401 0          10.255.0.41
                                                               10.255.0.42
```

The last entry is SW1's: ESI 0401, two next hops. CE1 and CE2 (single-homed, ESI 0) have one each.

### 2.4 When a link fails: one withdrawal for all MACs

If XE1 loses its link to SW1, it withdraws its type 1 route for the segment. XE3 then removes XE1 from **every** MAC
behind that segment at once, without waiting for each MAC's type 2 route to be withdrawn (**mass withdrawal**). A
segment with a thousand MACs fails over with one BGP update.

In the lab, XE1's Gi3 was shut down while SW1 was pinging CE3. Three seconds later XE3 listed SW1's MAC behind XE2 only,
SW1 had taken Et0/0 out of its bundle, and the ping kept going. When Gi3 came back, both next hops returned.

### 2.5 Split horizon on the segment

One loop is left. A broadcast from SW1 that arrives at XE1 is copied to every PE of the E-LAN, XE2 included. XE2 is also
on SW1's segment; if it is the DF, it would send the frame back down to SW1. To prevent that, each PE advertises a
**split-horizon label** for the segment (the ESI label, `Split Horizon label: 19` above). When XE1 sends XE2 a BUM frame
that came from segment 0401, it adds XE2's split-horizon label; XE2 sees it and does not send the frame out of that
segment.

### 2.6 The route types at a glance

The number at the start of each line of `show bgp l2vpn evpn` (`[1]`, `[2]`, …) is the route type. The type is the format
of the message, and it also decides what the PE is saying with the route. An L3VPN needed one kind of route ("prefix X
is behind me; send with this label"). An L2 service has several things to tell, so EVPN numbers its formats. The four
types of this unit:

| Type | Name | What the PE says | How many per PE |
|---|---|---|---|
| 2 | MAC/IP advertisement | "This MAC is behind me; for frames to it, use this label" | One per learned MAC (plus one with the IP when the IP is known) |
| 3 | IMET | "I am in this E-LAN; send me a copy of BUM frames with this label" | One per EVI |
| 4 | Ethernet segment route | "I am attached to this segment" | One per segment |
| 1 | Ethernet auto-discovery | "This segment is reachable through me too" (in EVPN-VPWS: "here is my end of the E-Line") | One per segment, and one per EVI |

In short: type 2 is about MACs, type 3 about BUM, and types 1 and 4 about Ethernet segments.

Which types appear depends on the service:

- **E-LAN with every site on one PE: types 2 and 3 only.** In switch terms, type 2 hands out the contents of the MAC
  address table in BGP, and type 3 builds the list of copies to make when flooding. The `Peers` lines of
  `show l2vpn evpn evi <EVI> detail` (`1 MAC, 1 MAC/IP, 1 IMET, 0 EAD` on the previous page) count the routes received
  from each PE by type: MAC and MAC/IP are type 2, IMET is type 3, EAD is type 1.
- **Multihoming adds types 4 and 1.** Type 4 stays among the PEs of the segment (XE3 does not import it): XE1 and XE2
  find each other and elect the DF. Type 1 speaks to the far PEs: XE3 learns that 0401 is reachable through both XE1
  and XE2, which gives aliasing and mass withdrawal. The type 2 route for SW1's MAC carries ESI 0401, and that ties it to
  the type 1 routes.
- **EVPN-VPWS (E-Line): type 1 only.** It only joins two ends, so there is no MAC to learn and nothing to flood. All a PE
  has to say is "my end of the E-Line is AC identifier 1, and here is the label", and it says it in the format of a
  per-EVI type 1 route, with the AC identifier in the Ethernet tag field.

Type 1 shows up in both EVPN-VPWS and multihoming because it is one format with different uses. The Ethernet tag tells
them apart: the AC identifier in EVPN-VPWS, 4294967295 in the per-segment route, and 0 in the per-EVI route of a
VLAN-based E-LAN.

## 3. Configuring it on IOS XE

### 3.1 The configuration

Both PEs carry the same configuration for the segment: the ESI and the redundancy mode, a Port-channel that belongs to
the segment, and an EFP on the Port-channel in the bridge domain of the E-LAN.

:::config fold Catalyst 8000V (IOS XE 17.15) — XE1's part of dual-homing site 4 all-active (XE2 has the same)
l2vpn evpn ethernet-segment 4                      ## the segment; 4 is only a local number (the discriminator)
 identifier type 0 00.00.00.00.00.00.00.04.01      ## the 9-octet value; shown as 0000.0000.0000.0000.0401
 redundancy all-active                             ## both PEs forward (the only mode on this platform)
!
interface Port-channel1
 no ip address
 lacp device-id 0000.0000.0004                     ## the LACP system ID sent to SW1; the same on both PEs
 evpn ethernet-segment 4                           ## this bundle is the segment
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
  exit                                             ## leave the service instance and the Port-channel
 exit
interface GigabitEthernet3
 channel-group 1 mode active                       ## the link to SW1, as the only member of Po1 on this PE
!
bridge-domain 200
 member Port-channel1 service-instance 200         ## site 4 joins the E-LAN of the previous page
!
:::

Each PE has one link to SW1, so each Port-channel has one member. The bundle that SW1 sees is made of one link to each
PE.

### 3.2 LACP: two PEs, one partner

LACP bundles only links whose other end reports the same **system ID**. Left alone, XE1 and XE2 each report their own,
and SW1 sees two partners. `lacp device-id` sets the ID the PE reports on that Port-channel; any MAC address works as
long as both PEs use the same one. In the lab, with the line on XE1 only:

```console
SW1#show etherchannel summary
1      Po1(SU)         LACP        Et0/0(P)        Et0/1(s)
SW1#show lacp neighbor
Et0/0         SA     32768     0000.0000.0004   0s  0x0    0x1    0x4     0x3D
Et0/1         SA     32768     001e.140a.fb00   0s  0x0    0x1    0x4     0xD
```

SW1 kept Et0/0 (`P`, in the bundle) and suspended Et0/1 (`s`), because the partner on Et0/1 had another system ID. XE2's
Port-channel stayed down. With the line on both PEs, SW1 showed `Et0/0(P) Et0/1(P)`.

### 3.3 Reading the outputs

- `show l2vpn evpn ethernet-segment detail`: the ESI, the mode, the PEs of the segment (`Forwarder List`), the
  split-horizon label.
- `show bgp l2vpn evpn route-type 4` and `route-type 1`: the segment's routes from both PEs.
- `show l2vpn evpn mac` on a far PE: the MACs behind the segment, with the ESI and two next hops.
- On SW1, `show etherchannel summary` and `show lacp neighbor`: whether both links are in the bundle, and the partner's
  system ID on each.

### 3.4 What goes wrong

| Mistake | What the lab showed |
|---|---|
| `lacp device-id` on one PE only, or different on the two | SW1 bundles one link and suspends the other; the other PE's Port-channel stays down |
| A different ESI on the two PEs (for example type 3 on one) | Each PE is alone on its segment; the far PE no longer has two next hops for SW1's MAC |
| The ESI value written as displayed (`0000.0000.0000.0000.0401`) | Rejected: `identifier type 0` takes the nine octets of the value, dot-separated |

The Catalyst 8000V offers only `redundancy all-active`. In **single-active** mode (on IOS XR and other platforms), only the
DF forwards for a VLAN and the other PE's link waits; the CE then needs no bundle across the PEs.

:::try
Fail one link of the segment. Do this after Task M11-8.

1. On SW1, start `ping 172.31.200.3 repeat 100000 timeout 1` (stop it with Ctrl+Shift+6).
2. On XE1, shut down GigabitEthernet3. On XE3, run `show l2vpn evpn mac` a few times. On SW1 (a second console), run
   `show etherchannel summary`.
3. On XE1, bring GigabitEthernet3 back up and look again after half a minute.

Measured in the lab: within 3 seconds XE3 listed SW1's MAC behind 10.255.0.42 only, SW1 showed Et0/0 waiting (`w`) and
then suspended (`s`), and the ping did not stop. In this lab SW1 runs `lacp rate fast`; IOL-L2 does not see the far end of
a link go down, so it relies on LACP to notice.
:::

### 3.5 The same on IOS XR

On IOS XR the segment is written under `evpn` → `interface Bundle-Ether<n>` → `ethernet-segment` → `identifier type 0
<value>`, and all-active is the default; `load-balancing-mode single-active` selects single-active. The bundle on both
PEs also needs the same LACP system ID (`lacp system mac <MAC>` under the bundle) for the CE to bundle the links. The
bundle's sub-interface joins the bridge domain as an attachment circuit.

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `l2vpn evpn ethernet-segment <n>` → `identifier type 0 <9 octets>`, `redundancy all-active` | `evpn` → `interface Bundle-Ether<n>` → `ethernet-segment` → `identifier type 0 <value>` |
| `interface Port-channel<n>` → `evpn ethernet-segment <n>` | (the segment is configured on the bundle under `evpn`) |
| `lacp device-id <MAC>` | `lacp system mac <MAC>` (under the bundle) |
| (single-active not available) | `load-balancing-mode single-active` |
| `show l2vpn evpn ethernet-segment detail` | `show evpn ethernet-segment detail` |

## Practice

In lab **XRT-12**, work through Task M11-8. Then go on to the next page, *Ethernet OAM*.

<p class="tolab"><a href="/_learn?id=XRT-12">Open lab XRT-12 in the workspace</a> — <a href="ba-m11-practice-5.html">Tasks</a></p>

:::note
Sources: MPLS Configuration Guide, Cisco IOS XE 17.x (EVPN Multihoming; EVPN over MPLS with IRB, whose example has
`lacp device-id` on the Port-channel). Both chapters name the ASR 1000 only. L2VPN configuration guides for the
ASR 9000 and NCS 5500, IOS XR 7.10.x (EVPN Features; the NCS 5500 example sets the same `lacp system mac` on both PEs),
and the Cisco tech note "Configure EVPN Route Types and Their Functions on IOS XR Routers" (2026). RFC 7432 (Ethernet segments,
route types 1 and 4, DF election, aliasing, mass withdrawal, the ESI label). All checked in November 2026. The outputs,
the LACP behaviour and the failover times come from measurements in lab XRT-12 (Catalyst 8000V 17.15.1a, IOL-L2 17.15).
:::
