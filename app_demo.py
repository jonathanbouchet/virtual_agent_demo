# https://discuss.streamlit.io/t/how-secure-streamlit-session-states-are/16260

import streamlit as st
import random
import sys
import time
import logging
import openai
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from utils import *
from io import BytesIO
from gtts import gTTS, gTTSError

# Create and configure logger
logging.basicConfig(
    filename="app.log",
    format='%(asctime)s %(message)s',
    filemode='w', )

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.INFO)

# init
if "password_correct" not in st.session_state:
    st.session_state.password_correct = False
if "password_correct_checked" not in st.session_state:
    st.session_state.password_correct_checked = False
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'requests' not in st.session_state:
    st.session_state.requests = []


def new_chat():
    st.title("Reflexive AI")
    st.header("Virtual Insurance Agent Accelerator")

    # Set API key
    openai_api_key = st.sidebar.text_input(
        ":blue[API-KEY]",
        placeholder="Paste your OpenAI API key here",
        type="password")

    active_voice = st.sidebar.radio(label=":blue[Active Voice]", options=('No', 'Yes'))

    if openai_api_key:

        def get_conversation_string():
            conversation_string = ""
            for i in range(len(st.session_state['responses']) - 1):
                conversation_string += "Human: " + st.session_state['requests'][i] + "\n"
                conversation_string += "Bot: " + st.session_state['responses'][i + 1] + "\n"
            return conversation_string

        llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k-0613", openai_api_key=openai_api_key, temperature=0)
        if 'buffer_memory' not in st.session_state:
            st.session_state.buffer_memory = ConversationBufferWindowMemory(
                k=10,
                return_messages=True
            )

        system_msg_template = SystemMessagePromptTemplate.from_template(
            template=template_insurance()
        )

        human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
        prompt_template = ChatPromptTemplate.from_messages(
            [system_msg_template, MessagesPlaceholder(variable_name="history"), human_msg_template]
        )
        conversation = ConversationChain(
            memory=st.session_state.buffer_memory,
            prompt=prompt_template,
            llm=llm, verbose=True
        )

        # greeting message from the assistant
        with st.chat_message("assistant"):
            greeting_msg = "how can I help you today ?"
            st.markdown(greeting_msg)
            # Add assistant response to chat history
            # st.session_state.messages.append({"role": "assistant", "content": greeting_msg})

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("type your message here"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)
                logging.info(f"[user]:{prompt}")

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                conversation_string = get_conversation_string()
                response = conversation.predict(input=f"Query:\n{prompt}")
                full_response = ""
                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.01)
                message_placeholder.markdown(full_response)
                if active_voice == "Yes":
                    sound_file = BytesIO()
                    try:
                        tts = gTTS(text=response, lang='en')
                        tts.write_to_fp(sound_file)
                        st.audio(sound_file, start_time=0)
                    except gTTSError as err:
                        st.error(err)
                    # t1 = gtts.gTTS(response)
                    # t1.save("test.mp3")
                    # playsound("test.mp3")
                logging.info(f"[assistant]:{full_response}")

            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            # check for user response right at the beginning by looking at any message non-empty
            if st.session_state:
                print(f"st.session_state: {st.session_state['messages']}")
                if st.session_state['messages'][-1]['role'] == "assistant":
                    download_transcript(st.session_state['messages'][-1]['content'])

            print(f"end of session\t{st.session_state.messages}")


def password_entered():
    """Checks whether a password entered by the user is correct."""
    if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
    ):
        st.session_state["password_correct"] = True
        del st.session_state["password"]  # don't store username + password
        del st.session_state["username"]
    else:
        st.session_state["password_correct"] = False


def check_password():
    """Returns `True` if the user had a correct password."""

    password_entered()

    if "password_correct" not in st.session_state:
        return False
    elif not st.session_state["password_correct"]:
        return False
    else:
        # Password correct.
        return True


if not st.session_state['password_correct_checked']:
    # Create an empty container
    placeholder = st.empty()

    # Insert a form in the container
    with placeholder.form("login"):
        st.markdown("#### Enter your credentials")
        username = st.text_input("username", key="username")
        password = st.text_input("Password", type="password", key="password")
        print(f"username{username}, password:{password}")
        submit = st.form_submit_button("Login")
        print(f"submit:{submit}")

    if submit and check_password():
        # If the form is submitted and the email and password are correct,
        # clear the form/container and display a success message
        placeholder.empty()
        st.success("Login successful")
        st.session_state['password_correct_checked'] = True
        new_chat()
    elif submit and not check_password():
        st.session_state['password_correct_checked'] = False
        st.error("User not known or password incorrect")
    else:
        pass
else:
    new_chat()
