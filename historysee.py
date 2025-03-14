import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime

def view_history():
    # Connect to the SQLite database
    conn = sqlite3.connect("inventory_history.db")
    cursor = conn.cursor()

    # Create the InventoryHistory table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS InventoryHistory
                      (MedicationID INTEGER, MedicationName TEXT, Quantity INTEGER, 
                       ExpirationDate TEXT, LotNumber TEXT, Location TEXT, ADDED TEXT, CurrentDate TEXT)''')  # Added CurrentDate column
    conn.commit()

    # Fetch data from the database
    cursor.execute("SELECT * FROM InventoryHistory")
    rows = cursor.fetchall()

    # Create and populate a new window to display the data
    history_window = tk.Toplevel(root)
    history_window.title("Inventory History Details")

    treeview = ttk.Treeview(history_window)
    treeview.pack(expand=True, fill="both")

    # Add columns to the Treeview
    columns = ("Medication ID", "Medication Name", "Quantity", "Expiration Date", "Lot Number", "Location", "Status", "Price","Date")  # Added "Current Date" column
    treeview["columns"] = columns
    for col in columns:
        treeview.heading(col, text=col)

    # Populate the Treeview with data
    for row in rows:
        treeview.insert("", "end", values=row)

    # Close the database connection
    conn.close()

# Create GUI
root = tk.Tk()
root.title("Inventory History Viewer")

# Button to view history
view_button = tk.Button(root, text="View Inventory History", command=view_history)
view_button.pack(padx=10, pady=10)

root.mainloop()
