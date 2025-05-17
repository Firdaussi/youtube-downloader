import tkinter as tk
from tkinter import ttk, messagebox

from src.ui.presenters import HistoryPresenter
from src.ui.base_tab import BaseTab
from src.utils.logging_utils import get_logger


class HistoryTab(BaseTab):
    """History tab implementation"""
    
    def __init__(self, parent, presenter: HistoryPresenter, **kwargs):
        # Get tab-specific logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.presenter = presenter
        super().__init__(parent, **kwargs)
        self.logger.debug("History tab initialized")
    
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
