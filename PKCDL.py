import requests
import os
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import time

# Enter your API key below
api_key = "f877e428-0cdf-4598-ad05-13db2b92ddf8"

class SetDownloader:
    def __init__(self):
        self.sets_data = None
        self.current_set = None
        self.card_data = None
        self.total_cards = 0
        self.cards_downloaded = 0
        self.download_complete = False
        
        # Create the GUI
        self.root = tk.Tk()
        self.root.title("Pokemon TCG Set Downloader")

        # Create the set selection dropdown
        self.set_label = ttk.Label(self.root, text="Select a set to download:")
        self.set_label.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)
        self.set_selection = ttk.Combobox(self.root, state="readonly")
        self.set_selection.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)
        
        # Create the progress bar
        self.progress_bar = ttk.Progressbar(self.root, mode="determinate")
        self.progress_bar.grid(column=0, row=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create status label
        self.status_label = ttk.Label(self.root, text="")
        self.status_label.grid(column=0, row=2, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create the download button
        self.download_button = ttk.Button(self.root, text="Download", command=self.download_set)
        self.download_button.grid(column=0, row=3, columnspan=2, padx=5, pady=5)

        # Create the folder selection button
        self.folder_button = ttk.Button(self.root, text="Select Download Folder", command=self.select_folder)
        self.folder_button.grid(column=0, row=4, columnspan=2, padx=5, pady=5)

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
    
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.download_folder_path = folder_path
            self.status_label.config(text=f"Download folder set to: {folder_path}")
    
    def load_sets_data(self):
        # Make a request to the Pokemon TCG API to get a list of all sets
        sets_response = requests.get(f"https://api.pokemontcg.io/v2/sets", headers={"X-Api-Key": api_key})
        self.sets_data = sets_response.json()["data"]
        
        # Populate the set selection dropdown
        self.set_selection["values"] = [set_data["name"] for set_data in self.sets_data]
    
    def download_set(self):
        # Reset counters
        self.cards_downloaded = 0
        self.download_complete = False
        
        # Check if download folder is selected
        if not self.download_folder_path:
            self.status_label.config(text="Please select a download folder first")
            return
            
        # Get the currently selected set
        self.current_set = self.set_selection.get()
        if not self.current_set:
            self.status_label.config(text="Please select a set to download")
            return
            
        # Update status
        self.status_label.config(text=f"Starting download of {self.current_set}...")
        
        # Make a request to the Pokemon TCG API to get a list of all cards for this set
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
        
        # Download each card image in a separate thread
        for card_index, card_data in enumerate(self.card_data):
            card_thread = threading.Thread(target=self.download_card_image, args=(card_index, card_data, set_folder_path))
            card_thread.start()

    def download_card_image(self, card_index, card_data, set_folder_path):
        card_id = card_data["id"]
        card_number = card_data["number"]
        card_name = card_data["name"]
        card_image_url = card_data["images"]["large"]
        
        # Download the card image
        try:
            card_image_response = requests.get(card_image_url)
            
            # Save the card image to a file in the set folder
            with open(os.path.join(set_folder_path, f"{card_number} {card_name}.png"), "wb") as card_image_file:
                card_image_file.write(card_image_response.content)
            
            # Update the progress bar
            self.cards_downloaded += 1
            self.progress_bar["value"] = self.cards_downloaded
            
            # Update the GUI with the current progress
            self.root.update_idletasks()
            
            # Check if all cards have been downloaded
            if self.cards_downloaded == self.total_cards:
                self.download_complete = True
                # Print to console that download is complete
                print(f"Download complete: {self.current_set} - All {self.total_cards} cards downloaded successfully!")
                # Update status label
                self.status_label.config(text=f"Download complete: {self.current_set} - All {self.total_cards} cards downloaded!")
        
        except Exception as e:
            print(f"Error downloading card {card_name} ({card_number}): {str(e)}")
    
    def check_download_status(self):
        """Thread to continuously check download status and update UI"""
        while True:
            # Only check when a download is in progress
            if self.card_data and not self.download_complete and self.cards_downloaded > 0:
                # Update the status label with current progress
                percentage = int((self.cards_downloaded / self.total_cards) * 100)
                self.status_label.config(text=f"Downloading: {self.cards_downloaded}/{self.total_cards} cards ({percentage}%)")
                
                # Check if download is complete
                if self.cards_downloaded == self.total_cards:
                    self.download_complete = True
                    self.status_label.config(text=f"Download complete: {self.current_set} - All {self.total_cards} cards downloaded!")
                    print(f"Download complete: {self.current_set} - All {self.total_cards} cards downloaded successfully!")
            
            # Sleep to avoid hogging resources
            time.sleep(0.5)


if __name__ == '__main__':
    set_downloader = SetDownloader()