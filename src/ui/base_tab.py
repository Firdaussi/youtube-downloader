import tkinter as tk
from src.utils.logging_utils import get_logger

class BaseTab(tk.Frame):
    """Base class for tab frames"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Use get_logger from logging_utils with the class name
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.create_widgets()
    
    def create_widgets(self):
        """Override in subclasses to create widgets"""
        raise NotImplementedError

