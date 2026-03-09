#!/usr/bin/env python3
"""
Pinterest Image Fetcher - Extracts all images from a Pinterest board using Playwright.
"""
import json
import sys
import time
from pathlib import Path
from typing import List, Dict
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    logger.error("Playwright not installed. Run: pip install playwright")
    sys.exit(1)


class PinterestFetcher:
    def __init__(self, board_url: str, headless: bool = True):
        self.board_url = board_url.rstrip('/')
        self.headless = headless

    def fetch_images(self) -> List[Dict]:
        logger.info(f"Fetching images from {self.board_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_viewport_size({"width": 1200, "height": 800})

            try:
                page.goto(self.board_url, wait_until="networkidle", timeout=30000)
                logger.info("Page loaded")

                # Scroll to load all images
                self._scroll_and_load(page)
                images = self._extract_images(page)

                logger.info(f"Extracted {len(images)} images")
                browser.close()
                return images
            except Exception as e:
                logger.error(f"Error: {e}")
                browser.close()
                return []

    def _scroll_and_load(self, page):
        logger.info("Scrolling to load images...")
        previous_count = 0
        no_new_count = 0

        for attempt in range(20):
            current = len(page.query_selector_all('img[src*="pinimg"]'))
            logger.info(f"  Scroll {attempt + 1}: {current} images")

            if current == previous_count:
                no_new_count += 1
                if no_new_count >= 2:
                    logger.info(f"Reached bottom: {current} images")
                    break
            else:
                no_new_count = 0

            previous_count = current
            page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            time.sleep(1)

    def _extract_images(self, page) -> List[Dict]:
        images = []
        img_elements = page.query_selector_all('img[src*="pinimg"]')
        logger.info(f"Found {len(img_elements)} image elements")

        for img in img_elements:
            try:
                src = img.get_attribute('src')
                if not src or 'placeholder' in src.lower():
                    continue

                # Get higher quality versions
                if '236x' in src:
                    src = src.replace('236x', '564x')
                elif '474x' in src:
                    src = src.replace('474x', '1200x')

                images.append({
                    'src': src,
                    'alt': img.get_attribute('alt') or 'Pinterest image',
                    'width': 400,
                    'height': 400,
                    'category': 'inspiration'
                })
            except:
                continue

        # Remove duplicates
        seen = set()
        unique = []
        for img in images:
            if img['src'] not in seen:
                seen.add(img['src'])
                unique.append(img)

        return unique


def main():
    parser = argparse.ArgumentParser(description='Fetch images from Pinterest board')
    parser.add_argument('--board-url', required=True, help='Pinterest board URL')
    parser.add_argument('--output', default='images.json', help='Output JSON file')
    parser.add_argument('--no-headless', action='store_true', help='Show browser')
    args = parser.parse_args()

    fetcher = PinterestFetcher(args.board_url, headless=not args.no_headless)
    images = fetcher.fetch_images()

    output_path = Path(args.output)
    output_path.write_text(json.dumps(images, indent=2), encoding='utf-8')
    logger.info(f"Saved {len(images)} images to {output_path}")


if __name__ == '__main__':
    main()
