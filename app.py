"""Streamlit UI for the DnD AI Game Master.

Run with:
    streamlit run app.py

Features demonstrated in the UI:
- Scenario selector (tavern, dungeon, combat, skill check, free narration)
- Chain-of-thought reasoning toggle (Planning & Reasoning)
- Tool call inspector (shows when LLM rolls dice / queries lore / etc.)
- RAG-backed lore retrieval
- TTS narration of any DM response
- DALL-E NPC portrait generation
- Persistent inventory & memory (RAG remembers past events)
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from game.agent import run_turn
from game.inventory import Inventory
from game.innovation import (
    generate_npc_portrait,
    generate_dungeon_map,
    synthesize_speech,
)
from game.llm import get_provider, get_model, reset_client
from game.rag import LoreStore, seed_from_directory
from game.tools import build_executor

load_dotenv()

st.set_page_config(page_title="DnD AI Game Master", page_icon="🐉", layout="wide")


# -------------------- Session state init --------------------
def init_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "inventory" not in st.session_state:
        st.session_state.inventory = Inventory()
        # Starter kit
        st.session_state.inventory.add_item("Health Potion", 2)
        st.session_state.inventory.add_item("Torch", 3)
        st.session_state.inventory.add_item("Gold", 25)
    if "lore_store" not in st.session_state:
        try:
            store = LoreStore()
            n = seed_from_directory(store)
            st.session_state.lore_store = store
            st.session_state.lore_seeded = n
        except Exception as e:
            st.session_state.lore_store = None
            st.session_state.lore_error = str(e)
    if "tool_log" not in st.session_state:
        st.session_state.tool_log = []


init_state()


# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("⚔️ DM Controls")

    # ---- Provider & model picker (overrides .env at runtime) ----
    st.subheader("🤖 Model")
    env_provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    provider_options = ["openai", "ollama"]
    provider_choice = st.selectbox(
        "Provider",
        provider_options,
        index=provider_options.index(env_provider) if env_provider in provider_options else 0,
        help="OpenAI = paid cloud. Ollama = free local (requires `ollama serve`).",
    )

    if provider_choice == "openai":
        openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-3.5-turbo"]
        default_openai = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if default_openai not in openai_models:
            openai_models.insert(0, default_openai)
        model_choice = st.selectbox(
            "OpenAI model",
            openai_models,
            index=openai_models.index(default_openai),
        )
        os.environ["OPENAI_MODEL"] = model_choice
    else:
        ollama_models = ["llama3.1", "llama3.2", "qwen2.5", "mistral-nemo", "phi3"]
        default_ollama = os.getenv("OLLAMA_MODEL", "llama3.1")
        if default_ollama not in ollama_models:
            ollama_models.insert(0, default_ollama)
        model_choice = st.selectbox(
            "Ollama model",
            ollama_models,
            index=ollama_models.index(default_ollama),
            help="Must be pulled locally first: `ollama pull <model>`",
        )
        os.environ["OLLAMA_MODEL"] = model_choice

    # If the user changed the provider this run, refresh the cached client.
    if st.session_state.get("_active_provider") != provider_choice:
        os.environ["LLM_PROVIDER"] = provider_choice
        reset_client()
        # Force the lore store to be rebuilt against the new embedding backend.
        st.session_state.pop("lore_store", None)
        st.session_state.pop("lore_seeded", None)
        st.session_state.pop("lore_error", None)
        try:
            store = LoreStore()
            n = seed_from_directory(store)
            st.session_state.lore_store = store
            st.session_state.lore_seeded = n
        except Exception as e:
            st.session_state.lore_store = None
            st.session_state.lore_error = str(e)
        st.session_state["_active_provider"] = provider_choice

    provider = get_provider()
    st.caption(f"Active: `{provider}` / `{get_model()}`")

    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        st.error(
            "OPENAI_API_KEY not found. Add it to .env, "
            "or switch the provider above to `ollama`."
        )
        st.stop()

    st.divider()

    scenario = st.selectbox(
        "Scenario",
        ["narration", "tavern", "dungeon", "combat", "skill_check"],
        index=0,
        help="Selects which system prompt + parameters the LLM uses.",
    )

    enable_reasoning = st.checkbox(
        "Show DM Thoughts (chain-of-thought)",
        value=False,
        help="Adds an explicit planning pass before each response.",
    )

    st.divider()
    st.subheader("📦 Inventory")
    inv_view = st.session_state.inventory.view()
    st.code(inv_view, language=None)

    st.divider()
    st.subheader("📚 Lore Database (RAG)")
    if st.session_state.get("lore_store"):
        st.write(f"Documents indexed: **{st.session_state.lore_store.count()}**")
        if st.session_state.get("lore_seeded", 0) > 0:
            st.caption(f"Seeded {st.session_state.lore_seeded} files this session.")
    else:
        st.warning(f"RAG offline: {st.session_state.get('lore_error', 'unknown')}")

    st.divider()
    st.subheader("🎨 Innovation")
    if provider != "openai":
        st.warning(
            "🖼️ Image generation is unavailable in **Ollama** mode "
            "(no local image model is bundled). Switch the provider above to "
            "**openai** to generate NPC portraits and dungeon maps."
        )
    else:
        npc_desc = st.text_input("NPC description", placeholder="grizzled half-orc innkeeper")
        if st.button("Generate NPC Portrait") and npc_desc:
            with st.spinner("Conjuring portrait..."):
                try:
                    url = generate_npc_portrait(npc_desc)
                    st.session_state.last_image_url = url
                    st.session_state.last_image_caption = npc_desc
                except Exception as e:
                    st.error(f"Image gen failed: {e}")

        map_desc = st.text_input("Map description", placeholder="moss-covered crypt entrance")
        if st.button("Generate Map") and map_desc:
            with st.spinner("Drawing map..."):
                try:
                    url = generate_dungeon_map(map_desc)
                    st.session_state.last_image_url = url
                    st.session_state.last_image_caption = f"Map: {map_desc}"
                except Exception as e:
                    st.error(f"Map gen failed: {e}")

    st.divider()
    if st.button("🔄 New Adventure (clear history)"):
        st.session_state.history = []
        st.session_state.tool_log = []
        st.rerun()


# -------------------- Main column --------------------
st.title("🐉 DnD AI Game Master")
st.caption("AI-powered Dungeon Master with RAG, tools, and multi-step reasoning")

if st.session_state.get("last_image_url"):
    st.image(
        st.session_state.last_image_url,
        caption=st.session_state.get("last_image_caption", ""),
        use_container_width=True,
    )

# Render conversation
for idx, entry in enumerate(st.session_state.history):
    if entry["role"] in ("user", "assistant"):
        with st.chat_message(entry["role"]):
            if entry["role"] == "assistant":
                if entry.get("reasoning"):
                    with st.expander("🧠 DM Thoughts (chain-of-thought)"):
                        st.markdown(entry["reasoning"])
                if entry.get("tool_calls"):
                    with st.expander(f"🛠️ Tools used ({len(entry['tool_calls'])})"):
                        for tc in entry["tool_calls"]:
                            st.markdown(f"**{tc['name']}**")
                            st.json({"args": tc["args"], "result": tc["result"]})
            st.markdown(entry["content"])
            if entry["role"] == "assistant":
                tts_key = f"tts-btn-{idx}"
                audio_key = f"tts-audio-{idx}"
                if st.button("🔊 Voice this narration", key=tts_key):
                    with st.spinner("Generating audio..."):
                        try:
                            audio_path = synthesize_speech(entry["content"])
                            st.session_state[audio_key] = audio_path
                        except Exception as e:
                            st.error(f"TTS failed: {e}")
                if st.session_state.get(audio_key):
                    st.audio(st.session_state[audio_key])

# Chat input
user_input = st.chat_input("What do you do?")

if user_input:
    executor = build_executor(
        st.session_state.inventory,
        st.session_state.lore_store,
    )

    with st.spinner("The DM consults the threads of fate..."):
        # Pass only role+content to the LLM (it doesn't need our UI metadata)
        clean_history = [
            {"role": e["role"], "content": e["content"]}
            for e in st.session_state.history
            if e["role"] in ("user", "assistant")
        ]
        result = run_turn(
            history=clean_history,
            user_message=user_input,
            scenario=scenario,
            tool_executor=executor,
            enable_reasoning_trace=enable_reasoning,
        )

    if result.tool_calls:
        st.session_state.tool_log.extend(result.tool_calls)

    # Persist turn (with reasoning + tool calls so they survive reruns)
    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.history.append({
        "role": "assistant",
        "content": result.narration,
        "reasoning": result.reasoning,
        "tool_calls": result.tool_calls,
    })

    # Save a memory snippet to the RAG so future turns can recall it
    if st.session_state.lore_store and len(st.session_state.history) % 4 == 0:
        try:
            recent = " ".join(
                e["content"] for e in st.session_state.history[-4:]
            )[:500]
            st.session_state.lore_store.remember(
                f"Recent player events: {recent}",
                tag="history",
            )
        except Exception:
            pass

    st.rerun()
