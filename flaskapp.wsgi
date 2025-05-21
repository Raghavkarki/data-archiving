import sys
import logging
import os

# Add your project directory to the sys.path
sys.path.insert(0, "/home/raghav/flaskdataarchiving")

# Set environment variable for Flask
os.environ['FLASK_ENV'] = 'production'

from app import app as application

logging.basicConfig(stream=sys.stderr)
