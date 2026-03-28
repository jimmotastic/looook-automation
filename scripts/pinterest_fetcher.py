#!/usr/bin/env python3
"""
Pinterest Image Fetcher - Extracts images from a Pinterest board.
Uses Pinterest's RSS feed first, falls back to requests-based scraping.
"""
import json
import re
import sys
import time
from pathlib import Path
from typing import List, Dict
import logging
import argparse
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PinterestFetcher:
    def __init__(self, board_url: str, headless: bool = True):
        self.board_url = board_url.rstrip('/')
        self.headless = headless
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def fetch_images(self) -> List[Dict]:
        logger.info(f"Fetching images from {self.board_url}")

        # Try RSS feed first
        images = self._fetch_via_rss()
        if images:
            logger.info(f"RSS: Got {len(images)} images")
            return images

        # Try requests-based HTML scraping
        images = self._fetch_via_requests()
        if images:
            logger.info(f"Requests: Got {len(images)} images")
            return images

        # Fall back to Playwright
        images = self._fetch_via_playwright()
        logger.info(f"Playwright: Got {len(images)} images")
        return images

    def _fetch_via_rss(self) -> List[Dict]:
        """Fetch via Pinterest RSS feed."""
        try:
            rss_url = self.board_url.rstrip('/') + '.rss'
            logger.info(f"Trying RSS: {rss_url}")
            resp = self.session.get(rss_url, timeout=30)
            if resp.status_code != 200:
                logger.info(f"RSS returned {resp.status_code}")
                return []

            images = []
            img_pattern = re.compile(r'<img[^>]+src="([^"]*pinimg[^"]*)"')
            for match in img_pattern.finditer(resp.text):
                src = match.group(1)
                if 'placeholder' in src.lower():
                    continue
                src = src.replace('236x', '564x').replace('474x', '1200x')
                images.append({
                    'src': src,
                    'alt': 'Pinterest image',
                    'width': 400,
                    'height': 400,
                    'category': 'inspiration'
                })

            # Deduplicate
            seen = set()
            unique = []
            for img in images:
                if img['src'] not in seen:
                    seen.add(img['src'])
                    unique.append(img)
            return unique
        except Exception as e:
            logger.info(f"RSS failed: {e}")
            return []

    def _fetch_via_requests(self) -> List[Dict]:
        """Fetch via direct HTTP requests with Pinterest's internal API."""
        try:
            logger.info("Trying requests-based fetch...")
            resp = self.session.get(self.board_url, timeout=30)
            if resp.status_code != 200:
                logger.info(f"Page returned {resp.status_code}")
                return []

            images = []
            # Look for pinimg URLs in the page source
            img_pattern = re.compile(r'https://i\.pinimg\.com/[^"\\]+\.(?:jpg|png|webp)')
            for match in img_pattern.finditer(resp.text):
                src = match.group(0)
                if 'placeholder' in src.lower() or '75x75' in src:
                    continue
                src = src.replace('236x', '564x').replace('474x', '1200x')
                images.append({
                    'src': src,
                    'alt': 'Pinterest image',
                    'width': 400,
                    'height': 400,
                    'category': 'inspiration'
                })

            # Deduplicate
            seen = set()
            unique = []
            for img in images:
                if img['src'] not in seen:
                    seen.add(img['src'])
                    unique.append(img)
            return unique
        except Exception as e:
            logger.info(f"Requests failed: {e}")
            return []

    def _fetch_via_playwright(self) -> List[Dict]:
        """Fall back to Playwright with stealth settings."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport={'width': 1200, 'height': 800},
                    locale='en-US',
                )
                page = context.new_page()

                # Block unnecessary resources
                page.route('**/*.{woff,woff2,ttf,otf}', lambda route: route.abort())

                page.goto(self.board_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)

                # Scroll to load images
                for _ in range(10):
                    page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                    page.wait_for_timeout(1500)

                # Extract images
                images = []
                content = page.content()
                img_pattern = re.compile(r'https://i\.pinimg\.com/[^"\\]+\.(?:jpg|png|webp)')
                for match in img_pattern.finditer(content):
                    src = match.group(0)
                    if 'placeholder' in src.lower() or '75x75' in src:
                        continue
                    src = src.replace('236x', '564x').replace('474x', '1200x')
                    images.append({
                        'src': src,
                        'alt': 'Pinterest image',
                        'width': 400,
                        'height': 400,
                        'category': 'inspiration'
                    })

                browser.close()

                # Deduplicate
                seen = set()
                unique = []
                for img in images:
                    if img['src'] not in seen:
                        seen.add(img['src'])
                        unique.append(img)
                return unique
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            return []


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
