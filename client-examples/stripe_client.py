"""
Setup:

    uv pip install langchain==0.3.21 langchain-mcp-adapters==0.0.5 langchain-openai==0.3.10

    export OPENAI_API_KEY=<your-openai-api-key>

Put this in your `servers.yaml` file:

```
servers:
  - namespace: stripe
    # Forward the Authorization header to the Stripe API
    forward_headers:
      - Authorization
    name: Stripe API
    url: https://raw.githubusercontent.com/stripe/openapi/refs/heads/master/openapi/spec3.yaml
    base_url: https://api.stripe.com
    # Select which API paths to expose over MCP. Each matching path will become a tool with arguments
    # from the query parameters or the JSON body.
    # For example, we're only exposing the endpoints to GET/POST a customer.
    paths:
      - /v1/customers$
```

Run the server (if not already running):

    uv run main.py

Finally, run the example:

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


async def run_agent(settings: dict[str, str]):
    async with MultiServerMCPClient(
        {
            "weather": {
                "url": "http://localhost:8000/stripe/sse",
                "transport": "sse",
                # Add a custom header to the request that can be forwarded to the OpenAPI endpoint.
                "headers": {
                    "Authorization": f"Bearer {settings.get('STRIPE_API_KEY')}",
                },
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
        print("Welcome to the Stripe Customer API!\nTry prompts like:")
        print(
            ' - Create a customer with name "Test Customer" and email "test@example.com"'
        )
        print(
            " - Show me all the customer names (this will return a list of customer names)"
        )
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
    asyncio.run(run_agent({"STRIPE_API_KEY": os.environ.get("STRIPE_API_KEY")}))
