# M13 — 証明書と TLS を土台から

次のページの gNMI とテレメトリは、どちらも TLS で守られ、証明書で動きが決まります。課題 M13-3 と M13-4 も同じです。
このページでは、その前に、証明書と TLS を土台から並べます。鍵ペア、署名、証明書、認証局(CA)、TLS の中で確かめる
4 つのこと、相互 TLS、自己署名と中間 CA を挟んだ証明書チェーンの確かめ方の順です。ブループリントの 5.7 のうち、TLS と相互 TLS の証明書にあたります。

使う道具は SRV01 の上の `openssl` だけで、このページではルータの設定を変えません。XR01 に証明書を置く場所とやり方は、
次のページの 3.2 節で扱います。

## 1. 何が嬉しいのか

### 1.1 困りごと: アドレスは身元を証明しない

XRT-15 では、SRV01 の gnmic が XR01 の 10.0.50.1 のポート 57400 へつなぎ、ラボのアカウントのユーザ名とパスワードを
送ります。逆向きに、XR01 は 10.0.50.10 のポート 57500 へインターフェイスのカウンタを送ります。どちらの側も、相手を
アドレスでしか知りません。

アドレスは身元の証明になりません。NMS のセグメントの別の機械が 10.0.50.1 を名乗れば、設定の誤りでも悪意でも、SRV01 はそこへ
パスワードを渡します。10.0.50.10 を名乗れば、XR01 はそこへカウンタを送ります。線の途中で読む者がいれば、暗号化していない
パスワードはそのまま読まれます。宛名が合っていても、受け取った人が本人とは限りません。

### 1.2 それ以前の手: 平文、パスワード、SSH のホスト鍵

- **平文**: SNMPv2c のコミュニティや、TLS を使わない gRPC(`no-tls`)は、パスワードにあたるものをそのまま運びます。
- **パスワード**: サーバがクライアントを確かめる手段です。逆向き、つまりクライアントがサーバを確かめることはできません。
  偽のサーバは、パスワードを受け取るだけで済みます。
- **SSH のホスト鍵**(M13-1 の NETCONF): SSH は接続を暗号化し、サーバは自分の鍵(ホスト鍵)で身元を示します。そのホスト鍵が
  本物かどうかは、ふつう、初めてつないだときに人が確かめて覚えさせます(`known_hosts`)。ルータが
  100 台なら、覚えさせる鍵も 100 本です。M13-1 のテンプレートは、この確かめを切っていました(`hostkey_verify=False`)。

### 1.3 TLS の答え: 第三者の署名で名前を証明する

- **名前を証明する**: サーバは証明書を見せます。証明書は「この公開鍵は collector.nms.lab のものです」という文に、認証局
  (CA)が署名したものです。
- **確かめる道具は 1 つで足りる**: 確かめる側が持つのは CA 証明書 1 枚です。同じ CA が署名した証明書なら、100 台分でも
  その 1 枚で確かめられます。SSH のように 1 台ずつ覚えさせなくて済みます。
- **暗号化する**: 確かめ終えたら、両端はその場で作った鍵で接続を暗号化します。
- **逆向きにも使える**: 相互 TLS では、クライアントも証明書を見せ、サーバが確かめます。パスワードに加えて、決まった CA
  から証明書をもらった相手かどうかも確かめられます。

## 2. 仕組み: 鍵、署名、証明書、CA

### 2.1 部品を並べる

部品は 6 つです。2 列目は、実印と印鑑登録証明書に置き換えたものです。ほぼそのまま対応します。

| 部品 | たとえ | 何か | XRT-15 では |
|---|---|---|---|
| 秘密鍵 | 実印 | 鍵ペアの片方。持ち主の外へ出さない | SRV01 の `~/pki/client.key`、XR01 の `ems.key`、telegraf の鍵 |
| 公開鍵 | 実印の印影 | ペアのもう片方。配ってよい | 証明書の中に入っている |
| 署名 | 押印 | 秘密鍵でデータに付ける印。対の公開鍵で、データが変わっていないことと、その秘密鍵で付けたことを確かめられる | TLS のハンドシェイクのたびに付く(2.5 節) |
| 証明書 | 印鑑登録証明書 | 名前・公開鍵・有効期間などに、発行者(CA)が署名したもの | `~/pki/client.pem`(nms-gnmi)、コレクタの証明書(collector.nms.lab)、XR01 の `ems.pem` |
| CA 証明書 | 役所の公印の見本 | CA 自身の名前と公開鍵。確かめる側が持つ | `~/pki/ca.pem`(NMS-LAB-CA) |
| 申請(CSR) | 印鑑登録の申請書 | 証明書にしてほしい名前と公開鍵を、自分の秘密鍵で署名して CA へ出すもの | ラボを作ったときに作られた(3.1 節) |

### 2.2 鍵ペア: 片方で付けた署名は、対のもう片方で確かめる

鍵ペアは、秘密鍵と公開鍵の 2 つで 1 組です。秘密鍵で付けた署名は、対になる公開鍵で確かめられ、ほかの鍵では
確かめられません。公開鍵から秘密鍵を割り出すことは、実用上できません。だから公開鍵は配ってよく、秘密鍵は持ち主の
外へ出しません。

証明書の中の公開鍵と、手元の秘密鍵が 1 組かどうかは、SRV01 で確かめられます。秘密鍵から取り出した公開鍵と、証明書の
中の公開鍵を、ハッシュにして比べます。同じなら 1 組です。CA の公開鍵は、別のものです。

```console
$ openssl pkey -in ~/pki/client.key -pubout | sha256sum
233893b38b499c135cf3b94f1050c0436065357330f8c324b5de6fe6b7b82fae  -
$ openssl x509 -in ~/pki/client.pem -noout -pubkey | sha256sum
233893b38b499c135cf3b94f1050c0436065357330f8c324b5de6fe6b7b82fae  -
$ openssl x509 -in ~/pki/ca.pem -noout -pubkey | sha256sum
bb56e6830b0cfb0e2b4f490677688b6f8dfcf420818653a89b844bd412b904ee  -
```

TLS 1.3(コレクタへの接続はこれでした)では、接続を暗号化する鍵は、この鍵ペアではありません。両端がハンドシェイクの
たびにその場で鍵を作って合意し、接続が終われば捨てます。証明書の鍵の仕事は、署名して身元を示すことです。コレクタにつないだ
ときの表示では、`Server Temp Key` がその場で作った鍵、`Peer signature type` がコレクタの付けた署名の方式です。証明書の鍵は、
暗号化には加わりません。署名だけの係です。

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname collector.nms.lab </dev/null 2>&1 | grep -E "Peer signature|Server Temp Key|^New"
Peer signature type: RSA-PSS
Server Temp Key: X25519, 253 bits
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
```

### 2.3 証明書: 名前と公開鍵に、CA が署名したもの

証明書は、フィールドの決まった 1 枚の文書です。`openssl x509` でフィールドを読めます。

```console
$ openssl x509 -in ~/pki/client.pem -noout -subject -issuer -dates -ext subjectAltName,extendedKeyUsage,basicConstraints
subject=O = NMS Lab, CN = nms-gnmi
issuer=O = NMS Lab, CN = NMS-LAB-CA
notBefore=Nov 15 14:57:02 2026 GMT
notAfter=Nov 12 14:57:02 2036 GMT
X509v3 Extended Key Usage: 
    TLS Web Client Authentication
```

| フィールド | 何か | `client.pem` では |
|---|---|---|
| subject | この証明書の持ち主の名前。CN(common name)はその一部 | CN = nms-gnmi |
| issuer | 署名した CA の名前 | CN = NMS-LAB-CA |
| notBefore・notAfter | 有効期間 | 2026 年 11 月 15 日から 10 年 |
| subjectAltName(SAN) | 証明書が有効な名前と IP アドレスの一覧 | なし |
| extendedKeyUsage | 用途。サーバ用(TLS Web Server Authentication)かクライアント用か | クライアント用 |
| 公開鍵 | 持ち主の公開鍵 | 2.2 節のハッシュ |
| 署名 | 上のフィールドすべてに、issuer の秘密鍵で付けた署名 | NMS-LAB-CA の署名 |

コレクタの証明書は、サーバ用で、名前とアドレスを SAN に持ちます。つないでくる側は、名前でつないでもアドレスでつないでも
照らせます。クライアント証明書の `client.pem` には SAN がありません。XR01 の gRPC サーバは、相互 TLS で、SAN の無い
`client.pem` を受け付けます(次のページ)。

```console
$ openssl s_client -connect 10.0.50.10:57500 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName,extendedKeyUsage
subject=O = NMS Lab, CN = collector.nms.lab
issuer=O = NMS Lab, CN = NMS-LAB-CA
X509v3 Subject Alternative Name: 
    DNS:collector.nms.lab, IP Address:10.0.50.10
X509v3 Extended Key Usage: 
    TLS Web Server Authentication
```

名前は CN と SAN の 2 か所に書けます。名前を照らすのに SAN を見るクライアントがあり、gnmic もそうです。XR01 の証明書を
アドレスで確かめたときの失敗の文は、`doesn't contain any IP SANs` でした(次のページの 2.5 節)。ラボのコレクタの証明書は、
名前を CN と SAN の両方に持たせてあります。

### 2.4 CA: 署名を信じる起点

CA 証明書 `ca.pem` は、subject と issuer が同じです。CA が自分で署名しています(自己署名)。`CA:TRUE` は、これが
ほかの証明書に署名してよい CA 証明書だという印です。CA の身元は、CA が自分で請け合っています。

```console
$ openssl x509 -in ~/pki/ca.pem -noout -subject -issuer -dates -ext basicConstraints
subject=O = NMS Lab, CN = NMS-LAB-CA
issuer=O = NMS Lab, CN = NMS-LAB-CA
notBefore=Nov 15 14:57:01 2026 GMT
notAfter=Nov 12 14:57:01 2036 GMT
X509v3 Basic Constraints: critical
    CA:TRUE
```

`ca.pem` を確かめてくれる、さらに上の誰かはいません。信じてよい理由は、この 1 枚を正しい経路で受け取ったことだけです。
この 1 枚を**トラスト アンカー**と呼びます。確かめる側は、証明書の issuer の名前で手元の CA 証明書を探し、
その公開鍵で署名を確かめます。`openssl verify` が同じことをします。CA を渡さないと、OpenSSL の既定の証明書ストア(Ubuntu では公開の
CA の一覧)から探し、NMS-LAB-CA は見つかりません。ルート CA と中間 CA の 2 段になる形は、3.3 節で扱います。

```console
$ cd ~/pki
$ openssl verify -CAfile ca.pem client.pem
client.pem: OK
$ openssl verify client.pem
O = NMS Lab, CN = nms-gnmi
error 20 at 0 depth lookup: unable to get local issuer certificate
error client.pem: verification failed
```

名前は写せますが、署名は写せません。試しに、NMS-LAB-CA という同じ名前の CA を別に作り、nms-gnmi の証明書を発行しました。
subject と issuer の表示は、本物の `client.pem` と一字一句同じです。偽の CA で確かめると OK、本物の `ca.pem` で確かめると、
issuer の名前は合うのに署名が合わず、失敗します。openssl は、渡された CA が本物かどうかを知りません。渡された CA で
確かめるだけです。

```console
$ openssl x509 -in fake.pem -noout -subject -issuer
subject=O = NMS Lab, CN = nms-gnmi
issuer=O = NMS Lab, CN = NMS-LAB-CA
$ openssl verify -CAfile fake-ca.pem fake.pem
fake.pem: OK
$ openssl verify -CAfile ~/pki/ca.pem fake.pem
O = NMS Lab, CN = nms-gnmi
error 7 at 0 depth lookup: certificate signature failure
error fake.pem: verification failed
...
```

XR01 が gRPC を有効にしたときに自分で作る `ems.pem` も、自己署名です。名前は `ems.cisco.com` だけです。保証する CA がいないので、クライアントがこれを信じるには、この 1 枚そのものを CA のファイルとして
持つか、確かめずに進むかです。前者は、その 1 枚だけを信じることになります。相手が証明書を作り直せば、配り直しです。

:::try
同じ名前の偽の CA を自分で作り、本物の CA では通らないことを確かめます。作るのは `/tmp/fake-ca` の中だけで、最後に消します。

1. `mkdir /tmp/fake-ca && cd /tmp/fake-ca` で、作業の場所を作ります。
2. 偽の CA を作ります: `openssl req -x509 -newkey rsa:2048 -nodes -keyout fake-ca.key -out fake-ca.pem -days 30 -subj "/O=NMS Lab/CN=NMS-LAB-CA"`
3. nms-gnmi の申請を作り、偽の CA で署名します:
   `openssl req -newkey rsa:2048 -nodes -keyout fake.key -out fake.csr -subj "/O=NMS Lab/CN=nms-gnmi"`、
   続けて `openssl x509 -req -in fake.csr -CA fake-ca.pem -CAkey fake-ca.key -CAcreateserial -out fake.pem -days 30`
4. `openssl x509 -in fake.pem -noout -subject -issuer` と `openssl x509 -in ~/pki/client.pem -noout -subject -issuer` を比べます。
5. `openssl verify -CAfile fake-ca.pem fake.pem` と `openssl verify -CAfile ~/pki/ca.pem fake.pem` を比べます。
6. `cd ~ && rm -rf /tmp/fake-ca` で消します。

結果の例: 4 の 2 つの表示は同じでした(`subject=O = NMS Lab, CN = nms-gnmi`・`issuer=O = NMS Lab, CN = NMS-LAB-CA`)。5 は、
偽の CA では `fake.pem: OK`、本物の CA では `error 7 at 0 depth lookup: certificate signature failure` でした。
:::

### 2.5 確かめる 4 つ

TLS 1.3 のハンドシェイクでは、サーバが証明書(Certificate)を送り、続けて、それまでのやり取りの記録に自分の秘密鍵で
署名したもの(CertificateVerify)を送ります。受け取った側は、次の 4 つを確かめます。

1. **信じる CA の署名か**: issuer の CA 証明書を手元に持っていて、その公開鍵で署名が合うか。
2. **有効期間の内か**: 確かめる側の今の時刻が、notBefore と notAfter の間にあるか。
3. **つないだ相手の名前か**: つなごうとした名前かアドレスが、証明書(SAN)に載っているか。
4. **相手は秘密鍵を持っているか**: CertificateVerify の署名が、証明書の公開鍵で合うか。

1 が要るのは、誰でも証明書の形の文書を作れるからです(2.4 節の偽の CA)。3 が要るのは、本物の CA が出した本物の証明書でも、
別の相手のものなら意味がないからです。NMS-LAB-CA は、collector.nms.lab と nms-gnmi の 2 枚を出しています。名前を見なければ、
同じ CA から別の名前の証明書をもらった者と区別できません。4 が要るのは、証明書は配る物で、誰でも写しを持てるからです。写しを見せる
だけでは、秘密鍵を持っていることにはなりません。

2 は、確かめる側の時計で比べます。`openssl verify` の `-attime` で時計の代わりの時刻を渡すと、期間の外では断ります。
期間の後なら `expired`、前なら `not yet valid` です。

```console
$ openssl verify -attime $(date -d "2037-01-01" +%s) -CAfile ca.pem client.pem
O = NMS Lab, CN = NMS-LAB-CA
error 10 at 1 depth lookup: certificate has expired
O = NMS Lab, CN = nms-gnmi
error 10 at 0 depth lookup: certificate has expired
error client.pem: verification failed
$ openssl verify -attime $(date -d "2026-01-01" +%s) -CAfile ca.pem client.pem
O = NMS Lab, CN = NMS-LAB-CA
error 9 at 1 depth lookup: certificate is not yet valid
error client.pem: verification failed
```

`depth` は、確かめている証明書の段です。0 が相手の証明書、1 がそれに署名した CA 証明書です。CA 証明書にも有効期間が
あり、同じように確かめられます。

### 2.6 相互 TLS と、線ごとの役

ふつうの TLS では、証明書を見せるのはサーバだけです。相互 TLS では、サーバがクライアントにも証明書を求め
(CertificateRequest)、クライアントは自分の証明書と CertificateVerify を返します。サーバは、それを自分が信じる CA で
確かめます。

迷わないための決まりが 2 つあります。

- **TLS サーバとクライアントは、どちらがつないだかで決まる。** 待ち受ける側がサーバです。同じ XR01 でも、線によって
  役が入れ替わります。
- **CA 証明書を持つのは、確かめる側。** 持つのは、相手の証明書に署名した CA 証明書です。自分の証明書のために持つの
  ではありません。

この 2 つを XRT-15 の線に当てはめると、次のとおりです。

| 線(つなぐ側 → 待ち受ける側) | サーバが見せる証明書と、クライアントの確かめ方 | クライアントが見せる証明書と、サーバの確かめ方 |
|---|---|---|
| gNMI(M13-3): SRV01 の gnmic → XR01 | `ems.pem`(ems.cisco.com、自己署名)。`ems.pem` そのものと名前 `ems.cisco.com` で確かめるか、確かめない | 相互 TLS なら `client.pem`(nms-gnmi)。XR01 が NMS-LAB-CA で確かめる |
| テレメトリのダイヤルアウト(M13-4): XR01 → SRV01 の telegraf | collector.nms.lab(NMS-LAB-CA が発行)。NMS-LAB-CA と、期待する名前かアドレスで確かめる | 見せない |
| RESTCONF(M13-2): SRV01 のスクリプト → PE2 | PE2 の HTTPS の証明書。確かめない(`verify=False`) | 見せない |

M13-2 の RESTCONF も、中身は TLS でした。スクリプトが確かめを切っていたので、証明書を意識せずに済んでいました。

### 2.7 押さえどころ

- 秘密鍵は持ち主の外へ出さない。配るのは証明書と CA 証明書だけ。
- 証明書は、名前と公開鍵に CA が署名したもの。CA 証明書は自己署名で、トラスト アンカー。
- 証明書を受け取った側が 4 つを確かめる: 信じる CA の署名か、有効期間の内か、つないだ相手の名前か、相手は秘密鍵を持って
  いるか。
- TLS 1.3 では、暗号化の鍵はその場で作る。証明書の鍵は署名に使う。
- TLS サーバは待ち受ける側。CA 証明書を持つのは確かめる側。相互 TLS では、両側が確かめる側になる。
- 自己署名の証明書は、その 1 枚を持つ相手にだけ信じられる。証明書チェーンでは、サーバが中間 CA 証明書も送り、クライアントは
  手元のルート CA までたどる(3.3 節)。

## 3. 組む: 証明書を作り、確かめる

### 3.1 証明書ができるまで: 鍵、申請、署名

ラボの証明書は、ラボを作ったときに SRV01 の上で作られました。図は、コレクタの証明書ができて、確かめる側の手元に CA
証明書が届くまでの順です。図の番号にカーソルを置くと(スマホでは押すと)、その部分のコマンドが出ます。

:::walk
legend: "1 枚の証明書ができるまで。青い番号は下の設定例の行。秘密鍵はどれも、作った機械から動かない。"
rows:
  - panel: NMS-LAB-CA
    sub: 認証局
    items:
      - ref: 1
        head: "**鍵ペアを作り、自分に署名する** `openssl req -x509 …`"
        say: ["`ca.key`(秘密鍵)は CA の手元に残す", "`ca.pem`(subject = issuer = NMS-LAB-CA)は配る"]
  - panel: コレクタ
    sub: telegraf の持ち主
    items:
      - ref: 2
        head: "**鍵ペアと申請を作る** `openssl req -newkey … collector.nms.lab`"
        say: ["`collector.key` は手元に残す", "申請(CSR)= 名前と公開鍵。自分の秘密鍵で署名してある"]
  - {wire: "[[=CSR]] [[CN=collector.nms.lab  公開鍵]] _→ CA へ"}
  - panel: NMS-LAB-CA
    sub: 認証局
    items:
      - ref: 3
        head: "**フィールドを足して署名する** `openssl x509 -req … -CAkey ca.key …`"
        say: ["SAN に `DNS:collector.nms.lab` と `IP:10.0.50.10`、用途にサーバ用", "CA の秘密鍵で署名 → `collector.pem`"]
  - {wire: ["[[=証明書]] [[collector.nms.lab  公開鍵  有効期間]]", "[[!NMS-LAB-CA の署名]] _→ コレクタへ"]}
  - {node: XR01, say: ["確かめる側。受け取るのは `ca.pem` だけ", "~鍵は 1 本も受け取らない"]}
  - aside: "`ca.key` が CA の外へ出ると"
    say: ["~持った者は誰でも、NMS-LAB-CA の署名で、どの名前の証明書でも作れる(2.4 節の偽の CA が、本物の名前と署名でできる)"]
:::

:::config SRV01(ラボを作ったとき)— NMS の CA を作り、コレクタの証明書を発行する
openssl req -x509 -newkey rsa:2048 \     ## ① 鍵ペアを作り、その場で自分に署名する(-x509)
  -nodes -keyout ca.key \                ## CA の秘密鍵。-nodes= パスフレーズを掛けない
  -out ca.pem -days 3650 \               ## CA 証明書。10 年有効
  -subj "/O=NMS Lab/CN=NMS-LAB-CA"       ## CA の名前。subject と issuer の両方になる
openssl req -newkey rsa:2048 -nodes \    ## ② コレクタの鍵ペアと申請。-x509 が無いので申請になる
  -keyout collector.key \                ## 秘密鍵はコレクタの手元へ
  -out collector.csr \                   ## 申請は CA へ
  -subj "/O=NMS Lab/CN=collector.nms.lab"   ## 証明書にしてほしい名前
cat > collector.ext <<'EOF'              ## ③ CA が足すフィールドを、ファイルに書いておく
subjectAltName=DNS:collector.nms.lab,IP:10.0.50.10   ## ③ 照らされる名前とアドレス(SAN)
extendedKeyUsage=serverAuth              ## ③ 用途: サーバ用
EOF
openssl x509 -req -in collector.csr \    ## ③ 申請を証明書にする
  -CA ca.pem -CAkey ca.key \             ## 発行者は NMS-LAB-CA。署名には CA の秘密鍵を使う
  -CAcreateserial \                      ## シリアル番号のファイルも作る
  -out collector.pem -days 3650 \        ## できた証明書。10 年有効
  -extfile collector.ext                 ## 足すフィールド(SAN と用途)を読む
:::

クライアント証明書の `client.pem` も同じ手順で、名前が nms-gnmi、足すフィールドが用途(クライアント用)だけです。申請は申請者の
秘密鍵で署名してあり、CA はそれで、申請者がその公開鍵の秘密鍵を持っていることを確かめます。偽の CA で試したときの
`openssl req -in fake.csr -noout -subject -verify` は、`Certificate request self-signature verify OK` を返しました。

### 3.2 確かめる: openssl s_client

`openssl s_client` は、TLS クライアントとしてつなぎ、サーバの証明書を確かめて結果を表示します。図は、SRV01 の上の
s_client が、同じ SRV01 の上のコレクタ(telegraf)につなぐときの順です。XR01 のダイヤルアウトも、同じ順に確かめます。

:::walk
legend: "コレクタが証明書を見せ、つないだ側が確かめる。青い番号は下の設定例の行。"
rows:
  - {node: openssl, kind: host, say: ["SRV01 の `openssl s_client`(TLS クライアント)", "_持つもの: `ca.pem` と、期待する名前"]}
  - {wire: "[[TCP → 10.0.50.10:57500]] [[=ClientHello]]"}
  - {node: telegraf, kind: host, say: ["SRV01 のコレクタ(TLS サーバ)", "_持つもの: コレクタの証明書と、その秘密鍵"]}
  - {wire: "[[=Certificate]] [[collector.nms.lab]] [[!CertificateVerify  RSA-PSS]] _→ s_client へ"}
  - panel: openssl
    sub: s_client が確かめる
    items:
      - ref: 1
        head: "**信じる CA の署名か** `-CAfile ~/pki/ca.pem`"
        match:
          - ["CA のファイルを渡さない", false, "`21 (unable to verify the first certificate)`"]
          - ["ca.pem(NMS-LAB-CA)", true, "合う"]
      - say: ["**有効期間の内か**(SRV01 の時計で)", "_Nov 15 2026 〜 Nov 12 2036"]
      - ref: 2
        head: "**つないだ相手の名前か** `-verify_hostname collector.nms.lab`"
        match:
          - ["nms-gnmi(同じ CA の別の名前)", false, "`62 (hostname mismatch)`"]
          - ["collector.nms.lab(SAN の DNS)", true, "合う"]
      - say: ["**相手は秘密鍵を持っているか**", "_CertificateVerify の署名を、証明書の公開鍵で確かめる"]
      - ref: 3
        head: "**落ちたら止める** `-verify_return_error`"
        say: ["書かなければ、結果を表示したまま接続を続ける"]
      - say: ["~4 つとも通った → その場で合意した鍵(X25519)で暗号化", "~`Verification: OK`・`Verified peername: collector.nms.lab`"]
  - aside: "同じ名前の別の CA が署名していたら"
    say: ["~issuer の名前は合う → `ca.pem` の公開鍵で署名が合わない(openssl verify では `7 certificate signature failure`。2.4 節)"]
:::

:::config SRV01 — コレクタの証明書を、CA と名前で確かめる
openssl s_client -connect 10.0.50.10:57500 \   ## TLS クライアントとして、コレクタのポートへつなぐ
  -CAfile ~/pki/ca.pem \                        ## ① 信じる CA。コレクタの証明書の署名を、これで確かめる
  -verify_hostname collector.nms.lab \          ## ② 期待する名前。証明書の SAN と照らす
  -verify_return_error \                        ## ③ 確かめに落ちたら、ハンドシェイクを止める
  -brief </dev/null                             ## 結果だけを短く出し、すぐに閉じる
:::

通ったときの表示です。1 行目の `Can't use SSL_get_servername` は、ここでの確かめの結果には関わりません(同じ出力の
`Verification: OK`)。

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname collector.nms.lab -verify_return_error -brief </dev/null
Can't use SSL_get_servername
CONNECTION ESTABLISHED
Protocol version: TLSv1.3
Ciphersuite: TLS_AES_128_GCM_SHA256
Peer certificate: O = NMS Lab, CN = collector.nms.lab
Hash used: SHA256
Signature type: RSA-PSS
Verification: OK
Verified peername: collector.nms.lab
Server Temp Key: X25519, 253 bits
```

名前を nms-gnmi にすると、`-verify_return_error` があるので、ハンドシェイクが `certificate verify failed` で止まります。

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname nms-gnmi -verify_return_error </dev/null
Can't use SSL_get_servername
depth=0 O = NMS Lab, CN = collector.nms.lab
verify error:num=62:hostname mismatch
4067344802700000:error:0A000086:SSL routines:tls_post_process_server_certificate:certificate verify failed:../ssl/statem/statem_clnt.c:1889:
CONNECTED(00000003)
...
Verification error: hostname mismatch
```

`-verify_return_error` が無いと、s_client は `verify error:num=62:hostname mismatch` を表示したあとも接続を続け、最後に
`Verify return code: 62 (hostname mismatch)` と書きます。失敗は表示されます。表示されるだけです。gnmic や XR01 は、
確かめに落ちたら接続をやめます(次のページの 3.4 節のエラーの文)。

:::try
s_client で、4 つの確かめのうち 2 つを、わざと落とします。どれもコレクタに一度つないで閉じるだけで、コレクタの設定は変わりません。

1. CA を渡さずにつなぎます: `openssl s_client -connect 10.0.50.10:57500 </dev/null 2>&1 | grep -E "verify error|Verify return"`
2. 正しい CA と、違う名前でつなぎます: `openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname nms-gnmi </dev/null 2>&1 | grep -E "verify error|Verify return"`
3. 名前の代わりにアドレスで照らします: `openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_ip 10.0.50.10 </dev/null 2>&1 | grep "Verify return"`

結果の例: 1 は `verify error:num=20:unable to get local issuer certificate` と `Verify return code: 21 (unable to verify the first certificate)`、
2 は `verify error:num=62:hostname mismatch` と `Verify return code: 62 (hostname mismatch)`、3 は `Verify return code: 0 (ok)` でした。
1 と 2 も、接続そのものは最後まで進みました。
:::

### 3.3 自己署名の証明書と、中間 CA を挟んだ証明書チェーン

ここまでの CA は 1 段でした。NMS-LAB-CA が、コレクタの証明書にじかに署名しています。インターネットのサーバ証明書は、ふつう、
ルート CA がじかに署名せず、間に**中間 CA** を挟みます。たとえば www.cisco.com は、自分の証明書、それに署名した中間 CA
(HydrantID Server CA O1)の証明書、その上のルート CA(IdenTrust Commercial Root CA 1)の証明書の 3 枚を送ってきました。

サーバの証明書を信じてもらう形は、2 つあります。図を 2 枚に分けて並べます。値は、SRV01 の一時的な場所で作った試しの
証明書のものです。ルート CA は DEMO-ROOT-CA、中間 CA は DEMO-ISSUING-CA、サーバは www.demo.lab、自己署名のサーバは
self.demo.lab です。

| | 自己署名の証明書 | CA が署名した証明書 |
|---|---|---|
| サーバが送るもの | 自分の証明書だけ | 自分の証明書と中間 CA 証明書(ルート CA まで送るサーバもある) |
| クライアントが前もって持つもの | サーバの証明書そのもの | ルート CA 証明書(公開の CA なら OS の一覧= トラスト ストアに入っている) |
| 信じる起点 | サーバの証明書 | ルート CA 証明書 |
| サーバが証明書を作り直したら | クライアントへ配り直す | 配り直さなくてよい(同じルート CA の下で発行し直すなら) |

試しの証明書に書いてあるフィールドと、それぞれの役目は次のとおりです(`openssl x509 -noout -subject -issuer -ext …` で読んだもの。
「A ← B」は subject が A、issuer が B)。

| 証明書 | 書いてあること | 誰が持ち、どう使うか |
|---|---|---|
| ルート CA(`root.pem`) | DEMO-ROOT-CA ← DEMO-ROOT-CA(自己署名)。CA:TRUE | クライアントが前もって持つ。信じる起点。サーバは送らなくてよい |
| 中間 CA(`inter.pem`) | DEMO-ISSUING-CA ← DEMO-ROOT-CA。CA:TRUE、pathlen:0(この下に CA を置かない)、用途 Certificate Sign | サーバが送る。パスになるだけで、それだけでは信じない |
| サーバ(`server.pem`) | www.demo.lab ← DEMO-ISSUING-CA。SAN DNS:www.demo.lab | サーバが送る。名前を照らし、CertificateVerify の署名を確かめるのに使う |
| 自己署名のサーバ(`self.pem`) | self.demo.lab ← self.demo.lab。SAN DNS:self.demo.lab | サーバが送り、クライアントも同じ 1 枚を前もって持つ |

**自己署名の証明書。** 起点はサーバの証明書そのものなので、上へたどる段がありません。図の番号にカーソルを置くと(スマホでは
押すと)、その部分のコマンドが出ます。

:::walk
legend: "自己署名の証明書を確かめる。信じる起点は、サーバの証明書そのもの。青い番号は下の設定例の行。"
rows:
  - {node: サーバ, kind: host, say: ["self.demo.lab(試しの s_server)", "_持つもの: self.pem(自己署名)と self.key"]}
  - {wire: ["[[=Certificate]] [[subject self.demo.lab]] [[issuer self.demo.lab]]", "[[!CertificateVerify]] _→ クライアントへ"]}
  - panel: クライアント
    sub: openssl s_client
    items:
      - ref: 1
        head: "**手元の一覧に、この 1 枚があるか** `-CAfile self.pem`"
        say: ["issuer = subject なので、上はたどれない"]
        match:
          - ["一覧に無い(OS の一覧・別の CA だけ)", false, "`18 (self-signed certificate)`"]
          - ["self.pem そのものを持つ", true, "起点として信じる"]
      - say: ["**有効期間の内か**"]
      - ref: 2
        head: "**つないだ相手の名前か** `-verify_hostname self.demo.lab`"
        say: ["SAN の DNS:self.demo.lab と照らす"]
      - say: ["**相手は秘密鍵を持っているか**", "_CertificateVerify を、self.pem の公開鍵で確かめる"]
      - say: ["~すべて通った → `Verification: OK`"]
  - aside: "サーバが証明書を作り直したら"
    say: ["~手元の self.pem は古い 1 枚のまま → 新しい証明書は一覧に無い → 18。クライアントへ配り直す"]
:::

:::config クライアント — 自己署名の証明書を、その 1 枚で確かめる
openssl s_client -connect 127.0.0.1:44332 \  ## 自己署名の証明書を見せる、試しのサーバへつなぐ
  -CAfile self.pem \                          ## ① 信じる一覧= サーバの証明書そのもの
  -verify_hostname self.demo.lab \            ## ② 期待する名前
  -verify_return_error -brief </dev/null      ## 落ちたら止め、結果だけを出す
:::

```console
$ openssl s_client -connect 127.0.0.1:44332 -verify_hostname self.demo.lab -verify_return_error </dev/null
Can't use SSL_get_servername
depth=0 O = Demo, CN = self.demo.lab
verify error:num=18:self-signed certificate
...
Verification error: self-signed certificate
$ openssl s_client -connect 127.0.0.1:44332 -CAfile self.pem -verify_hostname self.demo.lab -verify_return_error -brief </dev/null
Can't use SSL_get_servername
CONNECTION ESTABLISHED
...
Verification: OK
Verified peername: self.demo.lab
```

`self.pem` を CA のファイルとして渡すと通り、渡さないと `18 (self-signed certificate)` で止まります。ファイルの中身は、
クライアントにとって「この 1 枚だけを信じる」という一覧です。XR01 の `ems.pem` を gnmic で確かめるときも、同じ形になります。

**CA が署名した証明書(中間 CA あり)。** クライアントは、送られてきた証明書の issuer の名前で上へたどってパスを組み、手元の
ルート CA を起点にして、上から下へ署名を 1 段ずつ確かめます。

:::walk
legend: "中間 CA を挟んだ証明書を確かめる。サーバは自分の証明書と中間 CA 証明書を送り、クライアントは手元のルート CA までたどる。青い番号は下の設定例の行。"
rows:
  - {node: サーバ, kind: host, say: ["www.demo.lab(試しの s_server)", "_持つもの: server.pem・server.key・中間 CA の inter.pem"]}
  - {wire: ["[[=Certificate 0]] [[www.demo.lab ← DEMO-ISSUING-CA]]", "[[=Certificate 1]] [[DEMO-ISSUING-CA ← DEMO-ROOT-CA]]", "[[!CertificateVerify]] _ルート CA は送らない → クライアントへ"]}
  - panel: クライアント
    sub: issuer の名前で上へたどってパスを組み、起点から下へ署名を確かめる
    items:
      - say: ["**パスを組む**(下から上へ、issuer の名前で)", "_www.demo.lab → DEMO-ISSUING-CA(送られてきた 1 番)→ DEMO-ROOT-CA(手元の一覧)"]
      - ref: 1
        head: "**起点: 手元のルート CA** `-CAfile root.pem`"
        say: ["自己署名なので、上はたどらない。信じる理由は、手元の一覧にあること"]
        match:
          - ["中間 CA までしか持たない", false, "`2 (unable to get issuer certificate)`"]
          - ["送られてきたが、手元に無い", false, "`19 (self-signed certificate in certificate chain)`"]
          - ["DEMO-ROOT-CA を持つ", true, "起点にする"]
      - ref: 2
        head: "**中間 CA 証明書** `-untrusted inter.pem`"
        say: ["送られてきた物。それだけでは信じず、パスに使う"]
        match:
          - ["送られてこない", false, "`20 (unable to get local issuer certificate)`"]
          - ["CA:TRUE を持たない証明書", false, "`79 (invalid CA certificate)`"]
          - ["CA:TRUE の DEMO-ISSUING-CA", true, "署名を、ルート CA の公開鍵で確かめる"]
      - say: ["**サーバの証明書**", "_署名を、中間 CA の公開鍵で確かめる"]
      - say: ["**どの段も、有効期間の内か**"]
      - ref: 3
        head: "**つないだ相手の名前か** `-verify_hostname www.demo.lab`"
        say: ["照らすのは depth 0(サーバの証明書)だけ"]
      - say: ["**相手は秘密鍵を持っているか**", "_CertificateVerify を、depth 0 の公開鍵で確かめる"]
      - say: ["~すべて通った → `Verification: OK`"]
:::

:::config サーバ — 自分の証明書に、中間 CA 証明書を添えて送る
openssl s_server -accept 127.0.0.1:44330 \  ## 試しの TLS サーバ
  -cert server.pem -key server.key \         ## 自分の証明書と秘密鍵
  -cert_chain inter.pem                      ## ② 中間 CA 証明書も一緒に送る
:::

:::config クライアント — 送られてきた証明書チェーンを、手元のルート CA までたどって確かめる
openssl s_client -connect 127.0.0.1:44330 \  ## 中間 CA も送るサーバへつなぐ
  -CAfile root.pem \                          ## ① 信じる起点= ルート CA(OS の一覧にあたる)
  -verify_hostname www.demo.lab \             ## ③ 期待する名前。depth 0 と照らす
  -verify_return_error -brief </dev/null      ## 落ちたら止め、結果だけを出す
openssl verify -show_chain \                  ## 同じことをファイルで行い、組めた証明書チェーンを表示する
  -CAfile root.pem \                          ## ① 信じる起点
  -untrusted inter.pem \                      ## ② パスに使うだけの証明書(TLS ではサーバが送ってくる)
  server.pem                                  ## 確かめる証明書
:::

```console
$ openssl verify -show_chain -CAfile root.pem -untrusted inter.pem server.pem
server.pem: OK
Chain:
depth=0: O = Demo, CN = www.demo.lab (untrusted)
depth=1: O = Demo, CN = DEMO-ISSUING-CA (untrusted)
depth=2: O = Demo, CN = DEMO-ROOT-CA
$ openssl s_client -connect 127.0.0.1:44330 -CAfile root.pem -verify_hostname www.demo.lab -verify_return_error </dev/null
Can't use SSL_get_servername
depth=2 O = Demo, CN = DEMO-ROOT-CA
verify return:1
depth=1 O = Demo, CN = DEMO-ISSUING-CA
verify return:1
depth=0 O = Demo, CN = www.demo.lab
verify return:1
...
Certificate chain
 0 s:O = Demo, CN = www.demo.lab
   i:O = Demo, CN = DEMO-ISSUING-CA
...
 1 s:O = Demo, CN = DEMO-ISSUING-CA
   i:O = Demo, CN = DEMO-ROOT-CA
...
```

`(untrusted)` の印は、その証明書が手元の一覧に無く、パスに使っただけという意味です。印の無い depth 2 だけが起点です。
s_client は depth 2 から順に表示します。起点から下へ、署名を 1 段ずつ確かめているためです。サーバが送ってきたのは 0 と 1 の
2 枚で、ルート CA は送っていません。

パスが組めないときと、途中の段が CA でないときは、次のように止まります。`notca.pem` は、ルート CA が CA:FALSE で発行した
ふつうの証明書で、`bad.pem` はそれで署名した www.demo.lab の証明書です。

```console
$ openssl verify -CAfile root.pem server.pem
O = Demo, CN = www.demo.lab
error 20 at 0 depth lookup: unable to get local issuer certificate
error server.pem: verification failed
$ openssl verify -CAfile inter.pem server.pem
O = Demo, CN = DEMO-ISSUING-CA
error 2 at 1 depth lookup: unable to get issuer certificate
error server.pem: verification failed
$ openssl verify -CAfile root.pem -untrusted notca.pem bad.pem
O = Demo, CN = NOT-A-CA
error 79 at 1 depth lookup: invalid CA certificate
error bad.pem: verification failed
```

1 つ目は中間 CA を渡していません。中間 CA を送らないサーバにつないだときも、s_client は同じ `20` で止まりました。2 つ目は
中間 CA だけを起点にしたもので、その上のルート CA を探して見つからず、止まります。OpenSSL は既定で、自己署名の起点まで
たどれない証明書チェーンを受け付けません。3 つ目は、CA:TRUE を持たない証明書が署名しているので止まります。

送られてきた中間 CA 証明書は、信じる理由になりません。パスになるだけです。信じる理由になるのは、クライアントが前もって
持っていたルート CA 証明書だけです。サーバがルート CA まで送ってきても同じで、手元に無ければ
`19 (self-signed certificate in certificate chain)` で止まります。送ってきた相手の言い分は、その相手の言い分でしかありません。

:::try
ルート CA・中間 CA・サーバの 3 段の証明書を作り、パスが組めるときと組めないときを比べます。作るのは `/tmp/chain-demo` の
中だけで、最後に消します。

1. `mkdir /tmp/chain-demo && cd /tmp/chain-demo`
2. ルート CA: `openssl req -x509 -newkey rsa:2048 -nodes -keyout root.key -out root.pem -days 3650 -subj "/O=Demo/CN=DEMO-ROOT-CA"`
3. 中間 CA: `openssl req -newkey rsa:2048 -nodes -keyout inter.key -out inter.csr -subj "/O=Demo/CN=DEMO-ISSUING-CA"`、
   `printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\n" > inter.ext`、
   `openssl x509 -req -in inter.csr -CA root.pem -CAkey root.key -CAcreateserial -out inter.pem -days 1825 -extfile inter.ext`
4. サーバ: `openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/O=Demo/CN=www.demo.lab"`、
   `printf "subjectAltName=DNS:www.demo.lab\nextendedKeyUsage=serverAuth\n" > server.ext`、
   `openssl x509 -req -in server.csr -CA inter.pem -CAkey inter.key -CAcreateserial -out server.pem -days 365 -extfile server.ext`
5. `openssl verify -show_chain -CAfile root.pem -untrusted inter.pem server.pem`、`openssl verify -CAfile root.pem server.pem`、
   `openssl verify -CAfile inter.pem server.pem` を比べます。
6. `cd ~ && rm -rf /tmp/chain-demo` で消します。

結果の例: 5 の 1 つ目は `server.pem: OK` と depth 0〜2 の証明書チェーン、2 つ目は `error 20 at 0 depth lookup: unable to get local issuer certificate`、
3 つ目は `error 2 at 1 depth lookup: unable to get issuer certificate` でした。
:::

### 3.4 XRT-15 の持ち物

各機器が持つものを、自分を示すもの(見せる側の持ち物)と、相手を確かめるもの(確かめる側の持ち物)に分けると、次のとおり
です。秘密鍵は、どれも作った機械から動きません。

| 機器 | 自分を示すもの | 相手を確かめるもの |
|---|---|---|
| SRV01(gnmic など、つなぐ側の道具) | `~/pki/client.pem` と `~/pki/client.key`(相互 TLS で見せる) | `~/pki/ca.pem`(NMS-LAB-CA が発行した相手を確かめる)。XR01 の `ems.pem` を確かめるなら、その 1 枚 |
| SRV01(telegraf) | コレクタの証明書と鍵(`/etc/telegraf/pki/`。ラボのアカウントのままでは読めない) | —(クライアント証明書を求めない) |
| XR01 | `ems.pem` と `ems.key`(gRPC サーバが見せる) | gNMI クライアントを確かめる CA のファイルと、ダイヤルアウトでコレクタを確かめる CA のファイル。置き場と置き方は次のページの 3.2 節 |

### 3.5 落とし穴

- **秘密鍵を配る**: CA へ出すのは申請、確かめる側へ配るのは CA 証明書です。どちらにも秘密鍵は要りません。`ca.key` を
  配れば、受け取った者が NMS-LAB-CA として、どの名前の証明書でも作れます。
- **確かめを切る**: `--skip-verify`・`verify=False`・`hostkey_verify=False` は、暗号化はしても相手を確かめません。1.1 節の
  困りごとがそのまま残ります。ラボで形を見るためだけに使います。
- **s_client の結果を読まない**: 確かめに落ちても接続は続きます。`Verify return code` を読むか、`-verify_return_error` を
  付けます。
- **名前とアドレス**: アドレスでつなぐクライアントは、SAN の IP アドレスを探します。名前しか持たない証明書(`ems.pem`)は、
  アドレスでは通りません。
- **時計**: 有効期間は、確かめる側の時計で比べます。時計の狂った機器は、正しい証明書を `not yet valid` や `expired` で
  断ります(2.5 節では、時計の代わりに `-attime` で確かめました)。
- **中間 CA の送り忘れ**: サーバが中間 CA 証明書を送らないと、クライアントはパスを組めず `20` で止まります。手元に中間 CA
  だけを持たせても、ルート CA までたどれないので `2` で止まります(3.3 節)。
- **同じ名前の CA**: CA の名前が合っていても、署名が合わなければ通りません。CA 証明書は、ファイルの名前でなく中身で
  配ります。

## 実践

課題 M13-3 と M13-4 は、次のページ(gNMI・テレメトリ)を読んでから取り組みます。どちらの課題も、このページの 2.6 節の
表の、gNMI とテレメトリのダイヤルアウトの行にあたります。

<p class="tolab"><a href="/_learn?id=XRT-15">ワークスペースでラボ XRT-15 を開く</a> — <a href="e2-m13-gnmi-telemetry.html">次のページ: 状態を流す</a></p>

:::note
このページの出力は、XRT-15 の SRV01(Ubuntu 24.04、OpenSSL 3.0.13)で取得しました。偽の CA と証明書、3.3 節の試しの証明書(ルート CA・中間 CA・
自己署名のサーバ)と試しのサーバは、確かめのために一時的な場所で作り、その場で消しました。www.cisco.com が送る証明書チェーンは、
2026 年 11 月 16 日に確認しました。XR01 の証明書(`ems.pem`)と gnmic のエラーの文、XR01 が SAN の無いクライアント証明書を
受け付けることは、次のページの測定によります。出典: RFC 5280(4.1 節 証明書の基本の欄、4.2.1.6 節 SAN、4.2.1.9 節
basicConstraints、4.2.1.12 節 extendedKeyUsage、6.1 節 証明書のパスの確かめ方と有効期間)、RFC 8446(TLS 1.3。4.2.8 節 key_share、
4.3.2 節 CertificateRequest、4.4.2 節 Certificate、4.4.3 節 CertificateVerify)、RFC 2986(PKCS #10。証明書の申請)、RFC 4251
(4.1 節 ホスト鍵)、OpenSSL 3.0 のマニュアル(openssl-req、openssl-x509、openssl-verify、openssl-s_client、openssl-s_server、openssl-verification-options)。いずれも 2026 年 11 月に
確認。
:::
