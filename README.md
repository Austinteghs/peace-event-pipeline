# NPAID Peace Events Scraper System

A modular web scraping system for collecting peace events data from Nigerian sources, built following Data2Bots' job scraper architecture.

## 🎯 Project Overview

This scraper system collects peace events data for the Nigerian Peace Actions and Initiatives Database (NPAID) project, focusing on four pilot states:
- **Kaduna**
- **Katsina**
- **Benue**
- **Plateau**

## 📊 Data Schema

Each peace event record contains:

```python
{
    "EVENT_ID": "SHA256 hash",
    "EVENT_TITLE": "Event title",
    "EVENT_TYPE": "Peace Actions/Programmes/Dialogues/etc.",
    "EVENT_SUBTYPE": "Specific subtype",
    "ORGANIZATION": "Organizing entity",
    "STATE": "Nigerian state",
    "LGA": "Local Government Area",
    "LOCATION_DETAILS": "Detailed location",
    "DATE_POSTED": "YYYY-MM-DD",
    "EVENT_DATE": "YYYY-MM-DD",
    "EVENT_URL": "Source URL",
    "SOURCE_DOMAIN": "Domain name",
    "DESCRIPTION": "Event description",
    "OUTCOME": "Event outcome/results",
    "PRIMARY_ACTOR": "Main actor category",
    "ASSOCIATED_ACTOR": "Associated actor category",
    "ACTOR_INTERACTION": "Actor relationship",
    "SOURCE_TYPE": "Source category",
    "INGESTION_DATE": "YYYY-MM-DD",
    "VERIFICATION_STATUS": "Verified/Pending/Unverified",
    "GEOPOLITICAL_ZONE": "Nigerian geopolitical zone"
}
```

## 🏗️ Architecture

### Project Structure
```
npaid-peace-scraper/
├── scrapers/
│   ├── utils.py                 # Shared utilities
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Container configuration
│   ├── start.sh                # Startup script
│   ├── wanep_nigeria/          # WANEP Nigeria scraper
│   │   ├── scraper.py
│   │   ├── config.yml
│   │   └── __init__.py
│   ├── usip_org/               # USIP scraper (to be added)
│   ├── leadership_ng/          # Leadership News scraper (to be added)
│   └── ... (other sources)
├── .github/
│   └── workflows/
│       └── scraper-deploy.yml  # CI/CD pipeline
└── README.md
```

### Key Components

1. **utils.py**: Centralized utilities
   - Browser automation (Pyppeteer/Playwright)
   - S3 upload/download
   - Hash-based deduplication
   - Data validation with Pydantic
   - State/location extraction
   - SNS error notifications

2. **Individual Scrapers**: Modular design
   - Each source has its own folder
   - `scraper.py`: Main scraping logic
   - `config.yml`: Configuration parameters
   - Independent execution

3. **Data Pipeline**:
   - Scrape → Validate → Deduplicate → Store (S3/Local)
   - Hash-based deduplication prevents duplicates
   - Parquet format for efficient storage

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.10+
python --version

# Docker (for containerized deployment)
docker --version

# Azure CLI (for Azure deployment)
az --version
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
S3BUCKET=your-s3-bucket
HASH_PATH=peace_events/wanep_nigeria/hash.csv
SNS_ARN_DEVELOPERS=your-sns-arn
SNS_ARN_BUSINESS=your-sns-arn
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
EOF
```

4. **Run a scraper locally**
```bash
# Run WANEP Nigeria scraper
python wanep_nigeria/scraper.py

# Output will be saved to scrapers/data/ directory
```

### Docker Deployment

1. **Build Docker image**
```bash
cd scrapers
docker build \
  --build-arg SCRAPER_FOLDER=wanep_nigeria \
  --build-arg SCRAPER_METHOD=PUPPET \
  -t npaid-wanep-scraper:latest \
  .
```

2. **Run container**
```bash
docker run \
  -e ENV=prod \
  -e S3BUCKET=your-bucket \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  npaid-wanep-scraper:latest
```

## ☁️ Azure Deployment

### Setup Azure Resources

1. **Create Resource Group**
```bash
az group create \
  --name npaid-peace-scrapers-rg \
  --location eastus
```

2. **Create Container Registry**
```bash
az acr create \
  --resource-group npaid-peace-scrapers-rg \
  --name npaidregistry \
  --sku Basic
```

3. **Create S3 Bucket** (AWS)
```bash
aws s3 mb s3://npaid-peace-events-data
```

4. **Create SNS Topics** (AWS)
```bash
aws sns create-topic --name npaid-scraper-errors-dev
aws sns create-topic --name npaid-scraper-errors-business
```

### GitHub Actions CI/CD

1. **Configure GitHub Secrets**
   - `AZURE_CREDENTIALS`: Azure service principal JSON
   - `ACR_USERNAME`: Azure Container Registry username
   - `ACR_PASSWORD`: Azure Container Registry password
   - `AWS_ACCESS_KEY_ID`: AWS access key
   - `AWS_SECRET_ACCESS_KEY`: AWS secret key
   - `S3_BUCKET`: S3 bucket name
   - `SNS_ARN_DEVELOPERS`: SNS topic ARN for developers
   - `SNS_ARN_BUSINESS`: SNS topic ARN for business team

2. **Deploy via GitHub Actions**
   - Push to `main` branch triggers automatic deployment
   - Or manually trigger via Actions tab

3. **Schedule Scrapers**
```bash
# Create Azure Logic App or use cron jobs
az container create \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep-daily-scraper \
  --image npaidregistry.azurecr.io/wanep_nigeria:latest \
  --restart-policy OnFailure \
  --schedule "0 2 * * *"  # Run daily at 2 AM
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
    # ... more keywords
  
  event_types:
    - Peace Actions
    - Peace Programmes
    # ... more types
  
  other_params:
    - backfill: 'yyyy-mm-dd'  # or '2024-01-01' or ['2024-01-01', '2024-01-02']
    - rerun: 'yyyy-mm-dd'      # or '2024-01-01:2024-01-31' for date range
```

### Date Parameters

- `yyyy-mm-dd`: No action (scrape today)
- `2024-06-21`: Single date
- `['2024-06-21', '2024-06-23']`: Multiple specific dates
- `2024-06-21:2024-06-28`: Date range

## 🔍 Adding New Scrapers

To add a new source (e.g., Leadership News):

1. **Create scraper folder**
```bash
mkdir -p scrapers/leadership_ng
```

2. **Create files**
```bash
touch scrapers/leadership_ng/__init__.py
touch scrapers/leadership_ng/scraper.py
touch scrapers/leadership_ng/config.yml
```

3. **Implement scraper.py**
   - Follow the WANEP Nigeria template
   - Import utilities from `utils.py`
   - Implement source-specific scraping logic
   - Use hash-based deduplication

4. **Configure config.yml**
   - Set target states
   - Define search keywords
   - Configure backfill/rerun parameters

5. **Test locally**
```bash
python leadership_ng/scraper.py
```

6. **Deploy**
   - Push to GitHub
   - GitHub Actions will build and deploy

## 📊 Data Output

### Local Development
- CSV files saved to `scrapers/data/`
- Hash file: `scrapers/hash.csv`

### Production
- Parquet files uploaded to S3: `s3://bucket/peace_events/{source}/{date}/`
- Hash file: `s3://bucket/peace_events/{source}/hash.csv`

## 🛠️ Priority Sources to Implement

Based on domain analysis:

**Tier 1 (High Volume):**
- ✅ WANEP Nigeria (19.6% of current data)
- ⬜ USIP.org (50% of current data)

**Tier 2 (Nigerian Media):**
- ⬜ leadership.ng
- ⬜ vanguardngr.com
- ⬜ punchng.com
- ⬜ thenationonlineng.net
- ⬜ dailypost.ng

**Tier 3 (Government/Institutional):**
- ⬜ kdsg.gov.ng (Kaduna State)
- ⬜ ipcr.gov.ng
- ⬜ plateaupeacebuilding.org

## 🐛 Troubleshooting

### Common Issues

1. **Browser automation fails**
   - Ensure Chromium is installed
   - Check `SCRAPER_METHOD` build arg (DRIVER vs PUPPET)

2. **S3 upload fails**
   - Verify AWS credentials
   - Check S3 bucket permissions

3. **No events found**
   - Check date_list configuration
   - Verify website structure hasn't changed
   - Enable troubleshooting logs

4. **Duplicate events**
   - Hash file may be corrupted
   - Check hash generation logic

## 📈 Monitoring

- **Logs**: Check container logs in Azure Portal
- **SNS Notifications**: Error alerts sent to configured SNS topics
- **S3 Data**: Monitor parquet file creation dates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your scraper following the template
4. Test locally
5. Submit pull request

## 📄 License

[Add your license information]

## 👥 Team

Data2Bots - NPAID Project Team

## 📞 Support

For issues or questions:
- Create GitHub issue
- Contact: [your-email@data2bots.com]