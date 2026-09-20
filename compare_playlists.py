#!/usr/bin/env python3
"""
Compare metadata between two YouTube playlists to find differences
"""

import yt_dlp
import json
import sys

def get_playlist_info(playlist_id):
    """Extract comprehensive info from a playlist"""
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    
    ydl_opts = {
        'quiet': False,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'verbose': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"\n{'='*80}")
            print(f"Extracting info for: {playlist_id}")
            print(f"URL: {url}")
            print(f"{'='*80}\n")
            
            info = ydl.extract_info(url, download=False)
            
            return info
    except Exception as e:
        print(f"\n❌ ERROR extracting {playlist_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_playlist(info, label):
    """Analyze and display key info about a playlist"""
    if not info:
        print(f"\n❌ No info available for {label}\n")
        return
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS: {label}")
    print(f"{'='*80}\n")
    
    # Basic info
    print(f"Title: {info.get('title', 'N/A')}")
    print(f"ID: {info.get('id', 'N/A')}")
    print(f"Uploader: {info.get('uploader', 'N/A')}")
    print(f"Channel: {info.get('channel', 'N/A')}")
    print(f"Channel ID: {info.get('channel_id', 'N/A')}")
    
    # Entry info
    entries = info.get('entries', [])
    print(f"\nTotal Entries: {len(entries)}")
    
    if entries:
        print(f"\nFirst 3 entries:")
        for i, entry in enumerate(entries[:3], 1):
            print(f"\n  Entry {i}:")
            print(f"    ID: {entry.get('id', 'N/A')}")
            print(f"    Title: {entry.get('title', 'N/A')}")
            print(f"    Duration: {entry.get('duration', 'N/A')} seconds")
            print(f"    URL: {entry.get('url', 'N/A')}")
            
            # Check for format info
            formats = entry.get('formats')
            if formats:
                print(f"    Formats available: {len(formats)}")
            else:
                print(f"    Formats available: None (needs expansion)")
    
    # Availability info
    print(f"\nAvailability: {info.get('availability', 'N/A')}")
    print(f"Age Limit: {info.get('age_limit', 'N/A')}")
    print(f"Live Status: {info.get('live_status', 'N/A')}")
    
    # Technical details
    print(f"\nExtractor: {info.get('extractor', 'N/A')}")
    print(f"Extractor Key: {info.get('extractor_key', 'N/A')}")
    print(f"Webpage URL: {info.get('webpage_url', 'N/A')}")
    
    # Check for any error indicators
    if 'error' in info:
        print(f"\n⚠️  ERROR field present: {info.get('error')}")
    
    # Save full info to file
    filename = f"playlist_{label.lower().replace(' ', '_')}.json"
    with open(filename, 'w') as f:
        json.dump(info, f, indent=2, default=str)
    print(f"\n✅ Full metadata saved to: {filename}")

def compare_playlists(info1, info2, label1, label2):
    """Compare two playlists and highlight differences"""
    print(f"\n{'='*80}")
    print(f"COMPARISON: {label1} vs {label2}")
    print(f"{'='*80}\n")
    
    if not info1 or not info2:
        print("❌ Cannot compare - one or both playlists failed to load")
        return
    
    # Compare basic attributes
    attrs_to_compare = [
        'title', 'uploader', 'channel', 'channel_id', 'availability',
        'age_limit', 'live_status', 'extractor', 'extractor_key'
    ]
    
    print("Attribute Comparison:")
    print("-" * 80)
    for attr in attrs_to_compare:
        val1 = info1.get(attr, 'N/A')
        val2 = info2.get(attr, 'N/A')
        
        if val1 == val2:
            print(f"✓ {attr:20s}: SAME ({val1})")
        else:
            print(f"✗ {attr:20s}: DIFFERENT")
            print(f"  {label1:20s}: {val1}")
            print(f"  {label2:20s}: {val2}")
    
    # Compare entry counts
    entries1 = info1.get('entries', [])
    entries2 = info2.get('entries', [])
    
    print(f"\n{'='*80}")
    print(f"Entry count: {len(entries1)} vs {len(entries2)}")
    
    if entries1 and entries2:
        print(f"\nComparing first entry structure:")
        entry1 = entries1[0]
        entry2 = entries2[0]
        
        # Get all keys from both entries
        all_keys = set(entry1.keys()) | set(entry2.keys())
        
        print(f"\nKeys in {label1} entry: {sorted(entry1.keys())}")
        print(f"\nKeys in {label2} entry: {sorted(entry2.keys())}")
        
        only_in_1 = set(entry1.keys()) - set(entry2.keys())
        only_in_2 = set(entry2.keys()) - set(entry1.keys())
        
        if only_in_1:
            print(f"\n⚠️  Keys ONLY in {label1}: {sorted(only_in_1)}")
        if only_in_2:
            print(f"\n⚠️  Keys ONLY in {label2}: {sorted(only_in_2)}")

def main():
    # Playlist IDs
    working_id = "OLAK5uy_lk27ot5n0ywBWU37ybUjph2zDqQCnmlvg"
    failing_id = "OLAK5uy_kYQDmljomL0q1D1z3oCgogl6QHe36cR3c"
    
    print("\n" + "="*80)
    print("YouTube Playlist Metadata Comparison Tool")
    print("="*80)
    
    # Extract info from both playlists
    print("\n[1/4] Extracting WORKING playlist...")
    working_info = get_playlist_info(working_id)
    
    print("\n[2/4] Extracting FAILING playlist...")
    failing_info = get_playlist_info(failing_id)
    
    # Analyze each
    print("\n[3/4] Analyzing playlists...")
    analyze_playlist(working_info, "WORKING")
    analyze_playlist(failing_info, "FAILING")
    
    # Compare
    print("\n[4/4] Comparing playlists...")
    compare_playlists(working_info, failing_info, "WORKING", "FAILING")
    
    print("\n" + "="*80)
    print("✅ Analysis complete!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()