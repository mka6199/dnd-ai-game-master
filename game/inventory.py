"""
DnD AI Game Master - Manage Inventory Feature
Implements the 'Manage Inventory' use case from the Project Use Case Diagram.
"""


class Inventory:
    """Manages a player's inventory of items."""

    def __init__(self):
        self.items = {}

    def _find_key(self, item_name: str):
        """Case-insensitive lookup of an existing inventory key."""
        target = item_name.strip().lower()
        for key in self.items:
            if key.lower() == target:
                return key
        return None

    def add_item(self, item_name: str, quantity: int = 1) -> str:
        item_name = item_name.strip()
        if not item_name:
            raise ValueError("Item name cannot be empty.")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        # Title-case new items for consistent display; merge with existing case-insensitive matches.
        existing = self._find_key(item_name)
        if existing:
            self.items[existing] += quantity
            return f"Added {quantity}x {existing}. (Total: {self.items[existing]})"
        canonical = item_name.title()
        self.items[canonical] = quantity
        return f"Added {quantity}x {canonical}. (Total: {self.items[canonical]})"

    def remove_item(self, item_name: str, quantity: int = 1) -> str:
        item_name = item_name.strip()
        existing = self._find_key(item_name)
        if not existing:
            raise ValueError(f"'{item_name}' not found in inventory.")
        if quantity > self.items[existing]:
            raise ValueError(f"Only have {self.items[existing]}x {existing}.")

        self.items[existing] -= quantity
        if self.items[existing] == 0:
            del self.items[existing]
            return f"Removed all {existing} from inventory."
        return f"Removed {quantity}x {existing}. (Remaining: {self.items[existing]})"

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
