#!/usr/bin/env python3
"""
LOOOOK Pool Refresh - Fetches all images from Pinterest and regenerates the HTML grid.
"""
import json
import re
import sys
import os
from pathlib import Path
from typing import List, Dict
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PoolRefresher:
    def __init__(self, board_url: str, html_file: str):
        self.board_url = board_url
        self.html_file = Path(html_file)
        self.fetcher_script = Path(__file__).parent / 'pinterest_fetcher.py'

    def run(self, dry_run: bool = False) -> bool:
        logger.info("LOOOOK Pool Refresh Started")
        logger.info(f"  Board: {self.board_url}")
        logger.info(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")

        # Fetch images
        logger.info("[1/3] Fetching all images from Pinterest...")
        try:
            result = subprocess.run(
                ['python3', str(self.fetcher_script), '--board-url', self.board_url, '--output', 'images.json'],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Fetcher failed: {result.stderr}")
                return False

            with open('images.json', 'r') as f:
                images = json.load(f)
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return False

        logger.info(f"Fetched {len(images)} images")

        # Process to POOL format
        logger.info("[2/3] Processing into POOL format...")
        pool = []
        for idx, img in enumerate(images):
            cycle = idx % 10
            size = 'l' if cycle < 3 else ('m' if cycle < 7 else 's')
            pool.append({
                'src': img['src'],
                'size': size,
                'category': img.get('category', 'inspiration'),
                'alt': img.get('alt', 'LOOOOK mood board')
            })
        logger.info(f"Processed {len(pool)} images")

        # Update HTML
        logger.info("[3/3] Updating HTML...")
        try:
            html = self.html_file.read_text(encoding='utf-8')

            items = []
            for img in pool:
                items.append(f'''    {{
        src: "{img['src']}",
        size: "{img['size']}",
        category: "{img['category']}",
        alt: "{img['alt']}"
    }}''')

            pool_js = f"""const POOL = [
{',' .join(items)}
];"""

            new_html = re.sub(r'const POOL = \[[\s\S]*?\];', pool_js, html)

            if not dry_run:
                self.html_file.write_text(new_html, encoding='utf-8')
                logger.info(f"Wrote {self.html_file}")
            else:
                logger.info("DRY RUN - skipping write")
        except Exception as e:
            logger.error(f"HTML error: {e}")
            return False

        logger.info("Pool refresh complete!")
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Refresh LOOOOK pool')
    parser.add_argument('--board-url', help='Pinterest board URL')
    parser.add_argument('--html-file', default='index.html', help='Path to index.html')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()

    board_url = args.board_url or os.getenv('PINTEREST_BOARD_URL')
    if not board_url:
        logger.error("Pinterest board URL required")
        sys.exit(1)

    refresher = PoolRefresher(board_url, args.html_file)
    success = refresher.run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
