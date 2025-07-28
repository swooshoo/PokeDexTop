"""
ui/dialogs/generation_loading_dialog.py

Loading dialog shown during generation preloading with progress indication.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QMovie, QPixmap


class GenerationLoadingDialog(QDialog):
    """
    Professional loading dialog for generation preloading
    
    Features:
    - Progress bar with percentage
    - Current Pokemon being loaded
    - Estimated time remaining
    - Cancel button
    - Animated loading indicator
    """
    
    # Signal emitted when user cancels
    cancelled = pyqtSignal()
    
    def __init__(self, generation_name: str, total_cards: int, parent=None):
        super().__init__(parent)
        self.generation_name = generation_name
        self.total_cards = total_cards
        self.start_time = None
        self.current_card = 0
        
        self.initUI()
    
    def initUI(self):
        """Initialize the loading dialog UI"""
        self.setWindowTitle(f"Loading {self.generation_name}")
        self.setModal(True)
        self.setFixedSize(450, 250)
        
        # Prevent closing with X button during loading
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        self.title_label = QLabel(f"Loading {self.generation_name}")
        self.title_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        
        # Subtitle
        self.subtitle_label = QLabel("Preparing all Pokemon cards for smooth scrolling...")
        self.subtitle_label.setFont(QFont('Arial', 10))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 15px;")
        layout.addWidget(self.subtitle_label)
        
        # Progress section
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #e9ecef;
            }
        """)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_cards)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #ecf0f1;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #3498db, stop: 1 #2980b9);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # Progress info layout
        info_layout = QHBoxLayout()
        
        # Current item being loaded
        self.current_item_label = QLabel("Initializing...")
        self.current_item_label.setFont(QFont('Arial', 9))
        self.current_item_label.setStyleSheet("color: #34495e;")
        info_layout.addWidget(self.current_item_label)
        
        info_layout.addStretch()
        
        # Progress counter
        self.progress_counter_label = QLabel(f"0 / {self.total_cards}")
        self.progress_counter_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.progress_counter_label.setStyleSheet("color: #3498db;")
        info_layout.addWidget(self.progress_counter_label)
        
        progress_layout.addLayout(info_layout)
        
        # Time estimation
        self.time_estimate_label = QLabel("Estimating time...")
        self.time_estimate_label.setFont(QFont('Arial', 8))
        self.time_estimate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_estimate_label.setStyleSheet("color: #95a5a6;")
        progress_layout.addWidget(self.time_estimate_label)
        
        layout.addWidget(progress_frame)
        
        # Performance info
        self.performance_label = QLabel("💡 After loading: Perfect smooth scrolling with zero lag!")
        self.performance_label.setFont(QFont('Arial', 9))
        self.performance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.performance_label.setStyleSheet("color: #27ae60; margin-top: 10px;")
        layout.addWidget(self.performance_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button (optional - can be disabled during critical loading)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(QFont('Arial', 10))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Apply dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 10px;
            }
        """)
    
    def update_progress(self, current: int, total: int, message: str):
        """Update the progress dialog with current status"""
        import time
        
        self.current_card = current
        
        # Update progress bar
        self.progress_bar.setValue(current)
        
        # Update counter
        self.progress_counter_label.setText(f"{current} / {total}")
        
        # Update current item
        self.current_item_label.setText(message)
        
        # Calculate and show percentage
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar.setFormat(f"{percentage:.0f}%")
        
        # Time estimation
        if current > 0:
            if self.start_time is None:
                self.start_time = time.time()
            
            elapsed = time.time() - self.start_time
            if elapsed > 1:  # Only show estimate after 1 second
                rate = current / elapsed  # cards per second
                remaining_cards = total - current
                
                if rate > 0:
                    remaining_time = remaining_cards / rate
                    
                    if remaining_time < 60:
                        time_text = f"~{remaining_time:.0f} seconds remaining"
                    else:
                        minutes = remaining_time / 60
                        time_text = f"~{minutes:.1f} minutes remaining"
                    
                    self.time_estimate_label.setText(time_text)
                else:
                    self.time_estimate_label.setText("Calculating time...")
        
        # Update title with progress
        self.title_label.setText(f"Loading {self.generation_name} ({current}/{total})")
        
        # Disable cancel button when nearly complete
        if current >= total * 0.9:  # Last 10%
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Completing...")
    
    def set_completed(self):
        """Mark loading as completed"""
        self.progress_bar.setValue(self.total_cards)
        self.progress_bar.setFormat("100%")
        self.current_item_label.setText("Loading complete!")
        self.time_estimate_label.setText("Ready for smooth scrolling!")
        self.title_label.setText(f"{self.generation_name} Ready!")
        
        # Change cancel button to close
        self.cancel_button.setText("Close")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.cancel_button.setEnabled(True)
        
        # Auto-close after a brief delay
        QTimer.singleShot(1500, self.accept)
    
    def set_error(self, error_message: str):
        """Mark loading as failed"""
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e74c3c;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #fadbd8;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
                border-radius: 6px;
            }
        """)
        
        self.title_label.setText(f"Error Loading {self.generation_name}")
        self.title_label.setStyleSheet("color: #e74c3c; margin-bottom: 10px;")
        self.current_item_label.setText(f"Error: {error_message}")
        self.time_estimate_label.setText("Loading failed")
        
        # Change cancel button to retry/close
        self.cancel_button.setText("Close")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_button.setEnabled(True)
    
    def on_cancel(self):
        """Handle cancel button click"""
        if self.cancel_button.text() == "Cancel":
            # Emit cancel signal
            self.cancelled.emit()
        
        # Close dialog
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Emit cancel signal if loading is in progress
        if self.cancel_button.text() == "Cancel":
            self.cancelled.emit()
        event.accept()


class QuickLoadingDialog(QDialog):
    """
    Simpler, faster loading dialog for quick operations
    """
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(300, 120)
        
        # Remove window decorations for a cleaner look
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Message
        message_label = QLabel(message)
        message_label.setFont(QFont('Arial', 10))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(message_label)
        
        # Simple progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #3498db, stop: 1 #2980b9);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
                border: 2px solid #3498db;
            }
        """)
    
    def auto_close(self, delay_ms: int = 1000):
        """Auto-close the dialog after a delay"""
        QTimer.singleShot(delay_ms, self.accept)