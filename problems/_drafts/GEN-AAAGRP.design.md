# GEN-AAAGRP 設計メモ — IOS AAA サーバグループ構築問（難易度4）

状態: **未着手**（BACKLOG BL-001）。計画提案 2026-07-08、実装は保留中。

## ねらいと GEN-RADIUS-100 との棲み分け

| | GEN-RADIUS-100（既存） | GEN-AAAGRP（本問） |
|---|---|---|
| サーバ側 | 受験者が FreeRADIUS を構築 | **生成器が全自動構築（2台）** |
| IOS側 | 単一サーバ・既定ポート・`group radius` | **named サーバグループ・2台・非標準ポート・サーバ別キー** |
| 学習核心 | Linux×IOS の境界、Reject≠フォールバック | **冗長AAA設計とフェイルオーバー動作の理解** |

## トポロジ（4ノード＋MGMT）

```
SRV01(FreeRADIUS #1) ──┐
   10.99.1.2/30         RT01 ────── RT02
SRV02(FreeRADIUS #2) ──┘   10.1.12.0/30
   10.99.2.2/30
```

- IF/OSPF は投入済み（RT02 からも両サーバ到達可）
- SRV01/02 は init.sh で FreeRADIUS 完全構成済みで起動（clients.conf は各RTの **Lo0** のみ許可）

## 受験者への提供物：「サーバ仕様書」

ヒント控えめ方針と両立させるため、サーバ側の事実だけを仕様書形式で渡す（IOSコマンドは出さない）:

| 項目 | SRV01 | SRV02 |
|---|---|---|
| IP | 10.99.1.2 | 10.99.2.2 |
| 待受ポート | 1812/1813（標準） | **1912/1913 相当の非標準（seed乱数）** |
| 共有キー | K1（seed乱数） | K2（サーバ毎に別） |
| 受理する送信元 | 各RTの Loopback0 のみ | 同左 |

## IOS側の要件

1. **サーバ登録**: `radius server` 定義 ×2（名前付き new-style 必須）
2. **ポート設定**: SRV02 は auth-port/acct-port を仕様書に合わせる
3. **共有キー**: サーバ毎に異なる key
4. **サーバグループ**: `aaa group server radius <GRP名>` に2台登録＋`deadtime`
5. **ローカルDB**: 緊急用ローカル管理者（例 `emg-admin` priv15）＋SUZUKI維持。方式リストは `group <GRP> local`
6. **ひねり①（送信元）**: サーバは Lo0 からのみ受理 → `ip radius source-interface Loopback0` に自力で気付かせる（外すとサイレント無視→タイムアウトの実戦的症状）
7. **ひねり②（タイマ）**: 「片系障害時のログイン遅延を数秒以内に」→ `timeout`/`retransmit` チューニング（採点高速化も兼ねる）
8. （採否未決）`aaa accounting exec default start-stop group <GRP>` — サーバ側ログで採点

RADIUSアカウント台帳（admin=priv15 / monitor=priv1 / **SUZUKI登録必須**）は既存問踏襲。
「Reject時はlocalへ落ちない」締め出し教訓も維持。

## 採点設計（目玉: 3フェーズ挙動採点）

1. **正常時**: 両RTで `test aaa group <GRP> … legacy` Accept、SSH実ログインで priv-lvl、誤パス Reject
2. **SRV01停止**（採点PBが SSH で `systemctl stop freeradius`）: それでも Accept → SRV02のポート/キー/グループ登録の証明
3. **両サーバ停止**: ローカル `emg-admin` でSSHログイン成功 → ローカルフォールバックの証明 → **always 節で必ず両サーバ再起動**

構成検査（show run regex）は方式リスト順序・グループ所属など挙動で見えない部分のみ。
`show aaa servers` の "auth-port 1912"（コロン無し表記）実効値も採点。

## 実装ステップ

1. **PoC（半日想定）**:
   - FreeRADIUS 非標準ポート待受（sites-enabled/default の listen 編集）＋IOS auth-port 疎通
   - `test aaa group <名前付きGRP>` 構文の IOL 実機確認
   - サーバ停止→フェイルオーバー→local 落ちの遅延実測（採点タイムアウト設計用）
2. **生成器 `gen_aaa_build.py`**: gen_radius_build.py の骨格流用。
   seed乱数 = ユーザ名/パス/キー2種/非標準ポート/グループ名/Lo0アドレス
3. **実機フルサイクル**: build→lab_up→素点→solution投入→100点確認（採点中のサーバ停止/復旧の安定性を重点確認）
4. **出題**: task.md 全文チャット貼り＋VSCodeプレビューリンク（規約どおり）

## リスクと対策

- **採点中のサーバ停止で採点自身が締め出し**: SUZUKI を RADIUS台帳＋ローカル両方に置き全フェーズSSH可。
  フェーズ3のログイン遅延は要件7のタイマ短縮が保険
- **非標準ポートの FreeRADIUS 設定は未検証** → PoC 最優先項目
- **Lo0送信元ひねりの難度調整**: 仕様書の文言で調整（「送信元IPに注意」の一言を足す/足さない）

## 未決事項

1. アカウンティング要件（8）の採否 — 推奨は「入れる」（サーバ側ログ採点は FNF 等で実績あり）
2. Lo0 送信元ひねり（6）の採否 — 外せば難易度 3.5 相当
3. 問題ID — `GEN-AAAGRP-<seed>`（生成器方式なら seed 系列を推奨）
