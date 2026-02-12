"""
WANEP Nigeria Peace Events Scraper - GCP Version with Web Crawling
This version includes pagination crawling and individual article scraping
"""

import datetime
import hashlib
import os
import sys
import time
import traceback
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scrapers.utils import (
    ENV_PROD, log_if_troubleshooting, logger, upload_to_gcs, publish_error_to_pubsub,
    PUBSUB_TOPIC_DEVELOPERS, save_csv_local, load_config,
    PUBSUB_TOPIC_BUSINESS, date_list_log_message, create_hash, extract_state_from_text,
    is_pilot_state, initialize_no_driver, PILOT_STATES
)

GCS_BUCKET = os.environ.get("GCS_BUCKET")
CONFIG_FILE = os.environ.get("CONFIG_PATH")
HASH_PATH = os.environ.get("HASH_PATH")

logger.info(f"GCS bucket location ==> {GCS_BUCKET}")
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
        for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                parsed_date = datetime.datetime.strptime(date_text.strip(), fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
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


def find_next_page_url(soup, current_url):
    """
    Find the URL for the next page of results
    Handles multiple pagination patterns
    """
    # Pattern 1: Look for "Next" button/link
    next_button = (
        soup.find('a', class_='next') or
        soup.find('a', class_='pagination-next') or
        soup.find('a', {'rel': 'next'}) or
        soup.find('a', text=re.compile(r'Next|next|→|»', re.I))
    )
    
    if next_button and next_button.get('href'):
        next_url = next_button['href']
        return urljoin(BASE_URL, next_url)
    
    # Pattern 2: Look for numbered pagination
    pagination = soup.find('div', class_='pagination') or soup.find('ul', class_='pagination')
    if pagination:
        links = pagination.find_all('a', href=True)
        for link in links:
            # Look for the next page number
            if link.get('aria-label') == 'Next page' or 'next' in link.get('class', []):
                return urljoin(BASE_URL, link['href'])
    
    # Pattern 3: Check URL for page parameter and increment
    parsed = urlparse(current_url)
    if 'page=' in parsed.query:
        # Extract current page number
        match = re.search(r'page=(\d+)', parsed.query)
        if match:
            current_page = int(match.group(1))
            next_page = current_page + 1
            next_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
            return next_url
    
    return None


def scrape_article_details(article_url):
    """
    Visit an individual article page and extract full details
    Returns additional information not available on listing page
    """
    try:
        logger.info(f"Fetching article details: {article_url}")
        html = initialize_no_driver(article_url)
        
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        details = {}
        
        # Extract full content/description
        content_elem = (
            soup.find('div', class_='article-content') or
            soup.find('div', class_='entry-content') or
            soup.find('article')
        )
        
        if content_elem:
            # Get all paragraphs
            paragraphs = content_elem.find_all('p')
            full_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            details['full_description'] = full_text[:1000]  # Limit to 1000 chars
        
        # Extract outcome/results if mentioned
        outcome_keywords = ['outcome', 'result', 'achievement', 'agreement', 'resolution']
        if content_elem:
            text = content_elem.get_text().lower()
            for keyword in outcome_keywords:
                if keyword in text:
                    # Try to extract the sentence containing the keyword
                    sentences = text.split('.')
                    for sentence in sentences:
                        if keyword in sentence:
                            details['outcome'] = sentence.strip()[:200]
                            break
        
        # Extract location details
        location_elem = soup.find('span', class_='location') or soup.find('div', class_='location')
        if location_elem:
            details['location_details'] = location_elem.get_text(strip=True)
        
        return details
        
    except Exception as e:
        logger.error(f"Error scraping article details from {article_url}: {e}")
        return {}


def scrape_wanep_news_with_crawling(date_list, target_states, config):
    """
    Scrape WANEP Nigeria news with pagination crawling
    
    Args:
        date_list: List of dates to filter
        target_states: List of states to filter
        config: Configuration dict with crawling settings
    """
    logger.info(f"Scraping WANEP Nigeria news for states: {target_states}")
    
    # Get crawling configuration
    crawling_config = config.get('crawling', {})
    max_pages = crawling_config.get('max_pages', 10)
    delay_seconds = crawling_config.get('delay_seconds', 2)
    follow_article_links = crawling_config.get('follow_article_links', False)
    
    logger.info(f"Crawling config: max_pages={max_pages}, delay={delay_seconds}s, follow_links={follow_article_links}")
    
    current_url = NEWS_URL
    page_count = 0
    total_articles_found = 0
    
    try:
        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"========== Scraping page {page_count}/{max_pages}: {current_url} ==========")
            
            # Get page content
            html = initialize_no_driver(current_url)
            if not html:
                logger.error(f"Failed to retrieve page {page_count}")
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all articles on this page
            articles = soup.find_all('article') or soup.find_all('div', class_='news-item')
            
            if not articles:
                logger.info(f"No articles found on page {page_count}, stopping crawl")
                break
            
            logger.info(f"Found {len(articles)} articles on page {page_count}")
            total_articles_found += len(articles)
            
            # Process each article
            for idx, article in enumerate(articles, 1):
                try:
                    # Extract basic info from listing
                    title_elem = article.find('h2') or article.find('h3') or article.find('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract article URL
                    link_elem = article.find('a', href=True)
                    if link_elem:
                        event_url = link_elem['href']
                        if not event_url.startswith('http'):
                            event_url = urljoin(BASE_URL, event_url)
                    else:
                        event_url = current_url
                    
                    # Extract date
                    date_elem = article.find('time') or article.find('span', class_='date')
                    if date_elem:
                        date_posted = extract_date_from_text(date_elem.get_text(strip=True))
                    else:
                        date_posted = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    # Filter by date if needed
                    if date_list and date_posted not in date_list:
                        log_if_troubleshooting(f"Skipping article (date filter): {title[:50]}")
                        continue
                    
                    # Extract description from listing
                    desc_elem = article.find('p') or article.find('div', class_='excerpt')
                    description = desc_elem.get_text(strip=True) if desc_elem else title
                    
                    # If configured, visit individual article for full details
                    additional_details = {}
                    if follow_article_links and event_url != current_url:
                        additional_details = scrape_article_details(event_url)
                        time.sleep(1)  # Small delay between article requests
                    
                    # Use full description if available
                    if additional_details.get('full_description'):
                        description = additional_details['full_description']
                    
                    # Extract state from title and description
                    state = extract_state_from_text(f"{title} {description}")
                    
                    # Filter by state
                    if state not in target_states and state != "NA":
                        log_if_troubleshooting(f"Skipping article (state filter): {title[:50]}")
                        continue
                    
                    # Classify event
                    event_type, event_subtype = classify_event_type(title, description)
                    primary_actor, associated_actor = extract_actors(description)
                    
                    # Geopolitical zone mapping
                    zone_map = {
                        'Kaduna': 'North West',
                        'Katsina': 'North West',
                        'Benue': 'North Central',
                        'Plateau': 'North Central'
                    }
                    geopolitical_zone = zone_map.get(state, "NA")
                    
                    # Create unique hash
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
                        "LGA": "NA",
                        "LOCATION_DETAILS": additional_details.get('location_details', state if state != "NA" else "Nigeria"),
                        "DATE_POSTED": date_posted,
                        "EVENT_DATE": date_posted,
                        "EVENT_URL": event_url,
                        "SOURCE_DOMAIN": "wanepnigeria.org",
                        "DESCRIPTION": description[:500],
                        "OUTCOME": additional_details.get('outcome', "NA"),
                        "PRIMARY_ACTOR": primary_actor,
                        "ASSOCIATED_ACTOR": associated_actor,
                        "ACTOR_INTERACTION": f"{primary_actor} - {associated_actor}" if associated_actor != "NA" else primary_actor,
                        "SOURCE_TYPE": "Civil Society Organization",
                        "INGESTION_DATE": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "VERIFICATION_STATUS": "Pending",
                        "GEOPOLITICAL_ZONE": geopolitical_zone
                    }
                    
                    event_list.append(event_info)
                    logger.info(f"  [{page_count}.{idx}] Added: {title[:60]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing article on page {page_count}: {e}")
                    continue
            
            # Find next page URL
            next_url = find_next_page_url(soup, current_url)
            
            if next_url:
                logger.info(f"Next page found: {next_url}")
                current_url = next_url
                
                # Be polite: delay between page requests
                logger.info(f"Waiting {delay_seconds} seconds before next page...")
                time.sleep(delay_seconds)
            else:
                logger.info("No more pages found, crawling complete")
                break
        
        logger.info(f"========== Crawling Summary ==========")
        logger.info(f"Pages crawled: {page_count}")
        logger.info(f"Articles found: {total_articles_found}")
        logger.info(f"Events collected: {len(event_list)}")
        logger.info(f"=====================================")
        
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        logger.error(traceback.format_exc())


def main():
    logger.info("############ Initializing WANEP Nigeria scraper with Web Crawling (GCP Version) ############")
    
    hash_blob_path = None
    gcs_bucket = None
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, "config.yml")
    
    if ENV_PROD:
        hash_blob_path = os.environ.get('HASH_PATH')
        gcs_bucket = os.environ.get('GCS_BUCKET')
    
    config_parameters = load_config(config_file)
    backfill = config_parameters['other_params'][0]['backfill']
    rerun = config_parameters['other_params'][1]['rerun']
    
    date_list, log_message = date_list_log_message(backfill, rerun, source_name, hash_blob_path, None)
    logger.info(log_message)
    
    dynamic_params = config_parameters['dynamic_params']
    target_states = dynamic_params[0]['states']
    first_run = dynamic_params[0]['first_run']
    
    logger.info(f"Target states: {target_states}")
    
    event_list.clear()
    
    # Use crawling version
    scrape_wanep_news_with_crawling(date_list, target_states, config_parameters)
    
    logger.info("Saving scraped data...")
    try:
        if not event_list:
            logger.info("No events found")
        elif ENV_PROD:
            logger.info(f"Uploading to GCS: {gcs_bucket}, {hash_blob_path}")
            upload_to_gcs(event_list, source_name, gcs_bucket, hash_blob_path)
            logger.info("Completed writing to GCS")
        else:
            logger.info("Saving locally")
            save_csv_local(event_list, source_name)
            logger.info("Completed local save")
    except Exception as e:
        message = f"Error saving data: \n {str(e)}\n\n{traceback.format_exc()}"
        logger.error(message)
        if ENV_PROD:
            publish_error_to_pubsub(message, PUBSUB_TOPIC_DEVELOPERS, source_name)
    
    logger.info("Scraping completed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_message = f"An error occurred:\n {str(e)}\n\n{traceback.format_exc()}"
        logger.error(error_message)
        if ENV_PROD:
            publish_error_to_pubsub(error_message, PUBSUB_TOPIC_BUSINESS, source_name)
            publish_error_to_pubsub(error_message, PUBSUB_TOPIC_DEVELOPERS, source_name)