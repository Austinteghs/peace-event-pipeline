"""
Google Cloud Platform utilities for NPAID Peace Events Scraper
Replaces AWS S3/SNS with GCS/Pub/Sub
"""

import logging
import hashlib
import io
import traceback
from datetime import datetime, timedelta
from pyppeteer import launch
from pyppeteer_stealth import stealth
import requests
import asyncio
import yaml
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd
import os
from playwright.sync_api import sync_playwright
from retry import retry
from pydantic import BaseModel, ValidationError

# Google Cloud imports
from google.cloud import storage
from google.cloud import pubsub_v1
import pyarrow.parquet as pq
import pyarrow as pa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PUBSUB_TOPIC_DEVELOPERS = os.environ.get('PUBSUB_TOPIC_DEVELOPERS')
PUBSUB_TOPIC_BUSINESS = os.environ.get('PUBSUB_TOPIC_BUSINESS')
ENV_PROD = os.environ.get('ENV')
GCS_BUCKET = os.environ.get('GCS_BUCKET')
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID')

# Initialize GCP clients
if ENV_PROD:
    storage_client = storage.Client()
    publisher = pubsub_v1.PublisherClient()
    troubleshooting = True if ENV_PROD == 'dev' else False
else:
    storage_client = None
    publisher = None
    troubleshooting = True

today = datetime.now().date()
yesterday = today - timedelta(days=1)

# Nigerian states for filtering
PILOT_STATES = ['Kaduna', 'Katsina', 'Benue', 'Plateau']
ALL_NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
    'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
    'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi',
    'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo',
    'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'FCT'
]


def log_if_troubleshooting(string):
    if troubleshooting:
        logger.info(string)


def publish_error_to_pubsub(message, topic_name, source):
    """Publish error message to Google Cloud Pub/Sub"""
    try:
        if not ENV_PROD or not publisher or not GCP_PROJECT_ID:
            logger.warning("Pub/Sub not configured, skipping notification")
            return None
        
        topic_path = publisher.topic_path(GCP_PROJECT_ID, topic_name)
        
        # Message must be a bytestring
        message_data = f"{source.title()} Peace Events Scraper Error:\n\n{message}"
        data = message_data.encode('utf-8')
        
        # Publish message
        future = publisher.publish(topic_path, data)
        message_id = future.result()
        
        logger.info(f"Published message to {topic_name}: {message_id}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to publish message to Pub/Sub: {e}")
        return None


def generate_dates(dates_range):
    start_date_str, end_date_str = dates_range.split(":")
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    date_list = []
    delta = timedelta(days=1)

    while start_date <= end_date:
        date_list.append(start_date.strftime("%Y-%m-%d"))
        start_date += delta

    return date_list


def get_yesterdays(dates):
    yesterdays = []
    for date in dates:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_before = date_obj - timedelta(days=1)
        yesterdays.append(day_before.strftime('%Y-%m-%d'))
    return yesterdays


def load_config(filename):
    """Load a configuration file."""
    with open(filename, 'r') as config_file:
        config = yaml.safe_load(config_file)['parameters']
    return config


def date_list_log_message(backfill, rerun, source, hash_file_key, hash_file):
    date_list = log_message = None
    date_scenarios = [
        (backfill, "Backfilling for "),
        (rerun, "Rerun for ")
    ]

    if backfill == "yyyy-mm-dd" and rerun == "yyyy-mm-dd":
        date_list = [yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]
        log_message = "Scraping for today"
    else:
        for date_scenario, log in date_scenarios:
            if date_scenario != "yyyy-mm-dd":
                if isinstance(date_scenario, list):
                    date_list = date_scenario
                elif ":" in date_scenario:
                    date_list = generate_dates(date_scenario)
                else:
                    date_list = [date_scenario]
                if ENV_PROD:
                    for date in date_list:
                        rerun_delete(date, source, hash_file_key, hash_file)
                date_list = get_yesterdays(date_list)
                log_message = f"{log} + {date_list}"

    return date_list, log_message


def create_hash(data):
    """Create SHA256 hash for deduplication"""
    event_id = hashlib.sha256(data.encode()).hexdigest()
    return event_id


def extract_state_from_text(text):
    """Extract Nigerian state from text"""
    if not text:
        return "NA"
    
    text_upper = text.upper()
    for state in ALL_NIGERIAN_STATES:
        if state.upper() in text_upper:
            return state
    return "NA"


def is_pilot_state(state_name):
    """Check if state is one of the 4 pilot states"""
    return state_name in PILOT_STATES


async def scrape_and_return_html(url):
    logger.info("Launching the browser...")
    browser = await launch(
        headless=True,
        executablePath='/usr/bin/chromium',
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )

    page = await browser.newPage()
    await stealth(page)
    await page.setRequestInterception(True)

    async def handle_request(request):
        if request.resourceType == 'script':
            await request.abort()
        else:
            await request.continue_()

    page.on('request', lambda request: asyncio.ensure_future(handle_request(request)))

    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36')
    await page.setViewport({'width': 1920, 'height': 1080})

    await page.evaluateOnNewDocument('''() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    }''')

    await page.setExtraHTTPHeaders({
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    })

    logger.info(f"Navigating to {url}")
    await page.goto(url, waitUntil='networkidle0')

    page_content = await page.content()
    logger.info("Page content retrieved successfully.")

    await browser.close()
    logger.info("Browser closed.")

    return page_content


def initialize_puppeteer_driver(url, click_dict=None, sleep=0):
    try:
        html_content = asyncio.run(scrape_and_return_html(url))
        return html_content
    except Exception as e:
        log_if_troubleshooting(f"Exception Occurred when accessing {url}: {e}")


def initialize_driver(url, click_dict=None, sleep=0):
    """Initialize the WebDriver with options and user agent."""
    if click_dict is None:
        click_dict = {}
    ua = UserAgent()
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch()
    user_agent = ua.random
    context = browser.new_context(user_agent=user_agent)
    page = context.new_page()
    page.goto(url)
    if click_dict:
        for key, value in click_dict.items():
            try:
                page.click(f'[{key}="{value}"]')
                time.sleep(sleep)
            except Exception as e:
                logger.info(f'element missing{e}')
    response = page.content()
    browser.close()
    playwright.stop()
    return response


def initialize_no_driver(url):
    """Makes a GET request to a URL and returns the HTML content."""
    try:
        response = requests.get(url, timeout=30)
        return response.text
    except requests.RequestException as e:
        logger.info(f"Request to {url} failed: {e}")
        return None


# Define the expected schema using Pydantic
class PeaceEventDataSchema(BaseModel):
    EVENT_ID: str
    EVENT_TITLE: str
    EVENT_TYPE: str
    EVENT_SUBTYPE: str
    ORGANIZATION: str
    STATE: str
    LGA: str
    LOCATION_DETAILS: str
    DATE_POSTED: str
    EVENT_DATE: str
    EVENT_URL: str
    SOURCE_DOMAIN: str
    DESCRIPTION: str
    OUTCOME: str
    PRIMARY_ACTOR: str
    ASSOCIATED_ACTOR: str
    ACTOR_INTERACTION: str
    SOURCE_TYPE: str
    INGESTION_DATE: str
    VERIFICATION_STATUS: str
    GEOPOLITICAL_ZONE: str


def validate_dataframe(df: pd.DataFrame, expected_columns):
    """Validate the DataFrame structure and content"""
    if list(df.columns) != expected_columns:
        raise ValueError(
            f"Columns are not in the expected order or are missing. Expected: {expected_columns}, Found: {list(df.columns)}"
        )

    for index, row in df.iterrows():
        try:
            PeaceEventDataSchema(**row.to_dict())
        except ValidationError as e:
            raise ValueError(f"Row {index} failed validation: {e}")


def load_existing_hashes_gcs(bucket_name, hash_blob_path):
    """Load existing event hashes from Google Cloud Storage"""
    columns = ['EVENT_ID', 'DATE']
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(hash_blob_path)
        
        if not blob.exists():
            return pd.DataFrame(columns=columns)
        
        # Download to memory
        hash_content = blob.download_as_bytes()
        existing_hashes_df = pd.read_csv(io.BytesIO(hash_content))
        
        if 'EVENT_ID' not in existing_hashes_df.columns or 'DATE' not in existing_hashes_df.columns:
            return pd.DataFrame(columns=columns)
        
        return existing_hashes_df
    
    except Exception as e:
        logger.warning(f"Could not load existing hashes: {e}")
        return pd.DataFrame(columns=columns)


def load_existing_hashes_local(hash_filename):
    """Load existing event hashes from local file"""
    columns = ['EVENT_ID', 'DATE']
    try:
        existing_hashes_df = pd.read_csv(hash_filename, header=None, names=columns)
        return existing_hashes_df
    except FileNotFoundError:
        dataframe = pd.DataFrame(columns=columns)
        dataframe.to_csv(hash_filename, index=False)
        return dataframe


def save_new_hashes_gcs(new_hashes, bucket_name, hash_blob_path):
    """Save new event hashes to Google Cloud Storage"""
    try:
        columns = ['EVENT_ID', 'DATE']
        existing_hashes_df = load_existing_hashes_gcs(bucket_name, hash_blob_path)
        new_hashes_df = pd.DataFrame(new_hashes, columns=columns)
        updated_hashes_df = pd.concat([existing_hashes_df, new_hashes_df]).drop_duplicates(subset='EVENT_ID')
        
        # Upload to GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(hash_blob_path)
        
        csv_buffer = io.StringIO()
        updated_hashes_df.to_csv(csv_buffer, index=False)
        blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')
        
        logger.info(f"Saved {len(new_hashes)} new hashes to GCS: {hash_blob_path}")
    except Exception as e:
        logger.error(f"Error saving new hashes to GCS: {e}")
        logger.error(traceback.format_exc())


def save_new_hashes_local(new_hashes, hash_filename):
    """Save new event hashes to local file"""
    try:
        columns = ['EVENT_ID', 'DATE']
        new_hashes_df = pd.DataFrame(new_hashes, columns=columns)
        existing_hashes_df = load_existing_hashes_local(hash_filename)
        updated_hashes_df = pd.concat([existing_hashes_df, new_hashes_df]).drop_duplicates(subset='EVENT_ID')
        updated_hashes_df.to_csv(hash_filename, index=False)
    except Exception as e:
        logger.info(f"Error: {e}")


def save_csv_local(event_list, source):
    """Save peace events to local CSV file"""
    df = pd.DataFrame(event_list)
    existing_hashes = load_existing_hashes_local('hash.csv')
    existing_hashes_df = pd.DataFrame(existing_hashes)
    existing_event_ids = existing_hashes_df['EVENT_ID']

    new_events = df[~df['EVENT_ID'].isin(existing_event_ids)]
    
    event_columns = [
        "EVENT_ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_SUBTYPE", "ORGANIZATION",
        "STATE", "LGA", "LOCATION_DETAILS", "DATE_POSTED", "EVENT_DATE", "EVENT_URL",
        "SOURCE_DOMAIN", "DESCRIPTION", "OUTCOME", "PRIMARY_ACTOR", "ASSOCIATED_ACTOR",
        "ACTOR_INTERACTION", "SOURCE_TYPE", "INGESTION_DATE", "VERIFICATION_STATUS",
        "GEOPOLITICAL_ZONE"
    ]

    new_events = new_events[event_columns]
    new_events = new_events.astype(str)

    try:
        validate_dataframe(new_events, event_columns)
        logger.info("DataFrame passed validation!")
        current_datetime = str(datetime.now()).replace(" ", "-").replace(":", "-").replace(".", "-")
        directory_name = "data"
        os.makedirs(directory_name, exist_ok=True)
        csv_filename = f"{directory_name}/{source.lower().replace(' ', '-')}_peace_events_{current_datetime}.csv"
        new_events.to_csv(csv_filename, index=False, encoding='utf-8')
        
        save_new_hashes_local(
            [(row['EVENT_ID'], row['DATE_POSTED']) for _, row in new_events.iterrows()],
            "hash.csv"
        )
        logger.info(f"Saved {len(new_events)} new events to {csv_filename}")
    except ValueError as e:
        logger.info(f"DataFrame validation failed: {e}")


def upload_to_gcs(event_list, source, bucket_name, hash_blob_path):
    """Upload peace events to Google Cloud Storage as Parquet"""
    existing_hashes = load_existing_hashes_gcs(bucket_name, hash_blob_path)
    df = pd.DataFrame(event_list)
    df = df.astype(str)

    if not existing_hashes.empty:
        existing_event_ids = existing_hashes["EVENT_ID"]
        new_events = df[~df["EVENT_ID"].isin(existing_event_ids)]
    else:
        new_events = df

    if not new_events.empty:
        event_columns = [
            "EVENT_ID", "EVENT_TITLE", "EVENT_TYPE", "EVENT_SUBTYPE", "ORGANIZATION",
            "STATE", "LGA", "LOCATION_DETAILS", "DATE_POSTED", "EVENT_DATE", "EVENT_URL",
            "SOURCE_DOMAIN", "DESCRIPTION", "OUTCOME", "PRIMARY_ACTOR", "ASSOCIATED_ACTOR",
            "ACTOR_INTERACTION", "SOURCE_TYPE", "INGESTION_DATE", "VERIFICATION_STATUS",
            "GEOPOLITICAL_ZONE"
        ]

        new_events = new_events[event_columns]
        current_datetime = datetime.now().strftime('%Y-%m-%d')
        
        try:
            validate_dataframe(new_events, event_columns)
            logger.info("DataFrame passed validation!")
            
            # Convert to Parquet and upload
            bucket = storage_client.bucket(bucket_name)
            blob_path = f'peace_events/{source}/{current_datetime}/data.parquet'
            blob = bucket.blob(blob_path)
            
            # Write parquet to buffer
            table = pa.Table.from_pandas(new_events)
            parquet_buffer = io.BytesIO()
            pq.write_table(table, parquet_buffer)
            parquet_buffer.seek(0)
            
            # Upload to GCS
            blob.upload_from_file(parquet_buffer, content_type='application/octet-stream')
            logger.info(f"Writing data to gs://{bucket_name}/{blob_path}")
            
            # Save hashes
            save_new_hashes_gcs(
                [(row["EVENT_ID"], row['INGESTION_DATE']) for _, row in new_events.iterrows()],
                bucket_name,
                hash_blob_path
            )
        except Exception as e:
            logger.error(f"Error writing file and hashing to parquet: {e}")
            logger.error(traceback.format_exc())


def rerun_delete(date, source, hash_blob_path, bucket_name):
    """Delete data for rerun in GCS"""
    if date != 'yyyy-mm-dd':
        blob_prefix = f'peace_events/{source}/{date}/'
        
        # Delete hash entries for this date
        df = load_existing_hashes_gcs(bucket_name, hash_blob_path)
        df = df[df['DATE'] != date]
        
        # Save updated hashes
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(hash_blob_path)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')
        
        # Delete data files
        blobs = bucket.list_blobs(prefix=blob_prefix)
        for blob in blobs:
            blob.delete()
            logger.info(f"Deleted {blob.name}")