# M11 supplement — E-LAN

The pages so far built E-Lines: one customer site to one other. This supplement is about the services that the
XR platforms of this track cannot run: **E-LAN** (many sites in one LAN), **EVPN multihoming** (one site on two PEs) and
**Ethernet OAM** (watching a service with CFM). It covers items 4.2.a, 4.2.c and 4.1.a of the CCNP Service Provider
blueprint.

| Page | Contents | Tasks |
|---|---|---|
| This page | Many sites in one LAN: VPLS, and EVPN's E-LAN | M11-6, M11-7 |
| EVPN multihoming | One site on two PEs, both links in use | M11-8 |
| Ethernet OAM | Watching an E-Line with CFM, measuring delay with Y.1731 | M11-9 |

The lab is **XRT-12**. IOS XRv 9000 refuses bridge domains and has no CFM (appendix), so the PEs here are
**Catalyst 8000V** routers running IOS XE 17.15.1a. The mechanisms of EVPN and CFM do not depend on the OS: the route
types, the Ethernet segment and the maintenance levels are the same on IOS XR. Each section shows the IOS XR form after
the IOS XE one, in the form of Cisco's configuration guides.

:::topo
nodes:
  CE1: {at: [0, 0.3], label: "CE1 (site 1)"}
  SW1: {at: [0, 1.6], label: "SW1 (site 4)"}
  CE2: {at: [0, 2.9], label: "CE2 (site 2)"}
  XE1: {at: [1.9, 0.3], label: "XE1 (PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2 (PE)"}
  P1: {at: [3.8, 1.6], label: "P1 (P, RR)"}
  XE3: {at: [5.7, 1.6], label: "XE3 (PE)"}
  CE3: {at: [7.6, 1.6], label: "CE3 (site 3)"}
links:
  - [CE1, XE1, "Gi2"]
  - [SW1, XE1, "Gi3"]
  - [SW1, XE2, "Gi3"]
  - [CE2, XE2, "Gi2"]
  - [XE1, P1, "CORE-1"]
  - [XE2, P1, "CORE-2"]
  - [P1, XE3, "CORE-3"]
  - [XE3, CE3, "Gi2"]
frames:
  - {label: "AS 65000 (IS-IS CORE, LDP)", nodes: [XE1, XE2, P1, XE3]}
:::

All four sites belong to customer C. P1 is the only core router and also the route reflector for EVPN. SW1 (site 4)
joins on the next page; this page uses sites 1, 2 and 3.

## 1. What it is good for

### 1.1 Three sites in one LAN

Customer C wants its three sites in one VLAN, as if all of them were plugged into one switch: one subnet
(172.31.200.0/24), the customer's own routing, and broadcasts such as ARP reaching every site.

### 1.2 Before: a mesh of E-Lines

With the E-Lines of M11, three sites need three E-Lines (1–2, 1–3, 2–3), and n sites need n(n−1)/2. Worse, an E-Line is
a wire, not a LAN: each CE needs one sub-interface and one subnet per E-Line, and the customer has to route between
them. Adding a fourth site means a new E-Line to every existing site.

### 1.3 The answer: the provider's network as one switch

An **E-LAN** makes the provider's network behave like one Ethernet switch. Each PE holds a **bridge domain**, a small
switch inside the PE: it learns which MAC address is behind which port, sends a frame for a known MAC to that port only,
and copies broadcasts and unknown destinations to every port. The "ports" are the customer's attachment circuits and
the paths to the other PEs. There are two ways to build the paths between PEs: **VPLS** joins the bridge domains with
pseudowires (section 2), and **EVPN** exchanges the MAC addresses in BGP (section 3).

## 2. VPLS

### 2.1 Bridge domains joined by a full mesh of pseudowires

In VPLS, each PE of the E-LAN has a bridge domain with two kinds of members:

- The customer's **attachment circuit** (on IOS XE an EFP, a `service instance` on the port; the same thing as M11's
  l2transport sub-interface).
- A **VFI** (virtual forwarding instance): the set of pseudowires to the other PEs of the same VPLS. Each pseudowire is
  an LDP pseudowire as in M11, with the **VPN ID** as its VC ID (210 here).

Every PE has a pseudowire to every other PE: a **full mesh**. With three PEs that is three pseudowires; the next
sections show why it must be full.

### 2.2 One frame at a time: CE1's ARP

CE1 pings CE3 (172.31.210.3) and first broadcasts an ARP request on VLAN 210. With the full mesh:

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  XE2: [3.4, 0.2]
  XE3: [3.4, 1.8]
  CE2: [5, 0.2]
  CE3: [5, 1.8]
links:
  - [CE1, XE1, "tag 210 | ARP"]
  - [XE1, XE2, "PW 210 (copy)"]
  - [XE1, XE3, "PW 210 (copy)"]
  - [XE2, CE2, "tag 210"]
  - [XE3, CE3, "tag 210"]
:::

1. XE1's EFP takes the frame and pops the tag. The bridge domain learns "CE1's MAC is behind Gi2 service instance 210".
2. The destination is broadcast, so XE1 sends one copy into each pseudowire of the VFI: to XE2 and to XE3. Each copy
   carries the pseudowire label that the other PE gave by LDP, and outside it the transport label to that PE.
3. XE2 and XE3 each learn "CE1's MAC is behind the pseudowire from XE1", and send the frame out of their own EFPs (the
   tag 210 is pushed again). XE2 does **not** send it into its pseudowire to XE3.
4. CE3 answers with a unicast frame to CE1's MAC. XE3 already knows that MAC is behind the pseudowire from XE1, and sends
   the answer there only.

The PEs learn MAC addresses from the frames themselves, as switches do (learning in the data plane). XE1's bridge
domain then shows the local MAC on the EFP and the remote one on a pseudowire:

```console
XE1#show bridge-domain 210
Bridge-domain 210 (3 ports in all)
State: UP                    Mac learning: Enabled
    GigabitEthernet2 service instance 210
    vfi VPLS210 neighbor 10.255.0.42 210
    vfi VPLS210 neighbor 10.255.0.43 210
   AED MAC address    Policy  Tag       Age  Pseudoport
   0   AABB.CC00.6A00 forward dynamic   297  VPLS210.404011, VPLS
                                             VC_LABEL: 17, Intf: GigabitEthernet1
   0   AABB.CC00.6900 forward dynamic   287  GigabitEthernet2.EFP210
```

### 2.3 Split horizon: why the mesh must be full

Step 3 is the rule that keeps VPLS free of loops: **a PE never sends a frame that came in on a pseudowire out of another
pseudowire of the same VFI** (split horizon). Without it, a broadcast would go round XE1 → XE2 → XE3 → XE1 for ever,
since Ethernet frames have no TTL. Because every PE has a direct pseudowire to every other, no frame ever needs a second
pseudowire hop.

The other side of the rule: if a pseudowire is missing, nothing relays around the gap. Suppose XE1 and XE3 each have a
pseudowire to XE2 only (a hub and spoke):

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  XE2: [3.2, 1]
  XE3: [5.2, 1]
  CE3: [6.8, 1]
links:
  - [CE1, XE1, "ARP"]
  - [XE1, XE2, "PW 210"]
  - [XE2, XE3, "PW 210\nnot sent (split horizon)"]
  - [XE3, CE3, ""]
:::

Then CE1's ping to CE3 fails, although XE2 has learned both CE1's and CE3's MACs, each on its pseudowire: XE2 knows
where CE3 is, and still will not send the frame there. `show l2vpn vfi` marks split horizon with `S` = `Y`:

```console
XE2#show l2vpn vfi name VPLS210
Legend: RT=Route-target, S=Split-horizon, Y=Yes, N=No
VFI name: VPLS210, state: up, type: multipoint, signaling: LDP
  VPN ID: 210
  Bridge-Domain 210 attachment circuits:
  Pseudo-port interface: pseudowire100001
  Interface          Peer Address     VC ID        S
  pseudowire100003   10.255.0.43      210          Y
  pseudowire100002   10.255.0.41      210          Y
```

A hub and spoke can be built on purpose (H-VPLS, with split horizon turned off on the hub's spoke pseudowires), but
then the hub is in charge of preventing loops. In a plain VPLS, the full mesh is the loop protection. (The `member` line
of the Catalyst 8000V's VFI has no option to turn split horizon off.)

### 2.4 Configuring VPLS on IOS XE

:::config Catalyst 8000V (IOS XE 17.15) — XE1's part of VPLS 210 (all three PEs have the same form)
l2vpn vfi context VPLS210                          ## the VFI: this PE's set of pseudowires for the VPLS
 vpn id 210                                        ## also the VC ID of every pseudowire; the same on all PEs
 member 10.255.0.42 encapsulation mpls             ## one line per other PE (the full mesh)
 member 10.255.0.43 encapsulation mpls
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## the attachment circuit (EFP)
  encapsulation dot1q 210                          ## takes the customer's VLAN 210 frames
  rewrite ingress tag pop 1 symmetric              ## untagged inside the bridge domain; pushed again on the way out
  exit                                             ## leave the service instance and the interface (section 3.6)
 exit
bridge-domain 210                                  ## the switch inside the PE
 member GigabitEthernet2 service-instance 210      ## its port towards the customer
 member vfi VPLS210                                ## its ports towards the other PEs
!
:::

On IOS XR the same is written under `l2vpn` → `bridge group <name>` → `bridge-domain <name>`: the attachment circuit as
`interface <sub-interface>`, and `vfi <name>` → `neighbor <PE> pw-id <VPN ID>` for each other PE. The IOS XRv 9000 of
this track refuses the bridge domain at commit (`VPLS Bridge domains not supported on this platform`).

### 2.5 Reading the outputs, and what goes wrong

- `show l2vpn vfi name <VFI>`: the pseudowires of the VFI, their VC IDs and split horizon.
- `show l2vpn atom vc`: each pseudowire's state (`UP`/`DOWN`).
- `show bridge-domain <BD>`: the members and the learned MAC addresses, with the port each was learned on.

What shows when one thing is wrong:

| Mistake | Pseudowires | What reaches what |
|---|---|---|
| A pseudowire of the mesh missing | All configured ones UP | The two PEs without a pseudowire between them cannot reach each other |
| One PE with a different `vpn id` | That PE's pseudowires DOWN (`LruRnd`: no label from the other end) | That PE's site reaches nobody |
| One EFP without `rewrite` (tag kept) | All UP | That site reaches nobody; its PE never learns the CE's MAC |

The last row is worth a closer look. XE1 and XE2 pop the tag, so frames cross the bridge domains untagged. An EFP that
does not pop sends them to its CE untagged; the CE's VLAN 210 sub-interface does not take them, the CE never answers,
and its MAC never appears in the PE's bridge domain. The pseudowires stay UP throughout, so the bridge domain's MAC
table is the place to look, not the pseudowire state.

:::try
See split horizon at work. Do this after Task M11-6.

1. On XE1, under `l2vpn vfi context VPLS210`, remove `member 10.255.0.43 encapsulation mpls`. On XE3, remove
   `member 10.255.0.41 encapsulation mpls`.
2. On CE1, run `clear arp-cache` and `ping 172.31.210.3`. On XE2, run `show bridge-domain 210`.
3. Put both members back and ping again.

An example result: the ping failed (0 percent), while XE2's bridge domain held CE1's and CE3's MACs, each on its
pseudowire. With the members back, the ping succeeded.
:::

## 3. EVPN's E-LAN

### 3.1 MAC addresses in BGP: route type 2

VPLS has two weak points. Every PE needs a pseudowire to every other, so the LDP sessions grow with the square of the
PEs. And the PEs learn remote MACs only from frames, so a frame for an unknown MAC is flooded to every PE.

EVPN keeps the bridge domains but replaces the pseudowires with BGP routes in the address family `l2vpn evpn`, as
EVPN-VPWS did for E-Lines. A PE still learns its own customers' MACs from frames on its attachment circuits, but then
advertises each of them as a **type 2** route (MAC/IP advertisement), with the label to use for frames to that MAC.
The other PEs install the MAC from BGP: they know where it is before any frame from it has crossed the core.

```console
XE1#show bgp l2vpn evpn
     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.42:200
 *>i  [2][10.255.0.42:200][0][48][AABBCC006A00][0][*]/20
                      10.255.0.42              0    100      0 ?
 *>i  [2][10.255.0.42:200][0][48][AABBCC006A00][32][172.31.200.2]/24
                      10.255.0.42              0    100      0 ?
```

`[2]` is the type. Then come the RD, the Ethernet tag (0), the MAC (48 bits) and, in the second route, the IP address
that goes with the MAC (32 bits). The PE learned the IP from the CE's ARP. The next hop is the PE behind which the MAC
lives.

### 3.2 Broadcasts: route type 3 and ingress replication

A broadcast still has to reach every site. Each PE advertises one **type 3** route (inclusive multicast Ethernet tag,
IMET) per EVPN instance. It says "I am in this E-LAN; for broadcasts, unknown unicast and multicast (BUM), send me a
copy with this label". With **ingress replication**, the PE that receives a broadcast from its customer makes one copy
per PE that sent a type 3 route, and sends each copy as a unicast across the core. The core needs no multicast.

```console
XE1#show bgp l2vpn evpn
Route Distinguisher: 10.255.0.41:200
 *>   [3][10.255.0.41:200][0][32][10.255.0.41]/17
 *>i  [3][10.255.0.41:200][0][32][10.255.0.42]/17
                      10.255.0.42              0    100      0 ?
 *>i  [3][10.255.0.41:200][0][32][10.255.0.43]/17
                      10.255.0.43              0    100      0 ?
```

The last field is the address of the PE that wants the copies. XE1 holds its own and those of XE2 and XE3, imported into
its own EVI's RD.

### 3.3 One frame at a time: CE1 to CE3

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.7, 1]
  P1: [4.1, 1]
  XE3: [5.8, 1]
  CE3: [7.5, 1]
links:
  - [CE1, XE1, "tag 200 | IP"]
  - [XE1, P1, "LDP label | EVPN label | frame"]
  - [P1, XE3, "EVPN label | frame"]
  - [XE3, CE3, "untagged | IP"]
:::

1. CE1's ARP request (broadcast) enters XE1. XE1 learns CE1's MAC on Gi2 and advertises it as a type 2 route. For the
   broadcast it makes a copy for each PE with a type 3 route (XE2, XE3) and sends each with that PE's BUM label.
2. CE3 answers. XE3 learns CE3's MAC on its EFP and advertises it as a type 2 route. It already knows CE1's MAC from
   XE1's type 2 route, so the answer goes to XE1 only.
3. CE1 now sends its ping to CE3's MAC. XE1 knows that MAC from XE3's type 2 route: it puts on the label carried in that
   route, and outside it the LDP label to XE3.
4. P1 removes the transport label (it is the hop before XE3). XE3 finds the bridge domain from the EVPN label and sends
   the frame to CE3, untagged.

Site 3 uses the port without a tag (section 3.6), yet the frame crosses the same E-LAN: inside every bridge domain the
frame is untagged, and each EFP adds or removes what its own site uses.

### 3.4 Configuring EVPN's E-LAN on IOS XE

The configuration has four parts: BGP towards the route reflector, the global EVPN settings, the EVPN instance, and the
bridge domain that joins the attachment circuit to the instance.

:::config fold Catalyst 8000V (IOS XE 17.15) — XE1's part of the EVPN E-LAN (EVI 200)
router bgp 65000
 bgp router-id 10.255.0.41                         ## Loopback0
 no bgp default ipv4-unicast                       ## this PE carries only EVPN in BGP
 neighbor 10.255.0.51 remote-as 65000              ## the route reflector P1, and nobody else
 neighbor 10.255.0.51 update-source Loopback0
 address-family l2vpn evpn
  neighbor 10.255.0.51 activate
  neighbor 10.255.0.51 send-community both         ## the route targets travel as extended communities
!
l2vpn evpn
 replication-type ingress                          ## BUM: one unicast copy per PE (no multicast in the core)
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## EVI 200; RD and RT automatic (10.255.0.41:200, 65000:200)
!
interface GigabitEthernet2
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
  exit                                             ## leave the service instance and the interface (section 3.6)
 exit
bridge-domain 200
 member GigabitEthernet2 service-instance 200
 member evpn-instance 200                          ## joins the bridge domain to the EVI (instead of a VFI)
!
:::

`vlan-based` means one bridge domain per EVI, the usual form. The route reflector needs nothing per EVI: it reflects
every `l2vpn evpn` route of its clients (in this lab P1 is an IOS XE router with the clients already configured).

On IOS XR, the bridge domain gets `evi <EVI>` instead of a VFI (`l2vpn` → `bridge group` → `bridge-domain` → `evi 200`),
the EVI itself goes under `evpn` → `evi 200` (with `advertise-mac`), and BGP has `address-family l2vpn evpn` globally and
under the neighbor, as in EVPN-VPWS.

### 3.5 Reading the outputs

`show l2vpn evpn evi <EVI> detail` is the overview: the automatic RD and route targets, the state, the replication type,
and per other PE the routes received.

```console
XE1#show l2vpn evpn evi 200 detail
EVPN instance:       200 (VLAN Based)
  RD:                10.255.0.41:200 (auto)
  Import-RTs:        65000:200
  Export-RTs:        65000:200
  State:             Established
  Replication Type:  Ingress (global)
  Encapsulation:     mpls
  Bridge Domain:     200
    BUM Label:       23
    Per-BD Label:    24
    State:           Established
    Pseudoports:
      GigabitEthernet2 service instance 200
        Routes: 1 MAC, 1 MAC/IP
    Peers:
      10.255.0.42
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
      10.255.0.43
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
```

`show l2vpn evpn mac` lists the MACs of the EVI with where they are: the local one on the EFP (`Gi2:200`), the remote
ones behind the PE that advertised them.

```console
XE1#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
-------------- ----- ----- ------------------------ ---------- ---------------
aabb.cc00.6900 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc00.6a00 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.6b00 200   200   0000.0000.0000.0000.0000 0          10.255.0.43
```

The ESI column is 0 because each of these sites is attached to one PE only. The next page fills it in.

### 3.6 What goes wrong

- **No replication type.** Without `replication-type ingress` under `l2vpn evpn`, the EVI stays `State: Incomplete` with
  `Replication Type: Not set (global)` and `EVI Down, BD Up`. Nothing passes at all, not even between two PEs that
  have BGP up: the PE does not take part in the E-LAN until it knows how to send BUM. The IOS XE guide's examples
  always set it, and its EVPN chapter states that only ingress replication is supported for EVPN over MPLS.
- **A site without a tag.** At site 3 the customer sends this E-LAN untagged. The EFP there is `encapsulation untagged`,
  with nothing to pop. An EFP with `encapsulation dot1q 200` at XE3 matched nothing, and site 3 reached nobody (0
  percent). The other services on the same port (VLANs 210 and 130) keep their own tagged EFPs.
- **Pasting a configuration.** IOS XE also has a `bridge-domain` command inside `service instance` (the older way of
  putting an EFP in a bridge domain). Pasted right after a service instance with only `!` in between, `bridge-domain 200`
  went to the EFP, and the `member` lines that followed were rejected (`Invalid input`), so the bridge domain never
  joined the EVI. Leave the service instance and the interface with `exit` first, as in the examples on these pages.
- **BGP towards the route reflector only.** A session between two PEs would also carry the routes, but then every new PE
  needs a session to every other, which is what EVPN set out to avoid.

:::try
See how much the replication type matters. Do this after Task M11-7.

1. On XE3, under `l2vpn evpn`, remove `replication-type ingress`.
2. On XE3, run `show l2vpn evpn evi 200 detail`. On CE1, run `clear arp-cache` and `ping 172.31.200.3`.
3. Put the line back, wait half a minute, and run the same commands again.

An example result: XE3's EVI went to `Incomplete Pending` with `Replication Type: Not set (global)` and `EVI Down,
BD Up`, and CE1's ping to site 3 failed (0 percent) while site 2 still answered. With the line back, the EVI was
`Established` again and the ping succeeded.
:::

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `l2vpn vfi context <name>` → `vpn id <n>`, `member <PE> encapsulation mpls` | `l2vpn` → `bridge group` → `bridge-domain` → `vfi <name>` → `neighbor <PE> pw-id <n>` |
| `bridge-domain <n>` → `member <IF> service-instance <n>` | `bridge-domain <name>` → `interface <sub-interface>` |
| `service instance <n> ethernet` (EFP) | `interface <sub-interface> l2transport` |
| `l2vpn evpn instance <EVI> vlan-based` + `member evpn-instance <EVI>` | `evpn` → `evi <EVI>` + `bridge-domain` → `evi <EVI>` |
| `l2vpn evpn` → `replication-type ingress` | — (the guide's EVPN examples have no such line) |
| `show l2vpn vfi`, `show bridge-domain <n>` | `show l2vpn bridge-domain [detail]` |
| `show l2vpn evpn evi <EVI> detail`, `show l2vpn evpn mac` | `show evpn evi vpn-id <EVI> detail`, `show evpn evi vpn-id <EVI> mac` |

## Practice

In lab **XRT-12**, work through tasks M11-6 and M11-7. Then go on to the next page, *EVPN multihoming*.

<p class="tolab"><a href="/_learn?id=XRT-12">Open lab XRT-12 in the workspace</a> — <a href="b8-m11-practice-4.html">Tasks</a></p>

:::note
The outputs on this page come from Catalyst 8000V 17.15.1a (XE1 to XE3) and IOS XE 17.15 on IOL (P1, the CEs, SW1).
Sources: MPLS Configuration Guide, Cisco IOS XE 17.x (Configuring Virtual Private LAN Services; EVPN Single-Homing; EVPN
over MPLS with IRB). The EVPN chapters name the ASR 1000; this lab ran them on the Catalyst 8000V. L2VPN and Ethernet
Services Configuration Guide for the ASR 9000, IOS XR 25.x (Implementing Multipoint Layer 2 Services) and 7.10.x (EVPN
Features). RFC 4762 (VPLS with LDP, full mesh and split
horizon), RFC 7432 (EVPN). All checked in November 2026. The outputs, the behaviour without a replication type, the
untagged site and each mistake in section 2.5 come from measurements in lab XRT-12 (Catalyst 8000V 17.15.1a).
:::
