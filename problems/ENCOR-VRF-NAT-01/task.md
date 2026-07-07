# 問題 ENCOR-VRF-NAT-01 : VRF対応 NAT（重複アドレス顧客の共有Internet接続・難易度6）

## シナリオ
エッジルータ **RT01** が 2 社の顧客（**RED** / **BLUE**）を VRF で収容している。両顧客は
**まったく同じプライベートアドレス `10.0.0.0/24`（重複）** を使っている。両顧客を、
**共有の 1 本のグローバル ISP 回線**経由で **インターネット `8.8.8.8` に接続**したい。

アドレスが重複しているため、**VRF 対応の NAT(PAT)** で各顧客を個別に変換する必要がある。

## トポロジ
```
  RED 顧客 10.0.0.1/24                         ┌── Internet 8.8.8.8
   (RT03) ── Et0/0[VRF RED]  ┐                 │   (RT02 / ISP)
                              RT01 ── Et0/2 ════╧═ 100.64.0.0/30 (global)
   (RT04) ── Et0/1[VRF BLUE] ┘  (エッジ / 変更対象)
  BLUE 顧客 10.0.0.1/24
```

| ルータ | 役割 | 設定 |
|--------|------|------|
| RT01 | エッジ（**変更対象**） | RED(Et0/0=10.1.13.1/30) ／ BLUE(Et0/1=10.2.14.1/30) ／ ISP(Et0/2=100.64.0.1/30, global) |
| RT02 | ISP / Internet（**変更不可**） | Et0/0=100.64.0.2 ／ Lo0=`8.8.8.8` |
| RT03 | RED 顧客（**変更不可**） | Lo0=`10.0.0.1/24` ／ Et0/0=10.1.13.2 ／ RT01へデフォルト |
| RT04 | BLUE 顧客（**変更不可**） | Lo0=`10.0.0.1/24` ／ Et0/0=10.2.14.2 ／ RT01へデフォルト |

## 到達目標 — RT01 のみ
1. VRF **RED / BLUE** を定義し、顧客IF を所属させる（Et0/2 は **global**＝VRFなし）。
2. **VRF対応 NAT(PAT)** を構成：
   - RED / BLUE それぞれの顧客 `10.0.0.0/24` を、**ISP 側 Et0/2** のアドレスへ **overload(PAT)** で変換する。
   - 顧客IF=`ip nat inside`、ISP IF=`ip nat outside`。
3. 経路：各 VRF の顧客向け経路と、**VRF から global 側 ISP へインターネットトラフィックを抜く**経路を用意する。
4. 結果として、**RT03（RED）と RT04（BLUE）の両方が `8.8.8.8` に到達**できること。

## 制約
- 変更してよいのは **RT01 のみ**。RT02 / RT03 / RT04 は変更不可。
- 重複アドレス `10.0.0.1` を **VRF ごとに正しく区別**して変換すること（混線・分離崩れは不可）。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は build 時に割当）。
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-VRF-NAT-01 --vault-password-file <(printf 'CCNP\n')
```
※ 採点は NAT 設定／inside・outside に加え、**RT03・RT04 から `8.8.8.8` への実ping**と、
`show ip nat translations vrf RED|BLUE` の**VRF別変換エントリ**を能動確認します。
