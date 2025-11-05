import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import firebaseTests.firebaseFullV10 as firebaseFullV10
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import os
import re
from firebaseTests.firebaseFullV10 import (
    create_ticket, provide_tech_support_advice, update_ticket_description, update_ticket_priority, update_ticket_status,
    update_ticket_progress, update_ticket_issue_level, delete_ticket, show_tickets, update_employee_name, update_employee_email, 
    update_employee_phone, update_employee_dateOfBirth, update_employee_employeeID, update_employee_password, update_employee_role, 
    update_employee_taxFileNumber, delete_employee, show_employee, show_employee_info, show_tickets_for_update, analyze_ticket_intent, 
    invoke_llm, current_tech_session, notAdmin
)

# Only initialize Firebase once (for Streamlit reruns)
if not firebase_admin._apps:
    cred = credentials.Certificate(r"firebaseTests/firestoreKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

st.set_page_config(page_title="Tech Support Chat", page_icon="💬", layout="wide")
with st.sidebar:
    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state['history'] = []
        st.rerun()
    st.markdown("<div style='text-align: right;'><span style='font-size: 1.5em;'>🔄</span></div>", unsafe_allow_html=True)
    if st.button("Reset UI & Chat History", key="reset_ui"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
st.title("💬 Tech Support AI Chat")
WELCOME_MSG = (
    "👋 **Welcome to Tech Support AI Chat!**\n\n"
    "As a base user, you can:\n"
    "- View, create, update, and delete your own support tickets\n"
    "- Update only the description field of your own tickets\n"
    "- View your own employee information\n"
    "- Ask tech support questions and get troubleshooting advice\n\n"
    "You **cannot**:\n"
    "- View, update, or delete other employees' data\n"
    "- Change ticket priority or status\n"
    "- Access admin-only tools or direct LLM calls\n"
    "- Perform any action outside your own account\n\n"
    "Simply type your issue or request below, and the AI will guide you through the available actions!"
)



if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'employee_id' not in st.session_state:
    st.session_state['employee_id'] = None
if 'current_tech_session' not in st.session_state:
    st.session_state['current_tech_session'] = current_tech_session.copy()

def authenticate_user_ui():
    st.info(WELCOME_MSG)
    st.subheader("🔐 AUTHENTICATION REQUIRED")
    # value = "AS397_573_131" #admin
    value="JS817_669_677" #user
    emp_id = st.text_input("Enter your employee ID:", value, key="auth")
    auth_btn = st.button("Authenticate", key="auth_btn")
    if auth_btn and emp_id:
        doc = db.collection('Employees').document(emp_id).get()
        if doc.exists:
            st.session_state['authenticated'] = True
            st.session_state['employee_id'] = emp_id
            # Set role in session and current_tech_session
            emp_data = doc.to_dict()
            role = emp_data.get('role', 'user')
            st.session_state['role'] = role
            print(role)
            st.session_state['current_tech_session']['employee_id'] = emp_id
            st.session_state['current_tech_session']['authenticated'] = True
            st.session_state['current_tech_session']['role'] = role
            firebaseFullV10.current_tech_session['employee_id'] = emp_id
            firebaseFullV10.current_tech_session['authenticated'] = True
            firebaseFullV10.current_tech_session['role'] = role
            st.success(f"Welcome, {emp_id}! Role: {role}")
                # Show startup message in chat history after login
            if len(st.session_state.get('history', [])) == 0:
                STARTUP_MSG = "💡 You are now logged in! Type your issue or request below to get started."
                st.session_state['history'].append({'role': 'assistant', 'content': STARTUP_MSG})
                st.chat_message('assistant').write(STARTUP_MSG)
            st.rerun()
        else:
            st.error("Employee ID not found.")
    # Show chat history (read-only) while unauthenticated
    for msg in st.session_state['history']:
        st.chat_message(msg['role']).write(msg['content'])
    st.stop()

def check_admin_status():
    role = st.session_state.get('role', None)
    st.session_state['is_admin'] = (role is not None and str(role).lower() == 'admin')

def chat_print(msg, role='assistant'):
    st.session_state['history'].append({'role': role, 'content': str(msg)})

if not st.session_state['authenticated']:
    authenticate_user_ui()

for msg in st.session_state['history']:
    st.chat_message(msg['role']).write(msg['content'])

user_input = st.chat_input("Type your message...")
STARTUP_MSG = "💡 You are now logged in! Type your issue or request below to get started."
if user_input:
    if len(st.session_state['history']) == 0:
        st.session_state['history'].append({'role': 'assistant', 'content': STARTUP_MSG})
        st.chat_message('assistant').write(STARTUP_MSG)
    st.session_state['history'].append({'role': 'user', 'content': user_input})
    st.chat_message('user').write(user_input)
    session = st.session_state['current_tech_session']
    firebaseFullV10.current_tech_session.update(session)
    import time
    max_attempts = 3
    intent_results = None
    user_role = st.session_state.get('role', None)
    for attempt in range(max_attempts):
        try:
            intent_results = analyze_ticket_intent(user_input, user_role=user_role, chat_history=st.session_state['history'])
        except Exception as e:
            intent_results = None
        if (isinstance(intent_results, list) and any(ir.get("tool") not in ["none", "unknown", None] for ir in intent_results)):
            break
        time.sleep(1.5)
    if not isinstance(intent_results, list):
        st.session_state['history'].append({'role': 'assistant', 'content': "Sorry, I couldn't understand your request after several attempts. Please rephrase or try again."})
        st.chat_message('assistant').write("Sorry, I couldn't understand your request after several attempts. Please rephrase or try again.")
        st.stop()
    # Block any response that doesn't actively call a tool or use call_llm
    if all(ir.get("tool") in ["none", "unknown", None] for ir in intent_results):
        with st.spinner('🤖 Thinking...'):
            try:
                result = invoke_llm(user_input)
                st.session_state['history'].append({'role': 'assistant', 'content': str(result)})
                st.chat_message('assistant').write(str(result))
            except Exception as e:
                st.session_state['history'].append({'role': 'assistant', 'content': f"Error calling invoke_llm: {e}"})
                st.chat_message('assistant').write(f"Error calling invoke_llm: {e}")
        st.stop()
    output = []
    # --- Unified Tool Flow ---
    with st.spinner('🤖 Thinking...'):
        for intent_result in intent_results:
            tool = intent_result.get("tool", "none")
            args = intent_result.get("args", {})
            missing_args = intent_result.get("missing_args", [])
            # Handle ticket deletion flow
            if tool == "delete_ticket":
                # If ticket_id is missing, show tickets and prompt for ID or number
                if "ticket_id" in missing_args:
                    tickets = show_tickets(st.session_state['employee_id'])
                    st.session_state['history'].append({'role': 'assistant', 'content': f"Here are your tickets. Please specify the ticket ID or ticket number to delete:\n{tickets}"})
                    st.chat_message('assistant').write(f"Here are your tickets. Please specify the ticket ID or ticket number to delete:\n{tickets}")
                    st.session_state['awaiting_ticket_delete'] = True
                    continue
                # If ticket_id is provided, allow deletion by number or ID
                ticket_id = args.get("ticket_id")
                if ticket_id:
                    # If user gave a ticket number, map to referenceCode
                    ticket_map = firebaseFullV10.current_tech_session.get('last_ticket_map', {})
                    if ticket_id.isdigit() and ticket_id in ticket_map:
                        ticket_id = ticket_map[ticket_id]
                    result = delete_ticket(ticket_id=ticket_id)
                    st.session_state['history'].append({'role': 'assistant', 'content': f"{result}"})
                    st.chat_message('assistant').write(f"{result}")
                    st.session_state['awaiting_ticket_delete'] = False
                    continue
            # Handle awaiting ticket delete state (user responds with ticket number or ID)
            if st.session_state.get('awaiting_ticket_delete', False):
                # Try to extract ticket number or ID from user input
                match = re.search(r"(?:ticket\s*)?(\d+|[A-Za-z0-9_-]{6,})", user_input, re.IGNORECASE)
                ticket_map = firebaseFullV10.current_tech_session.get('last_ticket_map', {})
                ticket_id = None
                if match:
                    val = match.group(1)
                    if val.isdigit() and val in ticket_map:
                        ticket_id = ticket_map[val]
                    else:
                        ticket_id = val
                if ticket_id:
                    result = delete_ticket(ticket_id=ticket_id)
                    st.session_state['history'].append({'role': 'assistant', 'content': f"{result}"})
                    st.chat_message('assistant').write(f"{result}")
                    st.session_state['awaiting_ticket_delete'] = False
                else:
                    st.session_state['history'].append({'role': 'assistant', 'content': "❗ Please specify a valid ticket ID or ticket number to delete."})
                    st.chat_message('assistant').write("❗ Please specify a valid ticket ID or ticket number to delete.")
                continue
            # --- Other tool flows ---
            if tool == "create_ticket" and "description" in missing_args:
                last_desc = session.get("last_issue_description")
                if last_desc:
                    args["description"] = last_desc
                    missing_args = [m for m in missing_args if m != "description"]
            if tool == "provide_tech_support_advice":
                session["last_issue_description"] = user_input
            if tool == "call_llm":
                prompt = args.get("prompt", user_input)
                try:
                    result = invoke_llm(prompt)
                    output.append(result)
                except Exception as e:
                    output.append(f"Error calling invoke_llm: {e}")
                continue
            if tool == "none" or tool == "unknown":
                output.append("❌ This AI agent is only built for tech support actions and answering tech support questions. Please ask a relevant question or use a supported action.")
                continue
            if missing_args:
                output.append(f"Missing arguments for {tool}: {', '.join(missing_args)}")
                continue
            try:
                func = getattr(firebaseFullV10, tool, None)
                if not func:
                    output.append(f"Function '{tool}' not implemented.")
                    continue
                if args:
                    result = func(**args)
                else:
                    result = func()
                if tool == "create_ticket":
                    session["last_issue_description"] = None
                output.append(result)
            except Exception as e:
                output.append(f"Error calling {tool}: {e}")
        for o in output:
            st.session_state['history'].append({'role': 'assistant', 'content': str(o)})
            st.chat_message('assistant').write(str(o))

