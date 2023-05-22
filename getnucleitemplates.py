#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import subprocess  # Changed from git to subprocess
import requests
from typing import List, Tuple
import shutil
import argparse

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

def read_urls_from_file(filepath: str) -> List[str]:
    """Read URLs from the provided text file, ignoring commented lines."""
    with open(filepath, 'r') as f:
        urls = f.readlines()
    return [url.strip() for url in urls if url.strip()]

def is_url_valid(url: str) -> bool:
    """Check if the URL exists and is not a 404."""
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code != 404
    except requests.ConnectionError:
        return False

def requires_auth(url: str) -> bool:
    """Check if the URL requires authentication."""
    response = requests.get(url)
    return response.status_code == 401

def clone_repo(url: str, index: int) -> Tuple[bool, bool]:
    """Attempt to clone the repository from the given URL."""
    repo_name = url.split('/')[-1]  # Extract repository name
    repo_name = f"{repo_name}_{index}"  # Append index to make it unique

    try:
        print(f"Cloning {url} into {repo_name}")
        # Clone the repository using a subprocess command instead of gitpython
        subprocess.check_output(['git', 'clone', '--no-checkout', '--depth', '1', url, repo_name])
        return True, False

    except subprocess.CalledProcessError as e:
        print(f"Failed to clone {url}. Reason: {e}")
        return False, False

def remove_empty_dirs() -> None:
    """Remove all empty directories in the current working directory."""
    for directory in os.listdir("."):
        if os.path.isdir(directory) and not os.listdir(directory):
            os.rmdir(directory)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default="nuclei.txt",
                        help="Filename to read the repositories from. Default is 'nuclei.txt'")
    args = parser.parse_args()

    # Path to the file
    filepath = os.path.join(script_dir, args.file)

    # Backup original file before any modifications
    shutil.copy2(filepath, f'{filepath}.bak')

    # Create a directory for the repositories if it doesn't exist
    if not os.path.exists("nuclei_templates"):
        os.makedirs("nuclei_templates")

    # Change the current working directory
    os.chdir("nuclei_templates")

    urls = read_urls_from_file(filepath)

    # Initialize counters for the total, successful, and failed attempts
    total_attempts, successful_downloads, failed_downloads, invalid_urls = 0, 0, 0, 0

    for index, url in enumerate(urls):
        if url.startswith('#'):  # ignore commented lines
            continue

        total_attempts += 1

        if not is_url_valid(url):
            print(f"URL not valid: {url}")
            invalid_urls += 1
            with open(filepath, 'r') as f:
                lines = f.readlines()
            with open(filepath, 'w') as f:
                for line in lines:
                    if line.strip() == url:
                        f.write(f"# {url}\n")  # Comment out the invalid url
                    else:
                        f.write(line)
            continue
        
        if requires_auth(url):
            print(f"URL requires authentication, skipping: {url}")
            continue
        
        success, _ = clone_repo(url, index)

        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1

    remove_empty_dirs()

    # Print summary
    print(f"\nTotal attempted downloads: {total_attempts}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"Ignored invalid URLs: {invalid_urls}")

if __name__ == "__main__":
    main()
