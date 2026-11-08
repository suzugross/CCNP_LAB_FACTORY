# M11 supplement — Ethernet OAM

The previous pages built services. This page watches one. E-Line 130 joins site 1 and site 3 with an LDP pseudowire
between XE1 and XE3, and it is in place. The provider wants to know when it breaks, and how long frames take to cross
it, without relying on the customer to complain. The lab is still XRT-12; Task M11-9 belongs to this page.

:::topo
nodes:
  CE1: {at: [0, 1], label: "CE1 (site 1)"}
  XE1: {at: [1.8, 1], label: "XE1 (MEP 1)"}
  P1: {at: [3.6, 1], label: "P1"}
  XE3: {at: [5.4, 1], label: "XE3 (MEP 3)"}
  CE3: {at: [7.2, 1], label: "CE3 (site 3)"}
links:
  - [CE1, XE1, "VLAN 130"]
  - [XE1, P1, "pseudowire 130"]
  - [P1, XE3, "pseudowire 130"]
  - [XE3, CE3, "VLAN 130"]
frames:
  - {label: "maintenance domain PROV (level 4)", nodes: [XE1, P1, XE3]}
:::

## 1. What it is good for

### 1.1 A break that nobody notices

Suppose the link between XE3 and P1 starts dropping every packet while both ports stay up: a fault inside a carrier's
transmission system, or a congested or misprogrammed device on the way. No interface goes down, so nothing reacts at
once. Set such a fault between XE3 and P1 (a CML link condition of 100 % loss), and ten seconds later IS-IS and LDP on
P1 still show their neighbours up, and the pseudowire is still UP at both ends. The customer's traffic, meanwhile, is
gone.

### 1.2 Before: wait for the routing protocols, or for the customer

Without anything else, the provider finds out in one of two ways:

- **The control protocols time out.** IS-IS (hold time 30 s by default) or LDP gives up on its neighbour, and the
  pseudowire goes down. That takes tens of seconds, and it only covers the faults that the control traffic also sees.
- **The customer calls.** The CEs can ping across the E-Line, but the CEs are the customer's.

The PE cannot simply ping across the E-Line either: the attachment circuit has no IP address, and the frames inside are
the customer's.

### 1.3 The answer: CFM on the service itself

**CFM** (Connectivity Fault Management, IEEE 802.1ag) puts monitoring points on the Ethernet service itself. A
**MEP** (maintenance end point) at each end of the E-Line sends small Ethernet frames, **continuity check messages**
(CCMs), through the same path as the customer's frames, and expects the other end's. When they stop, the MEP knows that
the service is broken, whatever the cause. CFM also offers a loopback (the Ethernet ping) and a linktrace (the Ethernet
traceroute). ITU-T **Y.1731** adds measurements on the same MEPs: frame delay, delay variation and loss.

## 2. How CFM works

### 2.1 Maintenance domains and levels

A **maintenance domain** is the part of the network that one party watches, and it has a **level** from 0 to 7. IEEE
802.1ag suggests levels 5 to 7 for customers, 3 and 4 for service providers, and 0 to 2 for operators. A MEP handles
CFM frames of its own level, drops those of lower levels, and lets those of higher levels through untouched. So the
domains nest: the customer can run its own CFM at level 5 between its CEs, straight through the provider's level 4
domain, and the provider's MEPs do not mistake it for their own.

In this lab, the provider's domain is **PROV** at level **4**.

### 2.2 Maintenance associations and MEPs

Inside a domain, a **maintenance association** (MA; IOS XE calls it a *service*) is one service to watch, here E-Line
130. Each MA has its MEPs, each with a number, the **MEP ID** (MPID); a MEP learns the MEPs of its MA from their CCMs.

A MEP has a direction. A **down MEP** faces the wire: it sends its CCMs out of the port, towards the CE. An **up MEP**
faces into the device: it sends its CCMs into the service, here into the pseudowire towards the other PE. To watch the
provider's part of the E-Line (from XE1's attachment circuit to XE3's), the MEPs are up MEPs on the attachment circuits.
In this lab, where the EFP is cross-connected to an LDP pseudowire, the MEP on the EFP is an up MEP; the outputs show it
as `Up` under `Dir`. An EVPN E-Line is different (3.3).

### 2.3 Continuity check: CCMs and the lifetime

Each MEP sends a CCM every **interval**. The other MEP keeps an entry for it, and the entry expires after **3.5
intervals** without a CCM. That is when the MEP declares the other end lost.

| CC interval | Lost after | In the lab, after a silent break between XE3 and P1 |
|---|---|---|
| 10 s (the default on IOS XE) | 35 s | XE1 still listed MEP 3 ten seconds later |
| 1 s | 3.5 s | MEP 3 was gone from XE1 by 3.2 s, and MEP 1 from XE3 likewise |

The interval is the whole trade-off: shorter intervals notice sooner and send more CCMs. Intervals of 100 ms and less
exist for protection switching; 1 second is common for service monitoring.

### 2.4 Loopback and linktrace

With the MEPs in place, the PE can ping and trace inside the service:

```console
XE1#ping ethernet mpid 3 domain PROV service E130
Sending 5 Ethernet CFM loopback messages to 001e.14d8.53bf, timeout is 5 seconds:!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
XE1#traceroute ethernet mpid 3 domain PROV service E130
Tracing the route to 001e.14d8.53bf on Domain PROV, Level 4, service E130, evc E130
Traceroute sent via Gi2:(10.255.0.43, 130), path found via MPDB
                             MAC      Ingress        Ingr Action  Relay Action
  Hops   Host             Forwarded   Egress         Egr Action   Previous Hop
B 1                    001e.f607.b6bf Gi2            IngOk        RlyMPDB
                       Forwarded
! 2                    001e.14d8.53bf                             RlyHit:MEP
                       Not Forwarded                              001e.f607.b6bf
```

The loopback goes to the other MEP's MAC address and back (LBM and LBR). The linktrace lists each CFM-aware hop: XE1
itself (`B`, a bridge that forwarded it), then MEP 3 (`!`). P1 does not appear: inside the pseudowire, P1 switches labels
and never sees the Ethernet frames.

### 2.5 Y.1731: measuring delay

Y.1731's **delay measurement** sends a DMM (delay measurement message) from one MEP to the other, which answers with a
DMR; the time stamps give the two-way frame delay. On IOS XE an IP SLA operation runs it and keeps statistics. The
operation below sends one DMM per second, and the two-way delay is about 0.7 to 1.9 ms:

```console
XE1#show ip sla statistics 130 details
Type of operation: Y1731 Delay Measurement
Latest operation return code: OK
 Number of measurements initiated: 29
 Number of measurements completed: 29
Delay:
  Number of TwoWay observations: 24
    Min/Avg/Max TwoWay: 688/1275/1916 (microsec)
Operation time to live: Forever
Operational state of entry: Active
```

## 3. Configuring CFM on IOS XE

### 3.1 The configuration

Three parts: CFM on as a whole, the domain with its service, and the MEP on the attachment circuit. The E-Line's EFP is
already named for the EVC `E130` (`service instance 130 ethernet E130`), which is how the service finds it.

:::config fold Catalyst 8000V (IOS XE 17.15) — XE1's part of CFM and Y.1731 delay measurement on E-Line 130 (XE3 has MPID 3 and no IP SLA)
ethernet cfm global                                ## turn CFM on for the router; without it the MEPs stay inactive
ethernet cfm domain PROV level 4                   ## the provider's domain
 service E130 evc E130                             ## the MA for E-Line 130; an xconnect EVC takes no VLAN here
  continuity-check                                 ## send CCMs
  continuity-check interval 1s                     ## lost after 3.5 s (the default 10 s gives 35 s)
!
interface GigabitEthernet2
 service instance 130 ethernet E130                ## the E-Line's EFP (in place)
  cfm mep domain PROV mpid 1                       ## an up MEP; the MEP ID is the site number
!
ip sla 130
 ethernet y1731 delay DMM domain PROV evc E130 mpid 3 cos 0 source mpid 1   ## DMM from MEP 1 to MEP 3, CoS 0
ip sla schedule 130 start-time now life forever    ## run it without end
!
:::

### 3.2 Reading the outputs

`show ethernet cfm maintenance-points local` lists this PE's MEPs. The `CC` column says whether the MEP sends CCMs:
`Y`, or `I` (inactive) when CFM is not on globally.

```console
XE1#show ethernet cfm maintenance-points local
MPID Domain Name                                 Lvl   MacAddress     Type  CC
1    PROV                                        4     001e.f607.b6bf XCON  Y
```

`show ethernet cfm maintenance-points remote` lists the MEPs learned from their CCMs. An entry disappears when it
expires; `show ethernet cfm errors` then lists the loss.

```console
XE1#show ethernet cfm maintenance-points remote
MPID  Domain Name                                 MacAddress          IfSt  PtSt
 Lvl  Domain ID                                   Ingress
 RDI  MA Name                                     Type Id             SrvcInst
      EVC Name                                                        Age
      Local MEP Info
3     PROV                                        001e.14d8.53bf      Up    Up
 4    PROV                                        Gi2:(10.255.0.43, 130)
 -    E130                                        XCON N/A            130
      E130                                                            0s
      MPID: 1 Domain: PROV MA: E130
Total Remote MEPs: 1
```

`Ingress` shows where the CCMs arrive: on Gi2's E-Line, from the pseudowire to 10.255.0.43 with VC ID 130.

### 3.3 What goes wrong

| Mistake | What it looks like |
|---|---|
| No `ethernet cfm global` | The MEPs exist with `CC` = `I`, and no remote MEP is ever learned |
| The default CC interval | A silent break is noticed after 35 s (still listed after 10 s) |
| `service … evc … vlan <n>` for an xconnect | Refused: a VLAN on the service line is for a bridge-domain service |
| The other end lost while Y.1731 runs | The operation stopped with `Latest operation return code: Internal error` and did not start again when MEP 3 came back; `ip sla restart 130` (in configuration mode) started it again |

An up MEP on the EFP of an EVPN-VPWS E-Line does not work (one end sends no CCMs). The IOS XE CFM chapter for
QFP-based platforms (which names the C8000v) lists the restriction: an EVPN EFI cannot be associated with an EVC, only
down MEPs are supported on the EFP in an EVPN scenario, and an up MEP cannot send CFM packets from the EFI to the peer
site. This lab watches the LDP pseudowire for that reason.

:::try
Make the break that nobody notices. Do this after Task M11-9.

1. On XE1, run `show ethernet cfm maintenance-points remote` and check that MEP 3 is listed.
2. In CML, set a link condition of 100 % loss on the link between XE3 and P1 (the link's Link Conditions tab). On XE1,
   repeat the command every second or two; on P1, run `show isis neighbors`.
3. Clear the link condition after about ten seconds. On XE1, run `show ip sla statistics 130 details`, then
   `ip sla restart 130` in configuration mode, and look at the statistics again.
4. To compare, remove `continuity-check interval 1s` on both PEs and repeat steps 1 to 3. Put the line back afterwards.

An example result: with 1 s, MEP 3 was gone within about 3 seconds, while P1 still listed XE3 as an IS-IS neighbour.
With the default interval, MEP 3 was still listed after 10 seconds. After the break, the Y.1731 operation showed
`Internal error` until it was restarted.
:::

### 3.4 The same on IOS XR

On IOS XR, CFM is configured under `ethernet cfm` → `domain PROV level 4` → `service E130 xconnect group <group> p2p
<name>`, with `continuity-check interval 1s`, and the MEP on the attachment circuit's sub-interface: `ethernet cfm` →
`mep domain PROV service E130 mep-id 1`. Unlike IOS XE, IOS XR sends no CCMs until `continuity-check` is configured for
the service. Y.1731 measurements are `ethernet sla` profiles (`type cfm-delay-measurement`)
applied under the MEP (`sla operation profile <P> target mep-id <n>`). The IOS XRv 9000 of this track has no `ethernet cfm` at all.

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `ethernet cfm global` | — (`ethernet cfm` is the configuration mode that holds the domains) |
| `ethernet cfm domain <D> level <n>` → `service <S> evc <EVC>` | `ethernet cfm` → `domain <D> level <n>` → `service <S> xconnect group <G> p2p <P>` |
| `continuity-check interval 1s` (default 10 s) | `continuity-check interval 1s` (off until configured) |
| `service instance <n> ethernet <EVC>` → `cfm mep domain <D> mpid <n>` | sub-interface → `ethernet cfm` → `mep domain <D> service <S> mep-id <n>` |
| `ping ethernet mpid <n> domain <D> service <S>` | `ping ethernet cfm domain <D> service <S> mep-id <n> source interface <IF>` |
| `ip sla <n>` → `ethernet y1731 delay DMM …` | `ethernet sla` → `profile <P> type cfm-delay-measurement` |
| `show ethernet cfm maintenance-points remote` | `show ethernet cfm peer meps` |

## Practice

In lab **XRT-12**, work through Task M11-9. This completes the M11 supplement; the appendix covers E-Tree, G.8032 and
802.1ah.

<p class="tolab"><a href="/_learn?id=XRT-12">Open lab XRT-12 in the workspace</a> — <a href="bc-m11-practice-6.html">Tasks</a></p>

:::note
The refused VLAN on an xconnect service and the up MEP that does not work on EVPN-VPWS come from the PoC.
Sources: Application Services Configuration Guide, Cisco IOS XE 17.x (Configuring Ethernet CFM for Cisco QFP-Based
Platforms; it names the C8000v, gives the default interval of 10 s, and lists the EVPN restriction). IP Addressing
Configuration Guide, Cisco IOS XE 17.x (Configuring IP SLAs Metro-Ethernet 3.0 (ITU-T Y.1731) Operations). Interface and
Hardware Component Configuration Guide for the ASR 9000, IOS XR 24.x (Configuring Ethernet OAM) and the ASR 9000 Ethernet
OAM command reference. IEEE 802.1ag (maintenance levels, the 3.5-interval lifetime), ITU-T G.8013/Y.1731.
All checked in November 2026. The outputs, the detection times, the behaviour without `ethernet cfm global` and the
stopped Y.1731 operation come from measurements in lab XRT-12 (Catalyst 8000V 17.15.1a).
:::
