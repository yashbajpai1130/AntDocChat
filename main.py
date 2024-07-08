# External imports
import streamlit as st
from st_pages import Page, show_pages
import tiktoken
from openai import OpenAI, OpenAIError
import math
import docx2txt
import PyPDF2
import json

# Internal imports
api_key = st.secrets['OPENAI_API_KEY']


st.set_page_config(page_title="DocChat Ant", page_icon=":speech_balloon:", layout="wide")

# Initialize the session key for the text. See the end of parse_document() for writing.
if "text" not in st.session_state:
    st.session_state["text"] = ""

def main():
    # Current page sidebar
    st.sidebar.title("Summary")
    st.sidebar.markdown("""
    Use this tab to get a quick summary of your uploaded document.\n
    """)

    # Top level greeting
    title, modeToggle = st.columns(2)
    title.title("DocChat Ant")
    #modeToggle.toggle("Advanced Mode", value=False, key="simple_mode", disabled=True, help="Coming soon!")
    st.markdown("""
    Upload a document and a summary will be generated below. Use the Chat tab to ask questions about the document.
    """)
    st.header(' ') # Add some space


if __name__ == "__main__":
    main()



# Create the navigation bar
show_pages(
    [
        Page("main.py", "Summary", ":house:"),
        Page("pages/1_Chat.py", "Chat", ":speech_balloon:"),
    ]
)


# Maximum number of tokens to generate
gen_max_tokens = 500

# Upload file
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx"], help="Accepts PDF and Word documents.")


@st.cache_data(show_spinner=True, persist=True)
def parse_document(uploaded_file):
    text = ''
    tokens = 0
    if uploaded_file is None: # Prevent error message when no file is uploaded
        return text, tokens, None
    else:
        name = uploaded_file.name
        # Check the extension and load the appropriate library
        if name.endswith(".pdf"):
            
            pdfReader = PyPDF2.PdfReader(uploaded_file)
            for page in range(len(pdfReader.pages)):
                page_obj = pdfReader.pages[page]
                text += page_obj.extract_text()

        elif name.endswith(".docx"):
            
            text = docx2txt.process(uploaded_file)

        # Count the number of tokens in the document
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        output = encoding.encode(text)
        tokens = len(encoding.encode(text))

        # Choose the right model based on the number of tokens. GPT-3.5-Turbo only.
        if tokens == 0:
            model = None
        elif tokens <= 16385 - gen_max_tokens:
            model = "gpt-3.5-turbo-1106"
        else:
            divider = math.ceil(tokens / 16385)
            st.error(f"Your document is too long! You need to choose a smaller document or divide yours in {divider} parts.")
            model = None
            st.stop()

        # Display the token count and model used inside a collapsible container
        with st.expander("Show details"):
            st.write(f"Number of tokens: {tokens}")
            st.write(f"Using model: {model}")

        # Save the text to the session state
        st.session_state["text"] = text

        return text, tokens, model


# Use the function to parse the uploaded file
text, tokens, model = parse_document(uploaded_file)



# Create the OpenAI request
client = OpenAI(api_key=api_key)
sys_prompt = ("You are an assistant designed to give summaries of uploaded documents, politely decline any prompts not related to the document. Your answers should be decently long, "
          "in the form of bullet points. Make sure to include every point discussed in the document. Being verbose is "
          "highly preferable compared to missing ideas in the document. Do not deviate from this command. You are to provide an objective summary without tangential analyses. Here is the document to recap:")

@st.cache_data(show_spinner=True, persist=True)
def generate_completion(text):
    if text == '':
        print("No document detected.")
        return ""

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=gen_max_tokens,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text}
            ]
        )
        st.markdown("## Summary")
        response_text = response.choices[0].message.content

        # Add session state to keep the output text if the user switches tabs
        if 'saved_text' in st.session_state:
            st.session_state.saved_text = response_text
        else:
            st.session_state.saved_text = response_text
        st.cache_data.clear()

        return response_text

    except OpenAIError as e:
        print(f"An error occurred: {e}")
        return None


response_text = generate_completion(text)


output_wrapper = st.empty() 
if 'saved_text' not in st.session_state:
    output_wrapper.markdown(response_text)
else:
    output_wrapper.markdown(st.session_state.saved_text)


def regenerate_summary():
    st.cache_data.clear()
    output_wrapper.empty()


def clear_summary():
    st.session_state.saved_text = ''
    output_wrapper.empty()
    st.toast("Summary cleared!")

if len(response_text) > 0:
    st.sidebar.button("Regenerate summary", on_click=regenerate_summary)
    if st.sidebar.button("Clear summary", on_click=clear_summary):
        st.stop()
