# AI 議事録

音声を録音し、自動で文字起こしするツール

## セットアップ

1. 必要なパッケージをインストール

```bash
pip install -r requirements.txt
```

2. BlackHole のインストール

- [BlackHole](https://existential.audio/blackhole/)をインストール
- システム環境設定 > サウンドで BlackHole 2ch が表示されることを確認

3. 環境変数の設定
   `.env.example`をコピーして`.env`を作成し、OpenAI API キーを設定します：

```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 1. 音声の録音

```bash
python src/main.py record
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
python src/main.py record --no-transcribe
```

#### 手動文字起こし

以下のいずれかの方法で文字起こしを実行できます：

1. 単一の音声ファイルを文字起こし

```bash
python src/main.py transcribe -f path/to/audio.wav
```

2. ディレクトリ内のすべての音声ファイルを文字起こし

```bash
python src/main.py transcribe -d path/to/directory
```

3. デフォルトの`recordings`ディレクトリ内のファイルを文字起こし

```bash
python src/main.py transcribe
```

オプション:

- `-f, --file`: 文字起こしする音声ファイルのパス
- `-d, --directory`: 文字起こしする音声ファイルのディレクトリ
- `-o, --output`: 出力先ディレクトリ（デフォルト: transcripts）

仕様:

- 対応フォーマット: .wav, .mp3, .m4a
- OpenAI Whisper API を使用して高精度な文字起こし
- 書き起こされたテキストは指定された出力ディレクトリに保存
- フォーマット: `[HH:MM:SS] 発言内容`

## 開発

テストの実行:

```bash
python -m pytest tests/ -v
```
