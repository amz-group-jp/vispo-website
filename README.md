# VISPO Website

VISPOフィットネスクラブのリデザインプレビュー。

HTML・CSS・JavaScriptによる静的サイトです。通常ページ・フォーム・案内23ページと保存記事等137ページ、合計160ページを収録しています。

## ローカルで確認

```sh
python3 -m http.server 8773 --bind 127.0.0.1
```

ブラウザで `http://localhost:8773/` を開きます。ソースの閲覧は追加パッケージ不要です。公開前には下記のビルド・検証を実行します。

## 内容について

写真・施設情報・料金は保存済みVISPOサイトをもとに構成しています。現在の適用料金・営業条件はクラブへご確認ください。体験・入会予約・お問い合わせは新サイト内で入力・確認し、既存の独立したフォームメーラーに直接送信します。旧サイトのHTMLやサーバーには依存しません。送信後の結果画面はフォームメーラー側に表示されます。電話リンクと地図リンクは実際の連絡先へ移動します。

## 公開先

- GitHub: https://github.com/amz-group-jp/vispo-website
- Cloudflare Pages: https://vispo-website.pages.dev/

更新をコミット・pushしたあと、Cloudflareにログイン済みのWrangler環境で `./deploy.sh` を実行すると、検証済みdistを確認用サイトへ反映します。既定は全ページnoindexのpreviewです。

GitHub Actionsでビルド・リンク・送信を遮断したフォーム検証を実行します。自動公開用ワークフローも用意していますが、現在はCLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_IDのSecretsが未登録のため公開しません。設定する場合は対象アカウントのCloudflare Pages Editに限定したAPIトークンを使い、ローカルの広権限OAuthトークンを転用しないでください。自動公開はsite-config.jsonのmodeがpreviewの間だけです。

本番切替時のみ、手順書のメール・DNS・受付の条件を満たした上でsite-config.jsonのmodeをproductionにし、`./deploy.sh --production` を使います。本番用設定では通常ページをindex、受付フォーム・保存記事・結果案内はnoindexにします。DNS操作はこのスクリプトに含みません。

公開対象はHTML/CSS/JS・許可したassets・favicon・robots/sitemap・ヘッダー・旧URL転送だけです。docs/tests/scripts/設定/レポート/Git情報はサイトへ配信しません。

## 受付フォーム（2026-10-08）

- 入会予約: web.html
- 体験申込: trial.html
- お問い合わせ: inquiry.html
- 会則: terms.html / 個人情報保護方針: privacy.html

入力・確認は新サイト内。既存フォームメーラーへmultipart POSTで送信し、同サービスの結果画面へ進みます。旧サイトへは遷移しません。独自の受付完了表示は行いません。フォームメーラーの契約・フォームと、通知受信用メールは引き続き必要です。

フォームキー/フィールド名/選択肢値を既存設定と照合。体験の時刻値0は、現行フォームメーラーに合わせ10:15と表示しています（旧サイトの10:00表示を修正）。2026/2027年の祝日設定を引継ぎ、それ以降は16時までの希望時間に限定します。JSなしでは10時台から16時までの選択肢と標準HTML送信になります。日時は希望であり、店舗返信後に予約確定です。

旧サイト閉鎖前の運用確認:
- フォームメーラーの通知先メール、完了画面の戻り先・リダイレクト先・通知メール内リンクを新サイトに変更する必要がないか管理画面で確認。
- 実送信および店舗のメール到達確認は未実施。
- 旧ドメインのメールを利用し続ける場合、メール契約とDNS/MXを保持。
- 体験料金と土日祝の受付時間、既存会則の料金記述に不一致あり。店舗確定後に更新。

個人情報をURLやlocalStorage等に保存しません。バリデーション・確認画面・送信ペイロードは、外部POSTを遮断したブラウザテストで確認済みです。実受付・メール到達を保証する試験ではありません。

フォーム検証: Playwrightが使える環境で、ローカルサーバー起動後に `VISPO_BASE=http://localhost:8774/ node tests/forms.cjs`。テストは送信先へのPOSTをすべて横取りし、外部へ実送信しません。

## 切替準備と確認

- docs/production-cutover.txt: DNS・メール維持・本番切替・ロールバック手順
- docs/legacy-url-map.csv: 保存された旧HTML257件の対応台帳
- docs/archive-report.json: 過去記事と素材の保全記録
- _redirects: 旧URLの301転送設定（同義URLを含む）
- reports/: ローカル検証結果。Gitおよび公開対象から除外

```sh
python3 scripts/test_build.py
python3 scripts/build.py
python3 scripts/verify.py
python3 scripts/build.py --mode production
python3 scripts/verify.py --mode production
python3 scripts/build.py
```

ブラウザ表示検証はPlaywright環境で `VISPO_BASE=http://localhost:8775/ node tests/site.cjs`。distを静的サーバーで配信して実行してください。

旧サイトの画像・PDFをassetsへ同梱しました。旧HTMLのsample-pageはWordPressの例文のため移行対象外とし404にします。元保存に欠けていた原寸画像2点も旧サイトから回収し、すべて新サイト側へ同梱しました。

公開HTTP検証（送信なし）: `node tests/release.cjs`。702件の旧URL301、404、非公開ファイルの非配信、canonical/noindexを確認します。通常CIでは実行せず、公開後に実施します。
