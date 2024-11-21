# Import necessary libraries
import psutil  # For monitoring system memory usage
import tkinter as tk  # For creating graphical user interface (GUI)
from tkinter import ttk  # Themed tkinter widgets for better UI
import requests  # For making HTTP requests to fetch data from APIs
import pandas as pd  # For data manipulation and analysis
import io  # For handling in-memory file objects
from geopy.geocoders import Nominatim  # For geocoding (location to coordinates)
from geopy.exc import GeocoderTimedOut  # Handle geocoding timeouts
import tkintermapview  # For embedding interactive maps into the tkinter UI
import math  # For mathematical operations (used in distance calculations)
import sys  # For system-level operations (e.g., exiting the program)
from concurrent.futures import ThreadPoolExecutor  # For running tasks asynchronously
from tkinter.filedialog import askopenfilename  # For opening file dialog to select files

# Configuration settings for the application
API_KEY = '618d86618ae931ebab8598370ac3a8f9'  # API key for accessing wildfire data
BASE_URL = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv'  # Base URL for NASA's wildfire API
DATA_SOURCE = 'VIIRS_NOAA20_NRT'  # Satellite data source
REGION = 'world'  # Default region to fetch data from
TIME_PERIOD = '10'  # Data from the last 24 hours
WINDOW_TITLE = "Wildfire Tracking Program"  # Application window title
WINDOW_WIDTH = 1200  # Width of the application window
WINDOW_HEIGHT = 800  # Height of the application window
PADDING = 10  # Padding for UI components
MEMORY_LIMIT_MB = 3072  # Maximum allowed memory usage in MB
R = 6371  # Radius of the Earth in kilometers, used in distance calculations

def check_memory_limit():
    """
    Check if the application's memory usage exceeds the predefined limit and terminate if it does.
    """
    process = psutil.Process()  # Get the current process information
    memory_usage = process.memory_info().rss / (1024 * 1024)  # Convert memory usage to MB
    if memory_usage > MEMORY_LIMIT_MB:
        print(f"Memory limit exceeded: {memory_usage:.2f} MB. Terminating the application.")
        sys.exit(1)  # Exit the program if memory usage is too high

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points (latitude, longitude) on the Earth's surface using the Haversine formula.
    Args:
        lat1, lon1: Coordinates of the first point
        lat2, lon2: Coordinates of the second point
    Returns:
        Distance in kilometers
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1  # Difference in latitude
    dlon = lon2 - lon1  # Difference in longitude
    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Distance in kilometers

class WildfireTracker:
    """
    Main class for the Wildfire Tracking application. Handles UI, data fetching, and data display.
    """
    def __init__(self, root):
        """
        Initialize the application UI and variables.
        Args:
            root: The main Tkinter window
        """
        self.root = root
        self.root.title(WINDOW_TITLE)  # Set window title
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")  # Set window dimensions
        self.geolocator = Nominatim(user_agent="wildfire_tracker")  # Initialize geolocator for location queries
        self.user_location = (0, 0)  # Default user location
        self.radius_km = 100  # Default radius for wildfire detection (in kilometers)
        self.filename = None  # Store filename for CSV data
        self.loaded_data = None  # Store loaded CSV data
        self.memory_check_id = None  # ID for memory check scheduling
        self.executor = ThreadPoolExecutor(max_workers=4)  # Thread pool for background tasks
        self.setup_ui()  # Setup the user interface
        self.detect_current_location()  # Detect user's location using their IP address

    def setup_ui(self):
        """
        Set up the user interface components, including buttons, labels, and map view.
        """
        self.create_menu()  # Add a menu bar to the application

        # Create the main frame for layout
        main_frame = ttk.Frame(self.root, padding=PADDING)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Add a title label
        ttk.Label(main_frame, text="Global Wildfire Tracking System", font=('Helvetica', 16, 'bold')).pack(pady=PADDING)

        # Location input frame
        location_frame = ttk.Frame(main_frame)
        location_frame.pack(pady=PADDING)
        ttk.Label(location_frame, text="Enter City and Country (e.g., 'Paris, France'):").pack(side=tk.LEFT, padx=5)
        self.location_entry = ttk.Entry(location_frame, width=30)  # Input box for location
        self.location_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(location_frame, text="Set Location", command=self.set_location).pack(side=tk.LEFT, padx=5)

        # Buttons for fetching data and loading CSV files
        ttk.Button(main_frame, text="Fetch Latest Wildfire Data", command=self.fetch_data).pack(pady=PADDING)
        ttk.Button(main_frame, text="Load CSV Data", command=self.load_csv_data).pack(pady=PADDING)
        ttk.Button(main_frame, text="Start Reading CSV Data", command=self.start_reading_csv_data).pack(pady=PADDING)

        # Status label for showing application messages
        self.status_label = ttk.Label(main_frame, text="Detecting your current location...", font=('Helvetica', 10))
        self.status_label.pack(pady=PADDING)

        # Map and text box for displaying data
        map_frame = ttk.Frame(main_frame)
        map_frame.pack(fill=tk.BOTH, expand=True)
        self.map_widget = tkintermapview.TkinterMapView(map_frame, width=800, height=600)  # Interactive map
        self.map_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_box = tk.Text(map_frame, height=30, width=40)  # Text box for displaying wildfire data
        self.text_box.pack(side=tk.RIGHT, fill=tk.Y, padx=PADDING)

    def create_menu(self):
        """
        Create the Options menu for the application.
        """
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        options_menu = tk.Menu(menu_bar, tearoff=0)  # Add dropdown options menu
        options_menu.add_command(label="Set Tracking Radius", command=self.set_radius)  # Add radius setting option
        menu_bar.add_cascade(label="Options", menu=options_menu)
    def set_radius(self):
        """
        Allow the user to set a new radius for wildfire detection.
        Opens a dialog box to enter the new radius.
        """
        # Create a new window for setting radius
        radius_window = tk.Toplevel(self.root)
        radius_window.title("Set Tracking Radius")
        ttk.Label(radius_window, text="Enter new radius in kilometers:").pack(pady=PADDING)

        # Input box for radius
        radius_entry = ttk.Entry(radius_window, width=20)
        radius_entry.pack(pady=PADDING)

        def update_radius():
            """
            Validate and update the tracking radius based on user input.
            """
            try:
                new_radius = int(radius_entry.get())  # Convert input to integer
                if new_radius <= 0:
                    raise ValueError("Radius must be a positive integer.")
                self.radius_km = new_radius  # Update the radius
                self.status_label.config(text=f"Tracking radius updated to {self.radius_km} km.")
                radius_window.destroy()  # Close the dialog box
            except ValueError as e:
                # Show error if input is invalid
                self.status_label.config(text=f"Invalid input: {e}")

        # Button to set the radius
        ttk.Button(radius_window, text="Set Radius", command=update_radius).pack(pady=PADDING)

    def detect_current_location(self):
        """
        Detect the user's current location using their IP address.
        Updates the map and displays the detected location.
        """
        try:
            # Fetch location data from an IP-based geolocation API
            response = requests.get("https://ipapi.co/json/", timeout=10)
            response.raise_for_status()
            location_data = response.json()  # Parse the response as JSON
            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")

            if latitude and longitude:
                # Update user location and map
                self.user_location = (latitude, longitude)
                self.map_widget.set_position(latitude, longitude)
                self.map_widget.set_zoom(10)  # Set zoom level on the map
                self.status_label.config(
                    text=f"Location detected: {location_data.get('city')}, {location_data.get('country_name')}"
                )
            else:
                # Handle case where location is unavailable
                self.status_label.config(text="Unable to detect current location.")
        except Exception as e:
            # Handle errors in location detection
            self.status_label.config(text=f"Error detecting location: {e}")

    def set_location(self):
        """
        Set the user's location manually based on their input.
        Geocodes the input to get coordinates and updates the map.
        """
        location_input = self.location_entry.get().strip()  # Get input from the user
        if not location_input:
            self.status_label.config(text="Please enter a city and country.")
            return
        try:
            # Geocode the input to get latitude and longitude
            location = self.geolocator.geocode(location_input, timeout=10)
            if location:
                # Update user location and map
                self.user_location = (location.latitude, location.longitude)
                self.map_widget.set_position(location.latitude, location.longitude)
                self.map_widget.set_zoom(10)  # Set zoom level
                self.status_label.config(text=f"Location set to: {location_input}")
            else:
                # Handle case where geocoding fails
                self.status_label.config(text="Location not found. Try 'City, Country'.")
        except GeocoderTimedOut:
            # Handle timeout errors
            self.status_label.config(text="Geocoding service timed out. Try again.")
        except Exception as e:
            # Handle other geocoding errors
            self.status_label.config(text=f"Error setting location: {e}")

    def fetch_data(self):
        """
        Fetch the latest wildfire data from the NASA API.
        Runs the task in a separate thread to avoid blocking the UI.
        """
        self.status_label.config(text="Fetching data...")
        self.executor.submit(self.fetch_data_task)  # Run fetch_data_task asynchronously

    def fetch_data_task(self):
        """
        Task to fetch wildfire data from the NASA API.
        Filters the data and displays it on the map and text box.
        """
        try:
            # Build the URL for the API request
            url = f'{BASE_URL}/{API_KEY}/{DATA_SOURCE}/{REGION}/{TIME_PERIOD}?region=1'
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Parse the CSV response into a pandas DataFrame
            data = pd.read_csv(io.StringIO(response.text))

            # Filter wildfires within the user-defined radius
            filtered_data = self.filter_wildfires_within_radius(data)

            # Update the UI to display the results
            self.root.after(0, lambda: self.display_data(filtered_data))
            self.root.after(0, lambda: self.show_results(filtered_data))
        except Exception as e:
            # Handle errors during data fetching
            self.root.after(0, lambda: self.show_error(f"Error fetching data: {e}"))

    def show_results(self, data):
        """
        Display the wildfire data results in the text box.
        Args:
            data: Filtered wildfire data as a pandas DataFrame
        """
        self.text_box.delete(1.0, tk.END)  # Clear previous text
        if data.empty:
            self.text_box.insert(tk.END, "No wildfires found within the specified radius.")
        else:
            # Display each wildfire record
            for _, row in data.iterrows():
                self.text_box.insert(tk.END, f"Location: ({row['latitude']}, {row['longitude']}), "
                                             f"Date: {row['acq_date']}\n")

    def display_data(self, data):
        """
        Display wildfire locations on the map.
        Args:
            data: Filtered wildfire data as a pandas DataFrame
        """
        self.map_widget.delete_all_marker()  # Clear existing markers on the map
        if data.empty:
            self.status_label.config(text="No wildfires found within the specified radius.")
        else:
            # Add markers for each wildfire location
            for _, row in data.iterrows():
                self.map_widget.set_marker(
                    row['latitude'], row['longitude'],
                    text=f"Fire detected!\nDate: {row['acq_date']}",
                    marker_color_circle="red", marker_color_outside="red"
                )
            self.status_label.config(text="Wildfire data displayed on the map.")

    def load_csv_data(self):
        """
        Load a CSV file containing wildfire data.
        Allows the user to manually load data instead of fetching from the API.
        """
        self.filename = askopenfilename(filetypes=[("CSV files", "*.csv")])  # Open file dialog
        if self.filename:
            self.status_label.config(text=f"Loaded file: {self.filename}")
            self.loaded_data = pd.read_csv(self.filename)  # Load the CSV data into a pandas DataFrame

    def start_reading_csv_data(self):
        """
        Start processing the loaded CSV data.
        Filters and displays the data if a file has been loaded.
        """
        if self.loaded_data is not None:
            filtered_data = self.filter_wildfires_within_radius(self.loaded_data)  # Filter the data
            self.show_results(filtered_data)  # Show results in the text box
            self.display_data(filtered_data)  # Display data on the map
        else:
            self.status_label.config(text="No CSV data loaded.")

    def filter_wildfires_within_radius(self, data):
        """
        Filter the wildfire data to include only locations within the specified radius.
        Args:
            data: Wildfire data as a pandas DataFrame
        Returns:
            Filtered DataFrame with wildfires within the radius
        """
        if self.user_location == (0, 0):  # Check if user location is set
            self.status_label.config(text="User location not set.")
            return pd.DataFrame()

        # Iterate over data rows and calculate distances
        filtered_data = []
        for _, row in data.iterrows():
            distance = haversine(self.user_location[0], self.user_location[1],
                                 row['latitude'], row['longitude'])
            if distance <= self.radius_km:  # Check if distance is within the radius
                filtered_data.append(row)

        return pd.DataFrame(filtered_data)  # Return the filtered data

    def show_error(self, message):
        """
        Display an error message on the status label.
        Args:
            message: Error message string
        """
        self.status_label.config(text=message)


# Entry point for the application
if __name__ == "__main__":
    root = tk.Tk()  # Create the main application window
    app = WildfireTracker(root)  # Initialize the WildfireTracker application
    root.mainloop()  # Run the Tkinter event loop
