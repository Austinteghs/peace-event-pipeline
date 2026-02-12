"""
Parallel processing utilities
Handles running multiple scrapers concurrently
"""

import asyncio
import concurrent.futures
from typing import List, Callable
from .logger import logger


def run_scrapers_parallel(scraper_functions: List[Callable], max_workers: int = 4):
    """
    Run multiple scraper functions in parallel using ThreadPoolExecutor
    
    Args:
        scraper_functions: List of scraper main() functions to run
        max_workers: Maximum number of concurrent workers
        
    Returns:
        List of results from each scraper
    """
    logger.info(f"Starting parallel execution of {len(scraper_functions)} scrapers with {max_workers} workers")
    
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scraper functions
        future_to_scraper = {
            executor.submit(func): func.__name__ 
            for func in scraper_functions
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_scraper):
            scraper_name = future_to_scraper[future]
            try:
                result = future.result()
                results.append({
                    'scraper': scraper_name,
                    'status': 'success',
                    'result': result
                })
                logger.info(f"✓ {scraper_name} completed successfully")
            except Exception as e:
                results.append({
                    'scraper': scraper_name,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"✗ {scraper_name} failed: {e}")
    
    # Summary
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    logger.info(f"Parallel execution complete: {successful} succeeded, {failed} failed")
    
    return results


async def run_scrapers_async(scraper_coroutines: List):
    """
    Run multiple async scraper coroutines concurrently
    
    Args:
        scraper_coroutines: List of async scraper coroutines
        
    Returns:
        List of results from each scraper
    """
    logger.info(f"Starting async execution of {len(scraper_coroutines)} scrapers")
    
    results = await asyncio.gather(*scraper_coroutines, return_exceptions=True)
    
    # Process results
    processed_results = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                'scraper': f'scraper_{idx}',
                'status': 'error',
                'error': str(result)
            })
            logger.error(f"✗ Scraper {idx} failed: {result}")
        else:
            processed_results.append({
                'scraper': f'scraper_{idx}',
                'status': 'success',
                'result': result
            })
            logger.info(f"✓ Scraper {idx} completed successfully")
    
    successful = sum(1 for r in processed_results if r['status'] == 'success')
    failed = len(processed_results) - successful
    
    logger.info(f"Async execution complete: {successful} succeeded, {failed} failed")
    
    return processed_results