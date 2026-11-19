# M14 — The parts of multicast and how they fit together

This unit is about sending one stream to many receivers at once: multicast. In the CCNP Service Provider blueprint
(SPCOR) it is section 4.4, implementing multicast services: 4.4.a, PIM (PIM-SM, PIM-SSM, PIM-BIDIR and PIMv6), and
4.4.b, IGMP v1, v2 and v3 and MLD.

Units M0 to M13 went through the blueprint once, and 4.4 was the only section they had not touched at all. M14 starts
the second round with it. The unit has three pages and an appendix.

| Page | Contents |
|---|---|
| This page | One TV channel followed across the board, the three questions it answers, the words and the parts, where each part is configured |
| Delivering one stream to many: IGMP and PIM sparse mode | What multicast is good for; IGMP; PIM-SM with a static RP: the shared tree, Register, the switch to the shortest-path tree |
| Two other trees: SSM and bidirectional PIM | Source-specific multicast with IGMPv3; bidirectional PIM and the DF |
| Finding the RP, IPv6, and troubleshooting | BSR and Auto-RP; PIMv6 and MLD; reading the state when nothing arrives |
| Appendix | Assert, MSDP and Anycast RP, a first look at multicast VPNs, the IGMP and MLD versions, defaults and commands side by side, what was checked |

The lab is XRT-16. A provider carries TV channels from a head-end, SRC1, to set-top boxes, RCV2 and RCV3. PE1, PE2, P1
and PE3 run IOS XRd 26.1.1. PE4 runs IOS XE 17.15 (IOL), and so do the three hosts.

RCV3 sits on a shared access LAN, ACCESS-3, together with two routers, PE3 and PE4; its default gateway is PE4. All
five routers run IS-IS (instance `CORE`, level 2), and the access links are passive.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1 (head-end)"}
  PE1: {at: [1.7, 0], label: "PE1"}
  P1: {at: [3.4, 1.35], label: "P1"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [6.8, 0], kind: host, label: "RCV2"}
  PE4: {at: [5.1, 1.7], label: "PE4 (IOS XE)"}
  PE3: {at: [3.4, 2.9], label: "PE3"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [6.8, 2.9], kind: host, label: "RCV3"}
links:
  - [SRC1, PE1, "HEADEND\n192.168.1.0/24"]
  - [PE1, PE2, "CORE-12 10.0.12.0/24"]
  - [PE1, P1, "CORE-1 10.0.1.0/24"]
  - {a: P1, b: PE2, label: "CORE-2 10.0.2.0/24", t: 0.42}
  - [P1, PE3, "CORE-3 10.0.3.0/24"]
  - [PE2, PE4, "CORE-4 10.0.4.0/24"]
  - [PE2, RCV2, "ACCESS-2\n192.168.2.0/24"]
  - {a: PE3, b: SW1, la: "Gi0/0/0/1 .252", ta: 0.5}
  - {a: PE4, b: SW1, la: "Et0/1 .253", ta: 0.35}
  - [SW1, RCV3, "ACCESS-3\n192.168.3.0/24"]
:::

The documents for IOS XRd (its data sheet and the release notes for 26.1.1) say nothing about multicast. On this
virtual platform it forwards multicast in every role the lab needs: first hop, RP, last hop and transit. The appendix
lists what was checked.

Multicast brings in many words at once: IGMP, PIM, RP, shared tree, Register, (\*,G), (S,G), DR, querier. On this
board they all describe one thing: how one channel from SRC1 reaches RCV2 and RCV3. This page follows one channel
across the board (section 2.1), answers three questions about it (section 2.2), and only then lines up the words.

## 1. What it is good for

### 1.1 The problem: one channel, many set-top boxes

SRC1 sends a TV channel, a steady stream of packets at a fixed rate. RCV2 and RCV3 want to watch it. On a real network
there are thousands of set-top boxes, and many of them watch the same channel at the same moment.

### 1.2 What came before: a copy for each receiver

With unicast, SRC1 sends a separate copy of every packet to each receiver, addressed to that receiver. The links near
the head-end carry as many copies of the same packet as there are viewers. A thousand set-top boxes, a thousand
identical copies on SRC1's link.

### 1.3 The answer: one copy on each link, and only where someone asked

Multicast sends to a group address (in IPv4, 224.0.0.0/4) instead of to a receiver. SRC1 sends one copy. The routers
copy the packet only where the paths to the receivers part, so each link carries at most one copy, and only the links
that lead to a receiver carry it at all.

For that, the routers need to know where the receivers are, and how to reach them from the source. The hosts tell
their router with IGMP (with MLD in IPv6), and the routers build the tree between them with PIM. The receivers ask,
and the tree grows from them back toward the sender.

## 2. How it works: one channel across the board

### 2.1 The picture

The figure follows one channel, 239.1.1.1, from SRC1 to RCV2 and RCV3. The RP is P1's Loopback0 (10.255.0.11),
configured by hand on every router. The circled numbers on the links give the order in which things happen.

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1 (source)"}
  PE1: {at: [1.7, 0], label: "PE1 (first hop)"}
  P1: {at: [3.4, 1.35], label: "P1 (RP)"}
  PE2: {at: [5.1, 0], label: "PE2 (last hop)"}
  RCV2: {at: [6.8, 0], kind: host, label: "RCV2 (receiver)"}
  PE4: {at: [5.1, 1.7], label: "PE4 (last hop, DR)"}
  PE3: {at: [3.4, 2.9], label: "PE3 (querier)"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [6.8, 2.9], kind: host, label: "RCV3 (receiver)"}
links:
  - [SRC1, PE1, "③ data"]
  - [PE1, P1, "③ Register"]
  - [PE1, PE2, "⑤ (S,G) Join, data"]
  - {a: P1, b: PE2, label: "② Join  ④ data\n⑤ Prune", t: 0.42}
  - [P1, PE3, ""]
  - [PE2, PE4, "② ⑤ Join\n④ ⑤ data"]
  - [PE2, RCV2, "① report\n④ ⑤ data"]
  - [PE3, SW1, ""]
  - [PE4, SW1, "④ ⑤ data"]
  - [SW1, RCV3, "① report\n④ ⑤ data"]
:::

- ① RCV2 and RCV3 report with IGMP that they want 239.1.1.1. On ACCESS-3, PE3 and PE4 both hear RCV3's report. PE3 is
  the querier (the lower address, .252) and PE4 is the DR (the higher address, .253). The DR is the one that acts.
- ② The last-hop routers, PE2 and PE4, send a (\*,G) Join toward the RP, one hop at a time: PE4 to PE2, PE2 to P1.
  Each router on the way remembers the interface the Join came in on. Those interfaces make up the shared tree, with
  its root at P1.
- ③ SRC1 starts sending. PE1, the first-hop router, knows nothing about the receivers. It wraps each packet in a
  Register message and sends it to the RP by unicast.
- ④ P1 takes the packet out of the Register and sends it down the shared tree: P1 to PE2, PE2 to RCV2 and to PE4, PE4
  onto ACCESS-3.
- ⑤ The packets have told PE2 and PE4 the source's address. PE2's shortest path to SRC1 is the direct link to PE1, not
  the way through P1. PE2 sends an (S,G) Join to PE1, PE4 sends one to PE2, and PE2 tells P1 that it no longer needs
  SRC1's packets on the shared tree (a Prune). From then on the channel runs PE1 → PE2 → RCV2 and PE2 → PE4 → RCV3,
  and P1 is no longer on its path.

### 2.2 Three questions the picture answers

Each step answers one of three questions. The answers name the parts that the next pages configure.

**Who says there is a receiver?** The receiver itself, with IGMP. A host that wants a group sends an IGMP report onto
its LAN, and the router keeps a table of the groups that have members on each interface (`show igmp groups`). To keep
the table current, one router per LAN, the querier, asks at intervals who is still a member; the query interval is 60
seconds on both IOS XR and IOS XE here.

When two routers share a LAN, they split the jobs by address: the lowest address is the querier, and the highest (with
the default DR priority) is the DR, which alone joins upstream for the LAN. On ACCESS-3 those are two different
routers. One asks, the other acts.

**How does the first packet find receivers that PE1 knows nothing about?** Through the RP. Every router knows the RP's
address for the group, so the receivers' side and the source's side have a place to meet without knowing each other.
The receivers' routers join toward the RP: the shared tree, (\*,G), "this group, from any source". The source's router
sends the first packets to the RP inside Registers.

While the RP sends a source's packets down the shared tree, it also joins toward the source, so that the packets reach
it natively, and then tells the first-hop router to stop registering (Register-Stop). PE1 needs to know where the RP
is, not where the receivers are.

**Why does the tree change after the first packets?** Because the shared tree goes through the RP, and the RP is not
always on the shortest path. PE2 reaches the RP over CORE-2 but reaches SRC1 directly over CORE-12. Until the first
packet arrives, PE2 does not know the source's address and can only join toward the RP.

Once it knows, it joins the shortest-path tree, (S,G), "this group, from this source", and prunes that source off the
shared tree. Both IOS XR and IOS XE switch after the first packet by default; `spt-threshold infinity` keeps a router
on the shared tree.

In PIM-SM, a router accepts a group's packets on one interface only: the one its unicast route points out of toward
the source (for an (S,G) entry) or toward the RP (for a (\*,G) entry). This is the RPF check. After the switch, PE2
keeps both entries, and they accept packets on different interfaces (an excerpt):

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

The (\*,G) entry accepts (`A`) on GigabitEthernet0/0/0/1, the link to P1. The (S,G) entry accepts on
GigabitEthernet0/0/0/0, the link to PE1, and forwards (`F`) to PE4 and onto RCV2's LAN (`LI`, local interest: a member
on that LAN).

On P1, the entry `(192.168.1.1,239.1.1.1)RPT` shows the interface toward PE2 as `off Prune`. P1 was the place to meet,
not the way to travel.

### 2.3 Two other trees, and how routers learn the RP

**SSM.** In source-specific multicast the receiver names the source as well as the group, which IGMPv3 (MLDv2 in IPv6)
can carry. The last-hop router then joins straight toward the source, (S,G), and no RP is involved: no shared tree, no
Register, no switch.

IOS XR treats 232.0.0.0/8 as SSM by default; IOS XE does so only after `ip pim ssm default`, or with a range of your
own. In an SSM range, a report that does not name a source (IGMPv1 or v2) is dropped.

**BIDIR.** In bidirectional PIM there is only the shared tree, and traffic flows on it in both directions: up toward
the RP from any sender, and down to every receiver. No router keeps (S,G) state, and no Register is sent. On each
link, one router, the DF (designated forwarder), forwards toward the RP and onto the link: the router with the best
route to the RP. It suits groups in which every member sends, such as a conference.

**The RP's address.** In PIM-SM and BIDIR every router must map each group to the same RP. There are three ways to
tell them. **Static**: the address is configured on every router. **BSR** (the standard, PIMv2): candidate RPs
announce themselves by unicast to the elected bootstrap router (BSR), and the BSR floods the list hop by hop to all
PIM routers (224.0.0.13); each router picks the RP from the list, and the lowest priority value wins.

**Auto-RP** (Cisco's own): candidate RPs announce themselves on 224.0.1.39, and a mapping agent picks one for each
range (the highest address) and announces the choice on 224.0.1.40. When a static RP and a learned one cover the same
groups, the learned one wins unless the static one is configured with `override`.

### 2.4 The words side by side

A magazine sold through newsagents works much the same way, and the right-hand column uses it as a picture: SRC1 is
the publisher, the set-top boxes are subscribers, and the routers are the newsagents and the depots in between.

| Word | What it is | For a magazine |
|---|---|---|
| Group address (G) | The destination of a multicast stream: 224.0.0.0/4 in IPv4, FF00::/8 in IPv6 | The title of the magazine |
| Source (S) | The host that sends to the group; SRC1 | The publisher |
| Receiver | A host that has joined the group; RCV2, RCV3 | A subscriber |
| IGMP, MLD | Between hosts and their router: which groups have members on this LAN | Telling the local newsagent which titles you want |
| Querier | The one router per LAN that asks, at intervals, who is still a member | The newsagent who asks every month who still wants it |
| PIM | Between routers: builds the tree from the members back toward the source or the RP | The newsagents' orders, passed up the chain |
| DR | The router on a LAN that joins upstream for its receivers and registers its sources | The one newsagent on the street who places the orders |
| RP | The router where the receivers' Joins and a source's first packets meet | The central depot |
| Register | The first-hop router's unicast message that carries a source's packet to the RP | The first copies, sent to the depot by courier |
| (\*,G), shared tree | State for "this group, from any source"; the tree with its root at the RP | Delivery from the depot, whoever published the issue |
| (S,G), shortest-path tree | State for "this group, from this source"; the tree with its root at the source, also called the source tree | Delivery straight from the publisher's warehouse |
| RPF check | A packet is accepted only on the interface that points back toward its source (or the RP) | Taking a delivery only from the van that comes from the depot's side |
| DF (BIDIR) | On each link, the one router that forwards toward the RP and onto the link | The one shop on each street that passes copies on |
| BSR, Auto-RP | Two ways for every router to learn the RP's address | The notice that tells every shop where the depot is |

### 2.5 Parts that are easy to mix up

- **The DR, the querier and the DF.** They are three separate elections on the same kind of LAN, and they need not
  pick the same router. The querier (IGMP) is the lowest address, and it only asks. The DR (PIM) has the highest DR
  priority, then the highest address, and it joins and registers. The DF (BIDIR only) is the router with the best
  route to the RP, chosen for each RP on each link. On ACCESS-3, PE3 is the querier and PE4 the DR. For a BIDIR RP on
  P1, PE3 is the DF: it has a direct link to P1, while PE4's path to P1 goes through PE2.
- **(\*,G) and (S,G).** (\*,G) means "this group, from any source", and its RPF interface points toward the RP. (S,G)
  means "this group, from this source", and its RPF interface points toward the source. PIM-SM uses both, SSM only
  (S,G), and BIDIR only (\*,G).
- **IGMP and PIM.** IGMP runs between hosts and the routers on their LAN; PIM runs between routers. A router speaks
  IGMP toward its hosts and PIM toward other routers. IOS XR starts both on an interface with one command.
- **The RP and the source.** The RP is a router address that every router agrees on, not the sender of the channel.
  With the default switch it carries a channel only for the first packets, and in SSM there is no RP at all.

### 2.6 Key points

- The receivers ask, and the routers build the tree from them back toward the sender. IGMP (MLD in IPv6) runs between
  hosts and their router, PIM between routers.
- In PIM-SM, the receivers' routers join toward the RP ((\*,G), the shared tree), and the source's router sends the
  first packets to the RP inside Registers. The RP is where the two meet.
- After the first packets, the last-hop routers join the source directly ((S,G), the shortest-path tree) and prune it
  off the shared tree: by default on both IOS XR and IOS XE.
- A router accepts a group's packets only on the interface toward the source or the RP (the RPF check).
- On a LAN with two routers, the lowest address is the IGMP querier and the highest is the PIM DR. The DR joins.
- SSM: the receiver names the source, and there is no RP. BIDIR: one shared tree used in both directions, a DF on each
  link, no (S,G).
- Every router learns the RP's address from its configuration (static), from BSR or from Auto-RP.

## 3. Building it: where each part is configured

### 3.1 Where each part lives on IOS XR and IOS XE

On IOS XR, multicast is configured in three blocks, and the first one decides where the other two apply. On IOS XE the
same parts are global commands and interface commands. The configuration examples are on the pages that follow; this
table only says where to look.

| Part | IOS XR | IOS XE |
|---|---|---|
| Multicast routing on the interfaces (starts PIM and IGMP) | `multicast-routing` → `address-family ipv4` → `interface all enable`, or one interface | `ip multicast-routing`, and `ip pim sparse-mode` on each interface |
| The RP, and what happens to which groups: static RP, SSM range, BIDIR, the switch to the shortest-path tree, BSR, Auto-RP | `router pim` → `address-family ipv4` | Global commands: `ip pim rp-address`, `ip pim ssm default` or `range`, `ip pim bidir-enable`, `ip pim spt-threshold`, `ip pim bsr-candidate`, `ip pim rp-candidate`, `ip pim send-rp-announce`, `ip pim send-rp-discovery` |
| PIM on one interface: DR priority, turning PIM off | `router pim` → `address-family ipv4` → `interface <if>` | `ip pim dr-priority` on the interface |
| IGMP on one interface: the version, the router as a member, a static group | `router igmp` → `interface <if>` | `ip igmp version`, `ip igmp join-group`, `ip igmp static-group` on the interface |
| IPv6 | The same blocks with `address-family ipv6`; MLD under `router mld` | `ipv6 multicast-routing`, `ipv6 pim rp-address`; `ipv6 mld …` on the interface |
| The group lists these commands refer to | `ipv4 access-list <name>`, with lines such as `permit ipv4 239.2.0.0 0.0.255.255 any` | `access-list <number> permit 239.2.0.0 0.0.255.255` |

On IOS XR, `interface all enable` under `multicast-routing` starts PIM and IGMP version 3 on every interface,
Loopback0 included, and `router pim` and `router igmp` need no `interface` lines unless an interface should behave
differently.

The reverse does not hold: `router pim` with an RP and nothing else enables no interface, and `show pim interface`
answers `No interfaces found for VRF default.` and nothing else.

### 3.2 The pages and the tasks of XRT-16

The six tasks are in lab XRT-16, two after each of the three body pages. You configure PE1, PE2, P1, PE3 and PE4. The
hosts SRC1, RCV2 and RCV3 only join groups and send, to test your work. The configuration examples on the pages use
other values than the tasks.

| Page | Tasks | What the tasks ask for |
|---|---|---|
| Delivering one stream to many: IGMP and PIM sparse mode | M14-1, M14-2 | PIM-SM with a static RP for part of the group range; keeping some groups on the shared tree |
| Two other trees: SSM and bidirectional PIM | M14-3, M14-4 | SSM ranges and IGMPv3; bidirectional PIM with another RP |
| Finding the RP, IPv6, and troubleshooting | M14-5, M14-6 | BSR with candidates in a set order; an IPv6 trial that has never delivered anything |

<p class="tolab"><a href="/_learn?id=XRT-16">Open lab XRT-16 in the workspace</a> — <a href="f1-m14-practice.html">Tasks M14-1 and M14-2</a></p>

:::note
The output on this page was taken on the XRT-16 board, with IOS XRd 26.1.1 (PE1, PE2, P1, PE3) and IOS XE 17.15 on IOL
(PE4 and the hosts), using the values of the examples on these pages (group 239.1.1.1, RP 10.255.0.11 for all
groups). The querier and the DR on ACCESS-3, the shared tree and the switch, the Prune on P1, the query interval, the
SSM default and the DF on ACCESS-3 were measured there. That IOS XRd forwards multicast was measured on a PoC board
with IOS XRv 9000 26.1.1 and IOS XRd 26.1.1 side by side, and again on XRT-16; the IOS XRd data sheet and the release
notes for 26.1.1 say nothing about multicast. Sources: RFC 7761 (PIM-SM; section 4.3.2 for the DR), RFC 2236
(IGMPv2), RFC 3376 (IGMPv3), RFC 4604 (section 3.5) and RFC 4607 (SSM), RFC 5015 (BIDIR), RFC 5059 (BSR); the
Multicast Configuration Guide (IOS XR 26.1.x–26.3.x) and Multicast Command Reference for the Cisco 8000, and the Multicast Configuration
Guide (IOS XR 25.x) and Command Reference for the ASR 9000; the IP Multicast Configuration Guide (IOS XE 17.x) and
the Cisco IOS IP Multicast Command Reference. All checked in November 2026.
:::
