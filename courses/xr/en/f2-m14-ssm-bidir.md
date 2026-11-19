# M14 — Two other trees: SSM and bidirectional PIM

The previous page built PIM sparse mode: the receivers join toward the RP, the first-hop router registers each source
with the RP, and the last-hop router then switches to the shortest-path tree. This page covers the two other kinds of
tree that PIM builds. In source-specific multicast (SSM), the receiver names the source, and the tree goes straight
from the receiver to it, without an RP. In bidirectional PIM, there is only the shared tree, and every sender's
packets travel on it in both directions.

This page covers PIM-SSM and PIM-BIDIR from 4.4.a of the blueprint, and IGMPv3 from 4.4.b. The board is XRT-16, as on
the previous page.

## 1. What it is good for

### 1.1 The problem: channels whose source is known, and a conference where everyone sends

The provider adds two services to the board. The first is a set of TV channels from the head-end SRC1, for set-top
boxes that already know where each channel comes from: the channel list gives both the group and the source,
192.168.1.1. Each channel has one source, and it is known before the first packet is sent.

The second is a conference. SRC1, RCV2 and RCV3 all join one group, and each of them sends to it as well as receiving
from it. Any site may talk at any moment, so there are as many sources as sites, and none of them is known in advance.

### 1.2 What came before: everything through the RP

PIM sparse mode, from the previous page, carries both, at a price.

- **The known source.** The receiver's IGMPv2 report names only the group, so the last-hop router PE2 first joins
  toward the RP P1, and the first-hop router PE1 registers SRC1 with the RP. Only when the first packets arrive over
  the shared tree does PE2 learn the source and switch to the shortest-path tree, over the direct link to PE1. The RP
  is needed to find a source that the receiver knew all along.
- **The conference.** Every site that sends is registered with the RP on its own, and every router that switches to
  the shortest-path tree keeps one (S,G) entry for each sender, next to the (*,G). Three senders give up to three
  (S,G) entries in a router for one group; a hundred sites give a hundred.

Either way, every router must know the RP, and the RP takes part in every new source, whether or not the traffic
ends up passing through it.

### 1.3 Two answers: no RP at all, or the RP as the root for every sender

- **SSM: no RP at all.** The receiver names both the group and the source in an IGMPv3 report. The last-hop router
  joins straight toward the source, and each router on the way keeps one (S,G) entry. There is no Register, no shared
  tree and no switch-over. The groups are usually in 232.0.0.0/8, the range set aside for SSM.
- **Bidirectional PIM: the RP as the root for every sender.** There is one tree per group, a (*,G) rooted at the RP
  address. A sender's packets travel up the tree toward the RP and down it to the receivers. There is no Register and
  no (S,G), so the state in a router does not grow with the number of senders.

SSM suits one-to-many with a known source, such as the TV channels; bidirectional PIM suits many-to-many, such as the
conference. Sparse mode stays for the rest. The three run on the same routers at the same time, each for its own
range of groups (sections 2.3 and 3.4).

## 2. How it works

On XRT-16, SRC1 sits behind PE1 and RCV2 behind PE2. RCV3 is on ACCESS-3, the LAN that PE3 and PE4 share; its gateway
is PE4. P1 is the RP of the previous page (Loopback0 10.255.0.11, for all groups). PE2's shortest path to SRC1 is the
direct link to PE1; its path to the RP is the link to P1.

On ACCESS-3, PE4 is the DR (the higher address) and PE3 the IGMP querier (the lower address). Each link label gives the
subnet and the interfaces at its two ends.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP)"}
  PE4: {at: [4.6, 2.0], label: "PE4 (IOS XE)"}
  PE3: [3.2, 3.1]
  SW1: [4.6, 3.1]
  RCV3: {at: [6.4, 3.1], kind: host}
links:
  - [SRC1, PE1, "192.168.1.0/24\nGi0/0/0/2"]
  - [PE1, PE2, "10.0.12.0/24\nGi0/0/0/0 — Gi0/0/0/0"]
  - [PE2, RCV2, "192.168.2.0/24\nGi0/0/0/3"]
  - [PE1, P1, "10.0.1.0/24\nGi0/0/0/1 — Gi0/0/0/0"]
  - [P1, PE2, "10.0.2.0/24\nGi0/0/0/1 — Gi0/0/0/1"]
  - [P1, PE3, "10.0.3.0/24\nGi0/0/0/2 — Gi0/0/0/0"]
  - {a: PE2, b: PE4, label: "10.0.4.0/24\nGi0/0/0/2 — Et0/0", t: 0.62}
  - [PE3, SW1, "Gi0/0/0/1"]
  - {a: PE4, b: SW1, label: "Et0/1", t: 0.3}
  - [SW1, RCV3]
frames:
  - {label: "ACCESS-3 192.168.3.0/24 (PE3 .252, PE4 .253, RCV3 .1)", nodes: [PE3, SW1, RCV3]}
:::

### 2.1 SSM: the receiver names the source

IGMPv3 (RFC 3376) lets a host's report carry a list of sources with a filter mode. In INCLUDE mode, the host asks for
the group only from the sources in the list. That is all that SSM needs from the host: "232.1.1.1, INCLUDE
192.168.1.1" names exactly one tree, the one from 192.168.1.1. IOS XR shows such a report as `Router mode: INCLUDE`,
with the source in the `Group source list` (section 3.2).

IGMPv1 and IGMPv2 reports carry only the group. In an SSM range, a router has no RP to send such a join to, and no
source either, so it drops the report; the group does not even appear in its IGMP table, and the receiver gets
nothing. SSM therefore needs IGMPv3 on the hosts and on the router interfaces that face them. Cisco's SSM mapping can
supply a source for version 1 and 2 reports; it is not used here.

### 2.2 SSM on the board: no RP, no Register

Follow RCV2 as it joins 232.1.1.1 from SRC1 (192.168.1.1). The group is in 232.0.0.0/8, which IOS XR treats as SSM
by default.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP): no entry"}
links:
  - [SRC1, PE1, "data →"]
  - [PE1, PE2, "← (S,G) Join\ndata →"]
  - [PE2, RCV2, "← IGMPv3: 232.1.1.1\nfrom 192.168.1.1\ndata →"]
  - {a: PE1, b: P1, style: dashed}
  - {a: P1, b: PE2, style: dashed}
:::

1. RCV2 sends an IGMPv3 report: 232.1.1.1, INCLUDE 192.168.1.1. PE2 is the only router on that LAN.
2. PE2 finds 232.1.1.1 in its SSM range, so it does not look for an RP. It creates (192.168.1.1, 232.1.1.1) and
   sends an (S,G) Join out of its RPF interface toward 192.168.1.1: Gi0/0/0/0, the direct link to PE1.
3. PE1 receives the Join on Gi0/0/0/0 and adds that interface to the (S,G) entry. SRC1 is directly connected to
   PE1, so the Join goes no further.
4. SRC1 sends. PE1 forwards each packet out of Gi0/0/0/0 only, and PE2 out of Gi0/0/0/3 to RCV2.

P1, the RP, has no entry for 232.1.1.1 at all. PE1 sends no Register, because 232.1.1.1 is in its SSM range too. There
is no switch-over: the very first packet travels on the shortest-path tree, because no other tree exists. Nobody
asked P1 anything.

### 2.3 The SSM range

Which groups are SSM is a setting on each router, the SSM range. IOS XR uses 232.0.0.0/8 by default. A configured
range replaces the default, so the list must name 232.0.0.0/8 too if those groups are still to be SSM. IOS XE has no
SSM range until `ip pim ssm` is configured: `ip pim ssm default` for 232/8, or `ip pim ssm range` with an access
list.

Every router must agree, because each one decides by its own range at the point where it acts. The first-hop router
decides whether a source in the group is registered with an RP. A last-hop router decides whether a report leads to an
(S,G) Join toward the source or a (*,G) Join toward an RP. A router in the middle decides whether a (*,G) Join for the
group is passed on. A router that disagrees breaks the tree at its own place.

ACCESS-3 shows how, with PE4 as the DR there:

- **PE4 with IOS XE's default IGMPv2 on Ethernet0/1.** RCV3's IGMPv3 report naming SRC1 never enters PE4's table, so
  PE4 sends no Join, and RCV3 gets nothing.
- **PE4 with IGMPv3 but without `ip pim ssm`.** PE4 records the report, but takes 232.1.1.1 for a sparse-mode group
  and sends a (*,232.1.1.1) Join toward the RP. PE2, for which 232.1.1.1 is SSM, does not pass it on, and P1 holds
  nothing. RCV3 gets nothing.

In both cases, the four XR routers look healthy: they show what an SSM range should show, and RCV2 keeps receiving.
The fault shows only on PE4 (section 3.2). The XR routers are not wrong; they are just not where the fault is.

### 2.4 Bidirectional PIM: one tree, packets go both ways

Bidirectional PIM (RFC 5015) keeps only the shared tree of sparse mode and lets packets travel on it in both
directions. For each group in a bidirectional range, every router keeps a (*,G) entry that points toward the RP
address, and receivers join it with (*,G) Joins, as on the shared tree of the previous page.

What changes is the sender's side. A router that receives a packet for the group from a sender does not register it.
It sends the packet up the tree, and each router on the way sends a copy out of every interface in the group's list
except the one it came in on. The interface toward the RP is in that list too, so the packet keeps going up while
copies go down the branches that have receivers. No router creates an (S,G) entry, and no router switches to a
shortest-path tree.

The RP address is only the root that every tree points at. Nothing is registered there and nothing is decapsulated;
Cisco's IOS XE overview notes that the RP address does not even have to belong to a router. In the examples, the RP
address is 10.255.1.11, on a loopback of P1 of its own (Loopback1), apart from the sparse-mode RP on Loopback0.

A router on the tree keeps one (*,G) per group, whether the group has one sender or a hundred. When SRC1 only sends
and has not joined, PE1 holds no entry for the group at all, and the packets still reach the receivers: PE1 sends
anything in the bidirectional range up toward the RP.

The cost is the path. Every packet follows the tree, and on the board a packet from SRC1 to RCV2 goes through P1,
never over the direct link between PE1 and PE2, because neither router's route to the RP address uses that link. The
most direct link on the board carries none of the conference.

### 2.5 The designated forwarder

A packet on its way up must be picked up from each link by exactly one router, or it would go up twice. Bidirectional
PIM therefore elects one router on every link, for every RP address: the designated forwarder (DF). The DF is the
router on the link with the best unicast route to the RP address. It forwards the group's packets onto the link, to
the receivers there, and it alone picks up packets from senders on the link and sends them toward the RP.

The figure shows the DF of each link for the RP address 10.255.1.11. On P1's own links, P1 wins (its route to its own
loopback is [0/0]). On the link between PE2 and PE4, PE2 is one link from P1 and PE4 two, so PE2 is the DF. On the
link between PE1 and PE2, both are one link from P1 with the same metric, [115/10], and the DF is PE2, the higher
address. On a LAN with one router, that router is the DF.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP 10.255.1.11)"}
  PE4: {at: [4.6, 2.0], label: "PE4 (DR)"}
  PE3: [3.2, 3.1]
  SW1: [4.6, 3.1]
  RCV3: {at: [6.4, 3.1], kind: host}
links:
  - [SRC1, PE1, "DF: PE1"]
  - [PE1, PE2, "DF: PE2"]
  - [PE2, RCV2, "DF: PE2"]
  - [PE1, P1, "DF: P1"]
  - [P1, PE2, "DF: P1"]
  - [P1, PE3, "DF: P1"]
  - {a: PE2, b: PE4, label: "DF: PE2", t: 0.62}
  - [PE3, SW1]
  - [PE4, SW1]
  - [SW1, RCV3]
frames:
  - {label: "ACCESS-3: DF PE3, DR PE4", nodes: [PE3, SW1, RCV3]}
:::

ACCESS-3 shows the point. PE4 is the DR there (192.168.3.253, the higher address), but PE3 is one link from P1 and
PE4 two, so PE3 is the DF. In bidirectional PIM it is the DF, not the DR, that serves a link's receivers (the IOS XE
configuration guide and RFC 5015).

RCV3's report reaches both routers. PE3 sends the Join toward the RP and forwards the group onto ACCESS-3; PE4 keeps
only an entry that points up toward the RP, with nothing below it. On ACCESS-3, PE4 holds the title and PE3 does the
work.

### 2.6 Key points

- SSM: the receiver names the source in an IGMPv3 INCLUDE report, and the last-hop router joins (S,G) straight toward
  it. No RP, no Register, no switch-over. IGMPv1 and IGMPv2 reports in an SSM range are dropped.
- The SSM range: 232/8 by default on IOS XR, none on IOS XE until `ip pim ssm`; a configured range replaces the
  default. Every router must agree.
- Bidirectional PIM: one (*,G) per group, rooted at the RP address; packets go up and down the same tree. No
  Register, no (S,G), no shortest-path tree.
- The DF: one per link and RP address, the router with the best route to the RP address. The DF, not the DR, serves
  the receivers on a link and picks up its senders' packets.
- The RP address must be in the IGP: the DF election and the tree both follow the unicast route to it.

## 3. Building it in IOS XR

### 3.1 SSM: the default range and a wider one

For 232.0.0.0/8, IOS XR needs nothing beyond what the previous page configured. The range is SSM by default, and IGMP
on IOS XR runs version 3 by default, so the host-facing interfaces of PE1, PE2 and PE3 already accept INCLUDE reports.

To make more groups SSM, give PIM an access list. The list replaces the default, so it names 232.0.0.0/8 as well. Each
line carries the group range in its first address field, where an access list usually has the source, and `any` in
the second. The example adds 239.100.0.0/16 on all four XR routers.

:::config PE1, PE2, P1, PE3 — SSM for 232.0.0.0/8 and 239.100.0.0/16
ipv4 access-list SSM-RANGE
 10 permit ipv4 232.0.0.0 0.255.255.255 any      ## Keep the default range: a configured list replaces it
 20 permit ipv4 239.100.0.0 0.0.255.255 any      ## The added range
!
router pim
 address-family ipv4
  ssm range SSM-RANGE                            ## The groups this list permits are SSM on this router
 !
!
:::

The example puts `ssm range` under `router pim`, `address-family ipv4`. The command reference places it under
`multicast-routing`, `address-family ipv4`; both places gave the same group map.

IOS XE needs two things on PE4: an SSM range, and IGMPv3 on the interface that faces the hosts (Ethernet0/1, on
ACCESS-3). Its IGMP runs version 2 by default.

:::config PE4 (IOS XE) — SSM on 232.0.0.0/8, and IGMPv3 toward ACCESS-3
ip pim ssm default                               ## 232.0.0.0/8 is SSM; without an ip pim ssm line, no group is
interface Ethernet0/1
 ip igmp version 3                               ## The default, version 2, does not record RCV3's version 3 reports
!
:::

:::config PE4 (IOS XE) — the same wider range as on the XR routers
access-list 30 permit 232.0.0.0 0.255.255.255    ## A standard list of group ranges
access-list 30 permit 239.100.0.0 0.0.255.255
ip pim ssm range 30                              ## In place of ip pim ssm default
:::

:::drill xr-m14-4

### 3.2 Checking SSM

Start with the range. `show pim group-map` lists the ranges and the mode of each; an SSM range has no RP (`0.0.0.0`).

```console
RP/0/RP0/CPU0:PE2#show pim group-map 232.1.1.1

IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

232.0.0.0/8*        SSM   config   0      0.0.0.0         
```

To test it, make RCV2 an IGMPv3 host and join the group with SRC1 as the source. Then look at PE2's IGMP table.

```console
RCV2(config)#interface Ethernet0/0
RCV2(config-if)#ip igmp version 3
RCV2(config-if)#ip igmp join-group 232.1.1.1 source 192.168.1.1
RCV2(config-if)#end
RP/0/RP0/CPU0:PE2#show igmp groups 232.1.1.1 detail

Interface:	GigabitEthernet0/0/0/3
Group:		232.1.1.1
Uptime:		00:00:12
Router mode:	INCLUDE
Host mode:	INCLUDE
Last reporter:	192.168.2.1
Suppress:	0
EVPN Remote group: False (Stale: False)
Group source list:
  Source Address   Uptime    Expires   Fwd    EVPNRemoteRoute   Flags
  192.168.1.1      00:00:12  00:01:58  Yes    No                Remote 4
```

`Router mode: INCLUDE` and the source in the list: the report named a source. Now send from SRC1 and read the PIM
topology along the path (excerpt; the flag legends are left out).

```console
SRC1#ping 232.1.1.1 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 232.1.1.1, timeout is 1 seconds:
Reply to request 0 from 192.168.2.1, 12 ms
Reply to request 1 from 192.168.2.1, 2 ms
...
Reply to request 9 from 192.168.2.1, 2 ms
RP/0/RP0/CPU0:PE2#show pim topology 232.1.1.1
...
(192.168.1.1,232.1.1.1)SPT SSM Up: 00:00:25 
JP: Join(00:00:23) RPF: GigabitEthernet0/0/0/0,10.0.12.1 Flags: 
  GigabitEthernet0/0/0/3      00:00:25  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 232.1.1.1
No PIM topology table entries found.
RP/0/RP0/CPU0:PE1#show pim topology 232.1.1.1
...
(192.168.1.1,232.1.1.1)SPT SSM Up: 00:00:29 
JP: Join(never) RPF: GigabitEthernet0/0/0/2,192.168.1.1* Flags: 
  GigabitEthernet0/0/0/0      00:00:29  fwd Join(00:03:00) 
```

- **`SPT SSM`**: an (S,G) entry of an SSM range. There is no (*,G) for the group.
- **PE2's RPF** points at PE1 over the direct link (Gi0/0/0/0, 10.0.12.1), and its receiver interface has `LI`
  (local interest, from IGMP) and `LH` (last hop).
- **PE1's RPF** points at SRC1 itself on Gi0/0/0/2, and Gi0/0/0/0 is in the list because PE2's Join arrived there.
  The entry has no `SR` (sending registers) flag.
- **P1** has nothing: the RP is not on the path and was not told about the group.

After the wider range of section 3.1, the group map lists both SSM ranges:

```console
RP/0/RP0/CPU0:PE2#show pim group-map
...
Group Range         Proto Client   Groups RP address      Info

224.0.1.39/32*      DM    perm     0      0.0.0.0         
224.0.1.40/32*      DM    perm     1      0.0.0.0         
224.0.0.0/24*       NO    perm     0      0.0.0.0         
239.100.0.0/16*     SSM   config   0      0.0.0.0         
232.0.0.0/8*        SSM   config   1      0.0.0.0         
224.0.0.0/4*        SM    config   2      10.255.0.11     RPF: Gi0/0/0/1,10.0.2.11
224.0.0.0/4         SM    static   0      0.0.0.0         RPF: Null,0.0.0.0
```

On IOS XE, `show ip mroute` marks an SSM entry with the flag `s`. Below, RCV3 has joined (192.168.1.1, 232.1.1.1)
with IGMPv3 and PE4 has `ip pim ssm` and IGMPv3 on Ethernet0/1; then the same join to a new group, 232.1.1.3, after
`ip pim ssm` was taken off PE4.

```console
PE4#show ip mroute 232.1.1.1
IP Multicast Routing Table
Flags: D - Dense, S - Sparse, B - Bidir Group, s - SSM Group, C - Connected,
       L - Local, P - Pruned, R - RP-bit set, F - Register flag,
       T - SPT-bit set, J - Join SPT, M - MSDP created entry, E - Extranet,
       X - Proxy Join Timer Running, A - Candidate for MSDP Advertisement,
       U - URD, I - Received Source Specific Host Report, 
...
(192.168.1.1, 232.1.1.1), 00:00:32/00:02:27, flags: sTI
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:32/00:02:27, flags: 

PE4#show ip mroute 232.1.1.3
...
(*, 232.1.1.3), 00:00:31/00:02:34, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:31/00:02:34, flags: 
```

With the range, the entry is an (S,G) with `s` (SSM group), `T` (on the shortest-path tree) and `I` (made from a
source-specific report). Without it, the same report gives a (*,G) with the RP and `S` (sparse): a sparse-mode join
for a group that the XR routers carry as SSM.

PE2, which treats 232.1.1.3 as SSM, did not pass that join on:
`show pim topology 232.1.1.3` on PE2 found no entry, and no ping to 232.1.1.3 was answered.

:::try
See what an SSM router does with a join that names no source. Do it after Task M14-3, and put the host back at the
end.

1. On RCV2, under `interface Ethernet0/0`, configure `ip igmp version 2` and `ip igmp join-group 232.2.2.2`.
2. After about 15 seconds, look at `show igmp groups 232.2.2.2 detail` and `show pim topology 232.2.2.2` on PE2, and
   at `show ip igmp groups` on RCV2.
3. On RCV2, remove both lines (`no ip igmp join-group 232.2.2.2`, `no ip igmp version`).

Example result: PE2 answered `No matching entries in IGMP` and `No PIM topology table entries found.`, while RCV2
listed 232.2.2.2 among its groups. The host lists the group as joined; the router has no record of it.
:::

### 3.3 Bidirectional PIM

Bidirectional PIM takes two things: an RP address that every router can reach, and on every router, the list of
groups that are bidirectional with that RP. The examples make 239.2.0.0/16 bidirectional, with the RP address
10.255.1.11 on a new loopback of P1. The sparse-mode RP of the previous page (10.255.0.11, for all groups) stays.

The figure follows one packet that RCV3 sends to 239.2.2.2, up to the RP address and down to RCV2 and SRC1. All three
hosts have joined the group. Rest the pointer on a number in the figure (or tap it on a phone) to see that part of
the configuration.

:::walk
legend: "One packet from RCV3. Every router holds only (*,239.2.2.2). Blue numbers: what the routers are given."
rows:
  - {node: RCV3, kind: host, say: ["Sends to 239.2.2.2 (a ping)", "_onto ACCESS-3, where PE3 and PE4 both see it"]}
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]]"}
  - panel: PE3
    sub: "IOS XRd · the DF on ACCESS-3"
    items:
      - ref: 2
        head: "**Bidirectional groups** `rp-address 10.255.1.11 BIDIR-GROUPS bidir`"
        say: ["239.2.2.2 is in the list → (*,G) BD, rooted at 10.255.1.11", "Who picks the packet up from ACCESS-3? The DF of the link:"]
        match:
          - ["PE3 192.168.3.252  one link to P1  [115/10]", true, "the DF"]
          - ["PE4 192.168.3.253  two links, through PE2", false, "not the DF"]
        then: ["→ up its RPF interface Gi0/0/0/0, toward 10.255.1.11"]
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]] _CORE-3, going up"}
  - panel: P1
    sub: "10.255.1.11 is its Loopback1"
    items:
      - ref: 1
        head: "**The RP address** `interface Loopback1`, passive in IS-IS"
        say: ["Every router's tree for 239.2.0.0/16 points at this address"]
      - say: ["(*,239.2.2.2): out of every interface that sent a Join, except the one it came in on", "~→ Gi0/0/0/1 to PE2 and Gi0/0/0/0 to PE1; not back out of Gi0/0/0/2"]
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]] _CORE-2, going down"}
  - panel: PE2
    sub: "IOS XRd · the DF on ACCESS-2"
    items:
      - ref: 2
        head: "`rp-address 10.255.1.11 BIDIR-GROUPS bidir`"
        say: ["(*,239.2.2.2) BD, built from RCV2's report; no (S,G)"]
        then: ["→ out of Gi0/0/0/3, where PE2 is the DF"]
  - {node: RCV2, kind: host, say: ["Receives it and answers"]}
  - aside: "P1's other copy"
    say: ["~Gi0/0/0/0 → PE1, the DF on the head-end LAN → SRC1, which answers too"]
  - aside: "PE4 on ACCESS-3: the DR, not the DF"
    say: ["~③ makes 239.2.2.2 bidirectional on PE4 as well. Its DF on Ethernet0/1 is PE3", "~→ PE4 sends nothing up and nothing onto ACCESS-3: its entry is (*,G) with the flags `BP`"]
:::

:::config P1 — an RP address of its own for the bidirectional groups, advertised in IS-IS
interface Loopback1                              ## ① The address that every tree of the bidirectional groups points at
 ipv4 address 10.255.1.11 255.255.255.255
!
router isis CORE
 interface Loopback1                             ## ① Every router needs a route to it: the DF election and the RPF use it
  passive                                        ## Advertise the address; no adjacency on a loopback
  address-family ipv4 unicast
  !
 !
!
:::

:::config PE1, PE2, P1, PE3 — 239.2.0.0/16 as bidirectional groups, rooted at 10.255.1.11
ipv4 access-list BIDIR-GROUPS
 10 permit ipv4 239.2.0.0 0.0.255.255 any        ## ② The bidirectional groups
!
router pim
 address-family ipv4
  rp-address 10.255.0.11                         ## From the previous page: sparse mode, all groups (section 3.4)
  rp-address 10.255.1.11 BIDIR-GROUPS bidir      ## ② The groups in the list are bidirectional, rooted at 10.255.1.11
 !
!
:::

:::config PE4 (IOS XE) — the same groups and RP address
ip pim bidir-enable                              ## ③ On PE4, the bidir keyword is refused until this line is in
access-list 20 permit 239.2.0.0 0.0.255.255      ## ③ The bidirectional groups
ip pim rp-address 10.255.0.11                    ## From the previous page: sparse mode, all groups (section 3.4)
ip pim rp-address 10.255.1.11 20 bidir           ## ③ The same RP address and groups as on the XR routers
:::

IOS XR needs no switch for bidirectional PIM: its neighbours already carry the flag `B` (bidir capable) in `show pim
neighbor`. Support depends on the platform. It works on this virtual platform, while the configuration guide for the
Cisco 8000 lists it as not supported there.

On PE4, the `bidir` keyword of `ip pim rp-address` is refused (`% Invalid input`) until `ip pim bidir-enable` is
configured, and `no ip pim bidir-enable` removes the bidirectional `ip pim rp-address` lines with it. The keyword
exists only once the feature is switched on.

:::drill xr-m14-5

### 3.4 When two static RPs cover the same group

In the examples, 239.2.2.2 matches two static RPs on every router: 10.255.0.11 for all groups (sparse mode) and
10.255.1.11 for 239.2.0.0/16 (bidirectional). IOS XR and IOS XE choose between them by different rules.

- **IOS XR uses the longer range.** 239.2.0.0/16 is longer than 224.0.0.0/4, so XR uses 10.255.1.11, bidirectional.
  `show pim group-map` for one group shows the range that is used. This is the longest match that RFC 7761
  describes; the XR documents do not state the rule.
- **IOS XE uses the RP with the highest address.** The command reference for `ip pim rp-address` (Catalyst 9600,
  IOS XE 17.13) says: "If a multicast group is matched by the access list of more than one configured ip pim
  rp-address command, then the RP for the group is determined by the RP with the highest RP address configured."

```console
RP/0/RP0/CPU0:PE2#show pim group-map 239.2.2.2
...
Group Range         Proto Client   Groups RP address      Info

239.2.0.0/16*       BD    config   1      10.255.1.11     RPF: Gi0/0/0/1,10.0.2.11
PE4#show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s): 224.0.0.0/4, Static
    RP: 10.255.0.11 (?)
Acl: 20, Static, Bidir Mode
    RP: 10.255.1.11 (?)
```

Here the two rules agree: 10.255.1.11 is higher than 10.255.0.11, so PE4 also picks the bidirectional RP, and its
entry for 239.2.2.2 names RP 10.255.1.11 with the flag `B` (section 3.5). Both rules are clear; they are just not the
same rule.

Turn the addresses round and they part. If the sparse-mode RP for all groups were 10.255.1.11 and the bidirectional
RP for 239.2.0.0/16 were 10.255.0.11, the XR routers would still carry 239.2.2.2 as bidirectional (the longer range),
but PE4 would map it to 10.255.1.11, the higher address, as a sparse-mode group.

As the DR on ACCESS-3, PE4 would then register what RCV3 sends and build (S,G) state for it. RCV3 still receives
through PE3, the DF, so delivery alone does not show the fault; PE4's entry does (an (S,G), and no `B`).

On IOS XE, make sure that only one `ip pim rp-address` matches each group: give the sparse-mode RP an access list
that leaves the bidirectional range out. On IOS XR, the longer range wins in any case.

### 3.5 Checking bidirectional PIM

`show pim df winner` lists, for each RP address and interface, the DF of that link and the metrics of its route to
the RP address ([administrative distance/metric]).

```console
RP/0/RP0/CPU0:PE2#show pim df winner

RP               Interface                    DF Winner        Metrics
10.255.1.11      GigabitEthernet0/0/0/2       10.0.4.2         [115/10]
10.255.1.11      GigabitEthernet0/0/0/3       192.168.2.254    [115/10]
10.255.1.11      GigabitEthernet0/0/0/1       10.0.2.11        [0/0]
10.255.1.11      GigabitEthernet0/0/0/0       10.0.12.2        [115/10]
10.255.1.11      Loopback0                    10.255.0.2       [115/10]
RP/0/RP0/CPU0:PE3#show pim df winner

RP               Interface                    DF Winner        Metrics
10.255.1.11      GigabitEthernet0/0/0/1       192.168.3.252    [115/10]
10.255.1.11      GigabitEthernet0/0/0/0       10.0.3.11        [0/0]
10.255.1.11      Loopback0                    10.255.0.3       [115/10]
```

On PE2, the DF toward P1 (Gi0/0/0/1) is P1 itself, 10.0.2.11, with [0/0]; on every other interface, PE2 is the DF
(10.0.4.2, 192.168.2.254, 10.0.12.2 are its own addresses). On PE3, the DF on ACCESS-3 (Gi0/0/0/1) is PE3,
192.168.3.252.

The topology holds only a (*,G), marked `BD`, even after every host has sent (excerpt):

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.2.2.2
...
(*,239.2.2.2) BD Up: 00:00:58 RP: 10.255.1.11 
JP: Join(now) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH DSS 
  GigabitEthernet0/0/0/3      00:00:58  fwd LI LH 
RP/0/RP0/CPU0:PE2#show mrib route 239.2.2.2
...
(*,239.2.2.2) RPF nbr: 10.0.2.11 Flags: IA RPF Inherit: 239.2.0.0/16
  Up: 00:00:58
  Outgoing Interface List
    GigabitEthernet0/0/0/1 Flags: F, Up: 00:00:58
    GigabitEthernet0/0/0/3 Flags: F LI, Up: 00:00:58
RP/0/RP0/CPU0:P1#show pim topology 239.2.2.2
...
(*,239.2.2.2) BD Up: 00:00:58 RP: 10.255.1.11* 
JP: Join(never) RPF: Loopback1,10.255.1.11* Flags: 
  GigabitEthernet0/0/0/0      00:00:58  fwd Join(00:02:31) 
  GigabitEthernet0/0/0/1      00:00:56  fwd Join(00:02:33) 
  GigabitEthernet0/0/0/2      00:00:41  fwd Join(00:02:48) 
```

- **`BD`**: the entry belongs to a bidirectional range. There is no (S,G) line, although SRC1 and RCV3 have both sent.
- **`DSS`** (Don't Signal Sources) on PE2's (*,G): the same flag appears under `spt-threshold infinity`; either way,
  the router stays on the (*,G).
- **The MRIB's outgoing list holds the RPF interface** (Gi0/0/0/1, `F`). That is what makes the tree bidirectional:
  what RCV2 sends goes up toward P1. A sparse-mode entry keeps its RPF interface in a separate incoming list, marked
  `A` (accept); this entry has no incoming list and inherits what it accepts from the range (`IA`, `Inherit:
  239.2.0.0/16`).
- **P1** is the root: `RP: 10.255.1.11*` (itself), RPF to Loopback1, and a Join from each of PE1, PE2 and PE3.

On IOS XE, `show ip pim interface df` gives the DF of each interface, with `*` where PE4 itself is the DF, and `show ip
mroute` marks the entry with `B`.

```console
PE4#show ip pim interface df
* implies this system is the DF
Interface                RP               DF Winner        Metric     Uptime
Ethernet0/1              10.255.1.11       192.168.3.252    10         00:00:08
Ethernet0/0              10.255.1.11       10.0.4.2         10         00:00:16
PE4#show ip mroute 239.2.2.2
...
(*, 239.2.2.2), 00:00:57/00:02:20, RP 10.255.1.11, flags: BP
  Bidir-Upstream: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/0, Bidir-Upstream/Sparse, 00:00:57/stopped, flags: 
```

PE4 is the DF nowhere (no `*`). Its entry has `B` (bidir group) and `P` (pruned), and the only interface in it is
the way up, Ethernet0/0. Ethernet0/1 is not there although RCV3 has joined: PE3 serves ACCESS-3.

The simplest test is a ping from a host (excerpt). Every host that joined answers each request once:

```console
RCV3#ping 239.2.2.2 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 239.2.2.2, timeout is 1 seconds:
Reply to request 0 from 192.168.3.1, 1 ms
Reply to request 0 from 192.168.1.1, 4 ms
Reply to request 0 from 192.168.2.1, 4 ms
...
Reply to request 9 from 192.168.3.1, 1 ms
Reply to request 9 from 192.168.1.1, 3 ms
Reply to request 9 from 192.168.2.1, 2 ms
```

192.168.3.1 is RCV3 answering its own ping; SRC1 (192.168.1.1) and RCV2 (192.168.2.1) are the other two members.

### 3.6 Pitfalls

- **IOS XE without `ip pim ssm`**: no group is SSM there. PE4 sends (*,G) Joins for 232/8 toward the RP, PE2 does not
  pass them on, and RCV3 gets nothing while the XR routers look healthy.
- **IGMPv2 on the DR's host interface**: IOS XE's default. RCV3's version 3 reports are not recorded, and nothing is
  joined.
- **A configured SSM range without 232/8**: the list replaces the default, and 232/8 is then no longer SSM on that
  router.
- **A host that joins without a source**: in an SSM range, IGMPv1 and IGMPv2 reports are dropped. The router's IGMP
  table shows nothing, while the host shows the group as joined.
- **A host left in version 2 mode**: if a router interface ran IGMPv2 for a while, its hosts answer in version 2.
  Setting the interface back to version 3 does not bring them back at once: a host keeps to version 2 for a while
  after the last version 2 query (with a 60-second query interval, 2 × 60 + 10 = 130 seconds by RFC 3376), and SSM
  stays dark until then.
- **Testing with the same group right after a change**: a Join sent before the change can keep a group flowing for
  up to 210 seconds, its hold time. Test with a group that nobody has joined yet.
- **`ip pim bidir-enable` on PE4**: without it, the `bidir` keyword is refused; `no ip pim bidir-enable` takes the
  bidirectional `ip pim rp-address` lines with it.
- **An IOS XE access list named `BIDIR`**: `ip pim rp-address … BIDIR bidir` fails with `% Ambiguous command`, because
  the name collides with the keyword. A numbered list works.
- **Two static RPs for one group**: IOS XR uses the longer range, IOS XE the higher RP address. Keep the lists from
  overlapping on IOS XE.
- **The RP address outside IS-IS**: the DF election and the tree both follow the unicast route to the RP address.
  Advertise the loopback that carries it.
- **Judging bidirectional PIM by delivery alone**: a router that has the mode wrong can still leave every host
  receiving, through the DF. Look for (S,G) entries and the `B` flag on every router.
- **Expecting the DR to serve the receivers**: in bidirectional PIM, the DF does. On ACCESS-3, PE4's entry has no LAN
  interface, and that is correct.

## Practice

Do Tasks M14-3 and M14-4 in lab **XRT-16**. The tasks use other ranges and another RP than the examples on this page.

<p class="tolab"><a href="/_learn?id=XRT-16">Open lab XRT-16 in the workspace</a> — <a href="f3-m14-practice-2.html">Tasks M14-3 and M14-4</a></p>

:::note
The output on this page was taken on XRT-16: IOS XRd 26.1.1 (PE1, PE2, P1, PE3) and IOS XE 17.15 on IOL (PE4 and the
hosts). Some results come from a test board on which PE1, PE2 and P1 had the same names and addresses (PE1 and PE2
were IOS XRv 9000 26.1.1 there) and the IOS XE 17.15 router on the shared LAN was called R5: the IGMPv2 join of
232.2.2.2, the two faults of section 2.3, PE1 holding no entry when SRC1 only sends,
the hosts' return to IGMPv3 (between 103 and 136 seconds after the router interface went back to version 3), and the Joins that
kept a group flowing after a change. The access-list name `BIDIR` comes from an earlier test on IOL 17.15.
Sources: the Multicast Command Reference for the Cisco 8000 and for the ASR 9000 (2026-09-11): SSM enabled by default
on 232/8, a configured range replacing it, `ssm range` under `multicast-routing`, and `ssm map` with the dropping of
IGMPv1 and IGMPv2 reports in an SSM range. The Multicast Configuration Guide for the Cisco 8000, IOS XR 26.1.x–26.3.x
(PIM Bidir listed as not supported on the Cisco 8000). For IOS XE: the IP Multicast PIM Configuration Guide, IOS XE
16.9, "IP Multicast Technology Overview" (SSM needs IGMPv3; bidirectional PIM forwards on (*,G) only, without
Register, and its RP address need not belong to a router); the Catalyst 9300 IP Multicast Routing Configuration
Guide, IOS XE 17.15, "Configuring PIM" (the DF has the most preferred unicast route to the RP, one DF for every RP of
bidirectional groups, only (*,G) entries for bidirectional groups; paraphrased); the IOS XE guide's statement that
the DF, not the DR, forwards to the receivers on a link; the Cisco IOS IP Multicast Command Reference (`ip pim ssm`
disabled by default; the `show ip mroute` flags `s`, `I` and `B`); the Catalyst 9600 Command Reference, IOS XE 17.13
(`ip pim rp-address`, quoted in section 3.4, and `ip pim bidir-enable`). RFC 3376 (IGMPv3, INCLUDE mode, and how long
a host keeps to an older version), RFC 4604 (section 3.5, version 1 and 2 reports in SSM ranges), RFC 4607 (232/8),
RFC 5015 (bidirectional PIM and the DF), RFC 7761 (section 4.7.1, the longest match of group ranges; the Join hold
time of 210 seconds). All checked in November 2026.
Where the documents and the devices differ or are silent: the Cisco 8000 guide lists bidirectional PIM as not
supported, and no document covers multicast on IOS XRd; both worked on IOS XRd and IOS XRv 9000 here. The XR documents
do not state how XR chooses between two static RPs for one group; the longer range was used. The Catalyst 9600
reference gives `ip pim bidir-enable` as enabled by default; on PE4 (IOL 17.15), the `bidir` keyword was refused until
it was configured. The command reference places `ssm range` under `multicast-routing`, where the 26.1.1 CLI help marks
it `cisco-support`; the same range worked there and under `router pim`. `show pim df winner` is not in the current
command references (only in the older one for the CRS). On the link between PE1 and PE2, where both routers had the
same metric, the higher address became the DF; the tie-break was not checked in the documents above.
:::
