# ZDR Router Video for ComfyUI

[ZDR Router](https://router.hello.ai/) の動画生成 API（`/v1/videos`）を ComfyUI から使うためのカスタムノードと、サンプルワークフローです。

- モデルは MiniMax H3（`minimax-h3`）を使います
- 動画の生成は ZDR Router 側で行うので、手元に GPU は要りません
- 生成した動画の最後のフレームから続きを作り、元の動画の後ろにつなげられます（Extend）。何本かつなげば 30 秒程度の動画も作れます

## 目次

- [用意するもの](#用意するもの)
- [インストール](#インストール)
- [API キーの設定](#api-キーの設定)
- [サンプルワークフロー](#サンプルワークフロー)
- [ノードの使い方](#ノードの使い方)
- [料金と生成時間](#料金と生成時間)
- [困ったとき](#困ったとき)

## 用意するもの

- ComfyUI（最新版を推奨）。動画の入出力に ComfyUI 本体の `comfy_api` を使うため、古い版では動かないことがあります
- ZDR Router のアカウントと API キー（`hello_` で始まる文字列）
  1. https://router.hello.ai/console/ にログインします
  2. クレジットをチャージします。動画生成はトライアルキーでは使えません
  3. API キーを発行します

## インストール

ComfyUI の `custom_nodes` フォルダで、このリポジトリを clone します。追加の Python パッケージは要りません（ComfyUI に入っている `av` と `Pillow` を使います）。

以下のパスは Comfy Desktop で、インストール名を既定の「ComfyUI」のまま作った場合のものです。インストール名を変えた場合は、パスの 1 つ目の `ComfyUI` をその名前に読み替えてください。

### macOS（Comfy Desktop）

ターミナルで次を実行します。

```bash
cd ~/ComfyUI-Installs/ComfyUI/ComfyUI/custom_nodes
git clone https://github.com/hellocloud-public/ZDR-Router-example.git
```

### Windows（Comfy Desktop）

[Git for Windows](https://git-scm.com/download/win) を入れたうえで、PowerShell で次を実行します。

```powershell
cd "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes"
git clone https://github.com/hellocloud-public/ZDR-Router-example.git
```

古いバージョンの Comfy Desktop で作ったインストールは、`%USERPROFILE%\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes` にあることがあります。

### git を使わない場合

GitHub の「Code」→「Download ZIP」でダウンロードして展開し、できたフォルダ（`ZDR-Router-example-main`）ごと上の `custom_nodes` フォルダに入れます。この方法では、更新するたびに入れ直す必要があります。

### 確認

Comfy Desktop を再起動します。ノード一覧の「ZDR Router」カテゴリに「ZDR Router Video (minimax-h3)」が出ていれば完了です。

### 更新

clone したフォルダで `git pull` し、Comfy Desktop を再起動します。

```bash
cd ~/ComfyUI-Installs/ComfyUI/ComfyUI/custom_nodes/ZDR-Router-example
git pull
```

Windows では `cd "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes\ZDR-Router-example"` に読み替えてください。

## API キーの設定

1. ZDR Router Video ノードを含むワークフローを開くと、API キーの入力欄が出ます
2. コンソールで発行した API キーを貼り付けて OK を押します
3. 「API キーを保存しました」と出れば完了です。次回からは聞かれません

キーは `custom_nodes/ZDR-Router-example/comfy/api_key.txt` に保存されます。ノードの入力欄には置かないので、ワークフローの JSON や生成した mp4 のメタデータにキーは入りません。`api_key.txt` は `.gitignore` に入れてあるので、git にコミットされることもありません。

キーを変えたいときは、`api_key.txt` を削除してからワークフローを開き直すと、もう一度入力欄が出ます。直接書き換えても構いません。

## サンプルワークフロー

`custom_nodes/ZDR-Router-example/comfy/example_workflows/` に入っています。JSON ファイルを ComfyUI の画面にドラッグ＆ドロップすると開けます。

| ファイル | 内容 | 長さ |
| --- | --- | --- |
| `zdr-router-gpu-to-datacenter-30s.json` | GPU の製造からデータセンターへの搬入までを 4 本の Extend でつなげた 30 秒の動画 | 8 + 8 + 7 + 7 秒 |

開いたら「実行」（Queue / Run）を押します。完成した動画は `ComfyUI/output/video/` に mp4 で保存されます。

## ノードの使い方

### 入力

| 名前 | 内容 |
| --- | --- |
| `prompt` | 作りたい動画の説明。英語のほうが意図どおりになりやすいです |
| `seconds` | 動画の長さ（5〜15 秒、1 秒刻み） |
| `aspect_ratio` | 縦横比。`16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9` |
| `extend_from`（任意） | 続きを作る元の動画。別の ZDR Router Video ノードの出力をつなぎます |

出力は `VIDEO` です。「Save Video」ノードにつなぐと保存できます。

出力サイズは縦横比で決まります（例: `16:9` は 2688×1536）。

### Extend（続きを作る）

`extend_from` に動画をつなぐと、その動画の最後のフレームを最初のフレームにして続きを生成し、元の動画の後ろに連結したものを出力します。ノードを鎖のようにつなげば、何本でも延ばせます。

- `aspect_ratio` は元の動画と同じにしてください。違うと、つないだときに画面の大きさが揃いません
- 最初のフレームの画像は自動で縮小・JPEG 化して送ります。ZDR Router は参照画像を合計 750KB までしか受け付けないためです。画質への影響はありません
- プロンプトの冒頭に「Continue seamlessly from the opening frame.」のように書き、毎回同じ画風の指定を入れると、つなぎ目が自然になりやすいです（`zdr-router-gpu-to-datacenter-30s.json` を参考にしてください）
- プロンプト内で `[0s-3s]` のように時間ごとの場面を書くと、展開を指定しやすくなります

## 料金と生成時間

- 料金は動画の秒数で決まります。Extend で続きを作るときは、最初のフレームの画像 1 枚分の料金が加わります。単価は https://router.hello.ai/pricing を見てください
- 送信時に見積り額をクレジットから確保し、完了時に実際の額で精算します。生成に失敗したジョブには料金がかかりません
- 生成には 5 秒の動画で 10〜13 分ほどかかります。混雑時はさらに時間がかかります。Extend は前の動画ができてから次を送るので、4 本つなぐと 1 時間程度かかります
- ComfyUI 側で実行を中断しても、すでに送ったジョブは ZDR Router 側で生成が続き、料金がかかります
- 利用額はコンソールの利用履歴で確認できます

## 困ったとき

エラーはノードの赤枠と ComfyUI のコンソールに出ます。

| 表示 | 原因と対処 |
| --- | --- |
| 「ZDR Router」カテゴリが出ない | clone した場所が、使っているインストールの `custom_nodes` か確認してください（[インストール](#インストール)のパス）。合っていれば、Comfy Desktop のログで `ZDR-Router-example` の行に `IMPORT FAILED` が出ていないか確認してください |
| `FileNotFoundError: ... api_key.txt` | API キーが設定されていません。ワークフローを開き直して入力欄からキーを入れてください |
| `ZDR Router 401: ...` | API キーが間違っているか、無効になっています。`api_key.txt` を削除して入れ直してください |
| `ZDR Router 402: ...` | クレジットが足りません。コンソールでチャージしてください |
| `ZDR Router 400: ...` | 入力が受け付けられませんでした。メッセージの内容を確認してください |
| `ZDR Router の動画ジョブ ... が failed で終わりました` | 生成に失敗しました。料金はかかっていません。プロンプトを変えて試してください |
| API キーの入力欄が出ない | ComfyUI を再起動し、ブラウザを再読み込みしてください。それでも出ないときは、ブラウザの開発者ツールのコンソールにエラーが出ていないか確認してください |

通信が一時的に切れたり、サーバーが一時的にエラーを返したりした場合、ノードは 10 秒おきに再試行し続けます。送信済みのジョブはすでに料金が確保されているので、途中で諦めないようにしています。

## お問い合わせ

- サポート: support@cloud.hello.ai（10:00-19:00）
- API のドキュメント: https://router.hello.ai/docs/videos/

運営: 株式会社HelloCloud
