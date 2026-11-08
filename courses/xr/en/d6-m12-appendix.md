# M12 — Appendix

This appendix covers the rest of blueprint item 1.4 that the main pages did not (TE and QoS, IntServ, the IPv6 flow
label), MACsec from 1.7.d and BGP FlowSpec from 1.5.f. None of it is done by hand in the lab (some of it does not run on
XRv 9000, and this unit's board has no RSVP-TE). At the end are what was checked on XRv 9000 and a command
correspondence table.

## 1. TE and QoS: DS-TE, MAM, RDM, CBTS, PBTS

### 1.1 What is missing

DiffServ decides the treatment for each mark at each hop of the core. But the path is still the IGP's shortest path. If
voice gathers on the shortest path and goes over the limit of that path's priority queues, marking alone cannot protect
it. RSVP-TE, the traffic engineering protocol, reserves bandwidth and chooses the path, but ordinary TE treats a link's
bandwidth as one pool and does not tell the classes apart.

**DS-TE** (DiffServ-aware TE, RFC 4124) splits TE bandwidth reservations by class. For each type of traffic (a
Class-Type, CT; up to 8), it sets a limit on the bandwidth that may be reserved on a link (a Bandwidth Constraint, BC; up
to 8), and an LSP reserves bandwidth within the limit of its CT. A pair of a CT and a preemption priority between LSPs is
a TE-Class; there can be up to 8 (section 4.2.1).

### 1.2 How the limits are set: MAM and RDM

Two rules (bandwidth constraint models) define how the BCs apply to the CTs.

| Model | Idea | Characteristics |
|---|---|---|
| **MAM** (Maximum Allocation Model, RFC 4125) | A dedicated limit per CT: reservations for CTc go up to BCc | Easy to follow, and the classes do not fight over bandwidth. The sum of the limits may exceed the link's reservable bandwidth. Unused bandwidth cannot be used by other classes |
| **RDM** (Russian Dolls Model, RFC 4127) | Nested limits: BC0 = all reservable bandwidth; CT7 up to BC7; CT6 and CT7 together up to BC6; …; all CTs together up to BC0 | Lower classes can use unused bandwidth. It uses bandwidth well, but protecting a class needs preemption |

According to the ASR 9000 guide, IOS XR has a Cisco-specific (prestandard) DS-TE mode and an IETF mode, and the default
model is RDM in both. MAM is configured with `bandwidth mam max-reservable-bw …` under the RSVP interface.

### 1.3 Choosing the path by class: CBTS and PBTS

Once DS-TE protects bandwidth on separate LSPs per class, these features decide which packets go into which LSP.

- **CBTS** (Class-Based Tunnel Selection, the IOS XE name): bundles TE tunnels to the same destination and sets the EXP
  values each tunnel carries (`tunnel mpls traffic-eng exp 5` and so on). The tunnels join a master tunnel
  (`exp-bundle master`) with `exp-bundle member`. If an input QoS policy rewrites the EXP, the rewritten value is used
  for the choice. One EXP value cannot be split over several tunnels.
- **PBTS** (Policy-Based Tunnel Selection, the IOS XR name): classifies packets (by precedence, EXP, DSCP and so on) to
  set a `forward-class`, and sends them into the tunnel with that `forward-class`. The ASR 9000 guide notes that it cannot
  be configured with `policy-map` (use `forward-class`), that a tunnel can have only one `forward-class`, that a tunnel
  without one is 0, and that it works only on L3 interfaces.

## 2. IntServ and RSVP

**IntServ** (Integrated Services, RFC 1633) reserves resources for each application flow and guarantees its treatment.
It has two kinds of service, guaranteed (a bound on delay) and predictive (a predictable treatment), and its keys are
resource reservation and admission control. Routers keep state per flow.

The reservation protocol is **RSVP** (RFC 2205). RSVP is simplex, receiver-oriented (the receiver asks for the
reservation) and soft-state (state disappears unless refreshed). It is not a routing protocol; it reserves along the
path that routing chose.

Provider cores do not use IntServ because it means keeping state for every flow, which does not scale (main page,
section 1.2). DiffServ solved this by aggregating the treatment by kind of mark. RSVP itself lives on in the core as
RSVP-TE, which reserves bandwidth for TE LSPs (what is reserved is the provider's LSP, not the customer's flow).

## 3. The IPv6 flow label

The IPv6 header has a 20-bit **flow label** (RFC 6437), a field in which the sender puts the same value on the packets
of one flow.

- 0 means "not labelled".
- A flow is identified by the triple (flow label, source address, destination address). Routers on the way can tell
  flows apart without reading the TCP or UDP ports (without digging through the extension headers).
- The main use is the hash that spreads traffic over equal-cost paths (ECMP) and link bundles, so values should be chosen
  to vary.
- Nodes on the way must not change a non-zero value (except for compelling security reasons).

It is a separate field from the QoS mark (DSCP); the flow label does not decide the treatment. The blueprint lists it
under QoS because it was made for flow-based treatment such as IntServ.

## 4. MACsec

**MACsec** (IEEE 802.1AE) encrypts the Ethernet frames between neighbouring devices, hop by hop, and protects them from
tampering. Keys are exchanged with MKA (MACsec Key Agreement). Unlike IPsec, it encrypts below IP, on the Ethernet frames.

The form of the configuration in the ASR 9000 guide is as follows. Support depends on the chassis and line cards
(it is hardware-dependent).

- `key chain <name>` → `macsec` → `key <ID>` → `key-string … cryptographic-algorithm aes-128-cmac` → `lifetime …`
- `macsec-policy <name>` (cipher and policy)
- Under the interface, `macsec psk-keychain <key chain> policy <macsec-policy>`
- Check it with `show macsec mka session`.

IOS XRv 9000 26.1.1 had `macsec` under `key chain`, but neither `macsec-policy` nor `macsec` under an interface (they
are not in the syntax). MACsec is not in the official support table of the release notes either.

## 5. BGP FlowSpec

This continues section 3.6 of the main page. FlowSpec rules travel as the NLRI of a new BGP address family (IPv4
flowspec). The NLRI holds the conditions (destination and source prefixes, protocol, ports, ICMP type, DSCP, packet
length and so on; twelve types in section 4.2.2 of RFC 8955), and the actions are extended communities (a rate limit, with
0 meaning drop; steering into a VRF; re-marking the DSCP and so on; section 7).

IOS XR writes rules in the same MQC form as QoS (`class-map type traffic` and `policy-map type pbr`) and hands them out
under `flowspec`. The form on this board is below (RR1 builds and sends the rules; XR01 receives them).

:::config RR1 (XRd) and XR01 — send and receive FlowSpec rules (XRv 9000 cannot apply them)
class-map type traffic match-all FS-ATTACK   ## The conditions (RR1)
 match destination-address ipv4 198.51.100.129 255.255.255.255
 match protocol icmp
 end-class-map
!
policy-map type pbr FS-POLICY                ## The action (RR1)
 class type traffic FS-ATTACK
  drop                                       ## Sent as a rate limit of 0
 !
 class type traffic class-default
 !
 end-policy-map
!
flowspec                                     ## Send the rules (RR1)
 address-family ipv4
  service-policy type pbr FS-POLICY
!
router bgp 65000                             ## Turn on ipv4 flowspec on both RR1 and XR01
 address-family ipv4 flowspec
 neighbor 10.255.0.1                         ## (The RR1 side; on XR01, address-family ipv4 flowspec under neighbor 10.255.0.52)
  address-family ipv4 flowspec
   route-reflector-client
!
flowspec                                     ## Apply the received rules (XR01)
 address-family ipv4
  local-install interface-all
:::

XR01 received the rule (`Dest:198.51.100.129/32,Proto:=1/72` in `show bgp ipv4 flowspec`, and `Traffic-rate: 0 bps` in
`show flowspec ipv4 detail`), but the packets were not dropped. The ASR 9000 guide notes that QoS takes precedence over
FlowSpec and that FlowSpec does not act on MPLS traffic.

## 6. What was checked on IOS XRv 9000

| Item | Official documentation | This lab (XRv 9000 26.1.1) |
|---|---|---|
| Rate without a licence | "Rate limitations of 200 Kbps for throughput for all interfaces" (Smart Licensing chapter); the CML page measured 168 kbps | About 4 Mbps went through (limited by what the sending IOL could generate) |
| Classification and marking | "Bi-directional Policing and Marking" in the support table | Works; the counters lag 10 to 30 seconds |
| Policers | The same | Work; the two-rate three-colour counts match the other CE's |
| Hierarchical policers | "Hierarchical Policers" in the support table | (Not tried) |
| Shapers and priority queues | Not in the support table; the 2018 data sheet says "H-QoS"; the data-plane chapter shows one priority and seven normal queues | The rate is held down; the queue holds about one packet |
| WRED | Not mentioned | Accepted, but the counts are 0 |
| Marks per class | ASR 9000 guide: "Choose only two set commands per class" | A third kind is refused at commit |
| uRPF | In the data sheet | Strict, loose and `allow-default` work |
| ACLs and ABF | "IPv4 and IPv6 ACL" and "ACL Based Forwarding" in the support table | Work; `hardware-count` counts; object-groups are not available |
| RTBH `set next-hop discard` | In the ASR 9000 guide | Works, and source-based uRPF drops with it |
| uRPF and recursion to Null0 | ASR 9000 TAC 116386: "unable to do recursive lookup to null0" | The same (not dropped through 192.0.2.1) |
| MACsec | Not mentioned | Not in the syntax |
| FlowSpec client | Not mentioned (a Community answer says "controller only") | Received but not applied |

The two disagreements between the documentation and the lab (the rate without a licence, and the shaper) may depend on
the release and the environment (CML). They are not used to decide whether a task is right.

## 7. Command correspondence (IOS XE and IOS XR)

| To do | IOS XE | IOS XR |
|---|---|---|
| End a class | (not written) | `end-class-map` |
| End a policy | (not written) | `end-policy-map` |
| EXP on every label pushed | `set mpls experimental imposition 5` | The same |
| The router's internal mark | `set qos-group 5` | The same (input only); `match qos-group 5` on output |
| Policer rates | `police cir 256000 pir 512000` (bps) | `police rate 256 kbps peak-rate 512 kbps` |
| Re-marking the excess | `exceed-action set-dscp-transmit af22` | `exceed-action set dscp af22` |
| Priority queue | `priority` (LLQ) | `priority level 1` (with a policer) |
| How the policy went in | `show policy-map interface` | `show qos interface <IF> input`, `output` |
| Counts | `show policy-map interface` | `show policy-map interface <IF> input`, `output` |
| Clearing the counts | `clear counters <IF>` | `clear qos counters interface <IF> input`, `output` |
| Strict uRPF | `ip verify unicast source reachable-via rx` | `ipv4 verify unicast source reachable-via rx` |
| Loose uRPF | `ip verify unicast source reachable-via any` | `ipv4 verify unicast source reachable-via any` |
| Count per ACL line | `show ip access-lists` (counted by default) | `ipv4 access-group … hardware-count` → `show access-lists ipv4 <name> hardware ingress location …` |
| The RTBH edge | A static route to the discard address plus the received next hop | The same, or RPL `set next-hop discard` |
| Not propagating TTL | `no mpls ip propagate-ttl` | `mpls ip-ttl-propagate disable` |
| Explicit null | `mpls ldp explicit-null` | `mpls ldp address-family ipv4 label local advertise explicit-null` |

:::note
Sources: RFC 4124 (sections 4.1.1 and 4.2.1), RFC 4125 (section 3), RFC 4127 (section 4), RFC 1633 (section 2.1), RFC 2205
(section 1), RFC 6437 (section 2), RFC 8955 (sections 4.2.2 and 7). The IOS XE MPLS TE Path Calculation and Setup
Configuration Guide, "MPLS Traffic Engineering Class-based Tunnel Selection"; the ASR 9000 MPLS Configuration Guide (IOS XR
24.x), "Implementing MPLS Traffic Engineering" (PBTS, DS-TE); the ASR 9000 System Security Configuration Guide (IOS XR
24.x), "Configure MACSec"; the ASR 9000 Routing Configuration Guide (IOS XR 24.x), "Implementing BGP Flowspec"; the IOS XRv
9000 Installation and Configuration Guide, release notes (25.1.1) and data sheet (2018); the CML page for IOS XRv 9000. All
checked in November 2026. The "This lab" column of the table and the FlowSpec and MACsec results come from measurements on
the PoC board (the same shape as XRT-14). IOS XE `no mpls ip propagate-ttl` and `mpls ldp explicit-null` have the same form
as in M8; in this lab, only PE2's explicit null was tried.
:::
