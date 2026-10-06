# Troubleshooting GEN-BGPRING-82573 : Configuration Audit Remediation (Difficulty 4)

## Scenario

A periodic configuration audit has detected routing-control configuration that is **not documented in the design document** on multiple devices. These are believed to have been used during a past migration and never removed. In addition, the monitoring report shows that traffic between RT02 and RT04 is taking a path that differs from the design.

## Topology (Physical)

```
  RT01 ──── RT02
   │          │
  RT04 ──── RT03
```
Link list (connections and addressing):
```
  RT01:E0/0(.1) ── RT02:E0/0(.2)   10.42.221.0/30
  RT02:E0/1(.1) ── RT03:E0/0(.2)   10.152.206.0/30
  RT03:E0/1(.1) ── RT04:E0/0(.2)   10.33.245.0/30
  RT04:E0/1(.1) ── RT01:E0/1(.2)   10.212.65.0/30
```

Loopback1 on each router is the site network (/24). The logical design (AS numbers and peering details) is not shown. Verify it on the devices.

## Requirements

1. Traffic between RT02 and RT04 must pass through the primary-contract transit AS (RT03), in both directions, as stated in the design document.
2. All routing-control configuration that is not documented in the design document must be removed.
3. The configuration documented in the design document (route-maps **RM-LP-IN** / **RM-PREPEND-OUT** and their application) must not be changed.
4. Reachability to all networks must be maintained.

## Restrictions

1. Everything that differs from the design document must be removed, regardless of whether it actually affects forwarding.
2. Deleting BGP sessions and adding static routes are not allowed.

## Access and Scoring

Log in to each device via SSH (`SUZUKI / CCNP`; the mgmt IPs are given when the problem is issued).

```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPRING-82573 --vault-password-file <(printf 'CCNP\n')
```
