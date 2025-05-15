# YouTube Playlist Downloader

A SOLID-compliant YouTube playlist downloader with environment variable support.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root (or copy and modify the sample):
   ```bash
   cp .env.sample .env
   ```

3. Edit the `.env` file to configure your environment:
   ```ini
   # YouTube Downloader Environment Configuration
   YOUTUBE_DOWNLOAD_DIR=/path/to/your/downloads
   YOUTUBE_COOKIE_FILE=/path/to/your/cookies.txt
   ```

## Environment Variables

The application can be configured using these environment variables:

YOUTUBE_DOWNLOAD_DIR     - Download directory (/mnt/m/Library/Youtube)
YOUTUBE_MAX_CONCURRENT   - Maximum concurrent downloads (3)
YOUTUBE_DEFAULT_QUALITY  - Default quality: best, 1080p, 720p, 480p, audio_only (best)
YOUTUBE_COOKIE_METHOD    - Cookie method: none, file, firefox, chrome, etc. (none)
YOUTUBE_COOKIE_FILE      - Path to cookie file ("")
YOUTUBE_RETRY_COUNT      - Number of retry attempts (3)
YOUTUBE_AUTO_RETRY       - Auto-retry failed downloads: true/false (true)
YOUTUBE_CHECK_DUPLICATES - Check for duplicate downloads: true/false (true)
YOUTUBE_BANDWIDTH_LIMIT  - Bandwidth limit: 0, 1M, 2M, etc. (0)
YOUTUBE_LOGS_DIR         - Log directory (logs)
YOUTUBE_LOG_LEVEL        - Logging level: DEBUG, INFO, WARNING, ERROR (INFO)

Values in parentheses are the defaults that will be used if the variable is not set.
To use these variables, either:

Set them in your .env file, or
Set them in your system environment before running the application, or
Prefix them when running the app: YOUTUBE_MAX_CONCURRENT=1 python main.py

## Running the Application

```bash
python main.py
```

## Cookie Authentication

For YouTube authentication, you can either:

1. Use browser cookies (set `YOUTUBE_COOKIE_METHOD` to your browser, e.g. `firefox`)
2. Use a cookie file (set `YOUTUBE_COOKIE_METHOD=file` and `YOUTUBE_COOKIE_FILE=/path/to/cookies.txt`)

To export cookies from your browser:
1. Install a cookies.txt extension
2. Log in to YouTube
3. Export cookies to a file
4. Set the path in your `.env` file

## Architecture

The application follows SOLID principles:
- Single Responsibility Principle: Each class has a single responsibility
- Open/Closed Principle: Easy to extend without modifying existing code
- Liskov Substitution Principle: Proper use of interfaces
- Interface Segregation Principle: Focused, specific interfaces
- Dependency Inversion Principle: Dependencies are injected, not created internally

## Debugging

If you experience issues:
1. Set `YOUTUBE_LOG_LEVEL=DEBUG` in your `.env` file
2. Check the logs in the `logs` directory
3. Run the debugging scripts: `python youtube_debug.py` or `python filepath_debug.py`