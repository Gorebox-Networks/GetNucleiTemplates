#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import git
import requests

# create directory for the repositories if it doesn't exist
if not os.path.exists("nuclei_templates"):
    os.makedirs("nuclei_templates")

# Change the current working directory
os.chdir("nuclei_templates")

# Read URLs from the text file
with open('../nuclei.txt', 'r') as f:
    urls = f.readlines()

for index, url in enumerate(urls):
    url = url.strip()  # Remove newline characters
    try:
        repo_name = url.split('/')[-1]  # Extract repository name
        repo_name = f"{repo_name}_{index}"  # Append index to make it unique
        print(f"Cloning {url} into {repo_name}")
        git.Repo.clone_from(url, repo_name)  # Clone the repository
    except Exception as e:
        print(f"Failed to clone {url}. Reason: {e}")
