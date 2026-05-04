"""Tool/function-calling definitions for the LLM.

Each tool has a JSON schema (sent to the model) and an executor (Python
function that runs when the model invokes the tool). The agent loop
dispatches tool calls back to these executors.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from game.roll_dice import roll_dice as _roll_dice
from game.inventory import Inventory


# ---------- Tool schemas (sent to OpenAI) ----------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": (
                "Roll D&D dice using standard notation. Use for ALL dice rolls: "
                "attack rolls (1d20+mod), damage (e.g. 1d8+3), saves, skill checks, ability rolls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "notation": {
                        "type": "string",
                        "description": "Dice notation, e.g. '1d20+5', '2d6', '4d6-1'",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this roll is being made (e.g. 'Goblin attack roll')",
                    },
                },
                "required": ["notation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_inventory",
            "description": "Add, remove, or view items in the player's inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "view"],
                    },
                    "item": {"type": "string", "description": "Item name (omit for view)"},
                    "quantity": {"type": "integer", "minimum": 1, "default": 1},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_lore",
            "description": (
                "Search the campaign lore database (RAG) for relevant world info, "
                "NPC backstory, location details, monster lore, or past player history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to retrieve",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_rules",
            "description": "Look up a D&D 5e rule, spell, condition, or ability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "What rule/spell/condition to look up",
                    },
                },
                "required": ["topic"],
            },
        },
    },
]


# ---------- Tool executors ----------

def _exec_roll_dice(notation: str, reason: str = "") -> dict:
    result = _roll_dice(notation)
    if reason:
        result["reason"] = reason
    return result


def _exec_manage_inventory(state_inventory: Inventory, action: str, item: str = "", quantity: int = 1) -> dict:
    try:
        if action == "view":
            return {"items": dict(state_inventory.items), "view": state_inventory.view()}
        elif action == "add":
            msg = state_inventory.add_item(item, quantity)
            return {"success": True, "message": msg, "items": dict(state_inventory.items)}
        elif action == "remove":
            msg = state_inventory.remove_item(item, quantity)
            return {"success": True, "message": msg, "items": dict(state_inventory.items)}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    except ValueError as e:
        return {"success": False, "error": str(e)}


def _exec_query_lore(rag_store, query: str, k: int = 3) -> dict:
    """Use RAG to retrieve lore. rag_store is a LoreStore instance."""
    results = rag_store.query(query, k=k)
    return {"query": query, "results": results}


def _exec_lookup_rules(rag_store, topic: str) -> dict:
    """Rules live in the same vector store, but with a 'rules' filter."""
    results = rag_store.query(topic, k=2, category_filter="rules")
    return {"topic": topic, "results": results}


def build_executor(state_inventory: Inventory, rag_store) -> Callable[[str, dict], Any]:
    """Build a single dispatch function bound to the current game state.

    Returns a callable: executor(tool_name, args_dict) -> result_dict
    """
    def executor(tool_name: str, args: dict) -> Any:
        if tool_name == "roll_dice":
            return _exec_roll_dice(**args)
        if tool_name == "manage_inventory":
            return _exec_manage_inventory(state_inventory, **args)
        if tool_name == "query_lore":
            return _exec_query_lore(rag_store, **args)
        if tool_name == "lookup_rules":
            return _exec_lookup_rules(rag_store, **args)
        return {"error": f"Unknown tool: {tool_name}"}

    return executor


def parse_tool_args(arguments_json: str) -> dict:
    """Safely parse tool call arguments JSON from the model."""
    try:
        return json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError):
        return {}
