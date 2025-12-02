import tkinter as tk
from tkinter import ttk, filedialog, messagebox  
from typing import List, Optional
import threading
from urllib.parse import urlparse, parse_qs

from src.data.models import DownloadProgress, DownloadQuality
from src.ui.presenters import DownloadPresenter
from src.ui.base_tab import BaseTab
from src.utils.logging_utils import get_logger

class DownloadTab(BaseTab):
    """Download tab implementation with queue system"""
    
    def __init__(self, parent, presenter: DownloadPresenter, **kwargs):
        # Get tab-specific logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.presenter = presenter
        self.presenter.on_progress_callback = self.update_progress
        self.presenter.on_status_change_callback = self.update_status
        self.presenter.on_playlist_complete_callback = self.mark_playlist_complete
        self.presenter.on_playlist_failed_callback = self.mark_playlist_failed
        self.presenter.on_all_complete_callback = self.reset_ui

        # Variables
        self.config = self.presenter.load_config()
        
        # Queue management
        self.playlist_queue = []  # List of (playlist_id, playlist_name) tuples
        self.current_playlist = None  # Currently downloading (id, name) tuple
        
        # Initialize performance tracking variables
        self._last_status_text = ""
        self._last_logged_progress = 0
        self._last_progress_time = 0
        
        super().__init__(parent, **kwargs)
        self.logger.debug("Download tab initialized")
    
    def create_widgets(self):
        """Create download tab widgets"""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add Playlists section (full width, compact)
        self._create_input_section(main_frame)
        
        # Download Queue section (full width)
        self._create_queue_section(main_frame)
        
        # Control buttons
        self._create_control_buttons(main_frame)
        
        # Active download section
        self._create_active_download_section(main_frame)
        
        # Download log (simplified)
        self._create_download_log_section(main_frame)
    
    def _create_input_section(self, parent):
        """Create playlist input section - full width, compact"""
        input_frame = tk.LabelFrame(parent, text="Add Playlists", padx=10, pady=5)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Top row: help text and buttons
        top_row = tk.Frame(input_frame)
        top_row.pack(fill=tk.X, pady=(0, 5))
        
        help_text = tk.Label(top_row, 
                            text="Paste playlist IDs or URLs (one per line)",
                            font=("Segoe UI", 9),
                            fg="gray",
                            anchor=tk.W)
        help_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Buttons on the right
        tk.Button(top_row, text="Add to Queue", command=self.add_to_queue,
                 bg="#2196F3", fg="white", padx=15).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(top_row, text="Load File", command=self.load_playlist_list,
                 padx=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(top_row, text="Clear", command=self.clear_input,
                 padx=10).pack(side=tk.RIGHT, padx=5)
        
        # Text area for pasting (6 lines)
        self.url_entry = tk.Text(input_frame, height=6, wrap=tk.WORD, font=("Consolas", 10))
        self.url_entry.pack(fill=tk.X)
    
    def _create_queue_section(self, parent):
        """Create queue display section - full width"""
        queue_frame = tk.LabelFrame(parent, text="Download Queue", padx=10, pady=5)
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Top row: status label and buttons
        top_row = tk.Frame(queue_frame)
        top_row.pack(fill=tk.X, pady=(0, 5))
        
        self.queue_status_label = tk.Label(top_row, text="Queue: 0 playlists", 
                                          anchor=tk.W, font=("Segoe UI", 9, "bold"))
        self.queue_status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Queue management buttons on the right
        tk.Button(top_row, text="Save Queue", command=self.save_queue,
                 padx=10).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(top_row, text="Clear Queue", command=self.clear_queue,
                 padx=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(top_row, text="Remove Selected", command=self.remove_from_queue,
                 padx=10).pack(side=tk.RIGHT, padx=5)
        
        # Create treeview with two columns
        tree_frame = tk.Frame(queue_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure style for monospace font
        style = ttk.Style()
        style.configure("Queue.Treeview", font=('Consolas', 9), rowheight=20)
        
        columns = ('playlist_id', 'name')
        self.queue_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', 
                                       height=12, style="Queue.Treeview")
        
        self.queue_tree.heading('playlist_id', text='Playlist ID')
        self.queue_tree.heading('name', text='Name')
        
        # Column widths: 35% for ID, 65% for name
        # Assuming total width ~800px: 280px for ID, 520px for name
        self.queue_tree.column('playlist_id', width=280, stretch=False)
        self.queue_tree.column('name', width=520)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_control_buttons(self, parent):
        """Create main control buttons"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Download button (primary action)
        self.download_button = tk.Button(
            button_frame, 
            text="Start Downloads", 
            command=self.start_downloads,
            bg="#4CAF50",
            fg="white", 
            padx=30,
            font=("Segoe UI", 10, "bold"),
            state=tk.DISABLED
        )
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        # Pause button
        self.pause_button = tk.Button(
            button_frame, 
            text="Pause", 
            command=self.pause_downloads, 
            state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        self.cancel_button = tk.Button(
            button_frame, 
            text="Cancel", 
            command=self.cancel_downloads, 
            state=tk.DISABLED,
            bg="#F44336", 
            fg="white"
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)
    
    def _create_active_download_section(self, parent):
        """Create active download display section"""
        active_frame = tk.LabelFrame(parent, text="Active Download", padx=10, pady=8)
        active_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Playlist info (first row)
        info_frame = tk.Frame(active_frame)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(info_frame, text="Playlist:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.active_playlist_label = tk.Label(info_frame, text="None", 
                                             font=("Consolas", 9), anchor=tk.W)
        self.active_playlist_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        tk.Label(info_frame, text="Name:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        self.active_name_label = tk.Label(info_frame, text="", anchor=tk.W)
        self.active_name_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Current track info (second row)
        track_frame = tk.Frame(active_frame)
        track_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(track_frame, text="Current Track:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.current_track_label = tk.Label(track_frame, text="None", 
                                           font=("Segoe UI", 10), anchor=tk.W, 
                                           fg="#0066CC")
        self.current_track_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(active_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Status
        self.status_label = tk.Label(active_frame, text="Ready", anchor=tk.W, font=("Segoe UI", 9))
        self.status_label.pack(fill=tk.X)
    
    def _create_download_log_section(self, parent):
        """Create simplified download log section"""
        log_frame = tk.LabelFrame(parent, text="Download Progress", padx=10, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for track progress
        tree_frame = tk.Frame(log_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('number', 'track', 'progress')
        self.log_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        
        self.log_tree.heading('number', text='#')
        self.log_tree.heading('track', text='Track')
        self.log_tree.heading('progress', text='Progress')
        
        self.log_tree.column('number', width=40, anchor=tk.CENTER)
        self.log_tree.column('track', width=400)
        self.log_tree.column('progress', width=100, anchor=tk.E)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Queue management methods
    def extract_playlist_id(self, text: str) -> Optional[str]:
        """Extract playlist ID from URL or return the text if it's already an ID"""
        text = text.strip()
        if not text:
            return None
            
        # Check if it's a URL
        if text.startswith('http://') or text.startswith('https://'):
            try:
                parsed = urlparse(text)
                params = parse_qs(parsed.query)
                
                if 'list' in params:
                    return params['list'][0]
                else:
                    self.logger.warning(f"No 'list' parameter found in URL: {text}")
                    return None
            except Exception as e:
                self.logger.error(f"Error parsing URL '{text}': {e}")
                return None
        else:
            # Assume it's already a playlist ID
            return text
    
    def fetch_playlist_name(self, playlist_id: str) -> str:
        """Fetch playlist name using yt-dlp (runs in background)"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            # Add cookies if configured
            if self.config.cookie_method != 'none':
                if self.config.cookie_method == 'file':
                    ydl_opts['cookiefile'] = self.config.cookie_file
                else:
                    ydl_opts['cookiesfrombrowser'] = (self.config.cookie_method,)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/playlist?list={playlist_id}", download=False)
                return info.get('title', 'Unknown Playlist')
                
        except Exception as e:
            self.logger.error(f"Error fetching playlist name for {playlist_id}: {e}")
            return "Unknown Playlist"
    
    def add_to_queue(self):
        """Add playlists from input to queue"""
        text = self.url_entry.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Input", "Please enter at least one playlist ID or URL")
            return
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        added_count = 0
        added_ids = []  # Track IDs to add to download service
        
        for line in lines:
            playlist_id = self.extract_playlist_id(line)
            if playlist_id:
                # Check if already in queue
                if any(pid == playlist_id for pid, _ in self.playlist_queue):
                    self.logger.info(f"Playlist {playlist_id} already in queue, skipping")
                    continue
                
                # Add to queue with placeholder name
                self.playlist_queue.append((playlist_id, "Fetching name..."))
                item_id = self.queue_tree.insert('', 'end', values=(playlist_id, "Fetching name..."))
                added_count += 1
                added_ids.append(playlist_id)
                
                # Fetch name in background
                def fetch_name_async(pid, iid):
                    name = self.fetch_playlist_name(pid)
                    # Update queue data
                    for i, (qid, _) in enumerate(self.playlist_queue):
                        if qid == pid:
                            self.playlist_queue[i] = (pid, name)
                            break
                    # Update UI in main thread
                    self.after(0, lambda: self.queue_tree.item(iid, values=(pid, name)))
                
                threading.Thread(target=fetch_name_async, args=(playlist_id, item_id), daemon=True).start()
        
        self.update_queue_status()
        self.url_entry.delete("1.0", tk.END)
        
        if added_count > 0:
            self.logger.info(f"Added {added_count} playlist(s) to queue")
            
            # If downloads are currently running, add these playlists to the download service queue
            if self.presenter.is_downloading():
                self.logger.info(f"Downloads are running, adding {len(added_ids)} playlist(s) to active download queue")
                self.presenter.add_to_download_queue(added_ids)
            
            # Enable download button if queue has items and not currently downloading
            if not self.presenter.is_downloading():
                self.download_button.config(state=tk.NORMAL)
    
    def remove_from_queue(self):
        """Remove selected item from queue"""
        selection = self.queue_tree.selection()
        if not selection:
            return
        
        for item in selection:
            values = self.queue_tree.item(item, 'values')
            playlist_id = values[0]
            
            # Remove from queue list
            self.playlist_queue = [(pid, name) for pid, name in self.playlist_queue if pid != playlist_id]
            
            # Remove from tree
            self.queue_tree.delete(item)
        
        self.update_queue_status()
    
    def clear_queue(self):
        """Clear all items from queue"""
        if self.playlist_queue and messagebox.askyesno("Clear Queue", "Remove all playlists from queue?"):
            self.playlist_queue.clear()
            self.queue_tree.delete(*self.queue_tree.get_children())
            self.update_queue_status()
    
    def update_queue_status(self):
        """Update queue status label"""
        count = len(self.playlist_queue)
        self.queue_status_label.config(text=f"Queue: {count} playlist{'s' if count != 1 else ''}")
        
        # Disable download button if queue is empty
        if count == 0:
            self.download_button.config(state=tk.DISABLED)
    
    def save_queue(self):
        """Save queue to file"""
        if not self.playlist_queue:
            messagebox.showinfo("Empty Queue", "Queue is empty")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                for playlist_id, name in self.playlist_queue:
                    f.write(f"{playlist_id}\t{name}\n")
            self.logger.info(f"Saved queue to {filename}")
    
    # Download control methods
    def start_downloads(self):
        """Start downloading playlists from queue"""
        if not self.playlist_queue:
            messagebox.showwarning("Empty Queue", "No playlists in queue")
            return
        
        # Reset track counter
        self._track_counter = 0
        
        # Clear log tree
        self.log_tree.delete(*self.log_tree.get_children())
        
        # Get all playlist IDs from queue
        playlist_ids = [pid for pid, _ in self.playlist_queue]
        
        # Create quick mode config
        quick_config = self.config
        quick_config.quick_mode = True
        quick_config.check_duplicates = False
        
        self.logger.info(f"Starting downloads for {len(playlist_ids)} playlist(s)")
        
        # Start downloads
        if self.presenter.start_downloads_quick(playlist_ids, quick_config):
            self.download_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)
            self.progress_bar.start()
            
            # Move first playlist to active
            if self.playlist_queue:
                self.current_playlist = self.playlist_queue[0]
                self.update_active_download()
    
    def pause_downloads(self):
        """Pause/resume downloads"""
        if self.pause_button['text'] == 'Pause':
            self.presenter.pause_downloads()
            self.pause_button.config(text='Resume')
        else:
            self.presenter.resume_downloads()
            self.pause_button.config(text='Pause')

    def cancel_downloads(self):
        """Cancel all downloads"""
        if messagebox.askyesno("Cancel Downloads", "Are you sure you want to cancel all downloads?"):
            self.logger.info("User requested download cancellation")
            self.status_label.config(text="Cancelling downloads...")
            self.update()  # Force UI update
            
            try:
                self.presenter.stop_downloads()
                self.logger.info("Stop command sent to download service")
            except Exception as e:
                self.logger.error(f"Error stopping downloads: {e}")
                messagebox.showerror("Error", f"Error stopping downloads: {e}")
            
            self.reset_ui()
    
    def clear_input(self):
        """Clear input text"""
        self.url_entry.delete("1.0", tk.END)
    
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
    
    def update_active_download(self):
        """Update active download display"""
        if self.current_playlist:
            playlist_id, name = self.current_playlist
            self.active_playlist_label.config(text=playlist_id)
            self.active_name_label.config(text=name)
        else:
            self.active_playlist_label.config(text="None")
            self.active_name_label.config(text="")
            self.current_track_label.config(text="None")
    
    # UI update methods
    def update_progress(self, progress: DownloadProgress):
        """Update progress display"""
        import time
        import os
        current_time = time.time()
        
        # Throttle updates
        if (hasattr(self, '_last_progress_time') and 
            current_time - self._last_progress_time < 0.5 and
            progress.status.value == 'downloading'):
            return
            
        self._last_progress_time = current_time
        
        # Update progress bar
        if progress.status.value == 'downloading':
            if self.progress_bar.cget('mode') == 'indeterminate':
                self.progress_bar.stop()
                self.progress_bar.config(mode='determinate')
            self.progress_bar['value'] = progress.progress
        
        # Update status
        if progress.status.value == 'downloading':
            speed_mb = progress.speed / 1024 / 1024 if progress.speed else 0
            
            if progress.eta and progress.eta < 100000:
                minutes = progress.eta // 60
                seconds = progress.eta % 60
                eta_str = f"{minutes}:{seconds:02d}"
            else:
                eta_str = "Unknown"
            
            status_text = f"Downloading: {speed_mb:.1f} MB/s - ETA: {eta_str}"
            self.status_label.config(text=status_text)
            
            # Update log tree with current file
            if progress.current_file:
                # Extract just the filename (basename)
                filename = os.path.basename(progress.current_file)
                
                # Update the current track label in Active Download section
                self.current_track_label.config(text=filename)
                
                # Get current index - use a counter if not provided
                if not hasattr(self, '_track_counter'):
                    self._track_counter = 0
                
                current_index = progress.current_index if hasattr(progress, 'current_index') and progress.current_index else None
                
                # If no index provided, increment our counter
                if current_index is None:
                    self._track_counter += 1
                    current_index = self._track_counter
                
                # Try to find existing entry or add new one
                found = False
                for item in self.log_tree.get_children():
                    values = self.log_tree.item(item, 'values')
                    if len(values) > 1 and values[1] == filename:
                        # Update existing entry
                        self.log_tree.item(item, values=(values[0], filename, f"{progress.progress:.1f}%"))
                        found = True
                        break
                
                if not found:
                    # Add new entry
                    self.log_tree.insert('', 'end', values=(
                        current_index,
                        filename,
                        f"{progress.progress:.1f}%"
                    ))
                    # Auto-scroll to bottom
                    children = self.log_tree.get_children()
                    if children:
                        self.log_tree.see(children[-1])
                        
                self.logger.debug(f"Track progress: #{current_index} {filename} - {progress.progress:.1f}%")
        else:
            self.status_label.config(text=progress.message)
    
    def update_status(self, message: str):
        """Update status message"""
        self.status_label.config(text=message)
        self.logger.info(message)
    
    def mark_playlist_complete(self, playlist_id: str):
        """Mark playlist as complete"""
        # Remove from queue
        self.playlist_queue = [(pid, name) for pid, name in self.playlist_queue if pid != playlist_id]
        
        # Remove from tree
        for item in self.queue_tree.get_children():
            if self.queue_tree.item(item, 'values')[0] == playlist_id:
                self.queue_tree.delete(item)
                break
        
        self.update_queue_status()
        
        # Move to next playlist if available
        if self.playlist_queue:
            self.current_playlist = self.playlist_queue[0]
            self.update_active_download()
        else:
            self.current_playlist = None
            self.update_active_download()
    
    def mark_playlist_failed(self, playlist_id: str, error: str):
        """Mark playlist as failed"""
        self.logger.error(f"Failed: {playlist_id} - {error}")
        messagebox.showerror("Download Failed", f"Playlist {playlist_id} failed:\n{error}")
    
    def reset_ui(self):
        """Reset UI after downloads complete or cancel"""
        self.download_button.config(state=tk.NORMAL if self.playlist_queue else tk.DISABLED)
        self.pause_button.config(state=tk.DISABLED, text="Pause")
        self.cancel_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar['value'] = 0
        self.status_label.config(text="Ready")
        self.current_playlist = None
        self.update_active_download()
        self.current_track_label.config(text="None")
        
        # Clear log tree
        self.log_tree.delete(*self.log_tree.get_children())