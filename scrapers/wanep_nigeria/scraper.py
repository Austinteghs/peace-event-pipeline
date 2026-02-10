import datetime
import hashlib
import os
import sys
import time
import traceback
import re
from bs4 import BeautifulSoup
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scrapers.utils import (
    ENV_PROD, log_if_troubleshooting, logger, upload_csv_to_s3, publish_error_to_sns,
    SNS_ARN_DEVELOPERS, save_csv_local, load_config, initialize_puppeteer_driver,
    SNS_ARN_BUSINESS, date_list_log_message, create_hash, extract_state_from_text,
    is_pilot_state, initialize_no_driver, PILOT_STATES
)

S3_BUCKET = os.environ.get("S3BUCKET")
CONFIG_FILE = os.environ.get("CONFIG_PATH")
HASHFILE = os.environ.get("HASH_PATH")

logger.info(f"S3 bucket location ==> {S3_BUCKET}")
logger.info(f"Config file path ==> {CONFIG_FILE}")

source_name = "wanep_nigeria"
event_list = []

# WANEP Nigeria base URLs
BASE_URL = "https://wanepnigeria.org"
NEWS_URL = f"{BASE_URL}/news"
PROGRAMS_URL = f"{BASE_URL}/programs"


def extract_date_from_text(date_text):
    """Extract and format date from various text formats"""
    try:
        # Try common date formats
        for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                parsed_date = datetime.datetime.strptime(date_text.strip(), fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If no format matches, return today's date
        return datetime.datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        log_if_troubleshooting(f"Error parsing date: {e}")
        return datetime.datetime.now().strftime("%Y-%m-%d")


def classify_event_type(title, description):
    """Classify event type based on title and description"""
    text = f"{title} {description}".lower()
    
    if any(word in text for word in ['dialogue', 'discussion', 'consultation', 'forum']):
        return "Peace Dialogues", "Community Dialogue"
    elif any(word in text for word in ['training', 'workshop', 'capacity', 'seminar']):
        return "Training and Capacity Building", "Peace Training"
    elif any(word in text for word in ['mediation', 'reconciliation', 'resolution']):
        return "Conflict Mediation", "Community Mediation"
    elif any(word in text for word in ['agreement', 'accord', 'treaty']):
        return "Peace Agreements", "Peace Agreement"
    elif any(word in text for word in ['warning', 'monitoring', 'alert']):
        return "Early Warning Systems", "Early Warning"
    elif any(word in text for word in ['program', 'programme', 'initiative', 'project']):
        return "Peace Programmes", "Peace Initiative"
    else:
        return "Peace Actions", "General Peace Action"


def extract_actors(description):
    """Extract primary and associated actors from description"""
    # Common actor patterns
    cso_keywords = ['wanep', 'ngo', 'civil society', 'organization', 'network']
    govt_keywords = ['government', 'ministry', 'commission', 'state', 'federal']
    community_keywords = ['community', 'youth', 'women', 'elders', 'traditional']
    intl_keywords = ['un', 'undp', 'usaid', 'eu', 'international']
    
    description_lower = description.lower()
    
    primary_actor = "NA"
    associated_actor = "NA"
    
    if any(word in description_lower for word in cso_keywords):
        primary_actor = "Civil Society Organizations (CSOs)"
    elif any(word in description_lower for word in govt_keywords):
        primary_actor = "State Ministries and Agencies"
    elif any(word in description_lower for word in community_keywords):
        primary_actor = "Community-Based Organizations (CBOs)"
    
    if any(word in description_lower for word in intl_keywords):
        associated_actor = "Multilateral Agencies"
    elif any(word in description_lower for word in govt_keywords) and primary_actor != "State Ministries and Agencies":
        associated_actor = "State Ministries and Agencies"
    
    return primary_actor, associated_actor


def scrape_wanep_news(date_list, target_states):
    """Scrape WANEP Nigeria news and events"""
    logger.info(f"Scraping WANEP Nigeria news for states: {target_states}")
    
    try:
        # Get the news page
        html = initialize_no_driver(NEWS_URL)
        if not html:
            logger.error("Failed to retrieve WANEP news page")
            return
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all news articles (adjust selectors based on actual website structure)
        articles = soup.find_all('article') or soup.find_all('div', class_='news-item')
        
        logger.info(f"Found {len(articles)} articles on WANEP Nigeria")
        
        for article in articles:
            try:
                # Extract title
                title_elem = article.find('h2') or article.find('h3') or article.find('a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link_elem = article.find('a', href=True)
                if link_elem:
                    event_url = link_elem['href']
                    if not event_url.startswith('http'):
                        event_url = BASE_URL + event_url
                else:
                    event_url = NEWS_URL
                
                # Extract date
                date_elem = article.find('time') or article.find('span', class_='date')
                if date_elem:
                    date_posted = extract_date_from_text(date_elem.get_text(strip=True))
                else:
                    date_posted = datetime.datetime.now().strftime("%Y-%m-%d")
                
                # Check if date is in our target date list
                if date_posted not in date_list:
                    continue
                
                # Extract description
                desc_elem = article.find('p') or article.find('div', class_='excerpt')
                description = desc_elem.get_text(strip=True) if desc_elem else title
                
                # Extract state from title and description
                state = extract_state_from_text(f"{title} {description}")
                
                # Only process if it's one of our pilot states
                if state not in target_states and state != "NA":
                    continue
                
                # Classify event type
                event_type, event_subtype = classify_event_type(title, description)
                
                # Extract actors
                primary_actor, associated_actor = extract_actors(description)
                
                # Determine geopolitical zone
                zone_map = {
                    'Kaduna': 'North West',
                    'Katsina': 'North West',
                    'Benue': 'North Central',
                    'Plateau': 'North Central'
                }
                geopolitical_zone = zone_map.get(state, "NA")
                
                # Create hash for deduplication
                hash_fields = (title, state, date_posted, event_url)
                event_id = create_hash("".join(map(str, hash_fields)))
                
                # Build event info
                event_info = {
                    "EVENT_ID": event_id,
                    "EVENT_TITLE": title,
                    "EVENT_TYPE": event_type,
                    "EVENT_SUBTYPE": event_subtype,
                    "ORGANIZATION": "WANEP Nigeria",
                    "STATE": state,
                    "LGA": "NA",  # LGA extraction would require more detailed parsing
                    "LOCATION_DETAILS": state if state != "NA" else "Nigeria",
                    "DATE_POSTED": date_posted,
                    "EVENT_DATE": date_posted,  # Assume event date same as posted date
                    "EVENT_URL": event_url,
                    "SOURCE_DOMAIN": "wanepnigeria.org",
                    "DESCRIPTION": description[:500],  # Limit description length
                    "OUTCOME": "NA",  # Would need detailed article parsing
                    "PRIMARY_ACTOR": primary_actor,
                    "ASSOCIATED_ACTOR": associated_actor,
                    "ACTOR_INTERACTION": f"{primary_actor} - {associated_actor}" if associated_actor != "NA" else primary_actor,
                    "SOURCE_TYPE": "Civil Society Organization",
                    "INGESTION_DATE": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "VERIFICATION_STATUS": "Pending",
                    "GEOPOLITICAL_ZONE": geopolitical_zone
                }
                
                event_list.append(event_info)
                log_if_troubleshooting(f"Added event: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(event_list)} events from WANEP Nigeria")
        
    except Exception as e:
        logger.error(f"Error scraping WANEP Nigeria: {e}")
        logger.error(traceback.format_exc())


def main():
    logger.info("############ Initializing WANEP Nigeria scraper ############")
    
    hash_file_key = None
    hash_file = None
    s3_bucket = None
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, "config.yml")
    
    if ENV_PROD:
        hash_file_key = os.environ.get('HASH_PATH')
        hash_file = hash_file_key.split("/")[1]
        s3_bucket = os.environ.get('S3BUCKET')
    
    config_parameters = load_config(config_file)
    backfill = config_parameters['other_params'][0]['backfill']
    rerun = config_parameters['other_params'][1]['rerun']
    
    date_list, log_message = date_list_log_message(backfill, rerun, source_name, hash_file_key, hash_file)
    logger.info(log_message)
    
    # Get target states from config
    dynamic_params = config_parameters['dynamic_params']
    target_states = dynamic_params[0]['states']
    first_run = dynamic_params[0]['first_run']
    
    logger.info(f"Target states: {target_states}")
    
    # Clear event list
    event_list.clear()
    
    # Scrape WANEP Nigeria
    scrape_wanep_news(date_list, target_states)
    
    # Save results
    logger.info("Saving scraped data...")
    try:
        if not event_list:
            logger.info("No events found")
        elif ENV_PROD:
            logger.info(f"Uploading to S3: {s3_bucket}, {hash_file}, {hash_file_key}")
            upload_csv_to_s3(event_list, source_name, s3_bucket, hash_file, hash_file_key)
            logger.info("Completed writing to S3")
        else:
            logger.info("Saving locally")
            save_csv_local(event_list, source_name)
            logger.info("Completed local save")
    except Exception as e:
        message = f"Error saving data: \n {str(e)}\n\n{traceback.format_exc()}"
        logger.error(message)
        if ENV_PROD:
            publish_error_to_sns(message, SNS_ARN_DEVELOPERS, source_name)
    
    logger.info("Scraping completed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_message = f"An error occurred:\n {str(e)}\n\n{traceback.format_exc()}"
        logger.error(error_message)
        if ENV_PROD:
            publish_error_to_sns(error_message, SNS_ARN_BUSINESS, source_name)
            publish_error_to_sns(error_message, SNS_ARN_DEVELOPERS, source_name)