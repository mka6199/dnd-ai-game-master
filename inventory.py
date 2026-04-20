"""
DnD AI Game Master - Manage Inventory Feature
Implements the 'Manage Inventory' use case from the Project Use Case Diagram.
"""


class Inventory:
    """Manages a player's inventory of items."""

    def __init__(self):
        self.items = {}

    def add_item(self, item_name: str, quantity: int = 1) -> str:
        item_name = item_name.strip()
        if not item_name:
            raise ValueError("Item name cannot be empty.")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        if item_name in self.items:
            self.items[item_name] += quantity
        else:
            self.items[item_name] = quantity

        return f"Added {quantity}x {item_name}. (Total: {self.items[item_name]})"

    def remove_item(self, item_name: str, quantity: int = 1) -> str:
        item_name = item_name.strip()
        if item_name not in self.items:
            raise ValueError(f"'{item_name}' not found in inventory.")
        if quantity > self.items[item_name]:
            raise ValueError(f"Only have {self.items[item_name]}x {item_name}.")

        self.items[item_name] -= quantity
        if self.items[item_name] == 0:
            del self.items[item_name]
            return f"Removed all {item_name} from inventory."
        return f"Removed {quantity}x {item_name}. (Remaining: {self.items[item_name]})"

    def view(self) -> str:
        if not self.items:
            return "Inventory is empty."
        lines = ["=== Inventory ==="]
        for item, qty in self.items.items():
            lines.append(f"  {item} x{qty}")
        lines.append(f"  ({len(self.items)} item type(s))")
        return "\n".join(lines)


def main():
    print("=== DnD AI Game Master - Inventory Manager ===\n")
    inv = Inventory()

    while True:
        cmd = input("Command (add/remove/view/quit): ").strip().lower()

        if cmd == "quit":
            print("Farewell, adventurer!")
            break
        elif cmd == "view":
            print(f"\n{inv.view()}\n")
        elif cmd == "add":
            name = input("  Item name: ").strip()
            qty = input("  Quantity (default 1): ").strip()
            qty = int(qty) if qty else 1
            try:
                print(f"  {inv.add_item(name, qty)}\n")
            except ValueError as e:
                print(f"  Error: {e}\n")
        elif cmd == "remove":
            name = input("  Item name: ").strip()
            qty = input("  Quantity (default 1): ").strip()
            qty = int(qty) if qty else 1
            try:
                print(f"  {inv.remove_item(name, qty)}\n")
            except ValueError as e:
                print(f"  Error: {e}\n")
        else:
            print("  Unknown command. Use add, remove, view, or quit.\n")


if __name__ == "__main__":
    main()
