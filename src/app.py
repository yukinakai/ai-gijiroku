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

# タブの作成
tab1, tab2 = st.tabs(["AI議事録アシスタント", "リアルタイム文字起こし"])

# タブ1: チャットUI
with tab1:
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

# タブ2: 文字起こし表示
with tab2:
    st.title("リアルタイム文字起こし")
    
    # 更新ボタン
    if st.button("文字起こしを更新"):
        st.rerun()
    
    # 文字起こし内容を表示
    transcript_text = read_transcript()
    st.markdown(transcript_text, unsafe_allow_html=True)

# サイドバー: 設定
with st.sidebar:
    st.title("設定")
    
    # チャット履歴のクリア
    if st.button("チャット履歴をクリア"):
        st.session_state.messages = []
        st.rerun() 