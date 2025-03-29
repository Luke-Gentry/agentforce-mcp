"""
Setup:

    uv pip install langchain==0.3.21 langchain-mcp-adapters==0.0.5 langchain-openai==0.3.10

    export OPENAI_API_KEY=<your-openai-api-key>

Put this in your `servers.yaml` file:

```
servers:
- namespace: httpbin
    name: httpbin
    url: file://test-specs/httpbin.yaml
    base_url: https://httpbin.org
    paths:
    - /get
    - /status
    - /ip
    - /headers
    - /user-agent

- namespace: weather
    name: Open Meteo API
    url: https://raw.githubusercontent.com/open-meteo/open-meteo/refs/heads/main/openapi.yml
    base_url: https://api.open-meteo.com
    # Forward the API key from the client's query parameters
    paths:
    - /v1/forecast$
```

Run it with:

    uv run examples/langchain_client.py
"""

import asyncio
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable must be set")


async def main():
    async with MultiServerMCPClient(
        {
            "weather": {
                "url": "http://localhost:8000/weather/sse",
                "transport": "sse",
            },
            "httpbin": {
                "url": "http://localhost:8000/httpbin/sse",
                "transport": "sse",
            },
        }
    ) as client:
        tools = client.get_tools()
        # Initialize the chat model
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant that can use various tools to help users. "
                    "Always explain what you're doing and why you're using specific tools.",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        chat_history = []
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() == "exit":
                    break
                response = await agent_executor.ainvoke(
                    {"input": user_input, "chat_history": chat_history}
                )
                print("\nAssistant:", response["output"])
                chat_history.extend(
                    [
                        HumanMessage(content=user_input),
                        AIMessage(content=response["output"]),
                    ]
                )

            except KeyboardInterrupt:
                print("\nChat session terminated by user")
                break


if __name__ == "__main__":
    asyncio.run(main())
