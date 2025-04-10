#!/usr/bin/env python
import argparse
import gc
import platform
from src.workflow.recording_workflow import RecordingWorkflow
from src.functions.transcribe import process_single_file, process_directory
from src.functions.recorder import AudioRecorder

def main():
    """メインエントリーポイント"""
    # メモリリーク対策：スクリプト開始時にガベージコレクションを強制実行
    gc.collect()
    
    parser = argparse.ArgumentParser(description="AI会議録システム")
    
    # サブコマンドの設定
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    
    # 録音コマンド
    record_parser = subparsers.add_parser("record", help="音声を録音します")
    record_parser.add_argument("-f", "--filename", help="保存するファイル名")
    record_parser.add_argument("-r", "--rate", type=int, default=48000, help="サンプリングレート（デフォルト: 48000Hz）")
    record_parser.add_argument("--no-transcribe", action="store_true", help="録音のみ実行し、文字起こしをスキップします")
    record_parser.add_argument("--realtime", action="store_true", help="リアルタイム文字起こしを有効にします")
    record_parser.add_argument("--speaker-diarization", action="store_true", help="話者判定を使用したリアルタイム文字起こしを有効にします")
    
    # 文字起こしコマンド
    transcribe_parser = subparsers.add_parser("transcribe", help="録音済みの音声ファイルを文字起こしします")
    transcribe_parser.add_argument("-f", "--file", help="文字起こしする音声ファイルのパス")
    transcribe_parser.add_argument("-d", "--directory", help="文字起こしする音声ファイルのディレクトリ")
    transcribe_parser.add_argument("-o", "--output", default="src/transcripts", help="出力先ディレクトリ（デフォルト: transcripts）")
    
    args = parser.parse_args()
    
    # メモリリーク対策：引数解析後にガベージコレクション
    gc.collect()
    
    if args.command == "record":
        workflow = RecordingWorkflow()
        filename = args.filename
        
        if args.speaker_diarization:
            # 話者判定を使用したリアルタイム文字起こしを実行
            recorder = AudioRecorder(recordings_dir="recordings")
            recorder.record_realtime(
                filename=filename,
                sample_rate=args.rate,
                input_device_id=None
            )
        elif args.realtime:
            # 通常のリアルタイム文字起こしを実行
            result = workflow.run_with_realtime_transcription(
                filename=filename,
                sample_rate=args.rate,
                skip_transcribe=args.no_transcribe
            )
            print(f"ワークフロー実行結果: {'成功' if result else '失敗'}")
        else:
            # 通常の録音を実行（文字起こしは録音後に実行）
            result = workflow.run(
                filename=filename,
                sample_rate=args.rate,
                skip_transcribe=args.no_transcribe
            )
            print(f"ワークフロー実行結果: {'成功' if result else '失敗'}")
            
    elif args.command == "transcribe":
        if args.file:
            process_single_file(args.file, args.output)
        elif args.directory:
            process_directory(args.directory, args.output)
        else:
            process_directory(output_dir=args.output)
    else:
        parser.print_help()
    
    # メモリリーク対策：ワークフロー終了後にガベージコレクション
    gc.collect()
    
    # 成功時は0、失敗時は1を返す
    return 0 if args.command in ["record", "transcribe"] else 1

if __name__ == "__main__":
    # メモリリーク対策：スクリプト終了時にもガベージコレクションを実行
    result = main()
    gc.collect()
    exit(result)