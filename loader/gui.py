# gui.py - Refactored GUI using SOLID principles

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
from typing import List

from models import DownloadConfig, DownloadProgress, DownloadQuality
from presenters import DownloadPresenter, HistoryPresenter, SettingsPresenter


class BaseTab(tk.Frame):
    """Base class for tab frames"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.create_widgets()
    
    def create_widgets(self):
        """Override in subclasses to create widgets"""
        raise NotImplementedError


class DownloadTab(BaseTab):
    """Download tab implementation"""
    
    def __init__(self, parent, presenter: DownloadPresenter, **kwargs):
        self.presenter = presenter
        self.presenter.on_progress_callback = self.update_progress
        self.presenter.on_status_change_callback = self.update_status
        self.presenter.on_playlist_complete_callback = self.mark_playlist_complete
        self.presenter.on_playlist_failed_callback = self.mark_playlist_failed
        
        # Variables
        self.config = self.presenter.load_config()
        self.quality_var = tk.StringVar(value=self.config.default_quality.value)
        self.concurrent_var = tk.IntVar(value=self.config.max_concurrent_downloads)
        self.bandwidth_var = tk.StringVar(value=self.config.bandwidth_limit)
        
        super().__init__(parent, **kwargs)
    
    def create_widgets(self):
        """Create download tab widgets"""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings section
        self._create_settings_section(main_frame)
        
        # Playlist input section
        self._create_input_section(main_frame)
        
        # Control buttons
        self._create_control_buttons(main_frame)
        
        # Progress section
        self._create_progress_section(main_frame)
        
        # Log output
        self._create_log_section(main_frame)
    
    def _create_settings_section(self, parent):
        """Create settings section"""
        settings_frame = tk.LabelFrame(parent, text="Quick Settings", padx=10, pady=5)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Directory selection
        dir_frame = tk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=2)
        tk.Label(dir_frame, text="Download Directory:").pack(side=tk.LEFT)
        self.dir_label = tk.Label(dir_frame, text=self.config.download_directory, 
                                 relief=tk.SUNKEN, anchor=tk.W, bg="white")
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(dir_frame, text="Browse", command=self.change_directory).pack(side=tk.LEFT)
        
        # Quality and settings
        quality_frame = tk.Frame(settings_frame)
        quality_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(quality_frame, text="Quality:").pack(side=tk.LEFT)
        quality_options = [q.value for q in DownloadQuality]
        self.quality_menu = ttk.Combobox(quality_frame, textvariable=self.quality_var, 
                                        values=quality_options, state="readonly", width=10)
        self.quality_menu.pack(side=tk.LEFT, padx=(5, 20))
        
        tk.Label(quality_frame, text="Concurrent:").pack(side=tk.LEFT)
        concurrent_spinner = tk.Spinbox(quality_frame, from_=1, to=5, 
                                      textvariable=self.concurrent_var, width=5)
        concurrent_spinner.pack(side=tk.LEFT, padx=5)
        
        tk.Label(quality_frame, text="Bandwidth:").pack(side=tk.LEFT, padx=(20, 5))
        bandwidth_options = ["0", "1M", "2M", "5M", "10M"]
        bandwidth_menu = ttk.Combobox(quality_frame, textvariable=self.bandwidth_var,
                                      values=bandwidth_options, state="readonly", width=8)
        bandwidth_menu.pack(side=tk.LEFT, padx=5)
        
        # Cookie status
        cookie_status_frame = tk.Frame(settings_frame)
        cookie_status_frame.pack(fill=tk.X, pady=2)
        tk.Label(cookie_status_frame, text="Cookie Status:").pack(side=tk.LEFT)
        status_text = f"Using {self.config.cookie_method}" if self.config.cookie_method != 'none' else "No authentication"
        status_color = "green" if self.config.cookie_method != 'none' else "orange"
        self.cookie_status_label = tk.Label(cookie_status_frame, text=status_text, fg=status_color)
        self.cookie_status_label.pack(side=tk.LEFT, padx=5)
    
    def _create_input_section(self, parent):
        """Create playlist input section"""
        input_frame = tk.LabelFrame(parent, text="Playlist IDs (one per line)", padx=10, pady=5)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.url_entry = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD)
        self.url_entry.pack(fill=tk.BOTH, expand=True)
        
        # Define tags for highlighting
        self.url_entry.tag_configure("current_playlist", background="#d0f0c0")
        self.url_entry.tag_configure("done_playlist", background="#e0e0e0")
        self.url_entry.tag_configure("failed_playlist", background="#f0c0c0")
    
    def _create_control_buttons(self, parent):
        """Create control buttons"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.download_button = tk.Button(button_frame, text="Download Playlists", 
                                        command=self.start_download, bg="#4CAF50", 
                                        fg="white", padx=20)
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = tk.Button(button_frame, text="Pause", 
                                     command=self.pause_downloads, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Clear", command=self.clear_input).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save List", command=self.save_playlist_list).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Load List", command=self.load_playlist_list).pack(side=tk.LEFT, padx=5)
    
    def _create_progress_section(self, parent):
        """Create progress section"""
        progress_frame = tk.LabelFrame(parent, text="Progress", padx=10, pady=5)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(progress_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=5)
    
    def _create_log_section(self, parent):
        """Create log section"""
        log_frame = tk.LabelFrame(parent, text="Log", padx=10, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_output = scrolledtext.ScrolledText(log_frame, height=10, 
                                                   state=tk.DISABLED, wrap=tk.WORD)
        self.log_output.pack(fill=tk.BOTH, expand=True)
    
    # Event handlers
    def start_download(self):
        """Start download process"""
        # Update config with current values
        self.config.default_quality = DownloadQuality(self.quality_var.get())
        self.config.max_concurrent_downloads = self.concurrent_var.get()
        self.config.bandwidth_limit = self.bandwidth_var.get()
        self.presenter.save_config(self.config)
        
        # Get playlist IDs
        playlist_ids = self.get_playlist_ids()
        
        if self.presenter.start_downloads(playlist_ids):
            self.download_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.progress_bar.start()
    
    def pause_downloads(self):
        """Pause/resume downloads"""
        if self.pause_button['text'] == 'Pause':
            self.presenter.pause_downloads()
            self.pause_button.config(text='Resume')
        else:
            self.presenter.resume_downloads()
            self.pause_button.config(text='Pause')
    
    def change_directory(self):
        """Change download directory"""
        directory = filedialog.askdirectory(initialdir=self.config.download_directory)
        if directory:
            self.config.download_directory = directory
            self.dir_label.config(text=directory)
            self.presenter.save_config(self.config)
            self.log(f"Changed download directory to: {directory}")
    
    def get_playlist_ids(self) -> List[str]:
        """Get playlist IDs from text entry"""
        text = self.url_entry.get("1.0", tk.END).strip()
        return [line.strip() for line in text.splitlines() if line.strip()]
    
    def clear_input(self):
        """Clear input text"""
        self.url_entry.delete("1.0", tk.END)
        self.log("Cleared playlist list")
    
    def save_playlist_list(self):
        """Save playlist list to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            content = self.url_entry.get("1.0", tk.END).strip()
            with open(filename, 'w') as f:
                f.write(content)
            self.log(f"Saved playlist list to {filename}")
    
    def load_playlist_list(self):
        """Load playlist list from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r') as f:
                content = f.read()
            self.url_entry.delete("1.0", tk.END)
            self.url_entry.insert("1.0", content)
            self.log(f"Loaded playlist list from {filename}")
    
    # UI update methods
    def update_progress(self, progress: DownloadProgress):
        """Update progress display"""
        if progress.status.value == 'downloading':
            speed_mb = progress.speed / 1024 / 1024 if progress.speed else 0
            eta_str = f"{progress.eta // 60}:{progress.eta % 60:02d}" if progress.eta else "Unknown"
            
            status_text = (f"Downloading: {progress.current_file} - "
                          f"{progress.progress:.1f}% - {speed_mb:.1f} MB/s - ETA: {eta_str}")
            self.status_label.config(text=status_text[:100])
    
    def update_status(self, message: str):
        """Update status message"""
        self.status_label.config(text=message)
        self.log(message)
    
    def mark_playlist_complete(self, playlist_id: str):
        """Mark playlist as complete in UI"""
        self._highlight_playlist(playlist_id, "done_playlist")
    
    def mark_playlist_failed(self, playlist_id: str, error: str):
        """Mark playlist as failed in UI"""
        self._highlight_playlist(playlist_id, "failed_playlist")
        self.log(f"Failed: {playlist_id} - {error}")
    
    def _highlight_playlist(self, playlist_id: str, tag: str):
        """Highlight playlist in entry widget"""
        self.url_entry.tag_remove("current_playlist", "1.0", tk.END)
        self.url_entry.tag_remove("done_playlist", "1.0", tk.END)
        self.url_entry.tag_remove("failed_playlist", "1.0", tk.END)
        
        start = self.url_entry.search(playlist_id, "1.0", tk.END)
        if start:
            end = f"{start} lineend"
            self.url_entry.tag_add(tag, start, end)
            self.url_entry.see(start)
    
    def log(self, message: str):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_output.configure(state=tk.NORMAL)
        self.log_output.insert(tk.END, formatted_message + "\n")
        self.log_output.see(tk.END)
        self.log_output.configure(state=tk.DISABLED)
        self.update()


class HistoryTab(BaseTab):
    """History tab implementation"""
    
    def __init__(self, parent, presenter: HistoryPresenter, **kwargs):
        self.presenter = presenter
        super().__init__(parent, **kwargs)
    
    def create_widgets(self):
        """Create history tab widgets"""
        history_frame = tk.Frame(self, padx=10, pady=10)
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = tk.Frame(history_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(control_frame, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear History", command=self.clear_history).pack(side=tk.LEFT, padx=5)
        
        # History display
        history_display_frame = tk.LabelFrame(history_frame, text="Download History", padx=10, pady=5)
        history_display_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Title', 'Status', 'Date', 'Path')
        self.history_tree = ttk.Treeview(history_display_frame, columns=columns, show='headings')
        
        self.history_tree.heading('ID', text='Playlist ID')
        self.history_tree.heading('Title', text='Title')
        self.history_tree.heading('Status', text='Status')
        self.history_tree.heading('Date', text='Date')
        self.history_tree.heading('Path', text='Path')
        
        self.history_tree.column('ID', width=150)
        self.history_tree.column('Title', width=250)
        self.history_tree.column('Status', width=100)
        self.history_tree.column('Date', width=150)
        self.history_tree.column('Path', width=300)
        
        scrollbar = ttk.Scrollbar(history_display_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_history()
    
    def refresh_history(self):
        """Refresh history display"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Load and display history
        history = self.presenter.get_history()
        
        for entry in reversed(history):  # Show newest first
            formatted_entry = self.presenter.format_history_entry(entry)
            self.history_tree.insert('', 'end', values=formatted_entry)
    
    def clear_history(self):
        """Clear download history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all download history?"):
            self.presenter.clear_history()
            self.refresh_history()
            self.logger.info("Download history cleared")


class SettingsTab(BaseTab):
    """Settings tab implementation"""
    
    def __init__(self, parent, presenter: SettingsPresenter, **kwargs):
        self.presenter = presenter
        self.config = self.presenter.load_config()
        
        # Variables
        self.cookie_method_var = tk.StringVar(value=self.config.cookie_method)
        self.cookie_file_var = tk.StringVar(value=self.config.cookie_file)
        self.auto_retry_var = tk.BooleanVar(value=self.config.auto_retry_failed)
        self.check_duplicates_var = tk.BooleanVar(value=self.config.check_duplicates)
        
        super().__init__(parent, **kwargs)
    
    def create_widgets(self):
        """Create settings tab widgets"""
        settings_frame = tk.Frame(self, padx=10, pady=10)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Cookie settings
        self._create_cookie_section(settings_frame)
        
        # Advanced settings
        self._create_advanced_section(settings_frame)
        
        # Save button
        tk.Button(settings_frame, text="Save Settings", command=self.save_settings, 
                 bg="#2196F3", fg="white").pack(pady=10)
    
    def _create_cookie_section(self, parent):
        """Create cookie settings section"""
        cookie_frame = tk.LabelFrame(parent, text="YouTube Authentication", padx=10, pady=5)
        cookie_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Cookie method selection
        cookie_method_frame = tk.Frame(cookie_frame)
        cookie_method_frame.pack(fill=tk.X, pady=2)
        tk.Label(cookie_method_frame, text="Cookie Method:").pack(side=tk.LEFT)
        cookie_methods = ["none", "file", "firefox", "chrome", "chromium", "edge", "opera", "safari"]
        self.cookie_method_menu = ttk.Combobox(cookie_method_frame, textvariable=self.cookie_method_var,
                                              values=cookie_methods, state="readonly", width=15)
        self.cookie_method_menu.bind("<<ComboboxSelected>>", lambda e: self.update_cookie_file_status())
        self.cookie_method_menu.pack(side=tk.LEFT, padx=5)
        
        # Cookie file path
        cookie_file_frame = tk.Frame(cookie_frame)
        cookie_file_frame.pack(fill=tk.X, pady=2)
        tk.Label(cookie_file_frame, text="Cookie File:").pack(side=tk.LEFT)
        self.cookie_file_entry = tk.Entry(cookie_file_frame, textvariable=self.cookie_file_var, width=40)
        self.cookie_file_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(cookie_file_frame, text="Browse", command=self.browse_cookie_file).pack(side=tk.LEFT)
        
        # Cookie file validator
        self.cookie_file_status = tk.Label(cookie_file_frame, text="Unknown", fg="gray")
        self.cookie_file_status.pack(side=tk.LEFT, padx=10)
        
        # Instructions
        instructions = tk.Text(cookie_frame, height=12, wrap=tk.WORD, bg="#f0f0f0")
        instructions.pack(pady=5, fill=tk.X)
        instructions.insert(1.0, 
            "YouTube requires authentication to prevent bot usage. Choose a method:\n\n"
            "BROWSER COOKIE METHOD (Recommended):\n"
            "1. Select your browser from the dropdown (e.g., 'chrome', 'firefox')\n"
            "2. Make sure you're logged into YouTube in that browser\n"
            "3. The app will extract cookies directly from your browser\n\n"
            "FILE METHOD (if browser method fails):\n"
            "1. Install 'cookies.txt' extension in your browser\n"
            "2. Go to YouTube.com and login\n"
            "3. Click the extension and export cookies.txt\n"
            "4. Select 'file' method and browse to the cookies.txt file\n"
            "5. Close your browser before downloading"
        )
        instructions.config(state=tk.DISABLED)
        
        self.update_cookie_file_status()
    
    def _create_advanced_section(self, parent):
        """Create advanced settings section"""
        advanced_frame = tk.LabelFrame(parent, text="Advanced Settings", padx=10, pady=5)
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Checkbutton(advanced_frame, text="Auto-retry failed downloads", 
                       variable=self.auto_retry_var).pack(anchor=tk.W)
        
        tk.Checkbutton(advanced_frame, text="Check for duplicate downloads", 
                       variable=self.check_duplicates_var).pack(anchor=tk.W)
    
    def browse_cookie_file(self):
        """Browse for cookie file"""
        filename = filedialog.askopenfilename(
            title="Select Cookie File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.cookie_file_var.set(filename)
            self.update_cookie_file_status()
    
    def update_cookie_file_status(self):
        """Update cookie file status indicator"""
        method = self.cookie_method_var.get()
        file_path = self.cookie_file_var.get()
        
        if method != 'file':
            self.cookie_file_status.config(text="Not used", fg="gray")
            return
        
        is_valid, errors = self.presenter.validate_cookies(method, file_path)
        
        if is_valid:
            self.cookie_file_status.config(text="✔ Valid", fg="green")
        else:
            if not file_path:
                self.cookie_file_status.config(text="✖ Not selected", fg="red")
            else:
                self.cookie_file_status.config(text="✖ Invalid", fg="red")
    
    def save_settings(self):
        """Save all settings"""
        # Update config object
        self.config.cookie_method = self.cookie_method_var.get()
        self.config.cookie_file = self.cookie_file_var.get()
        self.config.auto_retry_failed = self.auto_retry_var.get()
        self.config.check_duplicates = self.check_duplicates_var.get()
        
        if self.presenter.save_config(self.config):
            messagebox.showinfo("Settings Saved", "All settings have been saved successfully")
        else:
            errors = self.presenter.cookie_validator.get_validation_errors()
            messagebox.showerror("Validation Error", "\n".join(errors))


class YouTubeDownloaderApp(tk.Tk):
    """Main application window"""
    
    def __init__(self, 
                 download_presenter: DownloadPresenter,
                 history_presenter: HistoryPresenter,
                 settings_presenter: SettingsPresenter):
        super().__init__()
        
        self.title("YouTube Playlist Downloader")
        self.geometry("900x800")
        self.resizable(True, True)
        
        self.download_presenter = download_presenter
        self.history_presenter = history_presenter
        self.settings_presenter = settings_presenter
        
        self.create_widgets()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create main application widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.download_tab = DownloadTab(self.notebook, self.download_presenter)
        self.notebook.add(self.download_tab, text="Download")
        
        self.history_tab = HistoryTab(self.notebook, self.history_presenter)
        self.notebook.add(self.history_tab, text="History")
        
        self.settings_tab = SettingsTab(self.notebook, self.settings_presenter)
        self.notebook.add(self.settings_tab, text="Settings")
    
    def on_closing(self):
        """Handle application close"""
        if messagebox.askokcancel("Quit", "Do you want to quit? Any active downloads will be stopped."):
            self.download_presenter.stop_downloads()
            self.destroy()