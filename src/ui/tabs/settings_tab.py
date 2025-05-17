import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil

from src.ui.presenters import SettingsPresenter
from src.ui.base_tab import BaseTab
from src.utils.logging_utils import get_logger

class SettingsTab(BaseTab):
    """Enhanced settings tab implementation with output template options"""
    
    def __init__(self, parent, presenter: SettingsPresenter, **kwargs):
        # Get tab-specific logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.presenter = presenter
        self.config = self.presenter.load_config()
        
        # Variables
        self.cookie_method_var = tk.StringVar(value=self.config.cookie_method)
        self.cookie_file_var = tk.StringVar(value=self.config.cookie_file)
        self.auto_retry_var = tk.BooleanVar(value=self.config.auto_retry_failed)
        self.check_duplicates_var = tk.BooleanVar(value=self.config.check_duplicates)
        
        # New variables for output customization
        self.output_template_var = tk.StringVar(value=getattr(self.config, 'output_template', "%(playlist_index)02d-%(title)s.%(ext)s"))
        self.create_playlist_folder_var = tk.BooleanVar(value=getattr(self.config, 'create_playlist_folder', True))
        self.sanitize_filenames_var = tk.BooleanVar(value=getattr(self.config, 'sanitize_filenames', True))
        self.preferred_format_var = tk.StringVar(value=getattr(self.config, 'preferred_format', 'mp4'))
        self.use_postprocessing_var = tk.BooleanVar(value=getattr(self.config, 'use_postprocessing', True))
        
        # Default download directory
        self.default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube")
        
        super().__init__(parent, **kwargs)
        self.logger.debug("Settings tab initialized")
    
    def create_widgets(self):
        """Create settings tab widgets"""
        settings_frame = tk.Frame(self, padx=10, pady=10)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a notebook for settings categories
        self.settings_notebook = ttk.Notebook(settings_frame)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Authentication tab
        self.auth_tab = tk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.auth_tab, text="Authentication")
        self._create_cookie_section(self.auth_tab)
        
        # Output tab
        self.output_tab = tk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.output_tab, text="Output")
        self._create_output_section(self.output_tab)
        
        # Advanced tab
        self.advanced_tab = tk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.advanced_tab, text="Advanced")
        self._create_advanced_section(self.advanced_tab)
        
        # Save button (common to all tabs)
        tk.Button(settings_frame, text="Save Settings", command=self.save_settings, 
                 bg="#2196F3", fg="white").pack(pady=10)
    
    def _create_cookie_section(self, parent):
        """Create cookie settings section"""
        cookie_frame = tk.LabelFrame(parent, text="YouTube Authentication", padx=10, pady=5)
        cookie_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        instructions.pack(pady=5, fill=tk.BOTH, expand=True)
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
    
    def _create_output_section(self, parent):
        """Create output settings section with enhanced download directory options"""
        output_frame = tk.LabelFrame(parent, text="Output Settings", padx=10, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Download directory selection
        dir_frame = tk.LabelFrame(output_frame, text="Download Directory", padx=10, pady=5)
        dir_frame.pack(fill=tk.X, pady=5)
        
        # Directory entry and browse button
        dir_entry_frame = tk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X, pady=5)
        
        self.dir_entry = tk.Entry(dir_entry_frame, width=50)
        self.dir_entry.insert(0, self.config.download_directory)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = tk.Button(dir_entry_frame, text="Browse", command=self.browse_download_dir)
        browse_btn.pack(side=tk.LEFT, padx=2)
        
        default_btn = tk.Button(dir_entry_frame, text="Reset to Default", command=self.reset_to_default_dir)
        default_btn.pack(side=tk.LEFT, padx=2)
        
        # Disk space information
        disk_frame = tk.Frame(dir_frame)
        disk_frame.pack(fill=tk.X, pady=5)
        
        self.disk_space_label = tk.Label(disk_frame, text="", anchor=tk.W)
        self.disk_space_label.pack(fill=tk.X)
        
        # Update disk space display
        self.update_disk_space_info()
        
        # Create playlist folder option
        folder_frame = tk.Frame(output_frame)
        folder_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(folder_frame, text="Create playlist folder", variable=self.create_playlist_folder_var).pack(anchor=tk.W)
        
        # Sanitize filenames option
        sanitize_frame = tk.Frame(output_frame)
        sanitize_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(sanitize_frame, text="Sanitize filenames (remove invalid characters)", variable=self.sanitize_filenames_var).pack(anchor=tk.W)
        
        # Format options
        format_frame = tk.Frame(output_frame)
        format_frame.pack(fill=tk.X, pady=5)
        tk.Label(format_frame, text="Preferred format:").pack(side=tk.LEFT)
        format_options = ["mp4", "mkv", "webm", "mov", "flv"]
        format_menu = ttk.Combobox(format_frame, textvariable=self.preferred_format_var,
                                  values=format_options, state="readonly", width=10)
        format_menu.pack(side=tk.LEFT, padx=5)
        
        # Post-processing option
        postproc_frame = tk.Frame(output_frame)
        postproc_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(postproc_frame, text="Use post-processing (requires FFmpeg)", 
                      variable=self.use_postprocessing_var).pack(anchor=tk.W)
        
        # Output template
        template_frame = tk.LabelFrame(output_frame, text="Output Template", padx=10, pady=5)
        template_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Template entry
        self.output_template_entry = tk.Entry(template_frame, textvariable=self.output_template_var, width=50)
        self.output_template_entry.pack(fill=tk.X, pady=5)
        
        # Template presets
        presets_frame = tk.Frame(template_frame)
        presets_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(presets_frame, text="Presets:").pack(side=tk.LEFT, padx=(0, 5))
        
        presets = [
            ("Default", "%(playlist_index)02d-%(title)s.%(ext)s"),
            ("Simple", "%(title)s.%(ext)s"),
            ("With ID", "%(id)s-%(title)s.%(ext)s"),
            ("Index & Title", "%(playlist_index)02d-%(title)s.%(ext)s"),
            ("Complete", "%(playlist_index)02d-%(id)s-%(title)s.%(ext)s")
        ]
        
        for name, value in presets:
            # Use a lambda with a default argument to avoid variable capture issues
            btn = tk.Button(presets_frame, text=name, 
                          command=lambda v=value: self.output_template_var.set(v))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Template variables help
        help_text = tk.Text(template_frame, height=8, wrap=tk.WORD, bg="#f0f0f0")
        help_text.pack(fill=tk.BOTH, expand=True, pady=5)
        help_text.insert(1.0, 
            "Available variables for output template:\n\n"
            "%(title)s         - Video title\n"
            "%(id)s            - Video ID\n"
            "%(ext)s           - File extension\n"
            "%(playlist_index)s - Video number in playlist\n"
            "%(playlist_title)s - Playlist title\n"
            "%(playlist)s      - Playlist ID\n"
            "%(uploader)s      - Video uploader\n"
            "%(upload_date)s   - Upload date (YYYYMMDD)\n"
            "\nNote: For playlist index with leading zeros, use %(playlist_index)02d"
        )
        help_text.config(state=tk.DISABLED)
        
    def _create_advanced_section(self, parent):
        """Create advanced settings section"""
        advanced_frame = tk.LabelFrame(parent, text="Advanced Settings", padx=10, pady=5)
        advanced_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Auto-retry failed downloads
        retry_frame = tk.Frame(advanced_frame)
        retry_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(retry_frame, text="Auto-retry failed downloads", 
                       variable=self.auto_retry_var).pack(anchor=tk.W)
        
        # Check for duplicates
        duplicates_frame = tk.Frame(advanced_frame)
        duplicates_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(duplicates_frame, text="Check for duplicate downloads", 
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
                
    def browse_download_dir(self):
        """Browse for download directory"""
        directory = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.update_disk_space_info()
    
    def reset_to_default_dir(self):
        """Reset download directory to default"""
        # Create default directory if it doesn't exist
        os.makedirs(self.default_download_dir, exist_ok=True)
        
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, self.default_download_dir)
        self.update_disk_space_info()
        
    def update_disk_space_info(self):
        """Update disk space information for selected directory"""
        directory = self.dir_entry.get()
        
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.disk_space_label.config(text=f"Directory created: {directory}")
                self.logger.info(f"Created directory: {directory}")
                
            # Get disk usage information
            total, used, free = shutil.disk_usage(directory)
            
            # Convert to GB for readability
            total_gb = total / (1024**3)
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100
            
            # Update label with disk information
            self.disk_space_label.config(
                text=f"Disk Space: {free_gb:.1f} GB free of {total_gb:.1f} GB ({used_percent:.1f}% used)",
                fg="green" if free_gb > 10 else ("orange" if free_gb > 2 else "red")
            )
            
            # Log disk space status
            self.logger.debug(f"Disk space: {free_gb:.1f} GB free of {total_gb:.1f} GB")
            
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            self.disk_space_label.config(text=f"Error: {str(e)}", fg="red")
            
    def validate_directory(self, directory):
        """Validate and potentially create the download directory"""
        try:
            if not directory:
                return False, "Directory path cannot be empty"
                
            # Try to create directory if it doesn't exist
            if not os.path.exists(directory):
                os.makedirs(directory)
                return True, f"Directory created: {directory}"
                
            # Check if path is a directory
            if not os.path.isdir(directory):
                return False, f"Path exists but is not a directory: {directory}"
                
            # Check if directory is writable
            if not os.access(directory, os.W_OK):
                return False, f"Directory is not writable: {directory}"
                
            return True, "Directory is valid"
            
        except Exception as e:
            return False, f"Error validating directory: {str(e)}"
            
    def save_settings(self):
        """Save all settings"""
        # Validate download directory
        download_dir = self.dir_entry.get()
        is_valid, message = self.validate_directory(download_dir)
        
        if not is_valid:
            messagebox.showerror("Invalid Directory", message)
            return
            
        # Update config object with all settings
        self.config.download_directory = download_dir
        self.config.cookie_method = self.cookie_method_var.get()
        self.config.cookie_file = self.cookie_file_var.get()
        self.config.auto_retry_failed = self.auto_retry_var.get()
        self.config.check_duplicates = self.check_duplicates_var.get()
        
        # New settings for output customization
        self.config.output_template = self.output_template_var.get()
        self.config.create_playlist_folder = self.create_playlist_folder_var.get()
        self.config.sanitize_filenames = self.sanitize_filenames_var.get()
        self.config.preferred_format = self.preferred_format_var.get()
        self.config.use_postprocessing = self.use_postprocessing_var.get()
        
        if self.presenter.save_config(self.config):
            messagebox.showinfo("Settings Saved", "All settings have been saved successfully")
        else:
            errors = self.presenter.cookie_validator.get_validation_errors()
            messagebox.showerror("Validation Error", "\n".join(errors))
            
