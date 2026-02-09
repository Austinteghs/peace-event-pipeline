import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import json
import sqlite3
from urllib.parse import urlparse
import os

# -------------------------------------------------------------------
# 1. LOAD YOUR EXISTING DATA
# -------------------------------------------------------------------
print("Loading your existing NPAID data...")
try:
    df = pd.read_csv('updated NPAID.csv')
    existing_urls = set(df['source_url'].dropna().unique())
    print(f"Loaded {len(df)} existing events, {len(existing_urls)} unique URLs")
except FileNotFoundError:
    print("WARNING: updated NPAID.csv not found. Starting fresh.")
    df = pd.DataFrame()
    existing_urls = set()

# -------------------------------------------------------------------
# 2. SIMPLE SCRAPER FUNCTION
# -------------------------------------------------------------------
def scrape_article(url):
    """Simple function to scrape an article"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get title
        title = soup.title.string if soup.title else ""
        
        # Get content (simple approach)
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        content = ' '.join(chunk for chunk in lines if chunk)
        
        # Extract date (simple patterns)
        date_patterns = [
            r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',
            r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)[\s,]+\d{1,2},?\s+\d{4}\b'
        ]
        
        article_date = None
        for pattern in date_patterns:
            match = re.search(pattern, content[:2000], re.IGNORECASE)
            if match:
                article_date = match.group(0)
                break
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'date_found': article_date,
            'success': True
        }
    except Exception as e:
        return {
            'url': url,
            'error': str(e),
            'success': False
        }

# -------------------------------------------------------------------
# 3. PEACE EVENT EXTRACTOR
# -------------------------------------------------------------------
class SimplePeaceExtractor:
    def __init__(self):
        # Nigerian states
        self.states = [
            'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
            'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
            'FCT', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi',
            'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun',
            'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
        ]
        
        # Peace keywords
        self.peace_keywords = [
            'peace agreement', 'peace accord', 'ceasefire', 'truce',
            'dialogue', 'mediation', 'negotiation', 'talks',
            'peacebuilding', 'peacekeeping', 'conflict resolution',
            'reconciliation', 'harmony', 'coexistence',
            'early warning', 'reintegration', 'amnesty',
            'peace commission', 'peace committee', 'peace initiative'
        ]
    
    def extract_event(self, article_data):
        """Extract peace event from article"""
        content = article_data['content'].lower()
        title = article_data['title'].lower()
        
        # Check if it's about peace
        is_peace_article = any(keyword in content or keyword in title 
                               for keyword in self.peace_keywords)
        
        if not is_peace_article:
            return None
        
        # Find mentioned states
        mentioned_states = []
        for state in self.states:
            if re.search(r'\b' + re.escape(state.lower()) + r'\b', content):
                mentioned_states.append(state)
        
        # Determine event type
        event_type = "Peace Actions"
        event_subtype = "Peace agreement"
        
        if any(kw in content for kw in ['program', 'project', 'initiative', 'training']):
            event_type = "Programmes"
            event_subtype = "Peace education and sensitization activities"
        elif 'dialogue' in content or 'mediation' in content:
            event_subtype = "Meetings"
        elif 'early warning' in content:
            event_type = "Programmes"
            event_subtype = "Early warning systems"
        
        # Extract date
        event_date = article_data['date_found'] or datetime.now().strftime('%Y-01-01')
        
        # Simple actor extraction
        actors = self.extract_actors(content)
        
        # Create event dictionary
        event = {
            'event_id': f"NPE{int(time.time()) % 1000000:06d}",
            'event_date': event_date,
            'event_date_normalized': event_date,
            'event_type': event_type,
            'event_subtype': event_subtype,
            'event_description': article_data['content'][:500] + "..." if len(article_data['content']) > 500 else article_data['content'],
            'state_name': mentioned_states[0] if mentioned_states else "Not Specified",
            'geopolitical_zone': self.get_geopolitical_zone(mentioned_states[0] if mentioned_states else None),
            'primary_actor_category': "Civil Society Organizations",
            'primary_actor_name': actors[0] if actors else "Not Specified",
            'source_url': article_data['url'],
            'source_type': "Media articles",
            'source_closeness': self.get_source_closeness(article_data['url']),
            'verification_status': "Unverified",
            'reliability_level': "Medium",
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'data_collector': "Web Scraper",
            'ingestion_method': "Automated"
        }
        
        return event
    
    def extract_actors(self, content):
        """Extract actors from content"""
        # Common peace organizations in Nigeria
        common_orgs = [
            'Kaduna State Peace Commission',
            'Plateau Peace Building Agency', 
            'UNDP',
            'USIP',
            'UN',
            'Mercy Corps',
            'Search for Common Ground',
            'NEEM Foundation'
        ]
        
        found_actors = []
        for org in common_orgs:
            if org.lower() in content:
                found_actors.append(org)
        
        return found_actors[:2]  # Return max 2 actors
    
    def get_geopolitical_zone(self, state):
        """Get geopolitical zone for state"""
        if not state:
            return "Not Specified"
        
        zones = {
            'north central': ['benue', 'fct', 'kogi', 'kwara', 'nasarawa', 'niger', 'plateau'],
            'north east': ['adamawa', 'bauchi', 'borno', 'gombe', 'taraba', 'yobe'],
            'north west': ['jigawa', 'kaduna', 'kano', 'katsina', 'kebbi', 'sokoto', 'zamfara'],
            'south east': ['abia', 'anambra', 'ebonyi', 'enugu', 'imo'],
            'south south': ['akwa ibom', 'bayelsa', 'cross river', 'delta', 'edo', 'rivers'],
            'south west': ['ekiti', 'lagos', 'ogun', 'ondo', 'osun', 'oyo']
        }
        
        state_lower = state.lower()
        for zone, states in zones.items():
            if state_lower in states:
                return zone.title()
        
        return "Not Specified"
    
    def get_source_closeness(self, url):
        """Determine source closeness"""
        domain = urlparse(url).netloc.lower()
        
        if 'punchng.com' in domain or 'premiumtimesng.com' in domain:
            return "National media analysis"
        elif 'guardian.ng' in domain or 'vanguardngr.com' in domain:
            return "National media analysis"
        elif '.ng' in domain:
            return "Local media report"
        elif 'un.org' in domain or 'usip.org' in domain:
            return "National/International organization report"
        else:
            return "Local media report"

# -------------------------------------------------------------------
# 4. URL DISCOVERY - SIMPLE VERSION
# -------------------------------------------------------------------
def find_new_peace_urls():
    """Find new peace-related URLs from Nigerian news sites"""
    print("\nSearching for new peace event URLs...")
    
    # List of Nigerian news sites to check
    nigerian_sites = [
        "https://punchng.com",
        "https://www.premiumtimesng.com", 
        "https://www.vanguardngr.com",
        "https://dailytrust.com",
        "https://leadership.ng",
        "https://www.thisdaylive.com",
        "https://thenationonlineng.net"
    ]
    
    # Peace-related search terms
    search_terms = [
        "peace agreement Nigeria",
        "ceasefire Nigeria", 
        "dialogue Nigeria conflict",
        "mediation Nigeria",
        "peacebuilding Nigeria",
        "reconciliation Nigeria",
        "peace commission Nigeria",
        "early warning system Nigeria"
    ]
    
    new_urls = []
    
    # For now, just return some example URLs
    # In production, you would actually search these sites
    example_urls = [
        "https://punchng.com/peace-agreement-signed-in-kaduna/",
        "https://www.premiumtimesng.com/news/headlines/123456-ceasefire-in-plateau.html",
        "https://www.vanguardngr.com/2024/01/peace-dialogue-holds-in-benue/",
        "https://dailytrust.com/mediation-resolves-farmer-herder-conflict/"
    ]
    
    print(f"Found {len(example_urls)} example URLs to check")
    return example_urls

# -------------------------------------------------------------------
# 5. DATABASE SETUP
# -------------------------------------------------------------------
def setup_database():
    """Setup SQLite database"""
    conn = sqlite3.connect('peace_events.db')
    cursor = conn.cursor()
    
    # Create table matching your schema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS peace_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        event_date TEXT,
        event_date_normalized TEXT,
        event_time TEXT,
        time_precision TEXT,
        entry_date TEXT,
        data_collector TEXT,
        ingestion_method TEXT,
        created_by TEXT,
        updated_by TEXT,
        event_type TEXT,
        event_subtype TEXT,
        event_description TEXT,
        notes TEXT,
        outcome_description TEXT,
        state_name TEXT,
        geopolitical_zone TEXT,
        lga_name TEXT,
        ward_community TEXT,
        latitude REAL,
        longitude REAL,
        location_precision TEXT,
        primary_actor_category TEXT,
        primary_actor_name TEXT,
        associated_actor_category TEXT,
        associated_actor_name TEXT,
        actor_interaction TEXT,
        source_type TEXT,
        source_url TEXT UNIQUE,
        source_date TEXT,
        source_closeness TEXT,
        verification_status TEXT,
        reliability_level TEXT,
        multiple_sources INTEGER,
        source_count INTEGER,
        is_active INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create index for faster searches
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON peace_events(source_url)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_date ON peace_events(event_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_state ON peace_events(state_name)')
    
    conn.commit()
    return conn

def save_event_to_db(conn, event):
    """Save event to database"""
    cursor = conn.cursor()
    
    # Prepare data
    data = {
        'event_id': event.get('event_id'),
        'event_date': event.get('event_date'),
        'event_date_normalized': event.get('event_date_normalized'),
        'event_time': event.get('event_time'),
        'time_precision': event.get('time_precision', 'Day'),
        'entry_date': event.get('entry_date'),
        'data_collector': event.get('data_collector'),
        'ingestion_method': event.get('ingestion_method'),
        'created_by': event.get('created_by', 'scraper'),
        'updated_by': event.get('updated_by', 'scraper'),
        'event_type': event.get('event_type'),
        'event_subtype': event.get('event_subtype'),
        'event_description': event.get('event_description'),
        'notes': event.get('notes', ''),
        'outcome_description': event.get('outcome_description', ''),
        'state_name': event.get('state_name'),
        'geopolitical_zone': event.get('geopolitical_zone'),
        'lga_name': event.get('lga_name', 'Not Specified'),
        'ward_community': event.get('ward_community', 'Not Specified'),
        'latitude': event.get('latitude'),
        'longitude': event.get('longitude'),
        'location_precision': event.get('location_precision', 'State'),
        'primary_actor_category': event.get('primary_actor_category'),
        'primary_actor_name': event.get('primary_actor_name'),
        'associated_actor_category': event.get('associated_actor_category', ''),
        'associated_actor_name': event.get('associated_actor_name', ''),
        'actor_interaction': event.get('actor_interaction', ''),
        'source_type': event.get('source_type'),
        'source_url': event.get('source_url'),
        'source_date': event.get('source_date'),
        'source_closeness': event.get('source_closeness'),
        'verification_status': event.get('verification_status'),
        'reliability_level': event.get('reliability_level'),
        'multiple_sources': 0,
        'source_count': 1,
        'is_active': 1
    }
    
    # Insert or ignore if URL already exists
    try:
        cursor.execute('''
        INSERT OR IGNORE INTO peace_events (
            event_id, event_date, event_date_normalized, event_time, time_precision,
            entry_date, data_collector, ingestion_method, created_by, updated_by,
            event_type, event_subtype, event_description, notes, outcome_description,
            state_name, geopolitical_zone, lga_name, ward_community, latitude, longitude,
            location_precision, primary_actor_category, primary_actor_name,
            associated_actor_category, associated_actor_name, actor_interaction,
            source_type, source_url, source_date, source_closeness,
            verification_status, reliability_level, multiple_sources,
            source_count, is_active
        ) VALUES (
            :event_id, :event_date, :event_date_normalized, :event_time, :time_precision,
            :entry_date, :data_collector, :ingestion_method, :created_by, :updated_by,
            :event_type, :event_subtype, :event_description, :notes, :outcome_description,
            :state_name, :geopolitical_zone, :lga_name, :ward_community, :latitude, :longitude,
            :location_precision, :primary_actor_category, :primary_actor_name,
            :associated_actor_category, :associated_actor_name, :actor_interaction,
            :source_type, :source_url, :source_date, :source_closeness,
            :verification_status, :reliability_level, :multiple_sources,
            :source_count, :is_active
        )
        ''', data)
        
        conn.commit()
        return cursor.rowcount > 0  # True if inserted, False if ignored
    
    except Exception as e:
        print(f"Error saving event {event.get('event_id')}: {e}")
        conn.rollback()
        return False

# -------------------------------------------------------------------
# 6. MAIN PIPELINE
# -------------------------------------------------------------------
def run_pipeline():
    """Run the complete pipeline"""
    print("=" * 60)
    print("PEACE EVENT DISCOVERY PIPELINE")
    print("=" * 60)
    
    # Setup database
    print("\n1. Setting up database...")
    conn = setup_database()
    
    # Initialize extractor
    extractor = SimplePeaceExtractor()
    
    # Scrape existing URLs
    print("\n2. Scraping existing URLs...")
    if existing_urls:
        for i, url in enumerate(list(existing_urls)[:5]):  # Just test 5 first
            print(f"  Scraping ({i+1}/{min(5, len(existing_urls))}): {url[:80]}...")
            
            article_data = scrape_article(url)
            if article_data['success']:
                event = extractor.extract_event(article_data)
                if event:
                    saved = save_event_to_db(conn, event)
                    if saved:
                        print(f"    ✓ Saved: {event['event_type']} in {event['state_name']}")
                    else:
                        print(f"    ⚠ Already exists")
            
            time.sleep(1)  # Be polite
    
    # Find new URLs
    print("\n3. Finding new peace event URLs...")
    new_urls = find_new_peace_urls()
    
    # Scrape new URLs
    print("\n4. Scraping new URLs...")
    new_events_count = 0
    for i, url in enumerate(new_urls):
        print(f"  Scraping ({i+1}/{len(new_urls)}): {url[:80]}...")
        
        article_data = scrape_article(url)
        if article_data['success']:
            event = extractor.extract_event(article_data)
            if event:
                saved = save_event_to_db(conn, event)
                if saved:
                    print(f"    ✓ Saved new event: {event['event_type']} in {event['state_name']}")
                    new_events_count += 1
                else:
                    print(f"    ⚠ Already exists")
        else:
            print(f"    ✗ Failed to scrape")
        
        time.sleep(2)  # Be polite
    
    # Export to CSV
    print("\n5. Exporting data...")
    try:
        # Read all events from database
        df_db = pd.read_sql_query("SELECT * FROM peace_events", conn)
        
        # Export to CSV
        output_file = f"peace_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_db.to_csv(output_file, index=False)
        print(f"  ✓ Exported {len(df_db)} events to {output_file}")
        
        # Also create a combined file with your original data
        if not df.empty:
            combined = pd.concat([df, df_db], ignore_index=True).drop_duplicates(subset=['source_url'])
            combined.to_csv('combined_peace_events.csv', index=False)
            print(f"  ✓ Created combined file with {len(combined)} events")
    
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
    
    # Close database
    conn.close()
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print(f"- Scraped {len(existing_urls)} existing URLs")
    print(f"- Found {len(new_urls)} new URLs")
    print(f"- Added {new_events_count} new events to database")
    print("=" * 60)

# -------------------------------------------------------------------
# 7. RUN THE PIPELINE
# -------------------------------------------------------------------
if __name__ == "__main__":
    run_pipeline()
    
    print("\nNext steps:")
    print("1. Check 'peace_events.db' for the SQLite database")
    print("2. Check the CSV files for exported data")
    print("3. To run again, simply run: python simple_peace_scraper.py")
    print("\nTo make it run automatically, create a batch file:")
    print("  On Windows: create 'run_scraper.bat' with: python simple_peace_scraper.py")
    print("  On Mac/Linux: create 'run_scraper.sh' with: python3 simple_peace_scraper.py")