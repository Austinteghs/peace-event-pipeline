"""
Leadership Newspaper Peace Events Scraper - Fixed Version
"""

import datetime
import os
import sys
import time
import traceback
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    ENV_PROD, log_if_troubleshooting, logger, upload_to_gcs, publish_error_to_pubsub,
    PUBSUB_TOPIC_DEVELOPERS, save_csv_local, load_config,
    PUBSUB_TOPIC_BUSINESS, date_list_log_message, create_hash, extract_state_from_text,
    initialize_no_driver, PILOT_STATES
)

source_name = "leadership_ng"
event_list = []
BASE_URL = "https://leadership.ng"


def extract_date_from_text(date_text):
    try:
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.datetime.strptime(date_text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        if 'ago' in date_text.lower():
            if 'hour' in date_text.lower() or 'minute' in date_text.lower():
                return datetime.datetime.now().strftime("%Y-%m-%d")
            elif 'day' in date_text.lower():
                days_match = re.search(r'(\d+)\s*day', date_text.lower())
                if days_match:
                    days_ago = int(days_match.group(1))
                    date_obj = datetime.datetime.now() - datetime.timedelta(days=days_ago)
                    return date_obj.strftime("%Y-%m-%d")
        
        return datetime.datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def classify_event_type(title, description):
    text = f"{title} {description}".lower()
    
    if any(word in text for word in ['policy', 'legislation', 'law', 'bill']):
        return "Legislation / Policy", "Policy Development"
    elif any(word in text for word in ['dialogue', 'discussion', 'meeting', 'consultation']):
        return "Peace Dialogues", "Community Dialogue"
    elif any(word in text for word in ['training', 'workshop', 'capacity']):
        return "Training and Capacity Building", "Peace Training"
    elif any(word in text for word in ['mediation', 'reconciliation', 'resolution']):
        return "Conflict Mediation", "Community Mediation"
    elif any(word in text for word in ['agreement', 'accord', 'pact']):
        return "Peace Agreements", "Peace Agreement"
    elif any(word in text for word in ['warning', 'monitoring', 'alert']):
        return "Early Warning Systems", "Early Warning"
    elif any(word in text for word in ['program', 'programme', 'initiative', 'project']):
        return "Peace Programmes", "Peace Initiative"
    return "Peace Actions", "General Peace Action"


def extract_actors(description):
    description_lower = description.lower()
    primary_actor = "NA"
    associated_actor = "NA"
    
    if any(word in description_lower for word in ['government', 'governor', 'ministry', 'state']):
        primary_actor = "State Ministries and Agencies"
    elif any(word in description_lower for word in ['civil society', 'ngo', 'organization']):
        primary_actor = "Civil Society Organizations (CSOs)"
    elif any(word in description_lower for word in ['community', 'youth', 'women']):
        primary_actor = "Community-Based Organizations (CBOs)"
    
    return primary_actor, associated_actor


def scrape_leadership_news(date_list, target_states, config):
    logger.info(f"Scraping Leadership Newspaper for states: {target_states}")
    
    crawling_config = config.get('crawling', {})
    max_pages = crawling_config.get('max_pages', 15)
    delay_seconds = crawling_config.get('delay_seconds', 2)
    
    current_url = f"{BASE_URL}/category/news"
    page_count = 0
    
    try:
        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"========== Scraping page {page_count}/{max_pages}: {current_url} ==========")
            
            html = initialize_no_driver(current_url)
            if not html:
                logger.error(f"Failed to retrieve page {page_count}")
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('article') or soup.find_all('div', class_='post')
            
            if not articles:
                logger.info(f"No articles found on page {page_count}, stopping crawl")
                break
            
            logger.info(f"Found {len(articles)} articles on page {page_count}")
            
            for idx, article in enumerate(articles, 1):
                try:
                    title_elem = article.find('h2') or article.find('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Check if peace-related
                    peace_keywords = ['peace', 'conflict', 'dialogue', 'mediation', 'reconciliation']
                    if not any(keyword in title.lower() for keyword in peace_keywords):
                        continue
                    
                    link_elem = article.find('a', href=True)
                    if link_elem:
                        event_url = link_elem['href']
                        if not event_url.startswith('http'):
                            event_url = urljoin(BASE_URL, event_url)
                    else:
                        event_url = current_url
                    
                    date_elem = article.find('time') or article.find('span', class_='date')
                    if date_elem:
                        date_posted = extract_date_from_text(date_elem.get_text(strip=True))
                    else:
                        date_posted = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    if date_list and date_posted not in date_list:
                        continue
                    
                    desc_elem = article.find('p') or article.find('div', class_='excerpt')
                    description = desc_elem.get_text(strip=True) if desc_elem else title
                    
                    state = extract_state_from_text(f"{title} {description}")
                    
                    if state not in target_states and state != "NA":
                        continue
                    
                    event_type, event_subtype = classify_event_type(title, description)
                    primary_actor, associated_actor = extract_actors(description)
                    
                    zone_map = {
                        'Kaduna': 'North West',
                        'Katsina': 'North West',
                        'Benue': 'North Central',
                        'Plateau': 'North Central'
                    }
                    geopolitical_zone = zone_map.get(state, "NA")
                    
                    event_id = create_hash("".join(map(str, (title, state, date_posted, event_url))))
                    
                    event_info = {
                        "EVENT_ID": event_id,
                        "EVENT_TITLE": title,
                        "EVENT_TYPE": event_type,
                        "EVENT_SUBTYPE": event_subtype,
                        "ORGANIZATION": "Leadership Newspaper",
                        "STATE": state,
                        "LGA": "NA",
                        "LOCATION_DETAILS": state if state != "NA" else "Nigeria",
                        "DATE_POSTED": date_posted,
                        "EVENT_DATE": date_posted,
                        "EVENT_URL": event_url,
                        "SOURCE_DOMAIN": "leadership.ng",
                        "DESCRIPTION": description[:500],
                        "OUTCOME": "NA",
                        "PRIMARY_ACTOR": primary_actor,
                        "ASSOCIATED_ACTOR": associated_actor,
                        "ACTOR_INTERACTION": f"{primary_actor} - {associated_actor}" if associated_actor != "NA" else primary_actor,
                        "SOURCE_TYPE": "Nigerian Media",
                        "INGESTION_DATE": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "VERIFICATION_STATUS": "Pending",
                        "GEOPOLITICAL_ZONE": geopolitical_zone
                    }
                    
                    event_list.append(event_info)
                    logger.info(f"  [{page_count}.{idx}] Added: {title[:60]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing article on page {page_count}: {e}")
                    continue
            
            # Find next page
            next_button = soup.find('a', class_='next') or soup.find('a', {'rel': 'next'})
            if next_button and next_button.get('href'):
                current_url = urljoin(BASE_URL, next_button['href'])
                time.sleep(delay_seconds)
            else:
                logger.info("No more pages found")
                break
        
        logger.info(f"========== Crawling Summary ==========")
        logger.info(f"Pages crawled: {page_count}")
        logger.info(f"Articles found: {len(event_list)}")
        logger.info(f"Events collected: {len(event_list)}")
        
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        logger.error(traceback.format_exc())


def main():
    logger.info("############ Initializing Leadership Newspaper Scraper (GCP Version) ############")
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, "config.yml")
    
    config_parameters = load_config(config_file)
    backfill = config_parameters['other_params'][0]['backfill']
    rerun = config_parameters['other_params'][1]['rerun']
    
    hash_blob_path = os.environ.get('HASH_PATH') if ENV_PROD else None
    gcs_bucket = os.environ.get('GCS_BUCKET') if ENV_PROD else None
    
    date_list, log_message = date_list_log_message(backfill, rerun, source_name, hash_blob_path, None)
    logger.info(log_message)
    
    target_states = config_parameters['dynamic_params'][0]['states']
    
    logger.info(f"Target states: {target_states}")
    
    event_list.clear()
    scrape_leadership_news(date_list, target_states, config_parameters)
    
    logger.info("Saving scraped data...")
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