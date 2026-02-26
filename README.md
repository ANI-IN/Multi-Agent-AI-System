---
title: Multi-Agent Customer Support Demo
emoji: 🎵
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.12.0
app_file: app.py
pinned: false
license: mit
---

# 🎵 Multi-Agent Customer Support Demo

An AI-powered customer support system for a digital music store, built with **LangGraph** multi-agent orchestration.

## Features

- **Customer Identity Verification** — Human-in-the-loop verification via ID, email, or phone
- **Supervisor-Based Routing** — Intelligent query routing to specialized sub-agents
- **Music Catalog Agent** — Search albums, tracks, artists, and genres
- **Invoice Information Agent** — Retrieve purchase history, billing details, employee info
- **Long-Term Memory** — Saves and recalls user music preferences across conversations

## Architecture

```
User Query → Verify Identity → Load Memory → Supervisor → [Music Agent | Invoice Agent] → Save Memory → Response
```

## Setup

Set the following secrets in your Hugging Face Space settings:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) |
| `OPENAI_API_BASE` | Custom API base URL (optional, for compatible providers) |
| `MODEL_NAME` | Model name (default: `gpt-4o-mini`) |

## Sample Queries

- "My customer ID is 1. What was my most recent purchase?"
- "What albums do you have by the Rolling Stones?"
- "My phone number is +55 (12) 3923-5555. How much was my most recent invoice?"
- "What songs do you have in the Jazz genre?"

## Built With

- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) — LLM framework
- [Gradio](https://gradio.app/) — Web UI
- [Chinook Database](https://www.sqlitetutorial.net/sqlite-sample-database/) — Sample music store data
