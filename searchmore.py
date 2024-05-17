#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)

import os
import json
import time
import requests
import argparse
import subprocess
import shutil
from colorama import Fore, Style, init
from dotenv import load_dotenv
import logging
from typing import List, Set
import fcntl

# Initialize colorama and logging
init(autoreset=True)
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://api.github.com"
DEFAULT_SEARCH_TERMS = ["nuclei-templates", "nuclei-scripts", "nuclei-configs"]
NEW_TEMPLATES_FILE = "new_templates.txt"
NUCLEI_FILE = "nuclei.txt"
NUCLEI_BACKUP_FILE = f"{NUCLEI_FILE}.bak"
GITHUB_API_KEY = os.getenv('GITHUB_API_KEY')

def debug_log(msg: str, debug: bool, redact: bool = False) -> None:
    """Log the given message if debug is True. Redact sensitive information if redact is True."""
    if redact:
        msg = msg.replace(GITHUB_API_KEY, "[REDACTED]") if GITHUB_API_KEY else msg
        # Assuming we have a repository URL in the variable repo_url
        # repo_url_placeholder = "[REDACTED_REPO_URL]"
        # msg = msg.replace(repo_url, repo_url_placeholder) if 'repo_url' in locals() else msg
    if debug:
        logging.debug(msg)

def debug_log(msg: str, debug: bool, redact: bool = False) -> None:
    """Log the given message if debug is True. Redact sensitive information if redact is True."""
    if redact:
        msg = msg.replace(GITHUB_API_KEY, "[REDACTED]") if GITHUB_API_KEY else msg
        # Assuming we have a repository URL in the variable repo_url
        repo_url_placeholder = "[REDACTED_REPO_URL]"
        msg = msg.replace(repo_url, repo_url_placeholder) if 'repo_url' in locals() else msg
    if debug:
        logging.debug(msg)

def handle_response(response: requests.Response, debug: bool, authenticated: bool = True, redact: bool = False) -> bool:
    """Handle the response from an API request."""
    debug_log(f"{Fore.BLUE}[+] Received response with status code: {Fore.GREEN}{response.status_code}{Style.RESET_ALL}", debug, redact)

    if response.status_code == 403:
        print(f"{Fore.RED}[-] Forbidden: Check your token and permissions.{Style.RESET_ALL}")
        return False
    elif response.status_code != 200:
        print(f"{Fore.RED}[-] Error with status code: {Fore.RED}{response.status_code}{Style.RESET_ALL}")
        return False

    rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

    threshold = 5 if authenticated else 1

    if rate_limit_remaining < threshold:
        reset_time = max(rate_limit_reset - time.time(), 0)
        time.sleep(reset_time)

    return True

def append_to_file_securely(filename: str, data: List[str]) -> None:
    """Append data to a file in a secure manner."""
    with open(filename, "a") as file:
        fcntl.flock(file, fcntl.LOCK_EX)  # Acquire an exclusive lock
        for item in data:
            file.write(f"{item}\n")
        fcntl.flock(file, fcntl.LOCK_UN)  # Release the lock

def read_file_lines(filename: str) -> Set[str]:
    """Read lines from a file and return as a set of stripped strings."""
    if not os.path.exists(filename):
        return set()
    with open(filename, "r") as file:
        return set(line.strip() for line in file if line.strip() and not line.startswith("#"))

def search_github_repos(query_terms: List[str], debug: bool = False, redact: bool = False) -> None:
    """Search GitHub repositories based on query terms."""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    authenticated = True

    if GITHUB_API_KEY:
        headers['Authorization'] = f'token {GITHUB_API_KEY}'
    else:
        print(f"{Fore.YELLOW}[!] GitHub API token not found. Proceeding with unauthenticated search.{Style.RESET_ALL}")
        authenticated = False

    search_url = f"{BASE_URL}/search/repositories"
    search_params = {'q': ' OR '.join(query_terms), 'page': 1}

    debug_log(f"{Fore.BLUE}Searching repositories with terms: {Fore.GREEN}{query_terms}{Style.RESET_ALL}", debug, redact)

    found_repos = []
    existing_repos = read_file_lines(NUCLEI_FILE)
    new_templates_repos = read_file_lines(NEW_TEMPLATES_FILE)

    while True:
        try:
            response = requests.get(search_url, headers=headers, params=search_params)
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return

        if not handle_response(response, debug, authenticated, redact):
            return

        data = response.json()
        for repo in data.get("items", []):
            contents_url = f"{BASE_URL}/repos/{repo['full_name']}/contents"
            try:
                contents_response = requests.get(contents_url, headers=headers)
            except requests.RequestException as e:
                print(f"An error occurred: {e}")
                continue

            if not handle_response(contents_response, debug, authenticated, redact):
                continue

            contents = contents_response.json()
            if any(file['name'].endswith(('.yaml', '.yml')) for file in contents):
                repo_url = repo['html_url']
                if repo_url not in existing_repos and repo_url not in new_templates_repos:
                    print(f"{Fore.GREEN}[+] Found New Nuclei Template Repo: {Fore.MAGENTA}{repo_url}{Style.RESET_ALL}")
                    debug_log(f"{Fore.GREEN}[+] Adding {Fore.MAGENTA}{repo_url}{Style.RESET_ALL} to found repositories", debug, redact)
                    found_repos.append(repo_url)

        if 'next' not in response.links:
            break

        search_params['page'] += 1

    print(f"\n{Fore.GREEN}[+] Found {len(found_repos)} new Nuclei Template repositories.{Style.RESET_ALL}")

    if found_repos:
        user_input = input(f"{Fore.BLUE}[*] Do you want to download the found repositories? (y/n): {Style.RESET_ALL}").strip().lower()
        if user_input == 'y':
            append_to_file_securely(NEW_TEMPLATES_FILE, found_repos)
            print(f"{Fore.GREEN}[+] Running getnucleitemplates.py...{Style.RESET_ALL}")
            try:
                result = subprocess.run(["python3", "getnucleitemplates.py", "-f", NEW_TEMPLATES_FILE], check=True)
                if result.returncode != 0:
                    print(f"{FAIL_COLOR}Failed to run getnucleitemplates.py with return code {result.returncode}{Style.RESET_ALL}")
            except subprocess.CalledProcessError as e:
                print(f"{FAIL_COLOR}Failed to run getnucleitemplates.py. Reason: {e}{Style.RESET_ALL}")

        user_input = input(f"\n{Fore.BLUE}[*] Do you want to add the new found repositories to nuclei.txt? (y/n): {Style.RESET_ALL}").strip().lower()
        if user_input == 'y':
            append_to_file_securely(NUCLEI_FILE, found_repos)
    else:
        print(f"{Fore.LIGHTRED_EX}[-] No new repositories found.{Style.RESET_ALL}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="Enable debug logging", action="store_true")
    parser.add_argument("--redact", help="Redact sensitive information in logs", action="store_true")
    args = parser.parse_args()
    search_github_repos(DEFAULT_SEARCH_TERMS, debug=args.debug, redact=args.redact)
