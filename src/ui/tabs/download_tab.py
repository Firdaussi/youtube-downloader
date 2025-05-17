import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from typing import List

from src.data.models import DownloadProgress, DownloadQuality
from src.ui.presenters import DownloadPresenter
from src.ui.base_tab import BaseTab
from src.utils.logging_utils import get_logger

class DownloadTab(BaseTab):
    """Download tab implementation"""
    
    def __init__(self, parent, presenter: DownloadPresenter, **kwargs):
        # Get tab-specific logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
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
        self.logger.debug("Download tab initialized")
    
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
        
        # Also log to application logger with appropriate level
        self.logger.debug(message)
        
        # Update UI log
        self.log_output.configure(state=tk.NORMAL)
        self.log_output.insert(tk.END, formatted_message + "\n")
        self.log_output.see(tk.END)
        self.log_output.configure(state=tk.DISABLED)
        self.update()