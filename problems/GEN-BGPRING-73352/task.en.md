# Trouble Ticket GEN-BGPRING-73352 : Restoring the Path Selection Policy (difficulty 4)

## Scenario

The routers of four organizations are interconnected in a ring. A policy based on a contract is defined for the path of the traffic between RT01 and RT03. However, the most recent monitoring report shows that the traffic is transiting a path that is not intended. Note that last night, a configuration restore was performed as part of a device replacement.

## Topology (Physical)

```
  RT01 ──── RT02
   │          │
  RT04 ──── RT03
```
Link list (connections and addresses):
```
  RT01:E0/0(.1) ── RT02:E0/0(.2)   10.130.253.0/30
  RT02:E0/1(.1) ── RT03:E0/0(.2)   10.54.171.0/30
  RT03:E0/1(.1) ── RT04:E0/0(.2)   10.247.249.0/30
  RT04:E0/1(.1) ── RT01:E0/1(.2)   10.249.233.0/30
```

Loopback1 of each router is the site network (/24). The logical design (AS numbers and peering details) is not shown. Verify it on the devices.

## Requirements

1. The preference between the two transit ASs (RT02 / RT04) is, based on an agreement between the providers, **expressed by the MED attribute**. This agreement must be honored in path selection.
2. Traffic between RT01 and RT03 must transit the same transit AS (RT02) in both directions.
3. Reachability to all networks must be maintained.

## Restrictions

1. Removing BGP sessions and adding static routes are not allowed.
2. Changes that affect the path of traffic that is out of scope must be kept to a minimum.

## Access and Scoring

Log in to each device with SSH (`SUZUKI / CCNP`; the mgmt IP addresses are provided when the problem is presented).

```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPRING-73352 --vault-password-file <(printf 'CCNP\n')
```
