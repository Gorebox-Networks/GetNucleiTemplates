#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import git

# Create a directory for the repositories if it doesn't exist
if not os.path.exists("nuclei_templates"):
    os.makedirs("nuclei_templates")

# Change the current working directory
os.chdir("nuclei_templates")

# Read URLs from the text file
with open('../nuclei.txt', 'r') as f:
    urls = f.readlines()

# Counter for the total, successful, and failed attempts
total_attempts = 0
successful_downloads = 0
failed_downloads = 0
ignored_gists = 0

for index, url in enumerate(urls):
    url = url.strip()  # Remove newline characters
    
    # Ignore if URL is a gist
    if "gist.github.com" in url:
        print(f"Ignoring gist: {url}")
        ignored_gists += 1
        continue

    repo_name = url.split('/')[-1]  # Extract repository name
    repo_name = f"{repo_name}_{index}"  # Append index to make it unique
    total_attempts += 1

    try:
        print(f"Cloning {url} into {repo_name}")
        git.Repo.clone_from(url, repo_name)  # Clone the repository
        successful_downloads += 1
    except Exception as e:
        print(f"Failed to clone {url}. Reason: {e}")
        failed_downloads += 1

# Remove empty directories or failed downloads
for directory in os.listdir("."):
    if os.path.isdir(directory) and not os.listdir(directory):
        os.rmdir(directory)

# Print summary
print(f"\nTotal attempted downloads: {total_attempts}")
print(f"Successful downloads: {successful_downloads}")
print(f"Failed downloads: {failed_downloads}")
print(f"Ignored gists: {ignored_gists}")
