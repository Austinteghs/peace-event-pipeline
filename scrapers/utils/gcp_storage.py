"""
GCP Cloud Storage utilities
Handles uploading/downloading data to/from Google Cloud Storage
"""

import os
import pandas as pd
from google.cloud import storage
from datetime import datetime
from .logger import logger
from .constants import ENV_PROD


def upload_to_gcs(data, source_name, bucket_name, hash_blob_path):
    """
    Upload scraped data to Google Cloud Storage as Parquet file
    
    Args:
        data: List of dictionaries containing scraped events
        source_name: Name of the scraper source
        bucket_name: GCS bucket name
        hash_blob_path: Path to hash file in GCS
    """
    try:
        if not data:
            logger.info("No data to upload")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Create parquet file in memory
        parquet_buffer = df.to_parquet(index=False, compression='gzip')
        
        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Create blob path with date
        today = datetime.now().strftime("%Y-%m-%d")
        blob_path = f"peace_events/{source_name}/{today}/data.parquet"
        
        # Upload parquet file
        blob = bucket.blob(blob_path)
        blob.upload_from_string(parquet_buffer, content_type='application/octet-stream')
        
        logger.info(f"Uploaded {len(data)} records to gs://{bucket_name}/{blob_path}")
        
        # Update hash file
        update_hash_file(bucket, hash_blob_path, df)
        
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        raise


def save_parquet_to_gcs(df, source_name, bucket_name):
    """
    Save DataFrame directly to GCS as compressed Parquet
    
    Args:
        df: pandas DataFrame
        source_name: Name of the scraper source
        bucket_name: GCS bucket name
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        today = datetime.now().strftime("%Y-%m-%d")
        blob_path = f"peace_events/{source_name}/{today}/data.parquet"
        
        # Convert to parquet with gzip compression
        parquet_data = df.to_parquet(index=False, compression='gzip')
        
        blob = bucket.blob(blob_path)
        blob.upload_from_string(parquet_data, content_type='application/octet-stream')
        
        logger.info(f"Saved {len(df)} records to gs://{bucket_name}/{blob_path}")
        
    except Exception as e:
        logger.error(f"Error saving parquet to GCS: {e}")
        raise


def download_from_gcs(bucket_name, blob_path):
    """
    Download file from Google Cloud Storage
    
    Args:
        bucket_name: GCS bucket name
        blob_path: Path to file in GCS
        
    Returns:
        File contents as string
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            logger.info(f"File does not exist: gs://{bucket_name}/{blob_path}")
            return None
        
        content = blob.download_as_text()
        logger.info(f"Downloaded from gs://{bucket_name}/{blob_path}")
        return content
        
    except Exception as e:
        logger.error(f"Error downloading from GCS: {e}")
        return None


def update_hash_file(bucket, hash_blob_path, df):
    """
    Update hash file in GCS with new event IDs
    
    Args:
        bucket: GCS bucket object
        hash_blob_path: Path to hash file
        df: DataFrame with EVENT_ID column
    """
    try:
        # Download existing hash file
        hash_blob = bucket.blob(hash_blob_path)
        
        existing_hashes = set()
        if hash_blob.exists():
            hash_content = hash_blob.download_as_text()
            existing_hashes = set(hash_content.strip().split('\n'))
        
        # Add new hashes
        new_hashes = set(df['EVENT_ID'].tolist())
        all_hashes = existing_hashes.union(new_hashes)
        
        # Upload updated hash file
        hash_content = '\n'.join(sorted(all_hashes))
        hash_blob.upload_from_string(hash_content, content_type='text/plain')
        
        logger.info(f"Updated hash file with {len(new_hashes)} new hashes")
        
    except Exception as e:
        logger.error(f"Error updating hash file: {e}")