# Tech Support AI Agent 🤖

An AI-powered tech support system with ticket management and real-time assistance using NVIDIA's LLM API and Firebase Firestore for data storage. Built with Streamlit for an intuitive web interface.

## Features

- 🎫 **Ticket Management**: Create, update, view, and delete support tickets
- 🤖 **AI-Powered Support**: Get real-time troubleshooting advice using NVIDIA's GPU-accelerated LLM
- 👥 **Employee Management**: Manage employee profiles and information
- 🔐 **Role-Based Access Control**: Different permissions for base users and administrators
- 💬 **Interactive Chat Interface**: Streamlit-powered conversational UI
- 📊 **Firebase Integration**: Secure cloud storage for tickets and employee data

## Prerequisites

- Python 3.8 or higher
- Firebase account with Firestore database
- NVIDIA API key for LLM access

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/flexwalnut/tech-support-ADSN.git
cd tech-support-ADSN
```

### 2. Install Required Packages

Install all necessary Python dependencies:

```bash
pip install firebase-admin streamlit openai langchain langchain-core langchain-ollama langchain-chroma pandas google-cloud-firestore
```

Or use the following for individual packages:

```bash
pip install firebase-admin
pip install streamlit
pip install openai
pip install langchain
pip install langchain-core
pip install langchain-ollama
pip install langchain-chroma
pip install pandas
pip install google-cloud-firestore
```

### 3. Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable **Cloud Firestore** in your Firebase project
4. Navigate to **Project Settings** → **Service Accounts**
5. Click **Generate New Private Key** to download your service account JSON file
6. Rename the downloaded file to `firestoreKey.json`
7. Place `firestoreKey.json` in the `firebaseTests/` directory

**Important**: The `firestoreKey.json` file contains sensitive credentials. Never commit it to version control.

### 4. Set Up NVIDIA API

1. Visit the [NVIDIA API Integration](https://build.nvidia.com/) page
2. Sign up or log in to your NVIDIA account
3. Navigate to the API keys section
4. Generate a new API key (the project uses the GPT-based models)

#### Configure Your API Key

**Option 1: Environment Variable (Recommended)**

Set your API key as an environment variable:

**Windows Command Prompt:**
```cmd
set NVIDIA_API_KEY=your_actual_api_key_here
```

**Windows PowerShell:**
```powershell
$env:NVIDIA_API_KEY="your_actual_api_key_here"
```

**Linux/Mac:**
```bash
export NVIDIA_API_KEY="your_actual_api_key_here"
```

**Option 2: Direct Code Modification**

Edit `firebaseTests/firebaseFullV10.py` and add your API key directly:

```python
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="your_actual_api_key_here"  # Replace with your key
)
```

## Usage

### Running the UI Application

To start the Streamlit web interface:

```bash
streamlit run firebaseTests/firebaseFullV10UI.py
```

The application will open in your default web browser at `http://localhost:8501`

### Using the Core Backend

You can also import and use the backend functions directly in your Python scripts:

```python
from firebaseTests.firebaseFullV10 import (
    create_ticket,
    provide_tech_support_advice,
    update_ticket_status,
    show_tickets
)

# Example: Create a ticket
result = create_ticket(employee_id="EMP001", description="Laptop won't turn on")
print(result)

# Example: Get AI support advice
advice = provide_tech_support_advice("My computer is running slow")
print(advice)
```

## Project Structure

```
tech-support-ADSN/
├── firebaseTests/
│   ├── firebaseFullV10.py       # Core backend logic and AI functions
│   ├── firebaseFullV10UI.py     # Streamlit web interface
│   ├── employeeCreation.py      # Employee management utilities
│   ├── firestoreKey.json        # Firebase credentials (NOT included)
│   └── __pycache__/
├── NVIDIA_API_SETUP.md          # Detailed NVIDIA API setup guide
└── README.md                    # This file
```

## User Capabilities

### Base Users Can:
- View, create, update, and delete their own support tickets
- Update the description field of their tickets
- View their own employee information
- Ask tech support questions and get AI-powered troubleshooting advice

### Base Users Cannot:
- View, update, or delete other employees' data
- Change ticket priority or status (admin only)
- Access admin-only tools
- Perform actions outside their own account

## Firestore Collections

The application uses the following Firestore collections:

- **Employees**: Stores employee information (ID, name, email, phone, role, etc.)
- **Tickets**: Stores support tickets (description, priority, status, timestamps, etc.)

## Security Notes

⚠️ **Important Security Information:**

- Never commit `firestoreKey.json` to version control
- Add `firestoreKey.json` to your `.gitignore` file
- Keep your NVIDIA API key secure and private
- Use environment variables for sensitive credentials in production
- Set up proper Firebase security rules for your Firestore database

## Troubleshooting

### Firebase Connection Issues
- Ensure `firestoreKey.json` is in the correct location
- Verify your Firebase project has Firestore enabled
- Check that the service account has the necessary permissions

### NVIDIA API Errors
- Confirm your API key is valid and active
- Check your API usage limits
- Ensure you have internet connectivity

### Package Installation Issues
- Make sure you're using Python 3.8 or higher
- Try upgrading pip: `pip install --upgrade pip`
- Use a virtual environment to avoid conflicts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is available for educational and personal use.

## Support

For issues or questions, please open an issue on the GitHub repository.

---

**Note**: This is an educational project demonstrating AI-powered tech support automation. Ensure proper security measures are in place before deploying to production.

