#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import shutil
import subprocess
import time
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore, Style, init
from dotenv import load_dotenv
from pathlib import Path
from typing import List

# Initialize colorama
init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

def debug_log(msg: str, debug: bool):
    if debug:
        print(msg)

def handle_response(response, debug, authenticated=False):
    debug_log(
        f"{Fore.BLUE}[+] Received response with status code: {Fore.GREEN}{response.status_code}{Style.RESET_ALL}",
        debug,
    )

    if response.status_code == 403:
        print(f"{Fore.RED}[-] Forbidden: Check your token and permissions.{Style.RESET_ALL}")
        return False
    elif response.status_code != 200:
        print(f"{Fore.RED}[-] Error with status code: {Fore.RED}{response.status_code}{Style.RESET_ALL}")
        return False

    rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
    rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

    if rate_limit_remaining < 5:
        reset_time = rate_limit_reset - time.time()
        if reset_time > 0:
            print(f"{Fore.LIGHTRED_EX}[-] Approaching rate limit. Sleeping for {Fore.LIGHTGREEN_EX}{reset_time:.1f}{Style.RESET_ALL} seconds.")
            time.sleep(reset_time)
    else:
        sleep_time = (rate_limit_reset - time.time()) / max(rate_limit_remaining, 1)
        if sleep_time > 0:
            print(f"{Fore.YELLOW}[~] Respecting API limits. Sleeping for {sleep_time:.2f}s between requests...{Style.RESET_ALL}")
            time.sleep(sleep_time)

    return True

def append_to_file(filename: str, data: List[str]):
    try:
        with open(filename, "a") as file:
            for item in data:
                file.write(f"{item}\n")
    except Exception as e:
        print(f"{Fore.RED}[-] Failed to write to {filename}: {e}{Style.RESET_ALL}")

def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def validate_token(session, headers, debug: bool) -> bool:
    try:
        test_resp = session.get("https://api.github.com/user", headers=headers)
        if test_resp.status_code == 200:
            debug_log(f"{Fore.GREEN}[+] GitHub token validated successfully.{Style.RESET_ALL}", debug)
            return True
        else:
            print(f"{Fore.RED}[-] GitHub token validation failed: {test_resp.status_code}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[-] Token validation error: {e}{Style.RESET_ALL}")
    return False

def search_github_repos(query_terms, debug=False):
    base_url = "https://api.github.com"
    token = os.getenv("GITHUB_API_TOKEN")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token and token.strip():
        headers["Authorization"] = f"token {token}"

    session = create_session()
    if token and not validate_token(session, headers, debug):
        return

    search_url = f"{base_url}/search/repositories"
    search_params = {"q": " OR ".join(query_terms), "page": 1}

    debug_log(f"{Fore.BLUE}Searching repositories with terms: {Fore.GREEN}{query_terms}{Style.RESET_ALL}", debug)

    found_repos = []
    new_templates_file = "new_templates.txt"
    Path(new_templates_file).touch(exist_ok=True)

    shutil.copy("nuclei.txt", "nuclei.txt.bak")
    with open("nuclei.txt.bak", "r") as file:
        existing_repos = set(
            line.strip()
            for line in file.readlines()
            if line.strip() and not line.startswith("#")
        )

    with open(new_templates_file, "r") as file:
        new_templates_repos = set(
            line.strip()
            for line in file.readlines()
            if line.strip() and not line.startswith("#")
        )

    repo_counter = 0

    while True:
        print(f"{Fore.CYAN}[~] Fetching page {search_params['page']} of GitHub search results...{Style.RESET_ALL}")
        debug_log(f"{Fore.BLUE}[+] Sending GET request to: {Fore.MAGENTA}{search_url}{Style.RESET_ALL}", debug)
        try:
            response = session.get(search_url, headers=headers, params=search_params)
        except requests.RequestException as e:
            print(f"{Fore.RED}[-] Request failed: {e}{Style.RESET_ALL}")
            return

        if not handle_response(response, debug):
            return

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}[-] Failed to parse JSON response: {e}{Style.RESET_ALL}")
            return

        for repo in data.get("items", []):
            repo_counter += 1
            print(f"{Fore.LIGHTBLUE_EX}[~] Checking repo #{repo_counter}: {repo['full_name']}{Style.RESET_ALL}")
            contents_url = f"{base_url}/repos/{repo['full_name']}/contents"
            try:
                contents_response = session.get(contents_url, headers=headers)
            except requests.RequestException as e:
                print(f"{Fore.RED}[-] Request failed for contents: {e}{Style.RESET_ALL}")
                continue

            if not handle_response(contents_response, debug):
                continue

            try:
                contents = contents_response.json()
            except json.JSONDecodeError as e:
                print(f"{Fore.RED}[-] Failed to parse contents JSON: {e}{Style.RESET_ALL}")
                continue

            if any(file.get("name", "").endswith((".yaml", ".yml")) for file in contents):
                repo_url = repo.get("html_url")
                if repo_url and repo_url not in existing_repos and repo_url not in new_templates_repos:
                    print(f"{Fore.GREEN}[+] Found New Nuclei Template Repo: {Fore.MAGENTA}{repo_url}{Style.RESET_ALL}")
                    debug_log(f"{Fore.GREEN}[+] Adding {Fore.MAGENTA}{repo_url}{Style.RESET_ALL} to found repositories", debug)
                    found_repos.append(repo_url)

        if not response.links.get("next"):
            break

        search_params["page"] += 1

    print(f"\n{Fore.GREEN}[+] Found {len(found_repos)} new Nuclei Template repositories.{Style.RESET_ALL}")

    if found_repos:
        user_input = input(f"{Fore.BLUE}[*] Do you want to download the found repositories? (y/n): {Style.RESET_ALL}")
        if user_input.lower() == "y":
            append_to_file(new_templates_file, found_repos)
            print(f"{Fore.GREEN}[+] Running getnucleitemplates.py...{Style.RESET_ALL}")
            subprocess.run(["python3", "getnucleitemplates.py", "-f", new_templates_file])

        user_input = input(f"\n{Fore.BLUE}[*] Do you want to add the new found repositories to nuclei.txt? (y/n): {Style.RESET_ALL}")
        if user_input.lower() == "y":
            append_to_file("nuclei.txt", found_repos)
    else:
        print(f"{Fore.LIGHTRED_EX}[-] No new repositories found.{Style.RESET_ALL}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="Enable debug logging", action="store_true")
    parser.add_argument("--terms", nargs="+", default=["nuclei-templates", "nuclei-scripts", "nuclei-configs"], help="Search terms")
    args = parser.parse_args()
    search_github_repos(args.terms, debug=args.debug)
