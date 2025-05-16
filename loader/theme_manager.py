# theme_manager.py - Theme support for the application

import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class Theme:
    """Represents a UI theme with colors and styles"""
    
    def __init__(self, name: str, colors: Dict[str, str], fonts: Dict[str, Tuple]):
        self.name = name
        self.colors = colors
        self.fonts = fonts
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create a Theme from a dictionary"""
        return cls(
            name=data.get('name', 'Unnamed'),
            colors=data.get('colors', {}),
            fonts=data.get('fonts', {})
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert Theme to a dictionary"""
        return {
            'name': self.name,
            'colors': self.colors,
            'fonts': self.fonts
        }


class ThemeManager:
    """Manages application themes and their application to the UI"""
    
    # Default themes
    DEFAULT_THEMES = {
        "light": {
            "name": "Light",
            "colors": {
                "bg_primary": "#ffffff",
                "bg_secondary": "#f0f0f0",
                "fg_primary": "#000000",
                "fg_secondary": "#555555",
                "accent": "#2196F3",
                "accent_hover": "#1976D2",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "error": "#F44336",
                "border": "#e0e0e0",
                "input_bg": "#ffffff",
                "input_fg": "#000000",
                "button_bg": "#e0e0e0",
                "button_fg": "#000000",
                "highlight_bg": "#e3f2fd",
                "highlight_fg": "#1565C0",
                "tab_bg": "#f0f0f0",
                "tab_fg": "#000000",
                "tab_active_bg": "#ffffff",
                "tab_active_fg": "#2196F3",
                "progressbar": "#2196F3",
                "treeview_bg": "#ffffff",
                "treeview_fg": "#000000",
                "treeview_selected_bg": "#e3f2fd",
                "treeview_selected_fg": "#1565C0",
                # Tags for text widgets
                "current_playlist": "#d0f0c0",  # Light green
                "done_playlist": "#e0e0e0",     # Light gray
                "failed_playlist": "#f0c0c0"    # Light red
            },
            "fonts": {
                "default": ("Segoe UI", 10),
                "heading": ("Segoe UI", 12, "bold"),
                "large": ("Segoe UI", 14),
                "small": ("Segoe UI", 9),
                "monospace": ("Courier New", 10)
            }
        },
        "dark": {
            "name": "Dark",
            "colors": {
                "bg_primary": "#262626",
                "bg_secondary": "#1e1e1e",
                "fg_primary": "#ffffff",
                "fg_secondary": "#b0b0b0",
                "accent": "#42a5f5",
                "accent_hover": "#64b5f6",
                "success": "#66bb6a",
                "warning": "#ffa726",
                "error": "#ef5350",
                "border": "#424242",
                "input_bg": "#333333",
                "input_fg": "#ffffff",
                "button_bg": "#424242",
                "button_fg": "#ffffff",
                "highlight_bg": "#1e3a5f",
                "highlight_fg": "#90caf9",
                "tab_bg": "#1e1e1e",
                "tab_fg": "#b0b0b0",
                "tab_active_bg": "#333333",
                "tab_active_fg": "#64b5f6",
                "progressbar": "#42a5f5",
                "treeview_bg": "#333333",
                "treeview_fg": "#ffffff",
                "treeview_selected_bg": "#1e3a5f",
                "treeview_selected_fg": "#90caf9",
                # Tags for text widgets
                "current_playlist": "#2a4027",  # Dark green
                "done_playlist": "#3a3a3a",     # Dark gray
                "failed_playlist": "#4d2c2c"    # Dark red
            },
            "fonts": {
                "default": ("Segoe UI", 10),
                "heading": ("Segoe UI", 12, "bold"),
                "large": ("Segoe UI", 14),
                "small": ("Segoe UI", 9),
                "monospace": ("Courier New", 10)
            }
        },
        "high_contrast": {
            "name": "High Contrast",
            "colors": {
                "bg_primary": "#000000",
                "bg_secondary": "#121212",
                "fg_primary": "#ffffff",
                "fg_secondary": "#f0f0f0",
                "accent": "#00ffff",
                "accent_hover": "#40ffff",
                "success": "#00ff00",
                "warning": "#ffff00",
                "error": "#ff0000",
                "border": "#ffffff",
                "input_bg": "#121212",
                "input_fg": "#ffffff",
                "button_bg": "#333333",
                "button_fg": "#ffffff",
                "highlight_bg": "#003366",
                "highlight_fg": "#ffffff",
                "tab_bg": "#121212",
                "tab_fg": "#ffffff",
                "tab_active_bg": "#333333",
                "tab_active_fg": "#00ffff",
                "progressbar": "#00ffff",
                "treeview_bg": "#121212",
                "treeview_fg": "#ffffff",
                "treeview_selected_bg": "#003366",
                "treeview_selected_fg": "#ffffff",
                # Tags for text widgets
                "current_playlist": "#006600",  # Green
                "done_playlist": "#444444",     # Gray
                "failed_playlist": "#660000"    # Red
            },
            "fonts": {
                "default": ("Segoe UI", 11),
                "heading": ("Segoe UI", 13, "bold"),
                "large": ("Segoe UI", 15),
                "small": ("Segoe UI", 10),
                "monospace": ("Courier New", 11)
            }
        }
    }
    
    def __init__(self, theme_file: str = "themes.json"):
        self.theme_file = theme_file
        self.current_theme_name = "light"
        self.themes: Dict[str, Theme] = {}
        self.root: Optional[tk.Tk] = None
        self.style: Optional[ttk.Style] = None
        
        # Load default themes
        for theme_id, theme_data in self.DEFAULT_THEMES.items():
            self.themes[theme_id] = Theme.from_dict(theme_data)
            
        # Load custom themes
        self._load_themes()
    
    def _load_themes(self) -> None:
        """Load themes from file"""
        if not os.path.exists(self.theme_file):
            # Save default themes if file doesn't exist
            self._save_themes()
            return
            
        try:
            with open(self.theme_file, 'r') as f:
                data = json.load(f)
                
            # Load custom themes
            if "themes" in data:
                for theme_id, theme_data in data["themes"].items():
                    self.themes[theme_id] = Theme.from_dict(theme_data)
                    
            # Set current theme if specified
            if "current_theme" in data:
                self.current_theme_name = data["current_theme"]
                
        except Exception as e:
            logger.error(f"Error loading themes: {e}")
    
    def _save_themes(self) -> None:
        """Save themes to file"""
        try:
            # Convert themes to dictionary
            themes_dict = {theme_id: theme.to_dict() for theme_id, theme in self.themes.items()}
            
            # Create data to save
            data = {
                "current_theme": self.current_theme_name,
                "themes": themes_dict
            }
            
            # Save to file
            with open(self.theme_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving themes: {e}")
    
    def get_theme_ids(self) -> List[str]:
        """Get list of theme IDs"""
        return list(self.themes.keys())
    
    def get_theme_names(self) -> List[str]:
        """Get list of theme names"""
        return [theme.name for theme in self.themes.values()]
    
    def get_current_theme(self) -> Theme:
        """Get current theme"""
        return self.themes.get(self.current_theme_name, self.themes["light"])
    
    def set_current_theme(self, theme_id: str) -> bool:
        """Set current theme and apply it"""
        if theme_id in self.themes:
            self.current_theme_name = theme_id
            self._save_themes()
            
            # Apply theme if root is set
            if self.root is not None:
                self.apply_theme(self.root)
            return True
        return False
    
    def add_theme(self, theme_id: str, theme: Theme) -> bool:
        """Add a new theme"""
        if theme_id in self.themes:
            return False
            
        self.themes[theme_id] = theme
        self._save_themes()
        return True
    
    def remove_theme(self, theme_id: str) -> bool:
        """Remove a theme"""
        if theme_id not in self.themes or theme_id in ["light", "dark", "high_contrast"]:
            # Don't allow removing default themes
            return False
            
        del self.themes[theme_id]
        
        # Reset current theme if it was removed
        if self.current_theme_name == theme_id:
            self.current_theme_name = "light"
            
        self._save_themes()
        return True
    
    def apply_theme(self, root: tk.Tk) -> None:
        """Apply current theme to the UI"""
        self.root = root
        theme = self.get_current_theme()
        
        # Get ttk style
        self.style = ttk.Style(root)
        
        # Configure ttk theme (try to use closest match to current theme)
        try:
            if self.current_theme_name == "dark" or self.current_theme_name == "high_contrast":
                self.style.theme_use("clam")  # clam is more customizable for dark themes
            else:
                self.style.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            # Fallback to default theme
            available_themes = self.style.theme_names()
            if "clam" in available_themes:
                self.style.theme_use("clam")
        
        # Apply colors to root
        root.configure(bg=theme.colors["bg_primary"])
        
        # Configure ttk styles
        self._configure_ttk_styles(theme)
        
        # Apply widget-specific configuration
        self._configure_widgets(root, theme)
        
        # Update option database
        self._configure_option_db(root, theme)
    
    def _configure_ttk_styles(self, theme: Theme) -> None:
        """Configure ttk widget styles"""
        if not self.style:
            return
            
        colors = theme.colors
        
        # Configure TFrame
        self.style.configure("TFrame", background=colors["bg_primary"])
        
        # Configure TLabel
        self.style.configure("TLabel", 
                            background=colors["bg_primary"],
                            foreground=colors["fg_primary"])
        
        # Configure TButton
        self.style.configure("TButton",
                            background=colors["button_bg"],
                            foreground=colors["button_fg"],
                            font=theme.fonts["default"])
        
        self.style.map("TButton",
                      background=[("active", colors["accent_hover"]),
                                 ("pressed", colors["accent"])],
                      foreground=[("active", colors["button_fg"]),
                                 ("pressed", colors["button_fg"])])
        
        # Configure Accent.TButton for primary action buttons
        self.style.configure("Accent.TButton",
                            background=colors["accent"],
                            foreground="white",
                            font=theme.fonts["default"])
        
        self.style.map("Accent.TButton",
                      background=[("active", colors["accent_hover"]),
                                 ("pressed", colors["accent"])])
        
        # Configure Success.TButton for success action buttons
        self.style.configure("Success.TButton",
                            background=colors["success"],
                            foreground="white",
                            font=theme.fonts["default"])
        
        # Configure Warning.TButton and Error.TButton similarly
        self.style.configure("Warning.TButton",
                            background=colors["warning"],
                            foreground="black",
                            font=theme.fonts["default"])
                            
        self.style.configure("Error.TButton",
                            background=colors["error"],
                            foreground="white",
                            font=theme.fonts["default"])
        
        # Configure TEntry (text input fields)
        self.style.configure("TEntry",
                            fieldbackground=colors["input_bg"],
                            foreground=colors["input_fg"],
                            insertcolor=colors["fg_primary"])
        
        self.style.map("TEntry",
                      fieldbackground=[("readonly", colors["bg_secondary"])])
        
        # Configure TCombobox (dropdown menus)
        self.style.configure("TCombobox",
                            fieldbackground=colors["input_bg"],
                            foreground=colors["input_fg"],
                            background=colors["button_bg"],
                            arrowcolor=colors["fg_primary"])
        
        self.style.map("TCombobox",
                      fieldbackground=[("readonly", colors["input_bg"])],
                      foreground=[("readonly", colors["input_fg"])])
        
        # Configure Horizontal.TProgressbar
        self.style.configure("Horizontal.TProgressbar",
                            background=colors["progressbar"],
                            troughcolor=colors["bg_secondary"],
                            bordercolor=colors["border"])
        
        # Configure Vertical.TProgressbar
        self.style.configure("Vertical.TProgressbar",
                            background=colors["progressbar"],
                            troughcolor=colors["bg_secondary"],
                            bordercolor=colors["border"])
        
        # Configure TNotebook (tabs)
        self.style.configure("TNotebook",
                            background=colors["bg_primary"],
                            tabmargins=[2, 5, 2, 0])
        
        self.style.configure("TNotebook.Tab",
                            background=colors["tab_bg"],
                            foreground=colors["tab_fg"],
                            padding=[10, 2],
                            font=theme.fonts["default"])
        
        self.style.map("TNotebook.Tab",
                      background=[("selected", colors["tab_active_bg"]),
                                 ("active", colors["accent"])],
                      foreground=[("selected", colors["tab_active_fg"]),
                                 ("active", "white")])
        
        # Configure Treeview (used for lists and tables)
        self.style.configure("Treeview",
                            background=colors["treeview_bg"],
                            foreground=colors["treeview_fg"],
                            fieldbackground=colors["treeview_bg"],
                            font=theme.fonts["default"])
        
        self.style.map("Treeview",
                      background=[("selected", colors["treeview_selected_bg"])],
                      foreground=[("selected", colors["treeview_selected_fg"])])
        
        # Configure Treeview headers
        self.style.configure("Treeview.Heading",
                            background=colors["bg_secondary"],
                            foreground=colors["fg_primary"],
                            font=theme.fonts["default"])
        
        # Configure TSeparator
        self.style.configure("TSeparator",
                            background=colors["border"])
        
        # Configure TCheckbutton
        self.style.configure("TCheckbutton",
                            background=colors["bg_primary"],
                            foreground=colors["fg_primary"],
                            font=theme.fonts["default"])
        
        self.style.map("TCheckbutton",
                      background=[("active", colors["bg_primary"])],
                      foreground=[("active", colors["fg_primary"])])
        
        # Configure TRadiobutton
        self.style.configure("TRadiobutton",
                            background=colors["bg_primary"],
                            foreground=colors["fg_primary"],
                            font=theme.fonts["default"])
        
        self.style.map("TRadiobutton",
                      background=[("active", colors["bg_primary"])],
                      foreground=[("active", colors["fg_primary"])])
    
    def _configure_widgets(self, parent: tk.Widget, theme: Theme) -> None:
        """Recursively configure all widgets in the application"""
        colors = theme.colors
        
        # Configure this widget based on its type
        if isinstance(parent, tk.Frame) or isinstance(parent, tk.LabelFrame):
            parent.configure(bg=colors["bg_primary"])
        
        elif isinstance(parent, tk.Label):
            parent.configure(bg=colors["bg_primary"], fg=colors["fg_primary"])
        
        elif isinstance(parent, tk.Button):
            parent.configure(
                bg=colors["button_bg"],
                fg=colors["button_fg"],
                activebackground=colors["accent_hover"],
                activeforeground=colors["button_fg"]
            )
            
            # Special styles for specific buttons
            if "accent" in str(parent) or "download" in str(parent).lower():
                parent.configure(bg=colors["accent"], fg="white")
            elif "success" in str(parent):
                parent.configure(bg=colors["success"], fg="white")
            elif "warning" in str(parent):
                parent.configure(bg=colors["warning"], fg="black")
            elif "error" in str(parent):
                parent.configure(bg=colors["error"], fg="white")
        
        elif isinstance(parent, tk.Entry) or isinstance(parent, tk.Text):
            parent.configure(
                bg=colors["input_bg"],
                fg=colors["input_fg"],
                insertbackground=colors["fg_primary"]
            )
            
            # Configure text tags if it's a Text widget
            if isinstance(parent, tk.Text):
                tag_colors = {
                    "current_playlist": colors["current_playlist"],
                    "done_playlist": colors["done_playlist"],
                    "failed_playlist": colors["failed_playlist"]
                }
                
                for tag, color in tag_colors.items():
                    try:
                        parent.tag_configure(tag, background=color)
                    except:
                        pass  # Tag might not exist
        
        elif isinstance(parent, scrolledtext.ScrolledText):
            parent.configure(
                bg=colors["input_bg"],
                fg=colors["input_fg"],
                insertbackground=colors["fg_primary"]
            )
            
            # Configure text tags
            tag_colors = {
                "current_playlist": colors["current_playlist"],
                "done_playlist": colors["done_playlist"],
                "failed_playlist": colors["failed_playlist"]
            }
            
            for tag, color in tag_colors.items():
                try:
                    parent.tag_configure(tag, background=color)
                except:
                    pass  # Tag might not exist
        
        elif isinstance(parent, tk.Listbox):
            parent.configure(
                bg=colors["input_bg"],
                fg=colors["input_fg"],
                selectbackground=colors["treeview_selected_bg"],
                selectforeground=colors["treeview_selected_fg"]
            )
        
        elif isinstance(parent, tk.Canvas):
            parent.configure(bg=colors["bg_primary"])
        
        elif isinstance(parent, tk.Menu):
            parent.configure(
                bg=colors["bg_primary"],
                fg=colors["fg_primary"],
                activebackground=colors["accent"],
                activeforeground="white",
                borderwidth=1,
                relief=tk.SOLID
            )
        
        # Recursively process child widgets
        try:
            for child in parent.winfo_children():
                self._configure_widgets(child, theme)
        except:
            pass  # Some widgets don't support winfo_children
    
    def _configure_option_db(self, root: tk.Tk, theme: Theme) -> None:
        """Configure option database for new widgets"""
        colors = theme.colors
        fonts = theme.fonts
        
        # Default background and foreground
        root.option_add("*Background", colors["bg_primary"])
        root.option_add("*Foreground", colors["fg_primary"])
        
        # Configure fonts
        root.option_add("*Font", fonts["default"])
        root.option_add("*Heading.Font", fonts["heading"])
        root.option_add("*Label.Font", fonts["default"])
        root.option_add("*Button.Font", fonts["default"])
        root.option_add("*Entry.Font", fonts["default"])
        root.option_add("*Text.Font", fonts["default"])
        
        # Configure input widgets
        root.option_add("*Entry.Background", colors["input_bg"])
        root.option_add("*Entry.Foreground", colors["input_fg"])
        root.option_add("*Text.Background", colors["input_bg"])
        root.option_add("*Text.Foreground", colors["input_fg"])
        
        # Configure buttons
        root.option_add("*Button.Background", colors["button_bg"])
        root.option_add("*Button.Foreground", colors["button_fg"])
        root.option_add("*Button.activeBackground", colors["accent_hover"])
        root.option_add("*Button.activeForeground", colors["button_fg"])
        
        # Configure listbox
        root.option_add("*Listbox.Background", colors["input_bg"])
        root.option_add("*Listbox.Foreground", colors["input_fg"])
        root.option_add("*Listbox.selectBackground", colors["treeview_selected_bg"])
        root.option_add("*Listbox.selectForeground", colors["treeview_selected_fg"])
        
        # Configure menu
        root.option_add("*Menu.Background", colors["bg_primary"])
        root.option_add("*Menu.Foreground", colors["fg_primary"])
        root.option_add("*Menu.activeBackground", colors["accent"])
        root.option_add("*Menu.activeForeground", "white")
        root.option_add("*Menu.Borderwidth", 1)
        root.option_add("*Menu.Relief", "solid")
        
        # Configure scrollbars
        root.option_add("*Scrollbar.Background", colors["bg_secondary"])
        root.option_add("*Scrollbar.troughColor", colors["bg_secondary"])
        root.option_add("*Scrollbar.activeBackground", colors["accent"])
        root.option_add("*Scrollbar.borderWidth", 0)
        
        # Configure LabelFrame
        root.option_add("*LabelFrame.Background", colors["bg_primary"])
        root.option_add("*LabelFrame.Foreground", colors["fg_primary"])