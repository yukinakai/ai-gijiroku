#!/usr/bin/env python
import streamlit as st
import time
import os
from pathlib import Path
from src.functions.chat import ChatManager

# ページ設定
st.set_page_config(
    page_title="AI議事録アシスタント",
    page_icon="🎙️",
    layout="wide"
)

# セッション状態の初期化
if "chat_manager" not in st.session_state:
    st.session_state.chat_manager = ChatManager()
if "messages" not in st.session_state:
    st.session_state.messages = []

def read_transcript():
    """文字起こしファイルを読み込む"""
    transcript_path = Path("src/transcripts/20250407_test.txt")
    if transcript_path.exists():
        with open(transcript_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 改行を2回にすることで、Markdownで改行として表示されるようにする
            return content.replace("\n", "\n\n")
    return "文字起こしファイルが見つかりません。"

# 2カラムレイアウトの作成
chat_col, transcript_col = st.columns([1, 1])

# 左パネル: チャットUI
with chat_col:
    st.title("AI議事録アシスタント")
    
    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # ユーザー入力
    if prompt := st.chat_input("質問を入力してください"):
        # ユーザーメッセージの表示
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # AI応答の生成と表示
        with st.chat_message("assistant"):
            response = st.session_state.chat_manager.get_response(prompt)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# 右パネル: 文字起こし表示
with transcript_col:
    st.title("リアルタイム文字起こし")
    
    # 文字起こし内容を表示するためのコンテナ
    transcript_container = st.empty()
    
    # 文字起こしの更新
    def update_transcript():
        transcript_text = read_transcript()
        # 改行を保持したまま表示
        transcript_container.markdown(transcript_text, unsafe_allow_html=True)
    
    # 初期表示
    update_transcript()
    
    # 自動更新の制御
    auto_update = st.checkbox("自動更新を有効にする", value=True)
    if auto_update:
        st.rerun()

# サイドバー: 設定
with st.sidebar:
    st.title("設定")
    if st.button("チャット履歴をクリア"):
        st.session_state.messages = []
        st.rerun() 