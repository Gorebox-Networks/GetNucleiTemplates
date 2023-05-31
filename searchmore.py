#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import requests
import json
import time
import os
import subprocess
import shutil
import argparse
import getpass
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)

# Clear the screen
os.system('cls' if os.name == 'nt' else 'clear')

def debug_log(msg: str, debug: bool):
    """Log the given message if debug is True."""
    if debug:
        print(msg)

def search_github_repos(query_terms, debug=False):
    base_url = "https://api.github.com"
    token = os.getenv('GITHUB_API_TOKEN')  # Read the token from environment variable
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token.strip():  # If the user provided a token
        headers['Authorization'] = f'token {token}'
    search_url = f"{base_url}/search/repositories"
    search_params = {'q': ' OR '.join(query_terms), 'page': 1}
        
    debug_log(f"{Fore.BLUE}Searching repositories with terms: {Fore.GREEN}{query_terms}{Style.RESET_ALL}", debug)

    found_repos = []

    shutil.copy("nuclei.txt", "nuclei.txt.bak")
    with open("nuclei.txt.bak", "r") as file:
        existing_repos = set(line.strip() for line in file.readlines() if line.strip() and not line.startswith("#"))
    
    new_templates_file = "new_templates.txt"
    if not os.path.exists(new_templates_file):
        with open(new_templates_file, 'w'): pass  # create the file if it doesn't exist

    with open(new_templates_file, "r") as file:
        new_templates_repos = set(line.strip() for line in file.readlines() if line.strip() and not line.startswith("#"))

    while True:
        debug_log(f"{Fore.BLUE}[+] Sending GET request to: {Fore.MAGENTA}{search_url}{Style.RESET_ALL}", debug)

        response = requests.get(search_url, headers=headers, params=search_params)

        debug_log(f"{Fore.BLUE}[+] Received response with status code: {Fore.GREEN}{response.status_code}{Style.RESET_ALL}", debug)

        if response.status_code != 200:
            print(f"{Fore.RED}[-] Error with status code: {Fore.RED}{response.status_code}{Style.RESET_ALL}")
            return

        rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

        if rate_limit_remaining < 10:  # adjust the number as needed
            reset_time = rate_limit_reset - time.time()
            if reset_time > 0:
                print(f"{Fore.LIGHTRED_EX}[-] Approaching rate limit. Sleeping for {Fore.LIGHTGREEN_EX}{reset_time}{Style.RESET_ALL} seconds.")
                time.sleep(reset_time)

        data = response.json()

        for repo in data["items"]:
            # Check if repository contains .yaml or .yml files
            contents_url = f"{base_url}/repos/{repo['full_name']}/contents"
            contents_response = requests.get(contents_url, headers=headers)

            if contents_response.status_code != 200:
                continue

            contents = contents_response.json()
            if any(file['name'].endswith(('.yaml', '.yml')) for file in contents):
                repo_url = repo['html_url']
                if repo_url not in existing_repos and repo_url not in new_templates_repos:
                    print(f"{Fore.GREEN}[+] Found New Nuclei Template Repo: {Fore.MAGENTA}{repo_url}{Style.RESET_ALL}")
                    debug_log(f"{Fore.GREEN}[+] Adding {Fore.MAGENTA}{repo_url}{Style.RESET_ALL} to found repositories", debug)
                    found_repos.append(repo_url)

        if 'next' not in response.links:
            break

        search_params['page'] += 1

    print(f"\n{Fore.GREEN}[+] Found {len(found_repos)} new Nuclei Template repositories.{Style.RESET_ALL}")
    
    if found_repos:  # check if found_repos is not empty
        user_input = input(f"{Fore.BLUE}[*] Do you want to download the found repositories? (y/n): {Style.RESET_ALL}")

        if user_input.lower() == 'y':
            with open(new_templates_file, "a") as file:  # Open in append mode
                for repo in found_repos:
                    file.write(f"{repo}\n")

            print(f"{Fore.GREEN}[+] Running getnucleitemplates.py...{Style.RESET_ALL}")
            subprocess.run(["python3", "getnucleitemplates.py", "-f", new_templates_file])
        
        user_input = input(f"\n{Fore.BLUE}[*] Do you want to add the new found repositories to nuclei.txt? (y/n): {Style.RESET_ALL}")
        if user_input.lower() == 'y':
            with open("nuclei.txt", "a") as file:
                for repo in found_repos:
                    file.write(f"{repo}\n")
    else:
        print(f"{Fore.LIGHTRED_EX}[-] No new repositories found.{Style.RESET_ALL}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="Enable debug logging", action="store_true")
    args = parser.parse_args()
    search_terms = ["nuclei-templates", "nuclei-scripts", "nuclei-configs"]
    search_github_repos(search_terms, debug=args.debug)