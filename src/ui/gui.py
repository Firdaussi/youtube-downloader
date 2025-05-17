import tkinter as tk
from tkinter import ttk, messagebox
import logging

from src.ui.presenters import DownloadPresenter, HistoryPresenter, SettingsPresenter
from src.ui.tabs.download_tab import DownloadTab
from src.ui.tabs.history_tab import HistoryTab
from src.ui.tabs.settings_tab import SettingsTab
from src.utils.logging_utils import get_logger
from src.ui.base_tab import BaseTab

# Get module logger
logger = get_logger(__name__)

class YouTubeDownloaderApp(tk.Tk):
    """Main application window"""
    
    def __init__(self, 
                 download_presenter: DownloadPresenter,
                 history_presenter: HistoryPresenter,
                 settings_presenter: SettingsPresenter):
        super().__init__()
        
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.title("YouTube Playlist Downloader")
        self.geometry("900x800")
        self.resizable(True, True)
        
        self.download_presenter = download_presenter
        self.history_presenter = history_presenter
        self.settings_presenter = settings_presenter
        
        self.create_widgets()
        self.logger.info("Application UI initialized")
        
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
        
        self.logger.debug("All tabs created and added to notebook")
        
    def on_closing(self):
        """Handle application close"""
        if messagebox.askokcancel("Quit", "Do you want to quit? Any active downloads will be stopped."):
            self.logger.info("Application closing, stopping downloads")
            self.download_presenter.stop_downloads()
            self.destroy()