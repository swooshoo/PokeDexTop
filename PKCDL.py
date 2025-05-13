import requests
import os
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import time

# Enter your API key below
api_key = "2f3083d2-1a0d-4f68-86cb-b992bcc85f28"

class SetDownloader:
    def __init__(self):
        self.sets_data = None
        self.current_set = None
        self.card_data = None
        self.total_cards = 0
        self.cards_downloaded = 0
        self.cards_failed = 0
        self.download_complete = False
        self.failed_cards = []  # Track which cards failed to download
        
        # Create the GUI
        self.root = tk.Tk()
        self.root.title("Pokemon TCG Set Downloader")
        self.root.geometry("600x350")  # Make window a bit larger

        # Create the set selection dropdown
        self.set_label = ttk.Label(self.root, text="Select a set to download:")
        self.set_label.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)
        self.set_selection = ttk.Combobox(self.root, state="readonly", width=40)
        self.set_selection.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)
        
        # Create the progress bar
        self.progress_frame = ttk.LabelFrame(self.root, text="Download Progress")
        self.progress_frame.grid(column=0, row=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate", length=500)
        self.progress_bar.grid(column=0, row=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create status labels
        self.status_label = ttk.Label(self.progress_frame, text="")
        self.status_label.grid(column=0, row=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.detailed_status = ttk.Label(self.progress_frame, text="")
        self.detailed_status.grid(column=0, row=2, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create the download button
        self.download_button = ttk.Button(self.root, text="Download", command=self.download_set)
        self.download_button.grid(column=0, row=3, padx=5, pady=5)

        # Create the folder selection button
        self.folder_button = ttk.Button(self.root, text="Select Download Folder", command=self.select_folder)
        self.folder_button.grid(column=1, row=3, padx=5, pady=5)

        # Create a log frame
        self.log_frame = ttk.LabelFrame(self.root, text="Download Log")
        self.log_frame.grid(column=0, row=4, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create a scrolled text widget for logging
        self.log_text = tk.Text(self.log_frame, height=8, width=70, wrap=tk.WORD)
        self.log_text.grid(column=0, row=0, padx=5, pady=5)
        
        # Add scrollbar to the log text
        self.log_scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_scrollbar.grid(column=1, row=0, sticky=tk.NS)
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)
        self.log_text.config(state="disabled")  # Make it read-only

        # Create a variable to store the selected download folder path
        self.download_folder_path = ""
        
        # Load the sets data from the API
        self.load_sets_data()
        
        # Start a thread to check download status
        self.status_checker = threading.Thread(target=self.check_download_status)
        self.status_checker.daemon = True
        self.status_checker.start()
        
        # Start the GUI
        self.root.mainloop()
    
    def add_log_message(self, message):
        """Add a message to the log text widget"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Auto-scroll to the bottom
        self.log_text.config(state="disabled")
    
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.download_folder_path = folder_path
            self.status_label.config(text=f"Download folder set to: {folder_path}")
            self.add_log_message(f"Download folder set to: {folder_path}")
    
    def load_sets_data(self):
        try:
            # Make a request to the Pokemon TCG API to get a list of all sets
            sets_response = requests.get(f"https://api.pokemontcg.io/v2/sets", headers={"X-Api-Key": api_key})
            self.sets_data = sets_response.json()["data"]
            
            # Populate the set selection dropdown
            self.set_selection["values"] = [set_data["name"] for set_data in self.sets_data]
            self.add_log_message(f"Successfully loaded {len(self.sets_data)} sets from the API")
        except Exception as e:
            self.add_log_message(f"Error loading sets data: {str(e)}")
    
    def download_set(self):
        # Reset counters
        self.cards_downloaded = 0
        self.cards_failed = 0
        self.failed_cards = []
        self.download_complete = False
        
        # Check if download folder is selected
        if not self.download_folder_path:
            self.status_label.config(text="Please select a download folder first")
            self.add_log_message("Error: No download folder selected")
            return
            
        # Get the currently selected set
        self.current_set = self.set_selection.get()
        if not self.current_set:
            self.status_label.config(text="Please select a set to download")
            self.add_log_message("Error: No set selected")
            return
            
        # Update status
        self.status_label.config(text=f"Starting download of {self.current_set}...")
        self.add_log_message(f"Starting download of {self.current_set}")
        
        # Make a request to the Pokemon TCG API to get a list of all cards for this set
        try:
            set_id = next(set_data["id"] for set_data in self.sets_data if set_data["name"] == self.current_set)
            cards_response = requests.get(f"https://api.pokemontcg.io/v2/cards?q=set.id:{set_id}", headers={"X-Api-Key": api_key})
            self.card_data = cards_response.json()["data"]
            
            # Set the progress bar maximum value
            self.total_cards = len(self.card_data)
            self.progress_bar["maximum"] = self.total_cards
            self.progress_bar["value"] = 0
            
            # Create a directory for this set
            set_folder_path = os.path.join(self.download_folder_path, self.current_set)
            os.makedirs(set_folder_path, exist_ok=True)
            
            # Update status
            self.status_label.config(text=f"Downloading {self.total_cards} cards from {self.current_set}...")
            self.add_log_message(f"Found {self.total_cards} cards in set {self.current_set}")
            
            # Clear the log before starting new download
            self.log_text.config(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state="disabled")
            
            # Download each card image in a separate thread
            for card_index, card_data in enumerate(self.card_data):
                card_thread = threading.Thread(target=self.download_card_image, args=(card_index, card_data, set_folder_path))
                card_thread.start()
        
        except Exception as e:
            self.status_label.config(text=f"Error starting download: {str(e)}")
            self.add_log_message(f"Error starting download: {str(e)}")

    def download_card_image(self, card_index, card_data, set_folder_path):
        card_id = card_data["id"]
        card_number = card_data["number"]
        card_name = card_data["name"]
        
        try:
            card_image_url = card_data["images"]["large"]
            
            # Download the card image
            try:
                card_image_response = requests.get(card_image_url, timeout=30)  # Add timeout
                
                if card_image_response.status_code == 200:
                    # Save the card image to a file in the set folder
                    filename = f"{card_number} {card_name}.png"
                    filepath = os.path.join(set_folder_path, filename)
                    
                    with open(filepath, "wb") as card_image_file:
                        card_image_file.write(card_image_response.content)
                    
                    # Log success
                    self.add_log_message(f"Downloaded: {filename}")
                else:
                    # HTTP error
                    self.cards_failed += 1
                    self.failed_cards.append(f"{card_number} {card_name}")
                    error_msg = f"Failed to download card {card_name} ({card_number}): HTTP {card_image_response.status_code}"
                    self.add_log_message(error_msg)
                    print(error_msg)
            
            except Exception as e:
                # Network or file write error
                self.cards_failed += 1
                self.failed_cards.append(f"{card_number} {card_name}")
                error_msg = f"Error downloading card {card_name} ({card_number}): {str(e)}"
                self.add_log_message(error_msg)
                print(error_msg)
        
        except KeyError:
            # Missing image URL
            self.cards_failed += 1
            self.failed_cards.append(f"{card_number} {card_name}")
            error_msg = f"Error: No image URL for card {card_name} ({card_number})"
            self.add_log_message(error_msg)
            print(error_msg)
        
        # Update the progress bar regardless of success or failure
        # Using a lock to avoid race conditions when updating the progress
        with threading.Lock():
            self.cards_downloaded += 1
            self.progress_bar["value"] = self.cards_downloaded
            
            # Update the GUI with the current progress
            self.root.update_idletasks()
            
            # Check if all cards have been processed (downloaded or failed)
            if self.cards_downloaded == self.total_cards:
                self.download_complete = True
                # Print completion status
                if self.cards_failed > 0:
                    msg = f"Download complete with errors: {self.current_set} - {self.cards_downloaded - self.cards_failed}/{self.total_cards} successful, {self.cards_failed} failed"
                else:
                    msg = f"Download complete: {self.current_set} - All {self.total_cards} cards downloaded successfully!"
                
                print(msg)
                self.add_log_message(msg)
                
                # If there were failures, log them all together at the end
                if self.cards_failed > 0:
                    self.add_log_message(f"Failed cards: {', '.join(self.failed_cards)}")
    
    def check_download_status(self):
        """Thread to continuously check download status and update UI"""
        while True:
            # Only check when a download is in progress
            if self.card_data and not self.download_complete and self.cards_downloaded > 0:
                # Calculate stats
                successful = self.cards_downloaded - self.cards_failed
                percentage = int((self.cards_downloaded / self.total_cards) * 100)
                
                # Update the status labels with current progress
                self.status_label.config(text=f"Downloading: {self.cards_downloaded}/{self.total_cards} cards ({percentage}%)")
                
                if self.cards_failed > 0:
                    self.detailed_status.config(
                        text=f"Success: {successful} | Failed: {self.cards_failed} | Remaining: {self.total_cards - self.cards_downloaded}"
                    )
                else:
                    self.detailed_status.config(
                        text=f"Success: {successful} | Remaining: {self.total_cards - self.cards_downloaded}"
                    )
                
                # Check if download is complete
                if self.cards_downloaded == self.total_cards:
                    self.download_complete = True
                    if self.cards_failed > 0:
                        self.status_label.config(
                            text=f"Download complete with {self.cards_failed} errors: {successful}/{self.total_cards} cards successful"
                        )
                    else:
                        self.status_label.config(
                            text=f"Download complete: All {self.total_cards} cards downloaded successfully!"
                        )
            
            # Sleep to avoid hogging resources
            time.sleep(0.5)


if __name__ == '__main__':
    set_downloader = SetDownloader()