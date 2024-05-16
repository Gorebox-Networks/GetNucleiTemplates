#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)

import os
import subprocess
import requests
from typing import List, Tuple
import shutil
import argparse
from colorama import Fore, Style
from dotenv import load_dotenv, set_key
import getpass
import time

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

# Constants
SUCCESS_PREFIX = f"{Fore.GREEN}[+]{Style.RESET_ALL}"
FAILURE_PREFIX = f"{Fore.RED}[-]{Style.RESET_ALL}"
URL_COLOR = Fore.YELLOW
FAIL_COLOR = Fore.RED
INFO_COLOR = Fore.CYAN
ENV_FILE = ".env"
DEFAULT_FILE = "nuclei.txt"
ATTEMPTED_FILE = "attempted.txt"
CLONE_DIR = "nuclei-templates"

def read_urls_from_file(filepath: str) -> List[str]:
    with open(filepath, 'a'):
        pass  # Ensure the file exists
    with open(filepath, 'r') as file:
        return [url.strip() for url in file.readlines() if url.strip()]

def get_github_api_key() -> str:
    api_key = os.getenv('GITHUB_API_KEY')
    if not api_key:
        api_key = getpass.getpass(f"{Fore.GREEN}Enter your Github API Key (or press 'Enter' for unauthenticated search): {Style.RESET_ALL}")
        set_key(ENV_FILE, "GITHUB_API_KEY", api_key)
    return api_key

def is_url_valid(url: str) -> bool:
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code != 404
    except requests.ConnectionError:
        return False

def clone_repo(url: str, index: int) -> bool:
    repo_name = url.split('/')[-1] + f"_{index}_{time.strftime('%Y%m%d-%H%M%S')}"
    repo_path = os.path.join(CLONE_DIR, repo_name)

    if os.path.exists(repo_path):
        print(f"{INFO_COLOR}Repository {repo_name} already exists. Skipping.{Style.RESET_ALL}")
        return False

    try:
        print(f"{SUCCESS_PREFIX} Cloning {URL_COLOR}{url}{Style.RESET_ALL} into {repo_name}")
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', url, repo_path],
            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(f"{SUCCESS_PREFIX} Successful cloning {url}{Style.RESET_ALL}")
            return True
        else:
            raise subprocess.CalledProcessError(result.returncode, 'git clone')
    except subprocess.CalledProcessError as e:
        print(f"{FAILURE_PREFIX} Failed cloning repo {url}. Reason: {e}{Style.RESET_ALL}")
        return False

def process_urls(filepath: str) -> Tuple[int, int, int, int]:
    attempted_urls = read_urls_from_file(ATTEMPTED_FILE)
    urls = read_urls_from_file(filepath)

    total_attempts = 0
    successful_downloads = 0
    failed_downloads = 0
    invalid_urls = 0

    valid_urls = [url for url in urls if not url.startswith('#')]
    invalid_urls += len(urls) - len(valid_urls)

    for index, url in enumerate(valid_urls):
        total_attempts += 1
        print(f"\n{INFO_COLOR}--- Repository {total_attempts} ---{Style.RESET_ALL}")

        if url in attempted_urls:
            print(f"{INFO_COLOR}URL {URL_COLOR}{url}{Style.RESET_ALL} already cloned. Skipping.")
            continue

        if not is_url_valid(url):
            print(f"{FAIL_COLOR}Invalid URL: {url}{Style.RESET_ALL}")
            invalid_urls += 1
            continue

        if clone_repo(url, index):
            successful_downloads += 1
        else:
            failed_downloads += 1

        with open(ATTEMPTED_FILE, 'a') as file:
            file.write(f"{url}\n")

    return total_attempts, successful_downloads, failed_downloads, invalid_urls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default=DEFAULT_FILE, help="Filename to read the repositories from. Default is 'nuclei.txt'")
    args = parser.parse_args()

    filepath = os.path.join(script_dir, args.file)
    shutil.copy2(filepath, f'{filepath}.bak')

    if not os.path.exists(CLONE_DIR):
        os.makedirs(CLONE_DIR)

    os.chdir(CLONE_DIR)

    total_attempts, successful_downloads, failed_downloads, invalid_urls = process_urls(filepath)

    print(f"\n{INFO_COLOR}---- Summary ----")
    print(f"{INFO_COLOR}Total URLs attempted: {total_attempts}")
    print(f"{SUCCESS_PREFIX} Successfully downloaded: {successful_downloads}")
    print(f"{FAILURE_PREFIX} Failed to download: {failed_downloads}")
    print(f"{INFO_COLOR}Invalid URLs: {invalid_urls}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
