"""
Constants used across all scrapers
"""

import os

# Environment
ENV_PROD = os.environ.get("ENV", "dev") == "prod"

# Nigerian States
PILOT_STATES = ["Kaduna", "Katsina", "Benue", "Plateau"]

NIGERIAN_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue",
    "Borno", "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu",
    "Gombe", "Imo", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi",
    "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo",
    "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara", "FCT"
]

# Geopolitical Zones
GEOPOLITICAL_ZONES = {
    "North West": ["Kaduna", "Kano", "Katsina", "Kebbi", "Sokoto", "Zamfara", "Jigawa"],
    "North East": ["Adamawa", "Bauchi", "Borno", "Gombe", "Taraba", "Yobe"],
    "North Central": ["Benue", "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "FCT"],
    "South West": ["Ekiti", "Lagos", "Ogun", "Ondo", "Osun", "Oyo"],
    "South East": ["Abia", "Anambra", "Ebonyi", "Enugu", "Imo"],
    "South South": ["Akwa Ibom", "Bayelsa", "Cross River", "Delta", "Edo", "Rivers"]
}

# Pub/Sub Topics
PUBSUB_TOPIC_DEVELOPERS = os.environ.get("PUBSUB_TOPIC_DEVELOPERS", "npaid-scraper-errors-dev")
PUBSUB_TOPIC_BUSINESS = os.environ.get("PUBSUB_TOPIC_BUSINESS", "npaid-scraper-errors-business")