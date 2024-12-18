# Import necessary libraries
import psutil  # For checking memory usage
import tkinter as tk  # GUI framework
from tkinter import ttk  # Extended GUI components
import requests  # For HTTP requests
import pandas as pd  # Data manipulation and analysis
import io  # Handling streams
from geopy.geocoders import Nominatim  # Geocoding library
from geopy.exc import GeocoderTimedOut  # Handle geocoding timeouts
import tkintermapview  # Map visualization in Tkinter
import math  # For mathematical calculations (e.g., Haversine formula)
import sys  # System-level operations
from concurrent.futures import ThreadPoolExecutor  # Manage background tasks
from tkinter import Tk
from tkinter.filedialog import askopenfilename  # File dialog for opening files

# Configuration settings for API and application behavior
API_KEY = '618d86618ae931ebab8598370ac3a8f9'  # API key for NASA FIRMS
BASE_URL = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv'  # API base URL
DATA_SOURCE = 'VIIRS_NOAA20_NRT'  # Satellite data source
REGION = 'world'  # Data region
TIME_PERIOD = '10'  # Data time range (10 = last 24 hours)

# UI-related constants
WINDOW_TITLE = "Wildfire Tracking Program"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
PADDING = 10
RADIUS_KM = 100  # Detection radius in kilometers
MEMORY_LIMIT_MB = 3072  # Maximum memory usage limit in MB

# Constants for Haversine formula (Earth radius in kilometers)
R = 6371

def check_memory_limit():
    """
    Check if the memory usage exceeds the limit and terminate the application if necessary.
    """
    process = psutil.Process()
    memory_usage = process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
    if memory_usage > MEMORY_LIMIT_MB:
        print(f"Memory limit exceeded: {memory_usage:.2f} MB. Terminating the application.")
        sys.exit(1)

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points (lat1, lon1) and (lat2, lon2) using the Haversine formula.
    Args:
        lat1, lon1: Latitude and longitude of the first point
        lat2, lon2: Latitude and longitude of the second point
    Returns:
        Distance in kilometers
    """
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # Calculate distance
    distance = R * c
    return distance

class WildfireTracker:
    """
    Main application class for the Wildfire Tracking Program.
    """
    def __init__(self, root):
        """
        Initialize the application and set up the user interface.
        Args:
            root: The root Tkinter window
        """
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Initialize variables
        self.geolocator = Nominatim(user_agent="wildfire_tracker")  # Geolocator instance
        self.user_location = (0, 0)  # Default user location
        self.filename = None  # Store the file name for CSV
        self.loaded_data = None  # DataFrame for loaded data
        self.memory_check_id = None  # ID for memory check loop

        self.setup_ui()  # Set up the UI
        self.executor = ThreadPoolExecutor(max_workers=4)  # ThreadPool for background tasks

        # Detect user's location at startup
        self.detect_current_location()

    def setup_ui(self):
        """
        Set up the user interface components.
        """
        main_frame = ttk.Frame(self.root, padding=PADDING)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header label
        header = ttk.Label(main_frame, text="Global Wildfire Tracking System", font=('Helvetica', 16, 'bold'))
        header.pack(pady=PADDING)

        # Input section for manual location entry
        location_frame = ttk.Frame(main_frame)
        location_frame.pack(pady=PADDING)

        location_label = ttk.Label(location_frame, text="Enter City and Country (e.g., 'Paris, France'):")
        location_label.pack(side=tk.LEFT, padx=5)

        self.location_entry = ttk.Entry(location_frame, width=30)
        self.location_entry.pack(side=tk.LEFT, padx=5)

        set_location_button = ttk.Button(location_frame, text="Set Location", command=self.set_location)
        set_location_button.pack(side=tk.LEFT, padx=5)

        # Fetch wildfire data button
        self.fetch_button = ttk.Button(main_frame, text="Fetch Latest Wildfire Data", command=self.fetch_data)
        self.fetch_button.pack(pady=PADDING)

        # Load CSV data button
        self.load_csv_button = ttk.Button(main_frame, text="Load CSV Data", command=self.load_csv_data)
        self.load_csv_button.pack(pady=PADDING)

        # Start reading CSV data button
        self.start_reading_csv_button = ttk.Button(main_frame, text="Start Reading CSV Data", command=self.start_reading_csv_data)
        self.start_reading_csv_button.pack(pady=PADDING)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Detecting your current location...", font=('Helvetica', 10))
        self.status_label.pack(pady=PADDING)

        # Map and text box frame
        map_frame = ttk.Frame(main_frame)
        map_frame.pack(fill=tk.BOTH, expand=True)

        self.map_widget = tkintermapview.TkinterMapView(map_frame, width=800, height=600)
        self.map_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_box = tk.Text(map_frame, height=30, width=40)
        self.text_box.pack(side=tk.RIGHT, fill=tk.Y, padx=PADDING)

    def detect_current_location(self):
        """
        Detect the user's location using their IP address and update the map.
        """
        try:
            # Get location from IP
            response = requests.get("https://ipapi.co/json/", timeout=10)
            response.raise_for_status()
            location_data = response.json()

            # Extract latitude and longitude
            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")
            city = location_data.get("city")
            country = location_data.get("country_name")

            # Update map and status label
            if latitude and longitude:
                self.user_location = (latitude, longitude)
                self.map_widget.set_position(latitude, longitude)
                self.map_widget.set_zoom(10)
                self.status_label.config(text=f"Location detected: {city}, {country}")
            else:
                self.status_label.config(text="Unable to detect current location.")
        except Exception as e:
            self.status_label.config(text=f"Error detecting location: {e}")

    def set_location(self):
        """
        Set the user's location based on manual input (city and country).
        """
        location_input = self.location_entry.get().strip()
        if not location_input:
            self.status_label.config(text="Please enter a city and country.")
            return

        try:
            # Geocode the input
            location = self.geolocator.geocode(location_input, timeout=10)
            if location:
                self.user_location = (location.latitude, location.longitude)
                self.map_widget.set_position(location.latitude, location.longitude)
                self.map_widget.set_zoom(10)
                self.status_label.config(text=f"Location set to: {location_input}")
            else:
                self.status_label.config(text="Location not found. Please try 'City, Country'.")
        except GeocoderTimedOut:
            self.status_label.config(text="Geocoding service timed out. Try again.")
        except Exception as e:
            self.status_label.config(text=f"Error setting location: {e}")

    def fetch_data(self):
        """
        Fetch wildfire data from the API in a separate thread.
        """
        self.status_label.config(text="Fetching data...")
        self.fetch_button.state(['disabled'])  # Disable the button during fetch
        self.executor.submit(self.fetch_data_task)
    def fetch_data_task(self):
        """
        Task to fetch wildfire data from the API in a separate thread.
        This method processes the data and updates the UI.
        """
        try:
            # Construct the API URL
            url = f'{BASE_URL}/{API_KEY}/{DATA_SOURCE}/{REGION}/{TIME_PERIOD}?region=1'
            # Fetch the data
            data = self.fetch_single_data_task(url)
            # Filter wildfires within the specified radius
            filtered_data = self.filter_wildfires_within_radius(data)

            # Update the map and display results on the UI
            self.root.after(0, lambda: self.map_widget.set_position(*self.user_location))
            self.root.after(0, lambda: self.display_data(filtered_data))
            self.root.after(0, lambda: self.show_results(filtered_data))
            self.root.after(0, lambda: self.status_label.config(text="Done Fetching Data"))
        except Exception as e:
            # Handle unexpected errors
            self.root.after(0, lambda: self.show_error(f"Unexpected error: {str(e)}"))
        finally:
            # Re-enable the fetch button
            self.root.after(0, lambda: self.fetch_button.state(['!disabled']))

    def fetch_single_data_task(self, url):
        """
        Fetch data for a single region and return it as a DataFrame with retry logic.
        Args:
            url: The API URL for the data
        Returns:
            A Pandas DataFrame with the fetched data
        """
        for attempt in range(3):  # Retry up to 3 times
            try:
                # Make a GET request to the API
                response = requests.get(url, timeout=10)
                response.raise_for_status()  # Raise exception for HTTP errors
                # Parse the CSV response into a DataFrame
                return pd.read_csv(io.StringIO(response.text))
            except requests.exceptions.Timeout:
                if attempt < 2:  # Retry if it's not the last attempt
                    print("Timeout occurred, retrying...")
                else:
                    raise  # Raise the error on the final attempt
            except Exception as e:
                print(f"Error fetching data: {str(e)}")
                break  # Exit the loop on other exceptions

    def show_results(self, data):
        """
        Display wildfire results in the text box.
        Args:
            data: A DataFrame containing wildfire data
        """
        self.text_box.delete(1.0, tk.END)  # Clear the text box
        if data.empty:
            self.text_box.insert(tk.END, "No wildfires found within the specified radius.")
        else:
            # Insert each wildfire's details into the text box
            for index, row in data.iterrows():
                self.text_box.insert(tk.END, f"Location: {row['location']}, Date: {row['acq_date']}\n")

    def filter_wildfires_within_radius(self, data):
        """
        Filter wildfire data to include only those within the specified radius from the user's location.
        Args:
            data: A DataFrame containing wildfire data
        Returns:
            A filtered DataFrame
        """
        # Use the Haversine formula to calculate distance for each row
        filtered_data = data[data.apply(
            lambda row: haversine(self.user_location[0], self.user_location[1], row['latitude'], row['longitude']) <= RADIUS_KM,
            axis=1
        )]
        return filtered_data

    def display_data(self, data):
        """
        Display wildfire locations as markers on the map.
        Args:
            data: A DataFrame containing wildfire data
        """
        for index, row in data.iterrows():
            # Add a marker for each wildfire location
            self.map_widget.set_marker(row['latitude'], row['longitude'], text=row['location'])

    def show_error(self, message):
        """
        Display an error message in the status label.
        Args:
            message: The error message to display
        """
        self.status_label.config(text=message)

    def load_csv_data(self):
        """
        Open a file dialog to select a CSV file and load the data in a separate thread.
        """
        Tk().withdraw()  # Hide the root window
        self.filename = askopenfilename(filetypes=[("CSV files", "*.csv")])  # Open file dialog
        
        if not self.filename:
            self.status_label.config(text="No file selected. Exiting.")
            return

        # Submit the CSV loading task to the executor
        self.executor.submit(self.load_csv_data_task, self.filename)

    def load_csv_data_task(self, filename):
        """
        Task to load CSV data and update the UI with it.
        Args:
            filename: The path to the CSV file
        """
        try:
            # Read the CSV file into a DataFrame
            self.loaded_data = pd.read_csv(filename)
            print("Loaded DataFrame columns:", self.loaded_data.columns)  # Debugging line

            # Check if the required columns exist in the DataFrame
            if 'latitude' in self.loaded_data.columns and 'longitude' in self.loaded_data.columns and 'acq_date' in self.loaded_data.columns:
                self.loaded_data['formatted_coordinates'] = self.loaded_data.apply(
                    lambda row: f"({row['latitude']}, {row['longitude']}) - Date: {row['acq_date']}",
                    axis=1
                )
                self.root.after(0, lambda: self.update_text_box(self.loaded_data['formatted_coordinates']))
            else:
                self.root.after(0, lambda: self.status_label.config(text="CSV file must contain 'latitude', 'longitude', and 'acq_date' columns."))
        except Exception as e:
            # Handle errors during file loading
            self.root.after(0, lambda: self.status_label.config(text=f"Error loading CSV file: {str(e)}"))

    def start_reading_csv_data(self):
        """
        Start displaying the loaded CSV data in the text box.
        """
        if self.loaded_data is not None:
            self.update_text_box(self.loaded_data['formatted_coordinates'])
        else:
            self.status_label.config(text="No CSV file loaded. Please load a file first.")

    def update_text_box(self, formatted_coordinates):
        """
        Update the text box with formatted coordinates from the CSV data.
        Args:
            formatted_coordinates: A Series of formatted strings
        """
        self.text_box.delete(1.0, tk.END)  # Clear the text box
        for coord in formatted_coordinates:
            self.text_box.insert(tk.END, f"{coord}\n")

    def get_location(self, lat, lon):
        """
        Get the location (city and country) for given coordinates.
        Args:
            lat: Latitude
            lon: Longitude
        Returns:
            A string representing the location or an error message
        """
        try:
            location = self.geolocator.reverse((lat, lon), exactly_one=True, timeout=10)  # Reverse geocoding
            return location.address if location else "Unknown location"
        except GeocoderTimedOut:
            return "Geocoding service timed out."
        except Exception as e:
            return f"Error retrieving location: {str(e)}"

    def check_memory(self):
        """
        Periodically check memory usage and terminate if it exceeds the limit.
        """
        if self.root.winfo_exists():  # Ensure the window still exists
            check_memory_limit()
            self.memory_check_id = self.root.after(1000, self.check_memory)  # Schedule the next check after 1 second

    def cancel_memory_check(self):
        """
        Cancel the periodic memory check.
        """
        if self.memory_check_id:
            self.root.after_cancel(self.memory_check_id)

def main():
    """
    Initialize and run the Wildfire Tracking application.
    """
    root = tk.Tk()
    app = WildfireTracker(root)

    # Start periodic memory checks
    app.check_memory()

    # Ensure memory checks are canceled when the application closes
    root.protocol("WM_DELETE_WINDOW", lambda: [app.cancel_memory_check(), root.destroy()])

    # Start the Tkinter main event loop
    root.mainloop()

# Runs the application
if __name__ == "__main__":
    main()