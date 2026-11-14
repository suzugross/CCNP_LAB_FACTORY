# M13 — Counting flows and polling: NetFlow/IPFIX and SNMP

The previous pages configured the routers through models and streamed their counters with telemetry. This page covers
two older tools that providers still run on almost every router: flow records, which count who talks to whom through a
router, and SNMP, with which a management station reads the devices and is told when something happens.

It covers 5.8
(configure and verify NetFlow/IPFIX) and 5.10 (configure and verify SNMP v2c/v3) of the blueprint. On the XRT-15 board,
IOS XR has no NetFlow, so the flows are taken on PE2 (IOS XE) and SNMP is done on XR01.

## 1. What it is good for

### 1.1 The problem: who sends what, and is the backup link up?

Customer A sends its traffic through PE2 (GigabitEthernet2). The NMS team wants to know who is sending what: which of
customer A's hosts talk to which addresses, over which protocols, and how much. The interface counters on
GigabitEthernet2 give only totals: so many packets and bytes in, so many out. When the link fills up, the counters say
that it is full, not who filled it.

XR01's backup link to CE1 (GigabitEthernet0/0/0/2) carries nothing until the primary link fails. If it goes down, no
customer notices, and nobody finds out until the day it is needed. The NMS team wants every router to tell it at once,
without anyone logging in to look.

:::topo
nodes:
  CE1: {at: [0, 0], kind: host}
  PE2: [1.6, 1]
  XR01: [3.8, 1]
  SW1: [2.7, 2]
  SRV01: {at: [2.7, 3], kind: host, label: "SRV01 (NMS)"}
links:
  - {a: CE1, b: PE2, la: "Et0/0", lb: "Gi2"}
  - {a: PE2, b: XR01, la: "Gi1", lb: "Gi0/0/0/0"}
  - {a: CE1, b: XR01, label: "backup  Et0/1 – Gi0/0/0/2", t: 0.55}
  - {a: PE2, b: SW1, la: "Gi3 .2"}
  - {a: XR01, b: SW1, la: "Gi0/0/0/1 .1"}
  - {a: SW1, b: SRV01, label: "10.0.50.0/24  .10"}
:::

### 1.2 What came before: counters, polling and captures

- **Looking at each router**: `show interfaces` on one device at a time. Totals only, and only while someone is looking.
- **Polling the counters**: a station reads every interface's counters (the ifTable) every few minutes and draws graphs
  from the differences. That answers "how much" for many devices at once, but still not "who". Section 2.5 shows how it
  works.
- **Capturing packets**: copy the link's traffic to an analyser (SPAN, or tcpdump on a host). It shows everything,
  including who; but at a provider's rates there is far too much to keep, and a copy port is needed at every place you
  want to look.

### 1.3 The answers: flow records and a management protocol

- **Flow records** (NetFlow, IPFIX): the router itself sums the packets into conversations, one record per flow with its
  addresses, ports and counts, and sends the records to a collector. A record is far smaller than a capture and far richer
  than a counter. NetFlow is Cisco's; its version 9 introduced templates, and IPFIX is the IETF standard built from it.
- **SNMP** (Simple Network Management Protocol): one protocol for a station to read counters and state from every device
  (polling), and for a device to tell the station when something happens (traps). Version 2c is simple and unprotected;
  version 3 adds users, authentication and encryption.

Telemetry (the previous page) pushes the same counters more often and more efficiently. SNMP is still on almost every
device and in almost every NMS, and flow records answer a question that counters cannot.

## 2. How it works

### 2.1 A flow and the flow cache

A flow is a set of packets that pass one observation point (an interface, in one direction) and have the same values in
some fields of their headers. The fields that decide "same flow or not" are the **key** fields. Everything else a record
holds is a **non-key** field: counters that add up over the packets of the flow, the times of the first and the last
packet, and so on.

Traditional NetFlow used seven fixed keys: the source and destination addresses, the source and destination ports, the
protocol, the ToS byte and the input interface. Flexible NetFlow (IOS XE) lets you choose: `match` lines are keys and
`collect` lines are non-key fields. Fewer keys merge more packets into one flow (with only the two addresses as keys,
there is one flow per pair of hosts); more keys split them more finely.

The router keeps the flows in a **flow cache**. For each packet, the monitor takes the key fields, looks for an entry with
the same keys and adds to it; if there is none, it creates one.

Send 37 pings from CE1's Loopback100 to XR01's Loopback0:
all 37 echo requests have the same addresses, the same protocol (ICMP) and the same "ports", so they make one entry with
37 packets. ICMP has no ports; NetFlow puts the ICMP type and code where the destination port would be, and nfdump shows
them as `8.0` (echo request).

Example output (on SRV01; a record keyed on the addresses, the protocol, the ports and the input interface):

```console
$ nfdump -R /var/cache/nfdump/lab -o extended -c 10 'src ip 192.168.100.1'
Date first seen             Duration     Proto      Src IP Addr:Port          Dst IP Addr:Port     Flags Tos  Packets    Bytes      pps      bps    Bpp Flows
2026-11-10 14:27:08.500     00:00:00.049 ICMP     192.168.100.1:0     ->       10.255.0.1:8.0   ........   0       37    27676      755    4.5 M    748     1
Summary: total flows: 1, total bytes: 27676, total packets: 37, avg bps: 4.5 M, avg pps: 755, avg bpp: 748
```

The bytes are counted from the IP header on: 37 packets of 748 bytes are 27,676 bytes. The echo replies are a different
flow. Their source and destination are the other way round, and they do not pass the same observation point: they enter
PE2 from XR01 on GigabitEthernet1 and leave on GigabitEthernet2.

A key on the input interface keeps apart the same conversation arriving on two interfaces. The record does not carry the
interface's name but its SNMP number (the ifIndex, section 2.5), so the collector needs SNMP, or a table that the router
sends along, to turn the number into a name.

### 2.2 Timeouts: when a record leaves the cache

A flow has no end that the router can see (apart from TCP's FIN and RST). The router decides that a flow is over, and
exports its record, with timers:

- **Inactive timeout**: no packet of this flow for N seconds, so the flow is over. The default on the Catalyst 8000V is
  15 seconds.
- **Active timeout**: the flow is still running, but N seconds have passed since its entry was made. The router exports
  what it has so far and starts counting again. The default is 1800 seconds.
- **The cache is full**: the router ages out entries early to make room.

The ping train above left the cache 15 seconds after its last packet.

```console
PE2#show flow monitor FM-CUST cache format table
  Cache type:                               Normal (Platform cache)
  Cache size:                               200000
  Current entries:                               0
  High Watermark:                                1

  Flows added:                                   1
  Flows aged:                                    1
    - Inactive timeout    (    15 secs)          1

There are no cache entries to display.
```

Why the active timeout matters: a backup that runs for two hours is one flow. With the default of 1800 seconds, the
collector hears of it only every 30 minutes, and its graph shows nothing, then a 30-minute lump at once.

A requirement
such as "report a long flow at least every 60 seconds" is an active timeout of 60 seconds. The router then sends a record
for the flow every minute, each with the bytes and packets since the previous one (IPFIX names these counters
octetDeltaCount and packetDeltaCount). On the 8000V both timers take 1 to 604800 seconds.

### 2.3 Export: NetFlow v9 and IPFIX templates

NetFlow version 5 had one fixed record layout. Now that the fields are chosen per record, the collector has to be told
the layout. NetFlow v9 (RFC 3954) and IPFIX (RFC 7011) do it with **templates**:

1. The exporter sends a template: a number (the template ID, 256 or more) and the list of fields with their lengths.
2. Data records then name the template ID. A data record is only bytes; the collector cuts them up with the template.
3. Over UDP nothing guarantees that the template arrived, so the exporter sends it again at intervals (`template data
   timeout` on IOS XE). A collector that starts after the router, or missed the template, cannot decode the data until the
   next template arrives (RFC 7011 lets it hold the data records for a short time meanwhile).

Example output (PE2; the template of the record used in 2.1):

```console
PE2#show flow exporter FE-NMS templates
Flow Exporter FE-NMS:
Client: Flow Monitor FM-CUST
  Exporter Format: IPFIX (Version 10)
  Template ID    : 258
  Source ID      : 256
  Record Size    : 49
  Template layout
  _____________________________________________________________________________
  |                 Field                   |    ID | Ent.ID | Offset |  Size |
  -----------------------------------------------------------------------------
  | ipv4 source address                     |     8 |        |      0 |     4 |
  | ipv4 destination address                |    12 |        |      4 |     4 |
  | ip protocol                             |     4 |        |      8 |     1 |
  | transport source-port                   |     7 |        |      9 |     2 |
  | transport destination-port              |    11 |        |     11 |     2 |
  | interface input snmp                    |    10 |        |     13 |     4 |
  | counter bytes long                      |     1 |        |     17 |     8 |
  | counter packets long                    |     2 |        |     25 |     8 |
  | timestamp absolute first                |   152 |        |     33 |     8 |
  | timestamp absolute last                 |   153 |        |     41 |     8 |
  -----------------------------------------------------------------------------
```

Each row is a field with its number in the IANA registry of information elements (RFC 7012): 8 is sourceIPv4Address, 12
destinationIPv4Address, 4 protocolIdentifier, 7 and 11 the source and destination ports, 10 ingressInterface (the
ifIndex), 1 and 2 octetDeltaCount and packetDeltaCount, and 152 and 153 the times of the first and last packet in
milliseconds.

`long` makes a counter 8 bytes; a 4-byte byte counter wraps after 4 GB. The Source ID is the observation
domain, the part of the router that the records come from.

| | NetFlow v9 | IPFIX |
|---|---|---|
| Defined by | Cisco (RFC 3954, informational) | The IETF standard (RFC 7011) |
| Version in the header | 9 | 10 |
| The header also carries | Record count, router uptime, time, sequence number (counts export packets), source ID | Message length, export time, sequence number (counts data records), observation domain ID |
| Set IDs of template / options template | 0 / 1 | 2 / 3 |
| Field numbers | Cisco's list | The IANA registry; 1 to 127 are the same as in v9 |
| Vendor fields | No | An enterprise number with the field (the `Ent.ID` column) |
| Variable-length fields | No | Yes (strings such as URLs and application names) |
| Transport and port | UDP; the port is set on both ends (2055 is common) | SCTP (must be implemented), UDP, TCP; port 4739 (4740 with TLS or DTLS) |
| Times | Usually relative to the router's uptime (fields 22 and 21) | Usually absolute (152 and 153) |

IOS XE chooses with `export-protocol ipfix` or `export-protocol netflow-v9`; left out, it is v9. `show flow exporter`
shows IPFIX as `IPFIX (Version 10)`.

### 2.4 Sampling

PE2 looks at every packet. A provider's core router forwards hundreds of gigabits per second in hardware; looking up the
cache for every packet, and exporting a record for every short flow, would overwhelm the line card and the collector. So
such routers **sample**: they look at 1 packet out of N, chosen at random so that a regular pattern in the traffic does
not fool the count, and the collector multiplies the counts by N.

The totals of large flows come out right on average, while small flows may be missed entirely. That is enough for
planning capacity, billing by volume and spotting attacks, but not for proving that one particular packet passed.

IOS XR writes the rate in a `sampler-map` (`random 1 out-of N`) and names it on the interface together with the monitor
(section 3.2). IOS XE has the same idea (`sampler`, `mode random 1 out-of N`, `ip flow monitor M sampler S input`).

The
exporter can send the sampling rate to the collector as options data (`options sampler-table` on IOS XR), so that the
collector knows N.

### 2.5 SNMP: manager, agent, MIB

SNMP has three parts:

- **Manager**: the NMS (SRV01 in this lab). It asks, and it listens.
- **Agent**: a process on each device (XR01). It answers, and it reports.
- **MIB** (Management Information Base): the agreed set of things an agent can be asked about. Each item has an **OID**
  (object identifier), a path of numbers in one worldwide tree. 1.3.6.1 is "internet"; 1.3.6.1.2.1 is MIB-II, the
  standard set that every agent has; 1.3.6.1.4.1.9 is Cisco's own branch.

| Object | OID | What it holds |
|---|---|---|
| sysName | 1.3.6.1.2.1.1.5.0 | The device's name (`XR01`) |
| sysUpTime | 1.3.6.1.2.1.1.3.0 | Time since the agent started, in hundredths of a second |
| ifDescr | 1.3.6.1.2.1.2.2.1.2.*ifIndex* | The interface's name, one row per interface (ifTable) |
| ifInOctets | 1.3.6.1.2.1.2.2.1.10.*ifIndex* | Bytes received, 32 bits |
| ifHCInOctets | 1.3.6.1.2.1.31.1.1.1.6.*ifIndex* | Bytes received, 64 bits (ifXTable) |

The operations:

| Operation | Direction | What it does |
|---|---|---|
| Get | Manager → agent, UDP 161 | Reads the given OIDs |
| GetNext | Manager → agent | Reads the next OID in the tree. Repeated, it walks a table (`snmpwalk`) |
| GetBulk (v2c, v3) | Manager → agent | Many GetNexts in one request |
| Set | Manager → agent | Writes (needs write access) |
| Response | Agent → manager | The answer to the above |
| Trap, Inform | Agent → manager, UDP 162 | Reports an event (section 2.8) |

Example output (from SRV01: a Get of two objects, then a walk of ifDescr):

```console
$ snmpget -v2c -c PocRO 10.0.50.1 1.3.6.1.2.1.1.5.0 1.3.6.1.2.1.1.3.0
iso.3.6.1.2.1.1.5.0 = STRING: "XR01"
iso.3.6.1.2.1.1.3.0 = Timeticks: (2026) 0:00:20.26
$ snmpwalk -v2c -c PocRO 10.0.50.1 1.3.6.1.2.1.2.2.1.2 | head
iso.3.6.1.2.1.2.2.1.2.2 = STRING: "Null0"
iso.3.6.1.2.1.2.2.1.2.3 = STRING: "MgmtEth0/RP0/CPU0/0"
iso.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/0"
iso.3.6.1.2.1.2.2.1.2.7 = STRING: "GigabitEthernet0/0/0/1"
iso.3.6.1.2.1.2.2.1.2.8 = STRING: "Loopback0"
```

The tools print the OIDs as numbers (`iso.3.6.1…`) because SRV01 has no MIB files loaded; with them, the first line would
read `SNMPv2-MIB::sysName.0`.

The last number of each ifDescr row is the **ifIndex**, the agent's own number for the
interface. It is not derived from the name and differs from router to router: on XR01 in this lab, GigabitEthernet0/0/0/2
is 6. A reload may renumber the interfaces, which breaks graphs kept by number; `snmp-server ifindex persist` keeps the
numbers.

Counters are totals since the agent started. The manager reads them twice and divides the difference by the time between.
The 32-bit ifInOctets wraps after 4 GB, which at 1 Gb/s takes about 34 seconds, so with polls every five minutes use the
64-bit ifHCInOctets. 64-bit counters need v2c or v3.

### 2.6 SNMPv2c: a community and an access list

Versions 1 and 2c have no users. A request carries a **community** string, and the agent answers if it knows the
community: RO (read-only) allows reads, RW also writes. The string travels in clear text in every packet, so anyone who
sees the traffic can reuse it.

On IOS XR, an IPv4 access list on the community limits the sources that may use it. A request from a source that the
access list does not permit gets **no answer at all**; the manager simply times out. XR counts it in `show snmp` as
`Unknown community name`, the same as a wrong community, so the manager's side cannot tell the two apart.

Example output (XR01, after one request and its retry from a source that the access list did not permit):

```console
RP/0/RP0/CPU0:XR01#show snmp | include "Unknown community|Trap PDUs|pkts sent"
    2 Unknown community name
    0 Trap PDUs
             Number of pkts sent: 0
```

`show snmp group` lists a community as a group of its own, once for v1 and once for v2c, with the default view
`v1default` (all of 1.3.6.1) for reading and for notifications (section 3.4). Where XR01 answers SNMP at all is a separate
matter: while there is no MPP configuration, every enabled management protocol is accepted on every interface (M2). Limit
it with MPP as well as with the access lists.

### 2.7 SNMPv3: users, groups, views and the engine ID

SNMPv3 (RFC 3411 to 3418) replaces the community with two models:

- **USM** (User-based Security Model, RFC 3414): who the user is and how the messages are protected. A user has an
  authentication protocol and password (SHA here: every message carries a keyed hash, so a forged or altered message is
  rejected) and a privacy protocol and password (AES 128 here, RFC 3826: the contents are encrypted). There are three
  security levels: **noAuthNoPriv** (a user name only), **authNoPriv** (authenticated) and **authPriv** (authenticated and
  encrypted). IOS XR writes them `noauth`, `auth` and `priv`.
- **VACM** (View-based Access Control Model, RFC 3415): what the user may touch. A user belongs to a **group**. A group
  has a security level and up to three **views**, one each for reading, writing and notifications. A view is a set of OID
  subtrees, each `included` or `excluded`.

The passwords are not used as they are. The agent turns each password into a key and then **localises** the key with
its **engine ID**, the number that identifies this SNMP engine (RFC 3414, section 2.6). The same password gives a
different key on every router, so a key taken from one router opens no other.

Both ends must make the same key, so both must know the engine ID of the side that is **authoritative** for the message.
For a Get or a Set, that is the agent: the manager learns XR01's engine ID in a first exchange, and snmpget does this by
itself.

For a **trap**, the sender is authoritative and nothing is exchanged beforehand, so the receiver must already know
XR01's engine ID. That is why SRV01's trap receiver is configured with `createUser -e 0x<engine ID>`, and why the lab
fixes XR01's engine ID with `snmp-server engineID local`: if the ID changed, the receiver's keys would stop matching.

```console
RP/0/RP0/CPU0:XR01#show snmp engineid
SNMP engineID 00000009030000000aff0001
RP/0/RP0/CPU0:XR01#show running-config snmp-server
...
snmp-server user USR-V3 GRP-V3 v3 auth sha encrypted 1522040F253F3F2C796166 priv aes 128 encrypted 097C410A29171E045A5E57
...
```

A user is entered with `clear` passwords; after the commit, the running-config shows them `encrypted`. A wrong password
is refused with `snmpget: Authentication failure (incorrect password, community or key)`. The access list on a community
does not apply to v3: with SRV01 removed from it, v2c got no answer while v3 still read sysName.

### 2.8 Traps and informs

Polling finds a link that went down at the next poll, minutes later. Instead, the agent can send a **notification** to
the manager the moment something happens, to UDP port 162.

- **Trap**: sent once, with no acknowledgement. If it is lost, nobody knows.
- **Inform** (v2c and v3): the receiver answers with a Response, and the agent sends it again until it does, or gives up.
  For a v3 inform the receiver is the authoritative side, so the agent must learn the receiver's engine ID.

A notification is a list of variables. In the SNMPv2 form the first two are always sysUpTime.0 and snmpTrapOID.0, the name
of the notification (RFC 3416). linkDown is 1.3.6.1.6.3.1.1.5.3 and linkUp 1.3.6.1.6.3.1.1.5.4 (RFC 2863). XR01's traps
also carried the interface's ifIndex, ifDescr and ifType, and a Cisco-specific string, `down` or `up`.

Example output (the trap log on SRV01; each trap is one long line):

```console
2026-11-10 14:43:21 <UNKNOWN> [UDP: [10.0.50.1]:161->[10.0.50.10]:162]:
.1.3.6.1.2.1.1.3.0 = Timeticks: (283007) 0:47:10.07	.1.3.6.1.6.3.1.1.4.1.0 = OID: .1.3.6.1.6.3.1.1.5.3	.1.3.6.1.2.1.2.2.1.1.6 = INTEGER: 6	.1.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/2"	.1.3.6.1.2.1.2.2.1.3.6 = INTEGER: 6	.1.3.6.1.4.1.9.9.276.1.1.2.1.3.6 = STRING: "down"
2026-11-10 14:43:26 <UNKNOWN> [UDP: [10.0.50.1]:161->[10.0.50.10]:162]:
.1.3.6.1.2.1.1.3.0 = Timeticks: (283503) 0:47:15.03	.1.3.6.1.6.3.1.1.4.1.0 = OID: .1.3.6.1.6.3.1.1.5.4	.1.3.6.1.2.1.2.2.1.1.6 = INTEGER: 6	.1.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/2"	.1.3.6.1.2.1.2.2.1.3.6 = INTEGER: 6	.1.3.6.1.4.1.9.9.276.1.1.2.1.3.6 = STRING: "up"
```

Which events become notifications is chosen with `snmp-server traps …`; to whom, in which version and as which user, with
`snmp-server host`. For SNMPv3 the user's group must also allow notifications.

On XR01, a trap left only once the group had
a **notify view**: without it, `show snmp group` showed an empty `notifyview` and `show snmp` stayed at 0 Trap PDUs. The
command reference says that `snmp-server host` makes a notify view by itself and advises against setting one; on XR01 that
did not happen (the note gives the release).

### 2.9 Key points

- A flow is the packets with the same key fields at one point, in one direction. `match` is a key, `collect` a non-key
  field. One ping train is one flow.
- A record leaves the cache on the inactive timeout (15 s), on the active timeout (1800 s by default; "report every 60 s"
  is an active timeout of 60) or when the cache is full.
- v9 and IPFIX send a template first, and the collector cannot read the data without it. IPFIX is version 10, uses the
  IANA field numbers and UDP port 4739.
- Fast routers sample 1 packet out of N, and the collector multiplies by N.
- SNMP: the manager polls the agent's MIB on UDP 161; the agent sends traps and informs to UDP 162.
- v2c: the community travels in clear text. A source that the access list does not permit gets no answer
  (`Unknown community name`).
- v3: USM (authentication SHA, privacy AES, three levels) and VACM (a group with read, write and notify views). The keys are
  localised to the engine ID, so a trap receiver must know the sender's engine ID. On XR01, traps need the group's notify
  view.

## 3. Building it

### 3.1 Flexible NetFlow on IOS XE

Flexible NetFlow is built from four parts that refer to each other by name: the **record** (what makes a flow and what to
count), the **exporter** (where the records go, and in which format), the **monitor** (the cache that ties a record to one
or more exporters, with its timeouts), and the interface that the monitor is attached to, in a direction.

The example counts what customer A sends into the core, per ToS: it keys on the ToS byte instead of the ports, and
watches PE2's core-facing GigabitEthernet1 on output. The figure follows the 37 echo requests from CE1 through PE2 to
SRV01. Rest the pointer on a number in the figure (or tap it on a phone) to see that part of the configuration.

:::walk
legend: "Purple: inside PE2 only. Orange: what PE2 sends to the collector."
rows:
  - {node: CE1, kind: host, say: ["~ping 10.255.0.1 source Loopback100, 37 times, 748 bytes each"]}
  - {wire: "[[IP 192.168.100.1 → 10.255.0.1 ICMP 8.0]] _× 37, ToS 0"}
  - panel: PE2
    sub: Catalyst 8000V
    items:
      - say: ["~Enters on Gi2 (customer A); the route to 10.255.0.1 points out of Gi1. Not NetFlow"]
      - ref: 1
        head: "**Output on Gi1** `ip flow monitor FM-CORE output`"
        say: ["Shows each packet leaving Gi1 to the monitor; the packet goes on to XR01 as it is"]
      - ref: 2
        head: "**The monitor** `flow monitor FM-CORE`"
        say: ["Looks up its cache with the keys that its record names"]
      - ref: 3
        head: "**The record** `flow record FR-CORE`"
        say: ["Keys: ToS 0, ICMP, 192.168.100.1 → 10.255.0.1, output Gi1"]
        match:
          - ["packet 1", false, "no entry with these keys → a new entry"]
          - ["packets 2 to 37", true, "same keys → +1 packet, +748 bytes"]
      - say: ["[[~ToS 0 · ICMP · 192.168.100.1 → 10.255.0.1 · Gi1]] [[~37 pkts · 27676 B]]", "_the cache entry, with the times of the first and the last packet"]
      - ref: 2
        head: "**Timeouts** `cache timeout inactive 10` / `active 300`"
        say: ["10 s after the last ping the flow is over, and the entry leaves the cache"]
      - ref: 4
        head: "**The exporter** `flow exporter FE-V9`"
        say: ["NetFlow v9, from Loopback0 (10.255.0.2) to 10.0.50.10, UDP 4739"]
        then: ["→ the template (its ID and the list of fields), then the data record"]
  - {wire: "[[=UDP 10.255.0.2 → 10.0.50.10:4739]] [[!v9 template]] [[!data: 1 record]]"}
  - {node: SRV01, kind: host, say: ["nfcapd learns the template, decodes the record, writes a file a minute", "~`nfdump`: 1 flow, 37 packets, 27676 bytes"]}
  - aside: "The monitor on Gi1 input instead"
    say:
      - "~Gi1 input sees what comes back from XR01: [[IP 10.255.0.1 → 192.168.100.1 ICMP 0.0]]"
      - "~another flow; the 37 echo requests are not recorded"
  - aside: "The exporter to another port (`transport udp 2055`)"
    say:
      - "~nfcapd listens on UDP 4739 only, so the records are lost"
      - "~UDP has no acknowledgement: compare `Destination Port` in `show flow exporter`"
  - aside: "No `source` in the exporter"
    say:
      - "~The records leave from the exit interface's address: 10.0.50.2 (Gi3), not 10.255.0.2"
      - "~if the exit changes, the collector sees a different exporter"
:::

:::config fold PE2 — count the traffic into the core per ToS and export it with NetFlow v9
flow record FR-CORE                           ## ③ What makes a flow, and what to count
 match ipv4 tos                               ## Key: the ToS byte (the DSCP and ECN bits)
 match ipv4 protocol                          ## Key: ICMP, TCP, UDP and so on
 match ipv4 source address                    ## Key
 match ipv4 destination address               ## Key
 match interface output                       ## Key: the interface the packet leaves on
 collect counter bytes long                   ## Non-key: bytes, an 8-byte counter
 collect counter packets long                 ## Non-key: packets, an 8-byte counter
 collect timestamp absolute first             ## Non-key: the time of the first packet (a date, not uptime)
 collect timestamp absolute last              ## Non-key: the time of the last packet
!
flow exporter FE-V9                           ## ④ Where the records go
 destination 10.0.50.10                       ## SRV01
 source Loopback0                             ## Send from 10.255.0.2, whatever the exit interface
 transport udp 4739                           ## The port the collector listens on
 export-protocol netflow-v9                   ## The format; `ipfix` for IPFIX. Left out: v9
!
flow monitor FM-CORE                          ## ② The cache that ties the record to the exporter
 record FR-CORE
 exporter FE-V9                               ## More than one exporter may be named
 cache timeout active 300                     ## Report a running flow every 300 s
 cache timeout inactive 10                    ## A flow is over 10 s after its last packet
!
interface GigabitEthernet1                    ## ① Towards XR01 (the core)
 ip flow monitor FM-CORE output               ## Watch the packets leaving here
:::

Build the parts in the order record, exporter, monitor, interface: each part names the one before it. `template data
timeout` on the exporter sets how often the templates are sent again. IOS XE also has ready-made records, such as `record
netflow ipv4 original-input`, which has the seven traditional keys.

### 3.2 NetFlow on IOS XR, for reference

**On this lab's XR01 (XRd), and on XRv 9000 as well, NetFlow is not available.** There, the `flow` command configures BGP
FlowSpec, and `flow exporter-map` is rejected. This is why the flow task of this lab is on PE2.

Example output (XR01):

```console
RP/0/RP0/CPU0:XR01(config)#flow ?
  address-family  Address Family Identifier Type (IPv4/IPv6)
  apply-group     Apply configuration from a group
  exclude-group   Exclude apply-group configuration from a group
  local-install   Local installation of FlowSpec policy
  vrf             VRF configuration
  <cr>
RP/0/RP0/CPU0:XR01(config)#flow exporter-map FEM
                                  ^
% Invalid input detected at '^' marker.
```

On routers with NetFlow in their hardware, such as the ASR 9000, IOS XR builds it from three maps and one interface line.
The configuration below is the documented form, written for this board's addresses, to read and compare; it cannot be
tried in the lab.

:::config IOS XR on an ASR 9000 — sample 1 packet in 1000 on the core link and export IPFIX (not on XRd)
flow exporter-map FEM-NMS                     ## Where the records go
 version ipfix                                ## Or `version v9`
  template data timeout 300                   ## Send the templates again every 300 s
  options interface-table timeout 300         ## Also send the table of ifIndex and interface names
  options sampler-table timeout 300           ## and the sampling rate
 !
 transport udp 4739
 source Loopback0                             ## Required: without it the exporter stays disabled
 destination 10.0.50.10
!
flow monitor-map FMM-CORE                     ## The cache
 record ipv4                                  ## A predefined record, not built key by key
 exporter FEM-NMS                             ## Up to eight exporters
 cache entries 65535                          ## The default size
 cache timeout active 300                     ## The defaults are 1800 s (active) and 15 s (inactive)
 cache timeout inactive 15
!
sampler-map SM-1K                             ## The sampling rate
 random 1 out-of 1000                         ## 1 packet in 1000, chosen at random
!
interface GigabitEthernet0/0/0/0
 flow ipv4 monitor FMM-CORE sampler SM-1K ingress   ## The monitor, the sampler and the direction in one line
:::

The differences from IOS XE: the parts are maps; the record is chosen from predefined types; the interface line names a
sampler (the command reference shows it as required) and says `ingress` or `egress`.

Check it with `show flow monitor
FMM-CORE cache location 0/0/CPU0` (the cache is kept per line card), `show flow exporter-map FEM-NMS` and `show sampler-map
SM-1K`. The guide also advises against exporting through the management interface.

### 3.3 SNMP on IOS XR

The first `snmp-server` command starts the agent, SNMPv3 included. For v2c, a community and its access list are enough.
The example is for an operations station of the NMS team at 10.0.50.20 (it is not built in this lab).

:::config fold XR01 — let only the operations station read with SNMPv2c
ipv4 access-list OPS-HOSTS                    ## The sources that may use the community
 10 permit ipv4 host 10.0.50.20 any           ## The operations station
!
snmp-server community OPS-RO RO IPv4 OPS-HOSTS   ## Read-only; answers only the sources that OPS-HOSTS permits
:::

For SNMPv3 traps, six parts of XR01's configuration and one line on the receiver act on one event in turn. The figure
follows a linkDown from XR01 to the station; rest the pointer on a number (or tap it on a phone) to see that line of the
configuration.

:::walk
legend: "On the wire: the trap. Orange: what SNMPv3 adds. Every step on XR01 must pass, or nothing is sent."
rows:
  - panel: XR01
    sub: the agent
    items:
      - say: ["~GigabitEthernet0/0/0/2, the backup link to CE1, goes down"]
      - ref: 1
        head: "**Is the event wanted?** `snmp-server traps snmp linkdown`"
        say: ["A notification: linkDown (.1.3.6.1.6.3.1.1.5.3), with ifIndex 6, ifDescr and ifType"]
      - ref: 2
        head: "**To whom, and how?** `snmp-server host 10.0.50.20 traps version 3 priv ops-mon`"
        say: ["A trap to 10.0.50.20, UDP 162; SNMPv3 at authPriv, as the user ops-mon"]
      - ref: 3
        head: "**The user** `snmp-server user ops-mon OPS-V3 v3 auth sha … priv aes 128 …`"
        say: ["Its two passwords; it belongs to the group OPS-V3"]
      - ref: 4
        head: "**The group** `snmp-server group OPS-V3 v3 priv …`"
        match:
          - ["v3 priv", true, "the host line asks for priv: the level is met"]
          - ["notify OPS-ALL", true, "the group may receive notifications"]
      - ref: 5
        head: "**The notify view** `snmp-server view OPS-ALL 1.3.6.1 included`"
        match:
          - ["linkDown, ifIndex, ifDescr, ifType", true, "all under 1.3.6.1 → may be sent"]
      - ref: 6
        head: "**The keys** `snmp-server engineID local 00:00:00:09:03:00:00:00:0a:ff:00:01`"
        say: ["The passwords become keys localised to this engine ID", "The trap is signed (SHA) and encrypted (AES)"]
  - {wire: "[[=10.0.50.1 → 10.0.50.20:162]] [[!engine ID · user]] [[!signed · encrypted]]"}
  - panel: OPS
    sub: 10.0.50.20, snmptrapd
    items:
      - ref: 7
        head: "**Knows the sender** `createUser -e 0x00000009030000000aff0001 ops-mon …`"
        say: ["Makes the same keys from the same passwords and XR01's engine ID"]
        then: ["→ checks the signature, decrypts, and writes the trap to its log"]
  - aside: "Without `notify OPS-ALL` in ④"
    say:
      - "~`show snmp group`: notifyview empty. `show snmp`: 0 Trap PDUs. Nothing leaves XR01"
  - aside: "A receiver that does not know XR01's engine ID"
    say:
      - "~It cannot make XR01's keys: it can neither check nor decrypt the trap"
  - aside: "Polling with v2c from SRV01, which OPS-HOSTS does not permit"
    say:
      - "[[UDP 10.0.50.10 → 10.0.50.1:161 community OPS-RO]] ~no answer"
      - "~XR01 counts it as `Unknown community name` in `show snmp`"
:::

:::config fold XR01 — read the system group with SNMPv3 and send link traps at authPriv
snmp-server engineID local 00:00:00:09:03:00:00:00:0a:ff:00:01   ## ⑥ The engine ID (fixed in the lab; do not change it)
snmp-server view OPS-SYS 1.3.6.1.2.1.1 included   ## A view of the system group only (sysName, sysUpTime and so on)
snmp-server view OPS-ALL 1.3.6.1 included     ## ⑤ A view of everything under internet
snmp-server group OPS-V3 v3 priv read OPS-SYS notify OPS-ALL   ## ④ authPriv; reads the system group; may receive notifications
snmp-server user ops-mon OPS-V3 v3 auth sha clear OpsAuth-26 priv aes 128 clear OpsPriv-26   ## ③ Shown as `encrypted` after the commit
snmp-server host 10.0.50.20 traps version 3 priv ops-mon   ## ② Traps to the station as ops-mon, at authPriv
snmp-server traps snmp linkup                 ## ① The events that become notifications
snmp-server traps snmp linkdown               ## ①
snmp-server ifindex persist                   ## Keep the interface numbers across reloads
:::

:::config OPS (10.0.50.20) — the trap receiver for ops-mon (a snmptrapd configuration file)
createUser -e 0x00000009030000000aff0001 ops-mon SHA OpsAuth-26 AES OpsPriv-26   ## ⑦ The user, with XR01's engine ID (0x, no colons)
authUser log ops-mon priv                     ## Log the traps of ops-mon, at authPriv only
:::

The trap receiver on SRV01 in this lab (snmptrapd-lab) is configured the same way, for the user nms-trap. An inform is sent
with `informs` instead of `traps` on the host line. From IOS XR 25.4.x, DES and 3DES are no longer supported for privacy;
use AES.

### 3.4 Checking it

| What to look at | Command |
|---|---|
| The monitor on the interface, and its direction | `show flow interface <IF>` |
| The record, the exporter and the timeouts of a monitor | `show flow monitor <name>` |
| The flows now in the cache, and why flows left it | `show flow monitor <name> cache format table` |
| Where and how the records are sent | `show flow exporter <name>` |
| The fields the collector receives | `show flow exporter <name> templates` (section 2.3) |
| What was sent | `show flow exporter <name> statistics` |
| What reached the collector | On SRV01, `nfdump -R /var/cache/nfdump/lab -o extended '<filter>'` |
| The agent's counters (refused communities, traps sent) | `show snmp` |
| Groups and their views, users, trap hosts, engine ID | `show snmp group`, `show snmp user`, `show snmp host`, `show snmp engineid` |
| Reading from the NMS | On SRV01, `snmpget`, `snmpwalk` |
| What reached the trap receiver | On SRV01, `/var/log/snmptrapd-lab.log` |

Example output (PE2, a monitor on GigabitEthernet2 input that exports IPFIX):

```console
PE2#show flow interface GigabitEthernet2
Interface GigabitEthernet2
  FNF:  monitor:          FM-CUST
        direction:        Input
        traffic(ip):      on

PE2#show flow monitor
Flow Monitor FM-CUST:
  Description:       User defined
  Flow Record:       FR-CUST
  Flow Exporter:     FE-NMS
  Cache:
    Type:                 normal (Platform cache)
    Status:               allocated
    Size:                 200000 entries
    Inactive Timeout:     15 secs
    Active Timeout:       60 secs

    Trans end aging:   off

PE2#show flow exporter FE-NMS
Flow Exporter FE-NMS:
  Description:              User defined
  Export protocol:          IPFIX (Version 10)
  Transport Configuration:
    Destination type:       IP
    Destination IP address: 10.0.50.10
    Source IP address:      10.255.0.2
    Source Interface:       Loopback0
    Transport Protocol:     UDP
    Destination Port:       4739
    Source Port:            54542
    DSCP:                   0x0
    TTL:                    255
    Output Features:        Used

PE2#show flow exporter FE-NMS statistics
Flow Exporter FE-NMS:
  Packet send statistics (last cleared 00:01:01 ago):
    Successfully sent:         2                     (104 bytes)

  Client send statistics:
    Client: Flow Monitor FM-CUST
      Records added:           1
        - sent:                1
      Bytes added:             49
        - sent:                49
```

`Records added: 1` is the ping train of section 2.1, one flow; its 49 bytes are the record size of the template. On SRV01,
nfcapd starts a new file every minute, so a flow can take up to one or two minutes to appear in `nfdump` (in the run of
section 2.1, it was there within 50 seconds).

Example output (XR01, the SNMP side, after Task M13-6 and one flap of GigabitEthernet0/0/0/2):

```console
RP/0/RP0/CPU0:XR01#show snmp host
Notification host: 10.0.50.10 udp-port: 162  type: trap
user: nms-trap      security model: v3 priv
RP/0/RP0/CPU0:XR01#show snmp user
  User Name: nms-trap
  EngineId: localSnmpID
  storage-type: nonvolatile        active
RP/0/RP0/CPU0:XR01#show snmp | include "Trap PDUs|pkts sent|dropped"
    2 Trap PDUs
             Number of pkts sent: 2
          Number of pkts dropped: 0
    Number of Informs dropped: 0 
```

`show snmp host` shows the security level that XR01 really uses for each trap host, and `Trap PDUs` counts the traps sent:
here, one linkDown and one linkUp.

Example output (a router with a community `PocRO` and a v3 group `GRP-V3` that has no notify view):

```console
RP/0/RP0/CPU0:XR01#show snmp group
groupname: PocRO                         security model:snmpv1
readview : v1default                     writeview: 
notifyview: v1default
row status: active

groupname: PocRO                         security model:snmpv2c
readview : v1default                     writeview: 
notifyview: v1default
row status: active

groupname: GRP-V3                        security model:usm
readview : VIEW-ALL                      writeview: 
notifyview: 
row status: active
```

The community appears twice (v1 and v2c) with `v1default`. The v3 group has an empty `notifyview`: with this group, XR01
sends no v3 traps (section 2.8).

:::try
See that the community's access list does not touch SNMPv3. Do it after Task M13-6, and put things back at the end.

1. On SRV01, run `snmpget -v2c -c NMS-RO 10.0.50.1 1.3.6.1.2.1.1.5.0` and the SNMPv3 `snmpget` from the task's
   verification steps (user nms-trap). Both return `XR01`.
2. On XR01, delete the line of `NMS-ONLY` that permits SRV01 and commit. Run both commands again, then look at
   `show snmp | include "Unknown community"`.
3. Put the line back and commit.

An example result: with SRV01 removed from the access list, the v2c request ended in `Timeout: No Response from
10.0.50.1.`, while the v3 request still returned `STRING: "XR01"`. `Unknown community name` grew by two (the request and
its retry).
:::

### 3.5 Pitfalls

- **Compare `show snmp host` with the running-config.** On this release, changing an existing host line from `auth` to
  `priv` (typing the `priv` line over it, or removing the old line and adding the new one in the same commit) changed the
  running-config, but `show snmp host` kept `v3 auth`, and no traps arrived at the receiver, which accepts authPriv only.
  Remove the line and commit, then add it and commit.

```console
RP/0/RP0/CPU0:XR01#show running-config snmp-server host
snmp-server host 10.0.50.10 traps version 3 priv nms-trap

RP/0/RP0/CPU0:XR01#show snmp host
Notification host: 10.0.50.10 udp-port: 162  type: trap
user: nms-trap      security model: v3 auth
```

- **The level on the host line goes with the group's level.** With `auth` on the host line and a `priv` group, XR01 sent
  nothing (`Trap PDUs` stayed at 0).
- **The access list on a community does not protect SNMPv3.** v3 users are not restricted by it. To limit the interfaces on
  which XR01 answers at all, use MPP (M2).
- **Make the test event with a physical interface.** The linkDown and linkUp traps here were confirmed on GigabitEthernet
  interfaces, as in the lab's check. A loopback is not a reliable test (see the note).
- **The receiver must know the sender's engine ID.** If XR01's engine ID changes, the receiver's keys no longer match. Leave
  `snmp-server engineID local` alone in the lab.
- **AES, not DES.** From IOS XR 25.4.x, DES and 3DES are no longer supported for SNMPv3 privacy.
- **Give the collector time.** With a 15-second inactive timeout and nfcapd's one-minute files, a flow can take up to one
  or two minutes to appear. Look first at the router's cache and at `show flow exporter … statistics`.
- **Timeouts on IOS XE.** The 8000V's monitor takes `cache timeout active` and `inactive` from 1 to 604800 seconds. Without
  `export-protocol`, the exporter sends NetFlow v9, not IPFIX.
- **A record in use is locked.** A record that a monitor uses cannot be changed (`% Flow Record: Failed to field add: Object
  is in use`), and a monitor's record cannot be replaced by typing a new one
  (`% Flow Monitor: Failed to set record: Already there is an existing record configured`). Remove `record` from the monitor
  first. `export-protocol` cannot be changed while the exporter is in use.

## Practice

Do Tasks M13-5 and M13-6 in lab **XRT-15**.

<p class="tolab"><a href="/_learn?id=XRT-15">Open lab XRT-15 in the workspace</a> — <a href="e5-m13-practice-3.html">Tasks M13-5 and M13-6</a></p>

:::note
The output on this page was taken on the XRT-15 board (XR01 on IOS XRd 26.1.1, PE2 on Catalyst 8000V IOS XE 17.15.1a),
except the following, which come from the PoC board of this unit (the same addressing; one XR01 on XRv 9000 26.1.1 and one
on XRd 26.1.1, which behaved the same): the `snmpget` and `snmpwalk` with the community `PocRO`, `show snmp group`, the
`show running-config snmp-server` with `USR-V3`, the wrong-password and access-list tests, and `flow ?` on XR01.

The following are measurements: one ping train as one flow, its ageing after 15 seconds and the 50 seconds to nfdump;
NetFlow not available on XRd or XRv 9000 26.1.1 (XRd ships only the package `xr-netflow-stubs`; `flow` there is FlowSpec);
the community's access list (no answer, `Unknown community name`, no effect on v3); the notify view; the host line that keeps
`v3 auth` (XRd 26.1.1; not in the documentation); a host line at `auth` with a `priv` group sending nothing.

The locks on a
record in use were measured on IOS XE 17.15 on IOL, where the monitor also has no `cache timeout` at all and the record can
carry only uptime-based times (nfdump then shows the date 1970-01-01).

Two points were not confirmed on the device. A loopback's shutdown produced no trap, but at that time the group had no
notify view, so the test settles nothing. A receiver without the sender's engine ID was not tested on its own; the page
follows RFC 3414 there.

Where the documentation and the device differ: the System Management Command Reference says that `snmp-server host` creates
the notify view for its user and advises against setting one on the group; on XRd and XRv 9000 26.1.1, a group without a
notify view showed an empty `notifyview` and sent no v3 traps, and adding `notify` fixed it.

The NCS 5500 guide says that
SNMP answers only on management interfaces by default; on XRd and XRv 9000 26.1.1, XR01 answered on the NMS segment with no
MPP configuration, as M2 describes.

Sources: RFC 3954 (NetFlow v9), RFC 7011 (sections 3.1, 3.3.2, 3.4.1, 9.3 and 10.1), RFC 7012 and the IANA IPFIX
information element registry, RFC 3411 to 3418 (3414 USM, 3415 VACM, 3416 the PDUs, 3418 SNMPv2-MIB), RFC 3826 (AES),
RFC 1901 (v2c), RFC 2863 (IF-MIB, linkDown and linkUp). The Netflow Configuration Guide and Command Reference for the
ASR 9000 (IOS XR 7.9.x and 25.x: exporter-map, monitor-map, sampler-map, the defaults, the mandatory source interface),
the Network Services Configuration Guide for Cisco IOS XE 17.x (Flexible NetFlow, IPFIX export) and the Flexible NetFlow
chapter of the Catalyst 9500 IOS XE 17.17 guide (the default export protocol), the System Management Configuration Guide
for the NCS 5500 (IOS XR 26.x, Implementing SNMP: v3 enabled by the first command, DES and 3DES from 25.4.x, `ifindex
persist`) and the System Management Command Reference for the NCS 5500 (`snmp-server group`, `host` and `engineid`). All
checked in November 2026.
:::
