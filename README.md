# AI 議事録

音声を録音し、自動で文字起こしするツール。会議やインタビューの議事録作成を効率化します。

## 特徴

- **簡単な録音機能**: システムオーディオをキャプチャして録音
- **高精度な文字起こし**: OpenAI Whisper API を使用
- **時間軸付き出力**: すべての発言に対するタイムスタンプ付き

## システム要件

- Python 3.9 以上
- OpenAI API キー
- macOS 環境 (BlackHole によるオーディオルーティング)
- 必要な Python パッケージ (requirements.txt に記載)

## セットアップ

### 1. 必要なパッケージをインストール

```bash
pip install -r requirements.txt
```

### 2. BlackHole のインストール

- [BlackHole](https://existential.audio/blackhole/)をインストール
- システム環境設定 > サウンドで BlackHole 2ch が表示されることを確認

### 3. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、OpenAI API キーを設定します：

```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 1. 音声の録音

```bash
python -m src.main record
```

録音の手順：

1. 利用可能なオーディオデバイス一覧が表示されます
2. 使用する入力デバイスの ID を入力
3. 録音の準備:
   - システム環境設定 > サウンド > 出力 で録音したいデバイスを選択
   - オーディオ MIDI 設定を開き、複数出力装置を作成
   - 複数出力装置に、録音したいデバイスと BlackHole 2ch の両方を追加
   - システム環境設定 > サウンド > 出力 で作成した複数出力装置を選択
4. Enter キーを押して録音開始
5. Ctrl+C で録音停止

オプション:

- `-f, --filename`: 保存するファイル名を指定
- `-r, --rate`: サンプリングレートを指定（デフォルト: 48000Hz）
- `--no-transcribe`: 録音のみを実行し、文字起こしをスキップ

録音したファイルは`recordings`ディレクトリに保存されます。
デフォルトでは、録音完了後に自動的に文字起こしが実行され、結果が`transcripts`ディレクトリに保存されます。

### 2. 文字起こし

#### 自動文字起こし

録音完了後、デフォルトで自動的に文字起こしが実行されます。
文字起こしをスキップする場合は、`--no-transcribe`オプションを使用してください：

```bash
python -m src.main --no-transcribe
```

#### 手動文字起こし

以下のいずれかの方法で文字起こしを実行できます：

1. 単一の音声ファイルを文字起こし

```bash
python -m src.functions.transcribe -f path/to/audio.wav
```

2. ディレクトリ内のすべての音声ファイルを文字起こし

```bash
python -m src.functions.transcribe -d path/to/directory
```

3. デフォルトの`recordings`ディレクトリ内のファイルを文字起こし

```bash
python -m src.functions.transcribe
```

オプション:

- `-f, --file`: 文字起こしする音声ファイルのパス
- `-d, --directory`: 文字起こしする音声ファイルのディレクトリ
- `-o, --output`: 出力先ディレクトリ（デフォルト: transcripts）

仕様:

- 対応フォーマット: .wav, .mp3, .m4a
- OpenAI の最新モデル「gpt-4o-transcribe」を使用した高精度な文字起こし
- 音声の長さに応じて自動的にチャンク分割処理を行い、大きいファイルも処理可能
- 書き起こされたテキストは指定された出力ディレクトリに保存
- フォーマット: `[HH:MM:SS] 発言内容`
- API コスト情報も出力ファイルに含まれます

### 使用しているモデルについて

このアプリケーションは OpenAI の「gpt-4o-transcribe」モデルを使用しています。このモデルは以下の特徴があります：

- 高精度な日本語文字起こし能力
- 応答形式は「json」または「text」のみをサポート（以前の「verbose_json」はサポート外）
- 正確なタイムスタンプ機能は現在このモデルでは利用できないため、音声チャンクごとにタイムスタンプを付与する簡易方式を採用しています

## プロジェクト構造

```
ai-gijiroku/
├── src/
│   ├── functions/       # 核となる機能
│   │   ├── recorder.py  # 録音機能
│   │   └── transcribe.py # 文字起こし機能
│   ├── workflow/        # ワークフロー管理
│   │   └── recording_workflow.py # 録音ワークフロー
│   └── main.py          # メインエントリーポイント
├── recordings/          # 録音ファイル保存ディレクトリ
├── transcripts/         # 文字起こし結果保存ディレクトリ
└── tests/               # テストコード
```

## 開発

テストの実行:

```bash
python -m pytest tests/ -v
```

## トラブルシューティング

### 録音でエラーが発生する場合

- BlackHole が正しくインストールされていることを確認
- オーディオ MIDI 設定で複数出力装置が正しく設定されていることを確認
- 使用する入力デバイスに適切なアクセス権があることを確認

### 文字起こしでエラーが発生する場合

- OpenAI API キーが正しく設定されていることを確認
- インターネット接続が安定していることを確認
- サポートされている音声フォーマット(.wav, .mp3, .m4a)であることを確認

## ライセンス

Copyright (c) 2024 Yukinakai
