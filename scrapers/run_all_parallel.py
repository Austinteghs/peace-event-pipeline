"""
Run all scrapers in parallel
Entry point for parallel execution of multiple scrapers
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import run_scrapers_parallel, logger, ENV_PROD

# Import scraper main functions
from usip_org.scraper import main as usip_main
from leadership_ng.scraper import main as leadership_main
from vanguardngr_com.scraper import main as vanguard_main
from plateaupeacebuilding_org.scraper import main as plateau_main
from wanep_nigeria.scraper import main as wanep_main


def main():
    """
    Run all scrapers in parallel
    """
    logger.info("=" * 80)
    logger.info("NPAID PEACE SCRAPERS - PARALLEL EXECUTION")
    logger.info("=" * 80)
    logger.info(f"Environment: {'PRODUCTION' if ENV_PROD else 'DEVELOPMENT'}")
    
    # List of scraper functions to run
    scrapers = [
        usip_main,
        leadership_main,
        vanguard_main,
        plateau_main,
        wanep_main
    ]
    
    # Run scrapers in parallel (max 3 concurrent to be respectful to websites)
    results = run_scrapers_parallel(scrapers, max_workers=3)
    
    # Print summary
    logger.info("=" * 80)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 80)
    
    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        logger.info(f"{status_icon} {result['scraper']}: {result['status']}")
        if result['status'] == 'error':
            logger.error(f"  Error: {result['error']}")
    
    successful = sum(1 for r in results if r['status'] == 'success')
    total = len(results)
    
    logger.info("=" * 80)
    logger.info(f"FINAL RESULT: {successful}/{total} scrapers completed successfully")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nExecution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)