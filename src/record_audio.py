#!/usr/bin/env python
import argparse
from src.workflow.recording_workflow import RecordingWorkflow

def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-f', '--filename', type=str,
                       help='保存するファイル名（YYYYMMDD_[指定された名前].wav形式で保存されます）')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                       help='サンプリングレート（Hz）')
    parser.add_argument('--no-transcribe', action='store_true',
                       help='文字起こしをスキップする')
    
    args = parser.parse_args()
    
    # ワークフローの実行
    workflow = RecordingWorkflow()
    success = workflow.execute(
        filename=args.filename,
        sample_rate=args.rate,
        skip_transcribe=args.no_transcribe
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())