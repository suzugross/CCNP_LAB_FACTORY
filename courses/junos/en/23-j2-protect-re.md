# J2 — Protecting the RE: the lo0 filter

## 1. What protecting the RE gives you

### 1.1 The problem: the router itself accepts anyone

Inside the router, BGP, OSPF and SSH run on the RE (Routing Engine). It computes routes and takes configuration: it is the brain of the router.
In the starting topology, JUN02 accepts traffic for this RE from anyone. NET1 connects to SSH on JUN02, and SRV1, which is no BGP peer,
connects over TCP to port 179 (BGP) on JUN02.

```console
srv1:/# probe 192.168.0.2 179
open  tcp 192.168.0.2:179  0.00s
```

The RE handles far less traffic than the part that forwards packets at high speed (the PFE). Keeping the RE busy with traffic it does
not need affects route computation and keeping sessions up. You want to narrow what the RE receives to what it needs.

### 1.2 What came before

In IOS, SSH is narrowed with `access-class` on the vty lines, and other traffic for the RE with CoPP (a policy-map on the control plane).
There are two tools, and CoPP is mostly about limiting rates.

In IOS XR, LPTS limits traffic for the RE per kind of traffic, and MPP (Management Plane Protection) narrows the ways in for management
(M2 of the IOS XR track). Here, too, the mechanisms are split by purpose.

### 1.3 The Junos answer

Junos applies the same kind of firewall filter that you put on an interface to the input of **lo0**. lo0 is the interface that stands for
the RE: packets for the RE, from whichever interface, pass the input filter on lo0 before they reach the RE.
You list what the RE may receive in one filter and drop the rest.

## 2. How it works

### 2.1 The order a packet for the RE passes through

In this example, filter RE-GUARD is applied to lo0 on JUN01. We follow a packet from the server network of SRV1 (172.16.20.1) to SSH
on JUN01. Rest the pointer on a number in the drawing (tap it on a phone) to see that block of configuration in a pop-up, and its lines
are highlighted in the configuration example below.

:::walk
legend: The line carries IP packets. A packet for the RE passes the input filter of the interface it arrived on, then the input filter on lo0.
rows:
  - {node: SRV1, say: ["~Sends a TCP SYN from 172.16.20.1 to SSH on lo0 of JUN01 (192.168.0.1)"]}
  - {wire: "[[TCP 172.16.20.1 → 192.168.0.1:22]] _SYN"}
  - panel: JUN01
    sub: in front of the RE
    items:
      - {head: "**Input of et-0/0/1** no filter in this example", say: ["An interface filter, if there were one, would judge it here first, for transit and for the RE alike"]}
      - ref: 1
        head: "**Input of lo0** `filter input RE-GUARD`"
        say: ["The routing table says the destination is this router (192.168.0.1). Before it goes to the RE, it passes RE-GUARD"]
      - ref: 2
        head: "**RE-GUARD** terms from the top"
        match:
          - ["term OSPF  from protocol ospf", false, "no match"]
          - ["term ICMP  from protocol icmp", false, "no match"]
          - ["term SSH  from source-address 172.16.10.0/24, protocol tcp, destination-port ssh", false, "no match (the source is 172.16.20.1)"]
          - ["term NTP  from source-prefix-list NTP-SERVERS, protocol udp, port ntp", false, "no match"]
          - ["term EST  from protocol tcp, tcp-established", false, "no match (a SYN has no ACK)"]
          - ["term LAST  (no from)", true, "match → `count RE-GUARD-DROP`, `discard`"]
      - {say: ["~It never reaches the RE, and nothing goes back to SRV1 (timeout)"]}
  - {aside: "From 172.16.10.10", say: ["Matches SSH in ② → `accept` → SSH on the RE takes it"]}
  - {aside: "Packets passing through JUN01", say: ["~A packet from NET1 to 172.16.20.1, for example, is not for this router, so it does not pass the lo0 filter"]}
:::

:::config JUN01 — narrow what the RE receives (a filter on lo0)
set system ntp server 192.168.0.2                                                         ## The time source (as an NTP client)
set policy-options prefix-list NTP-SERVERS apply-path "system ntp server <*>"             ## ② Take the NTP servers' addresses from the configuration
set firewall family inet filter RE-GUARD term OSPF from protocol ospf                     ## ② OSPF adjacencies
set firewall family inet filter RE-GUARD term OSPF then accept                            ## ② 
set firewall family inet filter RE-GUARD term ICMP from protocol icmp                     ## ② ping and traceroute
set firewall family inet filter RE-GUARD term ICMP then accept                            ## ② 
set firewall family inet filter RE-GUARD term SSH from source-address 172.16.10.0/24      ## ② SSH only from
set firewall family inet filter RE-GUARD term SSH from protocol tcp                       ## ② the server network 172.16.10.0/24
set firewall family inet filter RE-GUARD term SSH from destination-port ssh               ## ② 
set firewall family inet filter RE-GUARD term SSH then accept                             ## ② 
set firewall family inet filter RE-GUARD term NTP from source-prefix-list NTP-SERVERS     ## ② NTP answers from
set firewall family inet filter RE-GUARD term NTP from protocol udp                       ## ② the NTP servers
set firewall family inet filter RE-GUARD term NTP from port ntp                           ## ② 
set firewall family inet filter RE-GUARD term NTP then accept                             ## ② 
set firewall family inet filter RE-GUARD term EST from protocol tcp                       ## ② Replies to TCP connections the router starts
set firewall family inet filter RE-GUARD term EST from tcp-established                    ## ② 
set firewall family inet filter RE-GUARD term EST then accept                             ## ② 
set firewall family inet filter RE-GUARD term LAST then count RE-GUARD-DROP               ## ② Count everything else,
set firewall family inet filter RE-GUARD term LAST then discard                           ## ② and drop it
set interfaces lo0 unit 0 family inet filter input RE-GUARD                               ## ① Apply it to packets for the RE
:::

Result: from 172.16.10.10 it connects, and from 172.16.20.1 it is dropped.

```console
srv1:/# probe 172.16.10.1 22
open  tcp 172.16.10.1:22  0.00s
srv1:/# probe 192.168.0.1 22 -s 172.16.20.1
timeout  tcp 192.168.0.1:22 from 172.16.20.1  3.00s

admin@jun01> show interfaces lo0.0 extensive | match ilter
      Input Filters: RE-GUARD

admin@jun01> show firewall filter RE-GUARD
Filter: RE-GUARD
Counters:
Name                                                                            Bytes              Packets
RE-GUARD-DROP                                                                     180                    3
```

The first probe goes to 172.16.10.1 (the address of et-0/0/1). Whichever interface address it goes to, a packet for this router passes
the lo0 filter.

### 2.2 Listing what the RE receives

A lo0 filter takes the shape "list what is needed, drop the rest", so the core of the job is listing everything the RE receives, with nothing left out.

| Kind | Example | How the term might look |
|---|---|---|
| Routing protocols | OSPF hellos and LSAs | `protocol ospf` |
| | BGP | `protocol tcp`, `port bgp`. Narrow it by the peers' addresses |
| Management | SSH | `protocol tcp`, `destination-port ssh`. Narrow it by the networks you manage from |
| Diagnostics | Answers to ping and traceroute | `protocol icmp` |
| Answers to traffic where the RE is the client | Answers from NTP, DNS and syslog servers | `protocol udp`, `port ntp` and so on. Narrow it by the servers |
| Replies to TCP the RE starts | SSH or file transfers from the router to other devices | `protocol tcp`, `tcp-established` |

A protocol that you leave out does not break at once. OSPF keeps an adjacency for the dead interval (40 seconds by default) after the
neighbour's hellos stop arriving. BGP keeps a session for the hold time (90 seconds in this topology). Nothing happens right after the
commit, and things break some time later, so the cause is easy to miss.

Here the OSPF term was removed from JUN02's lo0 filter, and we waited 45 seconds. JUN02 has lost its neighbour. JUN01 still receives
JUN02's hellos, but its own hellos no longer get through, so it stays in `Init`.

```console
admin@jun02> show ospf neighbor

admin@jun01> show ospf neighbor
Address          Interface              State           ID               Pri  Dead
10.0.12.2        et-0/0/0.0             Init            192.168.0.2      128    33
```

Whether the OSPF adjacency is kept also shows in the `Dead` column of `show ospf neighbor`. While hellos arrive, it keeps going back
to the 30s; when they stop, it counts down one second at a time.

### 2.3 apply-path: taking the peers' addresses from the configuration

If you narrow by BGP peers or NTP servers and write their addresses into the filter, you have to fix the filter every time you add one.
If you forget, the new peer cannot connect.

With `apply-path`, a prefix list takes its contents from the configuration. You write the path through the configuration hierarchy and
put `<*>` where it varies. With `system ntp server <*>`, every address written as an NTP server goes into the list. See what went in with
`display inheritance`.

```console
admin@jun01> show configuration policy-options prefix-list NTP-SERVERS | display inheritance
##
## apply-path was expanded to:
##     192.168.0.2;
##
apply-path "system ntp server <*>";
```

The addresses of BGP neighbours can be taken the same way, by writing a path under `protocols bgp`. Whether groups or neighbours are
added, the filter needs no rewriting.

### 2.4 Replies to connections the router starts

A lo0 filter sees everything the RE receives. That includes the replies to connections the RE itself starts toward others.
TCP replies have ACK set, so the `tcp-established` term of the previous page lets them through.

BGP has port 179 on one side, both when the peer connects in and when this router connects out. Written as `port bgp` (port 179 on
either the source or the destination), both directions of the session pass. With only `destination-port bgp`, the replies to a session
this router started (whose source port is 179) do not match the term.

Here JUN02's lo0 filter has no reply term, and JUN02 connects to port 8080 at the ISP. The SYN goes out, but the SYN and ACK coming back
are dropped by the lo0 filter, and it times out after 3 seconds (`rc=124` marks a timeout).

```console
admin@jun02> start shell command "timeout 3 bash -c 'exec 3<>/dev/tcp/10.0.23.2/8080 && head -c 2 <&3'; echo rc=$?"
rc=124
```

### 2.5 The management port is separate (Junos OS Evolved)

On this router (Junos OS Evolved), the lo0 filter **does not act on traffic to the management port**. The management port `re0:mgmt-0`
is handled as a separate way in, with its own routing table `mgmt_junos`. To narrow management traffic, apply a separate filter to the
logical unit of `re0:mgmt-0`.

The consoles of this topology are SSH sessions to the management port. RE-GUARD has no term for the management network, yet after it
was applied, a new console could still be opened.

```console
admin@jun01> show system users
 5:36AM  up 39 min, 2 users, load averages: 0.43, 0.28, 0.34
USER     TTY      FROM                              LOGIN@  IDLE WHAT
admin    pts/0    172.20.20.1                      05:35   4.00s -cli
admin    pts/1    172.20.20.1                      05:36   0.00s -cli
```

On Junos OS (the one that is not Evolved), the lo0 filter acts on management traffic too. Forget the term for the management network,
and you lock yourself out. When you try a lo0 filter on such a device, use `commit confirmed` from J0.

### 2.6 How to check

1. Is it applied: `Input Filters` in `show interfaces lo0.0 extensive | match ilter`.
2. Does it drop: the counter of the last term in `show firewall filter name`.
3. Is what you need still alive: `Full` and the `Dead` column in `show ospf neighbor`, `Establ` in `show bgp summary`.
   For BGP, `clear bgp neighbor peer` makes it reconnect; seeing it come back to `Establ` settles it.
4. From outside: SSH from a source you did not allow gives `timeout`, and from a source you allowed gives `open`.

## 3. Configuration examples

### 3.1 Protect the RE of JUN01

This is RE-GUARD from section 2.1. JUN01 does not run BGP, so there is no BGP term; instead it lets answers from its NTP server through.

Result: after RE-GUARD is applied, the OSPF adjacency is still `Full`, with `Dead` in the 30s.

```console
admin@jun01> show ospf neighbor
Address          Interface              State           ID               Pri  Dead
10.0.12.2        et-0/0/0.0             Full            192.168.0.2      128    32
```

### 3.2 From IOS and IOS XR to Junos

| In IOS | In IOS XR | In Junos |
|---|---|---|
| `access-class name in` under `line vty 0 4` | MPP (`control-plane management-plane`) narrows the ways in for SSH | The SSH term of the lo0 filter |
| CoPP (`service-policy input` under `control-plane`) | LPTS (rates limited automatically per kind) | The lo0 filter (rates are limited with a policer, page 4) |
| Fix the ACL by hand for each peer | Fix the prefix-set by hand | Take them from the configuration with `apply-path` |
| The management interface is covered by the same controls | MPP decides the management ways in | On Junos OS Evolved the management port is separate (a separate filter on `re0:mgmt-0`) |

## Practice

Move to lab **JNT-03** and work on task J2-3.

<p class="tolab"><a href="/_learn?id=JNT-03">Open lab JNT-03 in the workspace</a> — <a href="24-j2-practice-2.html">Tasks</a></p>

:::note
Sources: Juniper Networks, *Routing Policies, Firewall Filters, and Traffic Policers User Guide* (2026-06-23), "Junos OS Evolved Local
Packet Flow Control" (the lo0 filter does not apply to management traffic, and the management interface takes its own filter; on Junos OS
the lo0 filter applies to management traffic too), the section on `apply-path` in prefix lists, and the examples of protecting the RE
with lo0. LPTS and MPP of IOS XR are from M2 of the IOS XR track. The output with the OSPF term removed and the reply to TCP started by the
RE were captured on the topology of J1 (JNT-02), with a lo0 filter on JUN02. The output was captured on vJunos-Evolved
(Junos OS Evolved 26.2R1.7) in containerlab.
:::
