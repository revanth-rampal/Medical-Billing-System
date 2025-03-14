import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
import sqlite3

def register_user():
    # Create a new window for user registration
    register_window = tk.Toplevel(root)
    register_window.title("Register New Patient")

    # Labels and entry fields for registration
    patient_id_label = tk.Label(register_window, text="Patient ID:")
    patient_id_label.grid(row=0, column=0, padx=5, pady=5)
    patient_id_entry = tk.Entry(register_window)
    patient_id_entry.grid(row=0, column=1, padx=5, pady=5)

    first_name_label = tk.Label(register_window, text="First Name:")
    first_name_label.grid(row=1, column=0, padx=5, pady=5)
    first_name_entry = tk.Entry(register_window)
    first_name_entry.grid(row=1, column=1, padx=5, pady=5)

    last_name_label = tk.Label(register_window, text="Last Name:")
    last_name_label.grid(row=2, column=0, padx=5, pady=5)
    last_name_entry = tk.Entry(register_window)
    last_name_entry.grid(row=2, column=1, padx=5, pady=5)

    dob_label = tk.Label(register_window, text="Date of Birth:")
    dob_label.grid(row=3, column=0, padx=5, pady=5)
    dob_cal = DateEntry(register_window, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
    dob_cal.grid(row=3, column=1, padx=5, pady=5)

    gender_label = tk.Label(register_window, text="Gender:")
    gender_label.grid(row=4, column=0, padx=5, pady=5)
    gender_var = tk.StringVar(register_window)
    gender_var.set("Male")  # Default value
    gender_option = tk.OptionMenu(register_window, gender_var, "Male", "Female", "Others")
    gender_option.grid(row=4, column=1, padx=5, pady=5)

    email_label = tk.Label(register_window, text="Email:")
    email_label.grid(row=5, column=0, padx=5, pady=5)
    email_entry = tk.Entry(register_window)
    email_entry.grid(row=5, column=1, padx=5, pady=5)

    phone_label = tk.Label(register_window, text="Phone:")
    phone_label.grid(row=6, column=0, padx=5, pady=5)
    phone_entry = tk.Entry(register_window)
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
        conn = sqlite3.connect('patient_details.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS Patients
                     (PatientID INTEGER PRIMARY KEY, FirstName TEXT, LastName TEXT, DateOfBirth TEXT, Gender TEXT, Email TEXT, Phone TEXT)''')
        c.execute("INSERT INTO Patients VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (int(patient_id), first_name, last_name, date_of_birth, gender, email, phone))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Patient registered successfully.")
        register_window.destroy()  # Close the registration window after successful registration

    # Save button for registration
    save_button = tk.Button(register_window, text="Save", command=save_registration)
    save_button.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="WE")

def check_patient_id():
    patient_id = patient_id_entry.get()

    # Connect to the SQLite database
    conn = sqlite3.connect("patient_details.db")
    cursor = conn.cursor()

    # Check if the patient ID exists in the database
    cursor.execute("SELECT * FROM Patients WHERE PatientID=?", (patient_id,))
    result = cursor.fetchone()

    if result:
        messagebox.showinfo("Success", f"Patient with ID {patient_id} found.")
    else:
        messagebox.showinfo("Not Found", f"Patient with ID {patient_id} not found. Please register.")
        register_user()  # Prompt user to register if patient ID not found

    conn.close()

# Create GUI
root = tk.Tk()
root.title("Patient ID Checker")

# Label and entry field for patient ID
patient_id_label = tk.Label(root, text="Enter Patient ID:")
patient_id_label.grid(row=0, column=0, padx=5, pady=5)
patient_id_entry = tk.Entry(root)
patient_id_entry.grid(row=0, column=1, padx=5, pady=5)

# Button to check patient ID
check_button = tk.Button(root, text="Check Patient ID", command=check_patient_id)
check_button.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="WE")

root.mainloop()
