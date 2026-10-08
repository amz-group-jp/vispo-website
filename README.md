# VISPO Website

VISPOフィットネスクラブのリデザインプレビュー。

HTML・CSS・JavaScriptによる静的サイトです。トップ、施設、プログラム、料金、アクセス、1日体験、入会案内、予約・お問い合わせの8ページを収録しています。

## ローカルで確認

```sh
python3 -m http.server 8773 --bind 127.0.0.1
```

ブラウザで `http://localhost:8773/` を開きます。ビルドや追加パッケージは不要です。

## 内容について

写真・施設情報・料金は保存済みVISPOサイトをもとに構成しています。現在の適用料金・営業条件はクラブへご確認ください。体験・入会予約・お問い合わせは公式サイトの既存受付ページに接続しています。このサイト内では個人情報を入力・送信しません。電話リンクと地図リンクは実際の連絡先へ移動します。

## 公開先

- GitHub: https://github.com/amz-group-jp/vispo-website
- Cloudflare Pages: https://vispo-website.pages.dev/

更新をコミット・pushしたあと、Cloudflareにログイン済みのWrangler環境で `./deploy.sh` を実行すると本番サイトへ反映できます。GitHubへのpushだけでは自動デプロイされません。公開対象はHTML・CSS・JavaScript・画像・HTTPヘッダー設定のみです。

## 受付導線（2026-10-08）

- 体験: https://vispo-fit.com/experience （返信メールで予約確定）
- 入会予約: https://vispo-fit.com/web （仮登録後、来店して正式手続き）
- 問い合わせ: https://vispo-fit.com/contact
- 当日の体験・急ぎの相談: 029-839-2339

公式ページへのGETとフォームの存在を確認。実際の申し込み送信・メール到達テストは実施していません。体験料金（1,000円/2,200円）および土日祝受付時間に公式ページ内の不一致があるため、体験案内では店舗確認を案内しています。確定情報を受領後に更新してください。
