# XR Track 15 — Automation and Assurance

This lab is the practice part of unit **M13 Automation and assurance** of the XR track. The unit has three pages:
*Configuring through models: YANG, NETCONF and RESTCONF* (tasks M13-1 and M13-2), *Streaming state: gNMI, telemetry
and TLS* (tasks M13-3 and M13-4) and *Counting flows and polling: NetFlow/IPFIX and SNMP* (tasks M13-5 and M13-6).
Read each page before its tasks, and work through the tasks here, in order.

## Ground rules

- You configure **XR01** and **PE2**, and you work on **SRV01**, the network management station (NMS). Log in to SRV01
  from the workspace console with the lab account. CE1 belongs to the customer and is fixed; do not change it.
- Do not change the receivers on SRV01: the telemetry collector (telegraf), the flow collector (nfcapd-lab) and the trap
  receiver (snmptrapd-lab). You may read their files and start other programs of your own on SRV01.
- The tasks give no command examples. Each task states the behaviour that is required. SRV01 has the tools installed,
  but how to use them is yours to find (`--help`, `man`, the Cisco guides). For NETCONF only, a skeleton script is
  provided.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices and of SRV01.
  Leave configuration mode before you press it. Some checks send test traffic, or make a link go down and up, and count
  what reaches SRV01: they take one to two minutes.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- Each task also has a **How to verify** button: an example of checking your work in order (is it in → send and count →
  look where it arrives → did anything else break). Open it whenever you like; it is not logged. Verify by hand before you
  press Check.
- **Start over** on the **Tasks** tab returns XR01, PE2 and SRV01 to the state they had right after the lab was built. On
  SRV01, the files in your home directory (the skeleton in `~/m13` too) and what the receivers have recorded go back, and
  the programs you started are stopped. Your shell history stays.
- XR01 runs **IOS XRd** 26.1.1, the container form of IOS XR. PE2 runs **Catalyst 8000V** (IOS XE 17.15). On IOS XR in
  this lab, RESTCONF and NetFlow are not available; those tasks are on PE2.

## Topology

| Link | Ends | Addressing |
|---|---|---|
| CORE | XR01 GigabitEthernet0/0/0/0 ─ PE2 GigabitEthernet1 | 10.0.12.0/24 (XR01 .1, PE2 .2) |
| NMS | SW1 (an unmanaged switch): XR01 GigabitEthernet0/0/0/1, PE2 GigabitEthernet3, SRV01 ens3 | 10.0.50.0/24 (XR01 .1, PE2 .2, SRV01 .10) |
| ACCESS-A | PE2 GigabitEthernet2 ─ CE1 Ethernet0/0 | 172.16.1.0/24 (CE1 .1, PE2 .254) |
| BACKUP-A | XR01 GigabitEthernet0/0/0/2 ─ CE1 Ethernet0/1 | 172.16.2.0/24 (XR01 .1, CE1 .2) |

| Device | Role | Platform | Loopback0 |
|---|---|---|---|
| XR01 | Provider edge | IOS XRd 26.1.1 | 10.255.0.1/32 |
| PE2 | Provider edge | Catalyst 8000V, IOS XE 17.15 | 10.255.0.2/32 |
| CE1 | Customer A (fixed) | IOS XE 17.15 | LAN 192.168.100.0/24 (Loopback100 192.168.100.1) |
| SRV01 | NMS | Ubuntu 24.04 | — (10.0.50.10 on the NMS segment) |

- XR01 and PE2 run the IS-IS instance `CORE` (level 2). The NMS segment and the loopbacks are passive. PE2 has a static
  route to customer A's LAN and redistributes it into IS-IS.
- CE1 sends through PE2 (a default route to 172.16.1.254). The backup link to XR01 carries no traffic unless the
  primary fails (a default route with distance 250).
- SRV01 reaches XR01 and PE2 directly on the NMS segment, and their loopbacks through them.

What SRV01 provides:

| Service | Listens on | Where it writes |
|---|---|---|
| Telemetry collector (telegraf): gRPC dial-out, TLS only | TCP 57500 | `/var/log/telegraf/mdt.json` (one JSON object per line) |
| Flow collector (nfcapd-lab): NetFlow v9 and IPFIX | UDP 4739 | `/var/cache/nfdump/lab/` (a new file every minute; read it with `nfdump`) |
| Trap receiver (snmptrapd-lab): SNMPv3, user `nms-trap`, authPriv only | UDP 162 | `/var/log/snmptrapd-lab.log` |

| File on SRV01 | What it is |
|---|---|
| `~/pki/ca.pem` | The certificate of the NMS's certificate authority (NMS-LAB-CA). It issued the certificates below. |
| `~/pki/client.pem`, `~/pki/client.key` | The NMS's client certificate and key for gNMI (CN `nms-gnmi`). |
| `~/m13/nc_edit.py` | A NETCONF skeleton (ncclient) for Task M13-1. Fill in the `__FILL__` parts. |
| `~/m13/rc_customer_lo.py` | The NMS team's RESTCONF script for Task M13-2. Do not edit it. |

- The telemetry collector's certificate is issued by NMS-LAB-CA for the name `collector.nms.lab` and the address 10.0.50.10.
- XR01's SNMP engine ID is fixed (`snmp-server engineID local`), and the trap receiver knows it. Do not change it.

## M13 — Automation and assurance

### Task M13-1

The NMS team will manage XR01 through NETCONF.

- Make XR01 accept NETCONF over SSH on the standard NETCONF port, on the NMS segment (the global routing table).
- From SRV01, through NETCONF, add Loopback100 on XR01 with the description `NMS-MANAGED` and the address
  10.255.100.1/32. Do not make this change from the CLI: XR01's commit history must show it as a NETCONF change.

### Task M13-2

The NMS team's script `~/m13/rc_customer_lo.py` adds customer A's service loopback on PE2 through RESTCONF. Today it
fails.

- Make PE2 ready so that the script runs to the end as it is, then run it once.
- The account that the script uses is a local account on PE2.
- PE2 must not open plain HTTP.

### Task M13-3

The NMS will read XR01 through gNMI.

- Run XR01's gRPC server on port 57400, on the NMS segment (the global routing table), with TLS.
- Accept only clients that show a certificate issued by the NMS's certificate authority (`~/pki/ca.pem`). The NMS uses
  `~/pki/client.pem` and `~/pki/client.key`, and still logs in with the lab account.
- Refuse gRPC without TLS.

### Task M13-4

Your predecessor configured XR01 to stream the counters of its interfaces to the telemetry collector on SRV01, with gRPC
dial-out over TLS, every 10 seconds, in subscription `SUB-IF`. Nothing has ever arrived.

- Make the packet counters of XR01's interfaces arrive at the collector every 10 seconds, through subscription `SUB-IF`.
- Keep TLS: XR01 must check the collector's certificate.
- Do not change the collector.

### Task M13-5

The NMS collects flow records with IPFIX.

- On PE2, record the IPv4 traffic that enters from customer A (GigabitEthernet2). Each flow record holds the source and
  destination addresses, the protocol, the source and destination ports and the input interface, with the packet and
  byte counts.
- Export the records to the flow collector on SRV01 with IPFIX, from Loopback0.
- Report a long flow at least every 60 seconds.

### Task M13-6

Your predecessor configured SNMP on XR01 for the NMS. Two things do not work.

- The NMS reads XR01 with SNMPv2c, community `NMS-RO`, read-only, and only SRV01 may use that community. Today SRV01 gets
  no answer.
- XR01 must send a trap to the trap receiver on SRV01 both when a link goes down and when it comes back up, with
  SNMPv3 (user `nms-trap`, authentication and encryption). Today nothing reaches the trap receiver.
- Keep the community, the user and their passwords. Do not change SRV01.
