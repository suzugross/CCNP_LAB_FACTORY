# M2 — Securing the Management Plane

Every router you have hardened on IOS had the same questions to answer: who may log in, with which rights,
from where, and how much traffic aimed at the router itself it will take. IOS XR asks the same questions.
The answers are built differently, and two of them — rights and traffic to the router — are already in place
before you configure anything.

Everything shown here was captured on IOS XRv 9000 release 24.3.1.

## 1. Rights are task IDs

IOS gives a user a privilege level from 0 to 15 and maps commands onto levels. IOS XR has no levels.
Every command belongs to one or more **task IDs** — `ospf`, `rib`, `interface`, `aaa`, `bgp` and about a hundred more —
and a user holds each task ID with some of four permissions: read, write, execute, debug.

The pieces fit together in three layers:

| Layer | Holds |
|---|---|
| **task group** | task IDs with their permissions (it can also include other task groups) |
| **user group** | task groups (and other user groups) |
| **user** | membership of one or more user groups |

A set of predefined user groups covers the common cases — `root-lr`, `netadmin`, `sysadmin`, `operator`,
`cisco-support`, `read-only-tg` and others. The lab account you log in with is in `root-lr` and `cisco-support`.

`show user tasks` lists what the current session may do. For an account built for monitoring it reads:

```console
RP/0/RP0/CPU0:XR01#show user tasks
Task:       basic-services  : READ    WRITE    EXECUTE
Task:            interface  : READ             EXECUTE
Task:                 ospf  : READ
Task:                  rib  : READ
```

### Which task does a command need?

You do not have to guess. `describe` followed by a command line tells you which task IDs that command needs,
without running it:

```console
RP/0/RP0/CPU0:XR01#describe show route
The command is defined in ip_rib_cmds.parser

User needs ALL of the following taskids:

	rib (READ)
```

The answer depends on who asks. Run as the lab account, `describe ping 10.0.12.2` lists
`root-system (EXECUTE)` and `basic-services (READ WRITE EXECUTE)`. Run as the monitoring account above, the same
command lists only `basic-services`, and the ping works. `root-system` cannot be put into a task group at all.
When you build an account, check its commands while logged in as that account.

### What a missing right looks like

An exec command outside the user's tasks is refused outright:

```console
RP/0/RP0/CPU0:XR01#show route
% This command is not authorized
```

Configuration mode is different. The user can enter it, but every line is refused, so there is never anything to commit:

```console
RP/0/RP0/CPU0:XR01(config)#router ospf 1
% This command is not authorized
RP/0/RP0/CPU0:XR01(config)#commit
No configuration changes to commit.
```

`show running-config` does not fail at all. It shows the parts the user may read and leaves the rest out. The
monitoring account sees every interface by name and description, but no address, and the whole OSPF process:

```console
interface GigabitEthernet0/0/0/0
 description LINK1 to RT01
!
router ospf 1
 router-id 1.1.1.1
 area 0
  ...
```

Nothing tells the user that anything was left out. Keep that in mind when someone sends you a configuration
that "has no addresses".

## 2. Where management sessions are accepted

On IOS you limit management access line by line: an `access-class` on the VTY lines, `transport input` per line.
IOS XR has a feature for the whole router instead: **Management Plane Protection (MPP)**.

- While no MPP configuration exists, every management protocol that is enabled is accepted on every interface.
- As soon as any interface is configured under MPP, a protocol is accepted only on the interfaces where it is allowed.
  All other interfaces drop it.
- Interfaces come in two kinds: **out-of-band** (management interfaces; the VRF is named here too) and **inband**
  (interfaces that also carry data traffic). Each entry allows a protocol, optionally only from listed peers.

The effect is visible in the table of local listeners, `show lpts bindings brief` (section 4 explains LPTS).
Before MPP, the SSH and Telnet servers listen on any interface:

```console
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   any          any,22 any
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   any          any,23 any
 0/RP0/CPU0 TCP        LR IPV4 TCP    MGMT      any          any,22 any
```

With SSH allowed only on the management interface and Telnet only on one data interface from one peer:

```console
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   Gi0/0/0/0    any,23 2.2.2.2
 0/RP0/CPU0 TCP        LR IPV4 TCP    MGMT      Mg0/RP0/CPU0/0 any,22 any
```

A Telnet from any other source now gets `% Connection refused by remote host`. `show mgmt-plane` lists the
same configuration by interface.

### Do not lock yourself out

MPP is the first feature in this track that can cut off the session you are typing in. This is what
`commit confirmed` (M1) is for. One more detail from the lab:

- If you **leave configuration mode** while a confirmed commit is pending, it is rolled back at once (M1).
- If the **session drops** instead — you lock yourself out — the trial stays in place until the timer runs out,
  and then rolls back. Meanwhile **no other session can commit**:

```console
% Cannot commit because there is an unexpired trial/rollback session '00001000-00004dab-00000000'.
```

The history shows the rollback as its own entry, with `Rollback` in the Client column.

## 3. Logging in through an AAA server

The building blocks are the ones you know from IOS. The names differ slightly:

| Piece | On IOS XR |
|---|---|
| the server and its key | defined globally, by address |
| a server group | a named group that lists servers |
| the source address of requests | set per protocol, per VRF |
| authentication, authorisation, accounting | method lists — `default` or named |
| which list a session uses | the **line template** (`line console`, `line default`, or a named template) |

### Where requests come from

Without a source interface, XR01 sends TACACS+ requests from the address of the interface that faces the
server. If the server knows the router by its loopback, it has no key for that address. The server's log says so:

```console
tac_plus[3146]: connect from 10.0.50.1 [10.0.50.1]
tac_plus[3146]: Error 10.0.50.1 : Invalid AUTHEN/START packet (check keys)
```

On the router, nothing looks broken: local accounts still log in, because of the next point.

### When the next method is used

A method list such as "the server group, then local" does **not** mean "try the server, and if that fails, try local".
Cisco's AAA guide: *"The subsequent methods of authentication are used only if the initial method returns an
error, not if the request is rejected."*

- The server answers "no such user" → the login fails. Local accounts are not consulted.
- The server does not answer, or the exchange fails (wrong key, wrong source address) → local accounts are used.

So once the server works, an account that exists only on the router can no longer log in. That is usually what you
want. It is also why a key mismatch can go unnoticed: everything that matters still works, through the local fallback.

### Rights from the server

A TACACS+ server gives an IOS XR user its rights in the attribute `task`. The value lists task IDs with permissions,
user groups, or both; Cisco's guide gives `task = "rwx:bgp,#operator"` as an example. `#` introduces a **user group**.
After login, `show user group` shows the groups the server assigned, and `show user tasks` the resulting tasks.

In the lab, the users from the server received their tasks even before any `aaa authorization` line was configured:
the router made a second request for every login. The configuration guides use `aaa authorization exec` in their
examples. Configure it if you want the behaviour to be explicit, and test it on your release.

### The console

The console uses the `line console` template, and with it the `default` method lists unless it names others. If the
console must always use local accounts, it needs a method list of its own, and the template has to point at it.

### A server that comes back

When the server stops answering, XR01 marks it down and puts it on hold. `show tacacs` shows the state:

```console
Server: 10.0.50.10/49 opens=52 closes=47 aborts=8 errors=0
	status=down single-connect=false family=IPv4
	idle-timeout=0 on-hold=true
```

In the lab, logins kept falling back to local accounts for about 25 seconds after the server was running again.
The hold is configurable (`holddown-time`, globally or per server). Remember this when you test a fallback:
start the server again, then wait until `status=up` before you test the server path.

## 4. Traffic addressed to the router: LPTS

On IOS you protect the route processor with Control Plane Policing: you write class maps for the traffic you care
about and attach a policy to the control plane. Until you do, nothing is policed.

IOS XR polices from the start. **Local Packet Transport Services (LPTS)** sorts every packet addressed to the router
into a *flow* — OSPF from a known neighbour, BGP from a configured peer, SSH, ICMP and so on — and polices each flow in
the line card hardware before the packet reaches the route processor. You do not write classes. You change the rate
of a flow that already exists.

The policer table is per line card:

```console
RP/0/RP0/CPU0:XR01#show lpts pifib hardware police location 0/0/CPU0
flow_type            priority sw_police_id hw_policer_addr Cur. Rate  burst static_avgrate avgrate_type AggrAccepts   AggrDrops
OSPF-mc-known        high     2            217             2000       1000  2000           Static       84626         0
OSPF-mc-default      low      3            218             1500       750   1500           Static       2             0
ICMP-local           medium   12           227             1500       750   1500           Static       0             0
SSH-known            medium   27           242             300        150   300            Static       0             0
SSH-default          low      28           243             200        100   200            Static       0             0
ICMP-default         low      53           268             1500       750   1500           Static       168           0
```

- *known* and *default* are the two halves of most protocols: traffic from a configured peer or an established
  session, and everything else. An unknown host sending SSH gets the smaller budget.
- `avgrate_type` is `Static` for a default rate and `Global` for a rate you configured.
- The counters show which flow a packet landed in. Pings to the router's own addresses count under `ICMP-local`,
  not `ICMP-default`.
- Asked for the route processor's location, the command answers `This command is only supported on LC`.

A policer limits bursts as well as the average. With ICMP-local at 50 pps, pings sent five per second all pass,
a ping flood loses about 60 % of its packets, and an IOS ping — which sends the next echo as soon as the reply
arrives — loses every third one:

```console
RT01#ping 10.0.12.1 repeat 5
!!.!!
Success rate is 80 percent (4/5), round-trip min/avg/max = 2/2/4 ms
```

Keep that in mind before you take a ping from a router as proof that something is broken.

## 5. Access lists

ACLs work as on IOS, with a different notation:

- An IPv4 ACL is `ipv4 access-list <name>`. There is no separate numbered type: `101` is accepted, but only as a name.
- Every line has a sequence number. If you leave it out, XR numbers the lines 10, 20, 30 … for you.
- An ACL is applied under the interface with the direction spelled out: `ingress` or `egress`.
- Both a prefix length and a wildcard mask are accepted for addresses.

What an ACL does to traffic is the same as on IOS. An inbound ACL on an interface also filters traffic addressed to
the router. A list that ends in the implicit deny drops the OSPF hellos from the neighbour too, and the adjacency
goes down when the dead timer expires. In the lab, an inbound ACL that permitted only TCP took the OSPF adjacency on
that link down.

## 6. What changes in your habits

| On IOS you would | On IOS XR |
|---|---|
| give a user `privilege 15`, or a custom privilege level | build the rights from task IDs: task group → user group → user |
| guess which privilege level a command needs | `describe <command>`, logged in as the account that will use it |
| put an `access-class` on the VTY lines | Management Plane Protection, per interface and protocol |
| write CoPP before anything is protected | LPTS is already policing. Change the rate of one flow |
| trust that a server outage shows | check `show tacacs`. A working local fallback hides a dead server |

## Practice

Go to lab **XRT-02** and do the M2 tasks. Several of them can lock you out of XR01; the management interface is
how the checks reach it. Plan each risky change as a confirmed commit.

:::note
Sources: the IOS XR configuration guides for the ASR 9000 (System Security: *Configuring AAA Services*,
*Implementing Management Plane Protection*; IP Addresses and Services: *Implementing LPTS*) and their command
references, checked October 2026. The following come from measurement on 24.3.1, not from the documentation:
`show running-config` leaving out what the user may not read, `describe` answering differently per user, the
tasks arriving without `aaa authorization exec`, the 25-second hold, and the burst behaviour of the ICMP-local
policer. Check them on another release before you rely on them.
:::
