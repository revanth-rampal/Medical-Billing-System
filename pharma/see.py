import sqlite3
import tkinter as tk
from tkinter import ttk

def view_table_contents():
    table_name = table_combobox.get()
    if not table_name:
        return

    # Clear the treeview
    for row in treeview.get_children():
        treeview.delete(row)

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()

    for row in rows:
        treeview.insert("", "end", values=row)

    conn.close()

# Create the main window
root = tk.Tk()
root.title("SQLite Database Viewer")

# Create a combobox to select the table
table_combobox = ttk.Combobox(root, state="readonly", width=30)
table_combobox.grid(row=0, column=0, padx=10, pady=10)

# Button to view table contents
view_button = ttk.Button(root, text="View Table Contents", command=view_table_contents)
view_button.grid(row=0, column=1, padx=10, pady=10)

# Create a Treeview widget to display table contents
treeview = ttk.Treeview(root, columns=("column1", "column2", "column3", "column4", "column5", "column6", "column7"), show="headings")
treeview.heading("column1", text="Medication ID")
treeview.heading("column2", text="Medication Name")
treeview.heading("column3", text="Quantity")
treeview.heading("column4", text="Expiration Date")
treeview.heading("column5", text="Lot Number")
treeview.heading("column6", text="Location")
treeview.heading("column7", text="Price")  # Added column for Price
treeview.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

# Connect to the SQLite database and populate the combobox with table names
conn = sqlite3.connect("inventory.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
table_names = [table[0] for table in tables]
table_combobox["values"] = table_names

conn.close()

root.mainloop()
