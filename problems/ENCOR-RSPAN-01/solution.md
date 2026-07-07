# 模範解答 ENCOR-RSPAN-01

## SW01（送信元スイッチ）
```
configure terminal
vlan 199
 remote-span
 exit
monitor session 1 source interface GigabitEthernet0/1 both
monitor session 1 destination remote vlan 199
end
```

## SW02（宛先スイッチ）
```
configure terminal
vlan 199
 remote-span
 exit
monitor session 1 source remote vlan 199
monitor session 1 destination interface GigabitEthernet0/1
end
```

## ポイント
- RSPAN VLAN は**両SWで同じ番号**＋**両方で `remote-span`**。これが無いと普通の VLAN 扱いでミラーが運べない。
- 送信元SW：ローカル source（物理ポート）→ destination は **`remote vlan`**。
- 宛先SW：source は **`remote vlan`** → destination は物理ポート（アナライザ）。
- RSPAN VLAN はトランク（Gi0/0）を通って SW 間を渡る（本問はトランク設定済み）。
- 確認:
  - `show vlan remote-span` → `199`
  - SW01 `show monitor session 1` → `Type : Remote Source Session` / `Both : Gi0/1` / `Dest RSPAN VLAN : 199`
  - SW02 `show monitor session 1` → `Type : Remote Destination Session` / `Source RSPAN VLAN : 199` / `Destination Ports : Gi0/1`
