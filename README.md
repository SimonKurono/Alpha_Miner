# Google AI Agents

This repository contains a collection of AI agents built using the Google Agent Development Kit (ADK) and Gemini 2.x models. Each module demonstrates specific architectural patterns and capabilities for building sophisticated agentic workflows.

## Core Technologies
- **Google ADK**: A framework for building multi-agent systems with built-in support for tool use, loops, and sequential workflows.
- **Gemini 2.x Models**: Leveraging latest generative models for reasoning and tool orchestration.
- **Python-based agents**: All agents are implemented in Python with extensibility in mind.

## Agent Modules

### [Blog Post Agent](./blog_post_agent/)
Implements an iterative refinement workflow. It uses a **LoopAgent** where a **CriticAgent** provides feedback on initial drafts, and a **RefinerAgent** incorporates that feedback until the content is approved.

### [Currency Agent](./currency_agent/)
Demonstrates agent-to-agent delegation. An orchestration agent uses a specialized **CalculationAgent** (configured with a code executor) as a tool to perform precise arithmetic, while fetching real-time data via functional tools.

### [E-commerce Agent](./ecommerce_agent/)
Showcases remote agent interaction using the **Agent-to-Agent (A2A)** protocol. A root agent delegates product-specific queries to a remote catalog agent served via a web API.

### [Image Gen Agent](./image_gen_agent/)
Features integration with the **Model Context Protocol (MCP)**. It uses an external MCP server to generate images based on natural language prompts.

### [Research Agent](./research_agent/)
Focuses on observability and platform extensibility. It utilizes **Plugins** for comprehensive logging and monitoring of agent execution flows.

### [Stateful Agent](./stateful_agent/)
Implements session management and persistent memory. It uses a **DatabaseSessionService** with SQLite to maintain conversation history across different user sessions.

## Project Structure
- `blog_post_agent/`: Sequential and loop agent implementations.
- `currency_agent/`: Tool use and sub-agent delegation.
- `ecommerce_agent/`: Remote agent communication (A2A).
- `image_gen_agent/`: MCP tool integration.
- `research_agent/`: Logging and observability plugins.
- `stateful_agent/`: Persistence and session management.
- `observability.ipynb`: Interactive notebook for exploring agent logs.
- `requirements.txt`: Project dependencies including Google Cloud and GenAI libraries.

## Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in a `.env` file:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```
