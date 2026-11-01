# M10 — TI-LFA

This page covers how a router sends traffic around a failed link without waiting for the IGP to finish computing a new
path. It is section 3.3.d of the blueprint, and Task M10-3 uses it. Read section 2 of the previous page, "How segment
routing works" (stacking labels to write a waypoint), first.

## 1. What it is good for

### 1.1 From a failed link to recovery

Say PRIMARY fails. For IS-IS to repair the network the ordinary way, these steps are needed:

1. XR01 and RT01 notice the failure (300 ms with BFD, up to 30 seconds with IS-IS hellos alone).
2. The change is told to every router in an LSP (flooding).
3. Every router computes its shortest paths again (SPF).
4. Every router rewrites its forwarding table. With many prefixes, this is where the time goes.

Until steps 2 to 4 are done, the packets sent to PRIMARY are lost. In a network as small as this lab it takes about
100 ms, but in a large network with many prefixes it takes seconds.

**Fast reroute** (FRR) is the way not to wait for steps 2 to 4. The router next to the failure (the **point of local
repair**, XR01 here) computes a repair path in advance, "if this link fails, send it this way", and puts it in the
forwarding table. It switches to it the moment it notices the failure, so the outage lasts only as long as the detection
in step 1. Meanwhile, IS-IS converges as it always does.

### 1.2 Gaps in earlier repairs

There were ways to build a repair path before SR:

- **Loop-free alternate** (LFA, RFC 5286): just hand the packet to another neighbour, but only if that neighbour will
  not send it back along its shortest path to the destination. Whether the condition holds depends on the topology, and
  some destinations are left with no neighbour that meets it.
- **Remote LFA** (RFC 7490): carry the packet with a tunnel to a farther router, and release it there. It needs targeted
  LDP sessions, and it still cannot cover every destination.
- **RSVP-TE FRR**: set up bypass tunnels in advance. The routers along them need state for the tunnels.

**TI-LFA** (topology-independent LFA, RFC 9855) writes the repair path in SR labels. A path can be written in any
topology, so every destination can be protected. Only the point of local repair is configured; no tunnels and no
targeted sessions are needed.

## 2. How it works: the repair path written in labels

### 2.1 Just handing it to a neighbour sends it back

Say XR01 sends packets for RT01's loopback (16011) over PRIMARY. When PRIMARY fails, the only neighbour XR01 has left is
RT03. So can it just hand the packet to RT03, still with 16011?

From RT03 to RT01, the path back through XR01 (BACKUP 100 + PRIMARY 10 = 110) and the path through RT02 (CORE-B 100 +
CORE-A 10 = 110) cost the same. Right after the failure, RT03 does not know about it yet, so it sends some of the packets
back to XR01, that is, to the failed PRIMARY. That is why RT01's loopback has no plain LFA.

For RT02's loopback it is different. From RT03 to RT02, the direct link at 100 is shorter than going back through XR01
at 120, so RT03 does not send the packet back. RT02 has a plain LFA.

### 2.2 Adding one waypoint

To stop the packet coming back, it is enough to tell RT03 "go to RT02 first". From RT03, the shortest path to RT02 is
the direct link, and from RT02, the shortest path to RT01 is the direct CORE-A link. Neither leg uses PRIMARY. So for the
repair, XR01 stacks RT02's 16012 on top of 16011, and sends the packet to RT03.

:::topo
nodes:
  XR01: [0, 1]
  RT01: [1.4, 0.15]
  RT03: [1.4, 1.85]
  RT02: [2.8, 1]
links:
  - {a: XR01, b: RT01, label: "× PRIMARY", style: dashed}
  - [XR01, RT03, "16012 | 16011"]
  - [RT03, RT02, "16011"]
  - [RT02, RT01, "IP"]
:::

RT03 reads 16012, sends the packet to RT02, and pops 16012 because it is the hop before RT02. RT02 reads 16011, sends
the packet to RT01, and pops 16011 because it is the hop before RT01. RT01 receives a plain IP packet.

This repair path (XR01 → RT03 → RT02 → RT01) is exactly the path that IS-IS chooses once it has converged without
PRIMARY. TI-LFA computes the **post-convergence path** in advance, and chooses the labels that make the packet follow it.
The path is the same during the repair and after convergence, so the traffic does not take a third path while the
network converges.

### 2.3 Choosing the waypoint: P space and Q space

TI-LFA chooses the waypoint from two sets:

- **P space**: the routers that, once XR01 has handed the packet to a neighbour (RT03 here), can be reached from there
  along the shortest path without the failed link. Of the routers in the square, RT03 and RT02.
- **Q space**: the routers from which the destination can be reached along the shortest path without the failed link.
  For RT01, that is RT02 (and RT01 itself).

If a router is in both, it is enough to use it as the waypoint. There are two labels: "to the waypoint" and "to the
destination". The outputs call that router the P node. Here it is RT02, and 16012 in section 2.2 is its label.

Sometimes no router is in both. In the PoC, with BACKUP's metric at 10 and CORE-B still at 100, going from RT03 to RT02
back through XR01 and PRIMARY became cheaper (10 + 10 + 10 = 30), and RT02 left the P space. TI-LFA then joins the last
router of the P space (RT03) to the first router of the Q space (RT02) with an adjacency SID that names the link:

```console
       Backup path: TI-LFA (link), via 10.0.3.13, GigabitEthernet0/0/0/1 RT03, SRGB Base: 16000, Weight: 0, Metric: 130
         P node: RT03.00 [10.255.0.13], Label: ImpNull
         Q node: RT02.00 [10.255.0.12], Label: 23
         Prefix label: 16011
```

Label 23 is RT03's adjacency SID for its link to RT02 (CORE-B) (`show mpls forwarding-table` on RT03 lists it as
`10.0.23.12-A`). RT03 is XR01's neighbour, so no label is pushed for RT03 (`ImpNull`). In the CEF entry the backup read
`{ImplNull 23 16011}`.

### 2.4 In the square

Back on the original metrics, this is the repair path that XR01 prepared for RT01's loopback:

```console
RP/0/RP0/CPU0:XR01#show isis fast-reroute 10.255.0.11/32 detail
L2 10.255.0.11/32 [20/115] Label: 16011, medium priority
     via 10.0.1.11, GigabitEthernet0/0/0/0, Label: ImpNull, RT01, SRGB Base: 16000, Weight: 0
       Backup path: TI-LFA (link), via 10.0.3.13, GigabitEthernet0/0/0/1 RT03, SRGB Base: 16000, Weight: 0, Metric: 220
         P node: RT02.00 [10.255.0.12], Label: 16012
         Prefix label: 16011
         Backup-src: RT01.00
       P: No, TM: 220, LC: No, NP: No, D: No, SRLG: Yes

RP/0/RP0/CPU0:XR01#show cef 10.255.0.11/32 detail
...
   via 10.0.1.11/32, GigabitEthernet0/0/0/0, 4 dependencies, weight 0, class 0, protected [flags 0x400]
     local label 16011      labels imposed {ImplNull}
   via 10.0.3.13/32, GigabitEthernet0/0/0/1, 8 dependencies, weight 0, class 0, backup (TI-LFA) [flags 0xb00]
    next hop 10.0.3.13/32, Repair Node(s): 10.255.0.12
     local label 16011      labels imposed {16012 16011}
```

How to read it: `via 10.0.1.11` is the usual path (PRIMARY), `Backup path: TI-LFA (link), via 10.0.3.13` is the exit of
the repair path (RT03), `P node: RT02.00 … Label: 16012` is the waypoint, and `Prefix label: 16011` is the label of the
destination. `Metric: 220` is the metric of the post-convergence path. In CEF, the usual path is marked `protected` and
the repair path `backup (TI-LFA)`, and the repair path pushes `{16012 16011}`: the figure of section 2.2 exactly.

### 2.5 Configuration

IOS XR needs two lines on each interface: `fast-reroute per-prefix` turns on per-prefix protection, and
`fast-reroute per-prefix ti-lfa` lets it use SR. The default is link protection. Node protection and SRLG protection are
tie-breakers that you add (`fast-reroute per-prefix tiebreaker node-protecting index <n>`). When the repair needs four
labels or more, IOS XR builds it as an automatic SR-TE policy.

The IOS routers of the lab protect their own prefixes too, with `fast-reroute per-prefix level-2 all` and
`fast-reroute ti-lfa level-2` under `router isis` (`show isis fast-reroute ti-lfa tunnel`).

Here are XR01 and an IOS router of the lab (RT01). IOS XR configures it per interface, IOS XE for the whole IS-IS.

:::config fold XR01 — TI-LFA on both core links
router isis CORE
 interface GigabitEthernet0/0/0/0   ## PRIMARY
  address-family ipv4 unicast
   fast-reroute per-prefix          ## for each destination that leaves through this link, compute a repair path in advance
   fast-reroute per-prefix ti-lfa   ## the repair may stack labels (so destinations without a plain LFA get one too)
  !
 !
 interface GigabitEthernet0/0/0/1   ## BACKUP
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
  !
 !
!
:::

:::config RT01 (IOS XE) — from the lab's fixed configuration
router isis CORE
 net 49.0001.0100.0000.0011.00
 is-type level-2-only
 metric-style wide
 segment-routing mpls
 fast-reroute per-prefix level-2 all   ## a repair path for every level-2 destination
 fast-reroute ti-lfa level-2           ## use TI-LFA for the repair
!
:::

## 3. Speed depends on detection

How fast a repair works depends on how fast the failure is detected. In CML, a failed link does not take the interface
down on IOS XRv 9000, even when the link is stopped: IS-IS would wait for its hello hold time, 30 seconds. BFD (unit M7)
brings that down to the BFD detection time, 300 ms with 100 ms × 3 as in the lab.

The lab measured customer A's traffic from CEA1 to CEA2 every 10 ms while a link condition dropped every packet on
PRIMARY:

| On XR01 | Lost (10 ms each) |
|---|---|
| BFD, no TI-LFA | 42 |
| BFD and TI-LFA | 34 to 40 |
| BFD, no TI-LFA, SPF delayed (1 s, growing up to 5 s) | 342 and 467 |
| BFD and TI-LFA, SPF delayed (1 s, growing up to 5 s) | 41 and 34 |

In this small network IS-IS converges about 100 ms after BFD has spoken, so TI-LFA saves little: the detection time
dominates. The difference shows when convergence is slow, as it is in a large network with many prefixes. The lab
imitated that by delaying SPF (`spf-interval`: a first wait of 1 s that grows, up to 5 s, while changes follow each
other, as they did during the tests). With TI-LFA the outage stays at the detection time whatever IS-IS does.

Two more things showed up. BFD on IOS XR dampens a session that flaps: after each failure it waits longer before
bringing the session up again (2 seconds, then 5, and up to two minutes in the lab), and IS-IS waits with it. Wait a
couple of minutes between two tries, or disable dampening (`bfd` → `dampening disable`). And the guides do not promise
50 ms: the IOS XE guide states that TI-LFA "cannot guarantee 50ms".

:::try
Measure TI-LFA yourself with a ping. Do it after Task M10-3.

1. On XR01, under `router isis CORE` → `address-family ipv4 unicast`, add
   `spf-interval initial-wait 5000 secondary-wait 5000 maximum-wait 10000` and commit. This imitates a large network.
2. On CEB1, start `ping 10.102.2.1 source Loopback10 repeat 10000 timeout 1` (customer B, because customer A avoids
   PRIMARY after Task M10-4). While it runs, set a link condition of 100 % loss on PRIMARY in CML (the link's Link
   Conditions tab), and clear it after ten seconds.
3. On XR01, remove the two `fast-reroute` lines from GigabitEthernet0/0/0/0, commit, wait two minutes (BFD dampening),
   and do step 2 again.
4. Put the `fast-reroute` lines back and remove `spf-interval`, and commit.

What the lab measured: with TI-LFA, one ping was lost each time; without it, six were lost each time (twice each). The
ping timeout is one second, so one lost ping means an outage shorter than a second (BFD's 300 ms), and six mean the
five-second wait before SPF on top of it. With the normal SPF timers and TI-LFA, one ping was lost too. After each
failure, BFD dampening kept the adjacency with RT01 down for 40 to 120 seconds once the link condition was cleared.
:::

## 4. Microloops

After the repair has taken over, IS-IS still converges as usual. The routers do not all rewrite their forwarding tables
at the same moment. If, for a short while, router A sends a packet to B on its new table and B still sends it back to A
on its old one, the packet bounces between the two and is lost. This is a **microloop**. TI-LFA handles the repair
right after the failure, but not the loops during the convergence that follows (RFC 9855).

IOS XR has a separate feature, `microloop avoidance segment-routing` in the IS-IS address family. For a while after the
topology changes (`microloop avoidance rib-update-delay`, 5000 ms by default), XR01 sends the affected traffic on a
loop-free path written with stacked labels, and moves to the new shortest path only once the other routers' tables
agree. `show isis protocol` reports `Microloop avoidance: Enabled` with `Type: Segment Routing`. It is off by default on
IOS XR. The IOL routers report `enabled for segment-routing microloop avoidance` in `show isis fast-reroute summary`.

On XR01 it is one line in the IS-IS address family (two, to change the delay).

:::config fold XR01 — microloop avoidance
router isis CORE
 address-family ipv4 unicast
  microloop avoidance segment-routing         ## during convergence, send the affected destinations on a loop-free SR path
  microloop avoidance rib-update-delay 3000   ## (optional) how long before moving to the new shortest path; 5000 ms by default
 !
!
:::

## 5. Command names

| On IOS XE | On IOS XR |
|---|---|
| `fast-reroute per-prefix level-2 all` + `fast-reroute ti-lfa level-2` (under `router isis`) | `fast-reroute per-prefix` + `fast-reroute per-prefix ti-lfa` (per interface) |
| `show isis fast-reroute ti-lfa tunnel` | `show isis fast-reroute <prefix> detail` |
| `show isis fast-reroute summary` | `show isis fast-reroute summary` |

## Practice

In lab **XRT-10**, do Task M10-3. When it is done, go on to the next page, "SR policies and the PCE".

<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t3">Open Task M10-3 in the workspace</a> — <a href="a3-m10-practice-2.html">The tasks</a></p>

:::note
Sources: the Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x (2026: TI-LFA, microloop
avoidance) and its command reference (2025); the IOS XE Segment Routing Configuration Guide (2026: TI-LFA); RFC 5286, 7490
and 9855. All checked October 2026. The repair paths and their labels, the P and Q nodes, the outage measurements and BFD
dampening come from measurement in lab XRT-10 and its PoC.
:::
