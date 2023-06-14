#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import subprocess
import requests
from typing import List, Tuple
import shutil
import argparse
from colorama import Fore, Back, Style
from dotenv import load_dotenv, set_key
import getpass
from urllib.parse import urlparse

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

# Clear the screen
# os.system('cls' if os.name == 'nt' else 'clear')

# Add colorama initializations
print(Style.RESET_ALL)
success_prefix = f"{Fore.GREEN}[+]{Style.RESET_ALL}"
failure_prefix = f"{Fore.RED}[-]{Style.RESET_ALL}"
url_color = Fore.YELLOW
fail_color = Fore.RED
info_color = Fore.CYAN

# Create a session
session = requests.Session()

def read_urls_from_file(filepath: str) -> List[str]:
    """Read URLs from the provided text file, ignoring commented lines."""
    with open(filepath, 'a+') as f:
        urls = f.readlines()
    return [url.strip() for url in urls if url.strip()]

def get_github_api_key():
    """Gets Github API key from .env file or user input."""
    api_key = os.getenv('GITHUB_API_KEY')
    if not api_key:
        api_key = getpass.getpass(f"{Fore.GREEN}Enter your Github API Key (or press 'Enter' for unauthenticated search): {Style.RESET_ALL}")
        set_key(".env", "GITHUB_API_KEY", api_key)
    return api_key

def is_url_valid(url: str) -> bool:
    """Check if the URL exists and is not a 404."""
    try:
        response = session.head(url, allow_redirects=True)
        return response.status_code != 404
    except requests.ConnectionError:
        return False

def requires_auth(url: str, api_key: str) -> bool:
    """Check if the URL requires authentication."""
    headers = {'Authorization': f'token {api_key}'}
    response = session.get(url, headers=headers)
    return response.status_code == 403

def clone_and_validate_repo(url: str, index: int) -> Tuple[bool, bool, bool]:
    """Attempt to clone and validate the repository from the given URL."""
    repo_name = urlparse(url).path  # Extract repository name
    repo_name = f"{repo_name}_{index}"  # Append index to make it unique

    if os.path.exists(repo_name):
        print(f"{info_color}Repository {repo_name} already exists. Skipping.{Style.RESET_ALL}")
        return False, True, False

    print(f"{success_prefix} Cloning {url_color}{url}{Style.RESET_ALL} into {repo_name}")
    try:
        process = subprocess.Popen(
            ['git', 'clone', '--depth', '1', url, repo_name],
            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),  # Set GIT_TERMINAL_PROMPT=0
            stdout=subprocess.DEVNULL,  # Optional: Suppress stdout
            stderr=subprocess.DEVNULL,  # Optional: Suppress stderr
        )
        process.communicate()  # Wait for process to complete

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, 'git')

        print(f"{success_prefix} Validating {url_color}{url}{Style.RESET_ALL} using 'nuclei -validate'")
        validate_process = subprocess.Popen(
            ['nuclei', '-validate', '-t', repo_name],
            stdout=subprocess.DEVNULL,  # Optional: Suppress stdout
            stderr=subprocess.DEVNULL,  # Optional: Suppress stderr
        )
        validate_process.communicate()  # Wait for process to complete

        if validate_process.returncode != 0:
            raise subprocess.CalledProcessError(validate_process.returncode, 'nuclei')

        return True, True, True
    except subprocess.CalledProcessError:
        print(f"{failure_prefix} Failed to clone or validate {url_color}{url}{Style.RESET_ALL}.")
        print(f"{info_color}Please check this repository manually.{Style.RESET_ALL}")
        return False, True, False

def move_to_folder(url: str, index: int, folder_name: str):
    """Move cloned repository to the appropriate folder."""
    repo_name = urlparse(url).path  # Extract repository name
    repo_name = f"{repo_name}_{index}"  # Append index to make it unique

    dest_folder = os.path.join(script_dir, folder_name)
    os.makedirs(dest_folder, exist_ok=True)  # Create destination folder if it doesn't exist

    source_path = os.path.join(script_dir, repo_name)
    dest_path = os.path.join(dest_folder, repo_name)

    shutil.move(source_path, dest_path)

# Main script
def main():
    # Add command line arguments
    parser = argparse.ArgumentParser(description='Clone and validate Github repositories.')
    parser.add_argument('-f', '--filepath', help='The path to the file with the list of repository URLs.', required=True)
    args = parser.parse_args()

    api_key = get_github_api_key()
    urls = read_urls_from_file(args.filepath)
    total_attempts, successful_downloads, failed_downloads, invalid_urls = 0, 0, 0, 0

    for i, url in enumerate(urls, start=1):
        print(f"\n{i}/{len(urls)}: {url}")
        if is_url_valid(url):
            if requires_auth(url, api_key):
                print(f"{info_color}Skipping {url_color}{url}{Style.RESET_ALL} because it requires authentication.")
                continue

            successful_clone, attempted_clone, valid_url = clone_and_validate_repo(url, i)

            if successful_clone:
                move_to_folder(url, i, 'validated')
                successful_downloads += 1
            elif attempted_clone:
                move_to_folder(url, i, 'not-validated')
                failed_downloads += 1

            total_attempts += attempted_clone
            invalid_urls += not valid_url
        else:
            print(f"{failure_prefix} URL is not valid: {url_color}{url}{Style.RESET_ALL}")
            invalid_urls += 1

    print(f"\n{success_prefix} Done. {successful_downloads} repositories downloaded successfully out of {total_attempts} attempted. {invalid_urls} URLs were invalid.")

if __name__ == '__main__':
    main()
