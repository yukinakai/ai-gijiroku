# AI議事録作成ツール

Google MeetやZoomでのWeb会議の音声を自動で文字起こしするデスクトップアプリケーションです。OpenAI WhisperAPIを使用して高精度な文字起こしを実現します。

## 必要要件

- Node.js (v20.0.0以上)
- OpenAI API Key
- macOSまたはWindows

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/ai-gijiroku.git
cd ai-gijiroku
```

2. 依存パッケージをインストール:
```bash
npm install
```

3. 環境変数の設定:
```bash
cp .env.example .env
```
`.env`ファイルを編集し、OpenAI APIキーを設定してください:
```
OPENAI_API_KEY=your_api_key_here
```

## 開発

開発モードで実行:
```bash
npm run dev
```

## ビルド

アプリケーションをビルド:
```bash
npm run build
```

実行可能ファイルを作成:
```bash
npm run dist
```

## テスト

テストの実行:
```bash
npm test
```

## 機能

- Web会議の音声をリアルタイムでキャプチャ
- OpenAI Whisper APIを使用した高精度な文字起こし
- タイムスタンプ付きの文字起こし結果
- 開発モードでのDevTools対応

## ライセンス

ISC

## 注意事項

- 音声のキャプチャには、システムの音声出力デバイスへのアクセス権限が必要です。
- OpenAI APIの使用には、有効なAPIキーと十分なクレジットが必要です。
- 文字起こしの精度は、音声の品質や環境ノイズに依存します。