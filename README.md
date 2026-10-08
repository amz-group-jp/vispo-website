# VISPO Website

VISPOフィットネスクラブのリデザインプレビュー。

HTML・CSS・JavaScriptによる静的サイトです。トップ、施設、プログラム、料金、アクセス、1日体験、入会案内の7ページを収録しています。

## ローカルで確認

```sh
python3 -m http.server 8773 --bind 127.0.0.1
```

ブラウザで `http://localhost:8773/` を開きます。ビルドや追加パッケージは不要です。

## 内容について

写真・施設情報・料金は保存済みVISPOサイトをもとに構成しています。現在の適用料金・営業条件はクラブへご確認ください。予約・入会の送信機能はありません。電話リンクと地図リンクは実際の連絡先へ移動します。

## 公開先

- GitHub: https://github.com/amz-group-jp/vispo-website
- Cloudflare Pages: https://vispo-website.pages.dev/

更新をコミット・pushしたあと、Cloudflareにログイン済みのWrangler環境で `./deploy.sh` を実行すると本番サイトへ反映できます。GitHubへのpushだけでは自動デプロイされません。公開対象はHTML・CSS・JavaScript・画像・HTTPヘッダー設定のみです。
