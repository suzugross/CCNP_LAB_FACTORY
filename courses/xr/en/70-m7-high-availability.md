# M7 — High availability

A provider network is expected to keep forwarding while parts of it fail or restart. This unit covers four tools
that IOS XR offers for that, and the IS-IS side of each: link bundles, BFD, the overload bit, and restarting a
routing process without loss (graceful restart, NSF and NSR). In the CCNP Service Provider blueprint this is
section 2.8.

The outputs on this page were captured on IOS XRv 9000 26.1.1, with a Catalyst 8000V (IOS XE 17.15) and an IOS XE
17.15 router on IOL as neighbours (lab XRT-06). Times in seconds are measured in that lab, not guaranteed values.

## 1. Link bundles

### 1.1 Bundles on IOS XR

IOS XR calls a link aggregation group a **bundle**. The logical interface is `Bundle-Ether<n>`, and a physical
interface joins it with `bundle id <n>` under its own configuration. The addresses, the MTU and the routing protocols
belong to the bundle interface; the members carry no Layer 3 configuration.

The `mode` keyword of `bundle id` decides how the member is negotiated:

| Mode | Behaviour |
|---|---|
| `active` | runs LACP and sends LACPDUs on its own |
| `passive` | runs LACP but only answers a partner that sends LACPDUs |
| `on` | no LACP: the member is used as soon as its port is up |

`mode on` is also what you get when you leave the keyword out: `show running-config` then shows `bundle id 1 mode on`.
A static member trusts its port state alone. If the other end runs LACP, it waits for LACPDUs that never come and keeps
its own members out of the group, while the static end sends traffic into them:

```console
RP/0/RP0/CPU0:XR01#show bundle Bundle-Ether1
  Status:                                    Up
  Local links <active/standby/configured>:   2 / 0 / 2
  LACP:                                      Not operational
  Gi0/0/0/0             Local            Active       0x8000, 0x0000     1000000
  Gi0/0/0/1             Local            Active       0x8000, 0x0000     1000000

RT01#show etherchannel summary
1	Po1(RD)		LACP	 Gi1(susp) Gi2(susp)
```

The bundle looks healthy from XR01 and carries nothing. Two passive ends never start LACP either; both sides then
stay down. The Catalyst 8000V in the lab knows only `active` and `passive` for its routed port channel, and does not
let you change the mode of a member in place: the member has to leave the channel group first.

### 1.2 How LACP notices a failed member

A member can fail without its port going down: a fault inside a transport network, or a far end that is shut down
behind a converter. Only LACP can see that. Each end sends LACPDUs at a rate that its partner asks for, and drops a
member when three of them in a row are missing:

| Partner asks for | LACPDU every | Member leaves after |
|---|---|---|
| slow (the default) | 30 s | 90 s |
| fast | 1 s | 3 s |

On IOS XR, `lacp period short` under the member asks the partner for the fast rate; the `F` flag in the actor state of
`show lacp` shows that the request is made. In the lab, XR01 took 72 seconds to drop a member whose far end was shut
with the slow rate, and less than six seconds with `lacp period short`.

`bundle minimum-active links <n>` under the bundle sets how many members must be in use for the bundle to come up.
Below that number the whole bundle goes down, the remaining members go to standby, and the routing protocols move the
traffic elsewhere:

```console
RP/0/RP0/CPU0:XR01#show bundle Bundle-Ether1
  Status:                                    Down
  Local links <active/standby/configured>:   0 / 1 / 2
  Minimum active links / bandwidth:          2 / 1 kbps
  Gi0/0/0/0             Local            Standby      0x8000, 0x0001     1000000
  Gi0/0/0/1             Local            Configured   0x8000, 0x0002     1000000
```

Without the minimum, the bundle stays up on one member at half the bandwidth, which is the right choice only when
half the bandwidth is enough. A minimum is set on each end separately; in a real network both ends should agree.

### 1.3 MTU on IOS XR

The `mtu` command of IOS XR counts the Layer 2 header. An Ethernet interface or bundle has an MTU of 1514 by default,
of which 1500 is available to IP. IOS counts only the Layer 3 part, so the same number means different things on the
two sides:

```console
RP/0/RP0/CPU0:XR01#show ipv4 interface Bundle-Ether1 | include MTU
  MTU is 1500 (1486 is available to IP)
```

IS-IS notices the difference at once, because it pads its hellos to the full MTU of the interface. A neighbour with a
smaller MTU drops the padded hellos, so the adjacency comes up on one side only:

```console
RP/0/RP0/CPU0:XR01#show isis interface Bundle-Ether1
  Last PDU Rejected:        13:57:29 (3.75 sec ago), 1496 octets, P2P IIH, PDU larger than our MTU
    MTU:                    1483 (MTU is too small: L2 lsp-mtu is 1492)

RT01#show clns neighbors
XR01            Po1           0003.a004.5331      Init   22        L2   IS-IS
```

The padding exists to find exactly this mismatch. It can be turned off (`hello-padding disable` on IOS XR), but in the
lab that changed nothing: the hellos that XR01 rejected were RT01's, padded by RT01. And wherever an adjacency is
brought up that way, the mismatch stays: LSPs and IP packets larger than the smaller MTU are still lost.

## 2. BFD

### 2.1 What BFD adds

An IGP finds a dead neighbour when its hellos stop: IS-IS on IOS XR declares the adjacency down after 30 seconds by
default. BFD (RFC 5880) is a separate, light hello protocol between two interfaces, run at intervals of milliseconds,
and it tells the routing protocols that use it when the path is gone. The time to detect a failure is the remote
multiplier times the agreed interval, and each direction can have its own value.

For a single-hop session (RFC 5881) IOS XR uses the **echo** function when the neighbour supports it: XR01 sends
packets addressed to itself, the neighbour forwards them back, and the slow asynchronous packets only keep the session
alive. `show bfd session` shows both values:

```console
RP/0/RP0/CPU0:XR01#show bfd session
Interface           Dest Addr           Local det time(int*mult)      State
                                    Echo             Async   H/W   NPU
------------------- --------------- ---------------- ---------------- ----------
Gi0/0/0/2           10.0.2.12       300ms(100ms*3)   6s(2s*3)         UP
```

After a session has gone down, IOS XR holds it back for a while before it comes up again (dampening, starting at
2 seconds and growing with each flap). `show bfd session` then shows `DOWN DAMP`.

### 2.2 BFD for IS-IS on IOS XR

On IOS XR, BFD for a routing protocol is configured in the protocol, not on the interface: under the interface in
`router isis`, `bfd fast-detect ipv4` starts the session, and `bfd minimum-interval` and `bfd multiplier` set the
timers (150 ms and 3 by default). IOS sets the timers on the interface with `bfd interval` and then enables BFD for
IS-IS with `isis bfd` or `bfd all-interfaces`.

In the lab, a silent failure of the primary path (the ports at both ends stayed up and every packet was discarded)
stopped the traffic for 22 seconds without BFD and for one second with BFD at 100 ms × 3. XR01 logged the reason:

```console
%L2-BFD-6-SESSION_STATE_DOWN : BFD session to neighbor 10.0.2.12 on interface GigabitEthernet0/0/0/2 has gone down. Reason: Echo function failed
%ROUTING-ISIS-5-ADJCHANGE : ISIS (CORE): Adjacency to RT02 (GigabitEthernet0/0/0/2) (L2) Down, BFD session DOWN
```

A router that enables BFD for IS-IS also says so in its hellos (the BFD-enabled TLV, RFC 6213). When both ends do,
IOS XR treats BFD as required and holds the adjacency in **Init** until the BFD session is up:

```console
RP/0/RP0/CPU0:XR01#show isis adjacency detail
RT01           BE1                      *PtoP*         Init  25   not up   Yes Init None
  Topology (not running): [IPv4 Unicast (BFD is down)]
  BFD Status:             Neighbor Not Useable (BFD Required)
```

If the neighbour does not announce the TLV, the adjacency comes up with BFD down (`BFD Configured, but Not Required`).
A neighbour that announces the TLV but has no BFD timers on the interface therefore keeps the adjacency in Init for
good.

### 2.3 BFD and bundles

On a bundle, BFD can run in two ways. **BFD over bundle members** (BoB, RFC 7130) runs one session on each member
link (UDP port 6784), configured under the bundle interface, and removes a member whose session fails. **BFD over the
logical bundle** (BLB) is what a routing protocol starts when BFD is enabled for it on a bundle interface: one session
for the bundle as a whole. On IOS XRv 9000 a BLB session needs `bfd multipath include location` under `bfd`; without
it XR01 logs `No resources for session … on interface Bundle-Ether1`.

Both need a neighbour that runs BFD on its port channel. The Catalyst 8000V in the lab does not, so XRT-06 uses BFD
only on the primary link and leaves the bundle to LACP. With BoB configured against a neighbour that does not answer,
the members wait for the session indefinitely and the bundle stays as it was.

## 3. The overload bit

### 3.1 What it does

Every LSP carries an **overload** (OL) bit. Other routers do not use an overloaded router for transit, but they still
reach the prefixes that it advertises itself (ISO 10589, RFC 3787). `show isis database` shows the bit in the
`ATT/P/OL` column:

```console
RP/0/RP0/CPU0:XR01#show isis database
XR01.00-00          * 0x00000018   0xff94        1188 /*            0/0/1
```

`set-overload-bit` under `router isis` sets the bit until it is removed. That is how a router is taken out of the
transit path before maintenance without losing access to it: in the lab, RT01 sent the traffic for RT02 over the
backup link at once and still reached XR01's loopback over the bundle. A bit left set after the work keeps the router
out of every path, with no alarm.

### 3.2 At start-up

A router that has just started has an incomplete database and, if it runs BGP, an incomplete BGP table; traffic that
it attracts too early is lost. `set-overload-bit on-startup <seconds>` sets the bit for the given time after the
process starts, and `set-overload-bit on-startup wait-for-bgp` until BGP signals that it has converged.
`show isis protocol` shows which one is configured and whether the bit is set now:

```console
  Overload Bit Level-2: configured, clear
      on startup until BGP converges
```

The same command keyword holds all three forms, so a router has only one of them at a time. The lab measured when
the bit is actually set:

| Start of the process | OL bit in the LSP |
|---|---|
| cold start, no overload configured | about 10 seconds, until the database is complete |
| cold start, `on-startup 60` | about 60 seconds |
| `clear isis process`, `on-startup 60` | not set |
| NSF restart (section 4.2), `on-startup 60` | not set (`show isis protocol` shows `set`, the LSP does not) |

A process restart without NSF counts as a cold start. With NSF configured, a process restart no longer sets the bit;
the start-up overload is then left for cold starts, such as a reload of the whole router (not measured in the lab).

## 4. Restarting without loss

### 4.1 Processes on IOS XR

M0 showed that the routing protocols of IOS XR are separate processes. Each runs in its own protected memory and can
be restarted without restarting the others: `process restart isis` or `process restart bgp` in EXEC mode, and
`show processes isis` shows when it last started. A crash ends the same way, with the process started again by the
system manager. What the neighbours see depends on what the process does when it comes back.

Without any preparation, a restarted IS-IS process starts from nothing: it sends hellos that do not list its
neighbours, and the neighbours drop the adjacency (RT01 logged `Down, neighbor forgot us`) and form it again two
seconds later. The traffic through the router stops for that time.

### 4.2 IS-IS NSF

**Non-stop forwarding** keeps the forwarding table in the line cards while the control plane restarts, and lets the
restarting router rebuild its state without the neighbours noticing. IOS XR has two forms for IS-IS, selected with
`nsf` under `router isis`:

| Form | How the state is rebuilt | Needs the neighbours to |
|---|---|---|
| `nsf ietf` | the restarting router signals the restart in its hellos (RFC 8706, formerly RFC 5306) and the neighbours resend their databases | support the restart signalling (helper) |
| `nsf cisco` | the router restores state that it saved before the restart | nothing |

IOS and IOS XE act as IETF helpers without configuration. With `nsf ietf` on XR01, a process restart looked like this,
and neither RT01 nor RT02 logged an adjacency change:

```console
%ROUTING-ISIS-6-INFO_STARTUP_START : ISIS (CORE): IETF NSF controlled start beginning
%ROUTING-ISIS-5-ADJCHANGE : ISIS (CORE): Adjacency to 49.0001.0100.0000.0011 (Bundle-Ether1) (L2) Up, NSF Restart
%ROUTING-ISIS-6-INFO_STARTUP_FINISH : ISIS (CORE): IETF NSF controlled start completed
```

With `nsf cisco` the neighbours saw nothing either; XR01 logged `Cisco NSF controlled start` and the adjacencies
`Restored during NSF`. `show isis protocol` names the kind of the last start (`Most recent startup mode: IETF NSF
Restart` or `Cold Restart`). XR01's own adjacency table counts the uptime from the restart either way; the neighbours' logs are
where to look.

### 4.3 BGP graceful restart

BGP graceful restart (RFC 4724) does for BGP what NSF does for IS-IS. The restarting router keeps forwarding; its
peers keep the routes learned from it, mark them stale, and replace them when the session is back and the peer has
sent its table again (End-of-RIB). On RT02 the stale routes carry an `S`:

```console
RT02#show ip bgp | begin Network
     Network          Next Hop            Metric LocPrf Weight Path
 S>i  10.30.0.0/16     10.255.0.1               0    100      0 i
```

Without graceful restart on both sides, RT02 dropped the route for about five seconds (`% Subnet not in table`).

Graceful restart is a capability exchanged in the OPEN message, so it takes effect only for sessions opened after it
was configured: `bgp graceful-restart` under `router bgp` on IOS XR, the same command on IOS. Until the session is
reset (`clear bgp <neighbour>` on IOS XR), the neighbour still shows `Graceful-Restart is disabled` or only
`advertised`; when it works, IOS shows
`Graceful Restart Capability: advertised and received`. The restart time (120 seconds by default) bounds how long
the peers wait for the session, and the stale-path time (360 seconds) how long they keep the stale routes.

### 4.4 NSR

**Non-stop routing** goes further: a standby route processor keeps a synchronized copy of the protocol state,
including the TCP sessions of BGP, and takes over without the neighbours being involved at all. It needs two route
processors. `nsr` under `router isis` or `router bgp` is accepted on IOS XRv 9000, but with one route processor the
state stays `Not Ready`, and a process restart is still handled by NSF. BGP NSR was already enabled by default on this
release (`show bgp process` shows `Non-stop routing is enabled`), although the documents disagree about the default.

| Event | Protected by |
|---|---|
| a process restarts or crashes | NSF / graceful restart |
| the active route processor fails | NSR (and NSF as a fallback) |

## 5. Command names

| On IOS | On IOS XR |
|---|---|
| `channel-group <n> mode active` on the member | `bundle id <n> mode active` on the member |
| `interface Port-channel<n>` | `interface Bundle-Ether<n>` |
| `lacp rate fast` on the member | `lacp period short` on the member |
| `lacp min-bundle <n>` on the port channel | `bundle minimum-active links <n>` on the bundle |
| `show etherchannel summary`, `show lacp neighbor` | `show bundle`, `show lacp` |
| `mtu`, `ip mtu` (header not included) | `mtu` (Layer 2 header included) |
| `bfd interval … min_rx … multiplier …` on the interface + `isis bfd` | `bfd fast-detect ipv4`, `bfd minimum-interval`, `bfd multiplier` under the interface in `router isis` |
| `show bfd neighbors` | `show bfd session` |
| `set-overload-bit [on-startup …]` under `router isis` | `set-overload-bit [on-startup {<seconds> \| wait-for-bgp}]` under `router isis` |
| `nsf ietf` under `router isis` | `nsf {ietf \| cisco}` under `router isis` |
| `bgp graceful-restart` | `bgp graceful-restart` |

## Practice

Go to lab **XRT-06** and do the M7 tasks. The lab uses IOS XRv 9000, which takes about ten minutes to build.

<p class="tolab"><a href="/_learn?id=XRT-06">Open lab XRT-06 in the workspace</a> — <a href="71-m7-practice.html">The tasks</a></p>

:::note
Sources: the IOS XR *Interface and Hardware Component* configuration guide and command reference, "Configuring Link
Bundling" (modes and the default `on`, `bundle minimum-active links`, `lacp period short`), the XRv 9000 release notes
(the LACP period of 200 ms at the least, BFD over logical bundles), the technical note "MTU Behavior on Cisco IOS XR
and Cisco IOS Routers" and the IS-IS command reference (hello padding); the IOS XR *Routing* configuration guide and
command reference, "Implementing BFD" and "Implementing IS-IS" (BFD timers and defaults, BoB, BLB and
`bfd multipath include location`, `set-overload-bit` and its start-up forms, NSF, NSR on dual route processors only),
the IOS XR *BGP* configuration guide and command reference (graceful restart and its timers, BGP NSR) and the IOS XE
17.x guides (NSF awareness, BGP graceful restart, BFD), checked October 2026; RFC 5880, 5881, 7130, 6213, 3787, 4724
and 8706. The following come from measurement in lab XRT-06: the static bundle that shows up, the detection times of
LACP, the MTU messages, the BFD times and the Init state, the overload bit at start-up, the messages of an NSF restart,
the stale routes on RT02, NSR in the `Not Ready` state, and the default of BGP NSR.
:::
