# YouTube Playlist Downloader - SOLID Refactored

This is a refactored version of the YouTube playlist downloader that follows SOLID principles for better maintainability, testability, and extensibility.

## Architecture Overview

The application is now structured following SOLID principles:

### Single Responsibility Principle (SRP)
Each class has a single, well-defined responsibility:
- `DownloadQueue`: Manages the download queue
- `YouTubePlaylistDownloader`: Handles YouTube-specific downloading
- `DownloadService`: Orchestrates the download process
- `DownloadPresenter`: Handles UI interactions for downloads
- `JsonConfigurationRepository`: Manages configuration persistence
- `JsonHistoryRepository`: Manages history persistence

### Open/Closed Principle (OCP)
The application is open for extension but closed for modification:
- New download sources can be added by implementing the `PlaylistDownloader` interface
- New storage methods can be added by implementing repository interfaces
- New UI frameworks can be used by implementing new presenters

### Liskov Substitution Principle (LSP)
All implementations can be substituted for their interfaces without breaking functionality.

### Interface Segregation Principle (ISP)
Interfaces are focused and specific:
- `ConfigurationRepository`: Only configuration operations
- `HistoryRepository`: Only history operations
- `ProgressListener`: Only progress updates
- `CookieValidator`: Only cookie validation

### Dependency Inversion Principle (DIP)
High-level modules don't depend on low-level modules:
- All dependencies are injected through constructors
- Components depend on abstractions (interfaces), not concretions

## File Structure

```
models.py              - Domain models and data structures
interfaces.py          - Abstract interfaces (protocols)
repositories.py        - Data persistence implementations
validators.py          - Validation logic
queue_manager.py       - Download queue management
downloader.py          - Core YouTube downloader
download_service.py    - Download orchestration service
presenters.py          - UI presentation logic
gui.py                - GUI implementation
main.py               - Application entry point
test_example.py       - Example unit tests
```

## Key Benefits

1. **Testability**: Each component can be tested in isolation with mocked dependencies
2. **Maintainability**: Changes to one component don't affect others
3. **Extensibility**: New features can be added without modifying existing code
4. **Flexibility**: Different implementations can be swapped easily
5. **Clarity**: Each class has a clear, single purpose

## Usage

Run the application:
```bash
python main.py
```

Run tests:
```bash
python test_example.py
```

## Adding New Features

### Add a new download source:
1. Implement the `PlaylistDownloader` interface
2. Update dependency injection in `main.py`

### Add a new storage method:
1. Implement the repository interfaces
2. Update dependency injection in `main.py`

### Add a new UI:
1. Create new presenter classes
2. Create new UI implementation
3. Wire them together in `main.py`

## Dependencies

- tkinter (for GUI)
- yt-dlp (for YouTube downloading)
- Standard Python libraries

## Configuration

Configuration is stored in `downloader_config.json` and includes:
- Download directory
- Quality settings
- Concurrent download limits
- Cookie settings
- Retry and duplicate checking options

## Error Handling

Errors are handled at appropriate levels:
- Download errors are caught and reported through the progress listener
- Validation errors are reported before operations begin
- All errors are logged for debugging

## Testing

The modular architecture makes testing straightforward:
- Mock dependencies for unit tests
- Test business logic separately from UI
- Test each component in isolation

See `test_example.py` for testing examples.