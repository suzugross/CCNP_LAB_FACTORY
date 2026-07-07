# 問題 ENCOR-RSPAN-01 : RSPAN でスイッチ間をまたいでミラー（難易度5）

## シナリオ
監視対象の端末は **SW01** に、アナライザ（IDS）は離れた **SW02** に接続されている。
ローカル SPAN では届かないため、**RSPAN** を使って SW01 のユーザポートのトラフィックを
RSPAN VLAN に載せてトランク越しに SW02 へ運び、SW02 のアナライザポートへ出力する。

## トポロジ
```
  [営業端末]            RSPAN VLAN 199             [アナライザ]
   Gi0/1                  (trunk)                    Gi0/1
     │                Gi0/0 ═══ Gi0/0                  │
   SW01 ──────────────────────────────────────────── SW02
  (送信元スイッチ)                                  (宛先スイッチ)
```

| スイッチ | 役割 | ポート |
|----------|------|--------|
| SW01 | 送信元（source） | `Gi0/1`=営業端末(監視対象) ／ `Gi0/0`=SW02へのトランク |
| SW02 | 宛先（destination） | `Gi0/1`=アナライザ(ミラー先) ／ `Gi0/0`=SW01へのトランク |

- VLAN10(USERS) と Gi0/0 のトランク（dot1q）は両SWで設定済み。
- 管理は `Gi3/3` / VLAN999（**両SWとも触らないこと**）。

## 到達目標
1. **両スイッチ**に RSPAN 用 VLAN **199** を作成し、**RSPAN VLAN（remote-span）** として指定する。
2. **SW01（送信元）**：`monitor session 1` で
   - source = 監視対象ユーザポート **Gi0/1**
   - destination = **RSPAN VLAN 199**
3. **SW02（宛先）**：`monitor session 1` で
   - source = **RSPAN VLAN 199**
   - destination = アナライザ **Gi0/1**

## 制約
- 変更してよいのは **SW01 / SW02 のみ**。管理IF(`Gi3/3`)/VLAN999 には触れない。
- RSPAN VLAN は**両SWで同じ VLAN 番号**・**両方で remote-span 指定**が必須。

## アクセス・採点
- iosvl2 は mgmt SVI が上がらないため、**CMLコンソールから直接**解いてください（SSH/telnet不可）。
- 採点（console収集・両SW）：
  ```
  ansible-playbook playbooks/grade.yml -e problem=ENCOR-RSPAN-01 --vault-password-file <(printf 'CCNP\n')
  ```
  ※ `show vlan remote-span` と各SWの `show monitor session 1`（Type / source / destination）を確認します。
