import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

class ChatManager:
    """チャット機能を管理するクラス"""
    
    def __init__(self):
        """初期化"""
        # 環境変数の読み込み
        load_dotenv()
        
        # OpenAI APIキーの確認
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。.envファイルを確認してください。")
        
        # OpenAIクライアントの初期化
        self.client = OpenAI()
        
        # システムプロンプトの設定
        self.system_prompt = """あなたは会議やインタビューの議事録を分析し、質問に答えるアシスタントです。
以下の点に注意して回答してください：
1. 文字起こしの内容に基づいて回答する
2. 不明な点は「文字起こしの内容からは確認できません」と明確に伝える
3. 回答は簡潔かつ正確に行う
4. 必要に応じて文字起こしの該当部分を引用する"""
    
    def get_transcript(self) -> str:
        """最新の文字起こしを取得"""
        transcript_path = Path("src/transcripts/20250407_test.txt")
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
                # 改行を2回にすることで、Markdownで改行として表示されるようにする
                return content.replace("\n", "\n\n")
        return "文字起こしファイルが見つかりません。"
    
    def get_response(self, user_input: str) -> str:
        """ユーザーの質問に対する応答を生成"""
        # 文字起こしの取得
        transcript = self.get_transcript()
        
        # メッセージの構築
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"以下の文字起こし内容に基づいて質問に答えてください：\n\n{transcript}\n\n質問：{user_input}"}
        ]
        
        try:
            # OpenAI APIを使用して応答を生成
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"エラーが発生しました：{str(e)}" 