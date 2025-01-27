# AI議事録作成ツール - オーディオ録音機能

このツールは、macOS上でマイク入力とシステムオーディオ（スピーカー出力）を同時に録音するための機能を提供します。

## 前提条件

- macOS
- Python 3.11.0b3（pyenvで管理）
- Blackhole 2ch（仮想オーディオドライバ）

## セットアップ

1. 必要なツールのインストール（まだの場合）

```bash
# Homebrewを使用してBlackholeをインストール
brew install blackhole-2ch
```

2. Python環境のセットアップ

```bash
# pyenvで仮想環境を作成
pyenv virtualenv 3.11.0b3 ai-gijiroku # 3.11.0b3が最新

# プロジェクトディレクトリに移動
cd /path/to/ai-gijiroku

# 仮想環境を有効化
pyenv local ai-gijiroku

# シェルを再起動して仮想環境を反映
exec $SHELL -l

# 必要なパッケージをインストール
pip install -r requirements.txt
```

3. スクリプトの実行権限を設定

```bash
chmod +x record_audio.py
```

## システム設定

1. システム環境設定を開く
2. サウンド設定に移動
3. 出力タブで「BlackHole 2ch」を選択
   - これにより、システムの音声出力がBlackholeにルーティングされます

## 使用方法

### 基本的な使用方法

```bash
# 仮想環境が有効になっていることを確認（プロンプトに(ai-gijiroku)が表示されているか確認）
# 表示されていない場合は以下のコマンドを実行
pyenv activate ai-gijiroku

# 録音を開始
./record_audio.py

# エラーが出る場合は下記でも試す
pathto-pyenv/.pyenv/versions/ai-gijiroku/bin/python record_audio.py
```

### 利用可能なオプション

- `-l, --list`: 利用可能なオーディオデバイスを表示
- `-f, --filename`: 保存するファイル名を指定
- `-r, --rate`: サンプリングレート（Hz）を指定

### 使用例

```bash
# デバイス一覧を表示
./record_audio.py -l

# 特定のファイル名で録音
./record_audio.py -f my_recording.wav

# サンプリングレートを48kHzに設定して録音
./record_audio.py -r 48000
```

### 録音ファイルの保存場所

録音したファイルは、プロジェクトディレクトリ内の`recordings`フォルダに保存されます：

- ファイル名を指定しない場合：`recordings/recording_YYYYMMDD_HHMMSS.wav`
- ファイル名を指定した場合：`recordings/指定したファイル名`

録音開始時に保存先のパスが表示され、録音完了時にも確認メッセージが表示されます。

### 録音の停止

- 録音中はCtrl+Cを押すことで録音を停止できます
- 録音中は経過時間が表示されます
- 録音を停止すると、自動的にファイルが保存されます

## 注意事項

- 録音開始前に、システムの音声出力が「BlackHole 2ch」に設定されていることを確認してください
- 録音終了後は、必要に応じてシステムの音声出力を元の設定に戻してください
- 録音ファイルは自動的にWAV形式で保存されます
- スクリプトを実行する前に、必ず仮想環境が有効になっていることを確認してください

## トラブルシューティング

1. `ModuleNotFoundError: No module named 'sounddevice'`などのエラーが表示される場合
   - 仮想環境が有効になっているか確認（プロンプトに`(ai-gijiroku)`が表示されているか）
   - 仮想環境を有効化: `pyenv activate ai-gijiroku`
   - パッケージを再インストール: `pip install -r requirements.txt`

2. BlackHoleデバイスが見つからない場合
   - システム環境設定でBlackholeが正しくインストールされているか確認
   - 必要に応じてBlackholeを再インストール

3. 音声が録音されない場合
   - システムの音声出力が「BlackHole 2ch」に設定されているか確認
   - マイクの権限が正しく設定されているか確認

4. その他のエラーが発生する場合
   - 仮想環境が有効になっているか確認
   - 必要なパッケージが正しくインストールされているか確認
   - シェルを再起動して仮想環境を再読み込み: `exec $SHELL -l`