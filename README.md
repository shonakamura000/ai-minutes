# AI Minutes

日本語の会議を録音し、OpenAI Whisper APIで文字起こしを行い、その内容をGPTで要約するツールです。

## 使い方

1. `.env` ファイルを用意し、 `OPENAI_API_KEY` など必要な設定を行います。
2. 依存ライブラリをインストールします。
   ```bash
   pip install pyaudio requests python-dotenv
   ```
   もしくは `Pipfile` を利用している場合は `pipenv install` を実行してください。
3. 以下のコマンドで録音を開始します。
   ```bash
   python main.py --title 会議タイトル --segment 60
   ```
   `--segment` は録音を区切る秒数です。
4. 録音を終了するには `Ctrl+C` を押します。文字起こし結果と要約が `transcripts/` ディレクトリに保存されます。

## 出力先

`transcripts/` ディレクトリに議事録の JSON ファイルと要約テキストが保存されます。 `.gitignore` で除外設定されています。

## ライセンス

MIT License
