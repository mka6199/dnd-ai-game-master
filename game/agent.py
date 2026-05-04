"""ReAct-style agent loop for the DnD AI Game Master.

Implements multi-step reasoning: the LLM may plan, call tools, observe their
results, reason again, and finally respond. This module is the heart of the
"Planning & Reasoning" rubric section.

Reasoning trace
---------------
For complex scenarios the agent emits an explicit chain-of-thought "DM Thought"
string before tool calls so we can display its reasoning in the UI. This is
controlled by `enable_reasoning_trace=True`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from game.llm import chat
from game.prompts import (
    DM_SYSTEM_PROMPT, COMBAT_PROMPT, TAVERN_PROMPT, DUNGEON_PROMPT,
    SKILL_CHECK_PROMPT, PLANNER_PROMPT,
)
from game.tools import TOOL_SCHEMAS, parse_tool_args


SCENARIO_TO_PROMPT = {
    "narration": DM_SYSTEM_PROMPT,
    "combat": DM_SYSTEM_PROMPT + "\n\n" + COMBAT_PROMPT,
    "tavern": DM_SYSTEM_PROMPT + "\n\n" + TAVERN_PROMPT,
    "dungeon": DM_SYSTEM_PROMPT + "\n\n" + DUNGEON_PROMPT,
    "skill_check": DM_SYSTEM_PROMPT + "\n\n" + SKILL_CHECK_PROMPT,
}


@dataclass
class TurnResult:
    """The agent's response after one player turn."""
    narration: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # [{name, args, result}]
    reasoning: str = ""  # chain-of-thought trace (optional)
    raw_messages: list[dict] = field(default_factory=list)


def _serialize_tool_call(tc) -> dict:
    return {
        "id": tc.id,
        "name": tc.function.name,
        "arguments_json": tc.function.arguments,
    }


def run_turn(
    history: list[dict],
    user_message: str,
    scenario: str,
    tool_executor: Callable[[str, dict], dict],
    enable_reasoning_trace: bool = False,
    max_iterations: int = 6,
) -> TurnResult:
    """Run one full ReAct turn: reason -> tool calls -> observe -> respond.

    Args:
        history: Prior conversation history (list of OpenAI-style messages)
        user_message: The new player input
        scenario: One of SCENARIO_TO_PROMPT keys
        tool_executor: Function that executes a tool by name with args dict
        enable_reasoning_trace: If True, do a planning pass first (chain-of-thought)
        max_iterations: Cap on tool-call/response loop iterations

    Returns:
        TurnResult with narration, tool calls, and reasoning trace.
    """
    system = SCENARIO_TO_PROMPT.get(scenario, DM_SYSTEM_PROMPT)
    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    result = TurnResult()

    # ------- Optional planning pass (chain-of-thought) -------
    if enable_reasoning_trace:
        plan_msgs = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": (
                f"Scenario: {scenario}\nPlayer says: {user_message}\n\n"
                "Produce a concise THOUGHT/PLAN/TOOL trace using this exact format:\n"
                "THOUGHT: <one sentence about the situation>\n"
                "PLAN:\n  1. <step>\n  2. <step>\n  3. <step>\n"
                "TOOL: <which tool first and why>\n\n"
                "Output ONLY the trace. Do not narrate."
            )},
        ]
        plan_response = chat(plan_msgs, scenario="planning")
        result.reasoning = (plan_response.content or "").strip() or "_(planner returned empty)_"

    # ------- ReAct loop: tool calls until model is done -------
    for _ in range(max_iterations):
        response = chat(messages, scenario=scenario, tools=TOOL_SCHEMAS)

        # Append assistant's response to messages so it sees its own tool calls
        assistant_msg: dict = {"role": "assistant"}
        if response.content:
            assistant_msg["content"] = response.content
        if response.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.tool_calls
            ]
        messages.append(assistant_msg)

        # No tool calls? We're done.
        if not response.tool_calls:
            result.narration = response.content or ""
            break

        # Execute each tool call and append results
        for tc in response.tool_calls:
            args = parse_tool_args(tc.function.arguments)
            tool_result = tool_executor(tc.function.name, args)
            result.tool_calls.append({
                "name": tc.function.name,
                "args": args,
                "result": tool_result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result, default=str),
            })
    else:
        # Hit iteration cap without natural stop
        result.narration = (response.content or "*The DM pauses, gathering their thoughts...*")

    result.raw_messages = messages
    return result
