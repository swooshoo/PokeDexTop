"""
Session Cart Manager - Extracted from app.py lines 350-450
Manages the     cart during the current session
"""

from typing import Dict, Any, Callable, Optional

class SessionCartManager:
    """Manages the import cart during the current session"""
    
    def __init__(self):
        self.cart_items: Dict[str, Dict[str, Any]] = {}  # card_id -> card_data
        self.item_added_callback: Optional[Callable] = None
        self.item_removed_callback: Optional[Callable] = None
    
    def add_card(self, card_id: str, card_data: Dict[str, Any]) -> bool:
        """Add a card to the cart"""
        if card_id not in self.cart_items:
            self.cart_items[card_id] = card_data
            if self.item_added_callback:
                self.item_added_callback(card_id, card_data)
            return True
        return False  # Already in cart
    
    def remove_card(self, card_id: str) -> bool:
        """Remove a card from the cart"""
        if card_id in self.cart_items:
            card_data = self.cart_items.pop(card_id)
            if self.item_removed_callback:
                self.item_removed_callback(card_id, card_data)
            return True
        return False
    
    def get_cart_items(self) -> Dict[str, Dict[str, Any]]:
        """Get all items in cart"""
        return self.cart_items.copy()
    
    def get_cart_count(self) -> int:
        """Get number of items in cart"""
        return len(self.cart_items)
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items.clear()
        if self.item_removed_callback:
            self.item_removed_callback(None, None)  # Signal that cart was cleared
    
    def is_in_cart(self, card_id: str) -> bool:
        """Check if card is in cart"""
        return card_id in self.cart_items