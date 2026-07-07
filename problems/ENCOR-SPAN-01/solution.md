# 模範解答 ENCOR-SPAN-01

```
configure terminal
monitor session 1 source interface GigabitEthernet0/1 both
monitor session 1 source interface GigabitEthernet0/2 rx
monitor session 1 destination interface GigabitEthernet0/3
end
```

## ポイント
- `both`（既定）は送受信両方、`rx` は受信のみ、`tx` は送信のみ。要件で方向を分ける。
- destination ポートは SPAN 専用になり通常スイッチングから外れる。
- 確認: `show monitor session 1`
  - `Both : Gi0/1` / `Rx Only : Gi0/2` / `Destination Ports : Gi0/3`
