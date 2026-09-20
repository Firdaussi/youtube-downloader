#!/usr/bin/env python3
"""
Test download with EXACT same settings as the app to debug format issue
"""

import yt_dlp
import os

def test_download_exact():
    """Test with exact same config as the app"""
    video_id = "FGMfNg-IEHI"
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Mimic your app's exact configuration
    ydl_opts = {
        'format': 'best',  # Simplest possible
        'outtmpl': f'test_exact_{video_id}.%(ext)s',
        'quiet': False,
        'verbose': True,  # Get detailed output
        'no_warnings': False,
        'merge_output_format': 'mp4',
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 3,
        'ignoreerrors': False,
        'geo_bypass': True,
        'extractor_args': {
            'youtubetab': {
                'skip': ['authcheck']
            },
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    
    print(f"\n{'='*80}")
    print(f"Testing with EXACT app configuration")
    print(f"Video: {video_id}")
    print(f"URL: {url}")
    print(f"Format: {ydl_opts['format']}")
    print(f"{'='*80}\n")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\n✅ SUCCESS: Downloaded {info.get('title')}")
            print(f"Format used: {info.get('format_id')} - {info.get('format')}")
            return True
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_no_merge():
    """Test without merge_output_format"""
    video_id = "FGMfNg-IEHI"
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'test_no_merge_{video_id}.%(ext)s',
        'quiet': False,
        'verbose': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    
    print(f"\n{'='*80}")
    print(f"Testing WITHOUT merge_output_format")
    print(f"{'='*80}\n")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\n✅ SUCCESS: Downloaded {info.get('title')}")
            print(f"Format used: {info.get('format_id')} - {info.get('format')}")
            return True
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    print("\nTest 1: With merge_output_format (like app)")
    result1 = test_download_exact()
    
    print("\n\nTest 2: Without merge_output_format")
    result2 = test_with_no_merge()
    
    print(f"\n{'='*80}")
    print("RESULTS:")
    print(f"With merge: {'✅ SUCCESS' if result1 else '❌ FAILED'}")
    print(f"Without merge: {'✅ SUCCESS' if result2 else '❌ FAILED'}")
    print(f"{'='*80}\n")