# M13 — Streaming state: gNMI, telemetry and TLS

The previous page changed the router's configuration through data models. This page goes the other way: it gets the
router's state out, as a stream. The router reads its own counters at a set interval and pushes them to a collector,
or a collector subscribes to them with gNMI. Both run over gRPC and are protected with TLS. It covers 5.7 of the
blueprint (configuring dial-in and dial-out with gRPC and gNMI, TCP, TLS and mutual TLS certificates). The board is
XRT-15; the part this page uses is drawn at the start of section 2.

## 1. What it is good for

### 1.1 The problem: a five-minute poll does not see a twenty-second burst

The NMS team wants to know how busy XR01's interfaces are. A link that carries 30% on average can still be full for
twenty seconds at a time, and those twenty seconds are when customers' packets are dropped. To see such a burst, the
counters have to be read every ten seconds or so, on every interface of every router.

Reading that often by asking is heavy. Every reading is a request and a reply, the router looks the values up one
object at a time, and the NMS has to keep a timer running for every router. With hundreds of routers, the NMS spends
its time asking, and the routers spend CPU answering.

### 1.2 What came before: SNMP polling and CLI scraping

- **SNMP polling**: the NMS asks the router for MIB objects (the input and output octets of each interface and so on)
  with GET or GETBULK, usually every five minutes. Walking a table of a few hundred interfaces takes many round trips.
  The values carry no time of their own; the NMS stamps them when the reply arrives. SNMP itself is on the page
  *Counting flows and polling*.
- **CLI scraping**: a script logs in over SSH, runs `show interfaces` and cuts the numbers out of the text. The text is
  written for people. It changes between releases and platforms, and the script breaks without saying so.

Both ask from the outside, and asking every five minutes gives five-minute averages. Twenty seconds at 100% on an
otherwise idle link shows up as about 7%.

### 1.3 The streaming answer

- **Push instead of pull**: the router reads its own counters at a set interval, or when a value changes, and sends
  them over a connection that stays open. The collector only receives.
- **Named by data models**: what to send is named by a YANG path, from the same models that NETCONF uses (previous
  page). Each value arrives with its name, its keys (which interface) and the time it was read.
- **Compact on the wire**: the data are encoded in binary (GPB, Google Protocol Buffers) and carried by gRPC. One
  sample of every interface travels as one message.
- **Secured**: TLS encrypts the connection and lets each end check the other's certificate.

Cisco calls this model-driven telemetry (MDT). There are two ways to start it: XR01 connects to the collector
(dial-out), or the collector connects to XR01 and subscribes with gNMI (dial-in). Section 2.3 compares them.

## 2. How it works: one counter, from XR01 to the collector

On XRT-15, XR01 and SRV01 (the NMS) share the NMS segment 10.0.50.0/24. SRV01 runs the telemetry collector telegraf,
which listens on TCP 57500 and accepts only gRPC over TLS, and the gNMI client gnmic. XR01's gRPC server, once it is
configured, listens on TCP 57400.

:::topo
nodes:
  PE2: {at: [0, 0], label: "PE2"}
  XR01: {at: [2.6, 0], label: "XR01 (gRPC 57400)"}
  SW1: {at: [1.3, 1.2], kind: sw, label: "SW1"}
  SRV01: {at: [1.3, 2.4], kind: host, label: "SRV01 (telegraf 57500, gnmic)"}
links:
  - [PE2, XR01, "CORE 10.0.12.0/24"]
  - {a: XR01, b: SW1, la: "Gi0/0/0/1 .1"}
  - {a: PE2, b: SW1, la: "Gi3 .2"}
  - {a: SW1, b: SRV01, lb: "ens3 .10"}
frames:
  - {label: "NMS segment 10.0.50.0/24", nodes: [SW1, SRV01]}
:::

### 2.1 gRPC and gNMI

**gRPC** is a framework for calling functions on another machine (remote procedure calls), made by Google. It runs
over HTTP/2: one TCP connection carries many calls at once as separate streams, and either side can keep sending on a
stream for as long as it likes. That is what makes an endless stream of samples possible. The messages are defined in
protocol buffers (protobuf): each message is described in a `.proto` file and sent in a compact binary form.

**gNMI** (gRPC Network Management Interface) is a gRPC service defined by OpenConfig for managing network devices. It
has four calls (RPCs).

| RPC | What it does |
|---|---|
| Capabilities | The device lists the models and the encodings it supports |
| Get | Reads a snapshot of the data under a path |
| Set | Changes the configuration (update, replace, delete) |
| Subscribe | Asks the device to send data under a path, now and later (section 2.2) |

A gNMI path names a place in a YANG tree one element at a time, with list keys in brackets:
`/interfaces/interface[name=Loopback0]/state`. Which tree a path belongs to is its **origin**. With no origin, the
gNMI specification says it is OpenConfig. IOS XR's own models are named by putting the module name in front, as in
`Cisco-IOS-XR-shellutil-oper:system-time/uptime`. XR writes the origin into the paths it answers with
(`openconfig:/…`, `Cisco-IOS-XR-shellutil-oper:/…`).

The values in a gNMI message are encoded in the way the request asks for. IOS XR 26.1.1 lists only **JSON_IETF** in
its Capabilities (JSON written by the rules for YANG data, RFC 7951) and refuses plain JSON, which is gnmic's default:
the Get fails with `unsupported get-request encoding: JSON`. Give gnmic `-e json_ietf`.

```console
# On SRV01 (the TLS options are left out here; they come in section 2.5)
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … capabilities
gNMI version: 0.10.0
supported models:
  - Cisco-IOS-XR-um-hw-module-shut-cfg, Cisco Systems, Inc., 2022-03-08
  - Cisco-IOS-XR-sysmgr-oper, Cisco Systems, Inc., 2021-04-29
...
supported encodings:
  - JSON_IETF
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … get --path '/interfaces/interface[name=Loopback0]/state'
...
        "Path": "openconfig:/interfaces/interface[name=Loopback0]/state",
        "values": {
          "interfaces/interface/state": {
            "admin-status": "UP",
            "counters": {
              "carrier-transitions": "1"
            },
...
            "name": "Loopback0",
            "oper-status": "UP",
            "type": "iana-if-type:softwareLoopback"
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … get --path Cisco-IOS-XR-shellutil-oper:system-time/uptime
...
        "Path": "Cisco-IOS-XR-shellutil-oper:/system-time/uptime",
        "values": {
          "system-time/uptime": {
            "host-name": "XR01",
            "uptime": 824
```

Set changes the configuration, as NETCONF does. XR records a change made with gNMI in the commit history with the line
`ems` (the process that serves gRPC) and the client `YANG Frame`, where a NETCONF change shows the line `netconf`.

```console
RP/0/RP0/CPU0:XR01#show configuration commit list 4
SNo. Label/ID              User      Line                Client      Time Stamp
~~~~ ~~~~~~~~              ~~~~      ~~~~                ~~~~~~      ~~~~~~~~~~
1    1000000024            SUZUKI    ems                 YANG Frame  Tue Nov 10 13:41:00 2026
2    1000000023            SUZUKI    vty0:node0_RP0_CPU  CLI         Tue Nov 10 13:40:37 2026
...
```

### 2.2 Subscribe: stream, once and poll

A Subscribe request lists the paths and says how the client wants them. The request as a whole has one of three modes.

| Mode | What happens |
|---|---|
| STREAM | The call stays open and the device keeps sending. Each path has a sub-mode (below) |
| ONCE | The device sends the current values once, marks the end with `sync_response`, and closes the call |
| POLL | The call stays open; the device sends the current values each time the client sends a poll message |

Under STREAM, the sub-mode of each path decides when a value is sent.

- **SAMPLE**: every sample interval, whether the value changed or not. It suits counters, which change all the time.
- **ON_CHANGE**: every value once at the start, then a value only when it changes. It suits state that rarely
  changes, such as an interface's oper-status. The Telemetry guide limits it to state leaves.
- **TARGET_DEFINED**: the device chooses SAMPLE or ON_CHANGE for each leaf.

A STREAM first sends every value once and then `sync_response`, which tells the client that it now holds a complete
copy. From then on, only samples or changes follow.

On XR01, Subscribe worked with OpenConfig paths in ONCE, in STREAM with SAMPLE every 10 seconds, and in STREAM with
ON_CHANGE. Here is ONCE for the counters of Loopback0 (a loopback has only one counter there).

```console
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … subscribe --path '/interfaces/interface[name=Loopback0]/state/counters' --mode once
{
  "source": "10.0.50.1:57400",
  "subscription-name": "default-1794316110",
  "timestamp": 1794316112062859674,
  "time": "2026-11-10T13:08:32.062859674Z",
  "prefix": "openconfig:/",
  "updates": [
    {
      "Path": "interfaces/interface[name=Loopback0]/state",
      "values": {
        "interfaces/interface/state": {
          "counters": {
            "carrier-transitions": "1"
          }
        }
      }
    }
  ]
}
{
  "sync-response": true
}
```

Telemetry configured on the router makes the same choice with one number: `sample-interval` in milliseconds for
sampling, and 0 for event-driven (a value is sent when it changes).

### 2.3 Dial-in and dial-out

The difference is who opens the connection.

| | Dial-in | Dial-out |
|---|---|---|
| Who connects | The collector, to XR01's gRPC server (57400) | XR01, to the collector (57500 on XRT-15) |
| Who decides what is sent | The collector's request (gNMI Subscribe: paths, mode, interval) | XR01's configuration (sensor group, subscription, destination group) |
| Transport | gRPC only | gRPC, TCP or UDP |
| What XR01 needs | `grpc` | `telemetry model-driven`, and a CA file for TLS |
| After a break | The collector connects and subscribes again | XR01 keeps retrying by itself |
| Which way the firewall must let it through | Collector → router | Router → collector |

**Dial-in.** The collector connects to the router and asks. gNMI Subscribe is dial-in: gnmic names the paths in its
request, and XR01 needs nothing configured but its gRPC server. IOS XR's own telemetry can also run as dial-in: a
subscription configured on the router without a destination group is taken up by a collector that connects to the
gRPC server.

**Dial-out.** The router connects to the collector and sends what its configuration says. The collector only
listens. When the collector restarts, XR01 notices the break and connects again on its own; in the lab it was back
within a minute.

Dial-out can use gRPC, TCP or UDP. TCP carries the same encoded messages without gRPC and without TLS. UDP has no
session at all: XR01 shows the destination as Active whether or not anything listens, and every message has to fit in
one datagram (at most 65,507 bytes). The Telemetry guide does not recommend UDP for production.

Dial-out suits a fixed set of data for a known collector: the router's configuration says what goes where, and the
collector needs no list of routers. Dial-in suits a client that decides for itself what to read, such as a tool used
while troubleshooting.

### 2.4 Encodings and sensor paths

In dial-out, the destination group says how the samples are encoded.

| Encoding | What travels | What the collector needs |
|---|---|---|
| `gpb` (compact GPB) | Values tagged only with field numbers; the most compact | The `.proto` file of each path, to know which number is which |
| `self-describing-gpb` (key-value GPB) | Each value with its name | Nothing per path; telegraf decodes it as it is |
| `json` | Text | Nothing per path |

A **sensor path** is a YANG path written as `<module>:<path>`, without a slash after the colon:
`openconfig-interfaces:interfaces/interface/state/counters`. XR looks the path up in the models it has. When it finds
it, the path is **Resolved**, and XR collects from the nearest container; it shows the path as
`openconfig-interfaces:interfaces/interface/state{counters}`, the container `state` cut down to `counters`.

The path must exist in this release. Many examples, in guides and elsewhere, use the native path
`Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters`. On IOS XR 26.1.1
(both XRd and XRv 9000), that path is not there.

| Path | gNMI Get | As a sensor path |
|---|---|---|
| `openconfig-interfaces:interfaces/interface/state/counters` | Returns the counters | Resolved; samples arrive |
| `Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters` | NotFound | Not Resolved, `Invalid sensor path`; nothing is sent for it |

A sensor group with one path that does not resolve is shown as **Partial**, and the paths that do resolve are still
sent. The collector is not told that a path is missing, so check the state on the router (section 3.4).

On SRV01, telegraf turns each sample into lines of JSON, one object per line. Each interface gives two lines per
sample: one with seventeen fields (`counters/in_pkts`, `counters/out_pkts`, `counters/in_octets` and others) and one
with `counters/carrier_transitions`. The tags say which router sent it (`source`), through which subscription, for
which interface (`name`) and from which path.

### 2.5 TLS and mutual TLS: who proves what

TLS does two jobs before the first gRPC message: it lets the client make sure it is talking to the right server, and
it sets up the keys that encrypt the connection. The server shows a **certificate**: its public key and its names,
signed by a certificate authority (CA). The client checks three things: that a CA it trusts signed the certificate,
that the certificate is valid today, and that the name or address it meant to reach is in the certificate (in the
subject alternative names, SAN). The server then proves that it holds the private key that belongs to the
certificate. The private key never leaves its owner; only certificates travel.

In **mutual TLS** (mTLS), the server also asks the client for a certificate and checks it the same way, against the
CAs that the server trusts. Each side then needs two things: its own certificate and key, to prove itself, and the
certificate of the CA that signed the other side's, to check the other.

On XRT-15 the pieces are these.

| Connection | Shows a certificate | Checks it, with what | File on XR01 |
|---|---|---|---|
| gNMI dial-in, TLS | XR01: `ems.pem` (CN ems.cisco.com, signed by itself) | SRV01's gnmic: a CA file and the name, or no check at all (`--skip-verify`) | `/misc/config/grpc/ems.pem`, `ems.key` |
| gNMI dial-in, mutual TLS (in addition) | SRV01: `client.pem` (CN nms-gnmi, signed by NMS-LAB-CA) | XR01: the CA in `ca.cert` | `/misc/config/grpc/ca.cert` |
| Telemetry dial-out, TLS | SRV01's telegraf: CN collector.nms.lab, signed by NMS-LAB-CA | XR01: the CA in `dialout.pem`, and the name in `tls-hostname` (or the address) | `/misc/config/grpc/dialout/dialout.pem` |

When gRPC is first configured, XR makes a certificate for itself: `ems.pem` with its key `ems.key`, with the CN and the
SAN `ems.cisco.com`, signed by itself and valid for twenty years. No CA vouches for it, and its name is not XR01's
address. A client that checks it against the address it dialled fails with
`x509: cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs`. A client that wants to check
it anyway uses the certificate itself as its CA file (it can be fetched with `openssl s_client`) and checks the name
`ems.cisco.com` (gnmic `--tls-server-name`). In production, XR is given a certificate signed by the operator's own CA.

TLS proves which machines are talking. The user is still checked: every gRPC call carries a username and a password in
its metadata, and XR checks them with AAA, as it checks an SSH login. With `certificate-authentication` added to
`tls-mutual`, XR takes the username from the client certificate's CN instead.

Dial-out turns the roles round: XR01 is the TLS client and the collector is the server. XR01 checks the collector's
certificate with the CA in `dialout.pem` and checks the name: the one in `tls-hostname` if it is configured, otherwise
the destination address. The Telemetry guide says the name must match the certificate's CN. The lab's collector
certificate carries `collector.nms.lab` both as the CN and in the SAN, and carries the address 10.0.50.10 in the SAN
as well, so checking by the address works too. XR01 shows no certificate of its own on dial-out: a collector that
demands one never accepts the connection.

### 2.6 Key points

- Telemetry pushes data named by YANG paths, encoded in GPB, over a connection that stays open. gNMI is the gRPC
  service with four calls: Capabilities, Get, Set, Subscribe.
- Subscribe: STREAM (SAMPLE, ON_CHANGE, TARGET_DEFINED), ONCE, POLL. On the router, a sample interval in ms, or 0 for
  on change.
- Dial-in: the collector connects (gNMI, gRPC only). Dial-out: XR connects (three blocks; gRPC, TCP or UDP).
- On 26.1.1, gNMI on XR speaks JSON_IETF only, and an old native interface path is gone; check that every sensor path
  is Resolved.
- TLS: the server shows a certificate; the client checks the CA, the date and the name. Mutual TLS: the server checks
  the client too. On XR: `ems.pem` is shown to clients, `ca.cert` checks clients, `dialout/dialout.pem` checks
  collectors.

## 3. Building it in IOS XR

### 3.1 The gRPC server: TLS and mutual TLS

The gRPC server is off until `grpc` is configured. Without `no-tls`, it speaks TLS, and `tls-mutual` makes it ask
every client for a certificate. With no `vrf` line, it listens in the global routing table on all of XR01's
addresses. gNMI is served on the same port.

The figure follows gnmic on SRV01 as it connects with its client certificate. Rest the pointer on a number in the
figure (or tap it on a phone) to see that part of the configuration.

:::walk
legend: "TLS is set up before the first gNMI message. Blue numbers: what XR01 is given."
rows:
  - {node: SRV01, kind: host, say: ["gnmic with `--tls-cert client.pem --tls-key client.key`", "~and the lab account in `-u` and `-p`"]}
  - {wire: "[[TCP 10.0.50.10 → 10.0.50.1:57400]] [[=TLS hello]]"}
  - panel: XR01
    sub: gRPC server (process emsd)
    items:
      - ref: 1
        head: "**Listen** `grpc`  `port 57400`  `address-family ipv4`"
        say: ["No `no-tls`, so the server speaks TLS"]
      - say: ["Shows its own certificate `ems.pem` (CN ems.cisco.com, signed by itself)", "~SRV01 checks it with `--tls-ca` and `--tls-server-name`, or skips (`--skip-verify`)"]
      - ref: 2
        head: "**Ask for the client's certificate** `tls-mutual`"
        say: ["Checks the certificate that SRV01 shows"]
        match:
          - ["no certificate", false, "tls: certificate required"]
          - ["signed by a CA not in ca.cert", false, "tls: bad certificate"]
          - ["signed by the CA in ca.cert (NMS-LAB-CA)", true, "accepted"]
      - ref: 3
        head: "**The CA it trusts** `/misc/config/grpc/ca.cert`"
        say: ["A file, read when emsd starts: replace it, then `process restart emsd`"]
      - say: ["~TLS is up. Each call carries the username and password → AAA", "~→ Capabilities, Get, Set or Subscribe"]
  - aside: "A client without TLS (`--insecure`)"
    say: ["~The server waits for a TLS hello → `error reading server preface: EOF`"]
  - aside: "The client checks ems.pem against the address it dialled"
    say: ["~`cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs`", "~→ check it by the name in it: `--tls-server-name ems.cisco.com`"]
:::

:::config fold XR01 — a gRPC server on port 57400 that accepts only clients with a certificate
grpc                                          ## ① Start the gRPC server (the process emsd); gNMI uses it too
 port 57400                                   ## ① The default port; the range is 57344–57999
 address-family ipv4                          ## ① Listen on IPv4; no vrf line, so in the global routing table
 tls-mutual                                   ## ② Ask every client for a certificate and check it against ca.cert
!
:::

For a first look at gNMI in a lab, the server can run without TLS, as below. It is not for production: the username
and the password then cross the network in the clear. The port can be any free one in the range.

:::config XR01 — a gRPC server without TLS (a lab test only)
grpc
 port 57401                                   ## Another port in 57344–57999
 no-tls                                       ## Plain gRPC: clients connect with gnmic --insecure
 address-family ipv4
!
:::

The `grpc` block holds one server, so this replaces the settings above rather than adding a second server. XR refuses
`no-tls` while `tls-mutual` is configured; remove `tls-mutual` first.

```console
RP/0/RP0/CPU0:XR01(config-grpc)#no-tls
RP/0/RP0/CPU0:XR01(config-grpc)#commit

% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted. Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:XR01(config-grpc)#show configuration failed
...
grpc
 no-tls
!!% Invalid argument: Remove grpc tls mutual first!
```

### 3.2 Putting certificates on IOS XR

Certificates are not configuration lines. They are files in the Linux file system under `/misc/config/grpc`, next to
the files that XR made itself.

```console
RP/0/RP0/CPU0:XR01#run ls -la /misc/config/grpc/
total 32
drwxr-xr-x.  5 root root 4096 Nov 10 13:08 .
drwxr-xr-x. 16 root root 4096 Nov 10 13:08 ..
-rw-r--r--.  1 root root 1545 Nov 10 13:08 ca.cert
drwx------.  2 root root 4096 Nov 10 13:20 dialout
-rw-------.  1 root root 1679 Nov 10 13:08 ems.key
-rw-r--r--.  1 root root 1545 Nov 10 13:08 ems.pem
drwxr-xr-x.  2 root root 4096 Nov 10 12:55 gnsi
drwxr-xr-x.  2 root root 4096 Nov 10 13:08 trustpoint
```

XR's `copy` writes only into XR's own file systems (`harddisk:` and others). Copying straight into `/misc/config`
fails.

```console
RP/0/RP0/CPU0:XR01#copy http://10.0.50.10:8000/ca.pem /misc/config/grpc/dialout/dialout.pem
Copy: /misc/config/grpc/dialout/dialout.pem : path outside filesystem

Error: Copy failed with error 'Destination path is invalid'
```

So it takes two steps: `copy` the file to `harddisk:`, then copy it on with the Linux `cp` through `run`. `copy`
accepts http, tftp, ftp, sftp and scp as the source; on XRT-15, a small web server on SRV01 that serves `~/pki` is
enough. `copy` asks for the destination file name (`Destination filename [/harddisk:/…]?`): press Enter.

`ca.cert` is read when the gRPC process emsd starts. After replacing it, restart emsd. Until then XR keeps using the
old CA, and clients with a certificate from the new CA still get `tls: bad certificate`. The telemetry dial-out
carried on through the restart.

`dialout.pem` needs no restart. XR reads it when it next connects to the collector, and it retries on its own.

:::config fold XR01 — put the NMS's CA where the gRPC server and the dial-out look for it (EXEC mode)
copy http://10.0.50.10:8000/ca.pem harddisk:/nms-lab-ca.pem   ## Fetch the CA certificate (public, no key) from SRV01
run cp /harddisk:/nms-lab-ca.pem /misc/config/grpc/ca.cert   ## ③ Dial-in: the CA that client certificates must come from
process restart emsd                          ## ③ emsd reads ca.cert only when it starts
run cp /harddisk:/nms-lab-ca.pem /misc/config/grpc/dialout/dialout.pem   ## Dial-out: the CA for the collector's certificate
:::

To read a certificate on XR, run `openssl` through `run`. Compare the subject, the issuer and the SAN with what the
other side expects.

```console
RP/0/RP0/CPU0:XR01#run openssl x509 -in /misc/config/grpc/ems.pem -noout -subject -issuer -ext subjectAltName -dates
subject=C=US, ST=CA, L=San Jose, street=3700 Cisco Way, postalCode=95134, O=Cisco Systems, Inc., OU=CSG, CN=ems.cisco.com, serialNumber=638B85D4E4A
issuer=C=US, ST=CA, L=San Jose, street=3700 Cisco Way, postalCode=95134, O=Cisco Systems, Inc., OU=CSG, CN=ems.cisco.com, serialNumber=638B85D4E4A
X509v3 Subject Alternative Name:
    DNS:ems.cisco.com
notBefore=Nov 10 13:08:16 2026 GMT
notAfter=Nov 10 13:08:16 2046 GMT
```

The subject and the issuer are the same: the certificate is signed by itself. On SRV01, `openssl s_client -connect
<address>:<port> </dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName` shows the certificate that a
server presents, for XR01's gRPC server as well as for the collector.

Newer releases move gRPC certificates into SSL profiles managed through gNSI, and the guides say that the
`/misc/config/grpc` certificates will be deprecated in a future release. On 26.1.1, these files are what the gRPC
server and the dial-out use.

### 3.3 Dial-out: sensor group, destination group, subscription

Dial-out takes three blocks under `telemetry model-driven`. The **sensor group** says what to read, the
**destination group** says where to send it and how, and the **subscription** ties them together by name, with the
interval and the source interface.

The example sends XR01's uptime and its interface counters every 30 seconds. The figure follows one sample of
GigabitEthernet0/0/0/0's counters over gRPC with TLS to telegraf on SRV01. Rest the pointer on a number (or tap it on
a phone) to see that block.

:::walk
legend: "One sample on its way to the collector. Blue numbers: the blocks under telemetry model-driven."
rows:
  - panel: XR01
    sub: telemetry model-driven
    items:
      - ref: 1
        head: "**What to read** `sensor-group SG-HEALTH`"
        say: ["Each path is looked up in the YANG models of this release"]
        match:
          - ["openconfig-interfaces:interfaces/interface/state/counters", true, "Resolved"]
        then: ["→ the counters of every interface: in-pkts, out-pkts, in-octets …"]
      - ref: 2
        head: "**How often, where to** `subscription SUB-NMS-TLS`"
        say: ["`sensor-group-id SG-HEALTH sample-interval 30000`: every 30 s"]
        then: ["→ `destination-id DG-NMS-TLS`", "→ `source-interface Loopback0`: the connection comes from 10.255.0.1"]
      - ref: 3
        head: "**Where and how** `destination-group DG-NMS-TLS`"
        say: ["10.0.50.10 port 57500, `encoding self-describing-gpb`"]
      - ref: 4
        head: "**Check the collector** `protocol grpc tls-hostname collector.nms.lab`"
        say: ["XR01 is the TLS client; telegraf shows its certificate"]
        match:
          - ["signed by the CA in dialout/dialout.pem", true, "NMS-LAB-CA"]
          - ["collector.nms.lab is a name in it", true, "matches"]
  - {wire: "[[TCP 10.255.0.1 → 10.0.50.10:57500]] [[=TLS]] [[=gRPC]] [[GPB: in-pkts …]]"}
  - {node: SRV01, kind: host, say: ["telegraf decodes the sample", "_two JSON lines per interface in /var/log/telegraf/mdt.json"]}
  - aside: "No CA file, or a tls-hostname that is not in the certificate"
    say: ["~④ fails, the TLS handshake fails → the destination stays NA; nothing reaches SRV01", "~The subscription can still show ACTIVE. The reason is in `show grpc trace ems`"]
  - aside: "A sensor path that does not resolve"
    say: ["~① `Cisco-IOS-XR-infra-statsd-oper:…/latest/generic-counters` → Not Resolved", "~The group is Partial; the paths that resolve are still sent"]
:::

First the three blocks over plain TCP, which shows them without certificates. The lab's collector accepts only gRPC
over TLS on 57500, so a TCP destination needs a collector of its own (telegraf can also listen for TCP; here on port
57000).

:::config XR01 — send uptime and interface counters every 30 seconds to a collector over TCP
telemetry model-driven
 destination-group DG-NMS-TCP                 ## ③ Where to send, and how
  address-family ipv4 10.0.50.10 port 57000   ## The collector's address and port
   encoding self-describing-gpb               ## Each value travels with its name
   protocol tcp                               ## Plain TCP: no gRPC, no TLS
  !
 !
 sensor-group SG-HEALTH                       ## ① What to read
  sensor-path Cisco-IOS-XR-shellutil-oper:system-time/uptime   ## A native model: how long XR01 has been up
  sensor-path openconfig-interfaces:interfaces/interface/state/counters   ## OpenConfig: the counters of every interface
 !
 subscription SUB-NMS-TCP                     ## ② Ties the two together
  sensor-group-id SG-HEALTH sample-interval 30000   ## Every 30,000 ms; 0 would mean on change
  destination-id DG-NMS-TCP
  source-interface Loopback0                  ## The connection comes from Loopback0's address
 !
!
:::

Over gRPC with TLS, only the destination changes: `protocol grpc` and the name to check. The CA for the check is the
`dialout.pem` file from section 3.2.

:::config fold XR01 — send the same data to the gRPC collector over TLS, checking its certificate
telemetry model-driven
 destination-group DG-NMS-TLS                 ## ③
  address-family ipv4 10.0.50.10 port 57500   ## telegraf on SRV01 (gRPC over TLS)
   encoding self-describing-gpb
   protocol grpc tls-hostname collector.nms.lab   ## ④ TLS; the collector's certificate must carry this name
  !
 !
 subscription SUB-NMS-TLS                     ## ②
  sensor-group-id SG-HEALTH sample-interval 30000   ## ① The same sensor group
  destination-id DG-NMS-TLS
  source-interface Loopback0
 !
!
:::

`protocol grpc` alone also uses TLS, and checks the certificate against the destination address (10.0.50.10 is in the
lab certificate's SAN, so it works). `protocol grpc no-tls` sends gRPC in the clear.

### 3.4 Checking it

**The gRPC server.** `show grpc` shows the port, the VRF and the TLS settings (there is no `show grpc status`).
`Service ports gNMI : none` in the full output means that gNMI has no port of its own and uses the main one.

```console
RP/0/RP0/CPU0:XR01#show grpc | include "TLS|Port|Address family|VRF"
Address family                          : ipv4
Port                                    : 57400
VRF                                     : global-vrf
TLS                                     : enabled
TLS mutual                              : enabled
TLS v1.0                                : enabled
TLS Minimum Version                     : TLS 1.0
TLS Maximum Version                     : TLS 1.3
TLS cipher suites
  Default TLS1.3                        : aes_128_gcm_sha256
```

**A gNMI client that fails.** gnmic's error text names the missing piece. Try `capabilities` first; it needs no path.

| What gnmic says (excerpt) | What it means |
|---|---|
| `Error while dialing: dial tcp 10.0.50.1:57400 …` | Nothing listens there: no `grpc`, another port, or another VRF |
| `error reading server preface: EOF` | The client speaks plain gRPC (`--insecure`) to a TLS server |
| `x509: cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs` | The client checks the server's certificate against the address; check the name (`--tls-server-name`) or skip the check |
| `remote error: tls: certificate required` | `tls-mutual`, and the client showed no certificate |
| `remote error: tls: bad certificate` | The client's certificate is not signed by the CA in `ca.cert`, or `ca.cert` was replaced without restarting emsd |
| `unsupported get-request encoding: JSON` | gnmic's default encoding; add `-e json_ietf` |

**Telemetry.** Three commands, from the summary to the detail: `show telemetry model-driven subscription [name]`,
`show telemetry model-driven sensor-group [name]` and `show telemetry model-driven destination [name]`. The output
below comes from a test with other names: the sensor group SG-IF held the OpenConfig counters path and the
infra-statsd path, SUB-TCP sent to a TCP collector on 57000, SUB-TLS to a gRPC collector with TLS on 57600 checking the
name collector.lab, and SUB-MTLS to a collector on 57700 that demanded a client certificate. First, before any
collector was listening:

```console
RP/0/RP0/CPU0:XR01#show telemetry model-driven subscription
Subscription:  SUB-TCP  ID:  12                State: NA
-------------
  Sensor groups:
  Id                               Interval(ms)               State
  SG-IF                            10000                      Partial

  Destination Groups:
  Id       Encoding            Transport   State   Port    Vrf                               IP
  DG-TCP   self-describing-gpb tcp         NA      57000                                     10.0.50.10
    TLS :             False
...
RP/0/RP0/CPU0:XR01#show telemetry model-driven sensor-group
  Sensor Group Id:SG-IF
    ID:                 12
    Sensor Path:        openconfig-interfaces:interfaces/interface/state/counters
    Sensor Path State:  Resolved
    Sensor Path:        Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters
    Sensor Path State:  Not Resolved
      Status:           Invalid sensor path
```

Once the collectors were listening:

```console
RP/0/RP0/CPU0:XR01#show telemetry model-driven subscription
Subscription:  SUB-TCP  ID:  12                State: ACTIVE
-------------
  Sensor groups:
  Id                               Interval(ms)               State
  SG-IF                            10000                      Partial

  Destination Groups:
  Id       Encoding            Transport   State   Port    Vrf                               IP
  DG-TCP   self-describing-gpb tcp         Active  57000                                     10.0.50.10
    TLS :             False
...
RP/0/RP0/CPU0:XR01#show telemetry model-driven destination DG-TLS
  Destination Group Id:  DG-TLS
  --------------------
    Destination IP:       10.0.50.10
    Destination Port:     57600
    Subscription:         SUB-TLS
    State:                Active
    Encoding:             self-describing-gpb
    Transport:            grpc
    TLS :                 collector.lab
    Total bytes sent:     18282
    Total packets sent:   12
    Last Sent time:       2026-11-10 13:23:35.4233576752 +0000
...
    Collection Groups:
    ------------------
      Id: 11
      Sample Interval:      10000 ms
...
      Sensor Path:          openconfig-interfaces:interfaces/interface/state{counters}
RP/0/RP0/CPU0:XR01#show telemetry model-driven destination DG-MTLS
  Destination Group Id:  DG-MTLS
  --------------------
    Destination IP:       10.0.50.10
    Destination Port:     57700
    Subscription:         SUB-MTLS
    State:                NA
    Encoding:             self-describing-gpb
    Transport:            grpc
    TLS :                 collector.lab
...
```

- **Sensor Path State**: `Resolved` or `Not Resolved` for each path (with the reason under `Status`). A sensor group
  with some paths not resolved is `Partial` in the subscription; the resolved paths are still sent.
- **The destination's State**: `Active` means connected and sending; `NA` means not connected (nobody listens, TLS
  failed, or no route). This is the line that tells whether anything leaves XR01.
- **The subscription's State**: do not judge by it alone. With a `tls-hostname` that was not in the certificate, the
  subscription showed `ACTIVE` while its destination was `NA`.
- **TLS**: `False` for no TLS; otherwise the name (or the address) that XR01 checks the collector's certificate
  against.
- **Total packets sent** grows with every sample while the destination is Active.

**Why a destination is NA.** The show commands give no reason. The reason for a failed connection, such as a TLS
handshake that failed and the server name that XR01 checked, is in `show grpc trace ems` (add `last 20` to see only
the latest lines). Check the files with `run ls -la /misc/config/grpc/dialout/` and the collector's certificate from
SRV01 with `openssl s_client` (section 3.2).

**On the collector.** telegraf writes one JSON object per line. With `jq`, pick the lines of one interface and the
fields you want. Here the subscription samples every 10 seconds: two lines per sample (the same `timestamp`), the
first with seventeen fields and rising counters, the second with only `carrier_transitions`:

```console
$ grep '"GigabitEthernet0/0/0/0"' /var/log/telegraf/mdt.json | tail -6 | jq -c '[.timestamp, (.fields|keys|length), .fields["counters/in_pkts"], .fields["counters/out_pkts"], .fields["counters/in_unicast_pkts"]]'
[1794321912,17,732,658,284]
[1794321912,1,null,null,null]
[1794321922,17,733,659,284]
[1794321922,1,null,null,null]
[1794321932,17,734,660,284]
[1794321932,1,null,null,null]
```

:::try
See how a wrong name shows up. Do it after Task M13-4, and always put things back at the end.

1. On XR01, change the `protocol` line of the destination group of `SUB-IF` to `protocol grpc tls-hostname
   telemetry.nms.lab`, and commit.
2. After about 30 seconds, look at `show telemetry model-driven subscription SUB-IF | include "State|TLS"`. Compare the
   subscription's State with the destination's.
3. Look at `show grpc trace ems last 15`, and find the server name and the reason.
4. Put the `protocol` line back and commit. Check that the destination is Active again within a minute.

Example output: the subscription showed `State: ACTIVE` while the destination showed `State: NA` and
`TLS : telemetry.nms.lab`. The trace had
`Creating new client transport to "{Addr: \"10.0.50.10:57500\", ServerName: \"telemetry.nms.lab\", …` and
`connection error: desc = "transport: authentication handshake failed: tls: failed to verify certificate: x509:
certificate is valid for collector.n…` (the line is cut there). After the line was put back, the destination was
Active again within 30 seconds.
:::

### 3.5 Pitfalls

- **Plain JSON in gNMI**: XR 26.1.1 refuses it. Use `-e json_ietf` with gnmic.
- **Paths copied from old examples**: the infra-statsd interface path is `Not Resolved` on 26.1.1. After every commit,
  check that each sensor path is `Resolved`.
- **Replacing `ca.cert` and stopping there**: emsd reads it only at start. `process restart emsd`.
- **`copy` straight into `/misc/config`**: refused (`path outside filesystem`). Copy to `harddisk:` first, then
  `run cp`.
- **Reading only the subscription's State**: it can be `ACTIVE` while nothing is delivered. The destination's State
  must be `Active`, and `Total packets sent` must grow.
- **A tls-hostname that is not in the certificate**: read the names in the collector's certificate with `openssl
  s_client` and use one of them, or leave `tls-hostname` out when the certificate carries the address.
- **A collector that demands a client certificate**: XR does not show one on dial-out, and the destination stays `NA`.
- **`no-tls` with `tls-mutual`**: refused (`Remove grpc tls mutual first!`).
- **Checking ems.pem by the address**: it carries only the name `ems.cisco.com`. Check by that name, or skip the
  check in the lab.

## Practice

Do Tasks M13-3 and M13-4 in lab **XRT-15**. On SRV01, the NMS's CA and client certificate are in `~/pki`.

<p class="tolab"><a href="/_learn?id=XRT-15">Open lab XRT-15 in the workspace</a> — <a href="e3-m13-practice-2.html">Tasks M13-3 and M13-4</a></p>

:::note
The output on this page was taken on IOS XRd 26.1.1 (XR01 on XRT-15), and on a PoC board where IOS XRv 9000 26.1.1
and IOS XRd 26.1.1 were tested side by side (they behaved the same), with gnmic 0.49.1 and telegraf 1.32.3 on Ubuntu
24.04.
Sources: the gNMI specification (openconfig/reference, sections 2.3, 2.7, 3.1 and 3.5), RFC 7951 (JSON encoding of
YANG data). The Programmability Configuration Guide for the Cisco 8000 (cumulative) and the ASR 9000 (IOS XR 26.x):
the `grpc` keywords, the port range and default, the authentication methods (metadata with TLS, without TLS, with
mutual TLS, certificate-based), the self-signed certificate files, and the move of certificates to SSL profiles from
25.4.1. The Telemetry Configuration Guide for the Cisco 8000 (cumulative, 2026) and the NCS 5500 (IOS XR 26.x): dial-in
and dial-out, the three blocks, the transports and encodings, UDP, TLS on dial-out and `tls-hostname`, the dial-out CA
directory, the sample interval, the gNMI subscription modes, the show commands, and the sensor group example that
uses `Cisco-IOS-XR-shellutil-oper:system-time/uptime`. All checked in November 2026.
The following come from measurements: JSON_IETF as the only encoding, the Get and Subscribe results, the error texts,
the files under `/misc/config/grpc` and the restart of emsd, `copy` refusing `/misc/config`, the paths that resolve
and the one that does not, the states of subscriptions and destinations, the reasons in `show grpc trace ems`, XR
not showing a client certificate on dial-out, and telegraf's lines.
Where the documents and the device differ or are silent: the gNMI specification requires both ends to support plain
JSON, but XR 26.1.1 offers only JSON_IETF. The Telemetry guide says the name must match the CN; the lab certificate
carries the name both as the CN and in the SAN, so which of the two XR checks was not separated. The guides say
nothing about restarting emsd after `ca.cert` is replaced, or about client certificates on dial-out. From IOS XR
24.1.1, `grpc gnmi port` can give gNMI a port of its own (9339 by default); it was not used here.
:::
