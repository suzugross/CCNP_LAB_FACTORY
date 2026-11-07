# What EVPN-VPWS buys you — the same E-Line built two ways

There were two ways to build an E-Line (a service that looks like one cable): an LDP pseudowire, and EVPN-VPWS.
If all you do is join one line between one PE at each end, they are carried the same way. The outer label is the road
to the egress PE, and the inner label points to the remote AC (section 3.3 of *The services side by side*).

The difference shows in two situations. This page puts both ways side by side on the same topology to check them.

- When a customer site is attached to two PEs
- When the core road moves to SR and LDP is removed from the network

The output was taken on the following topology, built for this page. The PEs are three Catalyst 8000V (IOS XE 17.15.1a).
P1, RR1 and CE3 are IOL running IOS XE 17.15, and SW1 is IOL-L2. P1 is only a P router and does not run BGP.

:::topo
nodes:
  SW1: {at: [0, 1.6], label: "SW1 (site 4)"}
  XE1: {at: [1.9, 0.3], label: "XE1 (PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2 (PE)"}
  RR1: {at: [3.8, 0.3], label: "RR1 (RR)"}
  P1: {at: [3.8, 1.6], label: "P1 (P)"}
  XE3: {at: [5.7, 1.6], label: "XE3 (PE)"}
  CE3: {at: [7.6, 1.6], label: "CE3 (site 3)"}
links:
  - [SW1, XE1, "one link of Po1"]
  - [SW1, XE2, "one link of Po1"]
  - [XE1, P1, ""]
  - [XE2, P1, ""]
  - [P1, RR1, "IS-IS only"]
  - [P1, XE3, ""]
  - [XE3, CE3, "VLAN 150 160"]
frames:
  - {label: "AS 65000 (IS-IS CORE, LDP; SR in section 4)", nodes: [XE1, XE2, P1, RR1, XE3]}
:::

SW1 bundles its two links to XE1 and XE2 into one bundle (LACP Port-channel1). Both E-Lines join SW1 at site 4 to CE3
at site 3.

| VLAN | Built with | Addressing |
|---|---|---|
| 150 | EVPN-VPWS (EVI 150; the end at site 4 is 4, the end at site 3 is 3) | 172.31.150.0/24 (SW1 .4, CE3 .3) |
| 160 | LDP pseudowires (XE1 ⇔ XE3 is PW ID 161, XE2 ⇔ XE3 is 162) | 172.31.160.0/24 (SW1 .4, CE3 .3) |

## 1. Why bother

### 1.1 The problem: attaching a site to two PEs

Site 4 must not go down, so SW1 is attached to both XE1 and XE2: if one PE fails, traffic should keep flowing.
To SW1 the two links are one bundle, and the bundle spreads frames over both links.

The E-Line is "one cable joining site 4 and site 3". A frame should reach site 3 whichever link it enters.

### 1.2 The earlier answer: primary and backup pseudowires

An LDP pseudowire is a line that names the remote PE. XE3 builds two of them, one to XE1 and one to XE2, and keeps one as
the backup (pseudowire redundancy). Only one line is ever in use.

So the CE's bundle has to match: no frames may go towards the backup side. That needs another mechanism by which the PEs
agree which side of the bundle to use (MC-LAG or similar). This topology does not have one, and section 3.2 shows what
happens.

### 1.3 EVPN-VPWS's answer: two PEs claim the same ES

With EVPN-VPWS, XE1 and XE2 advertise the bundle to SW1 in BGP as the same ES (Ethernet Segment, numbered by its ESI).
The multihoming used for the E-LAN in the M11 add-on works for an E-Line too. Both links of the bundle are used, and when
one PE fails, a route is withdrawn and traffic moves over.

The EVPN-VPWS standard (RFC 8214) names this redundancy first among its benefits. And because the remote PE is found in
BGP, moving the core road to SR removes LDP from the network (section 4).

## 2. How it works: hand out end numbers in BGP

With EVPN-VPWS, each PE hands out "this end (`source`) of this EVI is here, and this is its label" in a route type 1
(the Ethernet A-D per EVI route). The remote PE looks for the route with its own `target` number.

On this topology XE1 and XE2 send the route for end 4, and XE3 sends the route for end 3. XE3 receives two routes for
end 4 through RR1, one from XE1 and one from XE2. The `[4]` at the end of the route is the end number.

```console
XE3#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.43:150][00000000000000000000][4]/23, version 6
Paths: (2 available, best #2, table evi_150)
  Flag: 0x20000000100
  Not advertised to any peer
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.42:150][00000000000000000000][4]/23 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, multipath(oldest)
      Rcvd Label: 23, Local Label: None
      Extended Community: RT:65000:150
      Originator: 10.255.0.42, Cluster list: 10.255.0.52
      rx pathid: 0, tx pathid: 0
      Updated on Nov 6 2026 23:43:40 UTC
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.41:150][00000000000000000000][4]/23 (global)
    10.255.0.41 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, multipath, best
      Rcvd Label: 23, Local Label: None
      Extended Community: RT:65000:150
      Originator: 10.255.0.41, Cluster list: 10.255.0.52
      rx pathid: 0, tx pathid: 0x0
      Updated on Nov 6 2026 23:43:33 UTC
```

(XE3's own route and the entries before import are omitted.)

XE3's configuration contains neither XE1's address nor XE2's. All it has is the end numbers (`service target 4 source 3`).
With two PEs at site 4, XE3's configuration is the same as with one.

XE3 sends to one PE of the two. Here it was XE2 (in `imposed label stack {19 23}`, 19 is the road to XE2 that P1 handed
out, and 23 is XE2's label for end 4).

```console
XE3#show l2vpn evpn vpws vc id 150 detail
EVPN name: SITE3-SITE4, state: up, type: point-to-point
  EVPN ID: 150
  VPWS Service Instance ID: Source 3, Target 4
  Labels: Local 23, Remote 23
  Next Hop Address: 10.255.0.42
  Associated member interface Gi2 up, Gi2:150 status is up
  Output interface: Gi1, imposed label stack {19 23}
```

(The remaining lines are omitted.)

XE1 and XE2 find the other PE that claims the same ESI through route type 4. When both are listed in `Forwarder List`,
the ES is up.

```console
XE1#show l2vpn evpn ethernet-segment detail
EVPN Ethernet Segment ID: 0000.0000.0000.0000.0401
  Local Discriminator:    4
  Interface:              Po1
  Redundancy mode:        all-active
  DF election wait time:  3 seconds
  Split Horizon label:    19
  State:                  Ready
  Encapsulation:          none
  Ordinal:                0
  Core Isolation:         No
  Forwarder List:         10.255.0.41 10.255.0.42
```

:::note
In the IOS XE 17.x MPLS configuration guide, the multihoming chapter is for the E-LAN and says nothing about EVPN-VPWS
multihoming (EVPN-VPWS has only a single-homing chapter). The Catalyst 8000V 17.15.1a on this topology accepted the
configuration and behaved as this page shows, but not in the standard form. The ESI in the type 1 routes stayed 0
(`[00000000000000000000]` in the output above), and XE3 used only one PE. Each time a PE came back, XE3 moved to the PE
whose route had arrived last.

With RFC 8214 all-active, the remote PE can also spread flows over both PEs. The IOS XR guides do document EVPN-VPWS
multihoming.
:::

## 3. Both ways on the same topology

### 3.1 EVPN-VPWS

XE1 and XE2 do not differ by a single character in this part of the configuration. The bundle becomes the ES, and the
bundle's service instance becomes end 4 of EVI 150.

:::config XE1 (IOS XE) — EVPN-VPWS with site 4 attached to two PEs (XE2 is the same)
l2vpn evpn ethernet-segment 4                      ## Create the ES. The number is only a name inside this PE
 identifier type 0 00.00.00.00.00.00.00.04.01      ## The ESI. Use the same value on XE1 and XE2 (the mark of one site)
 redundancy all-active                             ## Use both PEs
!
interface Port-channel1
 description to SW1 (site 4)
 no ip address
 evpn ethernet-segment 4                           ## Make this bundle ES 4
 lacp device-id 0000.0000.0004                     ## Both PEs claim the same LACP ID, so SW1 sees one partner
 service instance 150 ethernet
  encapsulation dot1q 150
  rewrite ingress tag pop 1 symmetric
!
interface GigabitEthernet3
 description to SW1 (site 4)
 no ip address
 channel-group 1 mode active                       ## Put the link to SW1 in the bundle
!
l2vpn evpn instance 150 point-to-point
 vpws context SITE4-SITE3
  service target 3 source 4                        ## Own end 4, remote end 3. The remote PE's address is not written
  member Port-channel1 service-instance 150
:::

:::config XE3 (IOS XE) — EVPN-VPWS at site 3
interface GigabitEthernet2
 description to CE3 (site 3)
 no ip address
 service instance 150 ethernet
  encapsulation dot1q 150
  rewrite ingress tag pop 1 symmetric
!
l2vpn evpn instance 150 point-to-point
 vpws context SITE3-SITE4
  service target 4 source 3                        ## The same lines, even with end 4 on two PEs
  member GigabitEthernet2 service-instance 150
:::

If the two PEs do not share the `lacp device-id`, SW1 sees two partners and stops one link of the bundle (measured in the
M11 add-on). With the same ID, both links of SW1's bundle are `P` (bundled).

```console
SW1#show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------------------
1      Po1(SU)         LACP        Et0/0(P)        Et0/1(P)
```

(The legend lines are omitted.)

SW1 was sending its pings to CE3 down the link to XE2 (Et0/1). Over 100 pings, Et0/1's output count went up by 101 and
Et0/0's by only 2, and every ping got through. The frames that entered XE2 reached XE3 from XE2's end 4 too.

```console
SW1#show interfaces Ethernet0/1 | include packets output
     56200 packets output, 6641213 bytes, 0 underruns
SW1#ping 172.31.150.3 repeat 100
Success rate is 100 percent (100/100), round-trip min/avg/max = 1/2/3 ms
SW1#show interfaces Ethernet0/1 | include packets output
     56301 packets output, 6653073 bytes, 0 underruns
```

(The lines in the middle of the ping are omitted. These counts were taken after the road moved to SR in section 4. Which
link SW1 uses has nothing to do with how the core road is built.)

The failover was measured too. While SW1 sent 15000 pings with a one-second timeout to CE3, a PE's link to SW1 was taken
down. The number of pings lost in a row is roughly the length of the break in seconds. Even in normal running, a single
ping is lost now and then.

| Link taken down | PE that XE3 was using | Pings lost in a row |
|---|---|---|
| XE1's Gi3 | XE2 | None (only single losses) |
| XE2's Gi3 | XE2 → moved to XE1 | At most 4 (about 4 seconds) |

Even when the side XE3 was using went down, it moved to XE1 in about 4 seconds. Losing its link of the bundle, XE2
withdraws its route for end 4, and XE3 moves to the remaining route from XE1. This is XE3 five seconds after XE2's link
went down.

```console
XE3#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.42:150][00000000000000000000][4]/23, version 15
Paths: (0 available, no best path)
  Not advertised to any peer
BGP routing table entry for [1][10.255.0.43:150][00000000000000000000][4]/23, version 16
Paths: (1 available, best #1, table evi_150)
  Not advertised to any peer
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.41:150][00000000000000000000][4]/23 (global)
    10.255.0.41 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
```

(The entry for XE1's route itself and the lines that follow are omitted.)

In CML, shutting the interface on the XE side leaves SW1's side of the link up. SW1 only notices when LACP packets stop
arriving (3 seconds with `lacp rate fast`). Most of the 4 seconds is this wait.

### 3.2 LDP pseudowires: primary and backup

The same shape was built with LDP pseudowires. XE1 and XE2 each set up a pseudowire to XE3. XE3 puts the two in one group,
with the line to XE1 as the primary and the line to XE2 as the backup.

:::config XE1 (IOS XE) — the LDP pseudowire at site 4 (XE2 uses PW ID 162)
interface Port-channel1
 service instance 160 ethernet
  encapsulation dot1q 160
  rewrite ingress tag pop 1 symmetric
!
l2vpn xconnect context SITE4-SITE3-LDP
 member Port-channel1 service-instance 160
 member 10.255.0.43 161 encapsulation mpls          ## Name the remote PE (XE3) by its address
:::

:::config XE3 (IOS XE) — primary and backup pseudowires
interface GigabitEthernet2
 service instance 160 ethernet
  encapsulation dot1q 160
  rewrite ingress tag pop 1 symmetric
!
l2vpn xconnect context SITE3-SITE4-LDP
 member GigabitEthernet2 service-instance 160
 member 10.255.0.41 161 encapsulation mpls group SITE4 priority 1   ## Primary = XE1. Both PEs are named
 member 10.255.0.42 162 encapsulation mpls group SITE4 priority 2   ## Backup = XE2. Same group, lower priority
:::

On XE3 the primary line is UP and the backup line is STANDBY.

```console
XE3#show l2vpn atom vc
                                       Service
Interface Peer ID         VC ID      Type   Name                     Status
--------- --------------- ---------- ------ ------------------------ ----------
pw100001  10.255.0.41     161        p2p    SITE3-SITE4-LDP          UP
pw100002  10.255.0.42     162        p2p    SITE3-SITE4-LDP          STANDBY
```

But not a single ping from SW1 to CE3 got through. As with EVPN-VPWS, SW1 sends down the link to XE2. XE2 does send the
frames into the backup line (its `Tx Counters` went from 29 to 47 over 20 pings). Even so, XE3 does not use what arrives
on the backup line.

```console
XE2#show l2vpn atom vc vcid 162 detail
pseudowire100001 is up, VC status is standby PW type: Ethernet
      Status sent to access circuit           : DOWN(standby)
      Status received from network peer       : DOWN(standby)
  Tx Counters
    47 output transit packets, 6580 bytes
    0 drops
```

(Only the relevant lines are extracted.)

With SW1's link to XE2 stopped, so that the bundle used only the link to XE1, the pings got through 100%. As section 1.2
said, with primary and backup pseudowires the CE's bundle must also be made to avoid the backup side.

When the primary XE1's link went down, XE3 marked the primary line DOWN and brought the backup line to XE2 UP. Only then
did the frames going to XE2 get through. When XE1's link came back, XE3 went back to the primary, and the pings stopped
again.

```console
XE3#show xconnect all
XC ST  Segment 1                         S1 Segment 2                         S2
------+---------------------------------+--+---------------------------------+--
IA pri   ac Gi2:160(Eth VLAN)            UP mpls 10.255.0.41:161              DN
UP pri   ac Gi2:160(Eth VLAN)            UP mpls 10.255.0.42:162              UP
```

(After XE1's link went down. The legend lines are omitted.)

### 3.3 Side by side

| | EVPN-VPWS | LDP pseudowires (primary and backup) |
|---|---|---|
| What site 3's PE (XE3) has to write | Only the end numbers (`target 4 source 3`) | Both of site 4's PEs, by address |
| Links in use | Both links of the bundle (frames entering XE2 arrive too) | Only the primary. Frames entering the backup do not arrive |
| The CE's bundle | Leave it as it is (the two PEs share the ES and the LACP ID) | Match it by another mechanism so the backup side is unused |
| When a PE fails | Withdraw the route and move over (about 4 seconds here) | The primary line goes down and the backup comes UP |

## 4. Move the road to SR and remove LDP

As M10 showed, the core road can be built with SR instead of LDP. With SR, the road needs no LDP. Do the two E-Lines still
need LDP?

On this topology, SR was added to IS-IS on P1 and XE1 to XE3 with a SID on each loopback, and then `mpls ip` was removed
from the core links.

:::config XE1 (IOS XE) — build the road with SR (P1, XE2 and XE3 the same with their own numbers)
segment-routing mpls
 connected-prefix-sid-map
  address-family ipv4
   10.255.0.41/32 index 41 range 1                 ## Give the loopback SID index 41 (label 16000+41)
  exit-address-family
!
router isis CORE
 segment-routing mpls                              ## IS-IS hands out the SIDs and builds the SR road
!
interface GigabitEthernet1
 no mpls ip                                        ## Stop LDP on the core link
:::

P1 had no LDP sessions left, and the road's labels changed to SR labels (16041 and so on).

```console
P1#show mpls ldp neighbor
P1#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
20         Pop Label  10.0.41.41-A     0             Et0/0      10.0.41.41
21         Pop Label  10.0.42.42-A     0             Et0/1      10.0.42.42
22         Pop Label  10.0.43.43-A     0             Et0/2      10.0.43.43
23         Pop Label  10.0.52.52-A     0             Et1/1      10.0.52.52
16041      Pop Label  10.255.0.41/32   582           Et0/0      10.0.41.41
16042      Pop Label  10.255.0.42/32   506           Et0/1      10.0.42.42
16043      Pop Label  10.255.0.43/32   1088          Et0/2      10.0.43.43
```

(20 to 23 are the SIDs of the links to the neighbouring routers.)

EVPN-VPWS kept working on the SR road (outer label 16041). It passes its labels in BGP, so LDP appears nowhere.

```console
XE3#show l2vpn evpn vpws vc id 150 detail
EVPN name: SITE3-SITE4, state: up, type: point-to-point
  EVPN ID: 150
  VPWS Service Instance ID: Source 3, Target 4
  Labels: Local 23, Remote 23
  Next Hop Address: 10.255.0.41
  Associated member interface Gi2 up, Gi2:150 status is up
  Output interface: Gi1, imposed label stack {16041 23}
```

(The remaining lines are omitted.)

The LDP pseudowires also stayed UP on the SR road. But XE3 still had targeted LDP sessions with XE1 and XE2: these are the
sessions that pass the pseudowire labels.

```console
XE3#show mpls ldp neighbor | include Peer|Targeted|Src
    Peer LDP Ident: 10.255.0.41:0; Local LDP Ident 10.255.0.43:0
	  Targeted Hello 10.255.0.43 -> 10.255.0.41, active, passive
    Peer LDP Ident: 10.255.0.42:0; Local LDP Ident 10.255.0.43:0
	  Targeted Hello 10.255.0.43 -> 10.255.0.42, active, passive
```

With the pseudowires removed from XE3, its LDP sessions went to zero. EVPN-VPWS kept working.

```console
XE3#show mpls ldp neighbor
XE3#
```

Even with an SR road, as long as LDP pseudowires are used, LDP stays in the network just for them. Moving them to EVPN-VPWS
lets both the road and the E-Line run without LDP, and LDP can leave the network.

## 5. Summary

| | LDP pseudowire | EVPN-VPWS |
|---|---|---|
| How the remote PE is found | Named by address | The end-number route (type 1) and the RT, in BGP through the RR |
| How labels are passed | Targeted LDP between the PEs | BGP |
| A site on two PEs | Primary and backup lines; the CE's bundle matched by another mechanism | Two PEs claim the same ES (the same as E-LAN multihoming) |
| When the road moves to SR | LDP stays for the pseudowires | LDP can go |
| One line, one PE at each end | The same | The same |

In a sentence: **EVPN-VPWS is the way to bring the E-Line into the EVPN family.** Multihoming and running without LDP
sit on the same BGP as L3VPN and the E-LAN. On the other hand, with a few PEs and a few lines, an LDP pseudowire is
simpler, as there is no BGP EVPN to set up.
