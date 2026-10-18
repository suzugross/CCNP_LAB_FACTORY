# M1 — Managing Configuration

In M0 you met the rule that nothing takes effect until you `commit`. This unit is about what that rule buys you:
a change is applied as a unit, it can be refused as a unit, it is recorded, and it can be taken back.

Everything shown here was captured on IOS XRv 9000 release 24.3.1.

## 1. Two configurations

There are always two configurations in play.

- The **running configuration** is what the router is doing now.
- The **target configuration** is private to your configuration session. It starts as a copy of the running
  configuration. The lines you type change the target only.

`commit` applies the difference between the two to the running configuration.

Three views tell you where you stand before you commit. All three are run from configuration mode.

| Command | Shows |
|---|---|
| `show configuration` | only the lines you have staged |
| `show commit changes diff` | the same change as `+` and `-` lines against the running configuration |
| `show configuration merge` | the whole configuration as it would be after the commit |

```console
RP/0/RP0/CPU0:XR01(config)#show commit changes diff
!! Building configuration...
!! IOS XR Configuration 24.3.1
-  interface Loopback11
-   ipv4 address 11.11.11.11 255.255.255.255
   !
end
```

## 2. A commit is all or nothing

A plain `commit` either applies every staged line or none of them. Here a BGP neighbor refers to a route policy
that has not been defined, in the same commit as an unrelated loopback:

```console
RP/0/RP0/CPU0:XR01(config)#commit
% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted.
  Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:XR01(config)#show configuration failed
!! SEMANTIC ERRORS: This configuration was rejected by
!! the system due to semantic errors. The individual
!! errors with each failed configuration command can be
!! found below.
router bgp 65001
 neighbor 10.0.12.2
  address-family ipv4 unicast
   route-policy NOPE in
!!% Could not find entry in list: Policy [NOPE] must be defined before it can be attached.
  !
 !
!
end
```

Two kinds of error exist. A *syntax* error is caught when you press Enter, as on IOS. A *semantic* error —
the line is well formed but cannot be applied — is caught at commit time, by the process that owns that part of
the configuration. `show configuration failed` shows the rejected lines with the reason under each.

After a refused commit:

- nothing was applied — the loopback did not go in either;
- nothing was lost — `show configuration` still shows everything you typed. Fix the problem and commit again.

`commit best-effort` is the alternative: it applies every line that can be applied and drops only the failing ones.
Use it deliberately. It gives you a configuration that nobody typed as a whole.

## 3. Every commit is recorded

```console
RP/0/RP0/CPU0:XR01#show configuration commit list
SNo. Label/ID              User      Line                Client      Time Stamp
~~~~ ~~~~~~~~              ~~~~      ~~~~                ~~~~~~      ~~~~~~~~~~
1    undo-first            SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:51 2026
2    second-change         SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:47 2026
3    first-change          SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:18:45 2026
4    1000000003            ZTP       ZTP                 CLI         Mon Oct 12 13:16:27 2026
5    1000000002            ZTP       ZTP                 CLI         Mon Oct 12 13:16:23 2026
6    1000000001            CVAC      UNKNOWN             CLI         Mon Oct 12 13:16:17 2026
```

Each commit gets an ID. You can give it a name and a note when you make it —
`commit label first-change comment add-lo11` — and from then on refer to it by the label.
A label must be unique; reusing one is refused.

What a commit changed:

```console
RP/0/RP0/CPU0:XR01#show configuration commit changes first-change
!! Building configuration...
!! IOS XR Configuration 24.3.1
interface Loopback11
 ipv4 address 11.11.11.11 255.255.255.255
!
end
```

`show configuration commit changes last 3` shows the last three together. The system log records each commit too,
with the user and the command that displays it.

This turns a familiar question around. On IOS, "what changed?" means comparing configurations and hoping someone
kept an archive. On IOS XR you ask the router, and it tells you who, when, from which line, and exactly which lines.

## 4. Going back

There are two different operations, and the difference matters.

**Roll back a run of commits, newest first.**

```console
RP/0/RP0/CPU0:XR01#rollback configuration ?
  last        Rollback last <n> commits made
  to          Rollback up to (and including) a specific commit
  to-exclude  Rollback up to (and excluding) a specific commit
```

This returns the router to an earlier point in time. Everything committed after that point goes, whoever made it.

**Take back one commit and leave the later ones alone.** In configuration mode:

```console
RP/0/RP0/CPU0:XR01(config)#load rollback changes first-change
Loading.
89 bytes parsed in 1 sec (88)bytes/sec
RP/0/RP0/CPU0:XR01(config)#show configuration
!! Building configuration...
!! IOS XR Configuration 24.3.1
no interface Loopback11
end
RP/0/RP0/CPU0:XR01(config)#commit label undo-first
```

`load rollback changes` does not change the router. It puts the *reverse* of that commit into your target
configuration, where you can read it, edit it, and commit it like anything else.
You can preview it from EXEC mode with `show configuration rollback changes <id>`.

A rollback is itself recorded as a commit. Nothing is erased from the history.

## 5. A commit that takes itself back

The change that worries you most is the one that might cut off your own access. For that there is

```console
RP/0/RP0/CPU0:XR01(config)#commit confirmed 30
```

The change is applied at once, provisionally. If you issue a plain `commit` within the time (30 to 65535 seconds,
or `minutes`), it becomes permanent. If you do not, the router rolls it back by itself, and the history shows it:

```console
1    1000000011            SUZUKI    con0_RP0_CPU0       Rollback    Mon Oct 12 13:20:46 2026
2    1000000010            SUZUKI    con0_RP0_CPU0       CLI         Mon Oct 12 13:20:12 2026
```

Two details, both measured on this release, decide whether this works for you.

- **Stay in configuration mode.** Leaving it (`end`, `exit`) cancels a pending confirmed commit immediately.
  The router does not wait for the timer. If your plan is "commit confirmed, drop out to EXEC, test, come back
  and confirm", the change is already gone by the time you test.
- After an automatic rollback your target configuration is empty. The change is not kept for a second attempt.

## 6. Replacing everything

`commit replace` does not merge. It makes the running configuration equal to your target configuration,
which means deleting everything that you did not stage. Before you ever use it, look:

```console
RP/0/RP0/CPU0:XR01(config)#hostname REPLACED
RP/0/RP0/CPU0:XR01(config)#show configuration changes
!! Building configuration...
!! IOS XR Configuration 24.3.1
hostname XR01
hostname REPLACED
no username SUZUKI
no vrf MGMT
no interface Loopback0
no interface MgmtEth0/RP0/CPU0/0
no interface GigabitEthernet0/0/0/0
no router ospf 1
no ssh server v2
no ssh server vrf MGMT
end
```

(Output shortened.) The user account, the management VRF and interface, and the SSH server are all on the list.

## 7. More than one person

Each configuration session has its own target configuration, so two people can prepare changes at the same time.
The router tells you about the others as you enter:

```console
RP/0/RP0/CPU0:XR01#configure terminal
Current Configuration Session  Line       User     Date                     Lock
00001000-00003a0b-00000000     vty0       SUZUKI   Mon Oct 12 13:21:20 2026
```

If someone else commits while you are still editing, your own commit stops and asks:

```console
One or more commits have occurred from other
configuration sessions since this session started
or since the last commit was made from this session.
You can use the 'show configuration commit changes'
command to browse the changes.
Do you wish to proceed with this commit anyway? [no]:
```

To keep everyone else out for the duration of a change, enter with `configure exclusive`.
Others can still enter configuration mode and stage lines, but their commit is refused:

```console
% Failed to commit .. Another configuration session
had a lock on the running configuration.
```

`show configuration sessions detail` and `show configuration lock` show who holds it.

## 8. What changes in your habits

| On IOS you would | On IOS XR |
|---|---|
| type carefully, because each line is live | stage, read `show configuration`, then commit |
| paste a block and hope the middle lines were accepted | the block is applied whole or refused whole |
| `reload in 10` before a risky change | `commit confirmed` |
| compare archived configurations to see what changed | `show configuration commit list`, `show configuration commit changes` |
| retype the reverse commands | `load rollback changes`, or `rollback configuration` |
| `configure replace` | `commit replace`, after `show configuration changes` |

## Practice

Go back to lab **XRT-01** and do the M1 tasks. Finish the M0 tasks first; some M1 tasks use LINK1.

<p class="tolab"><a href="/_learn?id=XRT-01">Open lab XRT-01 in the workspace</a> — <a href="11-m1-practice.html">The tasks</a></p>

:::note
The commit and rollback commands in this unit are not described in the current ASR 9000 *System Setup Command Reference*,
where one would look for them first (checked October 2026; the other volumes were not searched). The descriptions here come from the CLI help and from measurement on 24.3.1.
On another release, check the behaviour before you rely on it — above all the two details in section 5.
:::
