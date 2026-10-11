# Problem GEN-IPSLATS-88817 : WAN Path Monitoring Standard Compliance Troubleshooting (Difficulty 4)

## Scenario

You are the network administrator of a company. The edge router RT01 is dual-homed to
two ISPs (RT02 = primary / RT03 = backup) and reaches the Internet service `8.8.8.8`.
In accordance with the company's "WAN Path Monitoring Standard (excerpt below)", the health
of the primary path must be actively monitored, and traffic must automatically switch over
to the backup in the event of a failure.

Deployment and change work related to this monitoring was recently carried out. Since then,
the following trouble report has been submitted. Investigate and correct the configuration
of RT01 so that it fully complies with the monitoring standard.

## Trouble Report

> Part of the outbound traffic constantly goes through the backup ISP, and usage-based charges are increasing. There are no logs of switchover events.

## Topology

```
RT01 ──10.88.142.0/30── RT02 ──10.88.163.0/30── RT04(Internet)
    ╲─10.88.184.0/30── RT03 ──10.88.189.0/30──┘
              (an inter-ISP link 10.88.20.0/30 exists between RT02 and RT03)
```

- Each /30 uses .1/.2 in the order RT01 side, ISP side; on the uplinks, the ISP side is .1 and the RT04 side is .2.
- Internal address of RT01: `Loopback0 = 3.3.3.3` (the source of data traffic).
- `8.8.8.8` is reachable through either the primary or the backup ISP (for data).
- For liveness checks of the primary path, the provider offers a health beacon,
  **`100.64.124.26`, that is reachable only over the primary path (RT01→RT02→RT04)**.
  The backup ISP has no route to this beacon.

## WAN Path Monitoring Standard (excerpt)

1. **Monitoring** — Use IP SLA **39** to monitor the health beacon
   **`100.64.124.26`** with **ICMP echo**. The source must be the address of the
   primary-side interface, **`10.88.142.1`**.
2. **Pinning the probe path** — Pin a /32 static route for the beacon to the primary
   next-hop **`10.88.142.2`** (the probe must not depend on the default route).
3. **Tracking** — Use Track **35** to monitor the **reachability** of IP SLA 39.
4. **Path switchover** — The default route must be the primary **`10.88.142.2`**
   (tied to Track 35) under normal conditions, and the backup **`10.88.184.2`**
   (a floating static route with AD **250**) upon failure.
5. **Schedule** — The monitoring must run **permanently (life forever, start-time now)**.
6. **Completeness of the correction** — Do not leave any operation definitions that are not
   part of the monitoring standard, or any filters that interfere with the monitoring.

## Restrictions

- **RT02 / RT03 / RT04 are provider-managed devices. You may view them, but you must not
  change them.** Only RT01 may be reconfigured.
- Do not change the interface addresses or Loopback0 of RT01.
- The type, location, and number of causes are not disclosed. Compare the monitoring standard
  with the state of the devices to identify the differences.

## Access / Scoring

SSH `SUZUKI / CCNP` (mgmt addresses in order of assignment) or the CML console.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-IPSLATS-88817 --vault-password-file <(printf 'CCNP\n')
```
> Scoring checks the monitoring definition, operational state, and route configuration, as well as
> actual reachability to `8.8.8.8`. Optionally, to inject a far-side failure (RT02↔RT04) and
> demonstrate switchover and recovery:
> `ansible-playbook playbooks/verify_ipsla_generated.yml -e problem=GEN-IPSLATS-88817`
