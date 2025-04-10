#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)

import os
import subprocess
import requests
from typing import List, Tuple
import shutil
import argparse
from colorama import Fore, Style, init
from dotenv import load_dotenv, set_key
import getpass
import time
import logging
import fcntl
import re
from pathlib import Path

# Initialize colorama and logging
init(autoreset=True)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Track 404 URLs for commenting
urls_404 = []

def secure_set_key(file_path: str, key: str, value: str) -> None:
    try:
        set_key(file_path, key, value)
        os.chmod(file_path, 0o600)
    except Exception as e:
        logging.error(f"Failed to set key {key} in {file_path}: {e}")


def read_urls_from_file(filepath: str) -> List[str]:
    with open(filepath, 'a'):
        pass
    with open(filepath, 'r') as file:
        return [url.strip() for url in file.readlines() if url.strip()]


def write_urls_to_file(filepath: str, urls: List[str]) -> None:
    with open(filepath, 'w') as file:
        for url in urls:
            file.write(f"{url}\n")


def get_github_api_key() -> str:
    api_key = os.getenv('GITHUB_API_KEY')
    if not api_key:
        api_key = getpass.getpass(f"{Fore.GREEN}Enter your Github API Key (or press 'Enter' for unauthenticated search): {Style.RESET_ALL}")
        if not validate_api_key(api_key):
            print(f"{FAIL_COLOR}Invalid GitHub API Key format.{Style.RESET_ALL}")
            return ""
        secure_set_key(ENV_FILE, "GITHUB_API_KEY", api_key)
    return api_key


def validate_api_key(api_key: str) -> bool:
    return bool(api_key) and len(api_key) in (40, 64)


def sanitize_repo_name(name: str) -> str:
    return re.sub(r'[^\w\-_.]', '_', name)


def get_http_status_code(url: str) -> Tuple[bool, int]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return True, response.status_code
    except requests.RequestException as e:
        logging.warning(f"Request to {url} failed: {e}")
        return False, -1


def is_url_clonable(url: str) -> bool:
    ok, status = get_http_status_code(url)
    if not ok:
        return False
    if 200 <= status < 400:
        return True
    if status == 403:
        logging.warning(f"Access forbidden to {url} (403). Possibly rate-limited.")
    elif status == 404:
        logging.warning(f"URL {url} not found (404).")
        urls_404.append(url)
    elif status >= 500:
        logging.warning(f"Server error from {url}: {status}.")
    else:
        logging.warning(f"Unexpected response from {url}: {status}.")
    return False


def is_git_repo(url: str) -> bool:
    try:
        result = subprocess.run(
            ['git', 'ls-remote', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        logging.warning(f"Failed to verify Git repository at {url}: {e}")
        return False


def get_latest_commit_hash(url: str) -> str:
    try:
        result = subprocess.run(
            ['git', 'ls-remote', url, 'HEAD'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10
        )
        output = result.stdout.decode().strip()
        if output:
            return output.split('\t')[0]
    except Exception as e:
        logging.warning(f"Unable to retrieve latest commit hash from {url}: {e}")
    return ""


def clone_repo(url: str, index: int) -> bool:
    repo_base = sanitize_repo_name(url.split('/')[-1])
    commit_hash = get_latest_commit_hash(url)
    if not commit_hash:
        print(f"{FAILURE_PREFIX} Cannot retrieve latest commit for {url}. Skipping.{Style.RESET_ALL}")
        return False

    repo_name = f"{repo_base}_{commit_hash[:7]}"
    repo_path = os.path.join(CLONE_DIR, repo_name)

    if os.path.exists(repo_path):
        print(f"{INFO_COLOR}Repository {repo_name} already exists with same commit. Skipping.{Style.RESET_ALL}")
        return False

    try:
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        print(f"{SUCCESS_PREFIX} Cloning {URL_COLOR}{url}{Style.RESET_ALL} into {repo_name}")
        subprocess.run(
            ['git', 'clone', '--depth', '1', url, repo_path],
            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60
        )
        print(f"{SUCCESS_PREFIX} Successfully cloned {url}{Style.RESET_ALL}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{FAILURE_PREFIX} Failed cloning repo {url}. Reason: {e.stderr.decode(errors='ignore')}{Style.RESET_ALL}")
        return False
    except subprocess.TimeoutExpired:
        print(f"{FAILURE_PREFIX} Timeout cloning repo {url}{Style.RESET_ALL}")
        return False


def append_to_file_securely(filepath: str, data: List[str]) -> None:
    with open(filepath, 'a') as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        for item in data:
            file.write(f"{item}\n")
        fcntl.flock(file, fcntl.LOCK_UN)


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

        if not is_url_clonable(url):
            print(f"{FAIL_COLOR}Unreachable or invalid URL: {url}{Style.RESET_ALL}")
            invalid_urls += 1
            append_to_file_securely(ATTEMPTED_FILE, [url])
            continue

        if not is_git_repo(url):
            print(f"{FAIL_COLOR}URL is not a valid Git repository: {url}{Style.RESET_ALL}")
            invalid_urls += 1
            append_to_file_securely(ATTEMPTED_FILE, [url])
            continue

        if clone_repo(url, index):
            successful_downloads += 1
        else:
            failed_downloads += 1

        append_to_file_securely(ATTEMPTED_FILE, [url])

    return total_attempts, successful_downloads, failed_downloads, invalid_urls


def comment_failed_urls(filepath: str):
    if not urls_404:
        return
    with open(filepath, 'r') as f:
        lines = f.readlines()
    with open(filepath, 'w') as f:
        for line in lines:
            stripped = line.strip()
            if stripped in urls_404:
                f.write(f"# {stripped}  # Auto-commented: 404 not found\n")
            else:
                f.write(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default=DEFAULT_FILE, help="Filename to read the repositories from. Default is 'nuclei.txt'")
    args = parser.parse_args()

    filepath = os.path.join(script_dir, args.file)
    if not os.path.exists(filepath):
        logging.error(f"File {filepath} does not exist.")
        return

    try:
        shutil.copy2(filepath, f'{filepath}.bak')
    except Exception as e:
        logging.warning(f"Could not create backup of {filepath}: {e}")

    if not os.path.exists(CLONE_DIR):
        os.makedirs(CLONE_DIR)

    total_attempts, successful_downloads, failed_downloads, invalid_urls = process_urls(filepath)

    comment_failed_urls(filepath)

    print(f"\n{INFO_COLOR}---- Summary ----")
    print(f"{INFO_COLOR}Total URLs attempted: {total_attempts}")
    print(f"{SUCCESS_PREFIX} Successfully downloaded: {successful_downloads}")
    print(f"{FAILURE_PREFIX} Failed to download: {failed_downloads}")
    print(f"{INFO_COLOR}Invalid URLs: {invalid_urls}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
