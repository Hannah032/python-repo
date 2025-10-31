# LLM 챗봇
import streamlit as st
import ollama

st.title("LLM 챗봇 만들기")

if "history" not in st.session_state:
    st.session_state["history"] = []
    # st.session_state["history"].append("123")

for msg in st.session_state["history"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("메세지를 입력하세요")
# st.write(f"{prompt}")
if prompt:
    with st.chat_message("user"):
         st.write(prompt)
    st.session_state["history"].append({"role": "user", "content": prompt})

    resp = ollama.chat(model="gemma3:4b", messages=st.session_state["history"])
    with st.chat_message(resp.message.role):
        st.write(resp.message.content)
    st.session_state["history"].append(dict(resp.message))

