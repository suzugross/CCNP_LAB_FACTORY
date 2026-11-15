# J2 — Firewall filters: terms and actions

## 1. Why write in terms

### 1.1 The problem: one exit, different handling for different traffic

At JUN01's exit toward the server network, the web should pass, ping should pass, everything else should be stopped, and you want to
know how much was stopped. The handling differs from one kind of traffic to another, so one exit needs several pairs of condition and handling.

### 1.2 What came before

An IOS extended ACL has one condition and one permit or deny per line, and checks the lines from the top. Line numbers set the order,
and a packet that matches no line is dropped by the implicit deny. Per-line counters appear in `show access-lists`.
IOS XR ACLs follow the same idea, with numbered lines.

### 1.3 The Junos answer

A Junos firewall filter lines up terms instead of lines. One term can hold several conditions (`from`), and its actions (`then`) can be
combined, such as "count, then let through" or "count, record, then drop". Terms are written as in the policies of J1, so what you
learned there carries over: AND and OR in `from`, the order of terms, and `insert`.

## 2. How it works

### 2.1 The shape of a filter

A filter is written under `firewall`, per protocol family: `family inet` for IPv4, `family inet6` for IPv6.

```
firewall {
    family inet {
        filter filter-name {
            term term-name {
                from {
                    conditions;
                }
                then {
                    actions;
                }
            }
            term next-term-name {
                ...
            }
        }
    }
}
```

A term without `from` matches every packet. You use one at the end of a filter to catch "everything else".

### 2.2 from: match conditions

These are the conditions you use most.

| Condition | What it matches |
|---|---|
| `source-address`, `destination-address` | The source or destination address, written as a prefix |
| `address` | Either the source or the destination |
| `source-prefix-list`, `destination-prefix-list`, `prefix-list` | The prefixes listed in a prefix list under `policy-options` (page 4) |
| `protocol` | The IP protocol (`tcp`, `udp`, `icmp`, `ospf` and so on) |
| `source-port`, `destination-port` | The TCP or UDP port. Names such as `http` (80), `https` (443), `ssh` (22) and `bgp` (179) work too |
| `port` | The port on either side |
| `tcp-established` | TCP packets with the ACK or RST bit set (everything but the SYN that starts a connection) |
| `icmp-type` | The ICMP type (`echo-request` and so on) |

They combine as `from` does in J1. **Values of the same kind need only one to match (OR); conditions of different kinds must all match
(AND).** `destination-port [ http https ]` is port 80 or port 443; `protocol tcp` together with `destination-port http` is "TCP, and port 80".

Port conditions look at a field that both TCP and UDP have, so put `protocol tcp` or `protocol udp` in the same term.
`tcp-established` does not check that the packet is TCP either, so pair it with `protocol tcp`.

### 2.3 then: actions

Actions come in two kinds.

| Kind | Action | What it does |
|---|---|---|
| Terminating (ends the evaluation) | `accept` | Let it through |
| | `discard` | Drop it silently. Nothing goes back to the source |
| | `reject` | Drop it and send an ICMP unreachable back to the source |
| Does not end the evaluation | `count name` | Count it in a named counter |
| | `log` | Keep it for `show firewall log` |
| | `syslog` | Turn it into a syslog message |
| | `policer name` | Limit the rate (page 4) |
| Flow control | `next term` | Go on to the next term |

A term can have only one terminating action. Counting and recording actions go next to the terminating action.

**A packet that matches a term with no terminating action is let through (an implicit accept).** A term with only `then count X`
counts the packet and then lets it through. To drop it, add `discard`. On Junos OS Evolved, `next term` cannot be the last term.

### 2.4 The implicit discard at the end

A packet that matches no term is dropped at the end of the filter. The idea is the same as the implicit deny of an IOS ACL.
Unlike the policies of J1, nothing is left to a protocol default.

Packets dropped by the implicit discard are not counted by any counter. To count them, put a term without `from` at the end, with
`count` and `discard`. `term LAST` in the example of the previous page is such a term.

### 2.5 discard and reject

`discard` sends nothing back, and `reject` sends ICMP back. From outside, the difference is between being kept waiting and being
turned away at once. Here a filter that lets only ICMP through and drops the rest is applied to the ISP-facing input of JUN02, and NET1
sends after the action of the last term is changed.

```console
net1:/# probe 172.16.10.1 22 -s 198.51.100.10
timeout  tcp 172.16.10.1:22 from 198.51.100.10  3.00s
net1:/# probe 172.16.10.1 22 -s 198.51.100.10
unreachable (Host is unreachable)  tcp 172.16.10.1:22 from 198.51.100.10  0.00s
```

The first line is with `discard`: the sender waits for an answer and gives up. The second is with `reject`: it is turned away at once.
`reject` sends an ICMP destination unreachable (type 3), with code 13 (administratively prohibited) by default.
A type written after `reject` changes the code.

`probe` can also say `refused`. Here the filter has been removed, and the packet goes to port 8080 on SRV1, where nothing listens.

```console
net1:/# probe 172.16.20.1 8080 -s 198.51.100.10
refused  tcp 172.16.20.1:8080 from 198.51.100.10  0.00s
```

`refused` means the device at the other end sent a RST to say "nobody listens on that port". It proves the packet **got through** the
filters on the way.

Toward outside, `discard` is the usual choice. `reject` tells the world "there is a filter here", and sending ICMP costs some effort.
`reject` suits the inside, where you want users to learn of a failure quickly.

### 2.6 The order of terms and insert

Terms are checked from the top in the order written. A term added with `set` goes to the end, so if a term that drops "everything else"
is already there, a term added later receives nothing. As with the policies of J1, you reorder with `insert`.

```console
[edit]
admin@jun01# show firewall family inet filter TO-SERVERS | display set | match "term (EST|LAST)"
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP
set firewall family inet filter TO-SERVERS term LAST then discard
set firewall family inet filter TO-SERVERS term EST from protocol tcp
set firewall family inet filter TO-SERVERS term EST from tcp-established
set firewall family inet filter TO-SERVERS term EST then accept

[edit]
admin@jun01# insert firewall family inet filter TO-SERVERS term EST before term LAST

[edit]
admin@jun01# show firewall family inet filter TO-SERVERS | display set | match "term (EST|LAST)"
set firewall family inet filter TO-SERVERS term EST from protocol tcp
set firewall family inet filter TO-SERVERS term EST from tcp-established
set firewall family inet filter TO-SERVERS term EST then accept
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP
set firewall family inet filter TO-SERVERS term LAST then discard
```

### 2.7 Stateless: replies and tcp-established

A firewall filter judges each packet by its own contents. It does not remember who connected to whom (it is stateless).
So the replies to a TCP connection started from the inside are judged again by the filter in the direction they come back in.

TO-SERVERS from the previous page is applied in the direction toward SRV1. When SRV1 connects to the web on NET1 (port 8080), the SYN
going out passes, because that direction has no filter; but the SYN and ACK coming back meet TO-SERVERS, match no term, and are dropped.

TCP replies always have the ACK bit set. `tcp-established` matches packets with ACK or RST set, so a term that pairs it with
`protocol tcp` lets TCP replies through. The SYN that starts a connection has no ACK, so it does not match this term.
TCP connections newly started from outside are still judged by the terms after it.

Result: before and after the reply term (EST) is placed before LAST.

```console
srv1:/# probe 198.51.100.10 8080 -s 172.16.20.1
timeout  tcp 198.51.100.10:8080 from 172.16.20.1  3.00s
srv1:/# probe 198.51.100.10 8080 -s 172.16.20.1
open  tcp 198.51.100.10:8080 from 172.16.20.1  0.00s
net1:/# probe 172.16.20.1 443 -s 198.51.100.10
timeout  tcp 172.16.20.1:443 from 198.51.100.10  3.00s
```

This does not look at real state. A packet crafted outside with ACK set passes this term. Remembering connections and letting only
their replies back (a stateful firewall) is the job of other devices and features.
`established` in an IOS ACL follows the same idea: it looks at the ACK and RST bits.

### 2.8 Applying a filter to an interface

A filter is applied to the family of an interface's logical unit, one per direction.

```
set interfaces et-0/0/1 unit 0 family inet filter input  filter-name
set interfaces et-0/0/1 unit 0 family inet filter output filter-name
```

Check it on the `Input Filters` and `Output Filters` lines of `show interfaces … extensive`.

```console
admin@jun01> show interfaces et-0/0/1.0 extensive | match ilter
      Output Filters: TO-SERVERS
```

An output filter also acts on packets that the router itself (its RE) sends. In this topology, once TO-SERVERS was applied, SSH from
SRV1 to JUN01 stopped connecting: the SYN and ACK that JUN01 sent back to SRV1 were dropped by TO-SERVERS as they left et-0/0/1.
With the reply term (EST) added, it connected again.

### 2.9 Reading the numbers: show firewall

`show firewall` shows every counter of the filters in use. `show firewall filter name` narrows it to one.

```console
admin@jun01> show firewall filter TO-SERVERS
Filter: TO-SERVERS
Counters:
Name                                                                            Bytes              Packets
TO-SERVERS-DROP                                                                  1080                   18
WEB-IN                                                                            320                    6
```

Read right after the traffic, a counter may not have gone up yet. Wait a few seconds and read again. To reset the numbers, use
`clear firewall filter name` or `clear firewall all`.

## 3. Configuration examples

### 3.1 Narrow the traffic going out to the server network, and let replies back

This is TO-SERVERS from the previous page with the reply term added.

:::config JUN01 — narrow the traffic going out to the server network (replies pass too)
set firewall family inet filter TO-SERVERS term ICMP from protocol icmp                       ## Let all ICMP through
set firewall family inet filter TO-SERVERS term ICMP then accept                              ## 
set firewall family inet filter TO-SERVERS term WEB from destination-address 172.16.20.0/24   ## TCP port 80 to the server network only
set firewall family inet filter TO-SERVERS term WEB from protocol tcp                         ## 
set firewall family inet filter TO-SERVERS term WEB from destination-port http                ## 
set firewall family inet filter TO-SERVERS term WEB then count WEB-IN                         ## Count it and let it through
set firewall family inet filter TO-SERVERS term WEB then accept                               ## 
set firewall family inet filter TO-SERVERS term EST from protocol tcp                         ## TCP
set firewall family inet filter TO-SERVERS term EST from tcp-established                      ## with ACK or RST set (replies)
set firewall family inet filter TO-SERVERS term EST then accept                               ## Let it through
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP               ## Count everything else,
set firewall family inet filter TO-SERVERS term LAST then discard                             ## and drop it silently
set interfaces et-0/0/1 unit 0 family inet filter output TO-SERVERS                           ## Apply it to packets leaving et-0/0/1
:::

Written in this order, EST comes before LAST. If you add EST later, move it forward with `insert … term EST before term LAST`.

### 3.2 From IOS and IOS XR to Junos

| In IOS | In IOS XR | In Junos |
|---|---|---|
| `ip access-list extended name` | `ipv4 access-list name` | `firewall family inet filter name` |
| `10 permit tcp any 172.16.20.0 0.0.0.255 eq 80` | `10 permit tcp any 172.16.20.0/24 eq 80` | `term WEB from destination-address 172.16.20.0/24 protocol tcp destination-port http`, `then accept` |
| `permit tcp any any established` | `permit tcp any any established` | `term EST from protocol tcp tcp-established`, `then accept` |
| Implicit deny at the end | Implicit deny at the end | Implicit discard at the end |
| `deny ip any any log` | `deny ipv4 any any log` | `term LAST then count …`, `log`, `discard` |
| Line numbers set the order | Line numbers set the order | The order written. Reorder with `insert` |
| `ip access-group name out` | `ipv4 access-group name egress` | `set interfaces … family inet filter output name` |
| `show access-lists` | `show access-lists` | `show firewall` |

## Practice

Move to lab **JNT-03** and work on tasks J2-1 and J2-2.

<p class="tolab"><a href="/_learn?id=JNT-03">Open lab JNT-03 in the workspace</a> — <a href="22-j2-practice.html">Tasks</a></p>

:::note
Sources: Juniper Networks, *Routing Policies, Firewall Filters, and Traffic Policers User Guide* (2026-06-23), "Firewall Filter Match
Conditions for IPv4 Traffic" (port conditions go with protocol; `tcp-established` is an alias for `tcp-flags "(ack | rst)"` and does not
check that the packet is TCP), the terminating actions and action modifiers, the implicit accept when a term has no action, and the table
of actions for PTX (the default of `reject` is administratively prohibited). IOS XR ACLs are from M2 of the IOS XR track.
The output was captured on vJunos-Evolved (Junos OS Evolved 26.2R1.7) in containerlab.
:::
