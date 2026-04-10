"""Minimal LangChain agent — instrumentation fixture for Buzz E2E tests."""

import os

from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI


def run_agent(query: str) -> str:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
    )
    response = llm.invoke([HumanMessage(content=query)])
    return response.content


if __name__ == "__main__":
    result = run_agent("Hello, world!")
    print(result)
