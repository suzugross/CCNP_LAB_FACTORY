# M13 — Practice 1: configuring through models

These are the tasks of lab **XRT-15**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

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
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t1">Open in the lab workspace</a> — Read: <a href="e0-m13-netconf-yang.html#s2-1">2.1 YANG: a model of the configuration and the state</a> · <a href="e0-m13-netconf-yang.html#s2-2">2.2 Three families of models on IOS XR</a> · <a href="e0-m13-netconf-yang.html#s2-3">2.3 NETCONF: a session over SSH, RPCs and datastores</a> · <a href="e0-m13-netconf-yang.html#s2-4">2.4 Candidate, commit and confirmed commit</a> · <a href="e0-m13-netconf-yang.html#s3-1">3.1 Turning on NETCONF on IOS XR</a> · <a href="e0-m13-netconf-yang.html#s3-2">3.2 A NETCONF session from Python (ncclient)</a> · <a href="e0-m13-netconf-yang.html#s3-3">3.3 Where a NETCONF change shows up</a></p>


The NMS team will manage XR01 through NETCONF.

- Make XR01 accept NETCONF over SSH on the standard NETCONF port, on the NMS segment (the global routing table).
- From SRV01, through NETCONF, add Loopback100 on XR01 with the description `NMS-MANAGED` and the address
  10.255.100.1/32. Do not make this change from the CLI: XR01's commit history must show it as a NETCONF change.

### Task M13-2
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t2">Open in the lab workspace</a> — Read: <a href="e0-m13-netconf-yang.html#s2-5">2.5 RESTCONF: the same models over HTTPS</a> · <a href="e0-m13-netconf-yang.html#s2-6">2.6 Reading an external script</a> · <a href="e0-m13-netconf-yang.html#s3-4">3.4 Turning on RESTCONF on IOS XE</a> · <a href="e0-m13-netconf-yang.html#s3-5">3.5 Checking it</a></p>


The NMS team's script `~/m13/rc_customer_lo.py` adds customer A's service loopback on PE2 through RESTCONF. Today it
fails.

- Make PE2 ready so that the script runs to the end as it is, then run it once.
- The account that the script uses is a local account on PE2.
- PE2 must not open plain HTTP.
