# M6 — 実践(3) GTSM と TCP-AO

ラボ **XRT-17** の課題です。ラボから離れた場所でも読めるように、ここに載せています。
取り組むのはラボのワークスペースです。**Tasks** タブに、課題ごとの確認ボタン、段階式のヒント、
通過後に開く模範解があります。コマンド例は意図して示していません。

## M6 — BGP(追補)

### 課題 M6-7
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t7">ワークスペースで開く</a> — 読み物: <a href="65-m6-protect-session.html#s2-1">2.1 TTL で隣を確かめる: GTSM</a> · <a href="65-m6-protect-session.html#s3-1">3.1 GTSM の設定例</a> · <a href="65-m6-protect-session.html#s3-4">3.4 出力の読み方と落とし穴</a></p>


AS 65100 は、PE2 と X1 の間の eBGP セッションに GTSM(Generalized TTL Security Mechanism)を使用することに合意しました。

- PE2 と X1 の両方でこのセッションに GTSM を設定し、1 ホップ先の直接接続された相手から届くパケットだけを受け付けるようにしてください。
- セッションは確立している必要があり、PE2 は引き続き X1 から経路を学習する必要があります。

### 課題 M6-8
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t8">ワークスペースで開く</a> — 読み物: <a href="65-m6-protect-session.html#s2-2">2.2 TCP のセグメントに署名する: MD5 と TCP-AO</a> · <a href="65-m6-protect-session.html#s2-3">2.3 TCP-AO の鍵: キー チェーン、KeyID、SendID と ReceiveID</a> · <a href="65-m6-protect-session.html#s3-3">3.3 TCP-AO の設定例</a> · <a href="65-m6-protect-session.html#s3-4">3.4 出力の読み方と落とし穴</a></p>


PE3 と X2 の間の eBGP セッションを、TCP 認証オプション(TCP-AO)で保護します。値は AS 65100 と合意済みです。

| 項目 | 値 |
|---|---|
| キー チェーンの名前 | AS65100-AO |
| キー ID | 7 |
| 暗号アルゴリズム | AES-128-CMAC-96(IOS XE では aes-128-cmac) |
| キー文字列 | 5A3C9E107B2D4F6681A0C3E5F7092B4D |
| PE3 の SendID、ReceiveID | 37、73(X2 は SendID 73、ReceiveID 37) |
| TCP オプション | MAC の計算に含める |
| キーの有効期間 | 無期限 |

- PE3 と X2 の両方を設定してください。セッションは TCP-AO で確立している必要があります。
