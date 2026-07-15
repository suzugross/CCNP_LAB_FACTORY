# 問題 ENARSI-BGP-ASPATH-RM-01 : as-path マッチで BGP 属性制御（5本ノック・難易度4）

## この問題について（属性操作の型稽古）

上流の **RT02 (FEEDER, AS65099)** は、AS_PATH を作り分けた経路群（battery）を
RT01 へ eBGP で広告している。あなたは **RT01 (AS65001)** 上で、
**as-path で経路を識別して属性を付ける** ことで、経路の「選ばれ方／扱われ方」を制御する。

前段の as-path アクセスリスト道場（定義するだけ）の一段上で、今回は
**`route-map` で `match as-path` → `set 属性` を行い、neighbor に inbound 適用**して
実際に BGP テーブルへ効かせる（＝ ENARSI「BGP パス制御」の本丸）。

```
  RT01 (TARGET, AS65001) ──eBGP── RT02 (FEEDER, AS65099・変更禁止)
        ↑ ここで inbound route-map(match as-path → set 属性) を組む
```

## FEEDER が広告している battery（RT01 で `show ip bgp` の Path 列を確認）
| プレフィックス | RT01 が受信する AS_PATH | 位置づけ |
|---|---|---|
| 172.16.1.0/24 | `65099 65210` | 起源 65210 |
| 172.16.2.0/24 | `65099 65220` | 起源 65220 |
| 172.16.3.0/24 | `65099 65230` | 起源 65230 |
| 172.16.4.0/24 | `65099 65240` | 起源 65240 |
| 172.16.5.0/24 | `65099 65250 65260` | 65250 **経由**・起源 65260 |
| 172.16.6.0/24 | `65099` | 起源 65099（制御対象外）|
| 172.16.7.0/24 | `65099 65270` | 起源 65270（制御対象外）|

## 課題（RT01 で inbound の属性制御を行う・各20点）

> **課題1** — **AS 65210 が起源**（AS_PATH 末尾が 65210）の経路の **local-preference を 200** にせよ。
>
> **課題2** — **AS 65220 が起源**の経路の **weight を 100** にせよ。
>
> **課題3** — **AS 65230 が起源**の経路の **local-preference を 50** にせよ（不利にする）。
>
> **課題4** — **AS 65240 が起源**の経路に **community `65001:444`** を付与せよ。
>
> **課題5** — **AS 65250 を経由**（AS_PATH に 65250 を含む）する経路に、
> **as-path prepend で自AS(65001)を2回**足せ（inbound で AS_PATH を伸ばす）。

## 進め方（推奨）
- as-path 識別は `ip as-path access-list <n>` で（前回の道場の通り）。
- それを `route-map` の各 seq で `match as-path <n>` → `set ...` し、
  **1本の route-map を `neighbor 10.1.12.2 route-map <名前> in` で適用**するのが定石
  （各課題＝route-map の1シーケンス。条件は互いに素なので順序は問わない）。
- 適用後は inbound を再処理させること：**`clear ip bgp * in`**（効かなければ `clear ip bgp *`）。
- 素振り確認: `show ip bgp <prefix>`（`localpref` / `weight` / `Community:` / Path を見る）。

## 遵守事項
1. **RT02 (FEEDER) の変更は禁止**（show は可）。
2. RT01 の設定（as-path ACL / route-map / neighbor への適用）で解く。
   BGP セッションやインタフェースの構成は変えないこと。
3. 制御対象外（172.16.6.0/24・172.16.7.0/24）の属性を変えないこと。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。CML コンソールでも可。
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-ASPATH-RM-01 --vault-password-file <(printf 'CCNP\n')
```
採点は **効果ベース**（`show ip bgp <prefix>` の属性一致・各20点・部分点なし）。手段は問わない。
