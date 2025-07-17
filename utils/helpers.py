# utils/helpers.py
"""
General Utility Functions
Stateless helper functions for common operations across the application
"""

import re
import os
import unicodedata
from typing import List, Optional, Union, Tuple, Any
from difflib import SequenceMatcher
from PyQt6.QtWidgets import QApplication

    
# =============================================================================
# POKEMON NAME EXTRACTION & CLEANING
# =============================================================================

def extract_pokemon_name_from_card(card_name: str) -> Union[str, List[str], None]:
    """
    Extract Pokemon name(s) from card name using improved logic
    
    Args:
        card_name: The full card name from TCG
        
    Returns:
        str: Single Pokemon name for regular cards
        List[str]: Multiple Pokemon names for team-up cards
        None: If no Pokemon name could be extracted
    """
    if not card_name:
        return None
    
    # First, check for team-up cards (& symbol indicates multiple Pokemon)
    if ' & ' in card_name:
        # Extract all Pokemon names from team-up cards
        # Remove any suffixes first
        clean_team_name = re.sub(r'\s+(?:GX|TAG TEAM|LEGEND).*$', '', card_name)
        # Split by & and clean each name
        pokemon_names = []
        for name in clean_team_name.split(' & '):
            cleaned = clean_single_pokemon_name(name.strip())
            if cleaned:
                pokemon_names.append(cleaned)
        return pokemon_names if len(pokemon_names) > 1 else (pokemon_names[0] if pokemon_names else None)
    
    # For single Pokemon, use existing logic
    return clean_single_pokemon_name(card_name)


def clean_single_pokemon_name(card_name: str) -> Optional[str]:
    """
    Clean a single Pokemon name from card name
    
    Args:
        card_name: Card name to clean
        
    Returns:
        Cleaned Pokemon name or None if not found
    """
    if not card_name:
        return None
    
    # Remove card prefixes
    clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
    
    # Remove trainer possessives (e.g., "Team Rocket's", "Brock's", "Misty's")
    # This handles any possessive form ending with 's
    clean_name = re.sub(r"^[A-Za-z\s]+\'s\s+", '', clean_name)
    clean_name = re.sub(r"^Team\s+[A-Za-z\s]+\'s\s+", '', clean_name)
    
    # Handle special cases
    special_cases = {
        "Mr. Mime": "Mr. Mime",
        "Mime Jr.": "Mime Jr.",
        "Farfetch'd": "Farfetch'd",
        "Sirfetch'd": "Sirfetch'd",
        "Type: Null": "Type: Null",
        "Ho-Oh": "Ho-Oh",
        "Porygon-Z": "Porygon-Z",
        "Jangmo-o": "Jangmo-o",
        "Hakamo-o": "Hakamo-o",
        "Kommo-o": "Kommo-o"
    }
    
    for special_name, replacement in special_cases.items():
        if special_name in clean_name:
            return replacement
    
    # Remove regional prefixes but keep the base name
    regional_prefixes = ["Alolan", "Galarian", "Paldean", "Hisuian"]
    for region in regional_prefixes:
        if clean_name.startswith(f"{region} "):
            clean_name = clean_name.replace(f"{region} ", "", 1)
            break
    
    # Remove card suffixes
    clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|Prime|BREAK|Prism Star|◇|LV\.X|MEGA|M|Tag Team).*$', '', clean_name)
    
    # Remove any remaining special characters
    clean_name = re.sub(r'[◇★]', '', clean_name)
    
    return clean_name.strip()


def calculate_generation_from_pokedex(pokedex_number: int) -> Optional[int]:
    """
    Calculate Pokemon generation from National Pokedex number
    
    Args:
        pokedex_number: National Pokedex number
        
    Returns:
        Generation number (1-9) or None if invalid
    """
    if not pokedex_number or pokedex_number < 1:
        return None
    
    generation_ranges = [
        (1, 151, 1), (152, 251, 2), (252, 386, 3), (387, 493, 4), (494, 649, 5),
        (650, 721, 6), (722, 809, 7), (810, 905, 8), (906, 1025, 9)
    ]
    
    for start, end, gen in generation_ranges:
        if start <= pokedex_number <= end:
            return gen
    
    return 9  # Default to latest for new Pokemon


# =============================================================================
# STRING & TEXT UTILITIES
# =============================================================================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a string to be safe for use as a filename
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Safe filename string
    """
    if not filename:
        return "untitled"
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Normalize unicode
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove extra whitespace and replace spaces with underscores
    filename = re.sub(r'\s+', '_', filename.strip())
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Trim to max length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    # Ensure it's not empty
    return filename if filename else "untitled"


def fuzzy_match_strings(query: str, targets: List[str], threshold: float = 0.6) -> List[Tuple[str, float]]:
    """
    Find fuzzy matches between a query string and target strings
    
    Args:
        query: String to search for
        targets: List of strings to search in
        threshold: Minimum similarity ratio (0.0 to 1.0)
        
    Returns:
        List of (target, similarity_ratio) tuples, sorted by similarity
    """
    if not query or not targets:
        return []
    
    query_lower = query.lower()
    matches = []
    
    for target in targets:
        target_lower = target.lower()
        
        # Exact match gets priority
        if query_lower == target_lower:
            matches.append((target, 1.0))
            continue
        
        # Starts with gets high priority
        if target_lower.startswith(query_lower):
            ratio = 0.9 + (len(query) / len(target)) * 0.1
            matches.append((target, min(ratio, 1.0)))
            continue
        
        # Contains gets medium priority
        if query_lower in target_lower:
            ratio = 0.7 + (len(query) / len(target)) * 0.2
            matches.append((target, min(ratio, 1.0)))
            continue
        
        # Use sequence matcher for fuzzy matching
        ratio = SequenceMatcher(None, query_lower, target_lower).ratio()
        if ratio >= threshold:
            matches.append((target, ratio))
    
    # Sort by similarity ratio (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with optional suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: String to append when truncated
        
    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return text[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def is_valid_pokemon_id(pokemon_id: Union[str, int]) -> bool:
    """
    Validate if a Pokemon ID is valid (1-1025)
    
    Args:
        pokemon_id: Pokemon ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        id_int = int(pokemon_id)
        return 1 <= id_int <= 1025
    except (ValueError, TypeError):
        return False


def is_valid_generation(generation: Union[str, int]) -> bool:
    """
    Validate if a generation number is valid (1-9)
    
    Args:
        generation: Generation to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        gen_int = int(generation)
        return 1 <= gen_int <= 9
    except (ValueError, TypeError):
        return False


def validate_card_id_format(card_id: str) -> bool:
    """
    Validate if a card ID follows expected format patterns
    
    Args:
        card_id: Card ID to validate
        
    Returns:
        True if format looks valid, False otherwise
    """
    if not card_id or not isinstance(card_id, str):
        return False
    
    # Common TCG card ID patterns
    patterns = [
        r'^[a-zA-Z0-9]+-[a-zA-Z0-9]+$',  # set-number (e.g., xy1-1, base1-4)
        r'^[a-zA-Z]+\d+-\d+$',           # letters+numbers-number (e.g., xy11-54)
        r'^[a-zA-Z]+\d+[a-zA-Z]*-\d+$', # complex set codes
    ]
    
    return any(re.match(pattern, card_id) for pattern in patterns)


# =============================================================================
# FILE & PATH UTILITIES
# =============================================================================

def ensure_directory_exists(file_path: str) -> bool:
    """
    Ensure the directory for a file path exists
    
    Args:
        file_path: Full file path
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def is_path_writable(file_path: str) -> bool:
    """
    Check if a file path is writable
    
    Args:
        file_path: Path to check
        
    Returns:
        True if writable, False otherwise
    """
    try:
        # Ensure directory exists
        if not ensure_directory_exists(file_path):
            return False
        
        # Test write access
        test_file = file_path + '.test'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
        
    except (OSError, IOError, PermissionError):
        return False


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB, 0 if file doesn't exist
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0


# =============================================================================
# DATA PROCESSING UTILITIES
# =============================================================================

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def chunk_list(input_list: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size
    
    Args:
        input_list: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunked sublists
    """
    if chunk_size <= 0:
        return [input_list]
    
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
    """
    Flatten a nested list structure
    
    Args:
        nested_list: List of lists to flatten
        
    Returns:
        Flattened list
    """
    flattened = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    return flattened


# =============================================================================
# UI UTILITIES
# =============================================================================

def format_number_with_commas(number: Union[int, float]) -> str:
    """
    Format a number with comma separators
    
    Args:
        number: Number to format
        
    Returns:
        Formatted number string
    """
    try:
        return f"{number:,}"
    except (ValueError, TypeError):
        return str(number)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB", "250 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def calculate_grid_dimensions(total_items: int, items_per_row: int) -> Tuple[int, int]:
    """
    Calculate grid dimensions for layout
    
    Args:
        total_items: Total number of items
        items_per_row: Items per row
        
    Returns:
        Tuple of (rows, columns)
    """
    if items_per_row <= 0:
        return (0, 0)
    
    rows = (total_items + items_per_row - 1) // items_per_row  # Ceiling division
    cols = min(total_items, items_per_row)
    return (rows, cols)


# =============================================================================
# ERROR HANDLING UTILITIES
# =============================================================================

def log_error(error: Exception, context: str = "") -> str:
    """
    Format error for logging
    
    Args:
        error: Exception that occurred
        context: Additional context about where error occurred
        
    Returns:
        Formatted error string
    """
    error_msg = f"Error: {type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"[{context}] {error_msg}"
    return error_msg


def safe_execute(func, *args, default=None, **kwargs):
    """
    Safely execute a function and return default on error
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        default: Default value to return on error
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        return default
    

def center_window(window):
    """Center the window on the screen"""
    try:
        frame_geometry = window.frameGeometry()
        screen_center = QApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        window.move(frame_geometry.topLeft())
    except Exception as e:
        print(f"Warning: Could not center window: {e}")