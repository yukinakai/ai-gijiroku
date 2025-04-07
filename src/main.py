#!/usr/bin/env python
import argparse
import gc
from src.workflow.recording_workflow import RecordingWorkflow

def main():
    """メインエントリーポイント"""
    # メモリリーク対策：スクリプト開始時にガベージコレクションを強制実行
    gc.collect()
    
    parser = argparse.ArgumentParser(description='オーディオ録音・文字起こしスクリプト')
    
    # サブコマンドの設定
    subparsers = parser.add_subparsers(dest='command', help='実行するコマンド')
    
    # 録音コマンド
    record_parser = subparsers.add_parser('record', help='音声を録音')
    record_parser.add_argument('-f', '--filename', type=str,
                       help='保存するファイル名（YYYYMMDD_[指定された名前].wav形式で保存されます）')
    record_parser.add_argument('-r', '--rate', type=int, default=48000,
                       help='サンプリングレート（Hz）')
    record_parser.add_argument('--no-transcribe', action='store_true',
                       help='文字起こしをスキップする')
    record_parser.add_argument('--realtime', action='store_true',
                       help='リアルタイム文字起こしを有効にする')
    
    # 文字起こしコマンド
    transcribe_parser = subparsers.add_parser('transcribe', help='音声ファイルを文字起こし')
    transcribe_parser.add_argument('-f', '--file', type=str,
                           help='文字起こしする音声ファイルのパス')
    transcribe_parser.add_argument('-d', '--directory', type=str,
                           help='文字起こしする音声ファイルのディレクトリ')
    transcribe_parser.add_argument('-o', '--output', type=str, default='src/transcripts',
                           help='出力先ディレクトリ（デフォルト: src/transcripts）')
    
    args = parser.parse_args()
    
    # メモリリーク対策：引数解析後にガベージコレクション
    gc.collect()
    
    if args.command == 'record':
        # 録音ワークフローの実行
        workflow = RecordingWorkflow()
        success = workflow.execute(
            filename=args.filename,
            sample_rate=args.rate,
            skip_transcribe=args.no_transcribe,
            realtime_transcribe=args.realtime
        )
    elif args.command == 'transcribe':
        # 文字起こしの実行
        from src.functions.transcribe import process_single_file, process_directory
        
        if args.file:
            try:
                output_file = process_single_file(args.file, args.output)
                print(f"文字起こし完了: {output_file}")
                success = True
            except Exception as e:
                print(f"エラー: {str(e)}")
                success = False
        else:
            try:
                directory = args.directory or 'src/recordings'
                process_directory(directory, args.output)
                success = True
            except Exception as e:
                print(f"エラー: {str(e)}")
                success = False
    else:
        parser.print_help()
        success = False
    
    # メモリリーク対策：ワークフロー終了後にガベージコレクション
    gc.collect()
    
    # 成功時は0、失敗時は1を返す
    return 0 if success else 1

if __name__ == "__main__":
    # メモリリーク対策：スクリプト終了時にもガベージコレクションを実行
    result = main()
    gc.collect()
    exit(result)