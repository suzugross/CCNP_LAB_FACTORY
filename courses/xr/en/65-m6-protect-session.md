# M6 supplement — Protecting the session: GTSM and TCP-AO

The previous page handed out a backup path in advance. This page takes the two features that protect the BGP sessions
with the outside ASes themselves. GTSM (TTL security) uses the TTL of arriving packets to tell apart packets made far away
and drop them. TCP-AO puts on each TCP segment a MAC computed from a key, and the receiver checks it. The older MD5
authentication is covered alongside.

They are 1.5.b (BGP TTL security and protocol authentication) of the blueprint, and Tasks M6-7 and M6-8 of lab XRT-17
use them. ADD-PATH and PIC are on the page *Handing out a backup path*; prefix limits, dampening and aggregation are on
*Not taking too much*.

## 1. What it is good for

### 1.1 The problem: a session with the outside can be hit from the outside

AS 65000 has three eBGP sessions with outside ASes: PE1 with the customer CE1, PE2 with X1, and PE3 with X2. Each runs on
TCP port 179 between the addresses at the two ends of a directly connected link. The notes in brackets in the figure say
which session carries each configuration example on this page. The tasks (M6-7, M6-8) put GTSM on PE2–X1 and TCP-AO on
PE3–X2.

:::topo
nodes:
  CE1: {at: [0, 1], label: "CE1 (AS 65001)"}
  PE1: {at: [2.2, 1], label: "PE1"}
  P1: {at: [4.2, 1], label: "P1"}
  RR1: {at: [4.2, 2.5], label: "RR1"}
  PE2: {at: [6.2, 0], label: "PE2"}
  PE3: {at: [6.2, 2], label: "PE3"}
  X1: {at: [8.4, 0], label: "X1"}
  X2: {at: [8.4, 2], label: "X2"}
  T: {at: [10.1, 1], kind: host, label: "T 203.0.113.1"}
links:
  - {a: CE1, b: PE1, label: "172.16.1.0/24\n(3.2, MD5)"}
  - {a: PE1, b: P1}
  - {a: P1, b: PE2}
  - {a: P1, b: PE3}
  - {a: P1, b: RR1}
  - {a: PE2, b: X1, label: "172.16.2.0/24\n(3.3, TCP-AO)"}
  - {a: PE3, b: X2, label: "172.16.3.0/24\n(3.1, GTSM)"}
  - {a: X1, b: T}
  - {a: X2, b: T}
  - {a: X1, b: X2}
frames:
  - {label: "AS 65000", nodes: [PE1, P1, RR1, PE2, PE3]}
  - {label: "AS 65100", nodes: [X1, X2, T]}
:::

BGP runs over TCP, so making a packet that affects the session does not require speaking BGP. To PE3, a TCP segment that
arrives at its port 179 from 172.16.3.1 is a segment from X2. The source address is a value the sender writes in, and
packets reach PE3's 172.16.3.254 even from T, which sits beyond X2.

Two things can happen. PE3 accepts a forged segment (a TCP reset, for example) and the session goes down; or a flood of
segments keeps the CPU that runs BGP busy. The M6 configuration has no way to check that an arriving segment really
came from X2. If the address matches, it is X2.

### 1.2 What came before: ACLs and MD5

The first way is to filter by address. An infrastructure ACL (M12) at the edge of the provider network lets through
only the packets addressed to the infrastructure that are needed, such as BGP with the neighbors. LPTS in IOS XR (M2)
puts BGP from configured peers into a flow of its own and gives other packets for BGP a small allowance.

Both decide by the addresses and ports in the packet. A packet with 172.16.3.1 written as its source cannot be told
apart from a real packet from X2. Forging it takes writing one address.

The second way is MD5 authentication (RFC 2385). Both ends are configured with the same password, and each TCP segment
carries an MD5 digest computed with the password mixed in. A segment made by anyone who does not know the password has
the wrong digest and is dropped. It works between IOS XR and IOS XE as well (section 3.2).

It has weak points. RFC 5925 (TCP-AO), written to replace MD5 authentication, lists stronger MACs, protection against
replays even on long-lived sessions, and key IDs that let the keys be changed without losing segments. MD5
authentication has no key ID: during a key change, segments in transit are lost, or arriving segments have to be tried
against several keys.

And every forged segment still has its digest computed before it is dropped. Checking starts with computing.

### 1.3 The answer: check the distance with the TTL, and sign the segments

- **Check the distance with GTSM**: both ends send with TTL 255, and the receiver drops what arrives with a TTL below a
  set value. A packet from the directly connected neighbor arrives still at 255; a packet made beyond the link cannot
  arrive at 255. Only the TTL in the IP header is looked at, and no key has to be computed.
- **Sign the segments with TCP-AO**: the successor of MD5 authentication (RFC 5925). It computes a MAC with a key from a
  key chain and an algorithm such as AES-128-CMAC-96, and a KeyID tells the receiver which key was used.

The two do different jobs. RFC 5082 presents GTSM as a simple protection against attacks on the CPU and says it is no
substitute for authentication. Packets forged on the same link, and replays, are not stopped by the TTL. All of them
are configured on both ends: GTSM and MD5 authentication on one end only leave the session down, and TCP-AO does not
come up unless the key IDs at the two ends agree (sections 2.1, 3.2 and 3.4).

## 2. How it works

Section 2.1 follows the TTL of one packet arriving at PE3. Sections 2.2 and 2.3 follow one TCP segment from the moment it
is sent with a digest or a MAC until the receiver has checked it.

### 2.1 Checking the neighbor with the TTL: GTSM

The TTL of an IP packet drops by 1 each time a router forwards it, and a packet whose TTL reaches 0 is dropped. The
destination router does not forward the packet, so it does not decrement the TTL of packets addressed to itself. The
TTL on arrival tells how many routers the packet passed on the way. Provided the value it was sent with is known.

eBGP packets are normally sent with TTL 1: a value that reaches the directly connected neighbor and is not forwarded
beyond it. The receiver does not check the TTL that arrives. CE1, which does not use GTSM, shows `Outgoing TTL 1` and
`Mininum incoming TTL 0` (an excerpt; the spelling is as displayed).

```console
CE1#show ip bgp neighbors 172.16.1.254
...
Connection is ECN Disabled, Mininum incoming TTL 0, Outgoing TTL 1
```

TTL 1 is a value that keeps a packet from going too far. A forged packet made far away is accepted just like a real
one, as long as some TTL is left when it arrives. It limits where a packet goes; it does not check where it came from.

GTSM (RFC 5082) turns this around. Both ends send with TTL 255. A packet from the directly connected neighbor has no
router in between and arrives at 255. A packet from one router further away loses 1 at that router and arrives at 254.
255 is the largest TTL there is, so a packet made beyond the link cannot arrive at 255. The receiver accepts, from that
neighbor, only packets with TTL 255.

:::topo
nodes:
  T: {at: [0, 0], kind: host, label: "T (beyond X2)"}
  X2: {at: [3, 0], label: "X2 (directly connected)"}
  PE3: {at: [6, 0], label: "PE3 (ttl-security)"}
links:
  - {a: T, b: X2, label: "T sends with TTL 255"}
  - {a: X2, b: PE3, label: "sent by X2: 255 → accepted\nsent by T: 254 → dropped"}
:::

RFC 5082 assumes that both ends use GTSM. For neighbors a few hops apart, such as between loopbacks, a non-normative
appendix describes accepting a range down from 255 by a set number (for example 254 or 255).

IOS XR and IOS XE write the same idea in different ways. `ttl-security` under an IOS XR neighbor takes no hop count: it
sends with TTL 255 and accepts only 255. The `?` list has no number argument either.

```console
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#ttl-security ?
  disable              (Deprecated from 7.4.1) Replaced by inheritance-disable
  inheritance-disable  Prevent ttl-security from being inherited from the parent
  <cr>
```

IOS XE's `neighbor <address> ttl-security hops <1-254>` accepts 255 minus the hop count and above. With `hops 1` that is
254 and above, and X2 shows `Mininum incoming TTL 254, Outgoing TTL 255` (section 3.4). It is the strictest value IOS XE
can take, but since it lets 254 through, a packet from one more router beyond the neighbor also passes the TTL check.

On the TTL it sends, the IOS XE 17.x guide says that `ttl-security hops` secures the incoming direction only and has no
effect on outgoing packets. IOS XE 17.15 sends with 255, as RFC 5082 requires. A packet capture showed the same: the TTL
was 1 before the command and 255 after it (Appendix, section 6.1).

On one end only, no TCP connection is made. With `ttl-security` on PE3 alone and the session reset, X2 keeps sending
with TTL 1 and PE3 drops those packets. PE3's SYN, sent with TTL 255, is answered by X2 with TTL 1, and PE3 drops that
answer too. PE3 stays `Active` and X2 stays `Idle` (an excerpt; the configuration is in section 3.1).

```console
RP/0/RP0/CPU0:PE3#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     277     227          330    0    0 00:14:30          4
172.16.3.1        0 65100     105     166            0    0    0 00:00:41  Active
X2#show ip bgp neighbors 172.16.3.254
BGP neighbor is 172.16.3.254,  remote AS 65000, external link
  BGP version 4, remote router ID 0.0.0.0
  BGP state = Idle, down for 00:02:29
...
  Last reset 00:02:29, due to Active open failed
...
  No active TCP connection
```

One end accepts only 255 and the other sends only 1, so the TCP three-way handshake never completes. The ASR 9000
Routing Command Reference says that with the command on one end only the session progresses as far as OpenSent or
OpenConfirm and goes down at the hold time; on this board it stopped before TCP (Appendix, section 6.1).

IOS XR's `ttl-security` protects eBGP sessions; the Command Reference says it is not supported for iBGP neighbors.

### 2.2 Signing the TCP segments: MD5 and TCP-AO

With MD5 authentication (RFC 2385) the sender puts a 16-byte MD5 digest on each segment as a TCP option. The digest is
computed over the TCP pseudo-header (the source and destination addresses and so on), the TCP header without options,
the data, and the password agreed by both ends.

The receiver does the same computation with its own password and compares the result with the digest that arrived. A
segment that does not match is dropped without any reply. There is no mechanism for the two ends to negotiate whether to
use it. With the password on one end only, that end drops segments without a digest and the session does not come up
(section 3.2).

TCP-AO (RFC 5925) is the TCP option that replaces MD5 authentication. Each segment carries three things: KeyID,
RNextKeyID and the MAC. The KeyID is the number of the key used for the MAC, and the RNextKeyID is the number of the key
the sender would like to receive next. With these two the ends tell each other which key to use during a key change, and
keys are changed without losing segments.

The MAC is not computed with the key string itself. From the key string (the master key, in the RFC's words), the
addresses and ports at both ends of the connection and the initial sequence numbers of both sides, a key per connection
(the traffic key) is made and used. The same key string gives a different key on another connection, so a segment from
an earlier connection carried into the current one does not pass. The algorithms available on IOS XR are HMAC-SHA-1-96
and AES-128-CMAC-96.

Whether the other TCP options go into the MAC is also part of each key's agreement in RFC 5925. IOS XR and IOS XE set it
on the neighbor's `ao` line (include-tcp-options). If the two ends compute over different ranges, the MACs do not match,
so they must agree. RFC 5925 does not allow TCP-AO and MD5 authentication on the same connection at the
same time.

An IOS XR neighbor has three methods. `password` is RFC 2385 MD5 authentication and works with IOS XE's
`neighbor … password`. `keychain` is a different method that uses a key chain: Cisco's documents say it follows
draft-bonica-tcp-auth-05 and that a `keychain` on one end and a `password` on the other does not work.

`ao` is TCP-AO. A neighbor can use only one of them, and a second one is rejected at commit (section 3.4).

With the same string as a `keychain` on PE2 (algorithm HMAC-MD5) and as a `password` on X1, the session did not come up.
X1 logs the following lines (an excerpt):

```console
*Nov 21 08:57:13.944: %TCP-6-BADAUTH: No MD5 digest from 172.16.2.254(25975) to 172.16.2.1(179) tableid - 0
*Nov 21 08:57:21.944: %TCP-6-BADAUTH: No MD5 digest from 172.16.2.254(25975) to 172.16.2.1(179) tableid - 0
```

PE2's segments carry no RFC 2385 digest. The same string on both ends does not produce a matching digest when the
methods differ.

### 2.3 The TCP-AO keys: key chain, KeyID, SendID and ReceiveID

In RFC 5925 each TCP-AO key has two IDs. The SendID is the value put in the KeyID field of outgoing segments. The
ReceiveID (RecvID, in the RFC's words) is the value matched against the KeyID of arriving segments. Both are 0 to 255.

The KeyID of the segments you send is the value the other end matches, so your SendID must equal the other end's
ReceiveID, and the other way round. In the example of section 3.3, PE2 has SendID 12 and ReceiveID 21, and X1 has send-id
21 and recv-id 12: the pairs cross. The number you send is the number the other end receives.

:::topo
nodes:
  PE2: {at: [0, 0], label: "PE2  SendID 12 / ReceiveID 21"}
  X1: {at: [4.5, 0], label: "X1  send-id 21 / recv-id 12"}
links:
  - {a: PE2, b: X1, label: "PE2 → X1: KeyID 12\nX1 → PE2: KeyID 21"}
:::

The keys themselves live in a key chain: a named list of keys, each with a number, a key string, an algorithm, a period
for sending (send-lifetime) and a period for accepting (accept-lifetime). The NCS 5500 BGP guide requires the two periods
to have the same values for TCP-AO. Both the example on this page and the tasks use one key with no end date
(`infinite`).

On IOS XR, TCP-AO is built in three places:

- The key chain (`key chain <name>` → `key <number>`): the key string, the algorithm and the two periods.
- `tcp ao` → `keychain <name>` → `key <number> SendID <n> ReceiveID <n>`: the two IDs of that key.
- `ao <name> include-tcp-options enable` under the BGP neighbor: which key chain this session uses, and whether the TCP
  options go into the MAC.

The key chain and `tcp ao` are tied together by the key number (key 3 in the example). What goes into a segment's KeyID
field is not this number but the SendID. In the example, PE2 and X1 both use key number 3.

On IOS XE, the key chain itself is made a TCP key chain (`key chain <name> tcp`). Under the key come `send-id`, `recv-id`,
`key-string` and `cryptographic-algorithm`, so the IDs live in the key chain too.

The key string is 32 or 64 hexadecimal digits. The IOS XE guide says that IOS XE's `aes-128-cmac` works with IOS XR's
`AES-128-CMAC-96`. On the neighbor it is `neighbor <address> ao <name> include-tcp-options`.

If the IDs do not cross, the session does not come up. With send-id 12 and recv-id 21 on X1 as well, PE2 refuses the
segments from X1 and logs `%IP-TCP-3-BADAUTH : Invalid AO digest …` (section 3.4). Even with the key string and the
algorithm matching.

## 3. Configuring it in IOS XR

The configuration examples use sessions and values other than the tasks': GTSM on PE3–X2 (section 3.1), MD5
authentication on PE1–CE1 (section 3.2) and TCP-AO on PE2–X1 (section 3.3). Each example gives the IOS XR configuration
and then the IOS XE configuration of the other end.

### 3.1 The GTSM configuration

On IOS XR it is one line under the neighbor, on IOS XE one line under `router bgp`, and only IOS XE writes a hop count.
Adding it leaves an established session as it is until the session is reset (the Command Reference also says to clear
the session with `clear bgp`). Configured one end at a time, the session stays down until the second end is done
(section 2.1).

:::config PE3 — on the session with X2, accept only what arrives with TTL 255
router bgp 65000
 neighbor 172.16.3.1                          ## X2
  ttl-security                                ## Send with TTL 255 and accept only 255. Takes no hop count
 !
!
:::

:::config X2 (IOS XE) — on the session with PE3, accept only TTL 254 and above
router bgp 65100
 neighbor 172.16.3.254 ttl-security hops 1    ## Accept 255 − 1 = 254 and above, and send with TTL 255
:::

After committing on PE3 and resetting the session (the state in section 2.1), X2 was configured as well and the session
was reset from X2. PE3 receives two routes from X2 (an excerpt):

```console
RP/0/RP0/CPU0:PE3#clear bgp 172.16.3.1
X2#clear ip bgp 172.16.3.254
RP/0/RP0/CPU0:PE3#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     282     231          334    0    0 00:15:18          4
172.16.3.1        0 65100     113     170          334    0    0 00:00:37          2
```

### 3.2 The MD5 configuration

On IOS XR it is `password` under the neighbor, on IOS XE `neighbor … password`, with the same string on both ends. The
`clear` in IOS XR means the password is typed in plain text; the running configuration keeps it in the `encrypted`
form.

:::config PE1 — put an MD5 digest on the TCP segments of the session with CE1
router bgp 65000
 neighbor 172.16.1.1                          ## CE1
  password clear CUST-65001                   ## clear = typed in plain text. The running configuration keeps the encrypted form
 !
!
:::

:::config CE1 (IOS XE) — use the same password
router bgp 65001
 neighbor 172.16.1.254 password CUST-65001    ## The same string as on PE1
:::

With the password on PE1 alone and the session reset, both PE1 and CE1 stayed `Active`. CE1, which has no password,
logs nothing (an excerpt).

```console
RP/0/RP0/CPU0:PE1#clear bgp 172.16.1.1
RP/0/RP0/CPU0:PE1#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     352     119          393    0    0 00:16:12          2
172.16.1.1        0 65001     152     210            0    0    0 00:00:36  Active
CE1#show ip bgp summary
...
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
172.16.1.254    4        65000       0       0        1    0    0 00:00:38 Active
CE1#show logging | include BADAUTH|TCP-6
CE1#
```

With the password on CE1 as well and the session reset from CE1, it came up (an excerpt).

```console
CE1#clear ip bgp 172.16.1.254
RP/0/RP0/CPU0:PE1#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     352     120          395    0    0 00:16:59          2
172.16.1.1        0 65001     157     215          395    0    0 00:00:30          2
RP/0/RP0/CPU0:PE1#show running-config router bgp 65000 neighbor 172.16.1.1
router bgp 65000
 neighbor 172.16.1.1
  remote-as 65001
  password encrypted 1434273838497C7E747862
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
  !
 !
!
```

### 3.3 The TCP-AO configuration

The IOS XR configuration is three blocks that refer to each other by the key chain name (UPLINK-AO) and the key number
(3). The other end, X1 (IOS XE), has two blocks. The figure follows one segment sent from X1 to PE2 until PE2 has checked
it and answered. The numbers in the figure match the notes of the configuration examples below. Rest the pointer on a
number in the figure (or tap it on a phone) to see that part of the configuration.

:::walk
legend: "A TCP segment from X1 to PE2, and PE2's answer. Orange box: the TCP-AO option. Blue numbers: the configuration blocks."
rows:
  - panel: X1
    sub: IOS XE (the sender)
    items:
      - ref: 5
        head: "**The neighbor** `neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options`"
        say: ["Puts TCP-AO on the segments of the session with PE2, with the TCP options in the MAC"]
      - ref: 4
        head: "**The TCP key chain** `key chain UPLINK-AO tcp` → `key 3`"
        say: ["Puts its send-id, 21, in the KeyID", "Computes the MAC with the key string and aes-128-cmac"]
  - wire:
      - "[[IP  → 172.16.2.254]] [[TCP  → 179]] [[!TCP-AO  KeyID 21  MAC]]"
      - "_X1 → PE2"
  - panel: PE2
    sub: IOS XR (the receiver)
    items:
      - ref: 3
        head: "**The BGP neighbor** `ao UPLINK-AO include-tcp-options enable`"
        say: ["Segments of the session with 172.16.2.1 are checked with UPLINK-AO"]
      - ref: 2
        head: "**The key IDs** `tcp ao` → `keychain UPLINK-AO`"
        say: ["Matches the arriving KeyID 21 against the keys' ReceiveID"]
        match:
          - ["key 3 SendID 12 ReceiveID 21", true, "taken → key 3"]
      - ref: 1
        head: "**The key chain** `key chain UPLINK-AO` → `key 3`"
        say: ["Computes the MAC again with the same key string and AES-128-CMAC-96, and compares it with the MAC that arrived", "+Match → handed to TCP"]
  - wire:
      - "[[IP  → 172.16.2.1]] [[TCP  179 →]] [[!TCP-AO  KeyID 12  MAC]]"
      - "_PE2's answer. The KeyID is its SendID, 12"
  - {node: X1, say: ["~Checks it with key 3, whose recv-id is 12"]}
  - aside: "If the IDs do not cross (send-id 12 and recv-id 21 on X1 as well)"
    say: ["~X1's segments carry KeyID 12 → it does not match PE2's ReceiveID 21", "~PE2 logs `%IP-TCP-3-BADAUTH : Invalid AO digest …` and drops them. PE2 stays `Active`"]
  - aside: "If PE2 does not reset the session after ③ is added"
    say: ["~X1 closes the session because its configuration changed, but PE2 keeps the old session `Established`", "~`clear bgp 172.16.2.1` on PE2"]
:::

PE2 gets three things: the key chain, `tcp ao` and `ao` under the neighbor. The key chain and `tcp ao` are global
configuration, outside `router bgp`.

:::config PE2 — put an AES-128-CMAC-96 MAC on the segments of the session with X1, and check it
key chain UPLINK-AO                           ## ① The list of keys. tcp ao and the neighbor refer to it by this name
 key 3                                        ## ① The key number. Tied to key 3 in ②
  key-string clear 0F1E2D3C4B5A69788796A5B4C3D2E1F0   ## ① The key string. 32 hexadecimal digits, to suit IOS XE
  cryptographic-algorithm AES-128-CMAC-96     ## ① The MAC algorithm. Corresponds to IOS XE's aes-128-cmac
  accept-lifetime 00:00:00 january 01 2026 infinite   ## ① The period for accepting
  send-lifetime 00:00:00 january 01 2026 infinite     ## ① The period for sending. Same values as accept-lifetime
 !
!
tcp ao                                        ## ② The TCP-AO configuration (global)
 keychain UPLINK-AO                           ## ② The key chain of ①
  key 3 SendID 12 ReceiveID 21                ## ② KeyID 12 out, KeyID 21 in. Crossed with X1
 !
!
router bgp 65000
 neighbor 172.16.2.1                          ## ③ X1
  ao UPLINK-AO include-tcp-options enable     ## ③ TCP-AO on this session, with the TCP options in the MAC
 !
!
:::

X1 gets a TCP key chain and one line under the neighbor. The IDs are the reverse of PE2's.

:::config X1 (IOS XE) — use the same key and the crossed IDs
key chain UPLINK-AO tcp                       ## ④ A TCP key chain (the tcp at the end)
 key 3                                        ## ④ The key number
  send-id 21                                  ## ④ The KeyID it sends. Equal to PE2's ReceiveID
  recv-id 12                                  ## ④ The KeyID it accepts. Equal to PE2's SendID
  key-string 0F1E2D3C4B5A69788796A5B4C3D2E1F0 ## ④ 32 or 64 hexadecimal digits
  cryptographic-algorithm aes-128-cmac        ## ④ Corresponds to IOS XR's AES-128-CMAC-96
!
router bgp 65100
 neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options   ## ⑤ TCP-AO on the session with PE2. Including the options matches PE2
:::

Once both are committed, reset the session from PE2. A reset from X1 leaves PE2 holding the old session (section 3.4).

```console
RP/0/RP0/CPU0:PE2#clear bgp 172.16.2.1
RP/0/RP0/CPU0:PE2#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     307     163          407    0    0 01:26:24          2
172.16.2.1        0 65100     300     163          407    0    0 00:00:39          2
```

In the running configuration, the IOS XR key string appears in an encrypted form, `key-string password …`; `tcp ao`
appears as typed (an excerpt).

```console
RP/0/RP0/CPU0:PE2#show running-config key chain UPLINK-AO
key chain UPLINK-AO
 key 3
  accept-lifetime 00:00:00 january 01 2026 infinite
  key-string password 014320557E59225C02186C5C38534E45535453737D057D11610140234426507009
  send-lifetime 00:00:00 january 01 2026 infinite
  cryptographic-algorithm AES-128-CMAC-96
 !
!
RP/0/RP0/CPU0:PE2#show running-config tcp ao
tcp ao
 keychain UPLINK-AO
  key 3 SendID 12 ReceiveID 21
 !
!
```

### 3.4 Reading the output, and pitfalls

**GTSM**: IOS XR's `show bgp neighbor <neighbor>` ends with `TTL security is configured`. IOS XE's
`show ip bgp neighbors <address>` shows the hop count and the TTLs it accepts and sends (excerpts from PE3 and X2 after
section 3.1).

```console
RP/0/RP0/CPU0:PE3#show bgp neighbor 172.16.3.1

BGP neighbor is 172.16.3.1
 Remote AS 65100, local AS 65000, external link
 Remote router ID 10.100.255.2
  BGP state = Established, up for 00:00:37
...
  TTL security is configured
X2#show ip bgp neighbors 172.16.3.254
BGP neighbor is 172.16.3.254,  remote AS 65000, external link
  BGP version 4, remote router ID 10.255.0.3
  BGP state = Established, up for 00:00:39
...
  External BGP neighbor may be up to 1 hop away.
...
Connection is ECN Disabled, Mininum incoming TTL 254, Outgoing TTL 255
```

- `TTL security is configured`: IOS XR shows only that it is configured. It accepts 255 only, so no number is shown.
- `External BGP neighbor may be up to 1 hop away.`: what `hops 1` looks like.
- `Mininum incoming TTL 254`: the lowest TTL accepted. On a session without GTSM it is 0 (section 2.1).
- `Outgoing TTL 255`: the TTL sent. On a session without GTSM it is 1.

**MD5 authentication**: IOS XE shows `md5` in the `Option Flags` of the TCP connection. IOS XR's `show bgp neighbor` has
no line about the password; look at the running configuration (section 3.2).

```console
CE1#show ip bgp neighbors 172.16.1.254
...
Option Flags: nagle, path mtu capable, md5, win-scale
```

**TCP-AO**: on IOS XR, `show tcp authentication keychain <name>` shows whether the keys in the key chain can be used.

```console
RP/0/RP0/CPU0:PE2#show tcp authentication keychain UPLINK-AO

Keychain name: UPLINK-AO, configured for tcp-ao
Desired key: 3
Total number of keys: 1
Key details:
    Key ID: 3, Active, Valid
Total number of usable (Active & Valid) keys: 1
    Keys: 3, 
```

When the IDs were not crossed and the session did not come up, PE2 showed the same `Key ID: 3, Active, Valid`. This
display does not check whether the IDs agree with the other end. A valid key and an agreeing neighbor are two separate
things.

On IOS XE, `show ip bgp neighbors <address>` shows the neighbor's configuration and the key the TCP connection is using
(an excerpt from X1).

```console
X1#show ip bgp neighbors 172.16.2.254
...
  AO keychain UPLINK-AO include-tcp-options
...
Option Flags: nagle, path mtu capable, win-scale, TCP AO
...
TCP AO Key chain: UPLINK-AO

TCP AO Current Key:
 Id: 3, Send-Id: 21, Recv-Id: 12
 Include TCP Options: Yes
 Accept AO Mismatch: No

TCP AO Next Key:
 Id: 3, Send-Id: 21, Recv-Id: 12
 Include TCP Options: Yes
 Accept AO Mismatch: No
```

- `AO keychain UPLINK-AO include-tcp-options`: the neighbor's configuration. It is shown even when the session is not up.
- `Option Flags: … TCP AO`: this TCP connection uses TCP-AO. With MD5 authentication it is `md5`.
- `TCP AO Current Key`: the current key and its two IDs. There is one key, so `TCP AO Next Key` is the same key 3.
- This IOL (IOS XE 17.15) does not accept `show tcp ao key-chain <name>` (`% Invalid input detected at '^' marker.`).

| Command | What to look at |
|---|---|
| `show bgp summary` (IOS XR) | Whether the neighbor's line shows a state such as `Active` or a number of routes received |
| `show bgp neighbor <neighbor>` (IOS XR) | `BGP state`; with GTSM, `TTL security is configured` at the end |
| `show tcp authentication keychain <name>` (IOS XR) | Whether the TCP-AO key is `Active, Valid` |
| `show running-config key chain`, `show running-config tcp ao` (IOS XR) | The key configuration, and each key's SendID and ReceiveID |
| `show ip bgp neighbors <address>` (IOS XE) | `Mininum incoming TTL` and `Outgoing TTL`; `md5` or `TCP AO` in `Option Flags`; the IDs in `TCP AO Current Key` |
| `show logging` (both) | `BADAUTH` (a digest or MAC that does not match), `AO_KEYCHAIN` |

**What failures look like**: if the IDs are not crossed (send-id 12 and recv-id 21 on X1 as well), PE2 keeps the session
`Active` and logs `Invalid AO digest`. X1 logs an `AO_KEYCHAIN` line (excerpts).

```console
RP/0/RP0/CPU0:PE2#show logging last 15
...
RP/0/RP0/CPU0:Nov 21 11:07:41.785 UTC: tcp[144]: %IP-TCP-3-BADAUTH : Invalid AO digest from 172.16.2.1:27110 to 172.16.2.254:179 for vrf:default (0x60000000) 
...
X1#show logging | include AO|TCP
...
*Nov 21 11:07:41.785: %BGP-4-AO_KEYCHAIN: Failed to set TCB AO properties
```

On IOS XE, the IDs of a key that a neighbor is using cannot be changed as they are. Remove the neighbor's `ao` first,
fix the key, and put `ao` back. Write the removal exactly as configured, down to `include-tcp-options`: a partial
`no neighbor … ao <name>` gives `%BGP: No match to an existing config command`, and a key chain in use cannot be
deleted. A key in use cannot be changed while it is in use.

```console
X1(config)#key chain UPLINK-AO tcp
X1(config-keychain-tcp)#key 3
X1(config-keychain-tcp-key)#send-id 21
% Key 3 on key-chain UPLINK-AO is in use and cannot be modified
X1(config-keychain-tcp-key)#recv-id 12
% Key 3 on key-chain UPLINK-AO is in use and cannot be modified
```

```console
X1(config)#router bgp 65100
X1(config-router)#no neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options
X1(config-router)#exit
X1(config)#key chain UPLINK-AO tcp
X1(config-keychain-tcp)#key 3
X1(config-keychain-tcp-key)#send-id 21
X1(config-keychain-tcp-key)#recv-id 12
X1(config-keychain-tcp-key)#exit
X1(config-keychain-tcp)#exit
X1(config)#router bgp 65100
X1(config-router)#neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options
```

IOS XR does not bring down an established session when protection is added. The Command Reference says that adding a
`password` does not end the existing session at once, and that the session ends when the hold time runs out. When
TCP-AO was added, X1 closed the session because its configuration had changed, but PE2 stayed `Established`; the last
thing it had received from X1 was 1 minute 52 seconds earlier (an excerpt).

```console
RP/0/RP0/CPU0:PE2#show bgp neighbor 172.16.2.1

BGP neighbor is 172.16.2.1
 Remote AS 65100, local AS 65000, external link
 Remote router ID 10.100.255.1
  BGP state = Established, up for 00:03:18
...
  Last read 00:01:52, Last read before reset 00:06:27
X1#show ip bgp summary
...
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.100.255.2    4        65100     140     143      199    0    0 01:15:55        3
172.16.2.254    4        65000       0       0        1    0    0 00:00:51 Idle
X1#show logging | include AO|TCP-
...
*Nov 21 10:57:41.542: %BGP-5-NBR_RESET: Neighbor 172.16.2.254 reset (TCP AO config change)
```

`clear ip bgp 172.16.2.254` on X1 left PE2 `Established` all the same. `clear bgp 172.16.2.1` on PE2 resets the session
with the new configuration. The old session carries on regardless of the new configuration.

Adding a second method to an IOS XR neighbor is rejected at commit. Here PE1 already has a `password`, and the commit
creates the key chain CUST-KC and adds `keychain CUST-KC` to the same neighbor (an excerpt).

```console
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#keychain CUST-KC
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#commit
% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted. Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#show configuration failed
!! SEMANTIC ERRORS: This configuration was rejected by 
!! the system due to semantic errors. The individual 
!! errors with each failed configuration command can be 
!! found below.
router bgp 65000
 neighbor 172.16.1.1
  keychain CUST-KC
!!% Change would result in neighbor (172.16.1.1) with Password and Keychain/AO based authentication together
 !
!
end
```

`ttl-security` together with `ebgp-multihop` is treated differently by the two systems. IOS XR accepts both and lists them
side by side in the running configuration (in the Command Reference, `ttl-security` wins). IOS XE refuses (excerpts).

```console
RP/0/RP0/CPU0:PE3#show running-config router bgp 65000 neighbor 172.16.3.1
router bgp 65000
 neighbor 172.16.3.1
  remote-as 65100
  ebgp-multihop 2
  ttl-security
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
  !
 !
!
X2(config-router)#neighbor 172.16.3.254 ebgp-multihop 2
Remove ttl-security before configuring ebgp-multihop
```

The pitfalls in short:

- **GTSM on one end**: no TCP connection is made (PE3 `Active`, X2 `Idle`). Configure both ends.
- **Trying to give IOS XR's `ttl-security` a number**: it takes no argument and accepts only 255. IOS XE uses `hops 1`
  (254 and above).
- **`ttl-security` with `ebgp-multihop`**: IOS XR accepts both; IOS XE refuses.
- **Resetting only from the IOS XE end**: IOS XR keeps the old session. Use `clear bgp <neighbor>` on the IOS XR end.
- **Taking IOS XR's `keychain` for MD5 authentication**: it does not work with IOS XE's `password`. MD5 authentication is
  `password`.
- **Two methods on one neighbor**: rejected at commit.
- **IDs that do not cross**: `Invalid AO digest`, and the session does not come up. Your SendID is the other end's
  ReceiveID.
- **Changing a key that IOS XE is using**: `in use and cannot be modified`. Remove the neighbor's `ao` first, with the
  line exactly as configured.
- **include-tcp-options on one end only**: the two ends compute the MAC over different ranges. Make them agree.
- **The IOS XE key string**: 32 or 64 hexadecimal digits. Write the same string on IOS XR.

Do Tasks M6-7 and M6-8 in lab **XRT-17**. As the lab starts, neither GTSM nor authentication is configured anywhere.

<p class="tolab"><a href="/_learn?id=XRT-17">Open lab XRT-17 in the workspace</a> — <a href="66-m6-practice-3.html">Tasks M6-7 and M6-8</a></p>

:::note
The configuration examples and output on this page were taken on XRT-17, at places and with values other than the
tasks' (IOS XRv 9000 26.1.1 on PE1; IOS XRd 26.1.1 on PE2 and PE3; IOS XE 17.15, IOL, on CE1, X1 and X2): GTSM on
PE3–X2, MD5 authentication on PE1–CE1 (password CUST-65001), TCP-AO on PE2–X1 (key chain UPLINK-AO, key 3). The
following come from another board on which PE1 to PE3, P1, RR1, CE1, X1, X2 and T have the same names and addresses as on
XRT-17; there PE1 ran IOS XRd 26.1.1, and a second ingress PE ran IOS XRv 9000 26.1.1. The `ttl-security ?` list (the
same on IOS XRv 9000). The TTL values sent (a packet capture on PE2–X1: before GTSM, TTL 1 from both PE2 and X1; 255 from
PE2 after `ttl-security`, and from X1 after `ttl-security hops 1`; with GTSM on PE2 alone, X1 answered PE2's SYN with
TTL 1, and X1's own SYNs had TTL 1). That an IOS XR `keychain` does not work with an IOS XE `password` (PE2–X1; it did
not connect with the MD5 algorithm or with HMAC-MD5, and the log in section 2.2 is from the HMAC-MD5 run). The `No match`
for `no neighbor … ao <name>`, and that a key chain in use cannot be deleted.
Sources: RFC 5082 (section 1 on the purpose and the relation to authentication; sections 2 and 3 on sending TTL 255 and
the accepted range; section 5.2 on the tunnel exception; Appendix A on neighbors a few hops apart); RFC 2385 (section 2
on how the digest is computed, dropping without a reply when it does not match, and the absence of negotiation);
RFC 5925 (the TCP-AO format, KeyID and RNextKeyID, section 3.1 on SendID and RecvID, the TCP option flag, section 5.2 on
traffic keys, and the ban on using it together with MD5). The Routing Command Reference for Cisco ASR 9000 Series
Routers (`ttl-security`: off by default, accepts only 255 and sends 255, the one-ended case, coexistence with
`ebgp-multihop`, not for iBGP, the need for `clear bgp`; `password`: the existing session lasting until the hold time;
`keychain`). The BGP Configuration Guide for Cisco NCS 5500, IOS XR 25.x (the TCP-AO procedure and algorithms, how SendID
and ReceiveID pair up, the two periods with the same values, one method per neighbor, `keychain` following
draft-bonica-tcp-auth-05 and not working with `password`). The System Security Command Reference for Cisco ASR 9000,
"Keychain Management Commands" (`tcp ao`, `key … SendID … ReceiveID …`, `ao` under the neighbor). The IP Routing
Configuration Guide, Cisco IOS XE 17.x: "Configuring BGP Neighbor Session Options" (`ttl-security hops`, 255 minus the
hop count, the statement that it has no effect on outgoing packets, not together with `ebgp-multihop`) and "BGP Support
for TCP Authentication Option" (`key chain … tcp`, the number of digits in the key string, `aes-128-cmac` and
`AES-128-CMAC-96`, MD5 authentication or TCP-AO but not both). All checked in November 2026.
The following come from measurements: no TCP connection with GTSM on one end; the TTL IOS XE sends; MD5 authentication
working between IOS XR and IOS XE; the wording of displays and logs; `show tcp authentication keychain` not showing an ID
mismatch; IOS XE refusing to change a key in use; IOS XR keeping the old session; this IOL not accepting
`show tcp ao key-chain`.
Where the documents and the devices differ: GTSM on one end (the documents say the session progresses as far as OpenSent
or OpenConfirm; on the devices no TCP connection was made), and the TTL sent by IOS XE's `ttl-security hops` (the
document says it has no effect on outgoing packets; the device sent 255). Both are in the Appendix, section 6.1.
:::
