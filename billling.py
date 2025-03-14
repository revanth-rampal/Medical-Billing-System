import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class BillingSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical Billing System")
        
        # Connect to the SQLite database
        self.conn = sqlite3.connect('inventory.db')
        self.cursor = self.conn.cursor()

        # Label and Entry for Medication ID
        self.label_medication_id = ttk.Label(root, text="Medication ID:")
        self.label_medication_id.grid(row=0, column=0, padx=5, pady=5)
        self.entry_medication_id = ttk.Entry(root)
        self.entry_medication_id.grid(row=0, column=1, padx=5, pady=5)
        
        # Label and Entry for Quantity
        self.label_quantity = ttk.Label(root, text="Quantity:")
        self.label_quantity.grid(row=3, column=0, padx=5, pady=5)
        self.entry_quantity = ttk.Entry(root)
        self.entry_quantity.grid(row=3, column=1, padx=5, pady=5)
        
        # Button to add medication to bill
        self.button_add_medication = ttk.Button(root, text="Add Medication", command=self.add_medication_to_bill)
        self.button_add_medication.grid(row=4, column=0, padx=5, pady=5)
        
        # Button to remove medication from bill
        self.button_remove_medication = ttk.Button(root, text="Remove Medication", command=self.remove_medication_from_bill)
        self.button_remove_medication.grid(row=4, column=1, padx=5, pady=5)
        
        # Button to print receipt
        self.button_print_receipt = ttk.Button(root, text="Print Receipt", command=self.print_receipt)
        self.button_print_receipt.grid(row=4, column=2, padx=5, pady=5)
        
        # Treeview to display bill
        self.columns = ("Medication Name", "Price", "Quantity", "Single Price", "GST", "Total Price")
        self.treeview = ttk.Treeview(root, columns=self.columns, show="headings")
        for col in self.columns:
            self.treeview.heading(col, text=col)
        self.treeview.grid(row=5, column=0, columnspan=3, padx=5, pady=5)
        
        # Total price label
        self.label_total_price = ttk.Label(root, text="Total Price:")
        self.label_total_price.grid(row=6, column=0, padx=5, pady=5)
        self.total_price_var = tk.DoubleVar()  # Change to DoubleVar
        self.label_total_price_value = ttk.Label(root, textvariable=self.total_price_var)
        self.label_total_price_value.grid(row=6, column=1, padx=5, pady=5)
        
        # Initialize bill details
        self.bill = []
        self.total_price = 0

    def add_medication_to_bill(self):
        medication_id = self.entry_medication_id.get()
        quantity = self.entry_quantity.get()

        # Fetch medication details from the database
        self.cursor.execute("SELECT MedicationName, Price, Quantity FROM Medications WHERE MedicationID=?", (medication_id,))
        medication_details = self.cursor.fetchone()

        if medication_details:
            medication_name, price, available_quantity = medication_details
            single_price = price
            gst = price * 0.06  # 6% GST
            
            # Check if entered quantity is valid
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    raise ValueError("Quantity must be a positive integer")
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a positive integer")
                return
            
            # Check if entered quantity exceeds available quantity
            total_quantity_in_bill = sum(item[3] for item in self.bill if item[0] == medication_id)  # Sum of quantity of same medication in bill
            if total_quantity_in_bill + quantity > available_quantity:
                messagebox.showerror("Error", "Total quantity exceeds available stock")
                return
            
            total_price = (float(quantity) * price) + (float(quantity) * gst)  # Total price including GST
            
            # Update the bill
            self.bill.append((medication_id, medication_name, price, quantity, single_price, gst, total_price))
            
            # Update the total price
            self.total_price += total_price
            
            # Update the treeview
            self.treeview.insert("", "end", values=(medication_name, price, quantity, single_price, gst, total_price))
            
            # Update total price label with formatted value
            self.total_price_var.set("{:.2f}".format(self.total_price))  # Format to display only two decimal places
        else:
            messagebox.showerror("Error", f"Medication with ID {medication_id} not found.")
            
    def remove_medication_from_bill(self):
        selected_item = self.treeview.selection()
        if selected_item:
            item_values = self.treeview.item(selected_item, 'values')
            total_price = item_values[5]  # Total price is at index 5
            
            # Ensure total_price is a float
            if isinstance(total_price, str):
                total_price = float(total_price)

            self.total_price -= total_price
            self.total_price_var.set("{:.2f}".format(self.total_price))  # Format to display only two decimal places
            self.treeview.delete(selected_item)
            for index, item in enumerate(self.bill):
                if item[1] == item_values[0]:
                    self.bill.pop(index)
                    break
        else:
            messagebox.showerror("Error", "Please select an item to remove from the bill.")
            
    def print_receipt(self):
        try:
            with sqlite3.connect('inventory.db') as conn:
                cursor = conn.cursor()
                for item in self.bill:
                    medication_id, _, _, quantity, _, _, _ = item
                    cursor.execute("UPDATE Medications SET Quantity = Quantity - ? WHERE MedicationID = ?", (quantity, medication_id))
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        else:
            messagebox.showinfo("Receipt Printed", "Receipt printed successfully")

        # Clear the bill and reset total price
        self.bill = []
        self.total_price = 0
        self.total_price_var.set(0.0)
        self.treeview.delete(*self.treeview.get_children())

if __name__ == "__main__":
    root = tk.Tk()
    billing_system = BillingSystem(root)
    root.mainloop()
