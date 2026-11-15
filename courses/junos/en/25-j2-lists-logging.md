# J2 — Lists and logging: filter lists and records

## 1. What listing filters and recording give you

### 1.1 The problem: one entrance, two decisions with different purposes

The entrance from the ISP needs two decisions: "drop packets whose source address is wrong" and "let through only the services that may
pass". The first has the same contents at every entrance; the second differs from one entrance to another. Mixed into one filter, the
source check has to be copied into the filter of every entrance.

Beyond counting what was dropped, you may also want to see later what it was (from where, to where, to which port).

### 1.2 What came before

An IOS ACL can be applied only once per direction of an interface, so lines with different purposes are mixed into one ACL. To record
what was dropped, you put `log` at the end of a line and send it to syslog. IOS XR also has one ACL per direction of an interface.

### 1.3 The Junos answer

Junos can apply **a list of filters** in one direction (`input-list`, `output-list`). Make one filter for the source check, and you can
reuse it in front of the filter of each entrance. For recording there are two actions, `log` (a buffer inside the router) and `syslog`
(syslog messages), which you combine with `count`.

## 2. How it works

### 2.1 Filter lists

With `input-list [ A B ]`, an incoming packet is checked by A, then by B. A terminating action (`accept`, `discard`, `reject`)
anywhere ends it. A packet that matches no term of A is not dropped at the end of A; it goes on to B.
If it matches no term of the last filter either, the implicit discard applies there.

In this example, SRC-CHECK (a source check) and FROM-SERVERS (a counter) are listed on JUN01's entrance from the server network. We
follow a packet from SRV1 whose source (10.99.0.1) is not in the server network. Rest the pointer on a number in the drawing (tap it on
a phone) to see that block of configuration in a pop-up, and its lines are highlighted in the configuration example below.

:::walk
legend: The line carries IP packets. Listed filters are checked from left to right, and evaluation ends at a terminating action.
rows:
  - {node: SRV1, say: ["~Sends a ping to NET1 (198.51.100.10) with source 10.99.0.1"]}
  - {wire: "[[ICMP 10.99.0.1 → 198.51.100.10]] _echo-request"}
  - panel: JUN01
    sub: the entrance from the server network
    items:
      - ref: 1
        head: "**Input of et-0/0/1** `filter input-list [ SRC-CHECK FROM-SERVERS ]`"
        say: ["Checked in the order listed. SRC-CHECK first"]
      - ref: 2
        head: "**SRC-CHECK** is the source in the server network?"
        match:
          - ["term SPOOF  from source-address 0.0.0.0/0, 172.16.10.0/24 except, 172.16.20.0/24 except", true, "match (10.99.0.1 is in 0/0 and in neither excepted range) → `count SPOOF`, `syslog`, `log`, `discard`"]
      - {say: ["~It ends here. FROM-SERVERS is not checked"]}
  - {aside: "For source 172.16.20.1", say: ["Does not match SPOOF in ② (it is in an excepted range) → SRC-CHECK has no more terms → on to the next filter → matches ALL in ③ → `count FROM-SERVERS`, `accept`"]}
  - {aside: "With a `then accept` term added at the end of ②", say: ["~A packet from 172.16.20.1 is accepted there and the list ends → ③ is never checked, and FROM-SERVERS counts nothing"]}
:::

:::config JUN01 — check the source, then count (a filter list)
set firewall family inet filter SRC-CHECK term SPOOF from source-address 0.0.0.0/0              ## ② Any source,
set firewall family inet filter SRC-CHECK term SPOOF from source-address 172.16.10.0/24 except  ## ② except the two server networks
set firewall family inet filter SRC-CHECK term SPOOF from source-address 172.16.20.0/24 except  ## ② 
set firewall family inet filter SRC-CHECK term SPOOF then count SPOOF                           ## ② Count it
set firewall family inet filter SRC-CHECK term SPOOF then syslog                                ## ② Turn it into a syslog message
set firewall family inet filter SRC-CHECK term SPOOF then log                                   ## ② Keep it for show firewall log
set firewall family inet filter SRC-CHECK term SPOOF then discard                               ## ② Drop it
set firewall family inet filter FROM-SERVERS term ALL then count FROM-SERVERS                   ## ③ Count everything left,
set firewall family inet filter FROM-SERVERS term ALL then accept                               ## ③ and let it through
set interfaces et-0/0/1 unit 0 family inet filter input-list [ SRC-CHECK FROM-SERVERS ]         ## ① Apply the two, listed, to the input
set system syslog file fw-log firewall any                                                      ## Send the firewall filter messages to the file fw-log
:::

Result: a ping from 172.16.20.1 gets through, and a ping from 10.99.0.1 is dropped.

```console
srv1:/# ping -c 2 -W 1 -I 172.16.20.1 198.51.100.10
2 packets transmitted, 2 packets received, 0% packet loss
srv1:/# ping -c 2 -W 1 -I 10.99.0.1 198.51.100.10
2 packets transmitted, 0 packets received, 100% packet loss
```

Add a last term with only `then accept` to SRC-CHECK, and, as the second alternative case in the drawing says, the filters after it are
no longer checked. When the same shape was tried on JUN02, with an `accept` term at the end of the first filter the counter of the
second filter did not go up. Leave the end of the first filter as "no term matched", so that it hands over to the next filter.

Junos OS Evolved also has another way of listing, `input-chain`, which goes on to the next filter even after `accept`. It is available
on only some models, so this unit uses `input-list`.

### 2.2 Lists of addresses, and except

Besides writing addresses directly, source and destination conditions can use the prefix lists of `policy-options`
(`source-prefix-list`, `destination-prefix-list`, `prefix-list`). One list can serve both filters and routing policies.

Both addresses and prefix lists take `except`. Among the addresses listed in one condition, the one that **covers the packet's address
most specifically** decides, and if that one is `except`, the condition does not match. For 172.16.20.1 in SRC-CHECK, the most specific
cover is 172.16.20.0/24 rather than 0.0.0.0/0, and it is `except`, so the term does not match.

You use this to drop a wide range while keeping a part of it, for example when the addresses of a link you use fall inside a range of
private addresses you drop. Take that part out with `except`.

### 2.3 Counter names in a list

When filters are listed, Junos builds one filter for that interface. It is named `logical-interface-inet-i` (for input; output gets `-o`),
and its counters count under names with that suffix. Read under the original filter names, they stay at 0.

```console
admin@jun01> show interfaces et-0/0/1.0 extensive | match ilter
      Input Filters: et-0/0/1.0-inet-i
      Output Filters: TO-SERVERS

admin@jun01> show firewall
Filter: FROM-SERVERS
Counters:
Name                                                                            Bytes              Packets
FROM-SERVERS                                                                        0                    0
...
Filter: SRC-CHECK
Counters:
Name                                                                            Bytes              Packets
SPOOF                                                                               0                    0
...
Filter: et-0/0/1.0-inet-i
Counters:
Name                                                                            Bytes              Packets
FROM-SERVERS-et-0/0/1.0-inet-i                                                    168                    2
SPOOF-et-0/0/1.0-inet-i                                                           168                    2
```

You can narrow it by the built name, as in `show firewall filter et-0/0/1.0-inet-i`.

### 2.4 log and syslog

**`log`** keeps the packet's header information (time, action, interface, protocol, addresses) in a buffer in the part that forwards
packets (the PFE). You read it with `show firewall log`. The `Filter` column always says `pfe`, and the `Action` column says A (accept),
D (discard) or R (reject). Add `detail` to see the ports too.

```console
admin@jun01> show firewall log
Log :
Time      Filter    Action Interface           Protocol        Src Addr                                Dest Addr
05:37:11  pfe       D      et-0/0/1.0          ICMP            10.99.0.1                               198.51.100.10
05:37:12  pfe       D      et-0/0/1.0          ICMP            10.99.0.1                               198.51.100.10

admin@jun01> show firewall log detail
Time of Log: Nov 15 05:37:11, Filter: pfe, Filter action: Discard, Name of interface: et-0/0/1.0
Name of protocol: ICMP, Packet Length: 84, Source address: 10.99.0.1 Port: 0, Destination address: 198.51.100.10 Port: 0
ICMP type: 0, ICMP code: 0
```

The buffer is small, and the oldest entries go first. In this topology, entries from a few minutes before had sometimes disappeared.
It does not suit records you want to keep.

**`syslog`** turns the same information into a syslog message. The message comes with the **firewall** facility (the class of where a
message comes from), so something has to receive it. `set system syslog file name firewall any` writes the messages of the firewall
facility, at every severity, to the file `/var/log/name`. Read it with `show log name`.

```console
admin@jun01> show log fw-log
Nov 15 05:37:12  jun01 evo-aftmand-bt[14680]: FW: et-0/0/1.0   D ICMP 10.99.0.1 198.51.100.10     0     0 (2 packets)
```

After `FW:` come the interface, the action, the protocol, the source, the destination, the source port and the destination port.
Packets that come in quick succession are summed into one line, as `(2 packets)` at the end shows.

With `then syslog` but no file to receive it, it is kept nowhere. On the routers of this topology, firewall filter messages did not
appear in the default message file (`messages`) either.

### 2.5 Policers: limiting the rate

A **policer** puts an upper limit on the amount of traffic. By dropping (or marking) what goes over the limit, it keeps down, for
example, the amount of ICMP that reaches the RE. You use it by writing `policer name` among the actions of a firewall filter term.

```
set firewall policer name if-exceeding bandwidth-limit 1m      ← the limit on the average rate (bits per second)
set firewall policer name if-exceeding burst-size-limit 15k    ← how much may go over at once (bytes)
set firewall policer name then discard                         ← drop what goes over
```

`policer` is not a terminating action. Packets within the limit follow the terminating action of the same term (an implicit accept if none is written).

**On this virtual router (vJunos-Evolved), policers do not limit the rate.** The configuration commits, and a Policers section appears in
`show firewall`, but pings far over the limit were not dropped at all, and the number dropped stayed at 0. Learn how it works and how it
is written, and check its effect on real equipment (appendix 3.2).

## 3. Configuration examples

### 3.1 Check the source, then count

This is SRC-CHECK and FROM-SERVERS from section 2.1. The resulting syslog line is as in section 2.4.

### 3.2 Put a policer on ICMP to the RE

This is the ICMP term of RE-GUARD from the previous page with a policer added. On this virtual router the rate is not limited.

:::config JUN01 — put a limit on the ICMP that reaches the RE (no effect on this virtual router)
set firewall policer ICMP-1M if-exceeding bandwidth-limit 1m           ## Up to 1 Mbps on average
set firewall policer ICMP-1M if-exceeding burst-size-limit 15k         ## Up to 15 KB over at once
set firewall policer ICMP-1M then discard                              ## Drop what goes over
set firewall family inet filter RE-GUARD term ICMP then policer ICMP-1M   ## Add it to the ICMP term (accept stays)
:::

```console
admin@jun01> show firewall filter RE-GUARD
Filter: RE-GUARD
Counters:
Name                                                                            Bytes              Packets
RE-GUARD-DROP                                                                     180                    3
Policers:
Name                                                                            Bytes              Packets
ICMP-1M-ICMP                                                                        0                    0
```

A name in the Policers section is `policer-name-term-name`. The numbers are the packets dropped for going over the limit.

### 3.3 From IOS and IOS XR to Junos

| In IOS | In IOS XR | In Junos |
|---|---|---|
| One ACL per direction of an interface | The same | `input-list [ A B ]` lists several |
| `deny ip 10.0.0.0 0.255.255.255 any` (list the ranges) | The same | `source-address`, `source-prefix-list`. Keep a part with `except` |
| `log` at the end of a line → syslog | The same | `then log` (a buffer), `then syslog` (plus a file for the firewall facility) |
| `show logging` | `show logging` | `show firewall log`, `show log name` |
| `police` in CoPP | LPTS, `police` | A `firewall policer`, used with `then policer` in a term |

## Practice

Move to lab **JNT-03** and work on tasks J2-4 and J2-5.

<p class="tolab"><a href="/_learn?id=JNT-03">Open lab JNT-03 in the workspace</a> — <a href="26-j2-practice-3.html">Tasks</a></p>

:::note
Sources: Juniper Networks, *Routing Policies, Firewall Filters, and Traffic Policers User Guide* (2026-06-23), "Understanding Multiple
Firewall Filters Applied as a List" (how listed filters are evaluated; the `-i` and `-o` names), the section on filter chains
(`input-list` stops at accept or discard; `input-chain` is available on some PTX models from Junos OS Evolved 21.4R1), the `log` action
(a buffer in the PFE) and how to read `show firewall log` (Filter is always pfe), and the section on policers. *Network Management and
Monitoring Guide* (2026-07-06), the System Logging chapter (firewall in the table of facilities; the minimum configuration is
`file name { facility severity; }`). *vJunosEvolved Deployment Guide* (2025-11-11), the limitations (vJunosEvolved-BX does not support
firewall policers). That policers have no effect, and the output with an accept at the end of the first listed filter, were checked on
JUN02 in the topology of J1 (JNT-02). The output was captured on vJunos-Evolved (Junos OS Evolved 26.2R1.7) in containerlab.
:::
