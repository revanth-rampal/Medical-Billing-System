import tkinter as tk
from tkinter import messagebox
import sqlite3

def view_patient_database():
    # Create a new window for viewing patient database
    view_window = tk.Toplevel(root)
    view_window.title("Registered Patients")

    # Connect to the SQLite database
    conn = sqlite3.connect("patient_details.db")
    cursor = conn.cursor()

    # Retrieve all patient records from the database
    cursor.execute("SELECT * FROM Patients")
    patient_records = cursor.fetchall()

    # Display patient records in a text widget
    text_widget = tk.Text(view_window, height=20, width=60)
    text_widget.grid(row=0, column=0, padx=10, pady=10)

    # Insert patient records into the text widget
    for record in patient_records:
        text_widget.insert(tk.END, f"Patient ID: {record[0]}\n")
        text_widget.insert(tk.END, f"Name: {record[1]} {record[2]}\n")
        text_widget.insert(tk.END, f"Date of Birth: {record[3]}\n")
        text_widget.insert(tk.END, f"Gender: {record[4]}\n")
        text_widget.insert(tk.END, f"Email: {record[5]}\n")
        text_widget.insert(tk.END, f"Phone: {record[6]}\n\n")

    # Close the database connection
    conn.close()

# Create GUI
root = tk.Tk()
root.title("Patient Database Viewer")

# Button to view patient database
view_button = tk.Button(root, text="View Patient Database", command=view_patient_database)
view_button.pack(pady=20)

root.mainloop()
