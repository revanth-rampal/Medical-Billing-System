import tkinter as tk
from tkinter import messagebox
import sqlite3
import csv
from tkcalendar import DateEntry
from datetime import datetime

def save_data():
    try:
        medication_id = int(med_id_entry.get())
        price = int(price_entry.get())  # Get price as integer
    except ValueError:
        messagebox.showerror("Error", "Medication ID and Price must be integers.")
        return
    
    medication_name = med_name_entry.get()
    quantity = quantity_entry.get()
    expiration_date = expiration_cal.get_date().strftime('%d/%m/%Y')
    lot_number = lot_entry.get()
    location = location_entry.get()
    current_date = datetime.now().strftime('%d/%m/%Y')  # Get current date in DD/MM/YYYY format

    # Validate input
    if not all([medication_name, quantity, expiration_date, lot_number, location]):
        messagebox.showerror("Error", "Please fill in all fields.")
        return

    # Save to SQLite database (inventory)
    conn_inventory = sqlite3.connect('inventory.db')
    c_inventory = conn_inventory.cursor()
    c_inventory.execute('''CREATE TABLE IF NOT EXISTS Medications
                 (MedicationID INTEGER, MedicationName TEXT, Quantity INTEGER, 
                 ExpirationDate TEXT, LotNumber TEXT, Location TEXT, Price INTEGER, CurrentDate TEXT)''')  # Added CurrentDate column
    c_inventory.execute("INSERT INTO Medications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (medication_id, medication_name, int(quantity), expiration_date, lot_number, location, price, current_date))  # Include current date
    conn_inventory.commit()
    conn_inventory.close()

    # Save to CSV file (inventory)
    with open('inventory.csv', 'a', newline='') as file_inventory:
        writer_inventory = csv.writer(file_inventory)
        writer_inventory.writerow([medication_id, medication_name, quantity, expiration_date, lot_number, location, price, current_date])  # Include current date

    # Save to SQLite database (inventory history)
    conn_history = sqlite3.connect('inventory_history.db')
    c_history = conn_history.cursor()
    c_history.execute('''CREATE TABLE IF NOT EXISTS InventoryHistory
                 (MedicationID INTEGER, MedicationName TEXT, Quantity INTEGER, 
                 ExpirationDate TEXT, LotNumber TEXT, Location TEXT, ADDED TEXT, Price INTEGER, CurrentDate TEXT)''')  # Added CurrentDate column
    c_history.execute("INSERT INTO InventoryHistory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (medication_id, medication_name, int(quantity), expiration_date, lot_number, location, "ADDED", price, current_date))  # Include current date
    conn_history.commit()
    conn_history.close()

    # Save to CSV file (inventory history)
    with open('inventory_history.csv', 'a', newline='') as file_history:
        writer_history = csv.writer(file_history)
        writer_history.writerow([medication_id, medication_name, quantity, expiration_date, lot_number, location, "ADDED", price, current_date])  # Include current date

    messagebox.showinfo("Success", "Data saved successfully.")

# Create GUI
root = tk.Tk()
root.title("Medication Inventory Management")

# Labels
med_id_label = tk.Label(root, text="Medication ID:")
med_id_label.grid(row=0, column=0, padx=5, pady=5)
med_name_label = tk.Label(root, text="Medication Name:")
med_name_label.grid(row=1, column=0, padx=5, pady=5)
quantity_label = tk.Label(root, text="Quantity:")
quantity_label.grid(row=2, column=0, padx=5, pady=5)
expiration_label = tk.Label(root, text="Expiration Date:")
expiration_label.grid(row=3, column=0, padx=5, pady=5)
lot_label = tk.Label(root, text="Lot Number:")
lot_label.grid(row=4, column=0, padx=5, pady=5)
location_label = tk.Label(root, text="Location:")
location_label.grid(row=5, column=0, padx=5, pady=5)
price_label = tk.Label(root, text="Price:")  # New label for Price
price_label.grid(row=6, column=0, padx=5, pady=5)

# Entry fields
med_id_entry = tk.Entry(root)
med_id_entry.grid(row=0, column=1, padx=5, pady=5)
med_name_entry = tk.Entry(root)
med_name_entry.grid(row=1, column=1, padx=5, pady=5)
quantity_entry = tk.Entry(root)
quantity_entry.grid(row=2, column=1, padx=5, pady=5)
expiration_cal = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
expiration_cal.grid(row=3, column=1, padx=5, pady=5)
lot_entry = tk.Entry(root)
lot_entry.grid(row=4, column=1, padx=5, pady=5)
location_entry = tk.Entry(root)
location_entry.grid(row=5, column=1, padx=5, pady=5)
price_entry = tk.Entry(root)  # Entry field for Price
price_entry.grid(row=6, column=1, padx=5, pady=5)

# Save button
save_button = tk.Button(root, text="Save", command=save_data)
save_button.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="WE")

root.mainloop()
