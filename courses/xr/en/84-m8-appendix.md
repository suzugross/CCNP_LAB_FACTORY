# M8 — Appendix: Unified MPLS in pictures

This appendix tells the story of the page *M8 — Unified MPLS* again, slowly and with pictures, and leaves out the
commands. Read it before that page, or whenever the page gets dense.

## 1. What has to be built

A provider's services, such as the Layer 3 VPNs of unit M9, need a **path of labels** from the provider edge (PE)
where the traffic enters to the PE where it leaves. Every router on the way forwards on the label alone and never
looks at the customer's address. The end of the path is the exit PE's loopback: the address that stands for the router
itself and does not go away when one of its links fails.

:::topo
nodes:
  PE1: {at: [0, 0], label: "PE (entry)"}
  P1: {at: [1.4, 0], label: "P"}
  P2: {at: [2.8, 0], label: "P"}
  PE2: {at: [4.2, 0], label: "PE (exit)"}
links:
  - [PE1, P1, "label"]
  - [P1, P2, "label"]
  - [P2, PE2, "label"]
:::

Inside one IGP domain, LDP builds that path, as on the first M8 page. This page is about building it when the
network is too big for one domain: a core, and many access networks around it.

## 2. Three ways to build it

### 2.1 One IGP for everything

Put every router, core and access alike, into one IS-IS and one LDP.

:::topo
nodes:
  A1: {at: [0, 0], kind: cloud, label: "access ring 1 (20 routers)"}
  A2: {at: [0, 1.2], kind: cloud, label: "access ring 2 (20 routers)"}
  A3: {at: [0, 2.4], kind: cloud, label: "access ring 3 (20 routers)"}
  C: {at: [2.8, 1.2], kind: cloud, label: "core (10 routers)"}
links:
  - [A1, C]
  - [A2, C]
  - [A3, C]
frames:
  - {label: "one IS-IS, one LDP", nodes: [A1, A2, A3, C]}
:::

This works, and it is the simplest. But every router keeps every router and every link of the whole network, and
when a link flaps in ring 3, the routers of ring 1 and of the core run SPF again too. Access routers are usually small
and cheap. With thousands of them, this does not hold.

### 2.2 Separate IGPs, loopbacks copied across

Give each part its own IGP, and redistribute the loopbacks between the IGPs so that LDP can still build the path.

:::topo
nodes:
  A1: {at: [0, 0], kind: cloud, label: "access ring 1"}
  A2: {at: [0, 1.3], kind: cloud, label: "access ring 2"}
  A3: {at: [0, 2.6], kind: cloud, label: "access ring 3"}
  C: {at: [3, 1.3], kind: cloud, label: "core"}
links:
  - [A1, C, "redistribute"]
  - [A2, C, "redistribute"]
  - [A3, C, "redistribute"]
frames:
  - {label: "IS-IS 1", nodes: [A1]}
  - {label: "IS-IS 2", nodes: [A2]}
  - {label: "IS-IS 3", nodes: [A3]}
  - {label: "IS-IS core", nodes: [C]}
:::

The IGPs are separate on paper, but every loopback still ends up everywhere: the core learns the loopbacks of every
access router, and each ring learns those of the other rings. The amount to remember is what it was in 2.1, and every
point of redistribution needs its own care.

### 2.3 Separate IGPs, PE loopbacks in BGP (Unified MPLS)

Keep the IGPs separate and copy nothing between them. A **border** router sits between each access network and the
core. The borders pass only the loopbacks of the PEs across, in BGP, each with a label.

:::topo
nodes:
  A1: {at: [0, 0], kind: cloud, label: "access ring 1"}
  A2: {at: [0, 1.3], kind: cloud, label: "access ring 2"}
  A3: {at: [0, 2.6], kind: cloud, label: "access ring 3"}
  B1: {at: [1.6, 0], label: "border"}
  B2: {at: [1.6, 1.3], label: "border"}
  B3: {at: [1.6, 2.6], label: "border"}
  C: {at: [3.4, 1.3], kind: cloud, label: "core"}
links:
  - [A1, B1]
  - [A2, B2]
  - [A3, B3]
  - [B1, C, "BGP"]
  - [B2, C, "BGP"]
  - [B3, C, "BGP"]
frames:
  - {label: "IS-IS 1", nodes: [A1]}
  - {label: "IS-IS 2", nodes: [A2]}
  - {label: "IS-IS 3", nodes: [A3]}
  - {label: "IS-IS core", nodes: [C]}
:::

Each IGP knows only its own part, plus the address of its border. A flap in ring 3 stays in ring 3. The BGP routes do
not carry the topology, only "this PE is behind that border": when a link inside a ring fails and the ring's IGP
finds another way, the BGP routes do not change, because their next hop, the border, does not change. BGP changes
only when a PE itself appears or disappears. BGP was made to carry the hundreds of thousands of routes of the
Internet, so a few thousand loopbacks are no burden, and a policy can limit which loopbacks go to which access
network.

| | 2.1 One IGP | 2.2 Loopbacks copied | 2.3 Unified MPLS |
|---|---|---|---|
| An access router knows | the whole network | every loopback | its own ring and its border |
| A core router knows | the whole network | every loopback | the core |
| SPF after a flap in ring 3 runs on | every router | ring 3 | ring 3 |
| The path from PE to PE is built by | LDP | LDP | LDP in each part, BGP labels at the borders |

The border is what stitches the parts together. It belongs to both IGPs and both LDPs, but it does not make them talk
to each other: it joins them only through BGP, in the control plane, and by swapping labels, in the forwarding. Real
networks usually have two borders for each access network, so that one failure does not cut the access network off.
The lab has one, to keep the picture small.

## 3. Who knows what in the lab

The lab XRT-08 is the smallest version of 2.3: one access network, one border and one core.

| Router | Knows | Does not know |
|---|---|---|
| RT02, RT05 (PEs) | customer A's routes, from each other in BGP; the other PE's loopback, from XR01 in BGP with a label | the roads inside the other domain |
| XR01 (border) | the loopbacks and LDP labels of both domains | customer A's routes (after Task M8-8) |
| RT01, RT03 (core) | the core's loopbacks and labels | customer A's routes; that the access network exists |
| RT04 (access) | the access network's loopbacks and labels, and XR01's loopback | customer A's routes; that the core exists |

The address of the border is the one thing that both IGPs carry. Without it, the access routers could not reach XR01
for LDP and BGP at all (Task M8-6).

## 4. Who talks to whom

IS-IS forms its neighbours over a link, inside one domain, and in this lab LDP does the same. BGP neighbours can be
anywhere, as long as they can reach each other's loopback. In the lab there are three BGP sessions:

:::topo
nodes:
  RT05: {at: [0, 0], label: "RT05 (PE)"}
  RT02: {at: [4, 0], label: "RT02 (PE)"}
  XR01: {at: [2, 1.2], label: "XR01 (border)"}
links:
  - {a: RT05, b: RT02, label: "customer A's routes", style: dashed}
  - {a: RT05, b: XR01, label: "PE loopbacks, labeled", style: dashed}
  - {a: XR01, b: RT02, label: "PE loopbacks, labeled", style: dashed}
:::

| Pair | IS-IS | LDP | BGP |
|---|---|---|---|
| RT02 and RT01 or RT03 | yes (CORE) | yes | — |
| XR01 and RT01 or RT03 | yes (CORE) | yes | — |
| XR01 and RT04 | yes (ACCESS) | yes | — |
| RT04 and RT05 | yes (ACCESS) | yes | — |
| XR01 and RT02 | — | — | yes: PE loopbacks with labels, and XR01's own customer site |
| XR01 and RT05 | — | — | yes: PE loopbacks with labels |
| RT02 and RT05 | — | — | yes: customer A's routes only |

RT02 and RT05 are neighbours in BGP only. They are not next to each other and are in different IGP domains, so there
is no IS-IS or LDP between them. Their BGP session is a TCP connection between their loopbacks, and the only way each
of them knows to the other's loopback is the labeled route from XR01. That is why the session stays down until Task
M8-7 works, and why its own packets then cross XR01 with labels.

## 5. What the border tells the PEs

For RT05's loopback, XR01 sends RT02 a BGP route with three parts:

```text
destination: 10.255.0.15/32   (RT05's loopback)
next hop:    10.255.0.1       (XR01 itself)   "RT05 is behind me. Hand it to me."
label:       24003                            "Put this label on it. It tells me that it goes to RT05."
```

The next hop says **where** to hand the packet: to XR01. RT02 never learns where RT05 really is, only that it is
behind XR01. The label says **what to tell XR01**: XR01 reads 24003 and knows that the packet goes to RT05.

The route is usable only when RT02 can reach that next hop, in two ways:

- **in IS-IS**: XR01's loopback has to be in RT02's IGP. On the core side it was there since lab XRT-07; on the access
  side, Task M8-6 put it there. A BGP route whose next hop is not reachable shows as `(inaccessible)` and is not used.
- **with an LDP label**: the core routers forward on labels only. Without an LDP label for XR01's loopback, RT02 would
  have no label that takes the packet to XR01, and the core routers, which do not know XR01's BGP labels, could not
  deliver it. Because XR01's loopback is in IS-IS, LDP binds a label to it like to any other IGP prefix.

Put together, the PE puts two labels on the packet:

| | Meaning | From RT02 | From RT05 |
|---|---|---|---|
| top (outer) | "to XR01": the LDP label of its own domain | 20, from RT01 | RT04's label for XR01 |
| bottom (inner) | "to the other PE": XR01's BGP label | 24003 (to RT05) | 24001 (to RT02) |

## 6. One packet, step by step

A packet from customer A's site behind RT02 to the new site behind RT05. The numbers are the labels of the lab; in
this picture the traffic goes from left to right.

:::topo
nodes:
  RT02: {at: [0, 0], label: "RT02"}
  RT01: {at: [1.5, 0], label: "RT01"}
  XR01: {at: [3, 0], label: "XR01"}
  RT04: {at: [4.5, 0], label: "RT04"}
  RT05: {at: [6, 0], label: "RT05"}
links:
  - [RT02, RT01, "[20 | 24003]"]
  - [RT01, XR01, "[0 | 24003]"]
  - [XR01, RT04, "[16]"]
  - [RT04, RT05, "no label"]
:::

1. **RT02** knows from BGP that 10.50.0.0/16 is behind RT05. It knows from BGP with a label that RT05 is reached
   through XR01 with XR01's label 24003, and from LDP that XR01 is reached with RT01's label 20. It puts both labels
   on the packet, 24003 below and 20 on top.
2. **RT01** reads only the top label. 20 means "to XR01". It swaps it for 0, as XR01 asked (Task M8-5), and passes the
   packet on. It never learns where the packet really goes.
3. **XR01** removes the 0 and finds 24003, its own label, which means "to RT05". It swaps it for 16, the label that
   RT04 gave it in LDP for RT05's loopback.
4. **RT04** sees 16 and knows that the next router is RT05 itself, so it removes the label.
5. **RT05** receives a plain IP packet for 10.50.0.1, its own network.

Step 3 does not look at BGP for each packet. BGP and LDP have prepared one row of XR01's forwarding table for each PE
loopback in advance, and the packet only follows the row:

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop
Label  Label       or ID              Interface
24001  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11
24003  16          10.255.0.15/32     Gi0/0/0/2    10.0.14.14
```

The first row is for RT02, toward the core; the second is for RT05, toward the access network. The incoming label on
the left is the one that XR01 gave out in BGP; the outgoing label on the right is the one that it received in LDP in
the other domain. Both rows say 16, but they are two different labels from two different
neighbours, RT01 and RT04. RT05's own BGP label is implicit null ("no label needed at the end"), so only the LDP label
goes out. If another border followed behind RT05 and gave XR01 a real label, XR01 would swap to that label and put its
LDP label on top, and two labels would go out.

The way back is the same picture from right to left, with other numbers.

## 7. The border's two jobs

For each PE loopback that it passes on, the border has to say the two things of section 5: **"hand it to me"** (it
sets itself as the next hop) and **"with my label on it"** (it advertises a label of its own). On IOS XR each of the
two needs its own setting, and only the two together work. That is what Task M8-7 is about.

| "Hand it to me" (next hop self applied) | "With my label" (label allocated) | What RT02 sees for RT05's loopback | Customer traffic |
|---|---|---|---|
| no | no | next hop RT05, which RT02 cannot reach | stops |
| yes | no | nothing: XR01 does not send it | stops |
| no | yes | next hop RT05, which RT02 cannot reach | stops |
| yes | yes | next hop XR01, with XR01's label | flows |

In the lab, `next-hop-self` was configured in all four rows. On IOS XR, a route reflector applies it to the routes
that it reflects only with `ibgp policy out enforce-modifications`, and the label comes from `allocate-label`.

## 8. Why it looks like a lot of work for six routers

With six routers, one IGP would be simpler, and nothing in the lab gets slow or unstable. The benefit of 2.3 appears
only with size: add a hundred access rings to the lab, and the core's IS-IS stays exactly as it is.

There is a second reason. In M8 the service is plain IPv4 in the global routing table. If the border had customer A's
routes, it could route the packet itself even where the label path ends. With a Layer 3 VPN (unit M9), the inner VPN
label can be read only by the exit PE, so the label path has to reach that PE without a gap. Unified MPLS is the road;
the services of M9 travel on it.

## 9. The whole page in a few lines

- Services need a path of labels from PE to PE.
- A big network is split into several IGP domains, so that each stays small and calm.
- The IGPs exchange nothing. Only the PE loopbacks cross, in BGP, each with a label.
- The border tells each PE "the other PE is behind me, use my label", and swaps its label for the other domain's LDP
  label when the packets come.
- A PE puts two labels on the packet: its own domain's LDP label to the border, and the border's BGP label to the other
  PE. The border's loopback therefore has to be in the PE's IGP and have an LDP label.
- The PEs exchange the customer routes directly in BGP. They are not IS-IS or LDP neighbours.
- The routers in the middle forward on labels only and know nothing beyond their own domain.

<p class="tolab"><a href="82-m8-unified-mpls.html">Back to M8 — Unified MPLS</a></p>
