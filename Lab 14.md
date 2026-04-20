# Lab 14: Project Feature Submission

## Project: DnD AI Game Master

## Use Case Diagram

The Use Case Diagram for the DnD AI Game Master system is included in this repository:

- **Diagram 1 - Core Elements:** `Diagram1_Core_Elements.drawio` — Shows all actors (Player, LLM API, Vector Database, Image Generation Service, TTS Service), 17 use cases inside the system boundary, and association lines.
- **Diagram 2 - Relationships:** `Diagram2_Relationships.drawio` — Shows `<<include>>` and `<<extend>>` relationships between use cases.

## Completed Use Case: Roll Dice

The **Roll Dice** use case has been implemented in `roll_dice.py`.

### Description

The Roll Dice feature allows the player to roll standard DnD dice using standard notation (e.g., `2d6`, `1d20+5`, `3d8-2`). It supports:

- All standard DnD dice types: d4, d6, d8, d10, d12, d20, d100
- Multiple dice rolls (e.g., `4d6`)
- Modifiers (e.g., `1d20+5` for attack rolls with bonuses)
- Ability score generation using the 4d6-drop-lowest method

### How to Run

```bash
python roll_dice.py
```

### Relationship to Use Case Diagram

In the Use Case Diagram, **Roll Dice** is an `<<include>>` relationship from several use cases:

- **Engage in Combat** `<<include>>` Roll Dice — Combat requires dice rolls for attacks and saves
- **Attempt Skill Check** `<<include>>` Roll Dice — Skill checks require a d20 roll
- **Calculate Damage** `<<include>>` Roll Dice — Damage calculation requires rolling damage dice
