#!/usr/bin/env python3
"""
Simple Pokémon sprite downloader
Downloads all sprites to assets/sprites/pokemon/
No config dependencies - standalone script

Usage: python scripts/download_sprites.py
"""

import sys
import os
import requests
import time
from pathlib import Path

def download_all_sprites():
    """Download sprites for all 1,025 Pokémon"""
    # Get project root (parent directory of scripts)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Create sprites directory
    sprites_dir = project_root / 'assets' / 'sprites' / 'pokemon'
    sprites_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading sprites to: {sprites_dir}")
    
    success_count = 0
    failed_ids = []
    
    for pokemon_id in range(1, 1026):  # 1-1025
        sprite_path = sprites_dir / f"{pokemon_id}.png"
        
        if sprite_path.exists():
            print(f"✓ #{pokemon_id:4d} already exists")
            success_count += 1
            continue
        
        # Try multiple sources for better coverage
        urls = [
            f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png",
            f"https://assets.pokemon.com/assets/cms2/img/pokedex/detail/{pokemon_id:03d}.png",
            f"https://img.pokemondb.net/sprites/home/normal/{pokemon_id}.png"
        ]
        
        downloaded = False
        for i, url in enumerate(urls):
            try:
                print(f"⬇️  #{pokemon_id:4d} trying source {i+1}...", end="")
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(sprite_path, 'wb') as f:
                        f.write(response.content)
                    print(f" ✅ Success!")
                    success_count += 1
                    downloaded = True
                    break
                else:
                    print(f" ❌ {response.status_code}")
            except Exception as e:
                print(f" ❌ Error: {str(e)[:30]}")
        
        if not downloaded:
            print(f"❌ #{pokemon_id:4d} Could not download from any source")
            failed_ids.append(pokemon_id)
        
        # Rate limiting to be nice to servers
        time.sleep(0.1)
    
    print(f"\n🎉 Results:")
    print(f"   ✅ Downloaded: {success_count}/1025 sprites")
    print(f"   ❌ Failed: {len(failed_ids)} sprites")
    
    if failed_ids:
        print(f"\n📝 Failed Pokemon IDs: {failed_ids[:20]}")  # Show first 20
        if len(failed_ids) > 20:
            print(f"   ... and {len(failed_ids) - 20} more")
    
    print(f"\n📁 Sprites saved to: {sprites_dir}")
    
    # Create a simple placeholder for failed downloads
    if failed_ids:
        create_placeholder_sprite(sprites_dir)

def create_placeholder_sprite(sprites_dir):
    """Create a simple placeholder sprite for missing Pokemon"""
    placeholder_dir = sprites_dir.parent / 'placeholders'
    placeholder_dir.mkdir(exist_ok=True)
    
    placeholder_path = placeholder_dir / 'missing.png'
    
    # Create a simple placeholder using PIL if available, otherwise skip
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create 96x96 placeholder image
        img = Image.new('RGBA', (96, 96), (240, 240, 240, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw a simple "?" 
        try:
            font = ImageFont.truetype("Arial", 24)
        except:
            font = ImageFont.load_default()
        
        # Draw question mark
        draw.text((48, 48), "?", fill=(128, 128, 128, 255), anchor="mm", font=font)
        
        # Draw border
        draw.rectangle([0, 0, 95, 95], outline=(200, 200, 200, 255), width=2)
        
        img.save(placeholder_path)
        print(f"📝 Created placeholder: {placeholder_path}")
        
    except ImportError:
        print("📝 Skipping placeholder creation (PIL not available)")

if __name__ == '__main__':
    print("🎮 PokéDextop Sprite Downloader")
    print("=" * 40)
    download_all_sprites()