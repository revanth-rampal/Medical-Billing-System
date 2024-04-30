import tkinter as tk
from tkinter import ttk
import sqlite3

class BillingHistoryViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Billing History Viewer")

        # Connect to the SQLite database
        self.conn = sqlite3.connect('billing_history.db')
        self.cursor = self.conn.cursor()

        # Create the BillingHistory table if it doesn't exist
        self.create_table()

        # Create Treeview to display billing history
        self.columns = ("Medication Name", "Quantity", "Price", "GST Price", "Total Price", "Billing Date and time")
        self.treeview = ttk.Treeview(root, columns=self.columns, show="headings")
        for col in self.columns:
            self.treeview.heading(col, text=col)
        self.treeview.grid(row=0, column=0, padx=5, pady=5)

        # Button to fetch and display data
        self.fetch_button = ttk.Button(root, text="Fetch Data", command=self.fetch_data)
        self.fetch_button.grid(row=1, column=0, padx=5, pady=5)

    def create_table(self):
        # Create BillingHistory table if it doesn't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS BillingHistory (
                MedicationName TEXT,
                Quantity INTEGER,
                Price REAL,
                GSTPrice REAL,
                TotalPrice REAL,  -- Adding TotalPrice column
                BillingDateTime TEXT
            )
        """)
        self.conn.commit()

    def fetch_data(self):
        # Clear existing data
        for row in self.treeview.get_children():
            self.treeview.delete(row)

        # Fetch data from the database
        self.cursor.execute("SELECT * FROM BillingHistory")
        data = self.cursor.fetchall()

        # Insert data into Treeview
        for row in data:
            self.treeview.insert("", "end", values=row)

if __name__ == "__main__":
    root = tk.Tk()
    billing_history_viewer = BillingHistoryViewer(root)
    root.mainloop()
