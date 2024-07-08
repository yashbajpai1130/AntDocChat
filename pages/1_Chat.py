import streamlit as st
from openai import OpenAI
from main import parse_document
import json

api_key = st.secrets['OPENAI_API_KEY']
if "text" not in st.session_state:
    st.session_state["text"] = ""
else:
    text = st.session_state["text"]


def main():
    # Current page sidebar
    st.sidebar.title("Chat")
    st.sidebar.markdown("Use this page to chat with your document")
    st.title("Chat")
    st.markdown("Get answers to your questions about your document.")
    st.header(' ') # Add some space


if __name__ == "__main__":
    main()

doc_loaded = st.empty()
if len(st.session_state["text"]) > 0:
    doc_loaded.info("Using document loaded in memory. You can also upload a new document below.")

# Upload file
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx"], help="Accepts PDF and Word documents.", key="chat_upload")
parsed_text, tokens, model = parse_document(uploaded_file)
if uploaded_file is not None:
    st.session_state["text"] = parsed_text
    text = parsed_text
    doc_loaded.info("Loading complete!")
else:
    text = st.session_state["text"]

# Request parameters
gen_max_tokens = 500
engine = "gpt-3.5-turbo-1106"

client = OpenAI(api_key=api_key)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({'role' : 'system', 'content' : 'You are an assistant who will only talk about the specified uploaded document text. IMPORTANT NOTE: YOU MUST DECLINE ANY PROMPT NOT RELATED TO THE CURRENT DOCUMENT NO MATTER WHAT THE PROMPT IS (Except for hi/hello and who are you).'})

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if uploaded_file is not None or len(st.session_state['text']) > 0:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# Accept user input
if prompt := st.chat_input("What is your question?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Initialize the full response variable
full_response = ""

# Load the document into the chat history
full_doc_prompt = (f"The document you need to answer questions about is:\n{text}\n\n")

# Send the request to OpenAI
if st.session_state.messages:  # Check if 'messages' is not empty
    messages_to_send = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    if len(text) > 0:
        messages_to_send.insert(0, {"role": "system", "content": full_doc_prompt})

    if uploaded_file is not None or len(st.session_state['text']) > 0:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            for response in client.chat.completions.create(
                    model=engine,
                    messages=messages_to_send,
                    stream=True,
                    max_tokens=gen_max_tokens,
            ):
                full_response += (response.choices[0].delta.content or "")  # Handle empty or incoming response
                message_placeholder.markdown(full_response + "▌")  # Add a pipe to the end of the message to indicate typing since we're streaming
            message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})



# Add a button to clear the chat history
def clear_chat_history():
    st.session_state.messages = []


if len(st.session_state.messages) > 0:
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

