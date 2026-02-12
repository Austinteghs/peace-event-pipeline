"""
NPAID Scrapers Utilities Package
Modular utilities for web scraping, GCP integration, and data processing
"""

from .gcp_storage import upload_to_gcs, download_from_gcs, save_parquet_to_gcs
from .gcp_pubsub import publish_error_to_pubsub, PUBSUB_TOPIC_DEVELOPERS, PUBSUB_TOPIC_BUSINESS
from .browser import initialize_no_driver, initialize_driver
from .data_processing import (
    create_hash, extract_state_from_text, is_pilot_state,
    save_csv_local, date_list_log_message, load_config
)
from .constants import ENV_PROD, PILOT_STATES, NIGERIAN_STATES, GEOPOLITICAL_ZONES
from .logger import logger, log_if_troubleshooting
from .parallel import run_scrapers_parallel

__all__ = [
    # GCP Storage
    'upload_to_gcs',
    'download_from_gcs',
    'save_parquet_to_gcs',
    
    # GCP Pub/Sub
    'publish_error_to_pubsub',
    'PUBSUB_TOPIC_DEVELOPERS',
    'PUBSUB_TOPIC_BUSINESS',
    
    # Browser automation
    'initialize_no_driver',
    'initialize_driver',
    
    # Data processing
    'create_hash',
    'extract_state_from_text',
    'is_pilot_state',
    'save_csv_local',
    'date_list_log_message',
    'load_config',
    
    # Constants
    'ENV_PROD',
    'PILOT_STATES',
    'NIGERIAN_STATES',
    'GEOPOLITICAL_ZONES',
    
    # Logging
    'logger',
    'log_if_troubleshooting',
    
    # Parallel processing
    'run_scrapers_parallel',
]