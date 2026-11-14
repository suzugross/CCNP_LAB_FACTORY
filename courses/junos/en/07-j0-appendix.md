# J0 — Appendix

## 1. Junos OS and Junos OS Evolved

Juniper ships two operating systems under the Junos name. **Junos OS** runs its command shell on a FreeBSD kernel and is what you
meet on routers, switches and firewalls such as the MX, EX and SRX series. **Junos OS Evolved** runs on Linux and is what ACX, PTX and some QFX models
run. The CLI and the configuration are the same in both, which is why the pages of this track apply to both. Where a feature or
a default differs, the page says so.

`show version` tells you which one you are on:

```console
admin@jun01> show version | match Junos
Junos: 26.2R1.7-EVOI20260619095247-evo-builder-1
JUNOS-EVO OS 64-bit [junos-evo-install-ptx-fixed-x86-64-26.2R1.7-EVOI20260619095247-evo-builder-1]
```

`EVO` in the release name means Junos OS Evolved.

## 2. The virtual router in this lab

The Junos routers of the labs are **vJunos-Evolved**, the free virtual version of Junos OS Evolved, run in containerlab.
A few things you see on it come from the virtual router, not from Junos itself:

- **It is a PTX.** Juniper builds vJunos-Evolved on the PTX10001-36MR, and `show version` reports `Model: ptx10001-36mr`.
  That is why its ports are `et-` ports, and why defaults that differ on PTX routers (such as the default BGP policy) apply.
- **License messages.** Committing OSPF prints `warning: requires 'OSPF' license`, and `show ospf neighbor` starts with
  `Warning: License key missing`. Juniper's guide for vJunos-Evolved says that licenses are not required for it and that license
  messages can be ignored. OSPF works.
- **Limits.** It forwards only a few thousand packets per second, and Juniper lists features it does not support, among them
  VRRP and multicast. Units that need those will use another router.
- **The management network is a routing instance of its own.** The container's start-up configuration includes
  `set system management-instance`, which puts the management port `re0:mgmt-0` into the instance `mgmt_junos`. Its routes are
  in `mgmt_junos.inet.0`, apart from `inet.0`, so the routes you change in the lab are not the routes that carry your own access.
- **Ports appear a little late.** For about a minute after the container reports the router as healthy, `et-0/0/0` does not exist
  yet (`error: device et-0/0/0 not found`). You can configure it in the meantime: the configuration waits for the port.
- **Internal units.** Ports show a unit `16386` (or `32767` on a VLAN-tagged port) with the family `multiservice`. The router
  creates them for itself. You do not configure or use them.
- **Two more tables.** `show route` also lists `inet.2` and `inet.3` with copies of the direct routes. J0 does not use them.
- **The first commit.** The oldest entry of `show system commit`, `by root via other`, is the start-up configuration that the
  container loaded.

## 3. Translations in one table

| You want to | IOS | IOS XR | Junos |
|---|---|---|---|
| enter configuration | `configure terminal` | `configure` | `configure` (`private`, `exclusive`) |
| run a show from configuration | `do show …` | `do show …` | `run show …` |
| see the change before applying | — | `show configuration` | `show \| compare` |
| apply | as you type | `commit` | `commit` (`check`, `confirmed n`, `comment`, `and-quit`) |
| print as commands | `show running-config` | `show running-config` | `show configuration \| display set` |
| list the commits | — | `show configuration commit list` | `show system commit` |
| go back one change | — | `rollback configuration last 1` | `rollback 1` then `commit` |
| address an interface | `ip address` under the interface | `ipv4 address` under the interface | `set interfaces <port> unit <n> family inet address <a/len>` |
| shut an interface | `shutdown` | `shutdown` | `set interfaces <port> disable` |
| brief interface status | `show ip interface brief` | `show ipv4 interface brief` | `show interfaces terse` |
| routing table | `show ip route` | `show route` | `show route table inet.0` |
| enable OSPF on an interface | `network …` or `ip ospf … area` | `interface` under the area | `set protocols ospf area <a> interface <unit>` |
| redistribute into OSPF | `redistribute …` | `redistribute …` | an export policy (later unit) |

## 4. Where to look things up

- On the router: `?` after any word, and `help apropos <word>` for commands that contain the word.
- Juniper's documentation is organised by guide. The ones behind this unit: *CLI User Guide for Junos OS*,
  *Interfaces Fundamentals for Junos OS*, *Junos OS Routing Protocols Overview*, and *Routing Policies, Firewall Filters, and
  Traffic Policers User Guide*.

:::note
Sources: Juniper Networks, *vJunosEvolved Deployment Guide* (2025-11-11): the reference router, licenses, limitations and
unsupported features; *CLI User Guide for Junos OS* (2026-06-18): the FreeBSD kernel of Junos OS; *Junos OS Evolved Release 26.2R1
Release Notes* (2026-10-22): the platforms of Junos OS Evolved. The IOS XR column is from the IOS XR track. Outputs from
vJunos-Evolved, Junos OS Evolved 26.2R1.7.
:::
