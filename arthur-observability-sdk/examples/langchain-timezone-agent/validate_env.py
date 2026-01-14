"""
Environment validation helper for the OpenInference tracing tutorial.
"""

import os

def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = {
        "ARTHUR_BASE_URL": "Arthur instance URL (e.g., https://app.arthur.ai)",
        "ARTHUR_API_KEY": "Arthur API key from your dashboard",
        "OPENAI_API_KEY": "OpenAI API key"
    }

    optional_vars = {
        "ARTHUR_TASK_NAME": "Task name (will auto-create if not exists). Defaults to 'timezone-tutorial-agent'",
        "ARTHUR_TASK_ID": "Arthur task ID (alternative to ARTHUR_TASK_NAME)"
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"• {var}: {description}")

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  {var}")
        print("\nPlease update your .env file with the missing values.")
        return False

    # Check if at least one of ARTHUR_TASK_NAME or ARTHUR_TASK_ID is set
    task_name = os.getenv("ARTHUR_TASK_NAME")
    task_id = os.getenv("ARTHUR_TASK_ID")

    if not task_name and not task_id:
        print("💡 Note: Neither ARTHUR_TASK_NAME nor ARTHUR_TASK_ID is set.")
        print("   Using default task name: 'timezone-tutorial-agent'")
        print("   The SDK will automatically create this task if it doesn't exist.\n")

    return True 