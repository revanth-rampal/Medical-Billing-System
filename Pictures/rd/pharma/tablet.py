import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta

# Create InventoryHistory table if not exists
def create_inventory_history_table():
    conn_history = sqlite3.connect('inventory_history.db')
    c_history = conn_history.cursor()
    c_history.execute('''CREATE TABLE IF NOT EXISTS InventoryHistory
                 (MedicationID INTEGER, MedicationName TEXT, Quantity INTEGER, 
                 ExpirationDate TEXT, LotNumber TEXT, Location TEXT, ADDED TEXT, Price INTEGER, CurrentDate TEXT)''')
    conn_history.commit()
    conn_history.close()

# Load data from database
def load_data_from_db():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Medications")
    data = c.fetchall()
    conn.close()
    return data

# Check expiry dates and calculate days left
def check_expiry_dates(data):
    today = datetime.today()
    expiring_soon = []
    for item in data:
        expiration_date = datetime.strptime(item[3], '%d/%m/%Y')
        days_left = (expiration_date - today).days
        if 0 <= days_left <= 180:  # Check if expiry date falls within the next 6 months
            expiring_soon.append((item[1], item[2], item[3], days_left, item[4], item[5]))  # Include Lot Number and Location
    return expiring_soon

# Remove selected item from treeview and database
def remove_item():
    selected_item = tree.selection()
    if selected_item:
        item_values = tree.item(selected_item, 'values')
        medication_name = item_values[0]
        medication_id = None
        # Retrieve the MedicationID from the database using the MedicationName
        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("SELECT MedicationID FROM Medications WHERE MedicationName=?", (medication_name,))
        result = c.fetchone()
        if result:
            medication_id = result[0]
        conn.close()
        if medication_id:
            # Append "REMOVED" to the inventory_history.db
            conn_history = sqlite3.connect('inventory_history.db')
            c_history = conn_history.cursor()
            current_date = datetime.now().strftime('%d/%m/%Y')  # Get current date in DD/MM/YYYY format
            c_history.execute("INSERT INTO InventoryHistory (MedicationID, MedicationName, Quantity, ExpirationDate, LotNumber, Location, ADDED, CurrentDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (medication_id, medication_name, item_values[1], item_values[2], item_values[4], item_values[5 ], 'REMOVED', current_date))
            conn_history.commit()
            conn_history.close()
            
            # Delete from SQLite database
            conn = sqlite3.connect('inventory.db')
            c = conn.cursor()
            c.execute("DELETE FROM Medications WHERE MedicationID=?", (medication_id,))
            conn.commit()
            conn.close()
            
            tree.delete(selected_item)
            
            # Show remaining tablets
            show_remaining_tablets()
            messagebox.showinfo("Success", "Item removed successfully.")
        else:
            messagebox.showerror("Error", "Unable to find MedicationID for the selected item.")
    else:
        messagebox.showerror("Error", "Please select an item to remove.")

# Show remaining tablets in Treeview
def show_remaining_tablets():
    tree.delete(*tree.get_children())
    data_db = load_data_from_db()
    expiring_soon = check_expiry_dates(data_db)
    for item in expiring_soon:
        tree.insert("", "end", values=item)

# Create GUI
root = tk.Tk()
root.title("Expiring Tablets Checker")

# Create Treeview
columns = ("Medication Name", "Quantity", "Expiration Date", "Days Left", "Lot Number", "Location")
tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
for col in columns:
    tree.heading(col, text=col)
tree.pack(padx=20, pady=10)

# Remove button
remove_button = tk.Button(root, text="Remove", command=remove_item)
remove_button.pack(pady=10)

# Create InventoryHistory table if not exists
create_inventory_history_table()

# Show initial data in Treeview
show_remaining_tablets()

root.mainloop()
