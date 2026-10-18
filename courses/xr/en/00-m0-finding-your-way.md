# M0 — Finding Your Way

This unit is for an engineer who is fluent on IOS and IOS XE and is sitting in front of IOS XR for the first time.
It does not teach OSPF, VRFs or static routing. You know those. It teaches where IOS XR keeps them,
how to look at them, and how to find a command you have never typed.

Everything shown here was captured on IOS XRv 9000 release 24.3.1.

## 1. What you are logged in to

```console
RP/0/RP0/CPU0:XR01#
```

The prompt is a location followed by the host name. `0/RP0/CPU0` is rack 0, the route processor in slot RP0,
CPU instance 0. On a chassis with line cards, log messages from a card carry the card's own location:

```console
LC/0/0/CPU0:Oct 12 13:43:16.484 UTC: ifmgr[239]: %PKT_INFRA-LINK-3-UPDOWN : Interface GigabitEthernet0/0/0/0, changed state to Up
RP/0/RP0/CPU0:Oct 12 13:44:12.701 UTC: ospf[1039]: %ROUTING-OSPF-5-ADJCHG : Process 1, Nbr 2.2.2.2 on GigabitEthernet0/0/0/0 in area 0 from LOADING to FULL, Loading Done
```

Read those two lines again. The first comes from a process called `ifmgr` running on the line card.
The second comes from a process called `ospf` running on the route processor. The numbers in brackets are process IDs.

That is the main structural difference from IOS. IOS is one program. IOS XE is that same program (IOSd) running
as a process on Linux. IOS XR is a set of separate processes on a Linux kernel — one for OSPF, one for BGP,
one for the interface manager, one for each configuration session — spread across the route processor and the line cards.
Much of what feels unfamiliar on the command line follows from that.

There is no `enable`. What you may do is decided by the task groups your user belongs to, at login.

## 2. Interface names and their default state

Physical interfaces are named *type rack/slot/module/port*:

```console
RP/0/RP0/CPU0:XR01#show ipv4 vrf all interface brief

Interface                      IP-Address      Status          Protocol Vrf-Name
Loopback0                      1.1.1.1         Up              Up       default
MgmtEth0/RP0/CPU0/0            10.1.10.17      Up              Up       MGMT
GigabitEthernet0/0/0/0         10.0.12.1       Up              Up       default
GigabitEthernet0/0/0/1         10.0.13.1       Up              Up       CUST-A
GigabitEthernet0/0/0/2         10.0.21.1       Up              Up       default
```

Three things to notice.

- The management port is an interface of the route processor, so it is named after the route processor's location:
  `MgmtEth0/RP0/CPU0/0`.
- IPv4 and IPv6 have separate commands: `show ipv4 interface brief` and `show ipv6 interface brief`.
  The IOS spelling `show ip interface brief` is still accepted, but the CLI itself describes `ip` as
  "Deprecated, use ipv4 instead". Use the `ipv4` and `ipv6` forms.
- An administratively disabled interface shows `Shutdown` in the Status column.

A physical interface that has never been configured is administratively down, and the running configuration
says so with an explicit `shutdown` line. When you bring it up, the line disappears:

```console
interface GigabitEthernet0/0/0/2
 description LINK2 to RT01
 ipv4 address 10.0.21.1 255.255.255.0
!
```

There is no `no shutdown` in that output, and the interface is up. On IOS XR the `shutdown` line exists only while
the interface is disabled. Its absence means up.

Addresses are written with the address family first: `ipv4 address 10.0.21.1 255.255.255.0` (or `10.0.21.1/24`),
`ipv6 address 2001:db8:12::1/64`.

## 3. The configuration is a tree, and protocols own their interfaces

On IOS, an interface is where most things meet: `ip ospf 1 area 0`, `ip ospf cost`, `vrf forwarding`, and so on,
all under `interface`. On IOS XR the interface block holds only what belongs to the interface itself —
addresses, description, VRF membership, encapsulation. Everything a routing protocol needs to know about that interface
is written under the protocol.

This is OSPF on XR01:

```console
RP/0/RP0/CPU0:XR01#show running-config router ospf
router ospf 1
 router-id 1.1.1.1
 area 0
  interface Loopback0
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/2
   cost 50
   network point-to-point
  !
 !
!
```

- There are no `network` statements. An interface runs OSPF because it is listed under an area.
- Per-interface OSPF settings (`cost`, `network point-to-point`, authentication) are written under that entry,
  not under `interface GigabitEthernet…`.
- A setting written at a higher level is inherited by everything below it. Cisco's configuration guide puts it
  this way for the hello interval: the value configured at the interface level is used; otherwise the value
  at the area level; otherwise the value at the `router ospf` level; otherwise the default.
  The same applies to authentication, network type and most other interface parameters.

Static routes follow the same idea. They are not scattered `ip route` lines. There is one `router static` block,
divided by VRF and address family:

```console
RP/0/RP0/CPU0:XR01#show running-config router static
router static
 address-family ipv4 unicast
  0.0.0.0/0 10.0.12.2
 !
 vrf CUST-A
  address-family ipv4 unicast
   172.16.2.0/24 10.0.13.2
  !
 !
!
```

A VRF is declared at the top level with the address families it carries, and an interface joins it with a single
line under the interface:

```console
vrf CUST-A
 address-family ipv4 unicast
 !
!
interface GigabitEthernet0/0/0/1
 description CUST-A to RT02
 vrf CUST-A
 ipv4 address 10.0.13.1 255.255.255.0
!
```

:::note
On IOS, `vrf forwarding` removes the IP address from the interface and you have to put it back.
On this release of IOS XR, moving an addressed interface into a VRF kept the address. Do not rely on either memory.
Look at the result.
:::

## 4. Looking at part of the configuration

Because the configuration is a tree, you can ask for a branch of it. You have already seen two examples.
The pattern is `show running-config` followed by the same words you would type to get there in configuration mode:

```console
RP/0/RP0/CPU0:XR01#show running-config interface GigabitEthernet0/0/0/1
RP/0/RP0/CPU0:XR01#show running-config router ospf
RP/0/RP0/CPU0:XR01#show running-config router static
RP/0/RP0/CPU0:XR01#show running-config vrf CUST-A
```

Asking for something that is not configured is not an error in your typing:

```console
RP/0/RP0/CPU0:XR01#show running-config interface Loopback11
% No such configuration item(s)
```

Output modifiers work as on IOS (`| include`, `| exclude`, `| begin`). One difference will catch you on the first day:
a regular expression that contains `|` must be quoted, because an unquoted `|` starts another modifier.

```console
RP/0/RP0/CPU0:XR01#show version | include Version|uptime
                                                  ^
% Invalid input detected at '^' marker.
RP/0/RP0/CPU0:XR01#show version | include "Version|uptime"
Cisco IOS XR Software, Version 24.3.1
 Version      : 24.3.1
System uptime is 18 minutes
```

`| utility` gives a few UNIX tools (`egrep`, `wc`, `head`, `tail`, …) and `| file` saves the output.

Inside configuration mode, `show running-config …` shows what is running and plain `show configuration`
shows what you have typed but not yet applied. The second one matters, because of the next section.

## 5. Nothing happens until you commit

On IOS each line takes effect when you press Enter. On IOS XR the lines you type in configuration mode go into
a separate, private copy — the *target configuration*. The router keeps running its old configuration until you say
`commit`. Then all your lines are applied together.

```console
RP/0/RP0/CPU0:XR01(config)#interface Loopback12
RP/0/RP0/CPU0:XR01(config-if)#ipv4 address 12.12.12.12 255.255.255.255
RP/0/RP0/CPU0:XR01(config-if)#show configuration
!! Building configuration...
!! IOS XR Configuration 24.3.1
interface Loopback12
 ipv4 address 12.12.12.12 255.255.255.255
!
end
RP/0/RP0/CPU0:XR01(config-if)#commit
```

Until that last line, Loopback12 does not exist. This is the single most common reason for
"I configured it and nothing happened" on a first day with IOS XR.

There is no `write memory`. A committed change is already saved.

`abort` leaves configuration mode and throws away what you had typed. `end` leaves configuration mode too,
but if there are uncommitted lines it asks what to do with them first:

```console
RP/0/RP0/CPU0:XR01(config-if)#end
Uncommitted changes found, commit them before exiting(yes/no/cancel)? [cancel]:
```

`do` runs an EXEC command from configuration mode, as on IOS.

Unit M1 is about what this model lets you do. For now, remember two commands: `show configuration` and `commit`.

## 6. The routing table

```console
RP/0/RP0/CPU0:XR01#show route

Gateway of last resort is 10.0.12.2 to network 0.0.0.0

S*   0.0.0.0/0 [1/0] via 10.0.12.2, 00:04:44
L    1.1.1.1/32 is directly connected, 00:14:53, Loopback0
O    2.2.2.2/32 [110/2] via 10.0.12.2, 00:04:38, GigabitEthernet0/0/0/0
C    10.0.12.0/24 is directly connected, 00:04:44, GigabitEthernet0/0/0/0
L    10.0.12.1/32 is directly connected, 00:04:44, GigabitEthernet0/0/0/0
C    10.0.21.0/24 is directly connected, 00:14:53, GigabitEthernet0/0/0/2
L    10.0.21.1/32 is directly connected, 00:14:53, GigabitEthernet0/0/0/2
B    198.51.100.0/24 [20/0] via 10.0.12.2, 00:04:12
```

- (The legend of route codes and a few loopback routes are left out above.) The command is `show route`.
  Add `vrf <name>` for a VRF, `ipv6` for IPv6, or a protocol name (`show route ospf`) to filter.
- `L` is the router's own address on a connected network, listed separately as a /32.
- A specific prefix gives the detail, including which process installed it:

```console
RP/0/RP0/CPU0:XR01#show route 0.0.0.0/0

Routing entry for 0.0.0.0/0
  Known via "static", distance 1, metric 0, candidate default path
  Installed Oct 12 13:44:48.794 for 00:00:05
  Routing Descriptor Blocks
    10.0.12.2
      Route metric is 0
  No advertising protos.
RP/0/RP0/CPU0:XR01#show route 9.9.9.9/32

% Network not in table
```

Protocol commands drop the `ip` as well: `show ospf neighbor`, `show ospf interface brief`, `show bgp summary`.

```console
RP/0/RP0/CPU0:XR01#show ospf interface brief

Interfaces for OSPF 1

Interface          PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0                1     0               1.1.1.1/32         1     LOOP  0/0
Gi0/0/0/0          1     0               10.0.12.1/24       1     P2P   1/1
Gi0/0/0/2          1     0               10.0.21.1/24       50    P2P   1/1
```

## 7. Finding a command you do not know

You will not be given commands in the practice tasks. This is how to find them.

**Ask the CLI.** `?` works at every level and lists what is valid *at that point in the tree*.
If a keyword you expect is missing, you are probably at the wrong level — which, given section 3, is the usual mistake.
`show running-config ?` lists the branches you can ask for.

**Start from what is there.** Before changing a feature, display its branch of the running configuration.
The existing lines show you the hierarchy and the spelling.

**Use the right book.** Cisco publishes IOS XR documentation per platform. IOS XRv 9000 uses the ASR 9000 series
documents. There are two kinds, and they answer different questions.

| Document | Use it when |
|---|---|
| Configuration guides (Routing, Interface and Hardware Component, MPLS, L3VPN, System Security, …) | you know what you want to achieve and need the procedure and the concepts |
| Command references (same volumes) | you know the command and need its syntax, defaults and modes |

- Configuration guides: <https://www.cisco.com/c/en/us/support/routers/asr-9000-series-aggregation-services-routers/products-installation-and-configuration-guides-list.html>
- Command references: <https://www.cisco.com/c/en/us/support/routers/asr-9000-series-aggregation-services-routers/products-command-reference-list.html>

Chapters you will want in this unit: *Implementing OSPF* and *Implementing Static Routes* (Routing Configuration Guide),
*Configuring Ethernet Interfaces* (Interface and Hardware Component Configuration Guide).

## 8. From IOS to IOS XR — the first few translations

| You would type on IOS | On IOS XR |
|---|---|
| `enable` | nothing — privileges come from your user's task groups |
| `show ip interface brief` | `show ipv4 interface brief` / `show ipv6 interface brief` (the `ip` form is deprecated) |
| `show ip route` | `show route` (`vrf <name>`, `ipv6`, `ospf`, …) |
| `show … \| include a\|b` | `show … \| include "a\|b"` |
| `show ip ospf neighbor` | `show ospf neighbor` |
| `ip address 10.0.0.1 255.255.255.0` | `ipv4 address 10.0.0.1 255.255.255.0` |
| `interface …` / `ip ospf 1 area 0` | `router ospf 1` / `area 0` / `interface …` |
| `ip route 0.0.0.0 0.0.0.0 10.0.12.2` | `router static` / `address-family ipv4 unicast` / `0.0.0.0/0 10.0.12.2` |
| `vrf definition X` + `vrf forwarding X` | `vrf X` + `vrf X` under the interface |
| *(each line applies immediately)* | `commit` |
| `write memory` | nothing — a commit is saved |

## Practice

Open lab **XRT-01** in the workspace and do the M0 tasks. XR01 has been left half-configured.
Work out what is there before you change it.
