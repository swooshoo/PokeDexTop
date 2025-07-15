#!/usr/bin/env python3
"""
PokéDextop - Pokemon TCG Collection Manager
Entry point for the application
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ui.main_window import PokemonDashboard
from config.settings import APP_CONFIG
from utils.helpers import center_window


def setup_application():
    """Set up the QApplication with proper styling"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName(APP_CONFIG['app_name'])
    app.setApplicationVersion(APP_CONFIG['version'])
    return app


def main():
    """Main application entry point"""
    try:
        print(f"==== STARTING {APP_CONFIG['app_name']} ====")
        print("Bronze-Silver-Gold Data Architecture Initialized")
        
        app = setup_application()
        
        # Create and show main window
        main_window = PokemonDashboard()
        center_window(main_window)
        main_window.show()
        
        print("Application ready! Window dimensions locked.")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"CRITICAL APPLICATION ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()