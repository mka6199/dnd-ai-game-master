# Project Report — DnD AI Game Master

**Author:** Mka6199
**Course:** AI Methods Final Project
**Repo:** https://github.com/mka6199/dnd-ai-game-master

---

## 1. Base System Functionality

The DnD AI Game Master is a Streamlit web application that lets a single
player run a Dungeons & Dragons 5e adventure with an AI Dungeon Master.
The DM is powered by an OpenAI chat model, augmented with retrieval over a
ChromaDB lore database and a suite of function-calling tools.

### Scenarios the system can handle

The system can manage all of the following scenario types end-to-end:

1. **Free narration** — open-ended descriptive storytelling with the DM voice.
2. **Tavern social encounters** — distinct NPCs (Borin the dwarven barkeep,
   Old Wick the bard, Captain Vex the recruiter) with consistent personalities
   pulled from the lore store.
3. **Dungeon exploration** — atmospheric room descriptions, hidden traps,
   pulled from the canonical "Sunken Crypt" lore document.
4. **Combat resolution** — automated attack rolls, damage rolls, condition
   tracking, and monster stat retrieval (e.g. Goblin, Giant Spider).
5. **Skill checks** — Stealth, Persuasion, Investigation, etc. with proper
   DC selection and 1d20 rolls via the `roll_dice` tool.
6. **Multi-stage puzzles** — the Library of Bones gemstone-plinth puzzle is
   resolved with multi-step reasoning + lore retrieval.
7. **NPC interactions** — merchant bargaining and deceptive characters.
8. **Inventory management** — items added/removed by the DM via tool calls.
9. **Quest progress / persistent memory** — every few turns the agent writes
   a summary memory back into the vector store, so future turns can recall
   "what the player did" via RAG.
10. **AI-generated NPC portraits and dungeon maps** — DALL-E 3.
11. **Voiced narration** — the player can convert any DM message to speech.

### Architecture overview

```
app.py                  Streamlit UI (entry point)
game/
  llm.py                Thin wrapper over OpenAI Chat / Image APIs
  prompts.py            All system prompts + per-scenario parameters
  tools.py              Function-calling schemas + executors
  agent.py              ReAct-style multi-step reasoning loop
  rag.py                ChromaDB lore + memory store
  innovation.py         gTTS narration + DALL-E image generation
  inventory.py          Inventory data structure
  roll_dice.py          Dice notation parser + roller
data/lore/*.txt         Seed lore documents for RAG
```

This satisfies **LO1** (AI concepts) by combining LLMs, RAG, tool use, and
agentic reasoning, **LO2** (Python ecosystem) by integrating OpenAI, Chroma,
gTTS, Streamlit, and **LO3** (modular design) through the `game/` package
that cleanly separates concerns.

---

## 2. Prompt Engineering and Model Parameter Choice

### System prompts

Each scenario uses a different system prompt, all defined in
[`game/prompts.py`](game/prompts.py).

| Prompt | Purpose | Highlights |
|---|---|---|
| `DM_SYSTEM_PROMPT` | Master persona prepended to every scenario | 2-4 paragraph cap, second-person voice, explicit tool-use instructions |
| `TAVERN_PROMPT` | Distinct NPC voices in social encounters | "Reference player history if available via query_lore" |
| `COMBAT_PROMPT` | Tactical, terse combat narration | "Always call roll_dice for attack rolls" |
| `DUNGEON_PROMPT` | Atmospheric dungeon descriptions | "Do not reveal trap mechanics until the player searches" |
| `SKILL_CHECK_PROMPT` | DC selection + cinematic resolution | Includes Easy=10, Medium=15, Hard=20 |
| `PLANNER_PROMPT` | Chain-of-thought reasoning | Forces THOUGHT/PLAN/TOOL trace |

The DM prompt explicitly tells the model to *never roll dice itself* and
*never modify inventory directly* — it must call the tools. This enforces
the agentic pattern and keeps the game's mechanics deterministic.

### Model parameters

Per-scenario parameters are defined in `prompts.PARAMETERS` and selected by
the LLM wrapper. Rationale:

| Scenario | Temperature | Max Tokens | Rationale |
|---|---:|---:|---|
| Tavern | 1.0 | 500 | Maximum NPC personality variance; varied accents and quirks |
| Narration | 0.9 | 600 | Creative, varied descriptive prose |
| Combat | 0.6 | 400 | Lower variance — players need tactical clarity |
| Planning | 0.4 | 500 | Focused, structured chain-of-thought |
| Rules | 0.1 | 300 | Near-deterministic — rules must be accurate |

Lower temperatures for combat and rules prevent hallucinated mechanics;
higher temperatures for tavern and narration keep storytelling fresh.

### Few-shot / role conditioning

The DM prompt is itself an extensive role-conditioning prompt. The
`PLANNER_PROMPT` further conditions the model into a structured
THOUGHT/PLAN/TOOL output format — a soft form of in-context learning
that produces the chain-of-thought trace shown in the UI when "Show DM
Thoughts" is enabled.

---

## 3. Tools Usage

The agent is equipped with four tools, defined in [`game/tools.py`](game/tools.py)
and invoked via OpenAI's function-calling API:

| Tool | Purpose | Backed by |
|---|---|---|
| `roll_dice` | Roll arbitrary dice notation (`2d6`, `1d20+5`, etc.) | `game/roll_dice.py` |
| `manage_inventory` | Add / remove / view items | `game/inventory.py` |
| `query_lore` | Semantic search over campaign lore | `game/rag.py` (ChromaDB) |
| `lookup_rules` | Filtered lore search restricted to rules docs | `game/rag.py` |

Each tool ships with a JSON schema that the model receives, so it can decide
*when* to call which tool based on the natural-language situation. The agent
loop in `agent.py` dispatches tool calls back to Python executors and feeds
the results back into the conversation, giving the model grounded outputs to
narrate from.

Example trace (from a combat turn):

```
Player: "I attack the goblin with my longsword."
→ LLM tool call: roll_dice(notation="1d20+5", reason="Longsword attack")
   ← {"rolls":[14], "modifier":5, "total":19}
→ LLM tool call: lookup_rules(topic="goblin AC")
   ← {"results":[{"text":"AC 15..."}]}
→ LLM tool call: roll_dice(notation="1d8+3", reason="Longsword damage")
   ← {"rolls":[6], "modifier":3, "total":9}
→ Final narration: "Your blade arcs..."
```

This satisfies LO1/LO2: the system identifies the right Python ecosystem
resources (OpenAI tools API, ChromaDB) and integrates them into a single
coherent agent.

---

## 4. Planning & Reasoning

`game/agent.py` implements a **ReAct-style multi-step loop**:

1. **(Optional) Plan pass** — when the user enables "Show DM Thoughts", the
   agent first runs a separate planning prompt (`PLANNER_PROMPT`) that
   produces a THOUGHT / PLAN / TOOL chain-of-thought trace. The trace is
   surfaced in the UI inside an expander.

2. **ReAct loop** — the model is allowed up to 6 iterations of:
   - Generate a response with `tools=...`
   - If `tool_calls` are present, execute them and append their results
     as `role="tool"` messages
   - Otherwise, finalize with the narration

This pattern lets the DM, in a single player turn, *decide* to:
look up monster stats → roll an attack → roll damage → look up a rule →
narrate the outcome. Each step builds on the previous observation.

Concrete example for a multi-stage scenario (Library of Bones puzzle):

1. Player: "I examine the three plinths."
2. Agent THOUGHT: "Player is investigating the puzzle. I should retrieve
   the puzzle's canonical solution from lore."
3. Agent calls `query_lore(query="Library of Bones plinth gemstones")`.
4. Result: docs describing the red/blue/green gemstones.
5. Agent calls `roll_dice("1d20+3")` for an Investigation check at DC 13.
6. Agent narrates the puzzle's appearance + drops a hint scaled to roll.

This satisfies LO1 by demonstrating chain-of-thought reasoning combined
with grounded tool use.

---

## 5. RAG Implementation

The project uses **ChromaDB** as a persistent vector store with OpenAI's
`text-embedding-3-small` embeddings. See [`game/rag.py`](game/rag.py).

### Data sources

Lore lives in `data/lore/*.txt`. Each filename is `<category>__<title>.txt`.
The `seed_from_directory` helper loads all files on first launch and indexes
them under the appropriate category metadata:

| Category | Examples |
|---|---|
| `world` | Whispering Vale geography & history |
| `locations` | The Drunken Griffin tavern, Sunken Crypt of Veshara |
| `monsters` | Goblin, Giant Spider — full 5e stat blocks |
| `rules` | Fireball spell, conditions, skill checks DCs |
| `history` | Auto-generated player memory summaries |

### How retrieval is wired in

- The `query_lore` and `lookup_rules` tools both call into the same store;
  `lookup_rules` adds a `where={"category":"rules"}` filter so the model
  cannot hallucinate game rules from a fictional NPC bio.
- After every 4 user/assistant exchanges, `app.py` writes a short summary
  back into the store under `category="history"`. This means the DM can
  later retrieve and reference what the party has done — directly addressing
  the "Recalling past player interactions" scenario from the rubric.

### Why this satisfies the rubric

It uses retrieval-augmented generation to maintain lore *and* context, the
data sources are integrated thoughtfully (separate categories per concern),
and it directly enables higher-quality scenarios (monster encounters,
location descriptions, rules adjudication).

---

## 6. Additional Tools / Innovation

Three creative add-ons live in [`game/llm.py`](game/llm.py) and
[`game/innovation.py`](game/innovation.py):

### Pluggable LLM backend (OpenAI **or** Ollama)
[`game/llm.py`](game/llm.py) abstracts the chat API behind a single
`chat()` function and selects the backend from the `LLM_PROVIDER` env
variable. Setting `LLM_PROVIDER=ollama` routes every request to a local
[Ollama](https://ollama.com) server through its OpenAI-compatible `/v1`
endpoint, which means tool/function calling, streaming, and the agent
loop all work unchanged — no API costs, no internet required. The RAG
layer in [`game/rag.py`](game/rag.py) mirrors the same switch and uses
`nomic-embed-text` locally instead of OpenAI embeddings (writing to a
separate Chroma collection so vector dimensions never collide). This
directly addresses the requirement that the project be runnable without
paid API access.

### Voiced AI narration (gTTS)
The player can click "🔊 Voice this narration" beside any DM response.
The system uses Google's free TTS engine to render the narration as MP3
and plays it inline in the Streamlit UI. This brings the "Voiced AI
narration for dramatic storytelling" scenario to life and costs nothing
extra at the API layer.

### NPC portraits & dungeon maps (DALL-E 3)
The sidebar offers "Generate NPC Portrait" and "Generate Map" with two
specialized prompt templates:
- Portraits: painterly digital art, head-and-shoulders framing.
- Maps: hand-drawn ink-and-watercolor top-down style.

Both implement the "AI-generated NPC or monster portraits" and "Dynamic
map generation" scenarios from the rubric.

---

## 7. Code Quality & Modular Design

- **Modularity**: All game logic is inside the `game/` Python package with
  one module per concern (LLM, prompts, tools, agent, RAG, innovation).
  `app.py` only handles UI and state.
- **Documentation**: Every module has a module-level docstring; every public
  function has type hints and a docstring.
- **Configuration**: All secrets via `.env` (with `.env.example` checked in,
  `.env` git-ignored). Model name is parameterized via `OPENAI_MODEL` /
  `OLLAMA_MODEL`, and the active backend is selected by `LLM_PROVIDER`
  (`openai` or `ollama`).
- **Reproducibility**: `requirements.txt` pins minimum versions of each
  dependency.
- **Version control**: The repository has incremental commits demonstrating
  evolution — Lab 14 baseline → multi-feature final system.
- **Defensive coding**: Tool executors return structured error dicts instead
  of raising; the agent's tool loop is iteration-capped to prevent
  infinite tool-call loops.

This satisfies LO2 (Python best practices) and LO3 (maintainable, modular
implementation).

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your provider
cp .env.example .env
# then edit .env:
#   LLM_PROVIDER=openai  -> add OPENAI_API_KEY (paid)
#   LLM_PROVIDER=ollama  -> install Ollama and `ollama pull llama3.1`

# 3. Launch the app
python -m streamlit run app.py
```

The first launch will seed ChromaDB from `data/lore/` automatically.
