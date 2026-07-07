# 問題 GEN-RADIUS-100 : 中央認証(FreeRADIUS)×IOS AAA 構築（難易度4）

## シナリオ
監査対応のため、ルータのログイン認証を**中央 RADIUS サーバ(SRV01)**へ統合します。
アカウントは RADIUS で一元管理し、ローカルユーザは**サーバ障害時の予備**とします。

```
 SRV01 ────── RT01 ────── RT02
(FreeRADIUS)
 10.99.0.0/30   10.1.12.0/30
```

## 構成（初期状態で投入済み・変更不可）
- ルーティング(OSPF)・各 IF の IP は設定済み（RT02 からも SRV01 へ到達可能）
- SRV01: ens3 = `10.99.0.2/30`。**freeradius / freeradius-utils 導入済み（未設定）**
- 両ルータは現在ローカル認証（SUZUKI / CCNP）

## 要件
### A. RADIUS サーバ（SRV01 / FreeRADIUS）
- **アカウント台帳**（この 3 ユーザを認証できること）:

| ユーザ | パスワード | 権限 |
|--------|-----------|------|
| noc-hanako | `Noc-3863` | 管理者（ログイン直後から **priv 15**） |
| monitor-op | `Desk-6730` | 閲覧のみ（ログイン直後 **priv 1**） |
| SUZUKI | `CCNP` | 自動化・採点用（**priv 15・登録必須**） |

- 権限レベルは RADIUS の応答属性で機器へ渡すこと（Cisco の VSA を使う）
- **クライアント**: RT01・RT02 の 2 台。共有シークレット `Ccnp-Rad-8102`
- 既定で入っている **localhost クライアント（secret testing123）は採点が使うため残すこと**

### B. 機器側 AAA（RT01・RT02 の両方）
- ログイン認証を **RADIUS 優先・ローカル予備**に切り替えること
- exec 権限(認可)も RADIUS の属性に従うこと
- RADIUS サーバ定義: `10.99.0.2`、認証ポート 1812 / アカウンティング 1813

## 到達目標
- noc-hanako / monitor-op / SUZUKI が RADIUS 経由で両ルータへ SSH ログインできる
  （noc-hanako=即 priv15、monitor-op=priv1、SUZUKI=即 priv15）
- 誤パスワードは拒否される
- 各ルータで `test aaa group radius <user> <pass> legacy` が成功する

## サーバ操作ガイド（NW 機器と勝手が違う所だけ。設定値は要件から組み立てること）
SRV01 へは SSH `SUZUKI / CCNP`（sudo 可）。設定は **/etc/freeradius/3.0/** 配下。
- クライアント（NAS）定義: `clients.conf` — `client <名前> { ipaddr = … / secret = … }`
  の**改行区切り**（セミコロン不要。付けると構文エラー）
- ユーザ定義: `mods-config/files/authorize` — 1 ユーザ =
  `<名前> Cleartext-Password := "<パス>"` ＋ 続く行に**タブ字下げで応答属性**
  （属性行は最後の 1 行以外、行末カンマ）。Cisco の権限属性は
  `Cisco-AVPair = "shell:priv-lvl=<N>"`
- 検証と反映:
  - 構文チェック: `sudo freeradius -XC`
  - `sudo systemctl restart freeradius` → `systemctl status freeradius`
  - ローカル試験: `radtest <user> '<pass>' 127.0.0.1 0 testing123`
    （Access-Accept / Access-Reject が返る）
  - 詳細ログ: いったん `sudo systemctl stop freeradius` →
    `sudo freeradius -X`（フォアグラウンドデバッグ。Ctrl+C で戻し、start を忘れずに）
- ★**クライアントの ipaddr は「機器が RADIUS を送る送信元 IP」**。
  対向直結でないルータはどの IP から届くか（経路の出口 IF）を考えること

## 注意（締め出しリスク — 本問最大の落とし穴）
- `… group radius local` の **local 予備が効くのは「サーバ無応答」の時だけ**。
  RADIUS が生きていて **Reject を返した場合、ローカル認証へは切り替わらない**。
  → 台帳の SUZUKI 登録を漏らすと、自分も採点も締め出される
- 機器側の AAA を書いたら、**ログアウトする前に** 別セッション or `test aaa` で
  ログインできることを必ず確認すること（コンソールからは復旧可能）

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13）
```
ansible-playbook playbooks/grade.yml -e problem=GEN-RADIUS-100 -e max_attempts=10 \
  --vault-password-file <(printf 'CCNP\n')
```
