#!/usr/bin/env python3
"""
Test downloading with Android client to bypass SABR streaming issues
"""

import yt_dlp

def test_download(video_id, label):
    """Test downloading a single video"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': f'test_{label}_%(title)s.%(ext)s',
        'quiet': False,
        'no_warnings': False,
        # FIX FOR SABR STREAMING:
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']  # Try Android first, fall back to web
            }
        }
    }
    
    print(f"\n{'='*80}")
    print(f"Testing {label}: {video_id}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\n✅ SUCCESS: Downloaded {info.get('title')}")
            return True
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("Testing SABR Streaming Fix with Android Client")
    print("="*80)
    
    # Test video from "working" playlist
    result1 = test_download("lEbCL61qcQo", "working_playlist")
    
    # Test video from "failing" playlist  
    result2 = test_download("FGMfNg-IEHI", "failing_playlist")
    
    print("\n" + "="*80)
    print("Results:")
    print("="*80)
    print(f"Video 1 (working playlist): {'✅ SUCCESS' if result1 else '❌ FAILED'}")
    print(f"Video 2 (failing playlist): {'✅ SUCCESS' if result2 else '❌ FAILED'}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
    