"""
Plateau Peace Building Agency Scraper - GCP Version
"""

import datetime
import os
import sys
import time
import traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    ENV_PROD, logger, upload_to_gcs, publish_error_to_pubsub,
    PUBSUB_TOPIC_DEVELOPERS, save_csv_local, load_config,
    PUBSUB_TOPIC_BUSINESS, date_list_log_message, create_hash,
    initialize_no_driver
)

source_name = "plateaupeacebuilding_org"
event_list = []
BASE_URL = "https://www.plateaupeacebuilding.org"


def extract_date_from_text(date_text):
    try:
        for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%Y"]:
            try:
                return datetime.datetime.strptime(date_text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def classify_event_type(title, description):
    text = f"{title} {description}".lower()
    if any(w in text for w in ['dialogue', 'discussion', 'forum']):
        return "Peace Dialogues", "Community Dialogue"
    elif any(w in text for w in ['training', 'workshop', 'capacity']):
        return "Training and Capacity Building", "Peace Training"
    elif any(w in text for w in ['mediation', 'reconciliation']):
        return "Conflict Mediation", "Community Mediation"
    elif any(w in text for w in ['program', 'initiative', 'project']):
        return "Peace Programmes", "Peace Initiative"
    return "Peace Actions", "General Peace Action"


def scrape_plateau_peace(date_list, config):
    logger.info("Scraping Plateau Peace Building Agency")
    
    crawling_config = config.get('crawling', {})
    max_pages = crawling_config.get('max_pages', 10)
    
    try:
        pages_to_scrape = [
            f"{BASE_URL}/about.php",
            f"{BASE_URL}/programs.php",
            f"{BASE_URL}/news.php",
            f"{BASE_URL}/events.php"
        ]
        
        for page_url in pages_to_scrape:
            logger.info(f"Scraping: {page_url}")
            
            html = initialize_no_driver(page_url)
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            content_sections = soup.find_all(['div', 'section', 'article'])
            
            for section in content_sections:
                try:
                    headings = section.find_all(['h1', 'h2', 'h3', 'h4'])
                    
                    for heading in headings:
                        title = heading.get_text(strip=True)
                        
                        if len(title) < 10:
                            continue
                        
                        parent = heading.parent
                        paragraphs = parent.find_all('p') if parent else []
                        description = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])
                        
                        if not description:
                            description = title
                        
                        combined = f"{title} {description}".lower()
                        peace_keywords = ['peace', 'dialogue', 'mediation', 'reconciliation', 'conflict']
                        if not any(kw in combined for kw in peace_keywords):
                            continue
                        
                        date_posted = datetime.datetime.now().strftime("%Y-%m-%d")
                        event_type, event_subtype = classify_event_type(title, description)
                        event_id = create_hash("".join(map(str, (title, "Plateau", date_posted, page_url))))
                        
                        event_info = {
                            "EVENT_ID": event_id,
                            "EVENT_TITLE": title,
                            "EVENT_TYPE": event_type,
                            "EVENT_SUBTYPE": event_subtype,
                            "ORGANIZATION": "Plateau Peace Building Agency",
                            "STATE": "Plateau",
                            "LGA": "NA",
                            "LOCATION_DETAILS": "Plateau State",
                            "DATE_POSTED": date_posted,
                            "EVENT_DATE": date_posted,
                            "EVENT_URL": page_url,
                            "SOURCE_DOMAIN": "plateaupeacebuilding.org",
                            "DESCRIPTION": description[:500],
                            "OUTCOME": "NA",
                            "PRIMARY_ACTOR": "State Ministries and Agencies",
                            "ASSOCIATED_ACTOR": "Community-Based Organizations (CBOs)",
                            "ACTOR_INTERACTION": "State - Community",
                            "SOURCE_TYPE": "Government Agency",
                            "INGESTION_DATE": datetime.datetime.now().strftime("%Y-%m-%d"),
                            "VERIFICATION_STATUS": "Verified",
                            "GEOPOLITICAL_ZONE": "North Central"
                        }
                        
                        event_list.append(event_info)
                        logger.info(f"Added: {title[:60]}...")
                        
                except Exception as e:
                    logger.error(f"Error processing section: {e}")
                    continue
            
            time.sleep(2)
        
        logger.info(f"Scraping complete. Events collected: {len(event_list)}")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")


def main():
    logger.info("############ Initializing Plateau Peace Building Scraper ############")
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, "config.yml")
    
    config_parameters = load_config(config_file)
    backfill = config_parameters['other_params'][0]['backfill']
    rerun = config_parameters['other_params'][1]['rerun']
    
    hash_blob_path = os.environ.get('HASH_PATH') if ENV_PROD else None
    gcs_bucket = os.environ.get('GCS_BUCKET') if ENV_PROD else None
    
    date_list, log_message = date_list_log_message(backfill, rerun, source_name, hash_blob_path, None)
    logger.info(log_message)
    
    event_list.clear()
    scrape_plateau_peace(date_list, config_parameters)
    
    try:
        if not event_list:
            logger.info("No events found")
        elif ENV_PROD:
            upload_to_gcs(event_list, source_name, gcs_bucket, hash_blob_path)
        else:
            save_csv_local(event_list, source_name)
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        if ENV_PROD:
            publish_error_to_pubsub(str(e), PUBSUB_TOPIC_DEVELOPERS, source_name)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        if ENV_PROD:
            publish_error_to_pubsub(str(e), PUBSUB_TOPIC_BUSINESS, source_name)