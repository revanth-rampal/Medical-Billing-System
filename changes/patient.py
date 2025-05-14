import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# --- Patient Class (from previous model) ---
class Patient:
    """
    Represents a patient in the medical billing system.
    """
    next_patient_id = 1 # Class variable to keep track of the next available patient ID

    def __init__(self, first_name, last_name, date_of_birth, phone_number, email,
                 address_street, address_city, address_state, address_zip,
                 insurance_provider=None, insurance_policy_number=None):
        """
        Initializes a new Patient object.
        """
        self.patient_id = f"PAT{Patient.next_patient_id:05d}"
        Patient.next_patient_id += 1

        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.phone_number = phone_number
        self.email = email
        self.address = {
            "street": address_street,
            "city": address_city,
            "state": address_state,
            "zip": address_zip
        }
        self.insurance_info = {
            "provider": insurance_provider,
            "policy_number": insurance_policy_number
        }
        self.documents = [] # Placeholder

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        """String representation for easier display."""
        return (f"ID: {self.patient_id}, Name: {self.get_full_name()}, DOB: {self.date_of_birth}\n"
                f"Phone: {self.phone_number}, Email: {self.email}\n"
                f"Address: {self.address['street']}, {self.address['city']}, {self.address['state']} {self.address['zip']}\n"
                f"Insurance: {self.insurance_info.get('provider', 'N/A')} - {self.insurance_info.get('policy_number', 'N/A')}")

# --- Tkinter Application ---
class PatientRegistrationApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Patient Registration System")
        # self.root.geometry("700x750") # Adjust as needed
        
        # Apply a ttkbootstrap theme
        # You can try different themes like 'litera', 'cosmo', 'flatly', 'journal', 'lumen', 'minty', 'pulse', 'sandstone', 'united', 'yeti', 'superhero', 'darkly', 'cyborg'
        self.style = tb.Style(theme="superhero") # Using 'superhero' theme as an example

        self.patients_db = [] # In-memory list to store patient objects

        # Main frame
        self.main_frame = tb.Frame(self.root, padding=(20, 10))
        self.main_frame.pack(fill=BOTH, expand=YES)

        # --- Title ---
        title_label = tb.Label(self.main_frame, text="Patient Registration", font=("Helvetica", 18, "bold"), bootstyle=PRIMARY)
        title_label.pack(pady=(0, 20))

        # --- Form Sections ---
        form_frame = tb.Frame(self.main_frame)
        form_frame.pack(fill=X, padx=10)

        # Personal Information Section
        personal_info_frame = tb.Labelframe(form_frame, text="Personal Information", bootstyle=INFO, padding=15)
        personal_info_frame.pack(fill=X, pady=(0,10))

        self.create_entry_field(personal_info_frame, "First Name:", "first_name_entry", 0)
        self.create_entry_field(personal_info_frame, "Last Name:", "last_name_entry", 1)
        self.create_entry_field(personal_info_frame, "Date of Birth (YYYY-MM-DD):", "dob_entry", 2)
        self.create_entry_field(personal_info_frame, "Phone Number:", "phone_entry", 3)
        self.create_entry_field(personal_info_frame, "Email Address:", "email_entry", 4)

        # Address Information Section
        address_info_frame = tb.Labelframe(form_frame, text="Address Information", bootstyle=INFO, padding=15)
        address_info_frame.pack(fill=X, pady=(0,10))

        self.create_entry_field(address_info_frame, "Street:", "street_entry", 0)
        self.create_entry_field(address_info_frame, "City:", "city_entry", 1)
        self.create_entry_field(address_info_frame, "State:", "state_entry", 2)
        self.create_entry_field(address_info_frame, "Zip Code:", "zip_entry", 3)

        # Insurance Information Section
        insurance_info_frame = tb.Labelframe(form_frame, text="Insurance Information (Optional)", bootstyle=INFO, padding=15)
        insurance_info_frame.pack(fill=X, pady=(0,10))

        self.create_entry_field(insurance_info_frame, "Insurance Provider:", "insurance_provider_entry", 0)
        self.create_entry_field(insurance_info_frame, "Policy Number:", "insurance_policy_entry", 1)

        # --- Action Buttons ---
        button_frame = tb.Frame(self.main_frame, padding=(0, 15))
        button_frame.pack(fill=X)

        self.register_button = tb.Button(button_frame, text="Register Patient", command=self.register_patient, bootstyle=SUCCESS, width=20)
        self.register_button.pack(side=LEFT, padx=(0, 10), expand=YES, fill=X)

        self.clear_button = tb.Button(button_frame, text="Clear Fields", command=self.clear_all_fields, bootstyle=WARNING, width=20)
        self.clear_button.pack(side=LEFT, expand=YES, fill=X)

        # --- Status/Display Area (Optional - for showing registered patients) ---
        # For simplicity, we'll use message boxes for now.
        # A Treeview could be added here to list patients.
        
        # Center the window on screen
        self.root.update_idletasks() # Update "requested size" from geometry manager
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')


    def create_entry_field(self, parent_frame, label_text, entry_var_name, row_num):
        """Helper function to create a label and an entry field."""
        label = tb.Label(parent_frame, text=label_text, font=("Helvetica", 10))
        label.grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        
        entry = tb.Entry(parent_frame, font=("Helvetica", 10), bootstyle=DEFAULT)
        entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        setattr(self, entry_var_name, entry) # Store entry widget as an instance attribute

        parent_frame.columnconfigure(1, weight=1) # Make entry fields expand

    def gather_data(self):
        """Gathers data from all entry fields."""
        data = {
            "first_name": self.first_name_entry.get().strip(),
            "last_name": self.last_name_entry.get().strip(),
            "date_of_birth": self.dob_entry.get().strip(),
            "phone_number": self.phone_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "address_street": self.street_entry.get().strip(),
            "address_city": self.city_entry.get().strip(),
            "address_state": self.state_entry.get().strip(),
            "address_zip": self.zip_entry.get().strip(),
            "insurance_provider": self.insurance_provider_entry.get().strip(),
            "insurance_policy_number": self.insurance_policy_entry.get().strip(),
        }
        return data

    def validate_data(self, data):
        """Basic validation for required fields."""
        required_fields = ["first_name", "last_name", "date_of_birth", "phone_number", "email",
                           "address_street", "address_city", "address_state", "address_zip"]
        for field in required_fields:
            if not data[field]:
                messagebox.showerror("Validation Error", f"{field.replace('_', ' ').title()} is required.")
                # Focus on the problematic entry
                entry_widget = getattr(self, f"{field}_entry", None)
                if entry_widget:
                    entry_widget.focus_set()
                return False
        
        # Add more specific validations if needed (e.g., email format, phone format, DOB format)
        if "@" not in data["email"] or "." not in data["email"]: # Very basic email check
            messagebox.showerror("Validation Error", "Please enter a valid email address.")
            self.email_entry.focus_set()
            return False
            
        return True

    def register_patient(self):
        """Handles the patient registration process."""
        patient_data = self.gather_data()

        if not self.validate_data(patient_data):
            return

        try:
            new_patient = Patient(
                first_name=patient_data["first_name"],
                last_name=patient_data["last_name"],
                date_of_birth=patient_data["date_of_birth"],
                phone_number=patient_data["phone_number"],
                email=patient_data["email"],
                address_street=patient_data["address_street"],
                address_city=patient_data["address_city"],
                address_state=patient_data["address_state"],
                address_zip=patient_data["address_zip"],
                insurance_provider=patient_data["insurance_provider"] if patient_data["insurance_provider"] else None,
                insurance_policy_number=patient_data["insurance_policy_number"] if patient_data["insurance_policy_number"] else None
            )
            self.patients_db.append(new_patient)
            
            # For demonstration, print to console and show success message
            print("--- New Patient Registered ---")
            print(new_patient)
            print(f"Total patients in DB: {len(self.patients_db)}")
            print(f"Next Patient ID will be: PAT{Patient.next_patient_id:05d}")
            print("-----------------------------")

            messagebox.showinfo("Success", f"Patient {new_patient.get_full_name()} (ID: {new_patient.patient_id}) registered successfully!")
            self.clear_all_fields()
            self.first_name_entry.focus_set() # Set focus back to the first field

        except Exception as e:
            messagebox.showerror("Registration Error", f"An error occurred: {e}")
            print(f"Error during registration: {e}")

    def clear_all_fields(self):
        """Clears all entry fields in the form."""
        self.first_name_entry.delete(0, END)
        self.last_name_entry.delete(0, END)
        self.dob_entry.delete(0, END)
        self.phone_entry.delete(0, END)
        self.email_entry.delete(0, END)
        self.street_entry.delete(0, END)
        self.city_entry.delete(0, END)
        self.state_entry.delete(0, END)
        self.zip_entry.delete(0, END)
        self.insurance_provider_entry.delete(0, END)
        self.insurance_policy_entry.delete(0, END)
        self.first_name_entry.focus_set() # Set focus to the first field

if __name__ == "__main__":
    # The main Tkinter window
    # Using tb.Window for ttkbootstrap themed window
    app_root = tb.Window(themename="superhero") # or any other theme
    
    # Create an instance of the application
    app_gui = PatientRegistrationApp(app_root)
    
    # Start the Tkinter event loop
    app_root.mainloop()

