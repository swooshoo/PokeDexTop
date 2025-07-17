"""
Application configuration and constants
"""

import os
from pathlib import Path

# =====================================================
# APPLICATION CONFIGURATION
# =====================================================

APP_CONFIG = {
    'app_name': 'PokéDextop 1.0',
    'version': '1.0.0',
    'organization': 'PokéDextop',
    'author': 'PokéDextop Team'
}

# =====================================================
# DIRECTORY PATHS
# =====================================================

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
CACHE_DIR = Path.home() / '.pokedextop' / 'cache'
DATABASE_DIR = DATA_DIR / 'databases'

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DEFAULT_DB_PATH = DATABASE_DIR / 'pokedextop.db'

# =====================================================
# CACHE CONFIGURATION
# =====================================================

CACHE_CONFIG = {
    'tcg_cards': {
        'original': CACHE_DIR / 'tcg_cards' / 'original',
        'export': CACHE_DIR / 'tcg_cards' / 'export',
        'ui': CACHE_DIR / 'tcg_cards' / 'ui'
    },
    'sprites': {
        'original': CACHE_DIR / 'sprites' / 'original',
        'export': CACHE_DIR / 'sprites' / 'export',
        'ui': CACHE_DIR / 'sprites' / 'ui'
    },
    'artwork': {
        'original': CACHE_DIR / 'artwork' / 'original',
        'export': CACHE_DIR / 'artwork' / 'export',
        'ui': CACHE_DIR / 'artwork' / 'ui'
    }
}

# Create cache directories
for cache_type, paths in CACHE_CONFIG.items():
    for quality, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)

# =====================================================
# IMAGE QUALITY CONFIGURATIONS
# =====================================================

IMAGE_QUALITY_CONFIGS = {
    'ui': {
        'max_width': 300,
        'max_height': 300,
        'jpeg_quality': 75,
        'png_compression': 6,
        'cache_subdir': 'ui'
    },
    'export_high': {
        'max_width': 2000,    # Allow large images
        'max_height': 2000,
        'jpeg_quality': 95,
        'png_compression': 1,  # Minimal compression
        'cache_subdir': 'export/high'
    },
    'export_medium': {
        'max_width': 1000,
        'max_height': 1000,
        'jpeg_quality': 85,
        'png_compression': 3,
        'cache_subdir': 'export/medium'
    },
    'export_low': {
        'max_width': 500,
        'max_height': 500,
        'jpeg_quality': 70,
        'png_compression': 6,
        'cache_subdir': 'export/low'
    }
}

# =====================================================
# WIDGET DIMENSIONS (LEGACY COMPATIBILITY)
# =====================================================

WIDGET_DIMENSIONS = {
    # UI Display Dimensions
    'ui': {
        'pokemon_card': (300, 380),
        'tcg_card': (270, 410),
        'cart_item': (130, 85),
        'browse_card': (270, 410)
    },
    
    # Export Dimensions (Legacy Compatibility)
    'export': {
        'high': {
            'pokemon_card': (280, 420),     # Legacy dimensions
            'tcg_card': (245, 342),         # Standard card size
            'sprite_card': (280, 320),
            'image_sizes': {
                'tcg_card': (240, 336),     # TCG card image
                'sprite': (200, 200)        # Square sprites
            }
        },
        'medium': {
            'pokemon_card': (210, 315),
            'tcg_card': (180, 252),
            'sprite_card': (210, 240),
            'image_sizes': {
                'tcg_card': (180, 252),
                'sprite': (150, 150)
            }
        },
        'low': {
            'pokemon_card': (140, 210),
            'tcg_card': (120, 168),
            'sprite_card': (140, 160),
            'image_sizes': {
                'tcg_card': (120, 168),
                'sprite': (100, 100)
            }
        }
    }
}

# =====================================================
# POKEMON GENERATIONS
# =====================================================

POKEMON_GENERATIONS = [
    (1, "Generation I (Kanto)", 1, 151, "Kanto"),
    (2, "Generation II (Johto)", 152, 251, "Johto"),
    (3, "Generation III (Hoenn)", 252, 386, "Hoenn"),
    (4, "Generation IV (Sinnoh)", 387, 493, "Sinnoh"),
    (5, "Generation V (Unova)", 494, 649, "Unova"),
    (6, "Generation VI (Kalos)", 650, 721, "Kalos"),
    (7, "Generation VII (Alola)", 722, 809, "Alola"),
    (8, "Generation VIII (Galar)", 810, 905, "Galar"),
    (9, "Generation IX (Paldea)", 906, 1025, "Paldea")
]

# =====================================================
# API CONFIGURATION
# =====================================================

API_CONFIG = {
    'pokemontcg_io': {
        'base_url': 'https://api.pokemontcg.io/v2',
        'rate_limit': 0.1,  # 100ms between requests
        'timeout': 10
    },
    'pokeapi': {
        'base_url': 'https://pokeapi.co/api/v2',
        'sprite_url': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png',
        'artwork_url': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokemon_id}.png'
    }
}

# =====================================================
# EXPORT CONFIGURATION
# =====================================================

EXPORT_CONFIG = {
    'default_title': 'My Pokémon Collection',
    'supported_formats': ['PNG', 'JPG'],
    'default_format': 'PNG',
    'cards_per_row_range': (2, 5),
    'default_cards_per_row': 4,
    'quality_levels': ['high', 'medium', 'low'],
    'default_quality': 'high',
    'max_collection_size': 1000,  # Safety limit
    'footer_text': 'Exported by PokéDextop'
}

# =====================================================
# UI STYLING
# =====================================================

DARK_THEME_STYLE = """
QMainWindow {
    background-color: #2c3e50;
    color: white;
}
QTabWidget::pane {
    border: 1px solid #34495e;
    background-color: #2c3e50;
}
QTabBar::tab {
    background-color: #34495e;
    color: white;
    padding: 10px 16px;
    margin-right: 2px;
    border-radius: 4px 4px 0px 0px;
}
QTabBar::tab:selected {
    background-color: #3498db;
}
QTabBar::tab:hover {
    background-color: #2980b9;
}
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #1f618d;
}
QGroupBox {
    color: white;
    border: 2px solid #34495e;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}
QLineEdit {
    background-color: #34495e;
    border: 2px solid #2c3e50;
    border-radius: 4px;
    padding: 5px;
    color: white;
}
QLineEdit:focus {
    border: 2px solid #3498db;
}
QComboBox {
    background-color: #34495e;
    border: 2px solid #2c3e50;
    border-radius: 4px;
    padding: 5px;
    color: white;
}
QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid white;
    margin-right: 5px;
}
"""