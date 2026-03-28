#!/usr/bin/env python3
"""
Archive Image Fetcher - Extracts images from jjjj-image-library.com
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Dict
import logging
import argparse
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArchiveFetcher:
      def __init__(self, base_url: str = "https://jjjj-image-library.com/"):
                self.base_url = base_url
                self.session = requests.Session()
                self.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,*/*',
                })

      def fetch_images(self) -> List[Dict]:
                logger.info(f"Fetching images from {self.base_url}")
                try:
                              resp = self.session.get(self.base_url, timeout=30)
                              if resp.status_code != 200:
                                                logger.error(f"Archive returned {resp.status_code}")
                                                return []

                              images = []
                              img_pattern = re.compile(
                                  r'<img[^>]+src=["\']([^"\']*img\.jjjj-image-library\.com[^"\']*)["\']',
                                  re.IGNORECASE
                              )
                              for match in img_pattern.finditer(resp.text):
                                                src = match.group(1)
                                                if not src.startswith('http'):
                                                                      src = 'https://' + src.lstrip('/')
                                                                  images.append({
                                                    'src': src,
                                                    'alt': 'LOOOOK archive',
                                                    'category': 'archive'
                                                })

                              if not images:
                                                img_pattern2 = re.compile(
                                                                      r'https?://img\.jjjj-image-library\.com/[^\s"\'<>]+',
                                                                      re.IGNORECASE
                                                )
                                                for match in img_pattern2.finditer(resp.text):
                                                                      src = match.group(0)
                                                                      images.append({
                                                                          'src': src,
                                                                          'alt': 'LOOOOK archive',
                                                                          'category': 'archive'
                                                                      })

                                            seen = set()
                              unique = []
                              for img in images:
                                                if img['src'] not in seen:
                                                                      seen.add(img['src'])
                                                                      unique.append(img)

                                            logger.info(f"Found {len(unique)} unique images from archive")
                              return unique

                except Exception as e:
                              logger.error(f"Archive fetch error: {e}")
                              return []


def main():
      parser = argparse.ArgumentParser(description='Fetch images from archive site')
      parser.add_argument('--url', default='https://jjjj-image-library.com/',
                          help='Archive site URL')
      parser.add_argument('--output', default='archive_images.json',
                          help='Output JSON file')
      args = parser.parse_args()

    fetcher = ArchiveFetcher(args.url)
    images = fetcher.fetch_images()

    output_path = Path(args.output)
    output_path.write_text(json.dumps(images, indent=2), encoding='utf-8')
    logger.info(f"Saved {len(images)} images to {output_path}")


if __name__ == '__main__':
      main()
