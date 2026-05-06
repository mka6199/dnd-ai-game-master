# 🐉 DnD AI Game Master

An AI-powered Dungeons & Dragons 5e Dungeon Master built with Streamlit,
ChromaDB (RAG), and your choice of LLM provider — **OpenAI** (cloud, paid)
or **Ollama** (local, free).

> **Final project for AI Methods.** See [Project.md](Project.md) for the full
> rubric report covering scenarios, prompt engineering, tools, planning,
> RAG, innovation, and code quality.

## Features

- **Dual LLM backend** — switch between OpenAI (`gpt-4o-mini`) and Ollama (`llama3.1`) via one env var
- **Streamlit chat UI** with scenario selector (tavern / dungeon / combat / skill check / free narration)
- **Function-calling tools**: dice rolling, inventory management, lore retrieval, rules lookup
- **ReAct-style agent loop** with optional chain-of-thought DM Thoughts
- **RAG**: ChromaDB vector store seeded with world lore, monster stats, and rules
- **Persistent memory**: the DM remembers what your party has done
- **AI-generated NPC portraits & dungeon maps** via DALL-E 3 *(OpenAI mode only)*
- **Voiced narration** via gTTS *(free, both modes)*

## Quick Start

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Configure provider
Copy-Item .env.example .env
# edit .env -> set LLM_PROVIDER=openai (and add OPENAI_API_KEY)
#           OR set LLM_PROVIDER=ollama (free, no key needed)

# 3. Run
python -m streamlit run app.py
```

### Option A — OpenAI (cloud)

In `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### Option B — Ollama (free, local, no API key)

1. Install Ollama from https://ollama.com
2. Pull a tool-capable chat model and an embedding model:
   ```powershell
   ollama pull llama3.1
   ollama pull nomic-embed-text
   ```
3. In `.env`:
   ```
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.1
   OLLAMA_EMBED_MODEL=nomic-embed-text
   ```

> Notes on Ollama mode: Image generation (DALL-E) is automatically disabled.
> Tool-calling quality is lower than `gpt-4o-mini` — `llama3.1` and `qwen2.5`
> work best. The two providers use separate Chroma collections, so you can
> switch back and forth without rebuilding indexes.

## Project Structure

```
app.py              Streamlit UI entry point
game/               Core game package
  llm.py             Provider-aware LLM wrapper (OpenAI + Ollama)
  prompts.py         All system prompts + per-scenario parameters
  tools.py           Function-calling schemas + executors
  agent.py           ReAct multi-step reasoning loop
  rag.py             ChromaDB lore store (provider-aware embeddings)
  innovation.py      TTS + image generation
  inventory.py       Inventory data structure
  roll_dice.py       Dice notation roller
data/lore/          Seed lore .txt files
Project.md          Final project report
```
