"""
streamlit_app.py — Financial Data Analyst Assistant Web Demo UI.

Phase 4, Step 9.
Runs a simple web interface for testing the Multi-Agent Financial RAG.
"""

import streamlit as st
import pandas as pd
import json
import time

st.set_page_config(
    page_title="ViFinQA AI Assistant",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Financial Data Analyst Assistant")
st.markdown("""
Welcome to the Financial RAG Demo. 
Enter a financial question (e.g., *'Doanh thu thuần của AAA năm 2015 là bao nhiêu?'*) to test the Multi-Agent reasoning chain (Planner, Retriever, Programmer, Critic).
""")

# Sidebar for config
with st.sidebar:
    st.header("⚙️ Configuration")
    run_mode = st.radio("Run Mode", ["Sample (AAA)", "Full Dataset"], index=0)
    st.markdown("---")
    st.write("**Agent Status:**")
    st.success("🤖 Planner: Ready (14B)")
    st.success("🔍 Retriever: Ready (7B)")
    st.success("💻 Programmer: Ready (14B)")
    st.success("⚖️ Critic: Ready (3B)")

# Main Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Hỏi AI về số liệu tài chính..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Simulate Multi-Agent Pipeline steps
        with st.status("Executing Multi-Agent Chain...", expanded=True) as status:
            st.write("🕵️‍♂️ **Planner:** Analyzing query intent...")
            time.sleep(1)
            
            st.write("🔍 **Retriever:** Searching Table Corpus (BM25 + BGE-M3 Dense)...")
            time.sleep(1)
            st.code("table_id: AAA_2015_consolidated_page4_table0\nconfidence: 0.95")
            
            st.write("💻 **Programmer:** Generating Pandas Sandbox Query...")
            time.sleep(1.5)
            st.code("df[df['row_label_full'].str.contains('Doanh thu thuần', case=False)]['numeric__value'].values[0]", language="python")
            
            st.write("⚖️ **Critic:** Verifying output alignment with constraints...")
            time.sleep(1)
            
            status.update(label="Chain Execution Complete!", state="complete", expanded=False)
        
        # Final mocked answer for demo
        mock_answer = "Dựa trên Báo cáo tài chính hợp nhất năm 2015 của công ty AAA, **Doanh thu thuần** đạt **1,613,000,000,000 đồng** (1,613 tỷ đồng)."
        
        # Stream response
        full_response = ""
        for chunk in mock_answer.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
        
        with st.expander("Show Evidence Data"):
            df = pd.DataFrame({
                "row_label_full": ["Doanh thu bán hàng", "Các khoản giảm trừ", "Doanh thu thuần"],
                "numeric__value": [1615000000000, 2000000000, 1613000000000]
            })
            st.dataframe(df)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
