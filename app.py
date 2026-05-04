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

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY not found. Add it to .env")
        st.stop()

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
