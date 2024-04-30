import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime
from fpdf import FPDF

class MedicalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medical Application")

        # Initialize databases
        self.conn_patient_details = sqlite3.connect('patient_details.db', check_same_thread=False)
        self.conn_inventory = sqlite3.connect('inventory.db', check_same_thread=False)
        self.conn_billing_history = sqlite3.connect('billing_history.db', check_same_thread=False)

        # Initialize cursors
        self.cursor_patient_details = self.conn_patient_details.cursor()
        self.cursor_inventory = self.conn_inventory.cursor()
        self.cursor_billing_history = self.conn_billing_history.cursor()

        # Prompt user to enter patient ID
        self.label_patient_id = ttk.Label(root, text="Enter Patient ID:")
        self.label_patient_id.grid(row=0, column=0, padx=5, pady=5)
        self.entry_patient_id = ttk.Entry(root)
        self.entry_patient_id.grid(row=0, column=1, padx=5, pady=5)

        # Button to check patient and start billing system
        self.check_button = ttk.Button(root, text="Start Billing", command=self.check_patient)
        self.check_button.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="WE")

    def check_patient(self):
        patient_id = self.entry_patient_id.get()

        # Check if patient exists in the database
        self.cursor_patient_details.execute("SELECT * FROM Patients WHERE PatientID=?", (patient_id,))
        patient_details = self.cursor_patient_details.fetchone()

        if patient_details:
            # If patient exists, show billing system
            billing_system = BillingSystem(self.root, self.cursor_patient_details)
            billing_system.set_patient_id(patient_id)  # Set the patient ID in the billing system
            # Hide the Start Billing button
            self.check_button.grid_forget()
        else:
            # If patient doesn't exist, show alert and then register new patient
            messagebox.showinfo("Not Found", "Patient with ID not found.")
            self.register_patient()

    def register_patient(self):
        register_window = tk.Toplevel(self.root)
        register_window.title("Register New Patient")

        # Registration form elements
        patient_id_label = ttk.Label(register_window, text="Patient ID:")
        patient_id_label.grid(row=0, column=0, padx=5, pady=5)
        patient_id_entry = ttk.Entry(register_window)
        patient_id_entry.grid(row=0, column=1, padx=5, pady=5)

        first_name_label = ttk.Label(register_window, text="First Name:")
        first_name_label.grid(row=1, column=0, padx=5, pady=5)
        first_name_entry = ttk.Entry(register_window)
        first_name_entry.grid(row=1, column=1, padx=5, pady=5)

        last_name_label = ttk.Label(register_window, text="Last Name:")
        last_name_label.grid(row=2, column=0, padx=5, pady=5)
        last_name_entry = ttk.Entry(register_window)
        last_name_entry.grid(row=2, column=1, padx=5, pady=5)

        dob_label = ttk.Label(register_window, text="Date of Birth:")
        dob_label.grid(row=3, column=0, padx=5, pady=5)
        dob_cal = DateEntry(register_window, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        dob_cal.grid(row=3, column=1, padx=5, pady=5)

        gender_label = ttk.Label(register_window, text="Gender:")
        gender_label.grid(row=4, column=0, padx=5, pady=5)
        gender_var = tk.StringVar(register_window)
        gender_var.set("Male")  # Default value
        gender_option = ttk.OptionMenu(register_window, gender_var, "Male", "Female", "Others")
        gender_option.grid(row=4, column=1, padx=5, pady=5)

        email_label = ttk.Label(register_window, text="Email:")
        email_label.grid(row=5, column=0, padx=5, pady=5)
        email_entry = ttk.Entry(register_window)
        email_entry.grid(row=5, column=1, padx=5, pady=5)

        phone_label = ttk.Label(register_window, text="Phone:")
        phone_label.grid(row=6, column=0, padx=5, pady=5)
        phone_entry = ttk.Entry(register_window)
        phone_entry.grid(row=6, column=1, padx=5, pady=5)

        def save_registration():
            # Get data from entry fields
            patient_id = patient_id_entry.get()
            first_name = first_name_entry.get()
            last_name = last_name_entry.get()
            date_of_birth = dob_cal.get_date().strftime('%d/%m/%Y')
            gender = gender_var.get()
            email = email_entry.get()
            phone = phone_entry.get()

            # Validate input
            if not all([patient_id, first_name, last_name, date_of_birth, gender, email, phone]):
                messagebox.showerror("Error", "Please fill in all fields.")
                return

            # Save to SQLite database
            self.cursor_patient_details.execute('''CREATE TABLE IF NOT EXISTS Patients
                         (PatientID INTEGER PRIMARY KEY, FirstName TEXT, LastName TEXT, DateOfBirth TEXT, Gender TEXT, Email TEXT, Phone TEXT)''')
            self.cursor_patient_details.execute("INSERT INTO Patients VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (int(patient_id), first_name, last_name, date_of_birth, gender, email, phone))
            self.conn_patient_details.commit()

            messagebox.showinfo("Success", "Patient registered successfully.")
            register_window.destroy()  # Close the registration window after successful registration

        # Save button for registration
        save_button = ttk.Button(register_window, text="Save", command=save_registration)
        save_button.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="WE")


class BillingSystem:
    def __init__(self, root, cursor_patient_details):
        self.root = root
        self.cursor_patient_details = cursor_patient_details  # Store the cursor for patient details
        
        self.root.title("Medical Billing System")
        
        # Connect to the SQLite database for inventory
        self.conn_inventory = sqlite3.connect('inventory.db', check_same_thread=False)
        self.cursor_inventory = self.conn_inventory.cursor()

        # Connect to the SQLite database for billing history
        self.conn_billing_history = sqlite3.connect('billing_history.db', check_same_thread=False)
        self.cursor_billing_history = self.conn_billing_history.cursor()

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
        self.columns = ("id", "medication name", "price", "quantity", "PRICE", "GST ")
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
        self.patient_id = None

    def set_patient_id(self, patient_id):
        self.patient_id = patient_id
        
    def add_medication_to_bill(self):
        medication_id = self.entry_medication_id.get()
        quantity = self.entry_quantity.get()

        # Fetch medication details from the inventory database
        self.cursor_inventory.execute("SELECT MedicationName, Price, Quantity FROM Medications WHERE MedicationID=?", (medication_id,))
        medication_details = self.cursor_inventory.fetchone()

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
            self.treeview.insert("", "end", values=(medication_id, medication_name, price, quantity, single_price, gst))
            
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
                if item[0] == item_values[0]:
                    self.bill.pop(index)
                    break
        else:
            messagebox.showerror("Error", "Please select an item to remove from the bill.")
            
    def print_receipt(self):
        try:
            if not self.patient_id:
                raise ValueError("Patient ID not set")

            # Create PDF for receipt
            class PDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 12)
                    self.cell(0, 10, 'Receipt', 0, 1, 'C')

                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, 'Page %s' % self.page_no(), 0, 0, 'C')

            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)

            # Add patient details to receipt
            self.cursor_patient_details.execute("SELECT * FROM Patients WHERE PatientID=?", (self.patient_id,))
            patient_details = self.cursor_patient_details.fetchone()
            if patient_details:
                pdf.cell(200, 10, txt="Patient Details", ln=True, align='C')
                pdf.cell(200, 10, txt=f"Patient ID: {patient_details[0]}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Name: {patient_details[1]} {patient_details[2]}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Date of Birth: {patient_details[3]}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Gender: {patient_details[4]}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Email: {patient_details[5]}", ln=True, align='L')
                pdf.cell(200, 10, txt=f"Phone: {patient_details[6]}", ln=True, align='L')
                pdf.cell(200, 10, txt="", ln=True, align='L')

            # Add billing details to receipt
            pdf.cell(200, 10, txt="Billing Details", ln=True, align='C')
            
            # Define column widths
            col_widths = [10, 30, 30, 30, 30, 20, 20]
            col_names = ["id", "medication name", "price", "quantity", "PRICE", "GST", "Total"]
            
            # Add column names
            for col_name, col_width in zip(col_names, col_widths):
                pdf.cell(col_width, 10, txt=col_name, border=1, align='C')
            pdf.ln()
            
            # Add billing details
            for item in self.bill:
                for value, col_width in zip(item, col_widths):
                    pdf.cell(col_width, 10, txt=str(value), border=1, align='C')
                pdf.ln()
            
            # Save PDF with receipt_patientID name
            pdf_file_name = f"receipt_{self.patient_id}.pdf"
            pdf.output(pdf_file_name)

            # Insert billing history into database
            for item in self.bill:
                medication_id, medication_name, price, quantity, single_price, gst, total_price = item
                billing_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current date and time
                self.cursor_billing_history.execute("INSERT INTO BillingHistory (MedicationName, Quantity, Price, TotalPrice, BillingDate) VALUES (?, ?, ?, ?, ?)",
                                                    (medication_name, quantity, price, total_price, billing_date))

                # Update the inventory database
                self.cursor_inventory.execute("UPDATE Medications SET Quantity = Quantity - ? WHERE MedicationID = ?", (quantity, medication_id))
                
            self.conn_billing_history.commit()
            self.conn_inventory.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        except ValueError as ve:
            messagebox.showerror("Value Error", str(ve))
        else:
            messagebox.showinfo("Receipt Printed", "Receipt printed successfully")

        # Clear the bill and reset total price
        self.bill = []
        self.total_price = 0
        self.total_price_var.set(0.0)
        self.treeview.delete(*self.treeview.get_children())

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalApp(root)
    root.mainloop()
