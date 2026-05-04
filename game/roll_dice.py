"""
DnD AI Game Master - Roll Dice Feature
Implements the 'Roll Dice' use case from the Project Use Case Diagram.
Supports standard DnD dice: d4, d6, d8, d10, d12, d20, d100
"""

import random
import re


def roll_dice(notation: str) -> dict:
    """Roll dice using standard DnD notation (e.g., '2d6', '1d20+5', '3d8-2').

    Args:
        notation: Dice notation string like '2d6', '1d20+5', '4d6-1'

    Returns:
        Dictionary with rolls, total, and notation used.
    """
    notation = notation.strip().lower()
    pattern = r'^(\d+)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, notation)

    if not match:
        raise ValueError(f"Invalid dice notation: '{notation}'. Use format like '2d6' or '1d20+5'.")

    num_dice = int(match.group(1))
    die_faces = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num_dice < 1 or num_dice > 100:
        raise ValueError("Number of dice must be between 1 and 100.")
    if die_faces not in (4, 6, 8, 10, 12, 20, 100):
        raise ValueError(f"Invalid die type: d{die_faces}. Use d4, d6, d8, d10, d12, d20, or d100.")

    rolls = [random.randint(1, die_faces) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
    }


def roll_ability_scores() -> list:
    """Roll ability scores using the standard 4d6-drop-lowest method.

    Returns:
        List of 6 ability scores.
    """
    scores = []
    for _ in range(6):
        rolls = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)
        scores.append(sum(rolls[:3]))
    return scores


def main():
    print("=== DnD AI Game Master - Dice Roller ===\n")

    while True:
        user_input = input("Enter dice notation (e.g., 2d6, 1d20+5) or 'ability' for scores, 'quit' to exit: ").strip()

        if user_input.lower() == 'quit':
            print("Farewell, adventurer!")
            break

        if user_input.lower() == 'ability':
            scores = roll_ability_scores()
            print(f"\nAbility Scores (4d6 drop lowest): {scores}")
            print(f"Total: {sum(scores)}\n")
            continue

        try:
            result = roll_dice(user_input)
            print(f"\nRolling {result['notation']}...")
            print(f"  Rolls: {result['rolls']}")
            if result['modifier'] != 0:
                sign = '+' if result['modifier'] > 0 else ''
                print(f"  Modifier: {sign}{result['modifier']}")
            print(f"  Total: {result['total']}\n")
        except ValueError as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
