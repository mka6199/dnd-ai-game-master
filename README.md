# 🐉 DnD AI Game Master

An AI-powered Dungeons & Dragons 5e Dungeon Master built with OpenAI,
ChromaDB (RAG), Streamlit, and DALL-E 3.

> **Final project for AI Methods.** See [Project.md](Project.md) for the full
> rubric report covering scenarios, prompt engineering, tools, planning,
> RAG, innovation, and code quality.

## Features

- **Streamlit chat UI** with scenario selector (tavern / dungeon / combat / skill check / free narration)
- **Function-calling tools**: dice rolling, inventory management, lore retrieval, rules lookup
- **ReAct-style agent loop** with optional chain-of-thought DM Thoughts
- **RAG**: ChromaDB vector store seeded with world lore, monster stats, and rules
- **Persistent memory**: the DM remembers what your party has done
- **AI-generated NPC portraits & dungeon maps** via DALL-E 3
- **Voiced narration** via gTTS

## Quick Start

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Add your OpenAI API key
Copy-Item .env.example .env
# edit .env and paste your key

# 3. Run
streamlit run app.py
```

## Project Structure

```
app.py              Streamlit UI entry point
game/               Core game package
  llm.py             OpenAI client wrapper
  prompts.py         All system prompts + per-scenario parameters
  tools.py           Function-calling schemas + executors
  agent.py           ReAct multi-step reasoning loop
  rag.py             ChromaDB lore store
  innovation.py      TTS + image generation
  inventory.py       Inventory data structure
  roll_dice.py       Dice notation roller
data/lore/          Seed lore .txt files
Project.md          Final project report
Lab 14.md           Lab 14 submission
*.drawio            UML use case diagrams
```

## Use Case Diagrams

See `Diagram1_Core_Elements.drawio.png` and `Diagram2_Relationships.drawio.png`.
