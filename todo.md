# NPAID Peace Scraper Expansion - Implementation Plan

## Overview
Expanding the NPAID peace data scraper to cover 28 domains identified in the domain analysis report. Current implementation: WANEP Nigeria (19.6% of data). Target: Add high-priority sources to increase coverage and reduce dependency on USIP (50%).

## Priority Tiers

### Tier 1: High Volume Sources (Implement First)
1. ✅ **wanep_nigeria** - COMPLETE (19.6% of dataset, 22 records)
2. **usip_org** - CRITICAL (50% of dataset, 56 records)
   - Research institution with extensive Nigeria peace data
   - Multiple publication types and formats

### Tier 2: Nigerian Media (Diversification Priority)
3. **leadership_ng** - Leadership Newspaper (2 records, but high potential)
4. **vanguardngr_com** - Vanguard News (1 record, major Nigerian outlet)
5. **punchng_com** - Punch Newspaper (1 record, major Nigerian outlet)
6. **thenationonlineng_net** - The Nation (1 record)
7. **dailypost_ng** - Daily Post Nigeria (1 record)
8. **thisdaylive_com** - ThisDay Live (1 record)
9. **businessday_ng** - BusinessDay (1 record)

### Tier 3: Government & Institutional Sources
10. **plateaupeacebuilding_org** - Plateau Peace Building (3 records)
11. **kdsg_gov_ng** - Kaduna State Government (2 records)
12. **ipcr_gov_ng** - Institute for Peace and Conflict Resolution (1 record)
13. **fmino_gov_ng** - Federal Ministry of Interior (1 record)

### Tier 4: International Organizations
14. **un_org** - United Nations (3 records)
15. **undp_org** - UNDP (2 records)
16. **karunacenter_org** - Karuna Center (2 records)
17. **crisisgroup_org** - International Crisis Group (1 record)
18. **kofiannanfoundation_org** - Kofi Annan Foundation (1 record)

### Tier 5: Specialized Sources
19. **reuters_com** - Reuters (1 record)
20. **idea_int** - International IDEA (1 record)
21. **cleen_org** - CLEEN Foundation (1 record)
22. **genocidewatch_com** - Genocide Watch (1 record)
23. **c_r_org** - Conciliation Resources (1 record)
24. **tandfonline_com** - Taylor & Francis Academic (1 record)
25. **giz_de** - GIZ Germany (1 record)
26. **nigeria_iom_int** - IOM Nigeria (1 record)
27. **progressivenews_ng** - Progressive News (1 record)
28. **dailynewspulse_wordpress_com** - Daily News Pulse Blog (1 record)

## Implementation Strategy

### Phase 1: Foundation (Tier 1)
- Implement USIP scraper with multiple content type handling
- Test and validate against existing 56 records

### Phase 2: Media Expansion (Tier 2)
- Implement 7 Nigerian news site scrapers
- Focus on news article extraction and keyword matching
- Standardized approach for Nigerian media sites

### Phase 3: Government & Institutional (Tier 3)
- Implement 4 government/institutional scrapers
- Handle official press releases and reports

### Phase 4: International & Specialized (Tiers 4-5)
- Implement remaining 14 sources
- Lower priority but important for comprehensive coverage

## Technical Approach

### Scraper Components (Per Domain)
Each domain folder contains:
```
scrapers/{domain_name}/
├── __init__.py          # Package marker
├── config.yml           # Configuration (states, keywords, crawling settings)
└── scraper.py           # Main scraping logic
```

### Common Features
- **Keyword Matching**: peace dialogue, conflict resolution, peacebuilding, mediation, reconciliation, violence prevention, early warning, peace agreement, peace training, peace initiative
- **State Filtering**: Kaduna, Katsina, Benue, Plateau (pilot states)
- **Event Classification**: Peace Actions, Peace Programmes, Peace Dialogues, Conflict Mediation, Training, Early Warning, Peace Agreements
- **Actor Extraction**: CSOs, Government, Community-Based, International
- **Deduplication**: SHA256 hash-based using EVENT_ID
- **GCP Integration**: Cloud Storage (Parquet), Pub/Sub (error notifications)

### Crawling Strategies by Source Type

#### Research/Institutional Sites (USIP, Crisis Group, etc.)
- Publication listings with pagination
- Individual article/report pages
- PDF document handling
- Date-based filtering

#### News Sites (Leadership, Vanguard, Punch, etc.)
- News article listings
- Category/tag filtering (peace, conflict, security)
- Article detail pages
- Date archives

#### Government Sites (KDSG, IPCR, FMINO)
- Press release sections
- Event announcements
- Program pages
- Static content handling

#### NGO/CSO Sites (WANEP, Karuna, CLEEN)
- Project pages
- News/updates sections
- Event calendars
- Program descriptions

## Data Schema Compliance
All scrapers must output:
```python
{
    "EVENT_ID": "SHA256 hash",
    "EVENT_TITLE": str,
    "EVENT_TYPE": str,  # Peace Actions/Programmes/Dialogues/etc.
    "EVENT_SUBTYPE": str,
    "ORGANIZATION": str,
    "STATE": str,  # Kaduna/Katsina/Benue/Plateau
    "LGA": str,
    "LOCATION_DETAILS": str,
    "DATE_POSTED": "YYYY-MM-DD",
    "EVENT_DATE": "YYYY-MM-DD",
    "EVENT_URL": str,
    "SOURCE_DOMAIN": str,
    "DESCRIPTION": str,
    "OUTCOME": str,
    "PRIMARY_ACTOR": str,
    "ASSOCIATED_ACTOR": str,
    "ACTOR_INTERACTION": str,
    "SOURCE_TYPE": str,
    "INGESTION_DATE": "YYYY-MM-DD",
    "VERIFICATION_STATUS": str,
    "GEOPOLITICAL_ZONE": str
}
```

## Extended Peace Keywords Dictionary
```yaml
primary_keywords:
  - peace dialogue
  - conflict resolution
  - peacebuilding
  - peace building
  - community mediation
  - reconciliation
  - violence prevention
  - early warning
  - peace agreement
  - peace training
  - peace initiative
  - peace action
  - peace programme
  - peace program

secondary_keywords:
  - conflict management
  - dispute resolution
  - community dialogue
  - interfaith dialogue
  - peace education
  - peace advocacy
  - conflict prevention
  - peace negotiation
  - peace accord
  - ceasefire
  - peace process
  - peace talks
  - peace summit
  - peace forum
  - peace workshop

actor_keywords:
  cso: [civil society, ngo, organization, network, foundation, initiative]
  government: [government, ministry, commission, state, federal, local government]
  community: [community, youth, women, elders, traditional, religious leaders]
  international: [un, undp, usaid, eu, international, multilateral]
  security: [police, military, security, army]

location_indicators:
  - kaduna
  - katsina
  - benue
  - plateau
  - north west
  - north central
  - lga
  - local government
  - community
  - village
  - ward
```

## Testing & Validation
- [ ] Each scraper tested locally before deployment
- [ ] Verify data schema compliance
- [ ] Check deduplication logic
- [ ] Validate state extraction
- [ ] Test GCP upload functionality
- [ ] Monitor error notifications via Pub/Sub

## Deployment Checklist
- [ ] Docker build for each scraper
- [ ] GCP Container Registry push
- [ ] Cloud Run/Cloud Functions deployment
- [ ] Cloud Scheduler setup (daily runs)
- [ ] Monitoring dashboard configuration
- [ ] Error alerting ssetup

## Success Metrics
- Reduce USIP dependency from 50% to <30%
- Increase Nigerian media coverage from 9.8% to >25%
- Add 15+ new active sources
- Achieve 200+ peace events per month
- Maintain >90% data quality score