#!/usr/bin/env python3
"""
LOOOOK Pool Refresh - Fetches images from Pinterest + archive,
adds 15 new images to existing POOL in index.html.
"""
import json
import re
import sys
import os
import random
from pathlib import Path
from typing import List, Dict
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_NEW_IMAGES = 15


class PoolRefresher:
        def __init__(self, board_url: str, archive_url: str, html_file: str):
                    self.board_url = board_url
                    self.archive_url = archive_url
                    self.html_file = Path(html_file)
                    self.scripts_dir = Path(__file__).parent

        def _fetch_pinterest(self) -> List[Dict]:
                    try:
                                    result = subprocess.run(
                                                        ['python3', str(self.scripts_dir / 'pinterest_fetcher.py'),
                                                                          '--board-url', self.board_url, '--output', 'pinterest_imgs.json'],
                                                        capture_output=True, text=True, timeout=300
                                    )
                                    if result.returncode != 0:
                                                        logger.error(f"Pinterest fetch failed: {result.stderr}")
                                                        return []
                                                    with open('pinterest_imgs.json', 'r') as f:
                                                                        imgs = json.load(f)
                                                                    for img in imgs:
                                                                                        img['source'] = 'pinterest'
                                                                                    return imgs
except Exception as e:
            logger.error(f"Pinterest error: {e}")
            return []

    def _fetch_archive(self) -> List[Dict]:
                try:
                                result = subprocess.run(
                                                    ['python3', str(self.scripts_dir / 'archive_fetcher.py'),
                                                                      '--url', self.archive_url, '--output', 'archive_imgs.json'],
                                                    capture_output=True, text=True, timeout=120
                                )
                                if result.returncode != 0:
                                                    logger.error(f"Archive fetch failed: {result.stderr}")
                                                    return []
                                                with open('archive_imgs.json', 'r') as f:
                                                                    imgs = json.load(f)
                                                                for img in imgs:
                                                                                    img['source'] = 'archive'
                                                                                return imgs
except Exception as e:
            logger.error(f"Archive error: {e}")
            return []

    def _get_existing_pool(self) -> List[Dict]:
                html = self.html_file.read_text(encoding='utf-8')
                match = re.search(r'const POOL = \[([\s\S]*?)\];', html)
                if not match:
                                return []
                            pool_str = match.group(1)
        existing_srcs = re.findall(r'src:\s*"([^"]+)"', pool_str)
        existing_metas = re.findall(r'meta:\s*"([^"]+)"', pool_str)
        existing_sizes = re.findall(r'size:\s*"([^"]+)"', pool_str)
        pool = []
        for i in range(len(existing_srcs)):
                        pool.append({
                                            'src': existing_srcs[i],
                                            'meta': existing_metas[i] if i < len(existing_metas) else f'REF_{i:03d}',
                                            'size': existing_sizes[i] if i < len(existing_sizes) else 'm'
                        })
                    return pool

    def _get_next_pull_number(self, existing: List[Dict]) -> int:
                max_num = 0
        for item in existing:
                        m = re.search(r'(\d+)$', item.get('meta', ''))
                        if m:
                                            max_num = max(max_num, int(m.group(1)))
                                    return max_num + 1

    def _assign_meta(self, img: Dict, idx: int, source: str) -> str:
                if source == 'pinterest':
                                return f"REF_PINTEREST_BOARD_{random.randint(1,3)}_{idx:03d}"
else:
            return f"REF_DAILY_PULL_{idx:03d}"

    def run(self, dry_run: bool = False) -> bool:
                logger.info("LOOOOK Pool Refresh Started")
        logger.info(f"  Pinterest: {self.board_url}")
        logger.info(f"  Archive: {self.archive_url}")

        existing_pool = self._get_existing_pool()
        existing_srcs = {item['src'] for item in existing_pool}
        logger.info(f"Existing pool: {len(existing_pool)} images")

        next_num = self._get_next_pull_number(existing_pool)

        logger.info("[1/3] Fetching from Pinterest...")
        pinterest_imgs = self._fetch_pinterest()
        logger.info(f"Pinterest: {len(pinterest_imgs)} images")

        logger.info("[2/3] Fetching from archive...")
        archive_imgs = self._fetch_archive()
        logger.info(f"Archive: {len(archive_imgs)} images")

        all_new = []
        for img in pinterest_imgs:
                        if img['src'] not in existing_srcs:
                                            all_new.append(img)
                                    for img in archive_imgs:
                                                    if img['src'] not in existing_srcs:
                                                                        all_new.append(img)

                                                if not all_new:
                                                                logger.info("No new images found, pool unchanged")
                                                                return True

        random.shuffle(all_new)
        selected = all_new[:MAX_NEW_IMAGES]
        logger.info(f"Selected {len(selected)} new images to add")

        new_entries = []
        sizes = ['l', 'l', 'l', 'm', 'm', 'm', 'm', 's', 's', 's']
        for i, img in enumerate(selected):
                        idx = next_num + i
            meta = self._assign_meta(img, idx, img.get('source', 'pinterest'))
            size = sizes[i % len(sizes)]
            new_entries.append({
                                'src': img['src'],
                                'meta': meta,
                                'size': size
            })

        updated_pool = existing_pool + new_entries
        logger.info(f"Updated pool: {len(updated_pool)} total images")

        logger.info("[3/3] Updating HTML...")
        try:
                        html = self.html_file.read_text(encoding='utf-8')
            items = []
            for entry in updated_pool:
                                items.append(
                                                        f'  {{ src: "{entry["src"]}", meta: "{entry["meta"]}", size: "{entry["size"]}" }}'
                                )
                            pool_js = "const POOL = [\n" + ",\n".join(items) + "\n];"
            new_html = re.sub(r'const POOL = \[[\s\S]*?\];', pool_js, html)

            if not dry_run:
                                self.html_file.write_text(new_html, encoding='utf-8')
                                logger.info(f"Wrote {self.html_file}")
else:
                logger.info("DRY RUN - skipping write")
except Exception as e:
            logger.error(f"HTML error: {e}")
            return False

        logger.info(f"Pool refresh complete! Added {len(new_entries)} images.")
        return True


def main():
        import argparse
    parser = argparse.ArgumentParser(description='Refresh LOOOOK pool')
    parser.add_argument('--board-url', help='Pinterest board URL')
    parser.add_argument('--archive-url', default='https://jjjj-image-library.com/',
                                                help='Archive site URL')
    parser.add_argument('--html-file', default='index.html', help='Path to index.html')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()

    board_url = args.board_url or os.getenv('PINTEREST_BOARD_URL')
    if not board_url:
                logger.error("Pinterest board URL required")
        sys.exit(1)

    archive_url = args.archive_url or os.getenv('ARCHIVE_URL', 'https://jjjj-image-library.com/')

    refresher = PoolRefresher(board_url, archive_url, args.html_file)
    success = refresher.run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
        main()
