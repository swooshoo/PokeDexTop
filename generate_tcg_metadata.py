#!/usr/bin/env python
"""
TCG Metadata Generator

This script scans the TCG card directories and generates a complete metadata file
that includes information about all sets and cards.

Usage:
    python generate_tcg_metadata.py

The script will:
1. Scan the assets/tcg_cards directory for all set folders
2. Process each PNG file in each set
3. Generate metadata using filenames and any existing metadata
4. Save the complete metadata to assets/tcg_cards/index.json
"""

import os
import json
import glob
import re
from PIL import Image

# Paths
TCG_CARDS_PATH = os.path.join('assets', 'tcg_cards')
TCG_METADATA_FILE = os.path.join(TCG_CARDS_PATH, 'index.json')

def extract_card_info(filename):
    """Extract card information from filename."""
    # Remove extension
    base_name = os.path.basename(filename).split('.')[0]
    
    # Try to extract number at the beginning
    card_id = None
    card_name = base_name
    
    # Match pattern: start with numbers followed by space then text
    match = re.match(r'^(\d+)\s+(.+)$', base_name)
    if match:
        card_id = match.group(1)
        card_name = match.group(2)
    
    # Format card name nicely
    card_name = card_name.replace('_', ' ').strip()
    
    return {
        'id': card_id or base_name,
        'name': card_name
    }

def main():
    print("TCG Metadata Generator")
    print("======================")
    
    # Check if TCG cards directory exists
    if not os.path.exists(TCG_CARDS_PATH):
        print(f"Error: TCG cards directory not found at {TCG_CARDS_PATH}")
        return
    
    # Load existing metadata if available
    existing_metadata = {}
    if os.path.exists(TCG_METADATA_FILE):
        try:
            with open(TCG_METADATA_FILE, 'r') as f:
                existing_metadata = json.load(f)
                print(f"Loaded existing metadata with {len(existing_metadata.get('sets', {}))} sets")
        except Exception as e:
            print(f"Error loading existing metadata: {e}")
            print("Starting with empty metadata")
    
    # Initialize new metadata structure
    new_metadata = {
        'sets': {},
        'total_sets': 0,
        'total_cards': 0
    }
    
    # If existing metadata has structure we want to preserve, use it as base
    if 'sets' in existing_metadata:
        new_metadata['sets'] = existing_metadata['sets']
    
    # Get all set directories
    set_dirs = [d for d in os.listdir(TCG_CARDS_PATH) 
               if os.path.isdir(os.path.join(TCG_CARDS_PATH, d)) and d != '.git']
    
    print(f"Found {len(set_dirs)} set directories")
    
    # Process each set directory
    total_cards = 0
    for set_dir in sorted(set_dirs):
        set_path = os.path.join(TCG_CARDS_PATH, set_dir)
        print(f"Processing set: {set_dir}")
        
        # Find all PNG files in the set directory
        card_files = glob.glob(os.path.join(set_path, "*.png"))
        
        # Skip if no cards found
        if not card_files:
            print(f"  No card images found in {set_dir}, skipping")
            continue
        
        # Get or create set metadata
        if set_dir not in new_metadata['sets']:
            # Create new set entry
            set_name = set_dir.replace('_', ' ').title()
            new_metadata['sets'][set_dir] = {
                'name': set_name,
                'path': set_path.replace('\\', '/'),  # Use forward slashes for cross-platform compatibility
                'cards': {},
                'total_cards': 0
            }
        
        set_metadata = new_metadata['sets'][set_dir]
        
        # Process each card file
        for card_file in card_files:
            filename = os.path.basename(card_file).split('.')[0]
            
            # Skip if card already in metadata
            if filename in set_metadata['cards']:
                continue
            
            # Extract card info from filename
            card_info = extract_card_info(filename)
            
            # Get image dimensions
            try:
                with Image.open(card_file) as img:
                    width, height = img.size
                    card_info['width'] = width
                    card_info['height'] = height
            except Exception as e:
                print(f"  Warning: Could not process image {card_file}: {e}")
            
            # Add image path
            card_info['image_path'] = card_file.replace('\\', '/')  # Use forward slashes
            
            # Add to set metadata
            set_metadata['cards'][filename] = card_info
        
        # Update set card count
        set_metadata['total_cards'] = len(set_metadata['cards'])
        total_cards += set_metadata['total_cards']
        
        print(f"  Processed {set_metadata['total_cards']} cards in {set_dir}")
    
    # Update metadata totals
    new_metadata['total_sets'] = len(new_metadata['sets'])
    new_metadata['total_cards'] = total_cards
    
    # Save the updated metadata
    try:
        with open(TCG_METADATA_FILE, 'w') as f:
            json.dump(new_metadata, f, indent=2)
        print(f"Metadata saved to {TCG_METADATA_FILE}")
        print(f"Total sets: {new_metadata['total_sets']}")
        print(f"Total cards: {new_metadata['total_cards']}")
    except Exception as e:
        print(f"Error saving metadata: {e}")
    
if __name__ == "__main__":
    main()