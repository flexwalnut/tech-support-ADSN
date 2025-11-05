import firebase_admin
from datetime import datetime, timezone
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
from google.cloud.firestore_v1.base_query import FieldFilter, Or
from firebase_admin import credentials
from firebase_admin import firestore
import re
import os
import json as _json

if not firebase_admin._apps:
    cred = credentials.Certificate(r"firebaseTests/firestoreKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- LLM-Driven Modular Tools ---
def create_ticket(employee_id: str, description: str) -> str:
    """
    Create a support ticket for the given employee with the provided description.
    Sentiment/priority is determined from the description.
    Returns a formatted confirmation message.
    """
    employee_doc = db.collection('Employees').document(employee_id).get()
    if not employee_doc.exists:
        return f"Error: Employee with ID {employee_id} does not exist."
    employee_data = employee_doc.to_dict()
    employee_name = employee_data.get('name', 'Unknown')
    employee_email = employee_data.get('email', 'N/A')
    employee_phone = employee_data.get('phone', 'N/A')
    # Analyze issue severity (stub: default to L2/medium if LLM not available)
    issue_level, priority = 'L2', 'medium'
    try:
        result = analyze_issue_severity(description)
        if result:
            issue_level, priority = result
    except Exception:
        pass
    ref_code = f"{employee_id}-{datetime.now(timezone.utc).strftime('%Y_%m_%d-%H%M')}"
    ticket = {
        'name': employee_name,
        'employeeID': employee_id,
        'problemDescription': description,
        'issueLevel': issue_level,
        'progressReport': 'Unassigned',
        'priority': priority,
        'createdAt': datetime.now(timezone.utc),
        'updatedAt': 'N/A',
        'contact_info': {
            'email': employee_email,
            'phone': employee_phone
        },
        'referenceCode': ref_code
    }
    db.collection('Tickets').document(ref_code).set(ticket)
    return f"""
### 🎫 Support Ticket Created

**Reference Code:** `{ref_code}`
**Employee:** {employee_name} (`{employee_id}`)
**Description:** {description}
**Priority:** `{priority.upper()}`
**Level:** `{issue_level}`
**Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---
"""

def provide_tech_support_advice(issue_description: str):
    """
    Use LLM to provide comprehensive, well-formatted tech support advice for the reported issue.
    Returns detailed troubleshooting steps with clear formatting and explanations.
    """
    advice_prompt = f"""
    You are a senior IT tech support specialist with 15+ years of experience. A user has reported the following technical issue:

    REPORTED ISSUE: "{issue_description}"

    Please provide troubleshooting advice that would go over the main ways to solve the issue themselves. Please make this the length that the problem deserves, a smaller issue would only need a couple of things however a bigger issue would need a lot more so the choice is yours.

    Make your response comprehensive but organized, so users can easily follow along and understand each step.
    """
    
    try:
        # Request the maximum allowed response from the LLM for full advice
        advice = invoke_llm(advice_prompt, max_tokens=8192)  # Maximize token limit for longer, complete responses
        # If using a streaming LLM API, add logic here to wait for the full response before returning
        return advice
    except Exception as e:
        return f"""
        I'm sorry, but I couldn't generate detailed troubleshooting advice at this time.
    """

def update_ticket_description(ticket_id: str, new_description: str) -> str:
    """
    Update the problem description of a ticket.
    """
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Ticket with ID {ticket_id} does not exist."
    doc_ref.update({'problemDescription': new_description, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Ticket `{ticket_id}` description updated.**"

def update_ticket_progress(ticket_id: str, new_progress: str) -> str:
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Ticket with ID {ticket_id} does not exist."
    doc_ref.update({'progressReport': new_progress, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Ticket `{ticket_id}` progress report updated to `{new_progress}`.**"

def update_ticket_issue_level(ticket_id: str, new_issue_level: str) -> str:
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Ticket with ID {ticket_id} does not exist."
    doc_ref.update({'issueLevel': new_issue_level, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Ticket `{ticket_id}` issue level updated to `{new_issue_level}`.**"

def update_ticket_priority(ticket_id: str, new_priority: str) -> str:
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Ticket with ID {ticket_id} does not exist."
    doc_ref.update({'priority': new_priority, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Ticket `{ticket_id}` priority updated to `{new_priority}`.**"

def update_ticket_status(ticket_id: str, new_status: str) -> str:
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Ticket with ID {ticket_id} does not exist."
    doc_ref.update({'progressReport': new_status, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Ticket `{ticket_id}` status updated to `{new_status}`.**"

def delete_ticket(ticket_id: str) -> str:
    doc_ref = db.collection('Tickets').document(ticket_id)
    doc = doc_ref.get()
    if doc.exists:
        doc_ref.delete()
        return f"**🗑️ Ticket `{ticket_id}` deleted.**"
    else:
        return f"**❌ Ticket with ID `{ticket_id}` does not exist.**"

def show_tickets(employee_id: str) -> str:
    """
    Show all tickets for the given employee ID, formatted.
    """
    docs = db.collection('Tickets').where('employeeID', '==', employee_id).stream()
    tickets = [doc.to_dict() for doc in docs]
    # Set ticket number to reference code mapping for LLM intent resolution
    ticket_map = {}
    for idx, t in enumerate(tickets, 1):
        ticket_map[str(idx)] = t.get('referenceCode')
    current_tech_session['last_ticket_map'] = ticket_map
    if not tickets:
        return f"""
**No tickets found for employee ID `{employee_id}`.**
"""
    out = f"""
### 🎫 Tickets for `{employee_id}`
"""
    for idx, t in enumerate(tickets, 1):
        out += f"""
---
**Ticket #{idx}**
*ID:* `{t.get('referenceCode','N/A')}`
*Issue:* {t.get('problemDescription','N/A')}
*Priority:* `{t.get('priority','N/A').upper()}`
*Level:* `{t.get('issueLevel','N/A')}`
*Status:* `{t.get('progressReport','N/A')}`
*Created:* `{t.get('createdAt','N/A')}`
*Updated:* `{t.get('updatedAt','N/A')}`
"""
    return out

def update_employee_name(employee_id: str, new_name: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'name': new_name, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` name updated to `{new_name}`.**"

def update_employee_email(employee_id: str, new_email: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'email': new_email, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` email updated to `{new_email}`.**"

def update_employee_phone(employee_id: str, new_phone: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'phone': new_phone, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` phone updated to `{new_phone}`.**"

def update_employee_dateOfBirth(employee_id: str, new_dateOfBirth: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'dateOfBirth': new_dateOfBirth, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` date of birth updated to `{new_dateOfBirth}`.**"

def update_employee_employeeID(employee_id: str, new_employeeID: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'employeeID': new_employeeID, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` employee ID updated to `{new_employeeID}`.**"

def update_employee_password(employee_id: str, new_password: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'password': new_password, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` password updated.**"

def update_employee_role(employee_id: str, new_role: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'role': new_role, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` role updated to `{new_role}`.**"

def update_employee_taxFileNumber(employee_id: str, new_taxFileNumber: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Employee with ID {employee_id} does not exist."
    doc_ref.update({'taxFileNumber': new_taxFileNumber, 'updatedAt': datetime.now(timezone.utc)})
    return f"**✅ Employee `{employee_id}` tax file number updated to `{new_taxFileNumber}`.**"

def delete_employee(employee_id: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if doc.exists:
        doc_ref.delete()
        return f"**🗑️ Employee `{employee_id}` deleted.**"
    else:
        return f"**❌ Employee with ID `{employee_id}` does not exist.**"

def show_employee(employee_id: str) -> str:
    doc_ref = db.collection('Employees').document(employee_id)
    doc = doc_ref.get()
    if not getattr(doc, 'exists', False) or (callable(doc.exists) and not doc.exists()):
        return f"Employee with ID {employee_id} does not exist."
    data = doc.to_dict()
    # Show all relevant fields in a table
    fields = [
        ('Created At', data.get('createdAt', 'N/A')),
        ('Date of Birth', data.get('dateOfBirth', 'N/A')),
        ('Email', data.get('email', 'N/A')),
        ('Employee ID', data.get('employeeID', employee_id)),
        ('Name', data.get('name', 'N/A')),
        ('Password', data.get('password', 'N/A')),
        ('Phone', data.get('phone', 'N/A')),
        ('Role', data.get('role', 'N/A')),
        ('Tax File Number', data.get('taxFileNumber', 'N/A'))
    ]
    table = '\n'.join([f"| **{label}** | {value} |" for label, value in fields])
    return f"""
### 👤 Employee Info

| Field | Value |
|-------|-------|
{table}
"""

def show_employee_info(employee_id: str) -> str:
    return show_employee(employee_id)
show_employee_info = show_employee

def notAdmin(message: str = None) -> str:
    """
    Return a formatted message indicating the user does not have admin privileges.
    This function is called by the LLM when a user attempts an admin-only action.
    """
    if message:
        return f"⛔ {message}"
    return "⛔ You do not have admin privileges for this action."

def show_tickets_for_update():
    """
    Show all tickets for the current employee, formatted for update selection. No arguments required.
    """
    global current_tech_session
    employee_id = current_tech_session.get('employee_id')
    if not employee_id:
        return "No employee ID found in session. Please authenticate first."
    # Get tickets and store mapping of index to reference code in session
    docs = db.collection('Tickets').where('employeeID', '==', employee_id).stream()
    tickets = [doc.to_dict() for doc in docs]
    ticket_map = {}
    for idx, t in enumerate(tickets, 1):
        ticket_map[str(idx)] = t.get('referenceCode')
    current_tech_session['last_ticket_map'] = ticket_map
    # Show tickets as before
    if not tickets:
        return f"""
**No tickets found for employee ID `{employee_id}`.**
"""
    out = f"""
### 🎫 Tickets for `{employee_id}` (Select to update)
"""
    for idx, t in enumerate(tickets, 1):
        out += f"""
---
**Ticket #{idx}**
*ID:* `{t.get('referenceCode','N/A')}`
*Issue:* {t.get('problemDescription','N/A')}
*Priority:* `{t.get('priority','N/A').upper()}`
*Level:* `{t.get('issueLevel','N/A')}`
*Status:* `{t.get('progressReport','N/A')}`
*Created:* `{t.get('createdAt','N/A')}`
*Updated:* `{t.get('updatedAt','N/A')}`
"""
    return out
# Initialize NVIDIA OpenAI client
# You can set your API key as an environment variable: NVIDIA_API_KEY
# Or replace the os.getenv() with your actual API key
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    # api_key=os.getenv("NVIDIA_API_KEY", "YOUR OWN NVIDIA API KEY")  # Baseline Tests
    # api_key=os.getenv("NVIDIA_API_KEY", "YOUR OWN NVIDIA API KEY")  # Prompt Injection Tests
    # api_key=os.getenv("NVIDIA_API_KEY", "YOUR OWN NVIDIA API KEY")  # Indirect Reference Tests
    # api_key=os.getenv("NVIDIA_API_KEY", "YOUR OWN NVIDIA API KEY")  # Arithmatic Tests
    api_key=os.getenv("") # Second Arithamtic Tests
)

def make_json_serializable(obj):
    """
    Recursively convert Firestore datetime objects to strings for JSON serialization.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif hasattr(obj, 'isoformat') and callable(obj.isoformat):
        # Handles datetime, DatetimeWithNanoseconds, etc.
        return obj.isoformat()
    else:
        return obj
    
def invoke_llm(prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
    """
    Helper function to invoke the NVIDIA LLM with consistent parameters.
    """
    import time
    import logging
    from threading import Timer
    retries = 3
    delay = 2  # seconds
    last_error = None
    logging.basicConfig(level=logging.INFO)
    def timeout_handler():
        logging.error("LLM call timed out.")
    for attempt in range(retries):
        try:
            logging.info(f"Calling NVIDIA LLM (attempt {attempt+1}) with prompt: {prompt[:100]}...")
            # Set a timeout for the LLM call (simulate with Timer)
            result = [None]
            def call_llm():
                try:
                    result[0] = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        # model="qwen/qwen3-coder-480b-a35b-instruct",
                        # model="qwen/qwen3-next-80b-a3b-thinking",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        top_p=1,
                        max_tokens=max_tokens,
                        stream=False
                    )
                except Exception as e:
                    result[0] = e
            t = Timer(30, timeout_handler)  # 30 second timeout
            t.start()
            call_llm()
            t.cancel()
            completion = result[0]
            if isinstance(completion, Exception):
                last_error = str(completion)
                logging.error(f"LLM call error: {last_error}")
                time.sleep(delay)
                continue
            if not completion or not hasattr(completion, 'choices') or not completion.choices:
                last_error = "No response from LLM API."
                logging.error(last_error)
                time.sleep(delay)
                continue
            message = getattr(completion.choices[0], 'message', None)
            if not message or not hasattr(message, 'content'):
                last_error = "No message content in LLM response."
                logging.error(last_error)
                time.sleep(delay)
                continue
            content = message.content.strip()
            if not content:
                last_error = "Empty response from LLM."
                logging.error(last_error)
                time.sleep(delay)
                continue
            logging.info(f"LLM response: {content[:100]}")
            return content
        except Exception as e:
            last_error = str(e)
            logging.error(f"Error calling NVIDIA LLM (attempt {attempt+1}): {e}")
            time.sleep(delay)
    logging.error(f"Final LLM error after retries: {last_error}")
    return f"I apologize, but I'm having trouble processing your request right now. Error: {last_error}"

# Global variable to store the current tech support session context
current_tech_session = {
    'employee_id': None,
    'original_issue': None,
    'in_session': False,
    'authenticated': False,  # Track if user is authenticated with employee ID
    'awaiting_ticket_response': False,  # Track if we're waiting for user response to ticket prompt
    'last_issue_description': None,  # Store the issue for potential ticket creation
    'awaiting_ticket_management': False,  # Track if we're in ticket management mode
    'current_tickets': None,  # Store current user's tickets
    'selected_ticket': None,  # Store the selected ticket for operations
    'management_action': None,  # Store the action (update/delete)
    'update_field': None  # Store which field is being updated
}

def analyze_issue_severity(issue_description: str):
    """
    Use LLM to analyze the issue description and determine appropriate issue level and priority.
    Returns tuple: (issue_level, priority)
    """
    analysis_prompt = f"""
    Analyze the following IT support issue description and determine:
    1. Issue Level (L0-L4):
       - L0: Critical system outage, complete service failure, security breach
       - L1: High impact, service severely degraded, affects multiple users
       - L2: Medium impact, service partially affected, workaround available
       - L3: Low impact, minor inconvenience, single user affected
       - L4: Informational, general questions, requests

    2. Priority (low, medium, high):
       - high: Urgent, business critical, blocks work completely
       - medium: Important but not urgent, has workaround
       - low: Nice to have, minimal business impact

    Issue Description: "{issue_description}"

    Respond ONLY with the format: "LEVEL:Lx,PRIORITY:xxx" (e.g., "LEVEL:L2,PRIORITY:medium")
    """
    
    try:
        result = invoke_llm(analysis_prompt)
        # Parse the response
        import re
        level_match = re.search(r'LEVEL:(L[0-4])', result, re.I)
        priority_match = re.search(r'PRIORITY:(low|medium|high)', result, re.I)
        
        issue_level = level_match.group(1) if level_match else 'L2'  # Default to L2
        priority = priority_match.group(1).lower() if priority_match else 'medium'  # Default to medium
        
        return issue_level, priority
    except Exception as e:
        # Fallback to defaults if LLM analysis fails
        print(f"Issue analysis failed, using defaults: {e}")
        return 'L2', 'medium'

def retrieve_all_employees():
    """
    Retrieve all employee documents from the Employees collection.
    """
    docs = db.collection('Employees').stream()
    employees = []
    for doc in docs:
        data = doc.to_dict()
        data['ID'] = doc.id
        employees.append(data)
    return employees

def llm_missing_arg_handler(tool: str, missing_args: list, user_prompt: str, context: dict = None) -> str:
    """
    Uses the LLM to ask the user for missing arguments in a natural, context-aware way.
    If the user's reply fills the missing arguments, returns the new arguments.
    If the reply is ambiguous or unrelated, re-asks or re-runs intent analysis as needed.
    """
    # Compose a prompt for the LLM to ask for missing arguments
    context_str = ""
    if context:
        context_str = f"Context: {context}\n"
    missing_str = ', '.join(missing_args)
    prompt = f"""
You are a helpful tech support assistant. The user requested to perform the action: '{tool}'.
However, the following required arguments are missing: {missing_str}.
{context_str}
User's last message: '{user_prompt}'

Please ask the user for the missing information in a friendly, conversational way. If the user's reply provides the needed info, extract it and return it in JSON format. If the reply is ambiguous or unrelated, ask again for the missing info. If the reply is a new request, return a message indicating a new intent should be analyzed.
Respond ONLY with a JSON object:
{{
  "status": "ok" or "ask_again" or "new_intent",
  "args": {{ ... }}  # Only if status is ok
  "message": "..."  # What to say to the user
}}
"""
    response = invoke_llm(prompt)
    try:
        result = _json.loads(response)
    except Exception:
        # Fallback: just return the LLM's message
        return {"status": "ask_again", "args": {}, "message": response}
    return result

def process_prompt_for_tool_call(user_request: str, user_role: str = None, tech_session=None, llm_func=None, chat_history=None) -> str:
    """
    Constructs the intent prompt and calls the provided LLM function.
    Returns the raw LLM result (JSON string).
    """
    session = tech_session if tech_session is not None else globals().get('current_tech_session', {})
    employee_id = session.get('employee_id')
    last_issue_description = session.get('last_issue_description')
    role = user_role if user_role else "user"
    ticket_map = session.get('last_ticket_map', {})
    ticket_map_str = '\n'.join([f"{k}: {v}" for k, v in ticket_map.items()]) if ticket_map else 'None'
    
    # Format chat history for context
    history_str = ""
    if chat_history and len(chat_history) > 0:
        # Include last 5 messages for context (to avoid token limits)
        recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
        history_entries = []
        for msg in recent_history:
            role_name = msg.get('role', 'unknown')
            content = msg.get('content', '')
            # Truncate very long messages
            if len(content) > 200:
                content = content[:200] + "..."
            history_entries.append(f"{role_name.upper()}: {content}")
        history_str = '\n'.join(history_entries)
    else:
        history_str = "No previous conversation history available."
    
    intent_prompt = f'''
ADMIN FUNCTION RESTRICTIONS:

- The following functions are **admin-only** and must NOT be called unless the user's role is "admin":
    - Any function that views, updates, or deletes employee data for users other than the current employee ID.
    - Any function that creates, updates, shows, or deletes tickets for an employee ID other than the current user's.
    - Admin-only ticket update functions are any other than the description

- Regular users may:
    - View, create, update, and delete their own tickets (where employee_id matches their own).
    - Update only the description field of their own tickets (update_ticket_description) and nothing more.
    - View their own employee data (show_employee_info for their own ID).

- If a regular user requests an admin-only function, return a tool called "notAdmin" with a message explaining they do not have privileges.

- Always check the user's role before selecting a tool. If the user's role is not "admin", do not allow admin-only functions.

User Role: "{role}"
Current Employee ID: "{employee_id}"

RECENT CHAT HISTORY (for context):
{history_str}

You are an intent and argument extraction engine for a tech support system. Your job is to:
1. Select the most appropriate tool(s)/function(s) to call (see list below). You may return a single tool or a list of tools to execute in order, if the user's request requires multiple steps (e.g., show tickets before updating, or show then update).
2. Extract as many arguments as possible from the user's request and recent context.
3. Identify which required arguments are missing (if any).
4. Use the chat history to understand context and previous responses to make better decisions about what tools to call. If they want to refer to a previous response then look through {history_str} to get it and come back with a more detailed response.

User request: "{user_request}"
LAST ISSUE DESCRIPTION (use this for the description argument if the user refers to a previous issue or says something like 'create a ticket'): "{last_issue_description}"
TICKET NUMBER TO REFERENCE CODE MAP (from last shown tickets):
{ticket_map_str}

TOOLS (atomic, stateless, always require explicit arguments):
- create_ticket(employee_id: str, description: str)
- provide_tech_support_advice(issue_description: str)
- update_ticket_progress(ticket_id: str, new_progress: str)
- update_ticket_issue_level(ticket_id: str, new_issue_level: str)
- update_ticket_description(ticket_id: str, new_description: str)
- update_ticket_priority(ticket_id: str, new_priority: str)
- update_ticket_status(ticket_id: str, new_status: str)
- delete_ticket(ticket_id: str)
- show_tickets(employee_id: str)
- update_employee_name(employee_id: str, new_name: str)
- update_employee_email(employee_id: str, new_email: str)
- update_employee_phone(employee_id: str, new_phone: str)
- update_employee_dateOfBirth(employee_id: str, new_dateOfBirth: str)
- update_employee_employeeID(employee_id: str, new_employeeID: str)
- update_employee_password(employee_id: str, new_password: str)
- update_employee_role(employee_id: str, new_role: str)
- update_employee_taxFileNumber(employee_id: str, new_taxFileNumber: str)
- delete_employee(employee_id: str)
- show_employee_info(employee_id: str)
- show_tickets_for_update()  # Use this if the user wants to update a ticket but hasn't specified which one or which attribute. This function takes no arguments and will display all tickets for the current employee.

INSTRUCTIONS:
- Always use the CURRENT EMPLOYEE ID for any employee_id argument.
- If the user refers to a previous issue (e.g., 'Can I create a ticket?'), use the LAST ISSUE DESCRIPTION for the description argument if available.
- If a required argument is missing, list it in "missing_args" (do not invent values).
- If the user refers to a ticket by number (e.g., "ticket 2"), use the TICKET NUMBER TO REFERENCE CODE MAP to get the correct reference code for the ticket_id argument. If they use a reference code directly, use it as-is.
- If the user wants to update/ delete a ticket but hasn't specified the ticket number or the attribute to update, or if you think it would help the user, you may include "show_tickets_for_update" as the first tool in your list, followed by the update tool (if enough info is available after showing tickets).
- If the user wants to update a ticket but does not specify what field to update (e.g., description, priority, status), ask the user to rephrase their request to include the field/attribute they want to update.
- If the request is a general question or does not match any tool, set tool(s) to "none", this should be done as a final measure.
- If a user wants to delete a ticket that is not their own, return "notAdmin" with a message explaining they do not have privileges, you can find this out if the employee ID used isnt in the first digits of the ticket number (e.g., ticket Delete Ticket MR909_162_526-2025_09_16-0632 belongs to MR909_162_526 however if JM362_393_537 wants to delete it they cant).
- If a user want to view or modify employee data for any user no matter who they are, return "notAdmin" with a message explaining they do not have privileges.

Respond in strict JSON format. If only one tool is needed, return a single object. If multiple tools are needed, return a list of objects, each with:
{{
    "tool": "function name or 'none' or 'notAdmin'",
    "args": {{ "arg1": "value", ... }},
    "missing_args": ["arg1", ...]
}}

Examples:
User: "Update my ticket"
Response:
[
    {{"tool": "show_tickets_for_update", "args": {{}}, "missing_args": []}}
]

User: "Can I delete a ticket?"
Response:
[
    {{"tool": "show_tickets_for_update", "args": {{}}, "missing_args": []}}
]

User: "Update my ticket 1234 to high priority"
Response:
[
    {{"tool": "update_ticket_priority", "args": {{"ticket_id": "1234", "new_priority": "high"}}, "missing_args": []}}
]

User: "Update my ticket but I don't remember the number"
Response:
[
    {{"tool": "show_tickets_for_update", "args": {{}}, "missing_args": []}}
]

User: "Update my ticket 1234 but I don't know what to change"
Response:
[
    {{"tool": "show_tickets_for_update", "args": {{}}, "missing_args": []}},
    {{"tool": "update_ticket_priority", "args": {{"ticket_id": "1234"}}, "missing_args": ["new_priority"]}}
]

User: "My internet is really slow"
Response:
[
    {{"tool": "provide_tech_support_advice", "args": {{"issue_description": "My internet is really slow"}}, "missing_args": []}}
]

User: "How does this work?"
Response:
[
    {{"tool": "none", "args": {{}}, "missing_args": []}}
]
'''
    llm = llm_func if llm_func is not None else invoke_llm
    return llm(intent_prompt)

def analyze_ticket_intent(user_request: str, user_role: str = None, chat_history: list = None) -> str:
    """
    Use LLM to analyze user request and determine what tool/action they want, extract arguments, and identify missing arguments.
    Returns a dict: {"tool": ..., "args": {...}, "missing_args": [...]}.
    """
    global current_tech_session
    try:
        result = process_prompt_for_tool_call(user_request, user_role, tech_session=current_tech_session, chat_history=chat_history)
        import pprint
        print("INFO:root:LLM response:")
        pprint.pprint(result)
        result_stripped = result.strip()
        is_object = result_stripped.startswith('{') and result_stripped.endswith('}')
        is_array = result_stripped.startswith('[') and result_stripped.endswith(']')
        if not (is_object or is_array):
            print(f"Intent analysis failed: LLM did not return JSON. Raw output: {result_stripped}")
            return [{"tool": "unknown", "args": {}, "missing_args": []}]
        parsed = _json.loads(result_stripped)
        if is_object:
            parsed = [parsed]
        # Let the LLM be the sole authority on admin permissions - no backend filtering
        return parsed
    except Exception as e:
        print(f"Intent analysis failed: {e}")
        return {"tool": "unknown", "args": {}, "missing_args": []}

def analyze_ticket_intent_llm2(user_request: str, user_role: str = None, chat_history: list = None) -> str:
    """
    Use a second LLM to analyze user request and determine tool/action, arguments, and missing arguments.
    Returns a dict: {"tool": ..., "args": {...}, "missing_args": [...]}.
    """
    global current_tech_session
    # Replace 'invoke_llm_2' with the actual second LLM function if available
    def invoke_llm_2(prompt):
        # For now, use the same LLM as a placeholder
        return invoke_llm(prompt)
    try:
        result = process_prompt_for_tool_call(user_request, user_role, tech_session=current_tech_session, llm_func=invoke_llm_2, chat_history=chat_history)
        result_stripped = result.strip()
        is_object = result_stripped.startswith('{') and result_stripped.endswith('}')
        is_array = result_stripped.startswith('[') and result_stripped.endswith(']')
        if not (is_object or is_array):
            print(f"LLM2 Intent analysis failed: LLM did not return JSON. Raw output: {result_stripped}")
            return [{"tool": "unknown", "args": {}, "missing_args": []}]
        parsed = _json.loads(result_stripped)
        if is_object:
            parsed = [parsed]
        # Let the LLM be the sole authority on admin permissions - no backend filtering
        return parsed
    except Exception as e:
        print(f"LLM2 Intent analysis failed: {e}")
        return {"tool": "unknown", "args": {}, "missing_args": []}

def compare_intent_responses(resp1, resp2):
    """
    Compare two intent responses from LLMs. Returns True if they match, False otherwise.
    """
    import json
    def normalize(resp):
        if isinstance(resp, str):
            try:
                return json.loads(resp)
            except Exception:
                return resp
        return resp
    r1 = normalize(resp1)
    r2 = normalize(resp2)
    return r1 == r2
def handle_command(command: str):
    command_lower = command.lower()
    global current_tech_session

    # Handle session management commands
    if command_lower in ['end session', 'logout', 'clear session', 'reset', 'new user']:
        current_tech_session = {
            'employee_id': None,
            'original_issue': None,
            'in_session': False,
            'authenticated': False,
            'awaiting_ticket_response': False,
            'last_issue_description': None,
            'awaiting_ticket_management': False,
            'current_tickets': None,
            'selected_ticket': None,
            'management_action': None,
            'update_field': None
        }
        return "Session cleared. You can start fresh with a new employee ID."

    # Show current session info
    elif command_lower in ['session info', 'who am i', 'current user']:
        if current_tech_session['authenticated']:
            return f"Current session: Employee ID {current_tech_session['employee_id']}\nYou can type 'end session' to clear this and start fresh."
        else:
            return "No active session. Please describe your technical issue to get started."

    # Use both LLMs to analyze ticket/employee management intent and extract arguments
    intent_results_1 = analyze_ticket_intent(command)
    intent_results_2 = analyze_ticket_intent_llm2(command)
    output = []
    # Compare both LLM results
    if not compare_intent_responses(intent_results_1, intent_results_2):
        output.append("⚠️ Dispute detected between LLMs. Using main LLM result.\nLLM1: {}\nLLM2: {}".format(intent_results_1, intent_results_2))
    intent_results = intent_results_1
    for intent_result in intent_results:
        tool = intent_result.get("tool", "none")
        args = intent_result.get("args", {})
        missing_args = intent_result.get("missing_args", [])

        # If the user is asking for advice, store their prompt as the last issue description
        if tool == "provide_tech_support_advice":
            current_tech_session["last_issue_description"] = command
        # If user asks to create a ticket and description is missing, use last_issue_description
        if tool == "create_ticket" and "description" in missing_args:
            last_desc = current_tech_session.get("last_issue_description")
            if last_desc:
                args["description"] = last_desc
                missing_args = [m for m in missing_args if m != "description"]
        if tool == "notAdmin":
            output.append("⛔ You do not have admin privileges for this action.")
            continue
        if tool == "none":
            output.append("No ticket or employee management action detected.")
            continue
        if tool == "unknown":
            output.append("Sorry, I couldn't determine the correct action for your request.")
            continue

        # If there are missing arguments, use LLM-based handler
        if missing_args:
            # Call LLM error handler to ask user for missing args
            llm_result = llm_missing_arg_handler(tool, missing_args, command, context=current_tech_session)
            output.append(llm_result.get("message", ""))
            # If user provided missing args, try to call the tool again
            if llm_result.get("status") == "ok" and llm_result.get("args"):
                try:
                    func = globals().get(tool)
                    if func:
                        result = func(**llm_result["args"])
                        output.append(result)
                        continue
                except Exception as e:
                    output.append(f"Error calling {tool} with user-supplied args: {e}")
            # If LLM says to re-analyze intent, break and re-run intent analysis
            if llm_result.get("status") == "new_intent":
                return handle_command(llm_result.get("message", ""))
            # Otherwise, ask again or stop
            continue

        # Dynamically call the tool function with the arguments
        try:
            func = globals().get(tool)
            if not func:
                output.append(f"Function '{tool}' not implemented.")
                continue
            # If the function takes no arguments, call without args
            if args:
                result = func(**args)
            else:
                result = func()
            # If a ticket is created, clear last_issue_description to avoid reusing old issues
            if tool == "create_ticket":
                current_tech_session["last_issue_description"] = None
            output.append(result)
        except Exception as e:
            output.append(f"Error calling {tool}: {e}")
    return "\n".join(str(o) for o in output)

template = """
You are an expert technology support assistant and customer service representative.

YOUR PRIMARY ROLE: Help users with general questions, employee lookups, and ticket management operations.

IMPORTANT: For technical issues and problems, the system automatically detects these and provides specialized troubleshooting advice through a dedicated technical support flow. You should focus on:

CAPABILITIES:
- Answer general questions about the support system
- Search for employees by name, email, or phone number  
- Help with ticket operations (retrieve, update, delete tickets)
- Provide information about the system's capabilities
- Handle administrative requests

TICKET OPERATIONS:
For existing tickets, you can help users:
- Retrieve tickets by ID, employee ID, or contact info
- Update ticket information 
- Delete tickets when necessary
- Show all tickets in the system

EMPLOYEE SEARCH:
You can find employees by:
- Name, email, or phone number
- Return employee ID and contact information

TECHNICAL ISSUES: 
When users describe technical problems (computer won't start, login issues, etc.), the system automatically:
1. Detects it's a technical issue
2. Provides specialized troubleshooting advice
3. Offers to create a support ticket with the advice included

Conversation history:
{history}

Here is the user question to answer: {question}
"""

def generate_response(history: str, question: str) -> str:
    """
    Generate a response using the NVIDIA LLM with the template.
    """
    formatted_prompt = template.format(history=history, question=question)
    return invoke_llm(formatted_prompt, max_tokens=4096)

history = []

## Terminal authentication and main loop removed. All authentication is now handled in the UI layer (e.g., Streamlit).
 