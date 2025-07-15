"""
Session Cart Manager - Manages the import cart during current session
Extracted from the monolithic app.py
"""

from typing import Dict, Any, Optional, Callable, List


class SessionCartManager:
    """
    Manages the import cart during the current session
    Handles adding/removing cards and notifying listeners of changes
    """
    
    def __init__(self):
        self.cart_items: Dict[str, Dict[str, Any]] = {}  # card_id -> card_data
        self.item_added_callback: Optional[Callable] = None
        self.item_removed_callback: Optional[Callable] = None
        self.cart_cleared_callback: Optional[Callable] = None
    
    def add_card(self, card_id: str, card_data: Dict[str, Any]) -> bool:
        """
        Add a card to the cart
        
        Args:
            card_id: Unique card identifier
            card_data: Card information dictionary
        
        Returns:
            True if added successfully, False if already in cart
        """
        if card_id not in self.cart_items:
            self.cart_items[card_id] = card_data.copy()
            
            if self.item_added_callback:
                self.item_added_callback(card_id, card_data)
            
            return True
        
        return False  # Already in cart
    
    def remove_card(self, card_id: str) -> bool:
        """
        Remove a card from the cart
        
        Args:
            card_id: Unique card identifier
        
        Returns:
            True if removed successfully, False if not in cart
        """
        if card_id in self.cart_items:
            card_data = self.cart_items.pop(card_id)
            
            if self.item_removed_callback:
                self.item_removed_callback(card_id, card_data)
            
            return True
        
        return False
    
    def get_cart_items(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all items in cart
        
        Returns:
            Copy of cart items dictionary
        """
        return self.cart_items.copy()
    
    def get_cart_count(self) -> int:
        """
        Get number of items in cart
        
        Returns:
            Number of items currently in cart
        """
        return len(self.cart_items)
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items.clear()
        
        if self.cart_cleared_callback:
            self.cart_cleared_callback()
        elif self.item_removed_callback:
            # Fallback to item_removed_callback with None parameters
            self.item_removed_callback(None, None)
    
    def is_in_cart(self, card_id: str) -> bool:
        """
        Check if card is in cart
        
        Args:
            card_id: Unique card identifier
        
        Returns:
            True if card is in cart, False otherwise
        """
        return card_id in self.cart_items
    
    def get_card_data(self, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific card in cart
        
        Args:
            card_id: Unique card identifier
        
        Returns:
            Card data if in cart, None otherwise
        """
        return self.cart_items.get(card_id)
    
    def update_card_data(self, card_id: str, card_data: Dict[str, Any]) -> bool:
        """
        Update data for a card already in cart
        
        Args:
            card_id: Unique card identifier
            card_data: Updated card information
        
        Returns:
            True if updated successfully, False if not in cart
        """
        if card_id in self.cart_items:
            self.cart_items[card_id] = card_data.copy()
            return True
        
        return False
    
    def get_cards_by_pokemon(self, pokemon_name: str) -> List[Dict[str, Any]]:
        """
        Get all cards in cart for a specific Pokemon
        
        Args:
            pokemon_name: Name of the Pokemon
        
        Returns:
            List of card data for the specified Pokemon
        """
        matching_cards = []
        
        for card_id, card_data in self.cart_items.items():
            if card_data.get('pokemon_name', '').lower() == pokemon_name.lower():
                matching_cards.append({
                    'card_id': card_id,
                    **card_data
                })
        
        return matching_cards
    
    def get_cards_by_set(self, set_name: str) -> List[Dict[str, Any]]:
        """
        Get all cards in cart from a specific set
        
        Args:
            set_name: Name of the TCG set
        
        Returns:
            List of card data from the specified set
        """
        matching_cards = []
        
        for card_id, card_data in self.cart_items.items():
            if card_data.get('set_name', '').lower() == set_name.lower():
                matching_cards.append({
                    'card_id': card_id,
                    **card_data
                })
        
        return matching_cards
    
    def get_cart_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the cart contents
        
        Returns:
            Summary dictionary with counts and breakdowns
        """
        if not self.cart_items:
            return {
                'total_cards': 0,
                'unique_pokemon': 0,
                'unique_sets': 0,
                'pokemon_breakdown': {},
                'set_breakdown': {},
                'rarity_breakdown': {}
            }
        
        pokemon_count = {}
        set_count = {}
        rarity_count = {}
        
        for card_data in self.cart_items.values():
            # Count by Pokemon
            pokemon_name = card_data.get('pokemon_name', 'Unknown')
            pokemon_count[pokemon_name] = pokemon_count.get(pokemon_name, 0) + 1
            
            # Count by set
            set_name = card_data.get('set_name', 'Unknown')
            set_count[set_name] = set_count.get(set_name, 0) + 1
            
            # Count by rarity
            rarity = card_data.get('rarity', 'Unknown')
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        return {
            'total_cards': len(self.cart_items),
            'unique_pokemon': len(pokemon_count),
            'unique_sets': len(set_count),
            'pokemon_breakdown': pokemon_count,
            'set_breakdown': set_count,
            'rarity_breakdown': rarity_count
        }
    
    def set_callbacks(self, 
                     item_added: Optional[Callable] = None,
                     item_removed: Optional[Callable] = None,
                     cart_cleared: Optional[Callable] = None):
        """
        Set callback functions for cart events
        
        Args:
            item_added: Callback for when item is added (card_id, card_data)
            item_removed: Callback for when item is removed (card_id, card_data)
            cart_cleared: Callback for when cart is cleared (no parameters)
        """
        if item_added is not None:
            self.item_added_callback = item_added
        
        if item_removed is not None:
            self.item_removed_callback = item_removed
        
        if cart_cleared is not None:
            self.cart_cleared_callback = cart_cleared
    
    def bulk_add_cards(self, cards_data: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Add multiple cards to cart at once
        
        Args:
            cards_data: Dictionary of card_id -> card_data
        
        Returns:
            Dictionary mapping card_id to success status
        """
        results = {}
        
        for card_id, card_data in cards_data.items():
            results[card_id] = self.add_card(card_id, card_data)
        
        return results
    
    def bulk_remove_cards(self, card_ids: List[str]) -> Dict[str, bool]:
        """
        Remove multiple cards from cart at once
        
        Args:
            card_ids: List of card IDs to remove
        
        Returns:
            Dictionary mapping card_id to success status
        """
        results = {}
        
        for card_id in card_ids:
            results[card_id] = self.remove_card(card_id)
        
        return results
    
    def export_cart_data(self) -> Dict[str, Any]:
        """
        Export cart data for backup/restore purposes
        
        Returns:
            Complete cart state that can be imported later
        """
        return {
            'version': '1.0',
            'timestamp': time.time(),
            'cart_items': self.cart_items.copy(),
            'summary': self.get_cart_summary()
        }
    
    def import_cart_data(self, cart_data: Dict[str, Any]) -> bool:
        """
        Import cart data from backup
        
        Args:
            cart_data: Cart data from export_cart_data()
        
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            if cart_data.get('version') != '1.0':
                return False
            
            imported_items = cart_data.get('cart_items', {})
            
            # Clear current cart
            self.clear_cart()
            
            # Import items
            for card_id, card_data in imported_items.items():
                self.cart_items[card_id] = card_data
            
            # Notify of bulk change
            if self.item_added_callback:
                for card_id, card_data in self.cart_items.items():
                    self.item_added_callback(card_id, card_data)
            
            return True
            
        except Exception as e:
            print(f"Error importing cart data: {e}")
            return False


# Import for time module
import time