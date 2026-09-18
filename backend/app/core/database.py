"""
Database bridge module for backend API.
This imports the core database manager from the project root.
"""
import sys
import os

# Add project root to path to import core.database
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.database import DatabaseManager

__all__ = ['DatabaseManager']
