# NPAID Peace Events Scraper System - Updated

## 🎯 Project Overview

This scraper system collects peace events data for the Nigerian Peace Actions and Initiatives Database (NPAID) project. Based on comprehensive domain analysis of 112 existing records across 28 sources, this system prioritizes high-value sources and diversifies data collection beyond the current USIP dependency (50% of data).

### Current Implementation Status

**✅ Implemented (5 scrapers covering ~72% of existing data):**
1. **wanep_nigeria** - WANEP Nigeria (19.6%, 22 records) - COMPLETE
2. **usip_org** - USIP (50%, 56 records) - NEW
3. **leadership_ng** - Leadership Newspaper (1.8%, 2 records) - NEW
4. **vanguardngr_com** - Vanguard News (0.9%, 1 record) - NEW
5. **plateaupeacebuilding_org** - Plateau Peace Building (2.7%, 3 records) - NEW

**⬜ To Be Implemented (23 scrapers):**
- 6 Nigerian media outlets
- 3 government agencies
- 8 international organizations
- 6 specialized sources

## 📊 Data Schema

Each peace event record contains 21 fields:

```python
{
    "EVENT_ID": "SHA256 hash",              # Unique identifier
    "EVENT_TITLE": str,                     # Event title
    "EVENT_TYPE": str,                      # Peace Actions/Programmes/Dialogues/etc.
    "EVENT_SUBTYPE": str,                   # Specific subtype
    "ORGANIZATION": str,                    # Organizing entity
    "STATE": str,                           # Kaduna/Katsina/Benue/Plateau
    "LGA": str,                             # Local Government Area
    "LOCATION_DETAILS": str,                # Detailed location
    "DATE_POSTED": "YYYY-MM-DD",           # Publication date
    "EVENT_DATE": "YYYY-MM-DD",            # Event occurrence date
    "EVENT_URL": str,                       # Source URL
    "SOURCE_DOMAIN": str,                   # Domain name
    "DESCRIPTION": str,                     # Event description (max 500 chars)
    "OUTCOME": str,                         # Event outcome/results
    "PRIMARY_ACTOR": str,                   # Main actor category
    "ASSOCIATED_ACTOR": str,                # Associated actor category
    "ACTOR_INTERACTION": str,               # Actor relationship
    "SOURCE_TYPE": str,                     # Source category
    "INGESTION_DATE": "YYYY-MM-DD",        # Data collection date
    "VERIFICATION_STATUS": str,             # Verified/Pending/Unverified
    "GEOPOLITICAL_ZONE": str               # North West/North Central
}
```

## 🏗️ Architecture

### Project Structure
```
npaid-peace-scraper/
├── scrapers/
│   ├── utils.py                          # Shared utilities (GCP integration)
│   ├── requirements.txt                  # Python dependencies
│   ├── Dockerfile                        # Container configuration
│   ├── start.sh                          # Startup script
│   │
│   ├── wanep_nigeria/                    # ✅ COMPLETE
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   │
│   ├── usip_org/                         # ✅ NEW
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   │
│   ├── leadership_ng/                    # ✅ NEW
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   │
│   ├── vanguardngr_com/                  # ✅ NEW
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   │
│   ├── plateaupeacebuilding_org/         # ✅ NEW
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   │
│   └── ... (23 more to be implemented)
│
├── todo.md                                # Implementation roadmap
├── SCRAPERS_IMPLEMENTATION_GUIDE.md      # Detailed implementation guide
├── DEPLOYMENT_GUIDE.md                   # GCP deployment instructions
└── README.md                             # This file
```

### Key Components

1. **utils.py**: Centralized utilities (GCP Version)
   - Browser automation (Pyppeteer/Playwright)
   - Google Cloud Storage upload/download
   - Pub/Sub error notifications
   - Hash-based deduplication
   - Data validation with Pydantic
   - State/location extraction
   - Nigerian states and geopolitical zones

2. **Individual Scrapers**: Modular design
   - Each source has its own folder
   - `scraper.py`: Main scraping logic
   - `config.yml`: Configuration parameters
   - Independent execution

3. **Data Pipeline**:
   - Scrape → Validate → Deduplicate → Store (GCS/Local)
   - Hash-based deduplication prevents duplicates
   - Parquet format for efficient storage in GCS

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.10+
python --version

# Docker (for containerized deployment)
docker --version

# Google Cloud SDK (for GCP deployment)
gcloud --version
```

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd npaid-peace-scraper
```

2. **Install dependencies**
```bash
cd scrapers
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Create .env file
cat > .env << EOF
ENV=dev
GCS_BUCKET=your-gcs-bucket
HASH_PATH=peace_events/hash.csv
PUBSUB_TOPIC_DEVELOPERS=your-pubsub-topic
PUBSUB_TOPIC_BUSINESS=your-pubsub-topic
GCP_PROJECT_ID=your-project-id
EOF
```

4. **Run a scraper locally**
```bash
# Run WANEP Nigeria scraper
python wanep_nigeria/scraper.py

# Run USIP scraper
python usip_org/scraper.py

# Run Leadership News scraper
python leadership_ng/scraper.py

# Output will be saved to scrapers/data/ directory
```

### Docker Deployment

1. **Build Docker image**
```bash
cd scrapers
docker build \
  --build-arg SCRAPER_FOLDER=usip_org \
  --build-arg SCRAPER_METHOD=PUPPET \
  -t npaid-usip-scraper:latest \
  .
```

2. **Run container**
```bash
docker run \
  -e ENV=prod \
  -e GCS_BUCKET=your-bucket \
  -e GCP_PROJECT_ID=your-project \
  npaid-usip-scraper:latest
```

## ☁️ GCP Deployment

### Setup GCP Resources

1. **Create Resource Group**
```bash
gcloud projects create npaid-peace-scrapers
gcloud config set project npaid-peace-scrapers
```

2. **Create Cloud Storage Bucket**
```bash
gsutil mb gs://npaid-peace-events-data
```

3. **Create Pub/Sub Topics**
```bash
gcloud pubsub topics create npaid-scraper-errors-dev
gcloud pubsub topics create npaid-scraper-errors-business
```

4. **Enable Required APIs**
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable storage.googleapis.com
```

### Deploy Scrapers to Cloud Run

```bash
# Build and deploy USIP scraper
gcloud builds submit --tag gcr.io/npaid-peace-scrapers/usip-scraper \
  --build-arg SCRAPER_FOLDER=usip_org

gcloud run deploy usip-scraper \
  --image gcr.io/npaid-peace-scrapers/usip-scraper \
  --platform managed \
  --region us-central1 \
  --set-env-vars ENV=prod,GCS_BUCKET=npaid-peace-events-data,GCP_PROJECT_ID=npaid-peace-scrapers

# Schedule daily runs
gcloud scheduler jobs create http usip-daily \
  --schedule="0 2 * * *" \
  --uri="https://usip-scraper-xxxxx.run.app" \
  --http-method=POST
```

## 📝 Configuration

### config.yml Structure

```yaml
parameters:
  dynamic_params:
  - states:
    - Kaduna
    - Katsina
    - Benue
    - Plateau
    first_run: false
  
  search_keywords:
    - peace dialogue
    - conflict resolution
    - peacebuilding
    # ... more keywords
  
  event_types:
    - Peace Actions
    - Peace Programmes
    - Peace Dialogues
    # ... more types
  
  # Web Crawling Configuration
  crawling:
    enabled: true
    max_pages: 20
    delay_seconds: 2
    follow_article_links: true
  
  other_params:
    - backfill: 'yyyy-mm-dd'
    - rerun: 'yyyy-mm-dd'
```

### Date Parameters

- `yyyy-mm-dd`: No action (scrape today)
- `2024-06-21`: Single date
- `['2024-06-21', '2024-06-23']`: Multiple specific dates
- `2024-06-21:2024-06-28`: Date range

## 🔍 Adding New Scrapers

See `SCRAPERS_IMPLEMENTATION_GUIDE.md` for detailed instructions.

Quick steps:

1. **Create scraper folder**
```bash
mkdir -p scrapers/{source_name}
cd scrapers/{source_name}
touch __init__.py config.yml scraper.py
```

2. **Use existing scraper as template**
   - News sites: `leadership_ng/scraper.py`
   - Research: `usip_org/scraper.py`
   - Government: `plateaupeacebuilding_org/scraper.py`
   - NGO: `wanep_nigeria/scraper.py`

3. **Test locally**
```bash
python scraper.py
```

4. **Deploy to GCP**
```bash
gcloud builds submit --tag gcr.io/{project}/scraper
gcloud run deploy scraper --image gcr.io/{project}/scraper
```

## 📊 Data Output

### Local Development
- CSV files saved to `scrapers/data/`
- Hash file: `scrapers/hash.csv`
- Format: `{source}_peace_events_{timestamp}.csv`

### Production (GCP)
- Parquet files uploaded to GCS: `gs://bucket/peace_events/{source}/{date}/data.parquet`
- Hash file: `gs://bucket/peace_events/{source}/hash.csv`
- Automatic deduplication via EVENT_ID

## 🛠️ Implementation Priorities

### Phase 1: Foundation (COMPLETE)
- ✅ WANEP Nigeria scraper
- ✅ USIP scraper (highest volume source)

### Phase 2: Media Expansion (IN PROGRESS)
- ✅ Leadership News
- ✅ Vanguard News
- ⬜ Punch Newspaper
- ⬜ The Nation
- ⬜ Daily Post
- ⬜ ThisDay Live
- ⬜ BusinessDay

### Phase 3: Government & Institutional (STARTED)
- ✅ Plateau Peace Building
- ⬜ Kaduna State Government
- ⬜ IPCR
- ⬜ Federal Ministry of Interior

### Phase 4: International & Specialized
- ⬜ UN, UNDP, Karuna Center, Crisis Group
- ⬜ Reuters, CLEEN, Genocide Watch
- ⬜ Academic sources

## 🐛 Troubleshooting

### Common Issues

1. **Browser automation fails**
   - Ensure Chromium is installed
   - Check `SCRAPER_METHOD` build arg (DRIVER vs PUPPET)

2. **GCS upload fails**
   - Verify GCP credentials
   - Check Cloud Storage bucket permissions
   - Ensure service account has Storage Object Creator role

3. **No events found**
   - Check date_list configuration
   - Verify website structure hasn't changed
   - Enable troubleshooting logs (ENV=dev)

4. **Duplicate events**
   - Hash file may be corrupted
   - Check hash generation logic
   - Verify EVENT_ID uniqueness

## 📈 Monitoring

- **Logs**: Cloud Logging for Cloud Run services
- **Pub/Sub Notifications**: Error alerts sent to configured topics
- **GCS Data**: Monitor parquet file creation dates and sizes
- **Metrics**: Track events per source, success rates, error rates

## 📄 Extended Peace Keywords Dictionary

The system uses an extensive keyword dictionary for identifying peace-related content:

**Primary Keywords:**
peace dialogue, conflict resolution, peacebuilding, community mediation, reconciliation, violence prevention, early warning, peace agreement, peace training, peace initiative

**Secondary Keywords:**
conflict management, dispute resolution, interfaith dialogue, peace education, peace advocacy, conflict prevention, peace negotiation, peace accord, ceasefire, peace process

**Actor Keywords:**
- CSO: civil society, ngo, organization, network, foundation
- Government: ministry, commission, state, federal, local government
- Community: youth, women, elders, traditional leaders, religious leaders
- International: un, undp, usaid, eu, multilateral

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your scraper following the template
4. Test locally and with Docker
5. Submit pull request with documentation

## 📞 Support

For issues or questions:
- Create GitHub issue
- Check `SCRAPERS_IMPLEMENTATION_GUIDE.md`
- Review existing scraper implementations
- Contact: Data2Bots NPAID Team

## 📚 Additional Resources

- **Domain Analysis Report**: See project documentation
- **PRD**: NPAID Platform Comprehensive Product Requirements Document
- **Implementation Guide**: `SCRAPERS_IMPLEMENTATION_GUIDE.md`
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md`
- **TODO**: `todo.md` for roadmap and priorities

---

**Last Updated**: February 2024
**Version**: 2.0 (5 scrapers implemented, 23 pending)
**Coverage**: ~72% of existing data sources