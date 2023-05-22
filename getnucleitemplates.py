#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import git
import requests
import fileinput
from typing import List, Tuple


def read_urls_from_file(filepath: str) -> List[str]:
    """Read URLs from the provided text file, ignoring commented lines."""
    with open(filepath, 'r') as f:
        urls = f.readlines()
    return [url.strip() for url in urls if url.strip()]


def is_url_valid(url: str) -> bool:
    """Check if the URL exists and is not a 404."""
    try:
        response = requests.get(url)
        return response.status_code != 404
    except requests.ConnectionError:
        return False


def clone_repo(url: str, index: int) -> Tuple[bool, bool, bool]:
    """Attempt to clone the repository from the given URL."""
    # Ignore if URL is a gist
    if "gist.github.com" in url:
        print(f"Ignoring gist: {url}")
        return False, True, False

    repo_name = url.split('/')[-1]  # Extract repository name
    repo_name = f"{repo_name}_{index}"  # Append index to make it unique

    if not is_url_valid(url):
        print(f"URL not valid: {url}")
        return False, False, True

    try:
        print(f"Cloning {url} into {repo_name}")
        git.Repo.clone_from(url, repo_name)  # Clone the repository
        return True, False, False
    except Exception as e:
        print(f"Failed to clone {url}. Reason: {e}")
        return False, False, False


def remove_empty_dirs() -> None:
    """Remove all empty directories in the current working directory."""
    for directory in os.listdir("."):
        if os.path.isdir(directory) and not os.listdir(directory):
            os.rmdir(directory)


def main():
    # Create a directory for the repositories if it doesn't exist
    if not os.path.exists("nuclei_templates"):
        os.makedirs("nuclei_templates")

    # Change the current working directory
    os.chdir("nuclei_templates")

    urls = read_urls_from_file('../nuclei.txt')

    # Initialize counters for the total, successful, and failed attempts
    total_attempts, successful_downloads, failed_downloads, ignored_gists, invalid_urls = 0, 0, 0, 0, 0

    for index, url in enumerate(urls):
        if url.startswith('#'):  # ignore commented lines
            ignored_gists += 1
            continue

        total_attempts += 1
        success, is_gist, is_invalid = clone_repo(url, index)

        if success:
            successful_downloads += 1
        elif is_gist:
            ignored_gists += 1
        elif is_invalid:
            invalid_urls += 1
            with open('../nuclei.txt', 'a') as f:  # Append mode
                f.write(f"# {url}\n")  # Comment out the invalid url
            with fileinput.FileInput('../nuclei.txt', inplace=True, backup='.bak') as file:
                for line in file:
                    if url in line:
                        print(line.replace(url, f"# {url}"), end='')
        else:
            failed_downloads += 1

    remove_empty_dirs()

    # Print summary
    print(f"\nTotal attempted downloads: {total_attempts}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"Ignored gists: {ignored_gists}")
    print(f"Ignored invalid URLs: {invalid_urls}")


if __name__ == "__main__":
    main()
