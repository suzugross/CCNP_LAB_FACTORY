# M2 — Practice

These are the tasks of lab **XRT-02**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01 only**. RT01, RT02 and SRV01 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  `describe`, the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Steps** tab has a **Check** button for each task. It reads the live state of the devices, and for some
  tasks it logs in to XR01 with the accounts the task names. Leave configuration mode before you press it.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- Log in with the lab credentials. Management access (interface `MgmtEth0/RP0/CPU0/0`, VRF `MGMT`, SSH) must keep
  working throughout; the checks reach XR01 through it. Several tasks can lock you out of XR01. Plan for that.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| LINK1 | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.12.0/24 (XR01 .1, RT01 .2) |
| SERVERS | GigabitEthernet0/0/0/1 | SRV01 | 10.0.50.0/24 (XR01 .1, SRV01 .10) |
| LINK2 | GigabitEthernet0/0/0/2 | RT01 Ethernet0/1 | 10.0.21.0/24 (XR01 .1, RT01 .2) |
| LINK3 | GigabitEthernet0/0/0/3 | RT02 Ethernet0/0 | 10.0.23.0/24 (XR01 .1, RT02 .2) |

- XR01 Loopback0 1.1.1.1/32. RT01 Loopback0 2.2.2.2/32 (stands in for the NOC workstation).
  RT01 Loopback100 198.51.100.1/24 is the guest network.
- XR01 and RT01 run OSPF process 1, area 0, over LINK1. The addresses above are reachable from the start,
  except those behind LINK2 and LINK3 (subjects of M3).
- IPv6: LINK1 2001:DB8:12::/64 (XR01 ::1, RT01 ::2). XR01 Loopback0 2001:DB8::1/128, RT01 Loopback0 2001:DB8::2/128.
- LINK2 is a backup link to RT01. RT01 gives it OSPF cost 100.
- RT02 is the router of a branch in OSPF area 1, which RT02 runs as a stub area. Its LANs are 172.16.1.0/24,
  172.16.2.0/24 and 172.16.3.0/24 (RT02 .1); its Loopback0 is 3.3.3.3/32.
- SRV01 is a TACACS+ server. Its administrator reports that it is configured with XR01 as a client at **1.1.1.1**,
  with the key `XRT02-Tac-Key`, and that it holds these users:

  | User | Password | What the server grants |
  |---|---|---|
  | `ops1` | `Ops1-Pass` | network administration |
  | `view1` | `View1-Pass` | read-only |
  | the lab account | the lab password | full access |

## M2 — Securing the management plane

### Task M2-1
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m2t1">Open in the lab workspace</a> — Read: <a href="20-m2-management-plane.html#s1">1. Rights are task IDs</a></p>


The NOC needs a local account `noc1` with the password `Noc1-Pass`.

- Logged in as `noc1`, an operator must be able to display the routing table, the OSPF neighbours and the
  interfaces, to ping, and to clear the counters of an interface.
- `noc1` must not be able to change any configuration.
- Do not make `noc1` a member of any predefined user group. Build what it needs yourself.

### Task M2-2
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m2t2">Open in the lab workspace</a> — Read: <a href="20-m2-management-plane.html#s2">2. Where management sessions are accepted</a></p>


Restrict which interfaces accept management sessions on XR01.

- SSH must be accepted only on the management interface.
- On the data side, only the NOC workstation (2.2.2.2) may open a Telnet session to XR01, and only through LINK1.
  No other data-side source may open Telnet or SSH sessions to XR01.

### Task M2-3
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m2t3">Open in the lab workspace</a> — Read: <a href="20-m2-management-plane.html#s3">3. Logging in through an AAA server</a></p>


Authenticate and authorise logins on XR01 with SRV01.

- A user who exists only on SRV01 must be able to log in, and must receive exactly the rights the server grants:
  `ops1` can change configuration, `view1` cannot.
- Local accounts must be used only when SRV01 cannot be reached. While SRV01 is up, an account that exists only
  on XR01 must not be able to log in.
- The console must always authenticate against the local accounts, whether or not SRV01 is up.

### Task M2-4
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m2t4">Open in the lab workspace</a> — Read: <a href="20-m2-management-plane.html#s4">4. Traffic addressed to the router: LPTS</a></p>


Limit the rate at which XR01 accepts ICMP echo requests addressed to itself to **50 packets per second**.
Monitoring pings from SRV01 (five per second) must still succeed. Do not change how XR01 handles any other traffic.

### Task M2-5
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m2t5">Open in the lab workspace</a> — Read: <a href="20-m2-management-plane.html#s5">5. Access lists</a></p>


The guest network 198.51.100.0/24 must not reach XR01. Drop its traffic where it enters XR01.
The OSPF adjacency over LINK1 and everything else that crosses LINK1 must be unaffected.
