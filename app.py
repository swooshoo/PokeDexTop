import sys
import os
import json
import sqlite3
import hashlib
import requests
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QScrollArea,
                            QGridLayout, QTabWidget, QSizePolicy, QFrame,
                            QComboBox, QLineEdit, QCompleter,
                            QToolButton, QMessageBox, QDialog, QGroupBox, QRadioButton, 
                            QCheckBox, QButtonGroup, QDialogButtonBox, QFileDialog,
                            QProgressBar, QTextEdit, QSpinBox)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QSize, QStringListModel, pyqtSignal, QObject, QRectF, QThread, QTimer, QUrl
from PyQt5.QtPrintSupport import QPrinter 
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from utils import ImageLoader

# Pokemon TCG SDK imports
from pokemontcgsdk import Card, Set
from pokemontcgsdk.restclient import RestClient, PokemonTcgException


# =============================================================================
# BRONZE-SILVER-GOLD DATA ARCHITECTURE
# =============================================================================

class DatabaseManager:
    """
    Implements Bronze-Silver-Gold data architecture:
    
    BRONZE (Raw): Direct API responses stored as-is
    SILVER (Processed): Cleaned and normalized data 
    GOLD (Master): Business-ready data for applications
    """
    
    def __init__(self, db_path="data/databases/pokedextop.db"):
        self.db_path = db_path
        # Only create directory for file-based databases, not in-memory
        if db_path != ":memory:" and not db_path.startswith(":"):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
        self.configure_database_for_concurrency()
    
    def init_database(self):
        """Create Bronze-Silver-Gold data tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # =============================================================================
        # BRONZE LAYER - Raw API Data (Immutable Historical Record)
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                api_endpoint TEXT,
                UNIQUE(card_id, data_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                UNIQUE(set_id, data_hash)
            )
        """)
        
        # =============================================================================
        # SILVER LAYER - Processed & Cleaned Data
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_pokemon_master (
                pokemon_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                generation INTEGER,
                pokedex_numbers TEXT,  -- JSON array of national pokedex numbers
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_ids TEXT  -- JSON array of bronze record IDs
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_cards (
                card_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pokemon_name TEXT,
                set_id TEXT NOT NULL,
                set_name TEXT,
                artist TEXT,
                rarity TEXT,
                supertype TEXT,
                subtypes TEXT,  -- JSON array
                types TEXT,     -- JSON array  
                hp TEXT,
                number TEXT,
                image_url_small TEXT,
                image_url_large TEXT,
                national_pokedex_numbers TEXT,  -- JSON array
                legalities TEXT,  -- JSON object
                market_prices TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_cards(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_sets (
                set_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                series TEXT,
                printed_total INTEGER,
                total INTEGER,
                release_date TEXT,
                symbol_url TEXT,
                logo_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_sets(id)
            )
        """)
        
        # =============================================================================
        # GOLD LAYER - Business-Ready Application Data
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_user_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                pokemon_id INTEGER,
                card_id TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collection_type TEXT DEFAULT 'personal',  -- personal, wishlist, favorites
                notes TEXT,
                UNIQUE(user_id, pokemon_id, collection_type),
                FOREIGN KEY (pokemon_id) REFERENCES silver_pokemon_master(pokemon_id),
                FOREIGN KEY (card_id) REFERENCES silver_tcg_cards(card_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_pokemon_generations (
                generation INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                start_id INTEGER,
                end_id INTEGER,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # =============================================================================
        # S3 INTEGRATION LAYER - Image Management
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s3_image_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL UNIQUE,
                s3_bucket TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                s3_url TEXT NOT NULL,
                image_type TEXT,  -- 'sprite', 'card_small', 'card_large'
                entity_id TEXT,   -- pokemon_id or card_id
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                content_hash TEXT
            )
        """)
        
        # Performance indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bronze_cards_timestamp ON bronze_tcg_cards(data_pull_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_cards_pokemon ON silver_tcg_cards(pokemon_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_cards_set ON silver_tcg_cards(set_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gold_collections_user ON gold_user_collections(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_s3_cache_entity ON s3_image_cache(entity_id, image_type)")
        
        # Initialize generation data
        self.initialize_generations(cursor)
        
        conn.commit()
        conn.close()
    
    def initialize_generations(self, cursor):
        """Initialize Pokemon generation data"""
        generations = [
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
        
        for gen_data in generations:
            cursor.execute("""
                INSERT OR IGNORE INTO gold_pokemon_generations 
                (generation, name, start_id, end_id, region)
                VALUES (?, ?, ?, ?, ?)
            """, gen_data)
            
    def configure_database_for_concurrency(self):
        """Configure database for better concurrency handling"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Set busy timeout
            conn.execute("PRAGMA busy_timeout=30000")
            # Optimize for faster writes
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.commit()
        finally:
            conn.close()
    
    # =============================================================================
    # BRONZE LAYER OPERATIONS - Raw Data Storage
    # =============================================================================
    
    def store_bronze_card_data(self, card_data, api_endpoint="cards"):
        """Store raw card data in Bronze layer with deduplication"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            card_id = card_data.get('id')
            raw_json = json.dumps(card_data, sort_keys=True)
            content_hash = hashlib.sha256(raw_json.encode()).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT INTO bronze_tcg_cards 
                    (card_id, raw_json, data_hash, api_endpoint)
                    VALUES (?, ?, ?, ?)
                """, (card_id, raw_json, content_hash, api_endpoint))
                
                bronze_id = cursor.lastrowid
                conn.commit()
                
                # Process to Silver layer
                self.process_bronze_to_silver_card(bronze_id, card_data)
                print(f"✓ Stored new card data: {card_id}")
                return bronze_id
                
            except sqlite3.IntegrityError:
                cursor.execute("""
                    SELECT id FROM bronze_tcg_cards 
                    WHERE card_id = ? AND data_hash = ?
                """, (card_id, content_hash))
                result = cursor.fetchone()
                existing_id = result[0] if result else None
                print(f"⚡ Duplicate card data found: {card_id}")
                return existing_id
                
        except Exception as e:
            print(f"Database error storing card {card_data.get('id', 'unknown')}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def store_bronze_set_data(self, set_data):
        """Store raw set data in Bronze layer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_id = set_data.get('id')
        raw_json = json.dumps(set_data, sort_keys=True)
        content_hash = hashlib.sha256(raw_json.encode()).hexdigest()
        
        try:
            cursor.execute("""
                INSERT INTO bronze_tcg_sets 
                (set_id, raw_json, data_hash)
                VALUES (?, ?, ?)
            """, (set_id, raw_json, content_hash))
            
            bronze_id = cursor.lastrowid
            conn.commit()
            
            # Process to Silver layer
            self.process_bronze_to_silver_set(bronze_id, set_data)
            return bronze_id
            
        except sqlite3.IntegrityError:
            cursor.execute("""
                SELECT id FROM bronze_tcg_sets 
                WHERE set_id = ? AND data_hash = ?
            """, (set_id, content_hash))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    # =============================================================================
    # SILVER LAYER OPERATIONS - Processed Data
    # =============================================================================
    
    def process_bronze_to_silver_card(self, bronze_id, card_data):
        """Process Bronze card data to Silver layer (cleaned/normalized)"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
            cursor = conn.cursor()
            
            # Extract and clean card data
            card_id = card_data.get('id')
            name = card_data.get('name', '')
            pokemon_name = self.extract_pokemon_name_from_card(name)
            
            # Handle nested data safely
            set_data = card_data.get('set', {})
            images = card_data.get('images', {})
            legalities = card_data.get('legalities', {})
            tcgplayer = card_data.get('tcgplayer', {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_tcg_cards 
                (card_id, name, pokemon_name, set_id, set_name, artist, rarity, 
                supertype, subtypes, types, hp, number, 
                image_url_small, image_url_large, national_pokedex_numbers,
                legalities, market_prices, source_bronze_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                name,
                pokemon_name,
                set_data.get('id'),
                set_data.get('name'),
                card_data.get('artist'),
                card_data.get('rarity'),
                card_data.get('supertype'),
                json.dumps(card_data.get('subtypes', [])),
                json.dumps(card_data.get('types', [])),
                card_data.get('hp'),
                card_data.get('number'),
                images.get('small'),
                images.get('large'),
                json.dumps(card_data.get('nationalPokedexNumbers', [])),
                json.dumps(legalities),
                json.dumps(tcgplayer.get('prices', {})),
                bronze_id
            ))
            
            # Update Pokemon master using the same connection
            if pokemon_name and card_data.get('nationalPokedexNumbers'):
                self.update_silver_pokemon_master_with_connection(
                    cursor, pokemon_name, card_data.get('nationalPokedexNumbers')
                )
            
            conn.commit()
            
        except Exception as e:
            print(f"Error processing card to silver layer: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_silver_pokemon_master_with_connection(self, cursor, pokemon_name, pokedex_numbers):
        """Update Pokemon master using existing connection"""
        try:
            # Calculate generation from first pokedex number
            primary_number = pokedex_numbers[0] if pokedex_numbers else None
            generation = self.calculate_generation(primary_number) if primary_number else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_pokemon_master 
                (pokemon_id, name, generation, pokedex_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                primary_number,
                pokemon_name,
                generation,
                json.dumps(pokedex_numbers)
            ))
            
        except Exception as e:
            print(f"Error updating Pokemon master: {e}")
            raise
                
    def process_bronze_to_silver_set(self, bronze_id, set_data):
        """Process Bronze set data to Silver layer (cleaned/normalized)"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract and clean set data
            set_id = set_data.get('id')
            name = set_data.get('name', '')
            series = set_data.get('series', '')
            printed_total = set_data.get('printedTotal', 0)
            total = set_data.get('total', 0)
            release_date = set_data.get('releaseDate', '')
            
            # Handle nested data safely
            images = set_data.get('images', {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_tcg_sets 
                (set_id, name, series, printed_total, total, release_date, 
                symbol_url, logo_url, source_bronze_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                set_id,
                name,
                series,
                printed_total,
                total,
                release_date,
                images.get('symbol'),
                images.get('logo'),
                bronze_id
            ))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error processing set to silver layer: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def extract_pokemon_name_from_card(self, card_name):
        """Extract Pokemon name from card name using improved logic"""
        import re
        
        if not card_name:
            return None
        
        # Remove card prefixes
        clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
        
        # Handle special cases
        special_cases = {
            "Mr. Mime": "Mr. Mime",
            "Mime Jr.": "Mime Jr.",
            "Farfetch'd": "Farfetch'd",
            "Sirfetch'd": "Sirfetch'd",
            "Type: Null": "Type: Null"
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
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION).*$', '', clean_name)
        
        # Handle possessive forms
        possessive_match = re.match(r"(\w+\'s)\s+(\w+(?:\s+\w+)?)", clean_name)
        if possessive_match:
            return possessive_match.group(2)
        
        return clean_name.strip()
    
    def update_silver_pokemon_master(self, pokemon_name, pokedex_numbers):
        """Update or create Pokemon master record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate generation from first pokedex number
        primary_number = pokedex_numbers[0] if pokedex_numbers else None
        generation = self.calculate_generation(primary_number) if primary_number else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO silver_pokemon_master 
            (pokemon_id, name, generation, pokedex_numbers)
            VALUES (?, ?, ?, ?)
        """, (
            primary_number,
            pokemon_name,
            generation,
            json.dumps(pokedex_numbers)
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_generation(self, pokedex_number):
        """Calculate generation from pokedex number"""
        if not pokedex_number:
            return None
            
        generation_ranges = [
            (1, 151, 1), (152, 251, 2), (252, 386, 3), (387, 493, 4), (494, 649, 5),
            (650, 721, 6), (722, 809, 7), (810, 905, 8), (906, 1025, 9)
        ]
        
        for start, end, gen in generation_ranges:
            if start <= pokedex_number <= end:
                return gen
        return 9  # Default to latest
    
    # =============================================================================
    # GOLD LAYER OPERATIONS - Business Logic
    # =============================================================================
    
    def get_pokemon_by_generation(self, generation):
        """Get Pokemon for a generation (Gold layer query)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.pokemon_id, p.name, p.pokedex_numbers,
                   COUNT(c.card_id) as card_count,
                   GROUP_CONCAT(c.card_id) as available_cards
            FROM silver_pokemon_master p
            LEFT JOIN silver_tcg_cards c ON p.name = c.pokemon_name
            WHERE p.generation = ?
            GROUP BY p.pokemon_id, p.name
            ORDER BY p.pokemon_id
        """, (generation,))
        
        results = cursor.fetchall()
        conn.close()
        
        pokemon_dict = {}
        for row in results:
            pokemon_dict[str(row[0])] = {
                'id': row[0],
                'name': row[1],
                'generation': generation,
                'pokedex_numbers': json.loads(row[2]) if row[2] else [],
                'card_count': row[3],
                'available_cards': row[4].split(',') if row[4] else []
            }
        
        return pokemon_dict
    
    def get_user_collection(self, user_id='default'):
        """Get user's collection from Gold layer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT uc.pokemon_id, uc.card_id, c.name, c.image_url_large, c.set_name
            FROM gold_user_collections uc
            JOIN silver_tcg_cards c ON uc.card_id = c.card_id
            WHERE uc.user_id = ? AND uc.collection_type = 'personal'
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        collection = {}
        for row in results:
            collection[str(row[0])] = {
                'card_id': row[1],
                'card_name': row[2],
                'image_url': row[3],
                'set_name': row[4]
            }
        
        return collection
    
    def add_to_user_collection(self, user_id, pokemon_id, card_id):
        """Add card to user's collection (Gold layer)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO gold_user_collections 
            (user_id, pokemon_id, card_id, collection_type)
            VALUES (?, ?, ?, 'personal')
        """, (user_id, pokemon_id, card_id))
        
        conn.commit()
        conn.close()

# =============================================================================
# IMAGE LOADER
# =============================================================================

class ImageLoader(QObject):
    """Centralized image loading utility for the application"""
    
    imageLoaded = pyqtSignal(QPixmap)
    
    def __init__(self):
        super().__init__()
        self._network_manager = QNetworkAccessManager()
        self._loading_images = {}  # Track ongoing requests
        self._image_cache = {}  # Simple in-memory cache
    
    def load_image(self, url, label, size=None):
        """
        Load an image from URL and set it on a QLabel
        
        Args:
            url: Image URL
            label: QLabel to set the image on
            size: Optional tuple (width, height) to scale the image
        """
        if not url:
            label.setText("No Image")
            return
        
        # Check cache first
        if url in self._image_cache:
            self._set_image_on_label(label, self._image_cache[url], size)
            return
        
        # Show loading state
        label.setText("Loading...")
        label.setStyleSheet("color: #7f8c8d; background-color: #2c3e50; border-radius: 4px;")
        
        # Create request
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute, 
                           QNetworkRequest.PreferCache)
        
        reply = self._network_manager.get(request)
        
        # Store the reply with its associated data
        self._loading_images[reply] = (label, size, url)
        
        # Connect signals
        reply.finished.connect(lambda: self._on_image_loaded(reply))
        reply.error.connect(lambda: self._on_image_error(reply))
    
    def _on_image_loaded(self, reply):
        """Handle image loading completion"""
        if reply not in self._loading_images:
            reply.deleteLater()
            return
        
        label, size, url = self._loading_images.pop(reply)
        
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            
            if pixmap.loadFromData(data):
                # Cache the pixmap
                self._image_cache[url] = pixmap
                # Set on label
                self._set_image_on_label(label, pixmap, size)
            else:
                label.setText("Invalid\nImage")
                label.setStyleSheet("color: #e74c3c; background-color: #2c3e50; border-radius: 4px;")
        else:
            self._on_image_error(reply)
        
        reply.deleteLater()
    
    def _on_image_error(self, reply):
        """Handle image loading errors"""
        if reply in self._loading_images:
            label, _, _ = self._loading_images.pop(reply)
            label.setText("Failed to\nLoad Image")
            label.setStyleSheet("color: #e74c3c; background-color: #2c3e50; border-radius: 4px;")
        reply.deleteLater()
    
    def _set_image_on_label(self, label, pixmap, size):
        """Set pixmap on label with optional scaling"""
        if size:
            scaled_pixmap = pixmap.scaled(size[0], size[1], 
                                         Qt.KeepAspectRatio, 
                                         Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
        else:
            # Scale to label size
            label_size = label.size()
            scaled_pixmap = pixmap.scaled(label_size, 
                                         Qt.KeepAspectRatio, 
                                         Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
        
        label.setStyleSheet("")  # Clear loading styles


# =============================================================================
# TCG API CLIENT - Pokemon TCG SDK Integration
# =============================================================================

class TCGAPIClient:
    """Pokemon TCG API client using the official SDK"""
    
    def __init__(self, db_manager, api_key=None):
        self.db_manager = db_manager
        
        # Configure API key for higher rate limits
        if api_key:
            RestClient.configure(api_key)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def search_cards_by_pokemon_name(self, pokemon_name):
        """Search cards by Pokemon name"""
        try:
            self._rate_limit()
            
            # Search for cards containing the Pokemon name
            query = f'name:"{pokemon_name}"'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                try:
                    # Convert card object to dict for storage
                    card_data = self._card_to_dict(card)
                    bronze_id = self.db_manager.store_bronze_card_data(card_data)
                    stored_cards.append(card_data)
                except Exception as store_error:
                    print(f"Warning: Failed to store card {card.id}: {store_error}")
                    # Still add the card data even if storage fails
                    card_data = self._card_to_dict(card)
                    stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error searching for {pokemon_name}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error searching for {pokemon_name}: {e}")
            return []
    
    def search_cards_by_pokedex_number(self, pokedex_number):
        """Search cards by National Pokedex number"""
        try:
            self._rate_limit()
            
            query = f'nationalPokedexNumbers:{pokedex_number}'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                card_data = self._card_to_dict(card)
                self.db_manager.store_bronze_card_data(card_data)
                stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error for Pokedex #{pokedex_number}: {e}")
            return []
    
    def get_all_sets(self):
        """Fetch all TCG sets"""
        try:
            self._rate_limit()
            
            sets = Set.all()
            stored_sets = []
            
            for tcg_set in sets:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
                stored_sets.append(set_data)
            
            return stored_sets
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching sets: {e}")
            return []
    
    def get_cards_from_set(self, set_id, page_size=250):
        """Get all cards from a specific set"""
        try:
            page = 1
            all_cards = []
            
            # First, get and store the set information
            self._rate_limit()
            tcg_set = Set.find(set_id)
            if tcg_set:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
            
            # Then get all cards from the set
            while True:
                self._rate_limit()
                
                query = f'set.id:{set_id}'
                cards = Card.where(q=query, page=page, pageSize=page_size)
                
                if not cards:
                    break
                
                for card in cards:
                    card_data = self._card_to_dict(card)
                    self.db_manager.store_bronze_card_data(card_data)
                    all_cards.append(card_data)
                
                page += 1
                
                # Safety break for large sets
                if page > 20:
                    break
            
            return all_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching set {set_id}: {e}")
            return []
    
    def _card_to_dict(self, card):
        """Convert Card object to dictionary for storage"""
        return {
            'id': card.id,
            'name': card.name,
            'supertype': card.supertype,
            'subtypes': card.subtypes or [],
            'types': card.types or [],
            'hp': card.hp,
            'evolvesFrom': card.evolvesFrom,
            'attacks': [self._attack_to_dict(attack) for attack in (card.attacks or [])],
            'weaknesses': [self._weakness_to_dict(w) for w in (card.weaknesses or [])],
            'resistances': [self._resistance_to_dict(r) for r in (card.resistances or [])],
            'retreatCost': card.retreatCost or [],
            'convertedRetreatCost': card.convertedRetreatCost,
            'set': self._set_to_dict(card.set),
            'number': card.number,
            'artist': card.artist,
            'rarity': card.rarity,
            'flavorText': card.flavorText,
            'nationalPokedexNumbers': card.nationalPokedexNumbers or [],
            'legalities': self._legalities_to_dict(card.legalities),
            'images': {
                'small': card.images.small,
                'large': card.images.large
            } if card.images else {},
            'tcgplayer': self._tcgplayer_to_dict(card.tcgplayer) if card.tcgplayer else {}
        }
    
    def _set_to_dict(self, tcg_set):
        """Convert Set object to dictionary"""
        return {
            'id': tcg_set.id,
            'name': tcg_set.name,
            'series': tcg_set.series,
            'printedTotal': tcg_set.printedTotal,
            'total': tcg_set.total,
            'legalities': self._legalities_to_dict(tcg_set.legalities),
            'ptcgoCode': tcg_set.ptcgoCode,
            'releaseDate': tcg_set.releaseDate,
            'updatedAt': tcg_set.updatedAt,
            'images': {
                'symbol': tcg_set.images.symbol,
                'logo': tcg_set.images.logo
            } if tcg_set.images else {}
        }
    
    def _attack_to_dict(self, attack):
        """Convert Attack object to dictionary"""
        return {
            'name': attack.name,
            'cost': attack.cost or [],
            'convertedEnergyCost': attack.convertedEnergyCost,
            'damage': attack.damage,
            'text': attack.text
        }
    
    def _weakness_to_dict(self, weakness):
        """Convert Weakness object to dictionary"""
        return {
            'type': weakness.type,
            'value': weakness.value
        }
    
    def _resistance_to_dict(self, resistance):
        """Convert Resistance object to dictionary"""
        return {
            'type': resistance.type,
            'value': resistance.value
        }
    
    def _legalities_to_dict(self, legalities):
        """Convert Legalities object to dictionary"""
        if not legalities:
            return {}
        
        return {
            'unlimited': legalities.unlimited,
            'expanded': legalities.expanded,
            'standard': legalities.standard
        }
    
    def _tcgplayer_to_dict(self, tcgplayer):
        """Convert TCGPlayer object to dictionary"""
        return {
            'url': tcgplayer.url,
            'updatedAt': tcgplayer.updatedAt,
            'prices': self._prices_to_dict(tcgplayer.prices) if tcgplayer.prices else {}
        }
    
    def _prices_to_dict(self, prices):
        """Convert TCGPrices object to dictionary"""
        result = {}
        
        if prices.normal:
            result['normal'] = self._price_to_dict(prices.normal)
        if prices.holofoil:
            result['holofoil'] = self._price_to_dict(prices.holofoil)
        if prices.reverseHolofoil:
            result['reverseHolofoil'] = self._price_to_dict(prices.reverseHolofoil)
        if prices.firstEditionNormal:
            result['firstEditionNormal'] = self._price_to_dict(prices.firstEditionNormal)
        if prices.firstEditionHolofoil:
            result['firstEditionHolofoil'] = self._price_to_dict(prices.firstEditionHolofoil)
        
        return result
    
    def _price_to_dict(self, price):
        """Convert TCGPrice object to dictionary"""
        return {
            'low': price.low,
            'mid': price.mid,
            'high': price.high,
            'market': price.market,
            'directLow': price.directLow
        }

# =============================================================================
# UI COMPONENTS - Updated for Bronze-Silver-Gold Architecture
# =============================================================================

class DataSyncDialog(QDialog):
    """Advanced data sync dialog for TCG data"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.tcg_client = TCGAPIClient(db_manager)
        self.setWindowTitle("Sync Pokemon TCG Data")
        self.setMinimumWidth(500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # API Key section
        api_section = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()
        
        api_info = QLabel("Enter your Pokemon TCG API key for higher rate limits (optional):")
        api_layout.addWidget(api_info)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API Key (optional)")
        api_layout.addWidget(self.api_key_input)
        
        api_section.setLayout(api_layout)
        layout.addWidget(api_section)
        
        # Sync options
        sync_section = QGroupBox("Sync Options")
        sync_layout = QVBoxLayout()
        
        # Pokemon search
        pokemon_layout = QHBoxLayout()
        pokemon_layout.addWidget(QLabel("Pokemon Name:"))
        self.pokemon_input = QLineEdit()
        self.pokemon_input.setPlaceholderText("e.g., Pikachu, Charizard")
        pokemon_layout.addWidget(self.pokemon_input)
        
        self.pokemon_search_btn = QPushButton("Search Cards")
        self.pokemon_search_btn.clicked.connect(self.search_pokemon_cards)
        pokemon_layout.addWidget(self.pokemon_search_btn)
        
        sync_layout.addLayout(pokemon_layout)
        
        # Generation sync
        gen_layout = QHBoxLayout()
        gen_layout.addWidget(QLabel("Generation:"))
        
        self.gen_combo = QComboBox()
        generations = [
            ("All Generations", "all"),
            ("Generation 1 (Kanto)", 1),
            ("Generation 2 (Johto)", 2),
            ("Generation 3 (Hoenn)", 3),
            ("Generation 4 (Sinnoh)", 4),
            ("Generation 5 (Unova)", 5),
            ("Generation 6 (Kalos)", 6),
            ("Generation 7 (Alola)", 7),
            ("Generation 8 (Galar)", 8),
            ("Generation 9 (Paldea)", 9)
        ]
        
        for gen_name, gen_value in generations:
            self.gen_combo.addItem(gen_name, gen_value)
        
        gen_layout.addWidget(self.gen_combo)
        
        self.gen_sync_btn = QPushButton("Sync Generation")
        self.gen_sync_btn.clicked.connect(self.sync_generation)
        gen_layout.addWidget(self.gen_sync_btn)
        
        sync_layout.addLayout(gen_layout)
        
        # Set sync
        set_layout = QHBoxLayout()
        set_layout.addWidget(QLabel("TCG Set ID:"))
        self.set_input = QLineEdit()
        self.set_input.setPlaceholderText("e.g., base1, xy1")
        set_layout.addWidget(self.set_input)
        
        self.set_sync_btn = QPushButton("Sync Set")
        self.set_sync_btn.clicked.connect(self.sync_set)
        set_layout.addWidget(self.set_sync_btn)
        
        sync_layout.addLayout(set_layout)
        
        # Bulk operations
        bulk_layout = QHBoxLayout()
        self.sync_all_sets_btn = QPushButton("Sync All Sets")
        self.sync_all_sets_btn.clicked.connect(self.sync_all_sets)
        bulk_layout.addWidget(self.sync_all_sets_btn)
        
        self.reset_database_btn = QPushButton("Reset Database")
        self.reset_database_btn.clicked.connect(self.reset_database)
        self.reset_database_btn.setStyleSheet("background-color: #e74c3c;")
        bulk_layout.addWidget(self.reset_database_btn)
        
        sync_layout.addLayout(bulk_layout)
        
        sync_section.setLayout(sync_layout)
        layout.addWidget(sync_section)
        
        # Progress section
        progress_section = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to sync...")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setPlaceholderText("Sync logs will appear here...")
        progress_layout.addWidget(self.log_output)
        
        progress_section.setLayout(progress_layout)
        layout.addWidget(progress_section)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def search_pokemon_cards(self):
        """Search for cards by Pokemon name"""
        pokemon_name = self.pokemon_input.text().strip()
        if not pokemon_name:
            QMessageBox.warning(self, "Input Error", "Please enter a Pokemon name")
            return
        
        self.disable_buttons()
        self.progress_label.setText(f"Searching cards for {pokemon_name}...")
        self.log_output.append(f"🔍 Searching for {pokemon_name} cards...")
        
        try:
            # Configure API key if provided
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
                self.log_output.append("✓ API key configured")
            
            # Search for cards
            cards = self.tcg_client.search_cards_by_pokemon_name(pokemon_name)
            
            if cards:
                self.log_output.append(f"✓ Found {len(cards)} cards for {pokemon_name}")
                self.progress_label.setText(f"Found {len(cards)} cards for {pokemon_name}")
            else:
                self.log_output.append(f"⚠ No cards found for {pokemon_name}")
                self.progress_label.setText(f"No cards found for {pokemon_name}")
                
        except Exception as e:
            self.log_output.append(f"❌ Error: {str(e)}")
            self.progress_label.setText("Search failed")
        
        self.enable_buttons()
    
    def sync_generation(self):
        """Sync all Pokemon cards for a generation"""
        generation = self.gen_combo.currentData()
        
        if generation == "all":
            self.sync_all_generations()
            return
        
        self.disable_buttons()
        
        # Get generation range
        gen_ranges = {
            1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493), 5: (494, 649),
            6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025)
        }
        
        start_id, end_id = gen_ranges.get(generation, (1, 151))
        
        self.progress_bar.setRange(0, end_id - start_id + 1)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Syncing Generation {generation}...")
        self.log_output.append(f"🔄 Starting Generation {generation} sync (#{start_id}-#{end_id})")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            success_count = 0
            error_count = 0
            
            for pokedex_num in range(start_id, end_id + 1):
                try:
                    cards = self.tcg_client.search_cards_by_pokedex_number(pokedex_num)
                    if cards:
                        success_count += len(cards)
                        self.log_output.append(f"✓ #{pokedex_num}: {len(cards)} cards")
                    else:
                        self.log_output.append(f"○ #{pokedex_num}: no cards found")
                    
                    self.progress_bar.setValue(pokedex_num - start_id + 1)
                    QApplication.processEvents()
                    
                    # Add a small delay to prevent database locking
                    import time
                    time.sleep(0.1)  # 100ms delay between Pokemon
                    
                except Exception as e:
                    error_count += 1
                    self.log_output.append(f"❌ #{pokedex_num}: {str(e)}")
                    
                    # If too many errors, pause briefly
                    if error_count > 5:
                        self.log_output.append("⏸️ Too many errors, pausing for 2 seconds...")
                        time.sleep(2)
                        error_count = 0
            
            self.progress_label.setText(f"Generation {generation} sync complete! {success_count} cards synced")
            self.log_output.append(f"✅ Generation {generation} complete: {success_count} total cards")
            
        except Exception as e:
            self.log_output.append(f"❌ Generation sync failed: {str(e)}")
            self.progress_label.setText("Generation sync failed")
        
        self.enable_buttons()
    
    def sync_all_generations(self):
        """Sync all generations sequentially"""
        self.disable_buttons()
        self.log_output.append("🚀 Starting full database sync (all generations)")
        
        for gen in range(1, 10):
            self.gen_combo.setCurrentText(f"Generation {gen}")
            self.sync_generation()
            QApplication.processEvents()
    
    def sync_set(self):
        """Sync all cards from a specific set"""
        set_id = self.set_input.text().strip()
        if not set_id:
            QMessageBox.warning(self, "Input Error", "Please enter a set ID")
            return
        
        self.disable_buttons()
        self.progress_label.setText(f"Syncing set {set_id}...")
        self.log_output.append(f"📦 Syncing set: {set_id}")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            cards = self.tcg_client.get_cards_from_set(set_id)
            
            if cards:
                self.log_output.append(f"✓ Set {set_id}: {len(cards)} cards synced")
                self.progress_label.setText(f"Set {set_id} complete! {len(cards)} cards synced")
            else:
                self.log_output.append(f"⚠ No cards found for set {set_id}")
                self.progress_label.setText(f"No cards found for set {set_id}")
                
        except Exception as e:
            self.log_output.append(f"❌ Set sync failed: {str(e)}")
            self.progress_label.setText("Set sync failed")
        
        self.enable_buttons()
    
    def sync_all_sets(self):
        """Sync all available TCG sets"""
        reply = QMessageBox.question(self, "Confirm", 
            "This will sync ALL TCG sets and may take a very long time. Continue?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        self.disable_buttons()
        self.log_output.append("🌐 Starting full TCG database sync...")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            # First, get all sets
            sets = self.tcg_client.get_all_sets()
            self.log_output.append(f"📋 Found {len(sets)} sets")
            
            self.progress_bar.setRange(0, len(sets))
            
            total_cards = 0
            for i, tcg_set in enumerate(sets):
                set_id = tcg_set['id']
                self.progress_label.setText(f"Syncing {set_id}...")
                
                cards = self.tcg_client.get_cards_from_set(set_id)
                total_cards += len(cards)
                
                self.log_output.append(f"✓ {set_id}: {len(cards)} cards")
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()
            
            self.progress_label.setText(f"All sets synced! {total_cards} total cards")
            self.log_output.append(f"🎉 Full sync complete: {total_cards} cards from {len(sets)} sets")
            
        except Exception as e:
            self.log_output.append(f"❌ Full sync failed: {str(e)}")
            self.progress_label.setText("Full sync failed")
        
        self.enable_buttons()
    
    def reset_database(self):
        """Reset the entire database"""
        reply = QMessageBox.question(self, "Confirm Reset", 
            "This will DELETE ALL data in the database. Are you sure?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.db_manager.db_path)
                self.db_manager.init_database()
                self.log_output.append("🗑️ Database reset complete")
                self.progress_label.setText("Database reset")
            except Exception as e:
                self.log_output.append(f"❌ Reset failed: {str(e)}")
    
    def disable_buttons(self):
        """Disable all action buttons during operations"""
        self.pokemon_search_btn.setEnabled(False)
        self.gen_sync_btn.setEnabled(False)
        self.set_sync_btn.setEnabled(False)
        self.sync_all_sets_btn.setEnabled(False)
        self.reset_database_btn.setEnabled(False)
    
    def enable_buttons(self):
        """Re-enable all action buttons"""
        self.pokemon_search_btn.setEnabled(True)
        self.gen_sync_btn.setEnabled(True)
        self.set_sync_btn.setEnabled(True)
        self.sync_all_sets_btn.setEnabled(True)
        self.reset_database_btn.setEnabled(True)

class PokemonCard(QFrame):
    """Updated Pokemon card widget with working image support"""
    
    # Add a signal to notify when a card is imported
    cardImported = pyqtSignal(str, str)  # pokemon_id, card_id
    
    def __init__(self, pokemon_data, user_collection=None, image_loader=None, db_manager=None):
        super().__init__()
        self.pokemon_data = pokemon_data
        self.user_collection = user_collection or {}
        self.image_loader = image_loader or ImageLoader()
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            PokemonCard {
                background-color: #34495e;
                border-radius: 8px;
                margin: 5px;
                border: 2px solid #2c3e50;
            }
            PokemonCard:hover {
                background-color: #3498db;
                border: 2px solid #2980b9;
            }
        """)
        
        self.setFixedWidth(280)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Image container
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setMaximumHeight(350)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("background-color: #2c3e50; border-radius: 4px;")
        
        # Load the card image
        self.refresh_card_display()
        
        layout.addWidget(self.image_label, 1, Qt.AlignCenter)
        
        # Pokemon info
        name_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # Card count info
        card_count = self.pokemon_data.get('card_count', 0)
        if card_count > 0:
            count_label = QLabel(f"{card_count} cards available")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setStyleSheet("color: #3498db; font-size: 10px; background: transparent;")
            layout.addWidget(count_label)
        
        self.setLayout(layout)
        
        # Make clickable for card selection
        self.mousePressEvent = self.show_card_selection
    
    def refresh_card_display(self):
        """Refresh the card display based on current collection state"""
        pokemon_id = str(self.pokemon_data['id'])
        user_card = self.user_collection.get(pokemon_id)
        
        if user_card and user_card.get('image_url'):
            # Load TCG card image
            self.image_loader.load_image(user_card['image_url'], self.image_label, (240, 335))
            self.image_label.setToolTip(f"TCG Card: {user_card['card_name']}")
        else:
            # Show placeholder for now
            self.image_label.setText("Click to\nImport Card")
            self.image_label.setStyleSheet("""
                background-color: #2c3e50; 
                border-radius: 4px; 
                color: #bdc3c7;
                font-size: 12px;
            """)
    
    def show_card_selection(self, event):
        """Show card selection dialog"""
        pokemon_name = self.pokemon_data['name']
        available_cards = self.pokemon_data.get('available_cards', [])
        
        if not available_cards:
            QMessageBox.information(self, "No Cards", 
                f"No TCG cards found for {pokemon_name}.\n"
                "Use 'Sync Data' to search for cards.")
            return
        
        # Create card selection dialog with image loader and db_manager
        dialog = CardSelectionDialog(
            pokemon_name, 
            available_cards,
            pokemon_id=self.pokemon_data['id'],
            image_loader=self.image_loader,
            db_manager=self.db_manager,
            parent=self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            selected_card_id = dialog.get_selected_card()
            if selected_card_id:
                # Import the card
                self.import_card(selected_card_id)
    
    def import_card(self, card_id):
        """Import a card for this Pokemon"""
        if not self.db_manager:
            return
        
        pokemon_id = self.pokemon_data['id']
        
        # Add to database
        self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
        
        # Update our local collection data
        self.user_collection[str(pokemon_id)] = self.get_card_details(card_id)
        
        # Refresh the display
        self.refresh_card_display()
        
        # Emit signal for parent to know about the import
        self.cardImported.emit(str(pokemon_id), card_id)
    
    def get_card_details(self, card_id):
        """Get card details from database"""
        if not self.db_manager:
            return {}
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT card_id, name, image_url_large, set_name
            FROM silver_tcg_cards
            WHERE card_id = ?
        """, (card_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'card_id': result[0],
                'card_name': result[1],
                'image_url': result[2],
                'set_name': result[3]
            }
        return {}


# Updated CardSelectionDialog to accept pokemon_id and db_manager

class CardSelectionDialog(QDialog):
    """Dialog for selecting which TCG card to import"""
    
    def __init__(self, pokemon_name, card_ids, pokemon_id=None, image_loader=None, db_manager=None, parent=None):
        super().__init__(parent)
        self.pokemon_name = pokemon_name
        self.pokemon_id = pokemon_id
        self.card_ids = card_ids
        self.selected_card_id = None
        self.image_loader = image_loader or ImageLoader()
        self.db_manager = db_manager or DatabaseManager()
        self.selected_widget = None
        self.setWindowTitle(f"Select Card for {pokemon_name}")
        self.setMinimumWidth(600)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Select a TCG card for {self.pokemon_name}:")
        title.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(title)
        
        # Card grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        
        row, col = 0, 0
        columns = 3
        
        for card_id in self.card_ids:
            card_info = self.get_card_info(self.db_manager, card_id)
            if card_info:
                card_widget = self.create_card_widget(card_info)
                grid_layout.addWidget(card_widget, row, col)
                
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
        
        scroll_area.setWidget(grid_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        import_btn = QPushButton("Import Selected")
        import_btn.clicked.connect(self.accept)
        import_btn.setEnabled(False)
        self.import_btn = import_btn
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
    
    def get_card_info(self, db_manager, card_id):
        """Get card information from database"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT card_id, name, set_name, artist, rarity, image_url_large, image_url_small
            FROM silver_tcg_cards 
            WHERE card_id = ?
        """, (card_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'card_id': result[0],
                'name': result[1],
                'set_name': result[2],
                'artist': result[3],
                'rarity': result[4],
                'image_url_large': result[5],
                'image_url_small': result[6]
            }
        return None
    
    def create_card_widget(self, card_info):
        """Create a clickable card widget"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box | QFrame.Raised)
        widget.setFixedSize(180, 280)
        widget.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 4px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Card image
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setFixedHeight(160)
        image_label.setScaledContents(False)
        layout.addWidget(image_label)
        
        # Load image
        if card_info['image_url_small']:
            self.image_loader.load_image(card_info['image_url_small'], 
                                       image_label, (150, 160))
        else:
            image_label.setText("No Image")
        
        # Card info
        name_label = QLabel(card_info['name'])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 9, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        set_label = QLabel(f"Set: {card_info['set_name']}")
        set_label.setAlignment(Qt.AlignCenter)
        set_label.setStyleSheet("color: #bdc3c7; font-size: 8px;")
        layout.addWidget(set_label)
        
        if card_info['rarity']:
            rarity_label = QLabel(f"Rarity: {card_info['rarity']}")
            rarity_label.setAlignment(Qt.AlignCenter)
            rarity_label.setStyleSheet("color: #f39c12; font-size: 8px;")
            layout.addWidget(rarity_label)
        
        # Make clickable
        widget.card_id = card_info['card_id']
        widget.card_info = card_info
        widget.mousePressEvent = lambda event: self.select_card(widget)
        
        return widget
    
    def select_card(self, widget):
        """Select a card"""
        # Deselect previous
        if self.selected_widget:
            self.selected_widget.setStyleSheet("""
                QFrame {
                    background-color: #34495e;
                    border: 2px solid #2c3e50;
                    border-radius: 4px;
                }
                QFrame:hover {
                    border: 2px solid #3498db;
                }
            """)
        
        # Select new
        widget.setStyleSheet("""
            QFrame {
                background-color: #3498db;
                border: 2px solid #2980b9;
                border-radius: 4px;
            }
        """)
        
        self.selected_widget = widget
        self.selected_card_id = widget.card_id
        self.import_btn.setEnabled(True)
    
    def get_selected_card(self):
        """Get the selected card ID"""
        return self.selected_card_id
    
class GenerationTab(QWidget):
    """Generation tab with Bronze-Silver-Gold data integration"""
    
    def __init__(self, gen_name, generation_num, db_manager, image_loader=None):
        super().__init__()
        self.gen_name = gen_name
        self.generation_num = generation_num
        self.db_manager = db_manager
        self.image_loader = image_loader or ImageLoader()
        self.pokemon_cards = []  # Keep track of pokemon cards for updates
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel(self.gen_name)
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, 3)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip("Refresh Pokemon data from database")
        refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_button, 1)
        
        main_layout.addLayout(header_layout)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(self.stats_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #34495e;")
        main_layout.addWidget(line)
        
        # Scroll area for Pokemon grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #2c3e50;")
        
        # Load initial data
        self.refresh_data()
        
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
    
    def refresh_data(self):
        """Refresh Pokemon data from Gold layer"""
        # Clear existing cards
        self.pokemon_cards.clear()
        
        # Get Pokemon for this generation
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        # Update stats
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        self.stats_label.setText(
            f"Pokemon: {total_pokemon} | Imported: {imported_count} | Available Cards: {total_cards}"
        )
        
        # Create grid widget
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: #2c3e50;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(15)
        
        # Set up grid
        columns = 4
        for i in range(columns):
            grid_layout.setColumnStretch(i, 1)
        
        # Add Pokemon cards
        row, col = 0, 0
        for pokemon_id, pokemon_info in pokemon_data.items():
            pokemon_card = PokemonCard(
                pokemon_info, 
                user_collection, 
                self.image_loader,
                self.db_manager
            )
            
            # Connect the import signal to refresh just the stats
            pokemon_card.cardImported.connect(self.on_card_imported)
            
            self.pokemon_cards.append(pokemon_card)
            grid_layout.addWidget(pokemon_card, row, col, Qt.AlignCenter)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        # If no Pokemon found, show message
        if not pokemon_data:
            no_data_widget = QWidget()
            no_data_layout = QVBoxLayout(no_data_widget)
            
            no_data_label = QLabel(f"No Pokemon data found for {self.gen_name}")
            no_data_label.setAlignment(Qt.AlignCenter)
            no_data_label.setStyleSheet("color: #7f8c8d; font-size: 16px;")
            no_data_layout.addWidget(no_data_label)
            
            sync_hint = QLabel("Use 'Sync Data' to fetch Pokemon card data from the TCG API")
            sync_hint.setAlignment(Qt.AlignCenter)
            sync_hint.setStyleSheet("color: #95a5a6; font-size: 12px;")
            no_data_layout.addWidget(sync_hint)
            
            grid_layout.addWidget(no_data_widget, 0, 0, 1, columns)
        
        self.scroll_area.setWidget(grid_widget)
    
    def on_card_imported(self, pokemon_id, card_id):
        """Handle card import to update stats without full refresh"""
        # Update just the stats
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        self.stats_label.setText(
            f"Pokemon: {total_pokemon} | Imported: {imported_count} | Available Cards: {total_cards}"
        )

class PokemonDashboard(QMainWindow):
    """Main dashboard with complete Bronze-Silver-Gold architecture"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Initialize shared image loader
        self.image_loader = ImageLoader()
        
        # Set up generations (from database)
        self.load_generations()
        
        self.initUI()
    
    def load_generations(self):
        """Load generation data from database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT generation, name FROM gold_pokemon_generations 
            ORDER BY generation
        """)
        
        self.generations = cursor.fetchall()
        conn.close()
    
    def initUI(self):
        self.setWindowTitle('PokéDextop - TCG Cloud Edition')
        self.setGeometry(100, 100, 1400, 900)
        
        # Dark theme
        self.setStyleSheet("""
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
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Add toolbar
        self.create_toolbar(main_layout)
        
        # Create main tab widget
        self.main_tabs = QTabWidget()
        
        # Create My Pokedex tab
        self.create_pokedex_tab()
        
        # Create TCG Browse tab
        self.create_tcg_browse_tab()
        
        # Create Analytics tab
        self.create_analytics_tab()
        
        main_layout.addWidget(self.main_tabs)
        
        # Status bar
        self.update_status_bar()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_status_bar)
        self.refresh_timer.start(30000)  # Update every 30 seconds
    
    def create_toolbar(self, main_layout):
        """Create application toolbar"""
        toolbar_layout = QHBoxLayout()
        
        # Sync button
        sync_button = QPushButton("🔄 Sync Data")
        sync_button.setToolTip("Sync Pokemon TCG data from API")
        sync_button.clicked.connect(self.open_sync_dialog)
        toolbar_layout.addWidget(sync_button)
        
        toolbar_layout.addSpacing(20)
        
        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: white;")
        toolbar_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Pokemon or cards...")
        self.search_input.setMaximumWidth(200)
        self.search_input.returnPressed.connect(self.perform_search)
        toolbar_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍")
        search_btn.setMaximumWidth(40)
        search_btn.clicked.connect(self.perform_search)
        toolbar_layout.addWidget(search_btn)
        
        toolbar_layout.addStretch()
        
        # Database stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        toolbar_layout.addWidget(self.stats_label)
        
        main_layout.addLayout(toolbar_layout)
    
    def create_pokedex_tab(self):
        """Create the main Pokedex tab"""
        pokedex_tab = QWidget()
        pokedex_layout = QVBoxLayout(pokedex_tab)
        
        # Create generation tabs
        self.gen_tabs = QTabWidget()
        
        for generation, gen_name in self.generations:
            gen_tab = GenerationTab(gen_name, generation, self.db_manager, self.image_loader)
            self.gen_tabs.addTab(gen_tab, f"Gen {generation}")
        
        pokedex_layout.addWidget(self.gen_tabs)
        self.main_tabs.addTab(pokedex_tab, "📚 My Pokédex")
    
    def create_tcg_browse_tab(self):
        """Create TCG browsing tab"""
        tcg_tab = QWidget()
        tcg_layout = QVBoxLayout(tcg_tab)
        
        # Browse options
        browse_layout = QHBoxLayout()
        
        # Set filter
        browse_layout.addWidget(QLabel("Set:"))
        self.set_combo = QComboBox()
        self.set_combo.addItem("All Sets", "all")
        
        # Load sets (with error handling)
        try:
            self.load_sets_combo()
        except Exception as e:
            print(f"Warning: Could not load sets - {e}")
            # Add a message to sync sets first
            self.set_combo.addItem("No sets found - Sync data first", "none")
        
        browse_layout.addWidget(self.set_combo)
        
        # Rarity filter
        browse_layout.addWidget(QLabel("Rarity:"))
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItem("All Rarities", "all")
        
        try:
            self.load_rarities_combo()
        except Exception as e:
            print(f"Warning: Could not load rarities - {e}")
        
        browse_layout.addWidget(self.rarity_combo)
        
        # Apply filters button
        filter_btn = QPushButton("Apply Filters")
        filter_btn.clicked.connect(self.apply_tcg_filters)
        browse_layout.addWidget(filter_btn)
        
        browse_layout.addStretch()
        
        tcg_layout.addLayout(browse_layout)
        
        # TCG cards display area
        self.tcg_scroll = QScrollArea()
        self.tcg_scroll.setWidgetResizable(True)
        self.tcg_scroll.setStyleSheet("background-color: #2c3e50;")
        tcg_layout.addWidget(self.tcg_scroll)
        
        # Load initial TCG data
        try:
            self.apply_tcg_filters()
        except Exception as e:
            print(f"Warning: Could not apply initial filters - {e}")
            # Show empty state
            self.show_empty_tcg_state()
        
        self.main_tabs.addTab(tcg_tab, "🃏 Browse TCG Cards")

    def show_empty_tcg_state(self):
        """Show empty state when no TCG data is available"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        
        empty_label = QLabel("No TCG sets or cards found")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: #7f8c8d; font-size: 16px;")
        empty_layout.addWidget(empty_label)
        
        sync_hint = QLabel("Use 'Sync Data' to fetch TCG sets and cards")
        sync_hint.setAlignment(Qt.AlignCenter)
        sync_hint.setStyleSheet("color: #95a5a6; font-size: 12px;")
        empty_layout.addWidget(sync_hint)
        
        self.tcg_scroll.setWidget(empty_widget)
    
    def create_analytics_tab(self):
        """Create analytics and insights tab"""
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)
        
        # Collection statistics
        stats_group = QGroupBox("Collection Statistics")
        stats_layout = QVBoxLayout()
        
        self.collection_stats_label = QLabel()
        self.collection_stats_label.setStyleSheet("color: white; font-size: 12px;")
        stats_layout.addWidget(self.collection_stats_label)
        
        refresh_stats_btn = QPushButton("Refresh Statistics")
        refresh_stats_btn.clicked.connect(self.update_collection_stats)
        stats_layout.addWidget(refresh_stats_btn)
        
        stats_group.setLayout(stats_layout)
        analytics_layout.addWidget(stats_group)
        
        # Data quality metrics
        quality_group = QGroupBox("Data Quality")
        quality_layout = QVBoxLayout()
        
        self.data_quality_label = QLabel()
        self.data_quality_label.setStyleSheet("color: white; font-size: 12px;")
        quality_layout.addWidget(self.data_quality_label)
        
        quality_group.setLayout(quality_layout)
        analytics_layout.addWidget(quality_group)
        
        # Export options
        export_group = QGroupBox("Export & Backup")
        export_layout = QVBoxLayout()
        
        export_collection_btn = QPushButton("Export Collection")
        export_collection_btn.clicked.connect(self.export_collection)
        export_layout.addWidget(export_collection_btn)
        
        backup_db_btn = QPushButton("Backup Database")
        backup_db_btn.clicked.connect(self.backup_database)
        export_layout.addWidget(backup_db_btn)
        
        export_group.setLayout(export_layout)
        analytics_layout.addWidget(export_group)
        
        analytics_layout.addStretch()
        
        # Update initial stats
        self.update_collection_stats()
        self.update_data_quality_stats()
        
        self.main_tabs.addTab(analytics_tab, "📊 Analytics")
    
    def load_sets_combo(self):
        """Load available sets into combo box"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT set_id, name FROM silver_tcg_sets 
            ORDER BY name
        """)
        
        for row in cursor.fetchall():
            self.set_combo.addItem(f"{row[1]} ({row[0]})", row[0])
        
        conn.close()
    
    def load_rarities_combo(self):
        """Load available rarities into combo box"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT rarity FROM silver_tcg_cards 
            WHERE rarity IS NOT NULL
            ORDER BY rarity
        """)
        
        for row in cursor.fetchall():
            self.rarity_combo.addItem(row[0], row[0])
        
        conn.close()
    
    def apply_tcg_filters(self):
        """Apply filters to TCG card display"""
        # Get filter values
        selected_set = self.set_combo.currentData()
        selected_rarity = self.rarity_combo.currentData()
        
        # Build query
        query = "SELECT card_id, name, set_name, rarity, image_url_small FROM silver_tcg_cards WHERE 1=1"
        params = []
        
        if selected_set != "all":
            query += " AND set_id = ?"
            params.append(selected_set)
        
        if selected_rarity != "all":
            query += " AND rarity = ?"
            params.append(selected_rarity)
        
        query += " ORDER BY name LIMIT 100"  # Limit for performance
        
        # Execute query
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        cards = cursor.fetchall()
        conn.close()
        
        # Display cards
        self.display_tcg_cards(cards)
    
    def display_tcg_cards(self, cards):
        """Display TCG cards in grid"""
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: #2c3e50;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)
        
        columns = 5
        row, col = 0, 0
        
        for card_data in cards:
            card_widget = self.create_tcg_card_widget(card_data, self.image_loader)
            grid_layout.addWidget(card_widget, row, col)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        if not cards:
            no_cards_label = QLabel("No cards found with current filters")
            no_cards_label.setAlignment(Qt.AlignCenter)
            no_cards_label.setStyleSheet("color: #7f8c8d; font-size: 16px;")
            grid_layout.addWidget(no_cards_label, 0, 0, 1, columns)
        
        self.tcg_scroll.setWidget(grid_widget)
    
    def create_tcg_card_widget(self, card_data, image_loader=None):
        """Create a TCG card display widget"""
        card_id, name, set_name, rarity, image_url = card_data
        
        if not image_loader:
            image_loader = self.image_loader
        
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box | QFrame.Raised)
        widget.setFixedSize(150, 220)
        widget.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 4px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Card image
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setFixedHeight(120)
        image_label.setScaledContents(False)
        layout.addWidget(image_label)
        
        # Load image if URL exists
        if image_url:
            image_loader.load_image(image_url, image_label, (140, 120))
        else:
            image_label.setText("No Image")
            image_label.setStyleSheet("background-color: #2c3e50; border-radius: 2px; color: #7f8c8d;")
        
        # Card name
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 8, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # Set and rarity
        info_label = QLabel(f"{set_name}\n{rarity or 'Unknown'}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #bdc3c7; font-size: 7px;")
        layout.addWidget(info_label)
        
        # Make clickable for import
        widget.card_id = card_id
        widget.mousePressEvent = lambda event: self.quick_import_card(card_id, name)
        
        return widget
    
    def quick_import_card(self, card_id, card_name):
        """Quick import a card to collection"""
        # Extract Pokemon name and try to import
        pokemon_name = self.extract_pokemon_name(card_name)
        if pokemon_name:
            # Find Pokemon ID
            pokemon_id = self.find_pokemon_id_by_name(pokemon_name)
            if pokemon_id:
                self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
                QMessageBox.information(self, "Import Success", 
                    f"Imported {card_name} for {pokemon_name}!")
                self.refresh_all_tabs()
            else:
                QMessageBox.warning(self, "Import Failed", 
                    f"Could not find Pokemon '{pokemon_name}' in database")
        else:
            QMessageBox.warning(self, "Import Failed", 
                f"Could not determine Pokemon from card name: {card_name}")
    
    def extract_pokemon_name(self, card_name):
        """Extract Pokemon name from card (simplified version)"""
        import re
        
        # Remove prefixes and suffixes
        clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION).*$', '', clean_name)
        
        # Handle possessive forms
        possessive_match = re.match(r"(\w+\'s)\s+(\w+(?:\s+\w+)?)", clean_name)
        if possessive_match:
            return possessive_match.group(2)
        
        return clean_name.strip()
    
    def find_pokemon_id_by_name(self, pokemon_name):
        """Find Pokemon ID by name in database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pokemon_id FROM silver_pokemon_master 
            WHERE LOWER(name) = LOWER(?)
        """, (pokemon_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def perform_search(self):
        """Perform search across Pokemon and cards"""
        search_term = self.search_input.text().strip()
        if not search_term:
            return
        
        # Search in database
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Search Pokemon
        cursor.execute("""
            SELECT pokemon_id, name, generation FROM silver_pokemon_master 
            WHERE name LIKE ? 
            ORDER BY name
        """, (f'%{search_term}%',))
        
        pokemon_results = cursor.fetchall()
        
        # Search cards
        cursor.execute("""
            SELECT card_id, name, set_name FROM silver_tcg_cards 
            WHERE name LIKE ? 
            ORDER BY name 
            LIMIT 20
        """, (f'%{search_term}%',))
        
        card_results = cursor.fetchall()
        conn.close()
        
        # Show results dialog
        self.show_search_results(search_term, pokemon_results, card_results)
    
    def show_search_results(self, search_term, pokemon_results, card_results):
        """Show search results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Search Results: '{search_term}'")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Pokemon results
        if pokemon_results:
            layout.addWidget(QLabel(f"Pokemon ({len(pokemon_results)} found):"))
            pokemon_list = QLabel()
            pokemon_text = "\n".join([f"#{p[0]} {p[1]} (Gen {p[2]})" for p in pokemon_results])
            pokemon_list.setText(pokemon_text)
            pokemon_list.setStyleSheet("color: white; background-color: #34495e; padding: 10px;")
            layout.addWidget(pokemon_list)
        
        # Card results
        if card_results:
            layout.addWidget(QLabel(f"Cards ({len(card_results)} found):"))
            card_list = QLabel()
            card_text = "\n".join([f"{c[1]} ({c[2]})" for c in card_results])
            card_list.setText(card_text)
            card_list.setStyleSheet("color: white; background-color: #34495e; padding: 10px;")
            layout.addWidget(card_list)
        
        if not pokemon_results and not card_results:
            layout.addWidget(QLabel("No results found"))
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def open_sync_dialog(self):
        """Open the data sync dialog"""
        dialog = DataSyncDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_all_tabs()
            self.update_status_bar()
    
    def refresh_all_tabs(self):
        """Refresh all generation tabs"""
        for i in range(self.gen_tabs.count()):
            gen_tab = self.gen_tabs.widget(i)
            if hasattr(gen_tab, 'refresh_data'):
                gen_tab.refresh_data()
    
    def update_status_bar(self):
        """Update the status bar with current statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM silver_pokemon_master")
        pokemon_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM silver_tcg_cards")
        card_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gold_user_collections")
        imported_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT set_id) FROM silver_tcg_sets")
        set_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Update displays
        status_text = f"Pokemon: {pokemon_count} | Cards: {card_count} | Sets: {set_count} | Imported: {imported_count}"
        self.statusBar().showMessage(status_text)
        self.stats_label.setText(status_text)
    
    def update_collection_stats(self):
        """Update detailed collection statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Collection completion by generation
        cursor.execute("""
            SELECT g.generation, g.name, 
                   COUNT(p.pokemon_id) as total_pokemon,
                   COUNT(uc.pokemon_id) as imported_pokemon
            FROM gold_pokemon_generations g
            LEFT JOIN silver_pokemon_master p ON g.generation = p.generation
            LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
            GROUP BY g.generation, g.name
            ORDER BY g.generation
        """)
        
        gen_stats = cursor.fetchall()
        
        # Build stats text
        stats_text = "Collection Completion by Generation:\n\n"
        total_pokemon = 0
        total_imported = 0
        
        for gen_num, gen_name, pokemon_count, imported_count in gen_stats:
            if pokemon_count > 0:
                completion_rate = (imported_count / pokemon_count) * 100
                stats_text += f"{gen_name}: {imported_count}/{pokemon_count} ({completion_rate:.1f}%)\n"
                total_pokemon += pokemon_count
                total_imported += imported_count
        
        if total_pokemon > 0:
            overall_completion = (total_imported / total_pokemon) * 100
            stats_text += f"\nOverall: {total_imported}/{total_pokemon} ({overall_completion:.1f}%)"
        
        self.collection_stats_label.setText(stats_text)
        conn.close()
    
    def update_data_quality_stats(self):
        """Update data quality metrics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Data freshness
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN datetime(data_pull_timestamp) > datetime('now', '-7 days') THEN 1 END) as recent_records
            FROM bronze_tcg_cards
        """)
        
        total_records, recent_records = cursor.fetchone()
        
        # Missing images
        cursor.execute("""
            SELECT COUNT(*) FROM silver_tcg_cards 
            WHERE image_url_large IS NULL OR image_url_small IS NULL
        """)
        
        missing_images = cursor.fetchone()[0]
        
        quality_text = f"Data Quality Metrics:\n\n"
        quality_text += f"Total Records: {total_records}\n"
        quality_text += f"Recent (7 days): {recent_records}\n"
        quality_text += f"Missing Images: {missing_images}\n"
        
        if total_records > 0:
            freshness_rate = (recent_records / total_records) * 100
            quality_text += f"Data Freshness: {freshness_rate:.1f}%"
        
        self.data_quality_label.setText(quality_text)
        conn.close()
    
    def export_collection(self):
        """Export user collection to JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection", "my_pokemon_collection.json", 
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                collection = self.db_manager.get_user_collection()
                
                with open(file_path, 'w') as f:
                    json.dump(collection, f, indent=2)
                
                QMessageBox.information(self, "Export Complete", 
                    f"Collection exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")
    
    def backup_database(self):
        """Create a backup of the database"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", 
            f"pokedextop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", 
            "Database files (*.db)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.db_manager.db_path, file_path)
                QMessageBox.information(self, "Backup Complete", 
                    f"Database backed up to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")

def center_window(window):
    """Center the window on the screen"""
    frame_geometry = window.frameGeometry()
    screen_center = QApplication.desktop().availableGeometry().center()
    frame_geometry.moveCenter(screen_center)
    window.move(frame_geometry.topLeft())

def main():
    try:
        print("==== STARTING POKEDEXTOP TCG CLOUD EDITION ====")
        print("Bronze-Silver-Gold Data Architecture Initialized")
        
        # Create the application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Create the main window
        main_window = PokemonDashboard()
        
        # Center and show window
        main_window.resize(1400, 900)
        center_window(main_window)
        main_window.show()
        
        print("Application ready! Use 'Sync Data' to fetch Pokemon TCG cards.")
        
        # Enter main loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"CRITICAL APPLICATION ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()