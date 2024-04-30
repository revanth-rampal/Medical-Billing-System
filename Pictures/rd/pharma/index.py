import tkinter as tk
from tkinter import ttk
import subprocess

class MedicalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical Application")

        # Load the logo image and resize it to 200x200
        self.logo_image = tk.PhotoImage(file="logo.png").subsample(8)

        # Create a label to display the logo
        self.logo_label = tk.Label(root, image=self.logo_image)
        self.logo_label.grid(row=0, column=0, padx=10, pady=5)

        # Create buttons for each functionality
        buttons_frame = ttk.Frame(root, padding="20")
        buttons_frame.grid(row=1, column=0)

        # Button to open inventory management
        self.inventory_button = ttk.Button(buttons_frame, text="Inventory", command=self.open_inventory)
        self.inventory_button.grid(row=0, column=0, padx=10, pady=5)

        # Button to open billing system
        self.billing_button = ttk.Button(buttons_frame, text="Billing", command=self.open_billing)
        self.billing_button.grid(row=1, column=0, padx=10, pady=5)

        # Button to open billing history
        self.billing_history_button = ttk.Button(buttons_frame, text="patient details", command=self.open_billing_history)
        self.billing_history_button.grid(row=2, column=0, padx=10, pady=5)

        # Button to view tablets in store
        self.tablets_button = ttk.Button(buttons_frame, text="Tablets in Store", command=self.open_tablets)
        self.tablets_button.grid(row=3, column=0, padx=10, pady=5)

        # Button to view add/remove history
        self.history_button = ttk.Button(buttons_frame, text="Add/Remove History", command=self.open_history)
        self.history_button.grid(row=4, column=0, padx=10, pady=5)

        # Button to view expiry tablets
        self.expiry_button = ttk.Button(buttons_frame, text="Expiry Tablets", command=self.open_expiry)
        self.expiry_button.grid(row=5, column=0, padx=10, pady=5)

    def open_inventory(self):
        subprocess.Popen(["python", "inventory.py"])

    def open_billing(self):
        subprocess.Popen(["python", "pd1.py"])

    def open_billing_history(self):
        subprocess.Popen(["python", "patient_history.py"])

    def open_tablets(self):
        subprocess.Popen(["python", "see.py"])

    def open_history(self):
        subprocess.Popen(["python", "historysee.py"])

    def open_expiry(self):
        subprocess.Popen(["python", "tablet.py"])

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalApp(root)
    root.mainloop()
