# AI議事録

音声ファイルを自動で文字起こしするツール

## セットアップ

1. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

2. 環境変数の設定
`.env.example`をコピーして`.env`を作成し、OpenAI APIキーを設定します：
```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

1. 音声ファイルを`recordings`ディレクトリに配置
   - 対応フォーマット: .wav, .mp3, .m4a

2. 文字起こしを実行
```bash
python transcribe.py
```

3. 結果の確認
- 書き起こされたテキストは`transcripts`ディレクトリに保存されます
- フォーマット: `[HH:MM:SS] 発言内容`

## 開発

テストの実行:
```bash
python -m pytest test_transcribe.py -v