"""
Data processing utilities
Handles data transformation, validation, and file operations
"""

import hashlib
import os
import re
import yaml
import pandas as pd
from datetime import datetime, timedelta
from .logger import logger
from .constants import PILOT_STATES, NIGERIAN_STATES, GEOPOLITICAL_ZONES, ENV_PROD
from .gcp_storage import download_from_gcs


def create_hash(text):
    """Create SHA256 hash from text"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def extract_state_from_text(text):
    """
    Extract Nigerian state name from text
    
    Args:
        text: Text to search for state names
        
    Returns:
        State name or "NA" if not found
    """
    text_lower = text.lower()
    
    # Check pilot states first (higher priority)
    for state in PILOT_STATES:
        if state.lower() in text_lower:
            return state
    
    # Check all Nigerian states
    for state in NIGERIAN_STATES:
        if state.lower() in text_lower:
            return state
    
    return "NA"


def is_pilot_state(state):
    """Check if state is a pilot state"""
    return state in PILOT_STATES


def get_geopolitical_zone(state):
    """Get geopolitical zone for a state"""
    for zone, states in GEOPOLITICAL_ZONES.items():
        if state in states:
            return zone
    return "NA"


def load_config(config_file):
    """
    Load scraper configuration from YAML file
    
    Args:
        config_file: Path to config.yml file
        
    Returns:
        Dictionary with configuration parameters
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config['parameters']
    except Exception as e:
        logger.error(f"Error loading config file {config_file}: {e}")
        return {}


def save_csv_local(data, source_name):
    """
    Save scraped data to local CSV file
    
    Args:
        data: List of dictionaries containing scraped events
        source_name: Name of the scraper source
    """
    try:
        if not data:
            logger.info("No data to save")
            return
        
        df = pd.DataFrame(data)
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Save to CSV with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_peace_events_{timestamp}.csv"
        filepath = os.path.join(data_dir, filename)
        
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(data)} records to {filepath}")
        
    except Exception as e:
        logger.error(f"Error saving CSV locally: {e}")
        raise


def date_list_log_message(backfill, rerun, source_name, hash_blob_path, driver):
    """
    Generate date list and log message based on backfill/rerun parameters
    
    Args:
        backfill: Backfill date parameter (yyyy-mm-dd, list, or range)
        rerun: Rerun date parameter
        source_name: Name of the scraper source
        hash_blob_path: Path to hash file in GCS
        driver: Browser driver (not used, kept for compatibility)
        
    Returns:
        Tuple of (date_list, log_message)
    """
    date_list = []
    log_message = ""
    
    # Handle backfill parameter
    if backfill and backfill != 'yyyy-mm-dd':
        if isinstance(backfill, list):
            date_list = backfill
            log_message = f"Backfilling for dates: {', '.join(backfill)}"
        elif ':' in backfill:
            # Date range: 2024-01-01:2024-01-31
            start_date, end_date = backfill.split(':')
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            date_list = [(start + timedelta(days=x)).strftime('%Y-%m-%d') 
                        for x in range((end - start).days + 1)]
            log_message = f"Backfilling from {start_date} to {end_date}"
        else:
            # Single date
            date_list = [backfill]
            log_message = f"Backfilling for date: {backfill}"
    
    # Handle rerun parameter
    elif rerun and rerun != 'yyyy-mm-dd':
        if isinstance(rerun, list):
            date_list = rerun
            log_message = f"Rerunning for dates: {', '.join(rerun)}"
        elif ':' in rerun:
            start_date, end_date = rerun.split(':')
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            date_list = [(start + timedelta(days=x)).strftime('%Y-%m-%d') 
                        for x in range((end - start).days + 1)]
            log_message = f"Rerunning from {start_date} to {end_date}"
        else:
            date_list = [rerun]
            log_message = f"Rerunning for date: {rerun}"
    
    # Default: scrape for today
    else:
        log_message = "Scraping for today"
    
    return date_list, log_message