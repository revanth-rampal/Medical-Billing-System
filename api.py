# api.py

# Base URL for the UPCitemDB trial API lookup endpoint
UPCITEMDB_TRIAL_BASE_URL = "https://api.upcitemdb.com/prod/trial/lookup"

# For UPCitemDB:
# The specific trial API URL (UPCITEMDB_TRIAL_BASE_URL + "?upc=YOUR_UPC")
# generally does NOT require an API key to be explicitly sent with the request for basic lookups.
# This UPCITEMDB_API_KEY variable is a placeholder for if you switch to a paid UPCitemDB plan
# or use different endpoints from them that DO require an API key.
# If your chosen plan/endpoint requires a key, replace "YOUR_UPCITEMDB_API_KEY_GOES_HERE_IF_NEEDED" with it.
UPCITEMDB_API_KEY = "YOUR_UPCITEMDB_API_KEY_GOES_HERE_IF_NEEDED"


# Example for other API keys you might add in the future:
# OPENFDA_API_KEY = "YOUR_OPENFDA_API_KEY"
# GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"

