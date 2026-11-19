# M14 — Delivering one stream to many: IGMP and PIM sparse mode

The previous page laid out the whole unit. This page starts with the plainest case: one TV channel, sent by one
head-end and watched by many set-top boxes. The boxes tell their routers what they want with IGMP, and the routers
build a tree for the channel with PIM sparse mode, through a meeting point called the rendezvous point (RP).

The page covers PIM sparse mode from 4.4.a of the blueprint and IGMP versions 1, 2 and 3 from 4.4.b. The board is
XRT-16, drawn at the start of section 2. Source-specific multicast and bidirectional PIM are on the page *Two other
trees: SSM and bidirectional PIM*; finding the RP without configuring it by hand, IPv6 and troubleshooting are on
*Finding the RP, IPv6, and troubleshooting*.

## 1. What it is good for

### 1.1 The problem: one channel, many set-top boxes

On XRT-16, SRC1 stands in for the provider's head-end, which sends the TV channels, and RCV2 and RCV3 stand in for
set-top boxes in customers' homes. A channel is a stream of packets that goes on for hours. A box wants the channel it
is tuned to, and only while it is tuned to it; boxes change channels whenever their viewers do.

The boxes sit behind different routers: RCV2 behind PE2, and RCV3 on ACCESS-3, an access LAN that PE3 and PE4 share.
The head-end does not know which boxes are watching. A real provider has far more than two boxes and one channel, and
the same channel is watched behind many routers at the same time.

### 1.2 What came before: one copy per receiver, or flooding

- **A unicast copy for each receiver**: SRC1 sends each box its own copy, addressed to the box. With two boxes, every
  packet crosses the HEADEND link twice, and again on every link that the two paths share; with a thousand boxes, a
  thousand times. The head-end has to keep the list of who is watching.
- **Broadcast**: a broadcast reaches every host on one LAN and stops at the router. It cannot reach boxes behind
  other routers, and on its own LAN every host gets it, tuned in or not.
- **Flood and prune**: an older design (PIM dense mode) first sends every group out of every link, and routers that
  have no receivers then ask their neighbours to stop. Links where nobody is watching still carry the start of every
  channel.

The first repeats the channel once per viewer; the other two send it where nobody asked. The links pay either way.

### 1.3 The multicast answer: one copy per link

- **Sent once, to a group**: SRC1 sends each packet once, to a group address such as 239.1.1.1. The group stands for
  whoever wants the channel. The source address stays SRC1's own unicast address.
- **The receivers ask their own router**: a box tells the router on its LAN which groups it wants, with IGMP
  (section 2.2). The head-end never hears from the box.
- **The routers build a tree**: with PIM, the routers build a delivery tree from the source to every router that has
  receivers. A router copies a packet only where the tree branches, so a link carries at most one copy, however many
  boxes watch behind it.
- **The tree follows the audience**: a router joins the tree when its first receiver joins, and leaves it when its
  last receiver goes.

On the board, one copy goes from SRC1 through PE1 to PE2, and PE2 makes one copy for RCV2's LAN and one for PE4. SRC1
sends the same amount whether two boxes watch or two thousand. It has no way of telling which.

## 2. How it works: one channel from SRC1 to RCV2 and RCV3

XRT-16 has five routers. PE1, PE2, P1 and PE3 run IOS XRd 26.1.1 and PE4 runs IOS XE 17.15; SRC1, RCV2 and RCV3 are
IOS XE routers acting as hosts. All five routers run IS-IS (instance CORE, level 2).

The access links are passive, so ACCESS-3 never carries traffic between PE3 and PE4. On this page P1 is the RP. XRd
forwards multicast on this virtual platform; Cisco's documents do not cover multicast on XRd (see the note at the
end).

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1 (head-end)"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2 (set-top box)"}
  P1: {at: [3.5, 1.45], label: "P1 (RP 10.255.0.11)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4 (IOS XE)"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3 (set-top box)"}
links:
  - {a: SRC1, b: PE1, label: "HEADEND", lb: "Gi0/0/0/2", t: 0.3, tb: 0.7}
  - {a: PE1, b: PE2, label: "10.0.12.0/24", la: "Gi0/0/0/0", lb: "Gi0/0/0/0", ta: 0.16, tb: 0.84}
  - {a: PE1, b: P1, label: "10.0.1.0/24", la: "Gi0/0/0/1", lb: "Gi0/0/0/0", ta: 0.18, tb: 0.82}
  - {a: P1, b: PE2, label: "10.0.2.0/24", la: "Gi0/0/0/1", lb: "Gi0/0/0/1", ta: 0.18, tb: 0.82}
  - {a: P1, b: PE3, label: "10.0.3.0/24", la: "Gi0/0/0/2", lb: "Gi0/0/0/0", ta: 0.22, tb: 0.78}
  - {a: PE2, b: PE4, label: "10.0.4.0/24", la: "Gi0/0/0/2", lb: "Et0/0", ta: 0.3, tb: 0.8}
  - {a: PE2, b: RCV2, label: "ACCESS-2", la: "Gi0/0/0/3", t: 0.75, ta: 0.3}
  - {a: PE3, b: SW1, la: "Gi0/0/0/1 .252", ta: 0.42}
  - {a: PE4, b: SW1, la: "Et0/1 .253", ta: 0.4}
  - {a: SW1, b: RCV3, lb: ".1", tb: 0.72}
frames:
  - {label: "ACCESS-3 192.168.3.0/24", nodes: [SW1, RCV3]}
:::

Two things on this board shape the trees. PE2's shortest path to SRC1 is the direct link to PE1, but its path to the
RP goes through P1, so the tree through the RP and the shortest tree part at PE2. And ACCESS-3 has two routers, PE3
(.252) and PE4 (.253), while RCV3's default gateway is PE4.

A host that has joined a group answers pings sent to the group, so a ping from SRC1 to a group shows who received it.
The examples on this page use 239.1.1.1 as the TV channel.

### 2.1 Group addresses

A multicast packet is addressed to a group, not to a host. IPv4 sets aside 224.0.0.0/4 (224.0.0.0 to 239.255.255.255)
for groups. The source address is always the sender's own unicast address; only the destination is a group.

| Range | What it is for | On XRT-16 |
|---|---|---|
| 224.0.0.0/24 | Link-local: protocols on one link. Routers do not forward it, and it is usually sent with TTL 1. 224.0.0.1 is all hosts, 224.0.0.2 all routers, 224.0.0.13 all PIM routers, 224.0.0.22 IGMPv3 reports | In XR's group map with the mode `NO` |
| 224.0.1.0 to 238.255.255.255 | Globally scoped groups; 232.0.0.0/8 inside it is set aside for SSM (next row) | — |
| 232.0.0.0/8 | Source-specific multicast (SSM): the receiver names the source as well (*Two other trees*) | XR treats it as SSM by default |
| 239.0.0.0/8 | Administratively scoped: for use inside one organisation, like private unicast addresses | The TV channels on this page |

`show pim group-map` shows how a router treats each range. This is PE2 once multicast and the RP are configured
(section 3). A `*` marks a line in use; 224.0.1.39 and 224.0.1.40 belong to Auto-RP, one of the ways of finding the RP
(*Finding the RP*).

```console
RP/0/RP0/CPU0:PE2#show pim group-map
IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

224.0.1.39/32*      DM    perm     0      0.0.0.0         
224.0.1.40/32*      DM    perm     1      0.0.0.0         
224.0.0.0/24*       NO    perm     0      0.0.0.0         
232.0.0.0/8*        SSM   config   0      0.0.0.0         
224.0.0.0/4*        SM    config   0      10.255.0.11     RPF: Gi0/0/0/1,10.0.2.11
224.0.0.0/4         SM    static   0      0.0.0.0         RPF: Null,0.0.0.0
```

On an Ethernet LAN a group address becomes a MAC address: 01:00:5e followed by the low 23 bits of the group address.
A group address has 28 bits that can vary (224.0.0.0/4 fixes the first four), so five bits are lost and 32 groups
share each MAC address.

239.1.1.1 becomes 01:00:5e:01:01:01, and so do 224.1.1.1 and 239.129.1.1. A network card
that listens for 01:00:5e:01:01:01 takes in all 32 groups, and the host drops the ones it did not ask for by their IP
address. To the card, a channel on 239.1.1.1 and another on 239.129.1.1 are the same channel.

### 2.2 IGMP: the receiver tells its router

IGMP (Internet Group Management Protocol) runs between hosts and the routers on their own LAN, and nowhere else. The
router asks and the hosts answer; between routers, PIM takes over (section 2.4).

- **Query**: one router on the LAN, the querier, asks which groups are wanted. A general query goes to 224.0.0.1 (all
  hosts), every 60 seconds by default on both IOS XR and IOS XE, and gives the hosts up to 10 seconds to answer (the
  max response time).
- **Report**: a host says that it wants a group, when it joins and again in answer to each query.
- **Leave** (version 2 and later): a host says that it is leaving a group, to 224.0.0.2 (all routers). The querier
  then asks about that group alone (a group-specific query) and removes it if nobody answers within the last member
  query interval, 1 second on both IOS XR and IOS XE.

| | IGMPv1 | IGMPv2 | IGMPv3 |
|---|---|---|---|
| A report says | I want group G | I want group G | I want group G, from these sources only (INCLUDE) or from every source but these (EXCLUDE) |
| Leaving a group | No message: the group times out | A Leave, then a group-specific query | Another report: the host's list for G changes to no sources |
| Max response time in a query | No | Yes | Yes |
| The default on | — | IOS XE (PE4, and the hosts) | IOS XR (PE1, PE2, P1, PE3) |

Version 3 reports all go to 224.0.0.22, and source-specific multicast needs version 3 (*Two other trees*). A host
drops to an older version when its router asks in one: when PE2's interface towards RCV2 is set to version 1, the IOS
XE host RCV2 shows `Current IGMP host version is 1` (section 3.3).

With versions 2 and 3, the router with the lowest IP address on the LAN becomes the querier. The PIM designated router
(DR, section 2.4) is chosen the other way round, by the highest address after a priority, so on a LAN with two
routers the two jobs can go to different routers. On ACCESS-3 they do: PE3 (.252) is the querier and PE4 (.253) is
the DR.

```console
RP/0/RP0/CPU0:PE3#show igmp interface GigabitEthernet0/0/0/1
GigabitEthernet0/0/0/1 is up, line protocol is up
  Internet address is 192.168.3.252/24
  IGMP_AFD is enabled on interface
  Multihoming is disabled on interface [Stale : False]
  Location is 0xe
  Current IGMP version is 3
  IGMP query interval is 60 seconds
  IGMP querier timeout is 125 seconds
  IGMP max query response time is 10 seconds
  Last member query response interval is 1 seconds
  IGMP activity: 43 joins, 40 leaves
  IGMP querying router is 192.168.3.252 (this system)
  Time elapsed since last query sent 00:00:52
  Time elapsed since IGMP router enabled 00:01:00
  Time elapsed since last report received 00:00:45
PE4#show ip igmp interface Ethernet0/1
Ethernet0/1 is up, line protocol is up
  Internet address is 192.168.3.253/24
  IGMP is enabled on interface
  Current IGMP host version is 2
  Current IGMP router version is 2
  IGMP query interval is 60 seconds
...
  IGMP max query response time is 10 seconds
...
  Multicast designated router (DR) is 192.168.3.253 (this system)
  IGMP querying router is 192.168.3.252  
```

PE3 runs version 3 and PE4 version 2, each its own default. RFC 3376 and the IOS XR documents both want one version on all
the routers of a LAN (the RFC says to set them to the lowest one in use), so ACCESS-3 as built is outside the rules;
*Two other trees* comes back to it. The two routers do agree on who asks: PE4 lists PE3 as the querier.

RCV2 reports with version 2, the IOS XE default. PE2 keeps every membership in version 3 terms: `EXCLUDE` with an
empty source list means every source. `Expires` counts down and starts again with each report; when it runs out, the
group is removed from the interface.

```console
RP/0/RP0/CPU0:PE2#show igmp groups 239.1.1.1 detail
Interface:	GigabitEthernet0/0/0/3
Group:		239.1.1.1
Uptime:		00:00:19
Router mode:	EXCLUDE (Expires: 00:01:50)
Host mode:	INCLUDE
Last reporter:	192.168.2.1
Suppress:	0
EVPN Remote group: False (Stale: False)
Source list is empty
```

IPv6 has the same protocol under another name: MLD (Multicast Listener Discovery), carried in ICMPv6. MLDv1
corresponds to IGMPv2 and MLDv2 to IGMPv3, and IOS XR runs MLDv2 by default; it comes with IPv6 in *Finding the RP*.

### 2.3 RPF: a packet must arrive on the way back to its source

Unicast forwarding looks only at the destination. Multicast cannot: the destination is a group, and the group is
wherever its members are. A multicast router looks at the source instead. It forwards a packet only if the packet came
in on the interface that the router itself would use to send to the packet's source. This is the reverse path
forwarding (RPF) check, and a packet that fails it is dropped. On the shared tree (section 2.4) the check is made
against the RP's address instead of the source's.

Without the check, copies could go round in circles: PE1, P1 and PE2 form a triangle, and every router copies onto
every branch it has. With it, each router accepts the channel on one interface only, and copies it onto the others.

The interface comes from the unicast routing table. PIM has no routing protocol of its own, which is what "protocol
independent" in its name means; on XRT-16 the routes come from IS-IS. `show pim rpf` shows what PIM found.

```console
RP/0/RP0/CPU0:PE2#show pim rpf
Table: IPv4-Unicast-default
* 192.168.1.1/32 [115/10] 
    via GigabitEthernet0/0/0/0 with rpf neighbor 10.0.12.1
* 10.255.0.11/32 [115/10] 
    via GigabitEthernet0/0/0/1 with rpf neighbor 10.0.2.11
```

From PE2, SRC1 (192.168.1.1) is out of Gi0/0/0/0 through PE1 (10.0.12.1), and the RP is out of Gi0/0/0/1 through P1.
The same lookup decides where PIM sends its Joins: a router joins a tree by sending a Join to its RPF neighbour,
towards the source or the RP, and the packets come back down the same way. The trees are built backwards, from the
receivers. The data flows from the source; the requests flow towards it.

### 2.4 PIM sparse mode: the shared tree through the RP

PIM (Protocol Independent Multicast) runs between routers. A PIM router sends Hellos on each of its interfaces every
30 seconds and so finds its PIM neighbours. On each LAN the neighbours elect a designated router (DR): the highest DR
priority (1 by default) wins, then the highest IP address. The DR does the work for the hosts on its LAN: it joins
trees for the receivers and registers the senders (section 2.5).

Sparse mode sends a group only where it has been asked for. A request needs somewhere to go before anyone knows where
the sources are, so every group has a rendezvous point (RP): one router that all the routers know as the meeting
point for the group. The receivers' routers join towards the RP, and the sources are made known to it. The tree from
the RP to the receivers is the **shared tree**, written (*,G): any source, group G.

On this page P1's Loopback0 (10.255.0.11) is the RP for every group, configured by hand on every router
(section 3.2). The shared tree for 239.1.1.1 grows one hop at a time, as RCV2 and RCV3 join. The numbers match the
figure below.

- ① RCV2 reports 239.1.1.1. PE2, the only router on ACCESS-2 and so its DR, creates the entry (*,239.1.1.1) with
  Gi0/0/0/3 in its outgoing list.
- ② PE2 looks up the group's RP (10.255.0.11) and its RPF interface towards it (Gi0/0/0/1), and sends a (*,G) Join to
  P1. P1 is the RP: it creates (*,239.1.1.1) with Gi0/0/0/1, towards PE2, in its outgoing list. The tree has its root
  and goes no further up.
- ③ RCV3 reports 239.1.1.1 on ACCESS-3. PE4, the DR there, creates (*,239.1.1.1).
- ④ PE4's RPF neighbour towards the RP is PE2 (10.0.4.2), so its Join goes to PE2. PE2 already has (*,239.1.1.1): it
  adds Gi0/0/0/2, towards PE4, to the outgoing list, and sends nothing new towards P1. One Join upstream covers every
  branch below it.
- ⑤ PE3 hears RCV3's report as well, but it is not the DR on ACCESS-3, so it sends no Join. PE3 is one hop from the
  RP; the branch goes through PE4 all the same, because 253 is more than 252.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2 (DR on ACCESS-2)"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3 (querier, not DR)"}
  PE4: {at: [5.1, 1.65], label: "PE4 (DR on ACCESS-3)"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1, style: dashed}
  - {a: PE1, b: PE2, style: dashed}
  - {a: PE1, b: P1, style: dashed}
  - {a: P1, b: PE2, label: "② (*,G) Join\nPE2 → P1"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "④ (*,G) Join\nPE4 → PE2"}
  - {a: PE2, b: RCV2, label: "① IGMP report", t: 0.6}
  - {a: PE3, b: SW1, style: dashed, label: "⑤ no Join", t: 0.45}
  - {a: PE4, b: SW1, label: "③ IGMP report", t: 0.5}
  - {a: SW1, b: RCV3}
:::

A tree is kept only while it is asked for. Each router repeats its Joins every 60 seconds, and a router removes a
branch that has not been refreshed for 210 seconds. When the last receiver behind a router leaves, the router sends a
Prune upstream instead of a Join.

`show pim topology` shows PIM's entries. Here they are on PE2, P1, PE4 and PE1 once both boxes have joined, before
SRC1 sends anything.

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:20 RP: 10.255.0.11 
JP: Join(00:00:29) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/2      00:00:17  fwd Join(00:03:12) 
  GigabitEthernet0/0/0/3      00:00:20  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:22 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:22  fwd Join(00:03:07) 
PE4#show ip mroute 239.1.1.1
...
(*, 239.1.1.1), 00:00:21/00:02:41, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:21/00:02:41, flags: 
RP/0/RP0/CPU0:PE1#show pim topology 239.1.1.1
No PIM topology table entries found.
```

- `(*,239.1.1.1) SM … RP: 10.255.0.11`: the shared-tree entry, in sparse mode, with its RP.
- `JP: Join(00:00:29)`: PE2 has joined upstream and will repeat the Join in 29 seconds.
- `RPF: GigabitEthernet0/0/0/1,10.0.2.11`: the way to the RP, through P1.
- `Flags: LH`: PE2 is a last-hop router; it has receivers on its own LAN.
- `GigabitEthernet0/0/0/2 … fwd Join(00:03:12)`: the branch made by PE4's Join. It expires in 3 minutes 12 seconds
  unless the next Join comes.
- `GigabitEthernet0/0/0/3 … fwd LI LH`: local interest, from IGMP.
- On P1, `JP: Join(never)` and `RPF: Decapstunnel1`: the root has nobody upstream to join (Decapstunnel is in
  section 2.5).

PE4 (IOS XE) shows the same tree in `show ip mroute`. Its flags `SJC` mean sparse mode, J, and a member on a connected
interface; J says that, with the default setting, this router joins the source tree when a packet arrives
(section 2.6). PE1, one hop from SRC1, has no entry at all. Nobody has sent anything yet.

### 2.5 Register: how the RP learns the source

A sender needs no IGMP: SRC1 simply starts sending to 239.1.1.1. PE1 is the DR on SRC1's LAN, the first-hop router,
and it gets a packet for a group it has no tree for. It looks up the group's RP and sends the packet there in a
Register message: the whole multicast packet inside a unicast PIM packet addressed to 10.255.0.11. Unicast routing
takes it to P1; no tree is needed for that.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1 (first hop)"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1, label: "to 239.1.1.1", t: 0.4}
  - {a: PE1, b: PE2, style: dashed}
  - {a: PE1, b: P1, label: "① Register (unicast) PE1 → P1\n③ (S,G) Join P1 → PE1\n④ Register-Stop P1 → PE1"}
  - {a: P1, b: PE2, label: "② shared tree\nP1 → PE2"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "② shared tree"}
  - {a: PE2, b: RCV2}
  - {a: PE3, b: SW1, style: dashed}
  - {a: PE4, b: SW1}
  - {a: SW1, b: RCV3}
:::

② P1 takes the multicast packet out of the Register and sends it down the shared tree, so the first packets reach RCV2
and RCV3 this way.

IOS XR shows the unwrapping as an interface: on the RP, the entry for the source names a
Decapstunnel interface as the one its packets come in on (here Decapstunnel1; the number is not fixed). P1's MFIB
(section 3.5) counted three packets taken out of Registers and two sent on down the shared tree, 100 bytes each.

```console
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.1 detail
...
Forwarding/Replication Counts: Packets in/Packets out/Bytes out
Failure Counts: RPF / TTL / Empty Olist / Encap RL / Other
...
(192.168.1.1,239.1.1.1),  Flags:  , FMA: 0x0 ,
  Object-ID: 0xfffffffffffffffe 18446744073709551614
  Up: 00:00:17
  Last Used: 00:00:15
  SW Forwarding Counts: 3/2/200
  SW Replication Counts: 3/2/200
  SW Failure Counts: 0/0/0/0/0
...
  Decapstunnel1 Flags:  A, Up:00:00:15 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
```

③ Registers are meant only for the start. P1 also joins the source tree: it sends an (S,G) Join towards SRC1, through
PE1; (S,G) means this source and this group. ④ When the packets reach P1 natively, down that tree, P1 sends PE1 a
Register-Stop, and PE1 stops wrapping them. If the RP has no receivers for the group when a Register arrives, it
answers with a Register-Stop straight away.

The RP's (S,G) entry towards the source looks like this. The output comes from section 3.4, where the last-hop
routers stay on the shared tree, so P1 keeps this Join; `RR` means that a Register was received. With the defaults,
the next section shows what becomes of it.

```console
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:40 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:40  fwd Join(00:02:49) 

(192.168.1.1,239.1.1.2)SPT SM Up: 00:00:21 
JP: Join(00:00:28) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:10) RA RR (00:04:15) 
  No interfaces in immediate olist
```

### 2.6 Switching to the shortest-path tree

The shared tree takes the channel PE1 → P1 → PE2, but PE2's shortest way to SRC1 is the direct link to PE1. Once a
last-hop router knows the source (the first packet down the shared tree carries its address), it can join the source
directly. IOS XR and IOS XE both do so by default, as soon as the first packet arrives.

- ① PE2 sends an (S,G) Join for (192.168.1.1, 239.1.1.1) to its RPF neighbour for SRC1: PE1, over Gi0/0/0/0. PE1
  adds Gi0/0/0/0 to its (S,G) outgoing list, and the packets reach PE2 over the direct link.
- ② PE2 no longer needs this source on the shared tree. It sends P1 an (S,G,rpt) Prune: a Prune for one source, on
  the shared tree only. P1 marks Gi0/0/0/1 `off` for this source.
- ③ P1 is left with nobody who wants SRC1's packets from it. Its own (S,G) entry stops joining (`JP: Null`), and PE1's
  (S,G) entry sends only towards PE2.
- ④ PE4, the last-hop router for RCV3, switches too. Its RPF neighbour for SRC1 is PE2, so its (S,G) Join goes to
  PE2, which adds Gi0/0/0/2 to its (S,G) entry.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1}
  - {a: PE1, b: PE2, label: "① (S,G) Join PE2 → PE1\nsource tree: PE1 → PE2"}
  - {a: PE1, b: P1, style: dashed, label: "③ no longer joined"}
  - {a: P1, b: PE2, style: dashed, label: "② (S,G,rpt) Prune\nPE2 → P1"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "④ (S,G) Join\nPE4 → PE2"}
  - {a: PE2, b: RCV2}
  - {a: PE3, b: SW1, style: dashed}
  - {a: PE4, b: SW1}
  - {a: SW1, b: RCV3}
:::

SRC1's ten pings went out while all this happened. The first two got no reply, and request 3 got two replies from
each box; from request 4 on, each box answered each request once.

```console
# Only the Sending and Reply lines are kept
SRC1#ping 239.1.1.1 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 239.1.1.1, timeout is 1 seconds:
Reply to request 2 from 192.168.2.1, 16 ms
Reply to request 2 from 192.168.3.1, 23 ms
Reply to request 3 from 192.168.2.1, 4 ms
Reply to request 3 from 192.168.3.1, 6 ms
Reply to request 3 from 192.168.2.1, 5 ms
Reply to request 3 from 192.168.3.1, 4 ms
Reply to request 4 from 192.168.2.1, 3 ms
Reply to request 4 from 192.168.3.1, 3 ms
Reply to request 5 from 192.168.2.1, 3 ms
Reply to request 5 from 192.168.3.1, 3 ms
...
```

The state afterwards, on PE2, PE1, P1 and PE4:

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:43 RP: 10.255.0.11 
JP: Join(00:00:06) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/2      00:00:41  fwd Join(00:02:48) 
  GigabitEthernet0/0/0/3      00:00:43  fwd LI LH 

(192.168.1.1,239.1.1.1)SPT SM Up: 00:00:14 
JP: Join(00:00:35) RPF: GigabitEthernet0/0/0/0,10.0.12.1 Flags: KAT(00:03:19) RA 
  GigabitEthernet0/0/0/2      00:00:14  fwd Join(00:03:15) 
RP/0/RP0/CPU0:PE1#show pim topology 239.1.1.1
...
(192.168.1.1,239.1.1.1)SPT SM Up: 00:00:12 
JP: Join(never) RPF: GigabitEthernet0/0/0/2,192.168.1.1* Flags: KAT(00:03:19) RA 
  GigabitEthernet0/0/0/0      00:00:10  fwd Join(00:03:19) 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:41 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:41  fwd Join(00:02:48) 

(192.168.1.1,239.1.1.1)RPT SM Up: 00:00:11 RP: 10.255.0.11* 
JP: Prune(never) RPF: Decapstunnel1,10.255.0.11 Flags: KAT(00:03:21) RA DCC RR (00:04:23) 
  GigabitEthernet0/0/0/1      00:00:11  off Prune(00:03:18) 

(192.168.1.1,239.1.1.1) SM Up: 00:00:13 
JP: Null(never) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:21) RA DCC RR (00:04:23) 
  No interfaces in immediate olist
PE4#show ip mroute 239.1.1.1
...
(*, 239.1.1.1), 00:00:44/stopped, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:44/00:02:18, flags: 

(192.168.1.1, 239.1.1.1), 00:00:17/00:02:42, flags: JT
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:17/00:02:42, flags: 
```

- PE2 has two entries. The (*,G) stays, and `(192.168.1.1,239.1.1.1)SPT` has `RPF: GigabitEthernet0/0/0/0,10.0.12.1`:
  the source tree, over the direct link, with PE4's branch on Gi0/0/0/2.
- PE1's (S,G) sends on Gi0/0/0/0 only, towards PE2.
- P1 has three entries: the (*,G); `(192.168.1.1,239.1.1.1)RPT` with Gi0/0/0/1 `off Prune(…)`, which is PE2's
  (S,G,rpt) Prune; and the (S,G) itself with `JP: Null` and `No interfaces in immediate olist`.
- PE4's (S,G) has the flags `JT`: it joined the source tree (T: packets arrive on it).

The shared tree stays in place: the (*,G) entries remain on PE2, P1 and PE4, and only SRC1's packets have moved. The
price is state: every router on the source tree keeps an (S,G) entry for each source, beside the (*,G) for the group.
A provider can keep groups on the shared tree instead (section 3.4). P1 is still the RP for 239.1.1.1 and carries none
of it.

### 2.7 Key points

- Group addresses: 224.0.0.0/4. 224.0.0.0/24 is link-local, 232.0.0.0/8 is SSM, 239.0.0.0/8 is for use inside one
  organisation. On Ethernet, 01:00:5e plus the low 23 bits: 32 groups per MAC address.
- IGMP runs between hosts and their router: query, report, and (from version 2) leave. Version 3 adds sources. The
  querier is the lowest address; the DR is the highest priority, then the highest address. IOS XR defaults to
  version 3, IOS XE to version 2.
- RPF: a packet is accepted only on the interface towards its source (towards the RP on the shared tree), as the
  unicast table says. Joins go up the same way.
- Sparse mode: (*,G) Joins go hop by hop from the receivers' DRs to the RP, and are repeated every 60 seconds.
- Register: the first-hop router sends the first packets to the RP inside unicast Registers; the RP joins (S,G)
  towards the source, then sends a Register-Stop.
- By default the last-hop router switches to the shortest-path tree at the first packet: an (S,G) Join towards the
  source, and an (S,G,rpt) Prune towards the RP.

## 3. Building it in IOS XR

### 3.1 Turning multicast on: multicast-routing, router pim, router igmp

IOS XR keeps multicast in three configuration blocks. `multicast-routing` decides which interfaces take part, for
each address family. `router pim` holds PIM's settings: the RP, the switch to the source tree, and per-interface
options such as the DR priority. `router igmp` holds IGMP's settings: the version, and groups that the router joins
itself.

By default no interface is enabled, and only `multicast-routing` changes that. Enabling an interface there starts both
PIM (in sparse mode) and IGMP on it; `enable` and `disable` under `router pim` and `router igmp` have no effect on an
interface that `multicast-routing` has not enabled.

On XRT-16 as built, `multicast-routing` holds only the IPv6 family (your predecessor's trial), and IPv4 has no PIM
interface at all. Configuring `router pim` alone changes nothing:

```console
RP/0/RP0/CPU0:PE2#show pim interface
No interfaces found for VRF default.
RP/0/RP0/CPU0:PE2#show running-config multicast-routing
multicast-routing
 address-family ipv6
  interface all enable
 !
!
RP/0/RP0/CPU0:P1(config)#router pim
RP/0/RP0/CPU0:P1(config-pim)#address-family ipv4
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#rp-address 10.255.0.11
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#commit
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#end
RP/0/RP0/CPU0:P1#show pim interface
No interfaces found for VRF default.
```

The RP now has an address. It has no interface to be an RP on.

The figure follows RCV2's request for 239.1.1.1 up to the RP, through the blocks of PE2 and P1 in the order they act.
The numbers match the notes of the configuration examples in this section and the next. Rest the pointer on a number
in the figure (or tap it on a phone) to see that part of the configuration.

:::walk
legend: "RCV2's request for 239.1.1.1 climbs from the receiver to the RP. Blue numbers: the configuration on PE2 and P1."
rows:
  - {node: RCV2, kind: host, say: ["`ip igmp join-group 239.1.1.1` on Ethernet0/0", "~A set-top box asks for the channel (IGMP version 2)"]}
  - {wire: "[[IGMP report 239.1.1.1]] _on ACCESS-2"}
  - panel: PE2
    sub: last-hop router (the DR and the querier on ACCESS-2)
    items:
      - ref: 1
        head: "**Multicast on** `multicast-routing`  `interface all enable`"
        say: ["IGMP and PIM run on Gi0/0/0/3 and on the core links"]
      - say: ["~IGMP records 239.1.1.1 on Gi0/0/0/3 (`router igmp`: nothing set, the defaults)"]
      - ref: 2
        head: "**Which RP** `rp-address 10.255.0.11`"
        say: ["239.1.1.1 falls in 224.0.0.0/4 → RP 10.255.0.11"]
        then: ["→ RPF towards the RP: Gi0/0/0/1, neighbour 10.0.2.11", "→ (*,239.1.1.1) with Gi0/0/0/3 in the outgoing list"]
  - {wire: "[[PIM Join (*,239.1.1.1)]] _out Gi0/0/0/1, to P1"}
  - panel: P1
    sub: the RP
    items:
      - ref: 1
        head: "**Multicast on** `interface all enable`"
        say: ["PIM on Gi0/0/0/1 takes PE2's Join"]
      - ref: 2
        head: "**Which RP** `rp-address 10.255.0.11`"
        say: ["The RP is P1's own Loopback0"]
        then: ["→ (*,239.1.1.1) with RPF `Decapstunnel1` (us): the tree stops here", "→ Gi0/0/0/1, towards PE2, in the outgoing list"]
  - aside: "`router pim` without ①"
    say: ["~`show pim interface` → `No interfaces found for VRF default.` No IGMP, no PIM, no tree"]
  - aside: "① in place, but PIM switched off on Gi0/0/0/1 (`router pim` → `interface` → `disable`)"
    say: ["~PE2's (*,G) shows `RPF: Null,0.0.0.0`, and PE2 sends no Join"]
:::

:::config Every IOS XR router (PE1, PE2, P1, PE3) — IPv4 multicast on all interfaces
multicast-routing                             ## ① Which interfaces take part in multicast, per address family
 address-family ipv4                          ## ① IPv4; IPv6 has its own address-family ipv6
  interface all enable                        ## ① Every interface, Loopback0 too: PIM (sparse mode) and IGMP (version 3)
 !
!
:::

Interfaces can also be enabled one at a time: `interface <name>` under the same address family, then `enable`. One
interface can be kept out of `all` the same way, with `disable`. After the commit, PIM runs on every interface,
Loopback0 included (`show pim interface`, section 3.5).

### 3.2 A static RP

With a static RP, every router is told the RP's address by hand, and every router must be told the same address: the
receivers' Joins and the sources' Registers have to meet at one router. The address here is P1's Loopback0, which
IS-IS carries to every router; each router finds its way to it in the unicast table (`show pim rpf`, section 2.3).

On IOS XR, `rp-address` goes under `router pim`, in the address family. With no access list after the address, as
here, the RP serves all of 224.0.0.0/4 that is not set aside for something else; 232.0.0.0/8 stays SSM (the group map
in section 2.1). An access list of groups after the address limits the RP to those groups; *Two other trees* uses one.

:::config Every IOS XR router (PE1, PE2, P1, PE3) — P1's Loopback0 as the RP for all groups
router pim                                    ## ② PIM's own settings
 address-family ipv4
  rp-address 10.255.0.11                      ## ② P1's Loopback0; no access list, so all of 224.0.0.0/4
 !
!
:::

On IOS XE, multicast routing is switched on once for the router, and PIM interface by interface. IGMP starts on an
interface together with PIM: after `ip pim sparse-mode` alone, PE4's `show ip igmp interface` reads
`IGMP is enabled on interface`.

:::config PE4 (IOS XE) — multicast on both links, and the same RP
ip multicast-routing                          ## IPv4 multicast routing on, for the whole router
!
interface Ethernet0/0                         ## Towards PE2
 ip pim sparse-mode                           ## PIM in sparse mode on this interface; IGMP comes with it
!
interface Ethernet0/1                         ## ACCESS-3
 ip pim sparse-mode
!
ip pim rp-address 10.255.0.11                 ## The same RP as on the IOS XR routers
:::

P1 is configured with its own address and recognises itself. Its group map points the RPF for the RP at its
Decapstunnel and adds `(us)`; on PE2 the same line points at P1 (section 2.1).

```console
RP/0/RP0/CPU0:P1#show pim group-map 239.1.1.1
IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

224.0.0.0/4*        SM    config   0      10.255.0.11     RPF: De1,10.255.0.11 (us)
```

:::drill xr-m14-1

### 3.3 IGMP settings: version, join-group, static-group

IGMP needs no configuration to start: `multicast-routing` turns it on at version 3, with the defaults of section 2.2.
`router igmp` changes them. `version` takes 1, 2 or 3, for every interface (directly under `router igmp`) or for one
interface. Two more commands make the router itself the reason a group comes to an interface:

- `join-group`: the router joins the group on that interface, as a host would. It takes the group's packets in to its
  own processor and answers pings sent to the group, from its address on that interface. PIM marks the interface
  `LI II` (II: internal interest).
- `static-group`: the router forwards the group onto that interface as if a host had joined, with no host and
  without taking the packets in itself. The membership never expires. If both commands name the same group,
  `join-group` wins.

:::config PE2 — ACCESS-2 at IGMP version 2, and PE2 itself as a receiver of 239.9.9.9
router igmp                                   ## IGMP's own settings; without this block the defaults apply
 interface GigabitEthernet0/0/0/3             ## ACCESS-2, where PE2 is the DR
  version 2                                   ## 1, 2 or 3 (default 3): the version IOS XE hosts start with
  join-group 239.9.9.9                        ## PE2 joins: it answers pings sent to 239.9.9.9
 !
!
:::

:::config PE2 — 239.8.8.8 onto ACCESS-2 with no host asking
router igmp
 interface GigabitEthernet0/0/0/3             ## ACCESS-2, towards RCV2
  static-group 239.8.8.8                      ## As if a host had joined; the membership never expires
 !
!
:::

:::config PE4 (IOS XE) — the same three settings
interface Ethernet0/1                         ## ACCESS-3
 ip igmp version 2                            ## 1, 2 or 3; 2 is IOS XE's default, written out here
 ip igmp join-group 239.9.9.9                 ## PE4 itself joins and answers pings
 ip igmp static-group 239.8.8.8               ## Forward with no host asking
:::

When PE2's interface towards RCV2 was set to version 1, the lines on the querier, the max response time and the last
member query left PE2's output, and RCV2 dropped to version 1:

```console
RP/0/RP0/CPU0:PE2#show igmp interface GigabitEthernet0/0/0/3
GigabitEthernet0/0/0/3 is up, line protocol is up
  Internet address is 192.168.2.254/24
  IGMP_AFD is enabled on interface
  Multihoming is disabled on interface [Stale : False]
  Location is 0xe
  Current IGMP version is 1
  IGMP query interval is 60 seconds
  IGMP activity: 4 joins, 1 leaves
  Time elapsed since last query sent 00:00:01
  Time elapsed since IGMP router enabled 00:18:32
  Time elapsed since last report received 00:00:01
RCV2#show ip igmp interface Ethernet0/0
Ethernet0/0 is up, line protocol is up
  Internet address is 192.168.2.1/24
  IGMP is enabled on interface
  Current IGMP host version is 1
  Current IGMP router version is 2
...
```

With `static-group 239.8.8.8` on PE2, IGMP lists the group with `Expires: never` and PE2 itself as the last reporter,
and PIM joins the shared tree for it as for any receiver. Nobody answers SRC1's pings to 239.8.8.8: the group goes to
ACCESS-2, where no host joined it.

```console
RP/0/RP0/CPU0:PE2#show igmp groups 239.8.8.8 detail
Interface:	GigabitEthernet0/0/0/3
Group:		239.8.8.8
Uptime:		00:00:11
Router mode:	EXCLUDE (Expires: never)
Host mode:	EXCLUDE
Last reporter:	192.168.2.254
Suppress:	0
EVPN Remote group: False (Stale: False)
Source list is empty
RP/0/RP0/CPU0:PE2#show pim topology 239.8.8.8
...
(*,239.8.8.8) SM Up: 00:00:12 RP: 10.255.0.11 
JP: Join(00:00:37) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/3      00:00:12  fwd LI LH 
SRC1#ping 239.8.8.8 repeat 5 timeout 1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 239.8.8.8, timeout is 1 seconds:
.....
```

:::drill xr-m14-2

### 3.4 Staying on the shared tree

By default the last-hop router switches to the source tree at the first packet (section 2.6).
`spt-threshold infinity` under `router pim` keeps it on the shared tree; followed by `group-list` and an access list,
it applies to those groups only. IOS XE has the same command, `ip pim spt-threshold infinity` (also with a
`group-list`).

There are reasons to stay: to keep a channel on the links planned for it (on this board, off the direct PE1–PE2
link), or to spare the routers an (S,G) entry for every source. The cost is that the traffic goes through the RP.

The setting acts only on the router that has it, and only on the switch that router would start. On XRT-16 the
last-hop routers are PE2 (for RCV2) and PE4 (for RCV3), and PE4 sends its Joins through PE2. If PE4 still switches,
its (S,G) Join reaches PE2, and PE2 builds an (S,G) entry towards the source over the direct link because of it. So
the setting goes on both.

:::config PE2 — never switch to the source tree, for any group
router pim
 address-family ipv4
  spt-threshold infinity                      ## Stay on the shared tree; group-list <ACL> limits it to some groups
 !
!
:::

:::config PE4 (IOS XE) — the same
ip pim spt-threshold infinity                 ## For every group; group-list <ACL> limits it
:::

With the setting on both, SRC1's pings to a new group, 239.1.1.2, were answered ten times by each box, and the
channel went PE1 → P1 → PE2.

PE2 has only the (*,G), with `DSS` (Don't Signal Sources: PE2 does not start a switch).
P1 keeps its (S,G) Join towards PE1 and sends the packets down the shared tree: on this virtual platform its MFIB
counted them in on Gi0/0/0/0 and out on Gi0/0/0/1. PE4's (*,G) has `SC`, without the J.

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:38 RP: 10.255.0.11 
JP: Join(00:00:11) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH DSS 
  GigabitEthernet0/0/0/2      00:00:36  fwd Join(00:02:53) 
  GigabitEthernet0/0/0/3      00:00:38  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:40 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:40  fwd Join(00:02:49) 

(192.168.1.1,239.1.1.2)SPT SM Up: 00:00:21 
JP: Join(00:00:28) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:10) RA RR (00:04:15) 
  No interfaces in immediate olist
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.2 detail
...
(192.168.1.1,239.1.1.2),  Flags:  , FMA: 0x10000 ,
  Object-ID: 0xfffffffffffffffe 18446744073709551614
  Up: 00:00:21
  Last Used: 00:00:05
  SW Forwarding Counts: 13/12/1200
  SW Replication Counts: 13/12/1200
  SW Failure Counts: 0/0/0/0/0
...
  GigabitEthernet0/0/0/0 Flags:  A, Up:00:00:21 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
  GigabitEthernet0/0/0/1 Flags:  NS EG, Up:00:00:21 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
PE4#show ip mroute 239.1.1.2
...
(*, 239.1.1.2), 00:00:39/00:02:30, RP 10.255.0.11, flags: SC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:39/00:02:30, flags: 
```

:::try
See what a downstream router's default does to PE2's setting. Do it after Task M14-1 and before Task M14-2, and put
everything back at the end. The groups 239.1.1.3 and 239.1.1.4 lie outside the ranges the tasks use, and inside the
RP's range of Task M14-1.

1. On PE2, put `spt-threshold infinity` under `router pim` → `address-family ipv4`, and commit. Leave PE4 as it is.
2. On RCV2 and RCV3, join 239.1.1.3 (`ip igmp join-group 239.1.1.3` under `interface Ethernet0/0`). After about 15
   seconds, ping it from SRC1: `ping 239.1.1.3 repeat 10 timeout 1`.
3. Look at `show pim topology 239.1.1.3` on PE2 and P1, and at `show ip mroute 239.1.1.3` on PE4. Which entries does
   PE2 have, and which way does its (S,G) entry point?
4. Put `ip pim spt-threshold infinity` on PE4 as well. Join RCV2 and RCV3 to 239.1.1.4, ping it from SRC1, and look
   at the same three commands for 239.1.1.4.
5. Put everything back: `no spt-threshold infinity` on PE2 (and commit), `no ip pim spt-threshold infinity` on PE4,
   and `no ip igmp join-group` for both groups on RCV2 and RCV3.

Example result: with the setting on PE2 only, both boxes received the pings. PE2 had two entries: the (*,G) with the
flags `LH DSS`, and an (S,G) entry marked `SPT` with `RPF: GigabitEthernet0/0/0/0,10.0.12.1` and Gi0/0/0/2, towards
PE4, as its joined interface. P1 had the source's `RPT` entry with Gi0/0/0/1 `off Prune`. PE4's default had sent an
(S,G) Join to PE2, and PE2 took the channel over the direct link, for RCV2 as well.

With the setting on PE4 too, PE2
had only the (*,G) (`LH DSS`), PE4's (*,G) had the flags `SC`, and P1 had an (S,G) entry towards PE1
(`RPF: GigabitEthernet0/0/0/0,10.0.1.1`): the channel went PE1 → P1 → PE2.
:::

:::drill xr-m14-3

### 3.5 Reading the state

PIM's interfaces and neighbours, on PE2 and on PE4:

```console
RP/0/RP0/CPU0:PE2#show pim interface
PIM interfaces in VRF default
Address               Interface                     PIM  Nbr   Hello  DR    DR
                                                         Count Intvl  Prior

10.255.0.2            Loopback0                     on   1     30     1     this system
10.0.12.2             GigabitEthernet0/0/0/0        on   2     30     1     this system
10.0.2.2              GigabitEthernet0/0/0/1        on   2     30     1     10.0.2.11
10.0.4.2              GigabitEthernet0/0/0/2        on   2     30     1     10.0.4.4
192.168.2.254         GigabitEthernet0/0/0/3        on   1     30     1     this system
RP/0/RP0/CPU0:PE2#show pim neighbor
PIM neighbors in VRF default
Flag: B - Bidir capable, P - Proxy capable, DR - Designated Router,
      E - ECMP Redirect capable, S - Sticky DR Neighbor
      * indicates the neighbor created for this router

Neighbor Address             Interface              Uptime    Expires  DR pri      Flags

10.0.12.1                    GigabitEthernet0/0/0/0 00:01:02  00:01:44 1           B
10.0.12.2*                   GigabitEthernet0/0/0/0 00:01:09  00:01:43 1           (DR) B E
10.0.2.2*                    GigabitEthernet0/0/0/1 00:01:09  00:01:15 1           B E
10.0.2.11                    GigabitEthernet0/0/0/1 00:00:56  00:01:43 1           (DR) B
10.255.0.2*                  Loopback0              00:01:09  00:01:43 1           (DR) B E
10.0.4.2*                    GigabitEthernet0/0/0/2 00:01:09  00:01:40 1           B
10.0.4.4                     GigabitEthernet0/0/0/2 00:00:50  00:01:24 1           (DR) P
192.168.2.254*               GigabitEthernet0/0/0/3 00:01:09  00:01:22 1           (DR) B E
PE4#show ip pim neighbor
PIM Neighbor Table
Mode: B - Bidir Capable, DR - Designated Router, N - Default DR Priority,
      P - Proxy Capable, S - State Refresh Capable, G - GenID Capable,
      L - DR Load-balancing Capable
Neighbor          Interface                Uptime/Expires    Ver   DR
Address                                                            Prio/Mode
192.168.3.252     Ethernet0/1              00:00:56/00:01:18 v2    1 / G
10.0.4.2          Ethernet0/0              00:00:57/00:01:32 v2    1 / G
```

- **The neighbour count includes the router itself.** IOS XR lists itself on every interface, marked `*`. Loopback0
  has one neighbour, PE2 itself; Gi0/0/0/0 has two, PE1 and PE2.
- **The DR** is in the last column of `show pim interface` and is marked `(DR)` among the neighbours. On PE2's links,
  PE2 is the DR towards PE1 (10.0.12.2 is more than 10.0.12.1), P1 (10.0.2.11) towards P1, and PE4 (10.0.4.4) towards
  PE4.
- **The flags** say what each neighbour can do: the IOS XR routers show `B` (bidir capable), PE4 shows `P` (proxy
  capable). PE4 shows the IOS XR routers with `G` (GenID capable).

| Command (IOS XR) | What to read |
|---|---|
| `show pim interface` | Which interfaces run PIM (`on`/`off`), the neighbour count, the Hello interval, the DR priority and the DR |
| `show pim neighbor` | The neighbours on each interface, the DR, and what each one can do |
| `show igmp interface <if>` | The version, the timers, and the querier |
| `show igmp groups [<group>] [detail]` | The groups on each interface, the last reporter, and the source list |
| `show pim group-map [<group>]` | Which range a group falls in, its mode (`SM`, `SSM`, `DM`, `NO`) and its RP |
| `show pim rpf [<address>]` | The RPF interface and neighbour towards a source or the RP, and the route behind them |
| `show pim topology [<group>]` | PIM's entries: (*,G) and (S,G), the Join or Prune towards the RPF neighbour, and each outgoing interface with its reason (`LI` from IGMP, `Join` from a neighbour) |
| `show mrib route [<group>]` | The multicast routing table built from PIM and IGMP: the accepting interface (`A`) and the forwarding ones (`F`) |
| `show mfib route <group> detail` | The forwarding entries, with packet counts |

`show mrib route` is the shortest answer to "where does this router take the channel in, and where does it send it".
On PE2 after the switch, the (*,G) accepts on Gi0/0/0/1 (from P1), and the (S,G) accepts on Gi0/0/0/0 (from PE1); both
forward on Gi0/0/0/2 and Gi0/0/0/3.

```console
RP/0/RP0/CPU0:PE2#show mrib route 239.1.1.1
...
(*,239.1.1.1) RPF nbr: 10.0.2.11 Flags: C RPF
  Up: 00:00:44
  Incoming Interface List
    GigabitEthernet0/0/0/1 Flags: A NS, Up: 00:00:44
  Outgoing Interface List
    GigabitEthernet0/0/0/2 Flags: F NS, Up: 00:00:41
    GigabitEthernet0/0/0/3 Flags: F NS LI, Up: 00:00:44

(192.168.1.1,239.1.1.1) RPF nbr: 10.0.12.1 Flags: RPF
  Up: 00:00:14
  Incoming Interface List
    GigabitEthernet0/0/0/0 Flags: A, Up: 00:00:14
  Outgoing Interface List
    GigabitEthernet0/0/0/2 Flags: F NS, Up: 00:00:14
    GigabitEthernet0/0/0/3 Flags: F NS, Up: 00:00:14
```

`show mfib route <group> detail` counts. On this virtual platform (IOS XRd), `SW Forwarding Counts` grows with the
packets the router forwards, as packets in, packets out and bytes out; `SW Failure Counts` counts the drops by reason,
the first being RPF. Section 2.5 used these counts to see the Registers that P1 unwrapped.

On IOS XE, `show ip mroute` carries all of this in one table: the incoming interface and the RPF neighbour, the
outgoing interfaces, and the flags (`S` sparse, `C` a member on a connected interface, `J` join the source tree,
`T` on the source tree). `show ip pim interface`, `show ip pim neighbor` and `show ip igmp interface` match the IOS XR
commands above.

### 3.6 Pitfalls

- **`router pim` without `multicast-routing`**: no interface runs PIM or IGMP (`No interfaces found for VRF default.`).
- **One address family only**: IPv4 and IPv6 are enabled separately. IPv6's `interface all enable` does nothing for
  IPv4.
- **An RP missing on some routers, or a different RP on one**: the receivers' Joins and the sources' Registers must
  reach the same router. If they go to different routers, nothing arrives.
- **PIM switched off on the interface towards the RP**: the (*,G) shows `RPF: Null,0.0.0.0` and `show pim interface`
  shows the interface `off`.
- **Staying on the shared tree on one router only**: a downstream router that switches pulls the (S,G) through it
  anyway (section 3.4). The setting goes on every last-hop router.
- **Two IGMP versions on one LAN**: IOS XR defaults to version 3, IOS XE to version 2. Set one version on all the
  routers of the LAN.
- **`join-group` on a router that is not the DR of the LAN**: the DR forwards the group onto the LAN, and the copy
  reaches the other router on an interface that fails its RPF check. With `join-group 239.9.9.9` on PE3's ACCESS-3
  interface (PE4 is the DR there), only PE4 answered SRC1's pings; on PE2, the DR of ACCESS-2, PE2 answered every one.
- **Testing with a group used a minute ago**: Joins and (S,G) entries stay for up to 210 seconds after their cause has
  gone, so a fault can seem to make no difference. Test with a new group.
- **Clearing the state on the RP**: after `clear pim topology` on the RP, the receivers get nothing until the next
  periodic Join (up to 60 seconds).
- **`clear igmp groups`**: IOS XR's command is `clear igmp group`, in the singular; the plural is rejected.

## Practice

Do Tasks M14-1 and M14-2 in lab **XRT-16**. As the lab starts, IPv4 multicast is configured nowhere.

<p class="tolab"><a href="/_learn?id=XRT-16">Open lab XRT-16 in the workspace</a> — <a href="f1-m14-practice.html">Tasks M14-1 and M14-2</a></p>

:::note
The output on this page was taken on XRT-16 with this page's settings (they differ from the tasks): IOS XRd 26.1.1 on
PE1, PE2, P1 and PE3, and IOS XE 17.15 (IOL) on PE4 and the hosts. Some output and the example result of the
"Try it" come from a PoC board whose PE1, PE2 and P1 have the same names and addresses as on XRT-16; there PE1 and PE2
ran IOS XRv 9000 26.1.1, and the IOS XE 17.15 router in PE4's place had other addresses. From that board: the
IGMP version 1 output, the `static-group` output, PIM switched off on the interface
towards the RP, `spt-threshold infinity` on PE2 alone, the RP with its state cleared, and the lingering Joins. The
Register-Stop sent when the RP has no receivers, and IOS XE's IGMP and PIM defaults, were measured on IOS XE 17.15
alone in an earlier PoC.
Sources: the Multicast Configuration Guide for Cisco 8000 Series Routers, IOS XR 26.1.x–26.3.x, "Implementing Layer-3
Multicast Routing" (no interface enabled by default and enabling in multicast routing configuration mode, sparse mode
by default, the switch to the source tree when the first data packet arrives, MLDv2 enabled by default); the Multicast
Command Reference for Cisco 8000 Series Routers (the IGMP defaults; `enable`/`disable` under IGMP and PIM having no
effect unless the interface is enabled under `multicast-routing`; 232/8 as the default SSM range;
`spt-threshold infinity [group-list]`; `join-group`, `static-group`, and `join-group` taking precedence); the IP
Multicast configuration guides and command reference for Cisco IOS XE (the address ranges, the IGMP querier,
`ip pim spt-threshold`, `ip igmp join-group` and `ip igmp static-group`, the `J` flag of `show ip mroute`); RFC 2236
(IGMPv2, the Leave to 224.0.0.2), RFC 3376 (IGMPv3, reports to 224.0.0.22; section 7.3.1, one version on a LAN),
RFC 4604 (IGMPv3 for source-specific multicast) and RFC 7761 (PIM-SM: section 4.3.2 for the DR election, the Join/Prune
period of 60 seconds and holdtime of 210 seconds, Register and Register-Stop, the (S,G,rpt) Prune). All checked in
November 2026.
The following come from measurements: XRd forwarding multicast and counting it in the MFIB (no Cisco document
describes multicast on XRd; on IOS XRv 9000 the same counters stayed at 0 while the packets were delivered); the
output of `router pim` without `multicast-routing`; the querier and the DR on ACCESS-3; the Decapstunnel numbers
(0, 1 and 2 were seen on different boards and at different times); the flags; and the ping counts.
Where the documents and the device differ or are silent: the command reference gives the IGMP querier timeout as
120 seconds, while IOS XR shows 125 seconds (RFC 3376's formula); the value appears in the output above but is not
taught here. RFC 3376 asks for one IGMP version on a LAN; the board starts with two.
:::
