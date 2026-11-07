# Build order — all four in the same five steps

The previous page showed that the four services differ in two things: what the container is, and how its number is passed.
This page looks at the same thing from the configuration side. All four can be built in **the same five steps, in the same
order**. What differs is what you write in each step.

The configuration examples come from the same topology as the previous page, cut from the running-config that was entered and
worked in the PoC. IOS XE is XE1 (site 1); IOS XR is XR01 (site 4).

## 1. Why bother

### 1.1 The problem: not knowing where to start

When you add a service, the configuration is scattered: `router bgp`, `vrf`, `l2vpn`, `interface`, `bridge-domain`.
The tasks in each unit asked you to add or fix one of those places, so you never had the chance to build the whole thing
through and see "what to write, in what order".

If you learn it scattered, then when something is missing you also cannot tell where it has stopped.

### 1.2 The answer: five steps, from the bottom up

Service configuration is layered: each step rests on the one below. If you write from the bottom up and check each step,
you can tell at once "which step" it is when something stops.

| Step | What it does | L3VPN | VPWS (LDP) | VPLS | EVPN (E-LAN) |
|---|---|---|---|---|---|
| 0 Base | A labelled road to the remote PE's loopback | IGP and LDP (or SR). Common to all four | ← | ← | ← |
| 1 PE to PE | A way to find the other PEs | VPNv4 on the iBGP to the RR | None (named in step 2) | None (named in step 2) | L2VPN EVPN on the iBGP to the RR |
| 2 Container | Create the service's container | VRF (RD, RT) | xconnect (names the peer) | VFI (names the peers) and bridge domain | EVI and bridge domain |
| 3 Attach | Connect the customer's interface to the container | Put the subinterface in the VRF and exchange routes with the CE | The AC into the xconnect | The AC into the bridge domain | The AC into the bridge domain |
| 4 Check | Look from the bottom step up | The table in section 5 | | | |

Step 0 belongs to the core design; it is not something you build per service. What you write each time you add a service
is steps 1 to 3. And step 1 is written only once, the first time, for the services that use BGP.

## 2. Step 0: check the base

Before writing the service, check that there is a labelled road to the remote PE's loopback. If it is missing, nothing
gets through even if every step above is right. On this topology, removing `mpls ip` from P1's interface towards XR01 left
the L3VPN routes in place while the ping dropped to 0%, and the pseudowire between XE1 and XR01 went down.

```console
XE1#show mpls forwarding-table 10.255.0.42 32
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
22         18         10.255.0.42/32   0             Gi1        10.0.41.51
XE1#traceroute mpls ipv4 10.255.0.42/32
  0 10.0.41.41 MRU 1500 [Labels: 18 Exp: 0]
L 1 10.0.41.51 MRU 1500 [Labels: implicit-null Exp: 0] 7 ms
! 2 10.0.42.42 2 ms
```

If `Outgoing Label` is a number (18 here) or `Pop Label`, the road is there. If it is `No Label` (`Unlabelled` on IOS XR),
the road carries no label and the services will not get through. `traceroute mpls` shows the label at each hop of the road.
To run it from IOS XR, both the sender and the responder need `mpls oam` (M8).

## 3. Step 1: PE to PE (only for the services that use BGP)

L3VPN and EVPN find the other PEs in BGP. The PE sets up iBGP with the RR (RR1) and enables the address families it uses.
RR1's side is preinstalled, with the four PEs as RR clients (the last example in this section).

:::config XE1 (IOS XE) — iBGP to the RR
router bgp 65000
 bgp router-id 10.255.0.41
 no bgp default ipv4-unicast                      ## Do not enable IPv4 unicast on neighbours by default. Name only the families you use
 neighbor 10.255.0.52 remote-as 65000              ## The RR (RR1). PEs do not peer with each other directly
 neighbor 10.255.0.52 update-source Loopback0      ## Peer from the loopback: the same address as the end of the step 0 road
 !
 address-family vpnv4                              ## L3VPN routes (IPv4 with an RD, and a label)
  neighbor 10.255.0.52 activate
  neighbor 10.255.0.52 send-community both         ## The RT rides in an extended community. If it is not sent, the peer cannot import
 exit-address-family
 !
 address-family l2vpn evpn                         ## EVPN routes (types 1 to 4). Used by both the E-LAN and EVPN-VPWS
  neighbor 10.255.0.52 activate
  neighbor 10.255.0.52 send-community both
 exit-address-family
:::

:::config XR01 (IOS XR) — iBGP to the RR
router bgp 65000
 bgp router-id 10.255.0.1
 address-family vpnv4 unicast                      ## IOS XR first enables the family globally
 !
 neighbor 10.255.0.52
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast                     ## Then per neighbour. iBGP VPNv4 needs no policy
:::

XR01 does not take part in the E-LAN, so it has no `l2vpn evpn` family.

RR1's side is below. It names each PE as a neighbour, and `route-reflector-client` says "pass the routes from here on to the other PEs".
RR1 has no VRF and no `mpls ip`: it only hands out routes and never carries packets (section 3.5 of the previous page).

:::config RR1 (IOS XE) — the route reflector (preinstalled)
router bgp 65000
 bgp router-id 10.255.0.52
 no bgp default ipv4-unicast
 neighbor PE peer-group                            ## A bundle that gives the four PEs the same settings (a peer group)
 neighbor PE remote-as 65000
 neighbor PE update-source Loopback0
 neighbor 10.255.0.1 peer-group PE
 neighbor 10.255.0.41 peer-group PE
 neighbor 10.255.0.42 peer-group PE
 neighbor 10.255.0.43 peer-group PE                ## Adding a PE adds this line and its activate lines below
 !
 address-family vpnv4
  neighbor PE send-community both
  neighbor PE route-reflector-client               ## Pass routes from one client (PE) on to the other clients
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.41 activate
  neighbor 10.255.0.42 activate
  neighbor 10.255.0.43 activate
 exit-address-family
 !
 address-family l2vpn evpn                         ## XR01 is not in the E-LAN, so it is not in this family
  neighbor PE send-community both
  neighbor PE route-reflector-client
  neighbor 10.255.0.41 activate
  neighbor 10.255.0.42 activate
  neighbor 10.255.0.43 activate
 exit-address-family
:::

VPWS (LDP) and VPLS have no such step. The remote PEs are named inside the container in step 2, and a targeted LDP session
is set up automatically with each one you write.

## 4. Steps 2 and 3: the container and the attachment

The container (step 2) and the attachment (step 3) take a different form for each service. Here they are one by one,
in the same writing order.

### 4.1 L3VPN

The container is the VRF. The RD is a value that keeps routes apart per PE; the RT is a tag saying "which VRF this route
belongs to". PEs that export RT 65000:100 and import the same value are members of the same L3VPN.

:::config XE1 (IOS XE) — L3VPN site 1
vrf definition A                                   ## Step 2: the container
 rd 10.255.0.41:100                                ## A different RD per PE (here, "loopback:100")
 address-family ipv4
  route-target export 65000:100                    ## The tag put on this VRF's routes
  route-target import 65000:100                    ## Take in routes that carry this tag
 exit-address-family
!
interface GigabitEthernet2.100                     ## Step 3: the attachment. The subinterface that picks up CE1's VLAN 100
 encapsulation dot1Q 100
 vrf forwarding A                                  ## Put this subinterface in VRF A (before the address)
 ip address 172.16.1.254 255.255.255.0
!
router bgp 65000
 address-family ipv4 vrf A                         ## Step 3: exchange routes with the CE. Routes learned here go out as VPNv4
  neighbor 172.16.1.1 remote-as 65001
  neighbor 172.16.1.1 activate
:::

:::config XR01 (IOS XR) — L3VPN site 4
vrf A                                              ## Step 2: the container. The RTs go under the VRF
 address-family ipv4 unicast
  import route-target
   65000:100
  !
  export route-target
   65000:100
!
interface GigabitEthernet0/0/0/1.100               ## Step 3: the attachment
 vrf A
 ipv4 address 172.16.4.254 255.255.255.0
 encapsulation dot1q 100
!
route-policy PASS                                  ## Without a policy, IOS XR eBGP neither sends nor accepts routes (M5)
  pass
end-policy
!
router bgp 65000
 vrf A
  rd 10.255.0.1:100                                ## On IOS XR the RD goes under BGP (on IOS XE, under the VRF)
  address-family ipv4 unicast
  !
  neighbor 172.16.4.1                              ## Step 3: eBGP with CE4
   remote-as 65004
   address-family ipv4 unicast
    route-policy PASS in
    route-policy PASS out
:::

### 4.2 VPWS (LDP pseudowire)

The container is an xconnect. It holds just two ends: one is the AC (the customer's interface), the other is a pseudowire
to the remote PE. You name the remote PE and the VC ID (the PW ID on IOS XR). The VC ID is the same at both ends.

:::config XE1 (IOS XE) — E-Line from site 1 to site 4
interface GigabitEthernet2
 service instance 130 ethernet                     ## Step 3: the AC. Picks up VLAN 130 frames on this port
  encapsulation dot1q 130
  rewrite ingress tag pop 1 symmetric              ## Remove the tag on the way in and put it back on the way out
!
l2vpn xconnect context CE1-CE4                     ## Step 2: the container (any name)
 member GigabitEthernet2 service-instance 130      ## One end = the AC
 member 10.255.0.1 130 encapsulation mpls          ## The other end = a pseudowire to XR01 (VC ID 130). This is the naming
:::

:::config XR01 (IOS XR) — E-Line from site 4 to site 1
interface GigabitEthernet0/0/0/1.130 l2transport   ## Step 3: the AC. l2transport = used as an AC, not as an L3 interface
 encapsulation dot1q 130
 rewrite ingress tag pop 1 symmetric
!
l2vpn
 xconnect group SVC                                ## Step 2: a name that groups containers (any name)
  p2p CE4-CE1
   interface GigabitEthernet0/0/0/1.130            ## One end = the AC
   neighbor ipv4 10.255.0.41 pw-id 130             ## The other end = a pseudowire to XE1. The PW ID is the same at both ends
:::

### 4.3 VPLS

The container comes in two parts: the VFI (the bundle of pseudowires to the remote PEs) and the bridge domain (one switch
inside the PE). Putting both the AC and the VFI into the bridge domain connects the customer's port and the pseudowires to the same switch.

:::config XE1 (IOS XE) — VPLS site 1
l2vpn vfi context VPLS210                          ## Step 2: the bundle of pseudowires
 vpn id 210                                        ## The VPLS number. The same on every PE (it becomes the pseudowires' VC ID)
 member 10.255.0.42 encapsulation mpls             ## Named: XE2
 member 10.255.0.43 encapsulation mpls             ## Named: XE3. List every other PE
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## Step 3: the AC
  encapsulation dot1q 210
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 210                                  ## Step 2: the switch inside the PE
 member GigabitEthernet2 service-instance 210      ## Step 3: the AC becomes a port on the switch
 member vfi VPLS210                                ## So does the bundle of pseudowires
:::

Because the peers are named, every PE lists every other PE under `member`. Adding one site means adding one line on every existing PE.

### 4.4 EVPN E-LAN

As with VPLS the container is a bridge domain, and in place of the VFI you put in an EVI (EVPN instance). You do not write the
remote PEs. The RT decides membership; if you do not write one, as on this topology, "AS number:EVI" (65000:200) is added automatically.

:::config XE1 (IOS XE) — EVPN E-LAN site 1
l2vpn evpn                                         ## EVPN's global settings (once)
 replication-type ingress                          ## Copy BUM to each remote PE. Without it the EVI stays Incomplete and nothing passes
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## Step 2: the EVI. RD and RT are automatic (10.255.0.41:200, 65000:200)
!
interface GigabitEthernet2
 service instance 200 ethernet                     ## Step 3: the AC
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 200                                  ## Step 2: the switch inside the PE
 member GigabitEthernet2 service-instance 200      ## Step 3: the AC becomes a port on the switch
 member evpn-instance 200                          ## Connect the EVI to the switch (where VPLS has member vfi)
:::

Set next to the VPLS configuration, the only differences are that `member vfi` becomes `member evpn-instance`, the list of
remote PEs disappears, and step 1's BGP is needed instead. Adding a site does not change the existing PEs' configuration.

### 4.5 EVPN-VPWS

This builds an E-Line with BGP. The container is a point-to-point EVI. You do not write the remote PE; you write the numbers
of the two ends (source and target), swapped between the two sides.

:::config XE2 (IOS XE) — EVPN-VPWS from site 2 to site 3
interface GigabitEthernet2
 service instance 140 ethernet                     ## Step 3: the AC
  encapsulation dot1q 140
  rewrite ingress tag pop 1 symmetric
!
l2vpn evpn instance 140 point-to-point             ## Step 2: a point-to-point EVI (RT automatic, 65000:140)
 vpws context CE2-CE3
  service target 3 source 2                        ## My end is 2, the far end is 3. XE3 has "target 2 source 3"
  member GigabitEthernet2 service-instance 140
:::

Compared with the LDP pseudowire (section 4.2), `member 10.255.0.1 130 encapsulation mpls` (naming the remote PE) becomes
`service target 3 source 2` (just the end numbers). Which PE holds end 3 is learned from a BGP type 1 route.

## 5. Step 4: check from the bottom up

When you have finished writing, check from the bottom step up. A problem that shows in an upper step often has its cause in a lower one.

| Step | IOS XE | IOS XR | What to look at |
|---|---|---|---|
| 0 Base | `show mpls forwarding-table <remote Lo> 32` | `show mpls forwarding prefix <remote Lo>/32` | The outgoing label is a number or Pop |
| 1 PE to PE | `show bgp vpnv4 unicast all summary`, `show bgp l2vpn evpn summary` | `show bgp vpnv4 unicast summary` | The RR line is established and the received count is not 0 |
| 2 L3VPN | `show bgp vpnv4 unicast all labels`, `show ip route vrf A` | `show bgp vpnv4 unicast labels`, `show route vrf A` | The remote sites' routes are in the VRF, with labels |
| 2 Named | `show mpls ldp neighbor` (Targeted), `show l2vpn atom vc` | `show l2vpn xconnect` | A targeted session with the remote PE, and the pseudowire UP |
| 2 EVPN | `show l2vpn evpn evi <EVI> detail`, `show l2vpn evpn vpws vc id <EVI> detail` | — | The remote PEs on the Peers lines, State Established |
| 3 Attach | `show bgp vpnv4 unicast vrf A summary`, `show bridge-domain <BD>` | `show l2vpn xconnect detail` | eBGP with the CE, the AC up, the remote MACs |
| End to end | Ping from the CE to the remote site | | |

## 6. When it stops: where to look

These are mistakes actually made in earlier units, sorted by the step where they stop things. Each shows up in that step's output.

| Step | Missing or mismatched | How it shows | Measured in |
|---|---|---|---|
| 0 | No label on the road to the remote PE | L3VPN keeps its routes but nothing passes. The pseudowire goes down (`DN` on IOS XR, `pw-tx-fault` from the peer on IOS XE) | This page's topology |
| 2 | An L3VPN RT import that does not match the other side's export | Only the PE with the wrong import lacks the remote routes in its VRF. The other side has them, so routes show on one side and nothing gets through | This page's topology |
| 2 | No `replication-type ingress` for EVPN | The EVI stays `State: Incomplete` and nothing passes | M11 add-on |
| 2 | A mistyped VPLS VPN ID | That PE's pseudowires do not come up (the peer's label never arrives) | M11 add-on |
| 2 | Swapped EVPN-VPWS target | The two sides disagree, for example one side looks UP | M11 |
| 3 | No `route-policy` on IOS XR eBGP | The session with the CE comes up, but no routes are sent or accepted | M5, M6 |
| 3 | A forgotten `rewrite` on the AC (IOS XR LDP pseudowire) | The AC MTU becomes 1504 and it goes down with `Error: MTU mismatched` | M11 |
| 3 | A forgotten `rewrite` on the AC (VPLS) | The pseudowires are UP, but only that site cannot reach anyone | M11 add-on |

How a forgotten `rewrite` shows depends on the service and the OS. Sometimes it goes down and you notice; sometimes it stays UP
and nothing passes. When something is up but nothing passes, suspect the tag handling on the AC in step 3 first.

## 7. IOS XE and IOS XR side by side

| Step | IOS XE | IOS XR |
|---|---|---|
| 1 | `router bgp` → `address-family vpnv4` → `neighbor … activate` | `router bgp` → `address-family vpnv4 unicast` (global) → `neighbor` → `address-family vpnv4 unicast` |
| 2 L3VPN | `vrf definition A` → `rd`, `route-target` | `vrf A` → `import/export route-target`. The RD is under `router bgp` → `vrf A` → `rd` |
| 3 L3VPN | `vrf forwarding A` on the subinterface. The CE neighbour under `address-family ipv4 vrf A` | `vrf A` on the subinterface. `router bgp` → `vrf A` → `neighbor`; eBGP needs a `route-policy` |
| 2 VPWS | `l2vpn xconnect context` → `member <peer> <VC ID> encapsulation mpls` | `l2vpn` → `xconnect group` → `p2p` → `neighbor ipv4 <peer> pw-id <ID>` |
| 3 L2 | `service instance <n> ethernet` → `encapsulation dot1q`, `rewrite` | `interface <IF>.<n> l2transport` → `encapsulation dot1q`, `rewrite` |
| 2 E-LAN | `bridge-domain` → `member vfi` / `member evpn-instance` | The IOS XRv 9000 on this topology cannot use bridge domains (M11 appendix) |
