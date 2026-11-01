# M11 — E-Line and pseudowires

This unit is about **L2VPN**: services that carry a customer's Ethernet frames, as they are, to the far side of the core,
without the provider taking part in the customer's routing. It covers items 4.2 (L2VPN and carrier Ethernet) and
4.1.a (EVPN) of the CCNP Service Provider blueprint. The unit has three pages, a supplement of three more pages, and an
appendix.

| Page | Contents | Tasks |
|---|---|---|
| This page | What L2VPN is good for, how frames are wrapped in labels, the LDP pseudowire | M11-1, M11-2 |
| EVPN-VPWS | Building the pseudowire with BGP | M11-3, M11-4 |
| Q-in-Q | Carrying a customer's VLANs together | M11-5 |
| Supplement: E-LAN | Many sites in one LAN: VPLS and EVPN (lab XRT-12, Catalyst 8000V) | M11-6, M11-7 |
| Supplement: EVPN multihoming | One site on two PEs, both links in use | M11-8 |
| Supplement: Ethernet OAM | CFM and Y.1731 on an E-Line | M11-9 |
| Appendix | E-Tree, G.8032, 802.1ah | — |

The lab is XRT-11. It continues from lab XRT-10: the same square core, the same VPN customers, and XR01 and XR02 with the
work of the M10 tasks done. A new provider edge (PE), XR03, has joined beyond RT01 and serves customer B's site 3. The
outputs come from IOS XRv 9000 26.1.1 (XR01, XR03), IOS XRd 26.1.1 (XR02) and IOS XE 17.15 on IOL (the other routers).

:::topo
nodes:
  CEA1: {at: [-0.1, 1.1], label: "CEA1 (A, site 1)"}
  CEB1: {at: [-0.1, 2.3], label: "CEB1 (B, site 1)"}
  XR01: {at: [1.6, 1.7], label: "XR01 (PE)"}
  RT01: {at: [3.2, 1.0], label: "RT01 (P)"}
  RT03: {at: [3.2, 2.4], label: "RT03 (P)"}
  XR02: {at: [3.2, 3.5], label: "XR02 (RR, PCE)"}
  RT02: {at: [4.8, 1.7], label: "RT02 (PE)"}
  XR03: {at: [4.8, 0.2], label: "XR03 (PE, new)"}
  CEA2: {at: [6.5, 1.3], label: "CEA2 (A, site 2)"}
  CEB2: {at: [6.5, 2.2], label: "CEB2 (B, site 2)"}
  CEB3: {at: [6.5, 0.2], label: "CEB3 (B, site 3)"}
links:
  - [CEA1, XR01, "L3VPN + VLAN 100"]
  - [CEB1, XR01, "L3VPN + VLANs"]
  - [XR01, RT01, "PRIMARY 10"]
  - [XR01, RT03, "BACKUP 100"]
  - [RT01, RT02, "CORE-A 10"]
  - [RT03, RT02, "CORE-B 100"]
  - [RT03, XR02, "RR-LINK 10"]
  - [RT01, XR03, "CORE-C 10"]
  - [RT02, CEA2, "L3VPN + VLAN 200"]
  - [RT02, CEB2, "L3VPN + VLANs"]
  - [XR03, CEB3, "VLANs"]
frames:
  - {label: "AS 65000 (IS-IS CORE, SR-MPLS)", nodes: [XR01, RT01, RT03, RT02, XR02, XR03]}
:::

The numbers on the core links are IS-IS metrics. Sites 1 and 2 of customers A and B keep their Layer 3 VPN from M9
untagged, and add L2VPN on tagged sub-interfaces of the same ports. Site 3 has L2VPN only.

## 1. What it is good for

### 1.1 When an L3VPN is not enough

With the L3VPN of M9, the provider takes part in the customer's routing. The PE speaks BGP with the customer, puts the
customer's routes in a VRF and advertises them across the core. To the customer, the provider looks like one big router.

Some customers do not want that. They want their own routers to speak OSPF or IS-IS with each other directly, they do
not want to show their routing design to the provider, they want to carry frames that are not IP, or they want to join
their sites in the same VLAN. What they want is a service that behaves like one Ethernet cable between two sites.

### 1.2 Before

Providers used to sell leased lines between sites, or virtual circuits of Frame Relay or ATM. Both meant a network and
equipment of their own, apart from the core.

With Ethernet came the metro Ethernet switch and one VLAN per customer. But there are only 4094 VLAN numbers, and the
whole provider network becomes one spanning-tree domain. The bigger the network, the shorter the numbers run and the
wider a failure reaches.

### 1.3 The MPLS answer: wrap the frame in labels

An MPLS core carries any labelled packet, whatever is inside. In M9, the labels went on IP packets. In the same way, if
the PE wraps a customer's whole Ethernet frame in labels, the core carries it to the far PE without knowing anything
about it. This wrapped path is a **pseudowire** (PW).

There are no VLANs and no spanning tree in the core. A customer's VLAN number means something only inside its port, so
two customers may use the same numbers. The core labels are those of M10's segment routing, unchanged.

### 1.4 The service types

Ethernet services come in types by how many sites they join (MEF definitions).

| Type | Joins | Built with, for example | This lab's XR |
|---|---|---|---|
| E-Line | Two sites, one to one | Pseudowire (LDP), EVPN-VPWS | Practised |
| E-LAN | Many sites, all to all | VPLS, EVPN E-LAN | Not on this XR (supplement, on Catalyst 8000V) |
| E-Tree | Roots and leaves; leaves do not reach each other | EVPN E-Tree | Appendix only |
| E-Access | A customer and the boundary to another operator's network | A kind of E-Line | Appendix only |

The IETF name for what builds an E-Line is **VPWS** (Virtual Private Wire Service). The IOS XRv 9000 of this lab runs
only VPWS among the L2VPN services: `show l2vpn capability` shows `VPLS allowed: N` and `VPWS allowed: Y`, and a commit of
a bridge domain is rejected. The supplement covers E-LAN with Catalyst 8000V PEs (lab XRT-12), and the appendix the
others.

## 2. How it works: wrapping frames in labels

### 2.1 Attachment circuits and pseudowires

An E-Line is made of three parts.

- **Attachment circuit** (AC): the section between the customer's CE and the PE. Here it is a sub-interface that picks
  the frames of one VLAN on the port.
- **Pseudowire**: the section between PE and PE that carries the frames through the core. The two PEs agree that they
  are on the same pseudowire by the same number, the **PW ID** (also called the VC ID).
- **Cross-connect**: joins the AC and the pseudowire inside the PE. A frame from the AC goes to the pseudowire, and a
  frame from the pseudowire goes out of the AC. MAC addresses are not looked at.

In customer A's E-Line (Task M11-1), XR01's AC is CEA1's VLAN 100, RT02's AC is CEA2's VLAN 200, and the pseudowire's
PW ID is 100.

### 2.2 One hop at a time: CEA1 to CEA2

Follow a frame that CEA1 sends on VLAN 100 until it reaches CEA2. The label values were measured in one build of the lab
(the pseudowire labels change from build to build).

:::topo
nodes:
  CEA1: [0, 1]
  XR01: [1.5, 1]
  RT01: [3, 1]
  RT02: [4.5, 1]
  CEA2: [6, 1]
links:
  - [CEA1, XR01, "tag 100 | IP"]
  - [XR01, RT01, "16012 | 16 | frame"]
  - [RT01, RT02, "16 | frame"]
  - [RT02, CEA2, "tag 200 | IP"]
:::

1. XR01 picks the VLAN 100 frame on the AC and removes the tag.
2. It puts on the pseudowire label **16**: the value RT02 told XR01 to use for frames of this pseudowire.
3. Outside it, it puts the transport label to RT02, **16012** (RT02's prefix SID, M10), and sends it on PRIMARY.
4. RT01 sees 16012 and sends it to RT02. It is the hop before RT02, so it removes 16012.
5. RT02 sees 16 and knows the pseudowire towards CEA2. It removes the label, puts on the AC's VLAN 200 tag and sends
   the frame to CEA2.

Note that the VLAN numbers at the two ends differ: 100 and 200. A VLAN number is only a marker on the link between the
CE and the PE, and it never appears in the core. What ties the two sites together is the PW ID (100). XR01 removes the
tag on the way in (step 1) and RT02 puts on its own tag on the way out (step 5), so the numbers at the two ends may
differ or be the same (2.4).

In the other direction, RT02 puts on `{16001 24031}`: 16001 is the transport to XR01, and 24031 is the pseudowire label
XR01 told RT02. The receiving side chooses the pseudowire label, as it does with a VPN label in an L3VPN.

### 2.3 Handing out pseudowire labels: targeted LDP

The two PEs exchange the pseudowire labels with LDP. They are not neighbours, so LDP sends its hellos straight to the
other's loopback instead of out of a link. This is **targeted LDP**. What they exchange (FEC 128 of RFC 8077):

- **PW ID**: the two ends pair up only if it is the same.
- **Label**: the pseudowire label the other end should put on.
- **Interface parameters**: the AC's **MTU**, how the frame is carried (the **PW type**), and whether a **control word**
  is used.

IOS XR 26.1.1 brought up a targeted session to the pseudowire's other end with no `mpls ldp` configuration at all. The
lab's XR01 has had no LDP since M10-2. Even so, when the pseudowire was configured, the session to RT02 came up, and when
the pseudowire was removed, the session went away. `show mpls ldp summary` shows `Interfaces: 0 LDP configured`. LDP does
not run on the core links, and the transport labels stay those of SR.

### 2.4 Tags: rewrite and the PW type

The AC sub-interface sets which VLAN's frames it picks (`encapsulation`) and what it does with their tags (`rewrite`).
By default, IOS XR **keeps** the tags.

- `rewrite ingress tag pop 1 symmetric`: removes the outer tag on the way in and puts the same tag back on the way out.
  Frames cross the pseudowire without a tag, so the two ends may use different VLANs.
- `rewrite ingress tag translate 1-to-1 dot1q <VLAN> symmetric`: changes the tag's number.
- `rewrite ingress tag push dot1q <VLAN> symmetric`: adds one tag.

`symmetric` means the opposite operation on the way out; it is the only mode IOS XR offers.

The **PW type** sets the form of the frames in the pseudowire. IOS XR's default is type 5 (Ethernet), which carries the
frame as it is. With `transport-mode vlan`, it is type 4 (Ethernet VLAN), which assumes a VLAN tag on the frame. A
pseudowire whose ends have different PW types does not come up: between two XRs it went down with `Error: PW type
mismatched`. IOS XE follows the other end (autosense), so with IOS XE at the other end this mismatch did not show.

### 2.5 MTU: three numbers

In an E-Line, the MTU counts in three places.

- **The AC MTU**: the two PEs tell each other in LDP, and **if it differs, the pseudowire does not come up**. IOS XR's AC
  MTU is the parent port's MTU minus the Ethernet header (14 bytes), plus 4 bytes for each tag kept. With the port at its
  default of 1514, an AC with `pop 1` has 1500, and an AC that keeps its tag has 1504. IOS XE does not count the Layer 2
  header and signals 1500.
- **The port MTU**: raising the parent port's MTU raises the MTU of every AC on the port. A sub-interface `mtu` cannot
  exceed its parent: in the lab, with `mtu 9018` on the sub-interface, the AC stayed at 1500.
- **The core MTU**: the wrapped frame is the customer's packet plus an Ethernet header (14) and the labels (4 each), and
  the core does not fragment it. The lab's core is at 1500, so with the DF bit set, IP packets got through up to 1478
  bytes (1478 + 14 + 8 = 1500). Real networks run the core at a larger MTU than the customer's. IOL cannot change the
  MTU of its Ethernet interfaces, so this lab does not go into it.

## 3. Building an E-Line on IOS XR

### 3.1 Where the configuration goes

An E-Line is written in two places: the AC sub-interface, and the cross-connect under `l2vpn`.

:::config fold XR01 (IOS XR) — an E-Line on an LDP pseudowire
interface GigabitEthernet0/0/0/2.100 l2transport   ## l2transport= used as an AC, not a Layer 3 interface; it cannot have an IP address
 encapsulation dot1q 100                           ## pick the frames of VLAN 100 on this port
 rewrite ingress tag pop 1 symmetric               ## remove the tag on the way in, put it back on the way out; the pseudowire carries untagged frames
!
l2vpn
 xconnect group CUST-A                             ## a name for a group of cross-connects (any name)
  p2p A-100                                        ## one E-Line (any name)
   interface GigabitEthernet0/0/0/2.100            ## one end: the AC
   neighbor ipv4 10.255.0.12 pw-id 100             ## the other end: the pseudowire to RT02; the PW ID is the same at both ends
   !
  !
 !
!
:::

There is no `mpls ldp` here. As in section 2.3, IOS XR brings up the targeted session to the pseudowire's other end on
its own.

:::config RT02 (IOS XE) — customer A's E-Line, from the lab's fixed configuration
interface Ethernet0/2.200                          ## the sub-interface that picks CEA2's VLAN 200 (the parent port is the L3VPN)
 encapsulation dot1Q 200
 xconnect 10.255.0.1 100 encapsulation mpls        ## the pseudowire to XR01 (PW ID 100); a sub-interface xconnect carries the frame without its tag
!
:::

IOS XE also has a newer form with an EVC (`service instance`) and `l2vpn xconnect context`. The lab's RT02 uses the older
form, an `xconnect` on the sub-interface. Either way, it joined XR with PW type 5.

### 3.2 Reading the state

`show l2vpn xconnect` shows one line per E-Line. The E-Line is UP when both the AC (Segment 1) and the pseudowire
(Segment 2) are UP.

```console
RP/0/RP0/CPU0:XR01#show l2vpn xconnect
XConnect                   Segment 1                       Segment 2
Group      Name       ST   Description            ST       Description            ST
------------------------   -----------------------------   -----------------------------
CUST-A     A-100      UP   Gi0/0/0/2.100          UP       10.255.0.12     100    UP
```

The detail (`show l2vpn xconnect detail`) lists what the two ends told each other, in the Local and Remote columns. When
the pseudowire does not come up, look for the row that differs.

```console
  PW: neighbor 10.255.0.12, PW ID 100, state is up ( established )
    PW type Ethernet, control word disabled, interworking none
      MPLS         Local                          Remote
      ------------ ------------------------------ -----------------------------
      Label        24031                          16
      MTU          1500                           1500
      Control word disabled                       disabled
      PW type      Ethernet                       Ethernet
```

On RT02, `show l2vpn atom vc` and `show l2vpn atom vc vcid 100 detail` tell the same. The detail's `imposed label stack
{16001 24031}` is the two labels RT02 puts on (section 2.2).

### 3.3 Reading a pseudowire that stays down

When a pseudowire does not come up, IOS XR's detail ends with an `Error:` line. The mismatches made in the lab, and what
they showed:

| Mismatch | XR shows (XR at the other end) | With IOS XE at the other end |
|---|---|---|
| AC MTU (port MTU, an AC that forgot to pop its tag) | `Error: MTU mismatched` | IOS XE also shows `Last error: Pseudowire MTU mismatch with peer` |
| PW type (`transport-mode vlan` on one side only) | `Error: PW type mismatched` | IOS XE follows, and it comes up |
| Control word (on one side only) | `Error: illegal control word` | IOS XE follows, and it comes up |
| PW ID | The other end's label never arrives, and the `Remote` column stays empty | The same |

The same `MTU mismatched` can have more than one cause. An AC on a port with a raised MTU and an AC that forgot to pop
its tag both show it. The number in the MTU row (9000 or 1504) tells which.

:::try
See how an AC that forgot to pop its tag stops the pseudowire. Do this after Task M11-1.

1. On XR01, remove `rewrite ingress tag pop 1 symmetric` under `interface GigabitEthernet0/0/0/2.100 l2transport` and commit.
2. Run `show l2vpn xconnect detail` on XR01 and `show l2vpn atom vc vcid 100 detail` on RT02, and `ping 172.31.10.2` from CEA1.
3. Put the rewrite back, commit, and run the same commands again.

Measured in the lab: XR01's AC MTU became 1504, and the pseudowire went down with `Error: MTU mismatched` (RT02:
`Last error: Pseudowire MTU mismatch with peer`, MTU rows 1500 and 1504). The ping failed. With the rewrite back, it came
up within 30 seconds.
:::

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `encapsulation dot1Q <VLAN>` + `xconnect <peer> <VC ID> encapsulation mpls` on a sub-interface | `interface … l2transport` + `l2vpn` → `xconnect group` → `p2p` → `interface` and `neighbor ipv4 <peer> pw-id <ID>` |
| `service instance <n> ethernet` → `rewrite ingress tag pop 1 symmetric` | `rewrite ingress tag pop 1 symmetric` on the `l2transport` sub-interface |
| `show l2vpn atom vc [vcid <ID> detail]` | `show l2vpn xconnect [detail]` |
| `show mpls l2transport vc` (older form) | `show l2vpn xconnect` |
| `show mpls ldp neighbor` | `show mpls ldp neighbor brief`, `show mpls ldp discovery` |

## Practice

Go to lab **XRT-11** and work through tasks M11-1 and M11-2. XR01 and XR03 are IOS XRv 9000, so the lab takes about
15 minutes to build. Then go on to the next page, *EVPN-VPWS*.

<p class="tolab"><a href="/_learn?id=XRT-11">Open lab XRT-11 in the workspace</a> — <a href="b1-m11-practice.html">Tasks</a></p>

:::note
Sources: L2VPN and Ethernet Services Configuration Guide for the ASR 9000, IOS XR 25.x (2025; point-to-point Layer 2
services, the carrier Ethernet model) and its command reference. Release notes of the IOS XRv 9000, 24.1.1 (the L2VPN it
supports is VPWS). IOS XE 17 MPLS Configuration Guide (Any Transport over MPLS, L2VPN Protocol-Based CLIs). TAC documents
"MTU Behavior on Cisco IOS XR and Cisco IOS Routers" (116350) and "Understand IOS XR L2VPN Services and Features"
(116453). RFC 8077, 4448. All checked in November 2026. The following come from measurements in lab XRT-11 and its PoC:
the labels, the targeted session without LDP configuration, the AC MTU values, the sub-interface MTU having no effect,
the size that gets through with DF set, and what each mismatch shows.
:::
