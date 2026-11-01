# M11 — EVPN-VPWS

On the previous page, LDP built the pseudowire. This page builds the same E-Line with **BGP**. EVPN (Ethernet VPN) is a
family of ways to build Layer 2 services with BGP, and its point-to-point member is **EVPN-VPWS**. The lab is still
XRT-11; tasks M11-3 and M11-4 belong to this page.

## 1. What it is good for

### 1.1 The trouble with LDP pseudowires

With LDP pseudowires, every pair of PEs that share a pseudowire needs a targeted LDP session. The more PEs an E-Line
reaches, the more sessions there are. And the provider already runs BGP and route reflectors for its L3VPNs. For Layer 2
services alone, it keeps another control protocol's sessions between all those pairs.

An LDP pseudowire is also a single wire. Attaching a customer site to two PEs and using both at once (multihoming) is
not possible with it alone.

### 1.2 The EVPN answer: carry it with the L3VPN's tools

EVPN advertises what a pseudowire needs as BGP routes, in the address family `l2vpn evpn`. The tools of M9's L3VPN carry
over as they are: RDs and route targets, route reflectors, policies. A PE needs sessions with the route reflectors only,
not one per pair of PEs.

The EVPN family also has E-LAN and multihoming (both in the supplement) and E-Tree (appendix). EVPN-VPWS is its simplest
member, the E-Line. Of the family, this lab's XR handles EVPN-VPWS.

## 2. How it works

### 2.1 The EVI and the AC identifiers

An EVPN-VPWS E-Line is set by two things.

- **EVI** (EVPN instance): a number per E-Line, as a VRF is for an L3VPN. IOS XR makes the RD and route target from the
  EVI by itself: the RD is "router ID:EVI" and the route target is "AS number:EVI".
- **AC identifiers**: a number for each end of the E-Line. Each PE sets "my end is `source`, the other end is `target`".
  The E-Line joins when the other end's `source` matches this end's `target`.

In Task M11-3, the EVI is 400, the identifier of site 1's end (XR01) is 1, and site 3's end (XR03) is 3. XR01 sets
`target 3 source 1`, and XR03 sets `target 1 source 3`.

### 2.2 The route it carries: type 1

For its end, each PE advertises one EVPN **type 1** route (Ethernet auto-discovery, per EVI). The route carries:

- The RD and the Ethernet segment identifier (ESI). When a site is attached to one PE only, the ESI is 0.
- **Ethernet tag**: the AC identifier (`source`) goes here.
- **Label**: the label the other end should put on, like an LDP pseudowire's label.
- The route target, and the Layer 2 attributes extended community (`0x604`).

```console
RP/0/RP0/CPU0:XR03#show bgp l2vpn evpn
Route Distinguisher: 10.255.0.1:400
*>i[1][0000.0000.0000.0000.0000][1]/120
Route Distinguisher: 10.255.0.3:400 (default for vrf VPWS:400)
*>i[1][0000.0000.0000.0000.0000][1]/120
*> [1][0000.0000.0000.0000.0000][3]/120
```

`[1]` is the type, the next 0 is the ESI, and the last `[1]` or `[3]` is the Ethernet tag (the AC identifier). XR03 has
received XR01's route (tag 1) and imported it under its own EVI's RD.

### 2.3 One hop at a time: CEB1 to CEB3

Follow a frame that CEB1 sends on VLAN 400. The label values were measured in one build of the lab.

:::topo
nodes:
  CEB1: [0, 1]
  XR01: [1.5, 1]
  RT01: [3.2, 1]
  XR03: [4.7, 1]
  CEB3: [6.2, 1]
links:
  - [CEB1, XR01, "tag 400 | IP"]
  - [XR01, RT01, "16003 | 24004 | frame"]
  - [RT01, XR03, "24004 | frame"]
  - [XR03, CEB3, "tag 40 | IP"]
:::

1. XR01 picks the VLAN 400 frame on the AC and removes the tag.
2. It puts on label **24004**, carried in XR03's type 1 route, and outside it the transport label to XR03, **16003**
   (XR03's prefix SID).
3. RT01 sees 16003, sends the frame to XR03 and, as the hop before it, removes 16003.
4. XR03 sees 24004 and knows the E-Line of EVI 400. It removes the label, puts on the VLAN 40 tag and sends the frame to
   CEB3.

The data looks the same as on an LDP pseudowire. Only the way the labels are handed out differs.

### 2.4 The route reflector carries it

The PEs exchange `l2vpn evpn` routes with the route reflector XR02 only. XR02 has been the VPNv4 route reflector since
M9; adding the `l2vpn evpn` address family to the same sessions makes it reflect EVPN routes too. XR02 is IOS XRd and
takes no part in forwarding, so XRd can do the job.

With the new PE, XR03, the routes took about a minute to settle in the lab after the session came up. Right after the
session comes up, both ends of the E-Line still show `None`.

### 2.5 MTU and the control word

For EVPN-VPWS, IOS XR does not compare MTUs by default. The detail shows `Ignore MTU mismatch: Enabled` and `Transmit MTU
zero: Enabled`, and the other end is told an MTU of 0. So the `MTU mismatched` of the LDP pseudowire does not happen with
EVPN-VPWS. An AC that forgot to pop its tag leaves the E-Line UP and only makes the frame forms disagree (section 3.3). To
compare MTUs, set `transmit-l2-mtu` and `enforce-mtu-match` under the EVI.

## 3. Building EVPN-VPWS on IOS XR

### 3.1 Where the configuration goes

EVPN-VPWS is written in three places: BGP's `l2vpn evpn`, the AC sub-interface, and the cross-connect under `l2vpn`.

:::config fold XR01 (IOS XR) — an EVPN-VPWS E-Line
router bgp 65000
 address-family l2vpn evpn                         ## use the EVPN address family in BGP as a whole
 !
 neighbor 10.255.0.21                              ## the route reflector XR02 (the VPNv4 session since M9)
  address-family l2vpn evpn                        ## exchange EVPN routes on the same session
  !
 !
!
interface GigabitEthernet0/0/0/3.400 l2transport
 encapsulation dot1q 400
 rewrite ingress tag pop 1 symmetric               ## carried untagged, so it may differ from the other end's VLAN (40)
!
l2vpn
 xconnect group CUST-B
  p2p B-400
   interface GigabitEthernet0/0/0/3.400
   neighbor evpn evi 400 target 3 source 1          ## EVI 400; this end is 1, the other end is 3
   !
  !
 !
!
:::

XR03 runs BGP for the first time, so `router bgp 65000` needs `bgp router-id 10.255.0.3` and the neighbor XR02
(`remote-as`, `update-source Loopback0`). Its AC and cross-connect pair with XR01 by `target 1 source 3`.

:::config fold XR02 (IOS XR) — adding EVPN to the route reflector
router bgp 65000
 address-family l2vpn evpn                         ## the RR uses EVPN in BGP as a whole too
 !
 neighbor 10.255.0.1
  address-family l2vpn evpn
   route-reflector-client                          ## XR01 as an EVPN client
  !
 !
 neighbor 10.255.0.3                               ## the new PE, XR03
  remote-as 65000
  update-source Loopback0
  address-family l2vpn evpn
   route-reflector-client
  !
 !
!
:::

On IOS XR, an EVI works with the automatic RD and route target without anything under `evpn`. To fix the route target,
write `route-target import` and `export` under `evpn` → `evi 400` → `bgp`.

### 3.2 Reading the state

Segment 2 of `show l2vpn xconnect` shows `EVPN <EVI>,<target>,<other PE>`.

```console
RP/0/RP0/CPU0:XR01#show l2vpn xconnect
CUST-B     B-400      UP   Gi0/0/0/3.400          UP       EVPN 400,3,10.255.0.3  UP
```

While the other end's route has not arrived, the other PE's field is `None`. In the detail (`show l2vpn xconnect
detail`), the labels (Local and Remote) follow `EVPN: neighbor 10.255.0.3, PW ID: evi 400, ac-id 3, state is up
( established )`. `show evpn evi vpn-id 400 detail` shows the automatic RD and route target, the control word, and how
the MTU is handled.

### 3.3 Down, or up but not passing traffic

The mismatches made in the lab, and what they showed:

| Mismatch | This end | The other end | Traffic |
|---|---|---|---|
| This end's `target` is wrong (the other end's identifier mixed up) | DN, `neighbor None … local ready` | **UP** | Does not pass |
| Different route targets | DN | DN | Does not pass |
| One AC does not pop its tag | UP | UP | Does not pass |
| No EVPN on the route reflector | DN, `None` | DN, `None` | Does not pass |

The first row shows lopsided states. The other end receives this end's route (tag = this end's `source`), which matches
its own `target`, so it is UP. This end receives no route that matches its `target`, so it is DN. Do not decide from one
end alone that "the other side is UP, so the other side is right".

In the third row, the E-Line stays UP because the MTU is not compared (section 2.5). Frames from the end that popped
the tag arrive untagged, and the end that did not pop sends them to the CE untagged, so the CE's sub-interface does not
take them. In the other direction, a second tag lands on top of the tagged frame.

:::try
See what an AC that does not pop its tag looks like. Do this after Task M11-4.

1. On XR03, remove the rewrite under `interface GigabitEthernet0/0/0/1.40 l2transport` and commit.
2. Run `show l2vpn xconnect` on XR01 and XR03, and `ping 172.31.40.3` on CEB1.
3. Put the rewrite back, commit, and run the same commands again.

Measured in the lab: both ends stayed UP, and the ping failed (0 percent).
With the rewrite back, the ping succeeded (100 percent).
:::

### 3.4 With IOS XE at the other end

In this lab's environment, EVPN-VPWS between IOS XR and IOS XE (both IOL and the Catalyst 8000V) came up in the control
plane at both ends, but IOS XE dropped the frames going from IOS XR to IOS XE. IOS XE to IOS XE and IOS XR to IOS XR
worked. So this lab builds EVPN-VPWS between XRs only. Cisco's configuration guides for IOS XE routers have no EVPN-VPWS
chapter (the ASR 920 has one).

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `l2vpn evpn instance <EVI> point-to-point` → `vpws context <name>` → `service target <n> source <n>` | `l2vpn` → `xconnect group` → `p2p` → `neighbor evpn evi <EVI> target <n> source <n>` |
| `member <IF> service-instance <n>` | `interface <sub-interface>` under `p2p` |
| `show l2vpn evpn vpws vc id <EVI> detail` | `show l2vpn xconnect [detail]` |
| `show bgp l2vpn evpn` | `show bgp l2vpn evpn` |
| `address-family l2vpn evpn` → `neighbor … activate`, `send-community both` | `address-family l2vpn evpn` (in BGP as a whole and under the neighbor) |

## Practice

In lab **XRT-11**, work through tasks M11-3 and M11-4. Then go on to the next page, *Q-in-Q*.

<p class="tolab"><a href="/_learn?id=XRT-11">Open lab XRT-11 in the workspace</a> — <a href="b3-m11-practice-2.html">Tasks</a></p>

:::note
Sources: L2VPN and Ethernet Services Configuration Guide for the ASR 9000, IOS XR 25.x (2025; EVPN Virtual Private Wire
Service, and its restriction that from 7.3.2 an MTU of 0 is advertised and mismatches are ignored). IOS XE MPLS L2VPNs
Configuration Guide (ASR 920, EVPN VPWS). RFC 7432, 8214. All checked in November 2026. The following come from
measurements in lab XRT-11 and its PoC: the routes and labels, the automatic RD and route target, the time the routes
took to settle after the session came up, what each mismatch showed, and the results with IOS XE.
:::
