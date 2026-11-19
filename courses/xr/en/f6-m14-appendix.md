# M14 — Appendix

This appendix collects what the main pages mention only briefly or not at all: the Assert, which settles which router
forwards onto a shared LAN; MSDP and Anycast RP; a first look at multicast VPNs; and the IGMP and MLD versions side by
side. Then come the defaults of IOS XR and IOS XE, their commands side by side, what was checked in this unit, and
where the documents and the devices differ. MSDP, Anycast RP and multicast VPNs are not configured in the lab, and
nothing about them was measured.

## 1. Assert: who forwards onto a shared LAN

### 1.1 Two routers, one LAN, two copies

Normally one router forwards a group onto a LAN. There are moments when two do: when the DR changes, or when both
routers have their own reason to forward the same group onto it, for example a member configured on each. Every host
on the LAN then receives each packet twice.

The two routers find out from the packets themselves: each sees the group's packets arrive on an interface that it
forwards the group out of. Both then send an Assert message for the group onto the LAN, and a comparison decides which
one keeps forwarding.

### 1.2 How the Assert is decided

An Assert carries what its sender knows about its route back to the source (for the shared tree, back to the RP).
RFC 7761 (section 4.6.3) compares the two, in this order:

1. **The rpt bit.** An Assert for the shortest-path tree, (S,G), beats one sent for the shared tree.
2. **The metric preference of the route**: on Cisco routers, its administrative distance. The lower wins.
3. **The metric of the route.** The lower wins.
4. **The address on the LAN.** The higher wins.

The loser stops forwarding the group onto the LAN, and the winner keeps forwarding. The routers downstream on the LAN
take the winner as their upstream neighbour; IOS marks such a neighbour with `*` in `show ip mroute` (the legend says
`* - determined by Assert`). The address is the last resort, and on one LAN it never ties.

### 1.3 What it looks like on the devices

IOS XR marks an interface that has been through an Assert with `AS` in `show pim topology` (`AS - Assert` in the
legend). IOS XE marks the winner's outgoing interface with `A` in `show ip mroute` (`A - Assert winner`).

On the PoC board, a shared LAN had an IOS XRd router and an IOS XE router side by side, as ACCESS-3 does, but with
other addresses. The IOS XE router was the DR. When `dr-priority 10` made the XRd router the DR, one packet reached
the receiver on that LAN twice (21 replies to 20 pings), and the new DR's interface carried the Assert (an excerpt of
`show pim topology` on the XRd router):

```console
(*,239.1.1.1) SM Up: 00:15:00 RP: 10.255.0.11 
JP: Join(00:00:03) RPF: GigabitEthernet0/0/0/0,10.0.3.11 Flags: LH 
  GigabitEthernet0/0/0/1      00:15:00  fwd LI AS(self,00:02:28) LH 
```

`AS(self,…)` names this router on that interface. The duplicate came from the moment when both routers forwarded;
which of the four rules decided the Assert was not isolated. On an earlier board with IOS routers only, two routers
forwarded the same (S,G) onto one LAN with equal distance and metric: the one with the higher address won, and its
outgoing interface carried `A`.

## 2. MSDP and Anycast RP

### 2.1 One RP is one place

In PIM-SM, every source of a group registers with one router, and every shared tree of that group has its root there.
If the RP fails, the routers need another one. With static RPs, someone changes the configuration; with BSR, the other
candidates take over when the failed RP's entry times out (its holdtime: 150 seconds at the default interval).

An RP also knows only the sources that registered with it. Separate domains, each with its own RP, do not learn about
each other's sources this way.

### 2.2 MSDP: RPs tell each other about their sources

MSDP (Multicast Source Discovery Protocol, RFC 3618) connects RPs with TCP sessions on port 639. When a source
registers with one RP, that RP sends a Source-Active (SA) message to its MSDP peers: this source is sending to this
group, with the first data packet inside. An RP that has receivers for the group joins toward the source. MSDP was
made for multicast between the domains of different providers.

### 2.3 Anycast RP: one address on several RPs

Anycast RP gives several RPs the same address, on a loopback with a 32-bit mask, and advertises it in the IGP. Each
router's Joins and Registers go to the nearest of them, as unicast routing decides, and if one fails, routing
converges onto the others.

A source may register with one RP while its receivers join at another, so the RPs tell each other about their sources
with MSDP. Their MSDP sessions use each RP's own address, not the shared one, and the originator ID of the SAs is set
to it as well (by default the RP address would be used).

RFC 4610 does the same with PIM alone: the RPs pass Registers on to each other, and MSDP is not needed. MSDP runs only
on IPv4, so IPv6 uses this way; IOS XE calls it PIMv6 Anycast RP.

### 2.4 Where they come back

Neither is configured in this course yet. The SPRI blueprint (300-510) lists MSDP operations (2.2.d and 2.3.d), and
anycast RP and Phantom RP (2.3.a). They belong to the SPRI part of the course, which comes later.

## 3. Multicast VPNs, a first look

### 3.1 The problem: multicast inside a VRF

In an L3VPN (M9), a customer's packets travel in a VRF, and the P routers of the core know none of the customer's
routes (M8). If the customer runs multicast between its sites, its PIM Joins point toward customer sources and
customer RPs, which the core has no routes to. SPCOR lists the answer, mVPN, under 4.1.d, among the VPN services to
describe.

### 3.2 The words already on the board

This unit does not configure mVPN, but the IOS XRd routers already offer its parts. Under `multicast-routing` there is
`vrf`, and under its `address-family ipv4`, `?` lists among others (an excerpt):

```console
  bgp                         Enable BGP MVPN Discovery
  core-tree-protocol          Configure Core-tree-protocol
  export-rt                   Configure Export Route-Target
  import-rt                   Configure Import Route-Target
  mdt                         MVPN configuration
```

`router pim` → `address-family ipv4` offers `mdt` as well (`Multicast Distribution Tree commands`), and the legends of
`show pim topology` and `show mrib route` carry flags for it: `ME - MDT Encap`, `MD - MDT Decap`,
`MT - Crossed Data MDT threshold`, `BGP - BGP C-Multicast Join`.

Put together, the words give the shape: a VRF, a multicast distribution tree (MDT) across the core built by a
core-tree protocol, PEs that find each other through BGP, and route targets as in M9. The legends have been describing
it on every output of this unit.

### 3.3 Where it comes back

mVPN was not tried in this unit, and nothing on this page about it was measured. It comes with the SPRI part of the
course, whose blueprint also lists mLDP and P2MP (2.2.e).

## 4. The IGMP and MLD versions side by side

### 4.1 What each version adds

| Version | Defined in | What it adds |
|---|---|---|
| IGMPv1 | RFC 1112 | Queries from the router and reports from the hosts |
| IGMPv2 | RFC 2236 | A Leave message (sent to 224.0.0.2), the group-specific query, a maximum response time in the query, and the election of a querier (the lowest address) |
| IGMPv3 | RFC 3376 | Source lists: a report says which sources to receive from (INCLUDE) or which not to (EXCLUDE). Reports go to 224.0.0.22. SSM needs it |
| MLDv1 | RFC 2710 | IPv6's counterpart of IGMPv2, carried in ICMPv6 (query 130, report 131, done 132) |
| MLDv2 | RFC 3810 | IPv6's counterpart of IGMPv3 (report 143, sent to FF02::16) |

The difference shows on the router. With PE2's host-facing interface set to version 1 on the PoC board,
`show igmp interface` no longer had the lines for the querier and for the maximum response time; with versions 2 and 3
they are there. IOS XE hosts report with version 2 by default. IOS XR routers run version 3 and IOS XE routers version
2 by default (section 5).

### 4.2 When the versions on a LAN differ

A host answers in the version of the oldest querier it hears. When it hears a query of an older version, it falls back
to that version, and it returns to its own version only after it has heard no older query for a while: robustness ×
query interval + query response interval (RFC 3376, section 8.12), which is 2 × 60 + 10 = 130 seconds with these
values.

Example result: on the PoC board, PE2's host-facing interface was set to version 2, and the IOS XE host RCV2 fell back
to version 2. After PE2 was set back to version 3, RCV2 still reported in version 2 for between 103 and 136 seconds.
During that time its reports for an SSM group named no source, PE2 dropped them, and nothing in the SSM range arrived.
Once RCV2 was back at version 3, all 10 packets arrived.

The routers on one LAN must agree. RFC 3376 (section 7.3.1) says that all routers on a LAN MUST be configured with the
lowest version in use there, and the IOS XR documentation says that all routers on a subnet must run the same version.
As built, ACCESS-3 does not: PE3 runs IOS XR's default version 3 and PE4 runs IOS XE's default version 2. PE4 still
names PE3 as the querier.

## 5. Defaults on these platforms

The values below are what the devices of this lab show with no configuration, together with the documents that say the
same. "Device" means IOS XRd 26.1.1 for IOS XR and IOL 17.15 for IOS XE.

| Setting | IOS XR | IOS XE | Where it is stated |
|---|---|---|---|
| Multicast routing on interfaces | None until `multicast-routing` enables them | None until `ip multicast-routing` and `ip pim sparse-mode` | Cisco 8000 configuration guide ("by default, no interfaces are enabled"); devices |
| IGMP version | 3 | 2 | Cisco 8000 command reference; IOS command reference; devices |
| IGMP query interval | 60 s | 60 s | The same |
| IGMP maximum response time | 10 s | 10 s | The same |
| Last member query interval | 1 s | 1000 ms | Devices |
| MLD version | 2 | 2 | Cisco 8000 configuration guide ("MLDv2 is enabled … by default"); devices |
| MLD query interval, maximum response time | 125 s, 10 s | 125 s, 10 s | Devices |
| PIM hello interval | 30 s | 30 s | IOS command reference; devices |
| DR priority | 1 | 1 | IOS command reference; devices |
| Switch to the shortest-path tree | After the first packet | After the first packet | Cisco 8000 command reference and configuration guide; IOS command reference; devices |
| SSM range | 232.0.0.0/8 | None until `ip pim ssm default` (232/8) or `ip pim ssm range` | Cisco 8000 command reference; IOS command reference; devices |
| Bidirectional PIM | `rp-address … bidir` is accepted (on this virtual platform) | On PE4, `bidir` is refused until `ip pim bidir-enable` | Devices; see section 7.2 |
| Candidate RP priority (the lower wins) | 192 | 0 | Cisco 8000 configuration guide (example), RFC 5059 (section 3.2), device; IOS XE 17.x guide, device |
| Candidate RP interval (holdtime) | 60 s (150 s) | 60 s (150 s) | Devices; IOS command reference. On IOS XR, `interval 30` gives a holdtime of 75 s |
| Candidate BSR priority (the higher wins) | 1 | 0 | Cisco 8000 command reference, device; IOS XE 17.x guide, IOS command reference, device. RFC 5059 suggests 64 |
| BSR hash mask length | 30 | 0 | Device; IOS command reference, device |
| Auto-RP groups 224.0.1.39 and 224.0.1.40 | Flooded in dense mode out of every interface (`DM perm` in `show pim group-map`) | Forwarded on sparse-mode interfaces only with `ip pim autorp listener` | Cisco 8000 command reference (group-map example), CRS command reference; IOS command reference; devices |
| A static RP and a learned RP for the same groups | The learned one, unless the static one has `override` | The same | ASR 9000 configuration guide; devices |

The rows for the candidate RP and the candidate BSR point in opposite directions (a lower candidate RP priority wins,
a higher candidate BSR priority wins), and their defaults differ between the platforms. In a domain with both
platforms left at the defaults, an IOS XE candidate RP (0) beats an IOS XR one (192), and an IOS XR candidate BSR (1)
beats an IOS XE one (0).

## 6. Commands: IOS XE and IOS XR side by side

### 6.1 Configuration

On IOS XR, the commands in the right-hand column sit under `router pim` → `address-family ipv4` unless the row says
otherwise.

| To do | IOS XE (IOL 17.15) | IOS XR (26.1.1) |
|---|---|---|
| Turn on multicast routing | `ip multicast-routing`, and `ip pim sparse-mode` on each interface | `multicast-routing` → `address-family ipv4` → `interface all enable` (or `interface <if> enable`) |
| Stop multicast on one interface | `no ip pim sparse-mode` on the interface | `multicast-routing` → `address-family ipv4` → `interface <if>` → `disable` |
| Stop only PIM on one interface | (Not used in this unit) | `interface <if>` → `disable` |
| Static RP | `ip pim rp-address <rp> [<acl>] [override]` | `rp-address <rp> [<acl>] [override]` |
| Bidirectional RP | `ip pim bidir-enable`, then `ip pim rp-address <rp> <acl> bidir` | `rp-address <rp> <acl> bidir` |
| Stay on the shared tree | `ip pim spt-threshold infinity [group-list <acl>]` | `spt-threshold infinity [group-list <acl>]` |
| SSM range | `ip pim ssm default`, or `ip pim ssm range <acl>` | 232/8 without configuration; `ssm range <acl>` |
| Accept Registers only from some sources (on the RP) | (Not used in this unit) | `accept-register <acl>` |
| Candidate RP (BSR) | `ip pim rp-candidate <if> [group-list <acl>] [priority <n>]` | `bsr candidate-rp <address> [group-list <acl>] [priority <n>] [interval <s>]` |
| Candidate BSR | `ip pim bsr-candidate <if> [<hash-mask-length>] [<priority>]` | `bsr candidate-bsr <address> [hash-mask-len <n>] [priority <n>]` |
| Auto-RP candidate RP | `ip pim send-rp-announce <if> scope <ttl>` | `auto-rp candidate-rp <if> scope <ttl> interval <s>` |
| Auto-RP mapping agent | `ip pim send-rp-discovery <if> scope <ttl>` | `auto-rp mapping-agent <if> scope <ttl> interval <s>` |
| Pass Auto-RP on sparse-mode interfaces | `ip pim autorp listener` | Not needed (224.0.1.39 and 224.0.1.40 flood in dense mode) |
| DR priority | `ip pim dr-priority <n>` on the interface | `interface <if>` → `dr-priority <n>` |
| IGMP version | `ip igmp version <1-3>` on the interface | `router igmp` → `interface <if>` → `version <1-3>` |
| The router as a member of a group | `ip igmp join-group <group> [source <source>]` on the interface | `router igmp` → `interface <if>` → `join-group <group>` |
| Forward onto a LAN without a member | `ip igmp static-group <group>` on the interface | `router igmp` → `interface <if>` → `static-group <group>` |
| IPv6 | `ipv6 multicast-routing`; `ipv6 pim rp-address <rp>` | `multicast-routing` → `address-family ipv6` → `interface all enable`; `router pim` → `address-family ipv6` → `rp-address <rp>` |
| MLD | `ipv6 mld …` on the interface (a host joins with `ipv6 mld join-group <group>`) | `router mld` |

### 6.2 Show commands

| To see | IOS XE | IOS XR |
|---|---|---|
| PIM interfaces and the DR | `show ip pim interface [detail]` | `show pim interface [detail]` |
| PIM neighbours | `show ip pim neighbor` | `show pim neighbor` |
| IGMP on an interface: version, querier, timers | `show ip igmp interface` | `show igmp interface` |
| IGMP members | `show ip igmp groups [<group>] [detail]` | `show igmp groups [<group>] [detail]` |
| The multicast routing state | `show ip mroute [<group>]` | `show pim topology [<group>]` (PIM's view), `show mrib route [<group>]` (the routing table) |
| Forwarding counters | `show ip mfib count` | `show mfib route <group> detail` |
| RPF toward a source or the RP | `show ip rpf <address>` | `show pim rpf [<address>]` |
| Which RP serves which groups | `show ip pim rp mapping` | `show pim rp mapping`, `show pim group-map [<group>]` |
| The RP chosen for one group (BSR) | `show ip pim rp-hash <group>` | `show pim group-map <group>` |
| BSR | `show ip pim bsr-router` | `show pim bsr election`, `show pim bsr candidate-rp` |
| Auto-RP | `show ip pim autorp` | `show auto-rp mapping-agent`, `show auto-rp candidate-rp` |
| BIDIR: the DF on each interface | `show ip pim interface df` | `show pim df winner` |
| IPv6 | `show ipv6 pim interface`, `show ipv6 pim neighbor`, `show ipv6 mroute`, `show ipv6 mld interface`, `show ipv6 mld groups` | `show pim ipv6 interface`, `show pim ipv6 neighbor`, `show pim ipv6 topology`, `show pim ipv6 group-map`, `show mld interface`, `show mld groups` |

On IOS XR, the command that clears IGMP groups is singular: `clear igmp group`. `clear igmp groups` is refused as
invalid input.

## 7. What was checked, and where the documents and the devices differ

### 7.1 What was checked

| Item | IOS XRd 26.1.1 | IOS XRv 9000 26.1.1 | IOS XE on IOL 17.15 |
|---|---|---|---|
| Forwarding multicast data | Forwards as first hop, RP, last hop and transit | Forwards as first hop and last hop (PoC board) | Forwards (PE4, the DR on ACCESS-3) |
| MFIB software counters (`show mfib route … detail`) | Count the packets | Stay at 0 | — |
| Turning it on | `interface all enable` starts PIM and IGMPv3 on every interface, Loopback0 included; `router pim` alone enables none | `interface all enable`: the same, without `router pim` | `ip multicast-routing` and `ip pim sparse-mode` |
| PIM neighbour table | Lists the router itself (`*`); XR neighbours flagged `B`, IOS XE ones `P` | (Not checked separately) | XR neighbours flagged `G` |
| Querier and DR on a shared LAN | Querier = the lowest address, DR = the highest, also with IGMPv3 and IGMPv2 side by side | (Not tried) | The same; names the XR router as the querier |
| Switch to the shortest-path tree | After the first packet; `spt-threshold infinity` keeps the router on the shared tree | The same | The same (`ip pim spt-threshold infinity`) |
| SSM | 232/8 without configuration; IGMPv3 (S,G) joins delivered with no state on the RP; IGMPv2 joins in the range not listed | The same | Needs `ip pim ssm default` (or a range), and `ip igmp version 3` where it is the DR |
| BIDIR | Works; no (S,G); `show pim df winner` | Works | Needs `ip pim bidir-enable` |
| BSR | Candidate RP: priority 192, interval 60; candidate BSR: priority 1, hash mask length 30; the lower candidate RP priority wins | Candidate BSR: priority 1 | Learns the same RP from an XR BSR |
| Auto-RP | 224.0.1.39 and 224.0.1.40 flooded in dense mode; `show auto-rp mapping-agent`, `show auto-rp candidate-rp` | Works as the mapping agent | Learns the RP from an XR neighbour without `ip pim autorp listener` |
| A static RP and a learned RP | (Not tried) | The learned one wins; with `override`, the static one | The same (an earlier IOS-only board) |
| The router as a member | `join-group`: the router answers pings to the group (`II`) | `static-group`: forwards onto the LAN with no host | `ip igmp join-group`: the host answers pings |
| Changing the IGMP version | (Not tried) | `version 2` and `version 1`; the IOS XE host follows | The host returns to version 3 103 to 136 seconds after the router does |
| IPv6 | PIMv6 neighbours by link-local address; MLDv2; Registers taken out on `Decaps6tunnel0`; switch after the first packet | PIMv6 neighbours by link-local address; MLDv2 | `ipv6 mld join-group` on the host; a ping to an IPv6 group asks for the output interface |
| Assert | At a DR change, one duplicate; the new DR showed `AS(self,…)` | (Not tried) | — |

### 7.2 Where the documents and the devices differ

- **Multicast on IOS XRd** is not described in the documents of XRd (section 8).
- **BIDIR on IOS XR.** The Cisco 8000 configuration guide (26.x) lists PIM Bidir as not supported on that platform. On
  IOS XRv 9000 and IOS XRd it works. `show pim df winner` appears only in the command reference for the CRS, not in
  the current ones, and works here.
- **Where `ssm range` goes.** The command reference places it under `multicast-routing` → `address-family ipv4`; the
  configuration guide's section on the submodes puts it under `router pim`. IOS XRd 26.1.1 accepts it in both places,
  and both take effect; under `multicast-routing`, `?` marks it `(cisco-support)`. A range of your own replaces 232/8
  unless the list includes it (command reference); the examples on these pages list 232/8 in their own ranges.
- **The IGMP querier timeout.** The command reference's text gives 120 seconds. Its output example and the device show
  125 seconds, the value of RFC 3376's formula (section 8.5) for a 60-second query interval.
- **The default MLD version.** An older CRS document (IOS XR 4.0) gives MLDv1. The current configuration guide and the
  device give MLDv2.
- **`ip pim bidir-enable` on IOS XE.** The Catalyst 9600 command reference (17.13) gives "enabled" as the default. On
  PE4 (IOL 17.15), `ip pim rp-address … bidir` is refused with `% Invalid input` until `ip pim bidir-enable` is
  configured, and `no ip pim bidir-enable` removes the bidir RP lines as well. The default seems to differ between
  platforms.
- **Overlapping static RPs.** When two static RPs cover the same group, IOS XE uses the RP with the highest address
  (Catalyst 9600 command reference 17.13: "the RP for the group is determined by the RP with the highest RP address
  configured"). IOS XR used the longer range; its documents say nothing about it, and the behaviour matches the
  longest match of RFC 7761 (section 4.7.1).
- **In the examples on these pages** (all groups to 10.255.0.11, and 239.2.0.0/16 to 10.255.1.11 for BIDIR), both
  rules pick the same RP for 239.2.0.0/16, because the longer range also has the higher address. With a BIDIR RP whose
  address is lower, they would not.

Where a document and a device of this lab disagree, these pages describe what the device did and name the document.
Such points are not used to decide whether a task is right.

## 8. IOS XRd as a multicast router

The documents of IOS XRd do not cover multicast: its data sheet and the release notes for 26.1.1 do not mention it.
Everything this unit says about XRd forwarding multicast comes from the devices.

On this virtual platform, XRd forwarded multicast in every role: as the first hop (it builds the Registers), as the RP
(it takes them out, on the `Decapstunnel` interface), as the last hop and in transit. On XRT-16, PIM-SM, staying on
the shared tree, SSM, BIDIR, BSR and IPv6 all delivered 10 of 10 packets.

The counters differ between the two virtual platforms. On XRd, `SW Forwarding Counts` in `show mfib route … detail`
grow with the packets. On IOS XRv 9000 they stay at 0 although the packets arrive, so on XRv 9000 count at the
receivers. Example result on P1, after 3 + 10 pings to a group that stayed on the shared tree (an excerpt):

```console
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.2 detail
...
(192.168.1.1,239.1.1.2),  Flags:  , FMA: 0x10000 ,
...
  SW Forwarding Counts: 13/12/1200
  SW Replication Counts: 13/12/1200
  SW Failure Counts: 0/0/0/0/0
```

XRd starts in about 80 seconds. XRv 9000 takes about nine minutes, and the lab host runs at most two of them at once.
That is why XRT-16 uses XRd only.

Whether a hardware platform supports a feature is a question for that platform's guide. BIDIR is the example in this
unit: the Cisco 8000 guide lists it as not supported, and it works on both virtual platforms here.

:::note
Sources: RFC 7761 (sections 4.3.2, 4.6.3 and 4.7.1), RFC 1112, RFC 2236, RFC 3376 (sections 7.3.1, 8.5 and 8.12), RFC
2710, RFC 3810, RFC 4604 (section 3.5), RFC 4607, RFC 5015, RFC 5059 (section 3.2), RFC 3618 and RFC 4610. Cisco: the
Multicast Configuration Guide for the Cisco 8000 (IOS XR 26.1.x–26.3.x) and its Multicast Command Reference
(2026-09-11); the Multicast Configuration Guide for the ASR 9000 (IOS XR 25.1.x–25.4.x) and its Command Reference
(2026-09-11); the Multicast Command Reference for the CRS (2020) and a CRS document for IOS XR 4.0; the IP Multicast
Configuration Guides for IOS XE 17.x (including MSDP and PIMv6 Anycast RP); the Cisco IOS IP Multicast Command
Reference; the Catalyst 9600 command reference for IOS XE 17.13 (`ip pim rp-address`, `ip pim bidir-enable`); the IOS
XRd data sheet and the release notes for IOS XRd 26.1.1. The SPCOR (350-501) and SPRI (300-510) blueprints. All
checked in November 2026. Measured: on XRT-16 (IOS XRd 26.1.1 and IOL 17.15), the defaults of section 5 (except the
IOS XE candidate RP and BSR values and the last row), the BSR and Auto-RP rows of section 7.1, the overlapping static RPs, `bidir-enable` and the counters of
section 8; on a PoC board with IOS XRv 9000 26.1.1, IOS XRd 26.1.1 and IOL 17.15 (PE1 and PE2 on XRv 9000, P1 on XRd,
a shared LAN with an XRd router and an IOS XE router), the Assert, the IGMP versions and the host's return to version
3, `join-group` and `static-group`, the static and learned RPs, `ssm range`, the XRv 9000 counters, the IPv6 rows and
the `?` lists of section 3.2; on an earlier board with IOS routers only (IOL 17.15), the Assert between IOS routers,
the IOS XE candidate RP and BSR defaults, and Auto-RP without a listener.
:::
