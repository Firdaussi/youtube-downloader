# theme_tab.py - Theme selection tab for the application

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from typing import Dict, Any, Optional

from theme_manager import ThemeManager


class ThemeTab(tk.Frame):
    """Theme selection and customization tab"""
    
    def __init__(self, parent, theme_manager: ThemeManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.theme_manager = theme_manager
        self.create_widgets()
    
    def create_widgets(self):
        """Create theme tab widgets"""
        # Main frame with padding
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Theme selection section
        self._create_theme_selection(main_frame)
        
        # Theme preview section
        self._create_theme_preview(main_frame)
    
    def _create_theme_selection(self, parent):
        """Create theme selection section"""
        # Theme selection frame
        selection_frame = tk.LabelFrame(parent, text="Theme Selection", padx=10, pady=5)
        selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get available themes
        theme_ids = self.theme_manager.get_theme_ids()
        theme_names = self.theme_manager.get_theme_names()
        theme_options = {theme_names[i]: theme_ids[i] for i in range(len(theme_ids))}
        
        # Current theme
        current_theme = self.theme_manager.get_current_theme()
        
        # Theme selector
        selector_frame = tk.Frame(selection_frame)
        selector_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(selector_frame, text="Select Theme:").pack(side=tk.LEFT, padx=(0, 10))
        
        # Create dropdown for theme selection
        self.theme_var = tk.StringVar(value=current_theme.name)
        theme_dropdown = ttk.Combobox(selector_frame, textvariable=self.theme_var,
                                     values=list(theme_options.keys()), state="readonly")
        theme_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Apply button
        apply_button = tk.Button(selector_frame, text="Apply", 
                                command=lambda: self._apply_theme(theme_options[self.theme_var.get()]))
        apply_button.pack(side=tk.LEFT)
        
        # Theme description
        desc_frame = tk.Frame(selection_frame)
        desc_frame.pack(fill=tk.X, pady=5)
        
        # Theme descriptions
        descriptions = {
            "Light": "Default light theme with blue accents. Good for daytime use and high readability.",
            "Dark": "Dark theme with blue accents. Reduces eye strain in low-light environments.",
            "High Contrast": "Maximum contrast theme for accessibility. Ideal for users with visual impairments."
        }
        
        self.desc_label = tk.Label(desc_frame, text=descriptions.get(current_theme.name, ""), 
                                  anchor=tk.W, justify=tk.LEFT, wraplength=500)
        self.desc_label.pack(fill=tk.X)
        
        # Update description when theme changes
        def update_desc(*args):
            theme_name = self.theme_var.get()
            self.desc_label.config(text=descriptions.get(theme_name, ""))
            
        self.theme_var.trace_add("write", update_desc)
    
    def _create_theme_preview(self, parent):
        """Create theme preview section"""
        preview_frame = tk.LabelFrame(parent, text="Theme Preview", padx=10, pady=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a mini-UI with various widgets to preview theme
        # Header
        header_frame = tk.Frame(preview_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(header_frame, text="Preview Header", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        
        # Input fields
        input_frame = tk.Frame(preview_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(input_frame, text="Text Input:").pack(side=tk.LEFT, padx=(0, 5))
        tk.Entry(input_frame, width=30).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(input_frame, text="Dropdown:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(input_frame, values=["Option 1", "Option 2", "Option 3"], 
                    state="readonly", width=15).pack(side=tk.LEFT)
        
        # Buttons
        button_frame = tk.Frame(preview_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="Normal Button").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Primary Button", bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Success", bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Warning", bg="#FF9800", fg="black").pack(side=tk.LEFT, padx=5)
        
        # Checkboxes and radio buttons
        check_frame = tk.Frame(preview_frame)
        check_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(check_frame, text="Checkbox 1").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(check_frame, text="Checkbox 2").pack(side=tk.LEFT, padx=(0, 10))
        
        radio_var = tk.IntVar(value=1)
        ttk.Radiobutton(check_frame, text="Option A", variable=radio_var, value=1).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(check_frame, text="Option B", variable=radio_var, value=2).pack(side=tk.LEFT)
        
        # Progress bar
        progress_frame = tk.Frame(preview_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(progress_frame, text="Progress:").pack(side=tk.LEFT, padx=(0, 5))
        progress = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        progress['value'] = 70
        
        # Treeview (table)
        tree_frame = tk.Frame(preview_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=("name", "status"), show="headings", height=4)
        tree.heading("name", text="Name")
        tree.heading("status", text="Status")
        
        tree.column("name", width=150)
        tree.column("status", width=100)
        
        tree.insert("", "end", values=("Example Item 1", "Completed"))
        tree.insert("", "end", values=("Example Item 2", "In Progress"))
        tree.insert("", "end", values=("Example Item 3", "Pending"))
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Text area with tags
        text_frame = tk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(text_frame, text="Text with highlighting:").pack(anchor=tk.W)
        
        text_area = tk.Text(text_frame, height=3, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # Define tags
        text_area.tag_configure("current_playlist", background="#d0f0c0")
        text_area.tag_configure("done_playlist", background="#e0e0e0")
        text_area.tag_configure("failed_playlist", background="#f0c0c0")
        
        # Insert sample text with tags
        text_area.insert(tk.END, "This is a current download\n", "current_playlist")
        text_area.insert(tk.END, "This is a completed download\n", "done_playlist")
        text_area.insert(tk.END, "This is a failed download", "failed_playlist")
        
        # Make text read-only
        text_area.configure(state=tk.DISABLED)
    
    def _apply_theme(self, theme_id):
        """Apply selected theme"""
        if self.theme_manager.set_current_theme(theme_id):
            messagebox.showinfo("Theme Changed", f"Theme changed to {self.theme_var.get()}")
        else:
            messagebox.showerror("Error", "Failed to apply theme")