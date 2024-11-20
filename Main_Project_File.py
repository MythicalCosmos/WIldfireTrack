import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pandas as pd

class WildfireTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Wildfire Tracker")

        # Create input fields
        self.location_label = tk.Label(root, text="Location:")
        self.location_label.pack()
        self.location_entry = tk.Entry(root)
        self.location_entry.pack()

        self.date_label = tk.Label(root, text="Date (YYYY-MM-DD):")
        self.date_label.pack()
        self.date_entry = tk.Entry(root)
        self.date_entry.pack()

        self.severity_label = tk.Label(root, text="Severity (1-10):")
        self.severity_label.pack()
        self.severity_entry = tk.Entry(root)
        self.severity_entry.pack()

        # Submit button
        self.submit_button = tk.Button(root, text="Submit", command=self.submit_data)
        self.submit_button.pack()

        # Treeview to display data
        self.tree = ttk.Treeview(root, columns=("Location", "Date", "Severity"), show='headings')
        self.tree.heading("Location", text="Location")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Severity", text="Severity")
        self.tree.pack()

        # Load existing data
        self.load_data()

    def submit_data(self):
        location = self.location_entry.get()
        date = self.date_entry.get()
        severity = self.severity_entry.get()

        if location and date and severity:
            # Save data to CSV
            new_data = pd.DataFrame([[location, date, severity]], columns=["Location", "Date", "Severity"])
            new_data.to_csv("wildfires.csv", mode='a', header=False, index=False)

            # Insert data into treeview
            self.tree.insert("", tk.END, values=(location, date, severity))

            messagebox.showinfo("Success", "Data submitted successfully!")
            self.clear_entries()
        else:
            messagebox.showwarning("Input Error", "Please fill in all fields.")

    def load_data(self):
        try:
            self.data = pd.read_csv("wildfires.csv")
            for index, row in self.data.iterrows():
                self.tree.insert("", tk.END, values=(row["Location"], row["Date"], row["Severity"]))
        except FileNotFoundError:
            self.data = pd.DataFrame(columns=["Location", "Date", "Severity"])

    def clear_entries(self):
        self.location_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.severity_entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = WildfireTracker(root)
    root.mainloop()
