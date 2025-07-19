#!/usr/bin/env python3
"""
Test script to verify local sprite system is working, associated with Issue 52
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from cache.manager import CacheManager

def test_local_sprites():
    """Test local sprite detection and caching"""
    print("🧪 Testing Local Sprite System")
    print("=" * 40)
    
    # Initialize cache manager
    cache_manager = CacheManager()
    
    # Test some Generation 9 Pokemon that were failing
    test_pokemon = ['966', '945', '951', '971', '942']
    
    for pokemon_id in test_pokemon:
        print(f"\n🔍 Testing Pokemon #{pokemon_id}")
        
        # Test local sprite detection
        local_path = cache_manager.get_local_sprite_path(pokemon_id)
        if local_path:
            print(f"  ✅ Local sprite found: {local_path}")
            print(f"  📁 File size: {local_path.stat().st_size} bytes")
        else:
            print(f"  ❌ No local sprite found")
        
        # Test cache_image method
        fake_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
        cached_path = cache_manager.cache_image(fake_url, pokemon_id, 'sprite', 'ui')
        
        if cached_path:
            print(f"  ✅ Cached successfully: {cached_path}")
        else:
            print(f"  ❌ Caching failed")
    
    print(f"\n📊 Cache Statistics:")
    stats = cache_manager.get_cache_stats()
    print(f"  Total files: {stats.get('totals', {}).get('files', 0)}")
    print(f"  Total size: {stats.get('totals', {}).get('size', 0)} bytes")

if __name__ == '__main__':
    test_local_sprites()