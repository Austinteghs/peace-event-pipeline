"""
GCP Pub/Sub utilities
Handles error notifications via Google Cloud Pub/Sub
"""

import os
import json
from google.cloud import pubsub_v1
from .logger import logger
from .constants import ENV_PROD, PUBSUB_TOPIC_DEVELOPERS, PUBSUB_TOPIC_BUSINESS


def publish_error_to_pubsub(error_message, topic_name, source_name):
    """
    Publish error message to Pub/Sub topic
    
    Args:
        error_message: Error message to publish
        topic_name: Pub/Sub topic name
        source_name: Name of the scraper source
    """
    if not ENV_PROD:
        logger.info(f"[DEV MODE] Would publish to {topic_name}: {error_message[:100]}")
        return
    
    try:
        project_id = os.environ.get("GCP_PROJECT_ID")
        if not project_id:
            logger.error("GCP_PROJECT_ID not set, cannot publish to Pub/Sub")
            return
        
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic_name)
        
        message_data = {
            "source": source_name,
            "error": error_message,
            "timestamp": str(pd.Timestamp.now())
        }
        
        message_json = json.dumps(message_data)
        future = publisher.publish(topic_path, message_json.encode('utf-8'))
        
        message_id = future.result()
        logger.info(f"Published error to {topic_name}, message ID: {message_id}")
        
    except Exception as e:
        logger.error(f"Error publishing to Pub/Sub: {e}")