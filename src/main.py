#!/usr/bin/env python
import argparse
import gc
from src.workflow.recording_workflow import RecordingWorkflow

def main():
    """メインエントリーポイント"""
    # メモリリーク対策：スクリプト開始時にガベージコレクションを強制実行
    gc.collect()
    
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-f', '--filename', type=str,
                       help='保存するファイル名（YYYYMMDD_[指定された名前].wav形式で保存されます）')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                       help='サンプリングレート（Hz）')
    parser.add_argument('--no-transcribe', action='store_true',
                       help='文字起こしをスキップする')
    
    args = parser.parse_args()
    
    # メモリリーク対策：引数解析後にガベージコレクション
    gc.collect()
    
    # ワークフローの実行
    workflow = RecordingWorkflow()
    success = workflow.execute(
        filename=args.filename,
        sample_rate=args.rate,
        skip_transcribe=args.no_transcribe
    )
    
    # メモリリーク対策：ワークフロー終了後にガベージコレクション
    del workflow
    gc.collect()
    
    # 成功時は0、失敗時は1を返す
    return 0 if success else 1

if __name__ == "__main__":
    # メモリリーク対策：スクリプト終了時にもガベージコレクションを実行
    result = main()
    gc.collect()
    exit(result)