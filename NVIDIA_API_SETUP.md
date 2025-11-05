# NVIDIA API Setup Guide

## Getting Your API Key

1. Visit the NVIDIA API Integration page
2. Sign up or log in to your NVIDIA account
3. Navigate to the API keys section
4. Generate a new API key for the GPT-OSS-20B model

## Setting Up Your API Key

You have two options to configure your API key:

### Option 1: Environment Variable (Recommended)
Set your API key as an environment variable named `NVIDIA_API_KEY`:

**Windows:**
```cmd
set NVIDIA_API_KEY=your_actual_api_key_here
```

**PowerShell:**
```powershell
$env:NVIDIA_API_KEY="your_actual_api_key_here"
```

**Linux/Mac:**
```bash
export NVIDIA_API_KEY="your_actual_api_key_here"
```

### Option 2: Direct Code Modification
Edit the `firebaseFullV10.py` file and replace `YOUR_API_KEY_HERE` with your actual API key:

```python
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="your_actual_api_key_here"  # Replace this with your actual key
)
```

## Installing Required Dependencies

You'll need to install the OpenAI Python client:

```bash
pip install openai
```

## Model Information

The system is now configured to use:
- **Model**: `openai/gpt-oss-20b`
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Temperature**: 0.7 (configurable)
- **Max Tokens**: 1024 (configurable for different functions)

## Testing Your Setup

After setting up your API key, run the system and try asking a question. If everything is configured correctly, you should see responses from the NVIDIA GPT model instead of Ollama.

## Troubleshooting

If you encounter errors:
1. Verify your API key is correct
2. Check your internet connection
3. Ensure you have credits/access to the NVIDIA API
4. Check the console for specific error messages

The system includes fallback error handling, so if the NVIDIA API fails, you'll see descriptive error messages.
