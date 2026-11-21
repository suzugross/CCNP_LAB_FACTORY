# M6 supplement — Handing out a backup path: ADD-PATH and PIC

The previous page laid out the parts of BGP operations. This page takes the two of them that shorten the outage when
the primary exit fails: ADD-PATH hands out a backup path in advance, and PIC (Prefix Independent Convergence) puts that
backup into the forwarding table.

They are 2.4.g (additional paths) and 2.4.h (PIC) of the blueprint, and Tasks M6-5 and M6-6 of lab XRT-17 use them.
Route policies and next-hop-self were covered in the main M6 page. GTSM and TCP-AO are on the page *Protecting the
session*; prefix limits, dampening and aggregation are on *Not taking too much*.

## 1. What it is good for

### 1.1 The problem: two exits, and PE1 knows only one

The provider on XRT-17 (AS 65000) has five routers. PE1 is the ingress PE that connects the customer CE1 (AS 65001),
PE2 and PE3 are the two exits to AS 65100, P1 is a core router that runs no BGP, and RR1 is a dedicated route reflector
off the path. The core links run IS-IS (instance CORE, level 2) and LDP.

PE1 to PE3 are clients of RR1, with iBGP between their Loopback0 addresses, and every PE sets next-hop-self. X1 and X2
in AS 65100 both advertise T's 203.0.113.0/24. PE2 sets the local preference of the routes it learns from X1 to 200,
so PE2 is the primary exit and PE3 the backup exit.

:::topo
nodes:
  CE1: {at: [0, 1], kind: host, label: "CE1 (AS 65001)"}
  PE1: {at: [2.2, 1], label: "PE1 (ingress, XRv 9000)"}
  P1: {at: [4.2, 1], label: "P1 (no BGP)"}
  RR1: {at: [4.2, 2.5], label: "RR1 (route reflector)"}
  PE2: {at: [6.2, 0], label: "PE2 (primary exit)"}
  PE3: {at: [6.2, 2], label: "PE3 (backup exit)"}
  X1: {at: [8.2, 0], label: "X1"}
  X2: {at: [8.2, 2], label: "X2"}
  T: {at: [9.9, 1], kind: host, label: "T 203.0.113.1"}
links:
  - {a: CE1, b: PE1, label: "172.16.1.0/24"}
  - {a: PE1, b: P1, label: "10.0.1.0/24"}
  - {a: P1, b: PE2, label: "10.0.2.0/24"}
  - {a: P1, b: PE3, label: "10.0.3.0/24"}
  - {a: P1, b: RR1, label: "10.0.21.0/24"}
  - {a: PE2, b: X1, label: "172.16.2.0/24"}
  - {a: PE3, b: X2, label: "172.16.3.0/24"}
  - {a: X1, b: T}
  - {a: X2, b: T}
  - {a: X1, b: X2}
frames:
  - {label: "AS 65000", nodes: [PE1, P1, RR1, PE2, PE3]}
  - {label: "AS 65100", nodes: [X1, X2, T]}
:::

T's default route prefers X2, so the return traffic from T to CE1 goes through X2 and PE3. This page follows only the
forward direction, from CE1 to T.

The trouble is at PE3. PE3 knows two paths for 203.0.113.0/24: the iBGP path through PE2 that came from RR1 (local
preference 200), and the eBGP path it learned directly from X2 (100). The best is the path through PE2. BGP advertises
only its best path, and a best path learned over iBGP is not sent to iBGP peers. So PE3 sends RR1 nothing for this
destination.

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
BGP routing table entry for 203.0.113.0/24
...
Paths: (2 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external
...
RP/0/RP0/CPU0:RR1#show bgp 203.0.113.0/24
...
Paths: (1 available, best #1)
...
  65100, (Received from a RR-client)
    10.255.0.2 (metric 20) from 10.255.0.2 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (1 available, best #1)
...
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
```

Both of PE3's paths read `Not advertised to any peer`. RR1 and PE1 know only the path through PE2. The backup exit has
a backup and tells no one.

### 1.2 What came before: waiting for BGP to choose again

With nothing added, when PE2 drops out of the core (P1's interface towards PE2 goes down), IS-IS removes PE2's loopback,
10.255.0.2/32. Every BGP speaker watches whether the next hops of its paths can be reached in the RIB (next-hop
tracking). Once 10.255.0.2 cannot be reached, PE3 drops the path through PE2, its path from X2 becomes the best, and PE3
advertises it to RR1.

Until RR1 reflects that path to PE1 and PE1 puts it into the RIB and CEF, PE1 has nowhere to send CE1's packets. And BGP
does not act on next-hop changes at once: it handles them in batches, with an interval in between (the trigger delay).
IOS XR has two intervals: one for changes such as a next hop becoming reachable or unreachable (critical), and one for
IGP metric changes (non-critical).

The defaults for IPv4 unicast are 3000 ms critical and 10000 ms non-critical; for VPNv4 and VPNv6 the critical interval
has been 50 ms since 7.10.1. With PE2 cut off, traffic from CE1 to T stopped for 2.46 seconds when the ingress PE was
IOS XRd, and 3.26 seconds when it was IOS XRv 9000: about the length of that interval. CE1 kept sending every 10 ms
throughout.

A failure of the link between the exit PE2 and X1 is a different story. PE2's eBGP session goes down at once
(fast-external-fallover, on by default in IOS XR) and the withdrawal flows through RR1, so even with nothing added the
outage was 0.14 seconds. The trouble comes when PE2 itself vanishes from the core and the other routers have to notice
through next-hop tracking.

### 1.3 The answer: hand out the backup in advance, and install it in advance

- **Hand it out with ADD-PATH**: PE3 sends its path from X2 to RR1 as an additional path, even though it is not the
  best. RR1 reflects both the best and the backup, and PE1 knows two paths before anything fails.
- **Install it with PIC**: PE1 puts the backup path into the RIB and CEF next to the best path. As soon as IS-IS removes
  10.255.0.2/32, CEF switches to the backup without waiting for BGP. BGP chooses again afterwards, at its own interval.
- **Install one at the backup exit too**: this network is not a VPN, so PE3 must also install its own path through X2
  as a backup (section 2.5).

With all three in place, the outage came down to 0.15 to 0.21 seconds. BGP still waits its three seconds; forwarding no longer waits for BGP.

## 2. How it works

This page follows one route, 203.0.113.0/24. Sections 2.1 to 2.3 are before the failure, while the route travels from
PE3 through RR1 to PE1. Sections 2.4 and 2.5 are the moment of the failure, while a packet from CE1 travels from PE1 to
PE3.

### 2.1 A route reflector reflects only its best path

PE1 does not know the backup for two reasons, and they sit in different places.

- **PE3 does not send it**: as in section 1.1, PE3's best is the path through PE2, learned over iBGP, and PE3 does not
  send that to RR1. The path from X2 is not the best, so PE3 does not send that either.
- **RR1 reflects only one path**: even if RR1 had both paths, it would reflect only its own best to its clients. RR1's
  best is the path through PE2 (local preference 200), so PE1 would still receive one path.

Only one path fits because of how BGP UPDATEs work. When the same prefix arrives again from the same peer, the new one
replaces the old one (an implicit withdrawal). On one session, one prefix carries one path. To carry a second, the paths
need a mark that tells them apart (section 2.2).

For the first reason alone, best-external is an answer: when the best path is an iBGP path, it advertises the router's
best eBGP path to its iBGP and route-reflector peers. On PE3 it gives RR1 two paths, but RR1 still reflects only the
best, and PE1 still has one. With an IOS XRd ingress the outage was 3.02 seconds, no better than with nothing added.

Besides, Cisco's documents list best-external only for the VPNv4, VPNv6, VRF, L2VPN and labelled unicast address
families, and say that unlabelled best-external is not supported because it may create a routing loop (the reason is in
section 2.5). On this release (26.1.1) it commits and works on plain IPv4 unicast, but that disagrees with the documents,
so this lab does not use it ([Appendix](69-m6-appendix.html)).

### 2.2 ADD-PATH: path identifiers and capability negotiation

ADD-PATH (RFC 7911) puts a four-octet path identifier in front of each prefix in an UPDATE. A path is identified by the
pair of prefix and path ID, so any number of paths for the same prefix can be sent side by side. A new path replaces an
old one only when the path ID matches too. The sender picks the path ID, and it means something only on that session.

In the output, `Received Path ID` is the ID the peer attached, and `Local Path ID` is the ID this router attaches when it
sends the path. Following the path through X2: PE3 sends its path with ID 3, RR1 receives it as 3 and sends it on as 2,
and PE1 receives it as 2. A path from a peer that does not use ADD-PATH has `Received Path ID` 0. This is after the
configuration of section 3.1 and the session resets.

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
...
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.21     
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external, backup, add-path
      Received Path ID 0, Local Path ID 3, version 20
RP/0/RP0/CPU0:RR1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  65100, (Received from a RR-client)
    10.255.0.2 (metric 20) from 10.255.0.2 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
      Received Path ID 0, Local Path ID 1, version 5
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.1      
  65100, (Received from a RR-client)
    10.255.0.3 (metric 20) from 10.255.0.3 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, backup, add-path
      Received Path ID 3, Local Path ID 2, version 14
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
      Received Path ID 1, Local Path ID 1, version 9
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal
      Received Path ID 2, Local Path ID 0, version 0
```

PE3's path through X2 is now advertised to RR1 (10.255.0.21). RR1 sends the path from PE3 only to PE1 (10.255.0.1). PE1
is the only client that has said it can receive additional paths.

Before paths with IDs can be sent, both sides must agree on it in the OPEN message (the capability). The agreement is per
address family and per direction: each side announces that it can receive (1), send (2), or both (3). Additional paths
flow from A to B only if A announced send and B announced receive. On this board:

| Router | Send | Receive | Why |
|---|---|---|---|
| PE3 | Announces | — | Sends its own path through X2 to RR1, though it is not the best |
| RR1 | Announces | Announces | Receives from PE3 and reflects to PE1 |
| PE1 | — | Announces | Receives two paths from RR1 |
| PE2 | — | — | PE2's path is the best everywhere, so it needs no additional paths |

Because the capability is negotiated in OPEN, adding the configuration to a running session changes nothing until the
session is re-established. On IOS XR the reset is `clear bgp <neighbor>`. `clear bgp ipv4 unicast <neighbor>` takes
only `soft` or `long-lived-stale` after the address, and anything else gives `% Incomplete command.`. There is no soft
way to renegotiate the capability: OPEN is sent only at the start of a session.

```console
RP/0/RP0/CPU0:PE1#clear bgp ipv4 unicast 10.255.0.21
% Incomplete command.
```

On IOS XR, `additional-paths send` and `additional-paths receive` in the address family make the router announce the
capability to every iBGP neighbor in that address family. eBGP neighbors do not negotiate it (the eBGP session between
PE1 and CE1 stays at `Additional-paths operation: None`; section 3.3). To change it per neighbor, use
`capability additional-paths send` or `receive` under the neighbor (`disable` turns it off).

### 2.3 What to send and what to install: advertise and install in the selection policy

The capability is only an agreement that more than one path may be sent. Which paths are sent is decided by a route
policy attached with `additional-paths selection route-policy <name>`, through `set path-selection`. Without a selection
policy, a router with the send capability still sends only its best path.

This page uses `backup 1`. The backup path is chosen like this: from all the paths, remove the best and every path with
the same next hop as the best, then choose the best of what is left. A backup through the same exit as the best would
fail along with it. There is one backup only, and the only number `backup` accepts is 1.

The keyword after `backup 1` decides what is done with the backup.

| `set path-selection …` | Backup installed in the RIB and CEF? | Advertised |
|---|---|---|
| `backup 1 advertise` | No | The best and the backup |
| `backup 1 install` | Yes (PIC) | The best only |
| `backup 1 advertise install` | Yes (PIC) | The best and the backup |

There are also `all` (all paths), `group-best` (the best from each AS), `multipath` (the multipaths) and `best-path` (the
best only) (`set path-selection ?`).

On a router that computed a backup, the backup path's line carries `backup, add-path` (PE3 and RR1 in section 2.2). PE1
has only `receive`, so it receives the second path but computes no backup. In section 2.2, PE1's second path carries no
marks, and its `Local Path ID` is 0. A backup that has only been received is not used for anything yet.

On this board, PE3 and RR1 get `backup 1 advertise`, and PE1 gets `backup 1 install` (section 2.4). PE3 gets `install`
as well later (section 2.5).

### 2.4 PIC: the backup already in the forwarding table

`install` puts the backup path into the RIB and CEF, next to the best path. In the RIB, `show route … detail` shows
`Number of pic paths 1` and `BGP backup path` on the backup's line; in CEF, `show cef … detail` shows a path marked
`recursive, backup` (section 3.3). The backup is only installed; normal traffic takes the best path.

The speed comes from CEF's hierarchy. 203.0.113.0/24 does not point at an interface. It points at the next hop
10.255.0.2/32 (`recursive`), and 10.255.0.2/32, an IS-IS route, points at the interface towards P1. BGP routes with the
same next hop share this next-hop part.

When IS-IS removes 10.255.0.2/32, the shared part can no longer be resolved (`unresolved`), and every route that has a
backup moves to it at that moment. One change does it, however many routes there are: hence Prefix Independent
Convergence. On this board only 203.0.113.0/24 has a backup, so the "prefix independent" part of the name goes untested
here.

At a failure, things happen in this order.

- P1's interface towards PE2 goes down, and IS-IS removes 10.255.0.2/32.
- As soon as the path through 10.255.0.2 cannot be resolved, PE1's CEF starts sending through the backup, 10.255.0.3.
  BGP has done nothing yet.
- After the critical interval (3 seconds), PE1's BGP chooses again, and the path through PE3 becomes the best. RR1
  chooses again in the same way.

This is PE1 just after P1's interface towards PE2 was shut down. CEF marks the path through PE2 `unresolved`, and the
path in use (`[0]` under `Load distribution`) is already the backup, 10.255.0.3. In the RIB the path through PE2 is
still the primary. BGP made the path through PE3 the best about 2.6 seconds after the CEF update (`LDI Update time`)
(excerpt).

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
 LDI Update time Nov 21 11:19:03.906
...
  Level 1 - Load distribution: 0
  [0] via 10.255.0.3/32, recursive
...
   via 10.255.0.2/32, 0 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xeb5bb20 0x0]
    unresolved
...
   via 10.255.0.3/32, 3 dependencies, recursive, backup [flags 0x6100]
    path-idx 1 NHID 0x0 [0xf79e140 0x0]
    next hop 10.255.0.3/32 via 10.255.0.3/32
...
RP/0/RP0/CPU0:PE1#show route 203.0.113.0/24 detail
...
  Routing Descriptor Blocks
    10.255.0.2, from 10.255.0.21
...
    10.255.0.3, from 10.255.0.21, BGP backup path
...
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Last Modified: Nov 21 11:19:06.541 for 00:00:00
Paths: (1 available, best #1)
...
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, best, group-best
```

Yet with PIC on the ingress PE1 alone, the outage was 2.98 seconds. With PE1's critical BGP interval raised to 10
seconds, it was still about 3 seconds. PE1 had already switched; the packets were being lost further on.

### 2.5 The trap in an unlabelled network: the backup exit sends packets back

Follow the packet one hop further. On the backup path, PE1 pushes the LDP label for 10.255.0.3 and sends the packet to
P1. P1 is the hop before PE3, so it removes the label, and PE3 receives a plain IP packet. A traceroute taken while PE2
is gone shows a label only at P1 as well.

```console
CE1#traceroute 203.0.113.1 source 192.168.1.1 probe 1 timeout 2
Type escape sequence to abort.
Tracing the route to 203.0.113.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.1.254 2 msec
  2 10.0.1.11 [MPLS: Label 24001 Exp 0] 2 msec
  3 10.0.3.3 2 msec
  4 172.16.3.1 3 msec
  5 10.100.23.3 3 msec
```

PE3 looks up the packet's destination, 203.0.113.1, again in its own table. PE3's best is still the iBGP path through
PE2. Until PE3's BGP chooses again after its own critical interval (3 seconds), PE3 tries to send the packets back
towards PE2, and with no way left to PE2 they are dropped. PE1 has switched to the backup exit; the backup exit's own
table still points to the primary.

:::topo
nodes:
  CE1: {at: [0, 1], kind: host, label: "CE1"}
  PE1: {at: [2.2, 1], label: "PE1 (on the backup)"}
  P1: {at: [4.2, 1], label: "P1"}
  RR1: {at: [4.2, 2.5], label: "RR1"}
  PE2: {at: [6.2, 0], label: "PE2 (gone from the core)"}
  PE3: {at: [6.2, 2], label: "PE3 (best: via PE2)"}
  X1: {at: [8.2, 0], label: "X1"}
  X2: {at: [8.2, 2], label: "X2"}
  T: {at: [9.9, 1], kind: host, label: "T"}
links:
  - {a: CE1, b: PE1, label: "CE1 → T", t: 0.45}
  - {a: PE1, b: P1, label: "LDP label\nto 10.255.0.3"}
  - {a: P1, b: PE2, style: dashed, label: "down"}
  - {a: P1, b: PE3, label: "arrives as plain IP\nPE3 sends it back towards PE2"}
  - {a: P1, b: RR1, style: dashed}
  - {a: PE2, b: X1, style: dashed}
  - {a: PE3, b: X2, style: dashed, label: "unused without\nthe CEF backup"}
  - {a: X1, b: T, style: dashed}
  - {a: X2, b: T, style: dashed}
  - {a: X1, b: X2, style: dashed}
:::

The fix is PIC on PE3 as well. PE3's backup is its own eBGP path, learned from X2. With the selection policy set to
`backup 1 advertise install`, PE3 too switches its CEF to the path through X2 as soon as IS-IS removes 10.255.0.2/32.
The outage came down to 0.15 to 0.21 seconds. With the ingress BGP interval set to 10 seconds it stayed under 0.2
seconds: the switch happened in the forwarding tables alone.

With an IOS XRd ingress, the outage stayed at about 3.0 seconds even with PIC on PE3 (0.15 to 0.18 seconds with an
IOS XRv 9000 ingress in the same setup). On this virtual platform, when a
remote PE (PE2 here) disappeared from the IGP, an IOS XRd ingress did not use the installed backup; traffic came back
after about 3 seconds, the time BGP takes to choose again. The displays show the backup correctly. That is why the lab's
PE1 is an IOS XRv 9000 (section 3.4; [Appendix](69-m6-appendix.html)).

In a VPN this sending back does not happen. In an L3VPN (M9), the ingress PE pushes, under the transport label, a VPN
label that the egress PE allocated. When labels are allocated per prefix or per CE, the egress PE sends the packet to the
CE by that VPN label, without looking up the IP address again.

That sending back is why Cisco's documents refuse unlabelled best-external as something that may create a routing loop.
In the per-VRF label mode, with one label per VRF, the egress PE does look up the IP address in the VRF table, and the
documents refuse best-external in that mode too, for the same reason.

## 3. Configuring it in IOS XR

### 3.1 The ADD-PATH configuration

The configuration is six blocks on three routers, and they act on the route 203.0.113.0/24 and on CE1's packets in this
order: ①② PE3 chooses the backup path and sends it; ③ RR1 receives it and reflects the backup as well; ④ PE1 receives
it. That much is this section. ⑤ PE1 installs the backup in the RIB and CEF, and ⑥ PE3 installs its own backup too;
those two are section 3.2.

The top half of the figure shows the route being handed out from PE3 through RR1 to PE1; the bottom half shows a packet
from CE1 just after PE2 has dropped out of the core. The numbers match the notes of the configuration examples in this
section and the next. Rest the pointer on a number in the figure (or tap it on a phone) to see that part of the
configuration.

:::walk
legend: "Top half: before the failure, the backup path is handed out from PE3 to RR1 to PE1. Bottom half: a packet from CE1 to T just after the link between P1 and PE2 has gone down. Blue numbers: the configuration blocks."
rows:
  - panel: PE3
    sub: the backup exit (before the failure)
    items:
      - ref: 1
        head: "**Choose what to send** `set path-selection backup 1 advertise`"
        say: ["The best of the paths left once the best (via PE2) and its next hop are removed → the eBGP path from X2 is the backup"]
      - ref: 2
        head: "**Send capability** `additional-paths send`"
        say: ["Announces send in the OPEN to RR1 (takes effect after a reset)"]
  - {wire: "[[203.0.113.0/24  path ID 3  NH 10.255.0.3]] _PE3 → RR1"}
  - panel: RR1
    sub: route reflector (off the path)
    items:
      - ref: 3
        head: "**Receive, choose, send** `additional-paths receive`, `send`, `selection`"
        say: ["Holds two paths, the best from PE2 and the backup from PE3, and reflects the backup as well"]
  - wire:
      - "[[203.0.113.0/24  path ID 1  NH 10.255.0.2]] _the best"
      - "[[203.0.113.0/24  path ID 2  NH 10.255.0.3]] _the backup; RR1 → PE1"
  - panel: PE1
    sub: the ingress PE (IOS XRv 9000)
    items:
      - ref: 4
        head: "**Receive capability** `additional-paths receive`"
        say: ["Keeps the two as separate paths (path IDs 1 and 2)"]
      - ref: 5
        head: "**Install the backup** `set path-selection backup 1 install`"
        say: ["The path through PE3 goes into the RIB and CEF as the backup. The preparation ends here"]
      - say: ["~P1's link towards PE2 goes down, and IS-IS removes 10.255.0.2/32", "[[IP 192.168.1.1 → 203.0.113.1]] _arrives from CE1 every 10 ms"]
      - ref: 5
        head: "**CEF lookup for 203.0.113.0/24**"
        match:
          - ["via 10.255.0.2/32, … recursive", false, "unresolved (PE2's loopback is gone)"]
          - ["via 10.255.0.3/32, … recursive, backup", true, "taken → no waiting for BGP"]
  - {wire: "[[=LDP  to 10.255.0.3]] [[IP → 203.0.113.1]] _to P1"}
  - {node: P1, say: ["~No BGP. Forwards by the label", "~The hop before PE3, so it removes the label"]}
  - {wire: "[[IP → 203.0.113.1]] ^No label: PE3 looks up the destination again"}
  - panel: PE3
    sub: the backup exit (when the packet arrives)
    items:
      - ref: 6
        head: "**Install its own backup too** `set path-selection backup 1 advertise install`"
        say: ["PE3's IS-IS has removed 10.255.0.2/32 as well"]
        match:
          - ["via 10.255.0.2/32, … recursive", false, "unresolved (the primary exit, PE2)"]
          - ["via 172.16.3.1/32, … bgp-ext, backup", true, "taken → to X2"]
  - {wire: "[[IP → 203.0.113.1]] _out Gi0/0/0/1, to X2"}
  - {node: X2, say: ["~AS 65100. On to T by OSPF"]}
  - {wire: "[[IP → 203.0.113.1]]"}
  - {node: T, kind: host, say: ["~Delivered. Outage 0.15 to 0.21 seconds"]}
  - aside: "Without ⑥ (PE3 only advertises its backup)"
    say: ["~PE3's best is still the iBGP path via PE2 → sends back towards PE2 → no way to PE2, dropped", "~Until PE3's BGP chooses again after the critical interval (3 seconds). Outage about 3 seconds"]
  - aside: "Without the selection line in ③"
    say: ["~RR1 reflects only its best → PE1 never learns the backup, and ⑤ has nothing to install"]
:::

PE3 gets the policy that chooses what to send, and the send capability. The selection policy applies to every prefix in
the address family.

:::config fold PE3 — send the path from X2 to RR1 as a backup, though it is not the best
route-policy ADDPATH-OUT                      ## ① The policy that chooses what to send
  set path-selection backup 1 advertise       ## ① Compute one backup and advertise it; not installed in the RIB or CEF
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths send                       ## ② Announce the send capability to the iBGP neighbors (RR1)
  additional-paths selection route-policy ADDPATH-OUT   ## ① The policy chooses what this address family sends
 !
!
:::

RR1 gets both capabilities, and the policy that chooses what to reflect.

:::config fold RR1 — receive the backup from PE3 and reflect both the best and the backup
route-policy RR-ADDPATH                       ## ③ The policy that chooses what to reflect
  set path-selection backup 1 advertise       ## ③ Advertise one backup in addition to the best
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths send                       ## ③ Capability to send to the clients
  additional-paths receive                    ## ③ Capability to receive from PE3
  additional-paths selection route-policy RR-ADDPATH   ## ③ Computes the backup; without this line only the best is reflected
 !
!
:::

PE1 gets only the receive capability.

:::config fold PE1 — receive a second path from RR1
router bgp 65000
 address-family ipv4 unicast
  additional-paths receive                    ## ④ Announce the receive capability to RR1; receives only, makes no backup
 !
!
:::

Once all three are committed, reset the sessions to RR1 on PE3 and on PE1 so that the capability is negotiated. RR1
needs nothing: its peers reset the sessions. When the resets are done, RR1 and PE1 show `Paths: (2 available, best #1)`
(the output in section 2.2). The best is still the path through PE2.

```console
RP/0/RP0/CPU0:PE3#clear bgp 10.255.0.21
RP/0/RP0/CPU0:PE1#clear bgp 10.255.0.21
```

### 3.2 The PIC configuration

PE1 gets a policy that installs the backup, attached through selection. Selection does not change the capability, so no
reset is needed: after the commit, the backup is in the RIB and CEF straight away.

:::config fold PE1 — keep the backup through PE3 in the RIB and CEF
route-policy PIC                              ## ⑤ The policy that chooses the backup
  set path-selection backup 1 install         ## ⑤ Compute one backup and install it in the RIB and CEF; not advertised
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths selection route-policy PIC ## ⑤ No reset needed
 !
!
:::

On PE3, rewrite the policy from section 3.1. An IOS XR route policy is replaced as a whole, not edited line by line, so
entering an existing policy's name gives a warning.

```console
RP/0/RP0/CPU0:PE3(config)#route-policy ADDPATH-OUT
% WARNING: Policy object route-policy ADDPATH-OUT exists! Reconfiguring it via CLI will replace current definition. Use abort to cancel.
RP/0/RP0/CPU0:PE3(config-rpl)#  set path-selection backup 1 advertise install
RP/0/RP0/CPU0:PE3(config-rpl)#end-policy
RP/0/RP0/CPU0:PE3(config)#commit
```

:::config fold PE3 — keep its own path from X2 in the RIB and CEF as a backup too
route-policy ADDPATH-OUT                      ## ⑥ Rewritten under the same name; replaces the old contents
  set path-selection backup 1 advertise install   ## ⑥ Advertise the backup (as in ①) and install it in its own RIB and CEF
end-policy
:::

IOS XE chooses the paths to send by number and keyword, and says per neighbor which of the chosen paths go out.
Installing the backup in the RIB and CEF is one line. IOS XE's documents name PIC core (on by default) and PIC edge
separately, and give `bgp additional-paths install` as the PIC edge configuration.

| What | IOS XR | IOS XE |
|---|---|---|
| Announce the capability (whole address family) | `additional-paths send`, `additional-paths receive` | `bgp additional-paths send receive` (either one alone also works) |
| Announce the capability (per neighbor) | `capability additional-paths send`, `receive` under the neighbor | `neighbor <neighbor> additional-paths send receive` |
| Choose the paths to send | `set path-selection …` in a route policy, attached with `additional-paths selection route-policy` | `bgp additional-paths select best 2` (also `group-best`, `all`) |
| Send them to a neighbor | Decided by the selection policy | `neighbor <neighbor> advertise additional-paths best 2` |
| Install the backup in the RIB and CEF | `set path-selection backup 1 install` | `bgp additional-paths install` |

### 3.3 Reading the output

**`show bgp <prefix>`**: on PE1 after section 3.2, the second path carries `backup, add-path`, and its `Local Path ID`
goes from 0 to 2 (compare the output in section 2.2).

```console
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, backup, add-path
      Received Path ID 2, Local Path ID 2, version 12
      Originator: 10.255.0.3, Cluster list: 10.255.0.21
```

- `Paths: (2 available, best #1)`: two paths; the first is the best.
- `backup, add-path`: the path the selection policy chose as the backup.
- `Received Path ID 2`: the path ID RR1 attached to this path.

**`show route <prefix> detail`**: with a backup in the RIB, the entry shows `Number of pic paths 1`, and the backup's
line ends in `BGP backup path`. Without a backup, the two lines `Tag 65100` and `Number of pic paths …` are one line,
`Tag 65100, type internal`.

```console
RP/0/RP0/CPU0:PE1#show route 203.0.113.0/24 detail

Routing entry for 203.0.113.0/24
  Known via "bgp 65000", distance 200, metric 11
  Tag 65100
  Number of pic paths 1 , type internal
  Installed Nov 21 09:53:57.531 for 00:00:22
  Routing Descriptor Blocks
    10.255.0.2, from 10.255.0.21
      Route metric is 11, Wt is 1
...
    10.255.0.3, from 10.255.0.21, BGP backup path
      Route metric is 11, Wt is 1
...
```

**`show cef <prefix> detail`**: CEF lists the primary and the backup, and the backup is marked `backup`. PE3's backup is
the eBGP path from X2, which is also marked `bgp-ext` (excerpt).

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
   via 10.255.0.2/32, 3 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xf79e080 0x0], Internal 0x110e10a0
    next hop 10.255.0.2/32 via 10.255.0.2/32
...
   via 10.255.0.3/32, 2 dependencies, recursive, backup [flags 0x6100]
    path-idx 1 NHID 0x0 [0xf79e140 0x0]
    next hop 10.255.0.3/32 via 10.255.0.3/32
RP/0/RP0/CPU0:PE3#show cef 203.0.113.0/24 detail
...
   via 10.255.0.2/32, 2 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0x88531068 0x0], Internal 0x8aad50a0
    next hop 10.255.0.2/32 via 10.255.0.2/32
   via 172.16.3.1/32, 2 dependencies, recursive, bgp-ext, backup [flags 0x6120]
    path-idx 1 NHID 0x0 [0x88539800 0x0]
    next hop 172.16.3.1/32 via 172.16.3.1/32
```

- `recursive`: a path that points at a next hop, not an interface; the next hop is looked up through IS-IS.
- `backup`: the backup, not used in normal operation.
- Just after the failure, the primary line through 10.255.0.2 reads `unresolved`, while the backup stays resolved
  (the output in section 2.4).

**`show bgp nexthops`**: the next-hop tracking intervals, and whether each next hop can be reached. In `Status`, `[R]`
means reachable and `[UR]` unreachable (excerpt).

```console
RP/0/RP0/CPU0:PE1#show bgp nexthops
...
Gateway Address Family: IPv4 Unicast
Table ID: 0xe0000000
...
Critical Trigger Delay: 3000msec
Non-critical Trigger Delay: 10000msec
...
Status codes: R/UR Reachable/Unreachable
              C/NC Connected/Not-connected
              L/NL Local/Non-local
              PR   Pending Registration
              I    Invalid (Policy drop)
Next Hop        Status          Metric     Tbl-ID   Notf   LastRIBEvent      RefCount
10.255.0.2      [R][NC][NL]         20   e0000000   0/0    00:08:24 (Reg)        1/3
...
10.255.0.21     [R][NC][NL]         20   e0000000   1/0    00:10:30 (Cri)        0/3
172.16.1.1      [R][C][NL]           0   e0000000   1/0    00:10:46 (Cri)        1/4
```

**`show bgp neighbor <neighbor>`**: after the reset, an iBGP neighbor shows the lines `Additional-paths Send:` and
`Additional-paths Receive:` under `AF-dependent capabilities:` in the address-family part. Each direction shows
`advertised` (this router announced it) and `received` (the peer announced it), and a direction with both
(`advertised and received`) is in use.

PE3 has only the send direction complete and PE1 only the receive direction, and `Additional-paths operation:` reads
`Send` and `Receive` respectively. An eBGP neighbor shows neither line and stays at `None`. These are PE3's and PE1's
iBGP sessions with RR1 and PE1's eBGP session with CE1 (excerpt).

```console
RP/0/RP0/CPU0:PE3#show bgp neighbor 10.255.0.21
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Additional-paths Send: advertised and received
    Additional-paths Receive: received
    Extended Nexthop Encoding: advertised and received
...
  Additional-paths operation: Send
...
RP/0/RP0/CPU0:PE1#show bgp neighbor 10.255.0.21
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Additional-paths Send: received
    Additional-paths Receive: advertised and received
    Extended Nexthop Encoding: advertised and received
...
  Additional-paths operation: Receive
...
RP/0/RP0/CPU0:PE1#show bgp neighbor 172.16.1.1
...
 Remote AS 65001, local AS 65000, external link
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Extended Nexthop Encoding: advertised
...
  Additional-paths operation: None
```

| Command | What to look at |
|---|---|
| `show bgp <prefix>` | The number of paths (`Paths:`), the marks `backup` and `add-path`, `Received Path ID` and `Local Path ID`, which neighbors a path is advertised to |
| `show bgp neighbor <neighbor>` | The capability lines (`Additional-paths Send:`, `Receive:`) under `AF-dependent capabilities:` and `Additional-paths operation:` in the address family |
| `show route <prefix> detail` | `Number of pic paths`, and `BGP backup path` on the backup's line |
| `show cef <prefix> detail` | The primary and the backup (`recursive, backup`), and `unresolved` during a failure |
| `show bgp nexthops` | The next-hop tracking intervals (`Critical Trigger Delay`, `Non-critical Trigger Delay`) and whether each next hop can be reached |

### 3.4 Pitfalls

- **Adding the capability and stopping there**: it is negotiated in OPEN, so `Additional-paths operation: None` stays
  until the session is reset. The reset is `clear bgp <neighbor>`; `clear bgp ipv4 unicast <neighbor>` takes only
  `soft` or `long-lived-stale` after it.
- **A route reflector without selection**: with send and receive alone, RR1 reflects only its best path.
- **eBGP neighbors**: send and receive in the address family announce the capability to iBGP neighbors only. The eBGP
  session with CE1 does not negotiate it.
- **Receiving is not installing**: with `receive` alone, PE1's second path does not become a backup (`Local Path ID 0`,
  no marks). The backup is installed by PE1's own selection policy with `install`.
- **PIC on the ingress alone**: in an unlabelled network, the backup exit looks up the destination again in its own table
  and sends the packets back towards the primary exit. Put `install` on the backup exit too.
- **One backup**: `backup` takes only 1. A path with the same next hop as the best never becomes the backup.
- **An IOS XRd ingress on this virtual platform**: when a remote PE disappeared from the IGP, it did not use the
  installed backup, and traffic came back after about 3 seconds (the displays show the backup correctly). Local failures
  were fast: PE2 (IOS XRd) switched to its backup through PE3 in 0.05 seconds when it lost its link to X1. Use an
  IOS XRv 9000 as the ingress when PIC has to be shown with traffic ([Appendix](69-m6-appendix.html)).

Do Tasks M6-5 and M6-6 in lab **XRT-17**. As the lab starts, neither ADD-PATH nor PIC is configured anywhere.

<p class="tolab"><a href="/_learn?id=XRT-17">Open lab XRT-17 in the workspace</a> — <a href="64-m6-practice-2.html">Tasks M6-5 and M6-6</a></p>

:::note
The output in sections 2.2, 2.4 and 2.5, the steps in sections 3.1 and 3.2, the `show bgp`, `show route`, `show cef`
and `show bgp neighbor` output in section 3.3, and the outages of 0.15 to 0.21 s and 2.98 s in the text and the figure
were taken on XRT-17 with the task values (IOS XRv 9000 26.1.1 on PE1; IOS XRd 26.1.1 on PE2, PE3, P1 and RR1;
IOS XE 17.15, IOL, on CE1, X1, X2 and T). The output in section 1.1, the `show bgp nexthops` output in section 3.3 and
the other outage figures come from another board on which PE1 to PE3, P1, RR1, CE1, X1, X2 and T have the same names
and addresses as on XRT-17; there PE1 ran IOS XRd 26.1.1, and a second ingress PE ran IOS XRv 9000 26.1.1.
How the outages were measured: on both boards, an IP SLA udp-jitter operation from CE1 (192.168.1.1) to T every 10 ms,
counting the length of the run of lost packets in the forward direction (Loss Period Length). The failure was a
shutdown of P1's interface towards PE2 (stopping a link in CML does not bring the IOS XR interfaces down on this
virtual platform; M10, section 3). Figures on XRT-17: PIC on PE1 and PE3, 0.21 s and 0.15 s (two runs); PIC on PE1
alone, 2.98 s. Figures on the other board: nothing added, 2.46 s (IOS XRd ingress) and 3.26 s (IOS XRv 9000 ingress); the link between PE2 and X1 cut, 0.14 s
(IOS XRd ingress), and 0.05 s with PIC on PE2 as well (backup through PE3); best-external alone, 3.02 s (IOS XRd); PIC on the ingress alone, 3.54 s (IOS XRd) and 3.01 s
(IOS XRv 9000), and with the ingress critical interval at 10 s, 2.99 s and 2.93 s; PIC on PE3 as well, 0.18 s and 0.15 s
(IOS XRv 9000, ingress interval still 10 s) and 2.96 s, 3.02 s and 3.01 s (IOS XRd). In the ingress-only PIC runs and
the 0.15 s run, PE3 advertised its path through X2 with best-external. In the form used on this page (PE3 advertises it
with ADD-PATH, no best-external) the figures were 0.18 s (IOS XRv 9000) and 3.01 s (IOS XRd).
Sources: the Routing Command Reference for Cisco ASR 9000 Series Routers (`additional-paths send`, `receive` and
`selection`; the capability enabled automatically for iBGP neighbors; the reset it needs; the syntax of
`set path-selection` and the backup number being 1; the address families of `advertise best-external` and "Unlabelled
best-external is not supported as it may create routing loop"; the `nexthop trigger-delay` defaults and the 7.10.1
change); the Routing Configuration Guide for Cisco ASR 9000 Series Routers, IOS XR 24.x and 26.x, "Implementing BGP"
(critical and non-critical next-hop events, Installing Primary Backup Path for PIC, BGP PIC for RIB and FIB, the per-VRF
label mode and best-external); the BGP Configuration Guide for Cisco NCS 5500, IOS XR 25.x (BGP Additional Paths, the
best-external procedure); the TAC tech note "Configure and Verify BGP Path Selection in IOS-XR" (Doc ID 217097: what each
`set path-selection` keyword does, at most one backup in the RIB and CEF, the output marks); the Cisco IOS XR Routing
Configuration Guide for the XR 12000, Release 4.1 (how the backup is chosen); the Release Notes for ASR 9000, IOS XR
5.1.1 (the prefix-independent FIB update); the IP Routing Configuration Guide, Cisco IOS XE 17.x, "BGP Additional Paths"
and "BGP PIC Edge for IP and MPLS-VPN" (the IOS XE commands; not run on this board); RFC 7911 (path identifiers, the
Send/Receive values of the capability). All checked in November 2026.
The following come from measurements: the path IDs and path marks; the capability lines and the values of
`Additional-paths operation:`; selection needing no reset; `% Incomplete command.` from
`clear bgp ipv4 unicast <neighbor>`; the timing of CEF, the RIB and BGP just after the failure; the backup exit sending
packets back; the 3 seconds of an IOS XRd ingress.
Where the documents and the device differ or are silent: the documents do not support `advertise best-external` on plain
IPv4 unicast, but on 26.1.1 it committed and took effect on both IOS XRd and IOS XRv 9000. No Cisco document describes
how PIC behaves on IOS XRd.
:::
