import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
import sqlite3
import csv

def save_data():
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

    # Check for repetitive entry
    if patient_id in patient_ids:
        messagebox.showerror("Error", f"Patient with ID {patient_id} already exists.")
        return

    # Add data to list
    patient_ids.add(patient_id)

    # Save to SQLite database
    conn = sqlite3.connect('patient_details.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Patients
                 (PatientID INTEGER PRIMARY KEY, FirstName TEXT, LastName TEXT, DateOfBirth TEXT, Gender TEXT, Email TEXT, Phone TEXT)''')
    c.execute("INSERT INTO Patients VALUES (?, ?, ?, ?, ?, ?, ?)",
              (int(patient_id), first_name, last_name, date_of_birth, gender, email, phone))
    conn.commit()
    conn.close()

    # Save to CSV file
    with open('patient_details.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([patient_id, first_name, last_name, date_of_birth, gender, email, phone])

    messagebox.showinfo("Success", "Data saved successfully.")

# Initialize set to store patient IDs
patient_ids = set()

# Create GUI
root = tk.Tk()
root.title("Patient Data Entry")

# Labels
patient_id_label = tk.Label(root, text="Patient ID:")
patient_id_label.grid(row=0, column=0, padx=5, pady=5)
first_name_label = tk.Label(root, text="First Name:")
first_name_label.grid(row=1, column=0, padx=5, pady=5)
last_name_label = tk.Label(root, text="Last Name:")
last_name_label.grid(row=2, column=0, padx=5, pady=5)
dob_label = tk.Label(root, text="Date of Birth:")
dob_label.grid(row=3, column=0, padx=5, pady=5)
gender_label = tk.Label(root, text="Gender:")
gender_label.grid(row=4, column=0, padx=5, pady=5)
email_label = tk.Label(root, text="Email:")
email_label.grid(row=5, column=0, padx=5, pady=5)
phone_label = tk.Label(root, text="Phone:")
phone_label.grid(row=6, column=0, padx=5, pady=5)

# Entry fields
patient_id_entry = tk.Entry(root)
patient_id_entry.grid(row=0, column=1, padx=5, pady=5)
first_name_entry = tk.Entry(root)
first_name_entry.grid(row=1, column=1, padx=5, pady=5)
last_name_entry = tk.Entry(root)
last_name_entry.grid(row=2, column=1, padx=5, pady=5)
dob_cal = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
dob_cal.grid(row=3, column=1, padx=5, pady=5)
gender_var = tk.StringVar(root)
gender_var.set("Male")  # Default value
gender_option = tk.OptionMenu(root, gender_var, "Male", "Female", "Others")
gender_option.grid(row=4, column=1, padx=5, pady=5)
email_entry = tk.Entry(root)
email_entry.grid(row=5, column=1, padx=5, pady=5)
phone_entry = tk.Entry(root)
phone_entry.grid(row=6, column=1, padx=5, pady=5)

# Save button
save_button = tk.Button(root, text="Save", command=save_data)
save_button.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="WE")

root.mainloop()
