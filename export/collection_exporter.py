# export/collection_exporter.py
"""
Collection Exporter - Clean orchestration module
Handles export business logic without UI concerns
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from data.database import DatabaseManager


class ExportFormat(Enum):
    """Supported export formats"""
    PNG = "png"
    JSON = "json"
    CSV = "csv"
    HTML = "html"


class ExportQuality(Enum):
    """Export quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CollectionExporter:
    """Main collection exporter orchestrator"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.export_history = []
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default export configuration"""
        return {
            'custom_title': 'My Pokémon Collection',
            'include_pokedex_info': True,
            'include_set_label': True,
            'include_artist_label': False,
            'cards_per_row': 4,
            'image_quality': ExportQuality.HIGH.value,
            'generation_filter': 'all',
            'format': ExportFormat.PNG.value,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'app_version': '1.0',
                'export_version': '1.0',
                'created_by': 'PokéDextop'
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize export configuration"""
        validated_config = self.get_default_config()
        validated_config.update(config)
        
        # Validate specific fields
        if validated_config['cards_per_row'] < 2:
            validated_config['cards_per_row'] = 2
        elif validated_config['cards_per_row'] > 8:
            validated_config['cards_per_row'] = 8
        
        # Ensure quality is valid
        if validated_config['image_quality'] not in [q.value for q in ExportQuality]:
            validated_config['image_quality'] = ExportQuality.HIGH.value
        
        # Ensure format is valid
        if validated_config['format'] not in [f.value for f in ExportFormat]:
            validated_config['format'] = ExportFormat.PNG.value
        
        return validated_config
    
    def get_collection_summary(self, generation_filter: Union[str, int] = 'all') -> Dict[str, Any]:
        """Get collection summary for export planning"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Base query
        base_query = """
            SELECT COUNT(*) as total_cards,
                   COUNT(DISTINCT p.generation) as generations,
                   COUNT(DISTINCT p.pokemon_id) as unique_pokemon,
                   COUNT(DISTINCT c.set_id) as unique_sets
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
            JOIN silver_tcg_cards c ON uc.card_id = c.card_id
        """
        
        if generation_filter != 'all':
            base_query += " WHERE p.generation = ?"
            cursor.execute(base_query, (generation_filter,))
        else:
            cursor.execute(base_query)
        
        result = cursor.fetchone()
        
        # Get generation breakdown
        gen_query = """
            SELECT p.generation, g.name, COUNT(*) as card_count
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
            JOIN gold_pokemon_generations g ON p.generation = g.generation
        """
        
        if generation_filter != 'all':
            gen_query += " WHERE p.generation = ?"
            cursor.execute(gen_query + " GROUP BY p.generation, g.name ORDER BY p.generation", (generation_filter,))
        else:
            cursor.execute(gen_query + " GROUP BY p.generation, g.name ORDER BY p.generation")
        
        generations = cursor.fetchall()
        conn.close()
        
        return {
            'total_cards': result[0] if result else 0,
            'total_generations': result[1] if result else 0,
            'unique_pokemon': result[2] if result else 0,
            'unique_sets': result[3] if result else 0,
            'generation_breakdown': [
                {
                    'generation': gen[0],
                    'name': gen[1],
                    'card_count': gen[2]
                }
                for gen in generations
            ],
            'has_content': (result[0] if result else 0) > 0
        }
    
    def estimate_export_size(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate the export file size and dimensions"""
        validated_config = self.validate_config(config)
        summary = self.get_collection_summary(validated_config['generation_filter'])
        
        if summary['total_cards'] == 0:
            return {
                'estimated_file_size_mb': 0,
                'image_dimensions': (0, 0),
                'grid_dimensions': (0, 0),
                'warnings': ['No cards in collection']
            }
        
        # Calculate grid dimensions
        cards_per_row = validated_config['cards_per_row']
        total_cards = summary['total_cards']
        rows = (total_cards + cards_per_row - 1) // cards_per_row  # Ceiling division
        
        # Calculate image dimensions based on quality
        quality_settings = {
            ExportQuality.HIGH.value: {'card_size': (245, 342), 'spacing': 20},
            ExportQuality.MEDIUM.value: {'card_size': (180, 252), 'spacing': 15},
            ExportQuality.LOW.value: {'card_size': (120, 168), 'spacing': 10}
        }
        
        settings = quality_settings[validated_config['image_quality']]
        card_width, card_height = settings['card_size']
        spacing = settings['spacing']
        
        # Calculate total dimensions
        header_height = 80
        footer_height = 60
        label_height = 60 if any([
            validated_config['include_pokedex_info'],
            validated_config['include_set_label'], 
            validated_config['include_artist_label']
        ]) else 0
        
        total_width = (cards_per_row * card_width) + ((cards_per_row + 1) * spacing)
        total_height = header_height + (rows * (card_height + label_height + spacing)) + spacing + footer_height
        
        # Estimate file size (rough calculation)
        pixel_count = total_width * total_height
        estimated_size_mb = (pixel_count * 4) / (1024 * 1024)  # 4 bytes per pixel for RGBA
        
        # Add warnings for large exports
        warnings = []
        if total_width > 10000 or total_height > 10000:
            warnings.append("Very large image dimensions - may cause memory issues")
        if estimated_size_mb > 100:
            warnings.append(f"Large file size estimated: {estimated_size_mb:.1f}MB")
        if total_cards > 500:
            warnings.append("Large collection - export may take several minutes")
        
        return {
            'estimated_file_size_mb': round(estimated_size_mb, 2),
            'image_dimensions': (total_width, total_height),
            'grid_dimensions': (cards_per_row, rows),
            'card_dimensions': (card_width, card_height),
            'total_cards': total_cards,
            'warnings': warnings
        }
    
    def generate_export_filename(self, config: Dict[str, Any]) -> str:
        """Generate a safe filename for export"""
        validated_config = self.validate_config(config)
        
        # Create safe filename from title
        title = validated_config['custom_title']
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_').lower()
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Add generation info if filtered
        gen_suffix = ""
        if validated_config['generation_filter'] != 'all':
            gen_suffix = f"_gen{validated_config['generation_filter']}"
        
        # Add format extension
        format_ext = validated_config['format']
        
        return f"{safe_title}{gen_suffix}_{timestamp}.{format_ext}"
    
    def export_as_json(self, config: Dict[str, Any], file_path: str) -> bool:
        """Export collection as JSON"""
        try:
            validated_config = self.validate_config(config)
            collection_data = self.get_collection_data(validated_config['generation_filter'])
            summary = self.get_collection_summary(validated_config['generation_filter'])
            
            export_data = {
                'metadata': validated_config['metadata'],
                'export_config': validated_config,
                'collection_summary': summary,
                'cards': collection_data,
                'exported_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self._record_export(file_path, ExportFormat.JSON, validated_config)
            return True
            
        except Exception as e:
            print(f"JSON export failed: {e}")
            return False
    
    def export_as_csv(self, config: Dict[str, Any], file_path: str) -> bool:
        """Export collection as CSV"""
        try:
            import csv
            
            validated_config = self.validate_config(config)
            collection_data = self.get_collection_data(validated_config['generation_filter'])
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if not collection_data:
                    return False
                
                # Get all possible field names
                fieldnames = set()
                for card in collection_data:
                    fieldnames.update(card.keys())
                
                fieldnames = sorted(fieldnames)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(collection_data)
            
            self._record_export(file_path, ExportFormat.CSV, validated_config)
            return True
            
        except Exception as e:
            print(f"CSV export failed: {e}")
            return False
    
    def get_collection_data(self, generation_filter: Union[str, int] = 'all') -> List[Dict[str, Any]]:
        """Get collection data for export"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Build query based on generation filter
        if generation_filter == 'all':
            query = """
                SELECT uc.pokemon_id, uc.card_id, p.name as pokemon_name,
                       c.name as card_name, c.set_name, c.artist, c.rarity,
                       c.image_url_large, c.image_url_small, p.generation,
                       c.supertype, c.subtypes, c.types, c.hp, c.number,
                       uc.imported_at, uc.notes
                FROM gold_user_collections uc
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                ORDER BY p.pokemon_id
            """
            cursor.execute(query)
        else:
            query = """
                SELECT uc.pokemon_id, uc.card_id, p.name as pokemon_name,
                       c.name as card_name, c.set_name, c.artist, c.rarity,
                       c.image_url_large, c.image_url_small, p.generation,
                       c.supertype, c.subtypes, c.types, c.hp, c.number,
                       uc.imported_at, uc.notes
                FROM gold_user_collections uc
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                WHERE p.generation = ?
                ORDER BY p.pokemon_id
            """
            cursor.execute(query, (generation_filter,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'pokemon_id': row[0],
                'card_id': row[1],
                'pokemon_name': row[2],
                'card_name': row[3],
                'set_name': row[4],
                'artist': row[5],
                'rarity': row[6],
                'image_url_large': row[7],
                'image_url_small': row[8],
                'generation': row[9],
                'supertype': row[10],
                'subtypes': row[11],
                'types': row[12],
                'hp': row[13],
                'number': row[14],
                'imported_at': row[15],
                'notes': row[16]
            }
            for row in results
        ]
    
    def _record_export(self, file_path: str, format_type: ExportFormat, config: Dict[str, Any]):
        """Record export in history"""
        export_record = {
            'file_path': file_path,
            'format': format_type.value,
            'exported_at': datetime.now().isoformat(),
            'config': config,
            'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        self.export_history.append(export_record)
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get export history"""
        return self.export_history.copy()
    
    def cleanup_temp_files(self):
        """Clean up any temporary files created during export"""
        # Implementation for cleaning up temp files if needed
        pass


# Utility functions
def validate_export_path(file_path: str) -> bool:
    """Validate that export path is writable"""
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Test write access
        test_file = file_path + '.test'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
        
    except (OSError, IOError, PermissionError):
        return False


def get_supported_formats() -> List[str]:
    """Get list of supported export formats"""
    return [format_type.value for format_type in ExportFormat]


def get_quality_options() -> List[str]:
    """Get list of quality options"""
    return [quality.value for quality in ExportQuality]