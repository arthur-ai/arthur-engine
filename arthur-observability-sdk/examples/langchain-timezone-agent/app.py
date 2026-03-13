"""
Simple OpenInference Tracing Tutorial with LangChain using Arthur Observability SDK

This tutorial shows how to:
1. Set up OpenInference tracing with Arthur using the unified ArthurClient
2. Auto-instrument a LangChain agent
3. Use session/user context for tracking conversations
4. Use timezone conversion tools

The Arthur Observability SDK provides unified access to Arthur APIs and telemetry!
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import our timezone tools
from timezone_tools import get_current_time, convert_time_between_zones
from validate_env import validate_environment

# Load environment variables
load_dotenv()

# Import Arthur Observability SDK (after loading env vars)
from arthur_observability_sdk import ArthurClient, context, instrument_langchain

# Global Arthur client instance
arthur = None

def setup_arthur_client():
    """Set up Arthur client with API and telemetry."""
    global arthur

    # Initialize Arthur client (handles both API and telemetry!)
    # The client will automatically get or create a task based on task_name
    arthur = ArthurClient(
        task_name=os.getenv("ARTHUR_TASK_NAME", "timezone-tutorial-agent"),
        api_key=os.getenv("ARTHUR_API_KEY"),
        base_url=os.getenv("ARTHUR_BASE_URL"),
        service_name="multiagent-playground-tutorial",
        use_simple_processor=True  # Use SimpleSpanProcessor for immediate span export
    )

    # Auto-instrument LangChain
    instrument_langchain()

    print(f"✅ Arthur client initialized successfully")
    print(f"   Task ID: {arthur.task_id}")
    print(f"   Telemetry: {'Active' if arthur.telemetry.is_initialized() else 'Inactive'}")

def create_simple_agent():
    """Create a LangChain agent with timezone tools."""

    # Initialize the model
    model = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create tools list
    tools = [get_current_time, convert_time_between_zones]

    # Create a proper prompt template with system and user messages
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant with timezone conversion capabilities.

You can:
1. Get the current time in any timezone or city using the get_current_time tool
2. Convert times between different timezones using the convert_time_between_zones tool

When users ask about times, use the appropriate tool to provide accurate information.
For example:
- "What time is it in Zurich?" -> use get_current_time
- "What is 10pm EDT in California?" -> use convert_time_between_zones

Always provide clear, helpful responses with the time information. Be conversational and helpful."""),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    # Create the agent with tools
    agent = create_openai_tools_agent(
        llm=model,
        tools=tools,
        prompt=prompt
    )

    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True
    )

    return agent_executor

def chat_with_agent(agent_executor, message: str, session_id: str = "default-session", user_id: str = "demo-user"):
    """Chat with the agent with session and user tracking."""

    # Use context manager to add session and user metadata to traces
    with context(session_id=session_id, user_id=user_id):
        result = agent_executor.invoke({
            "input": message
        })

    return result["output"]

def main():
    """Main function to run the tutorial."""

    print("🚀 OpenInference Tracing Tutorial with Arthur Observability SDK")
    print("=" * 60)
    print("This agent helps you convert times between different timezones and cities.")
    print("All interactions are traced to Arthur for monitoring and analysis.")
    print()
    print("💡 Examples: 'What time is it in Tokyo?' or 'What is 3pm EST in London?'")
    print()

    try:
        # Validate environment first
        if not validate_environment():
            print("❌ Environment validation failed. Please check your .env file.")
            return

        # Set up Arthur client and create agent
        setup_arthur_client()
        agent = create_simple_agent()

        # Generate a unique session ID for this conversation
        import uuid
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        user_id = "demo-user"

        print(f"✅ Agent ready! Session ID: {session_id}")
        print("Start chatting (type 'quit' to exit):")
        print("-" * 60)

        while True:
            user_input = input("\nYou: ")

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            try:
                # Get response from agent with tracing and session context
                response = chat_with_agent(agent, user_input, session_id=session_id, user_id=user_id)
                print(f"Assistant: {response}")

            except Exception as e:
                print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("\nMake sure your .env file is configured correctly!")

    finally:
        # Cleanup: shutdown Arthur client to flush any pending spans
        if arthur:
            print("\n🔄 Flushing traces...")
            arthur.shutdown()
            print("✅ Traces flushed. Exiting.")

if __name__ == "__main__":
    main()
