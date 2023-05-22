#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import requests
import json
import time
import os
import subprocess
import shutil
import yaml

def search_github_repos(query_terms):
    base_url = "https://api.github.com"
    token = input("Please enter your GitHub API token (press 'Enter' for unauthenticated): ")
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token.strip():  # If the user provided a token
        headers['Authorization'] = f'token {token}'
    search_url = f"{base_url}/search/repositories"
    search_params = {'q': ' OR '.join(query_terms), 'page': 1}

    found_repos = []

    shutil.copy("nuclei.txt", "nuclei.txt.bak")
    with open("nuclei.txt.bak", "r") as file:
        existing_repos = set(line.strip() for line in file.readlines() if line.strip() and not line.startswith("#"))

    while True:
        response = requests.get(search_url, headers=headers, params=search_params)

        if response.status_code != 200:
            print(f"Error with status code: {response.status_code}")
            return

        rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

        if rate_limit_remaining < 10:  # adjust the number as needed
            reset_time = rate_limit_reset - time.time()
            if reset_time > 0:
                print(f"Approaching rate limit. Sleeping for {reset_time} seconds.")
                time.sleep(reset_time)

        data = response.json()

        for repo in data["items"]:
            # Check if repository contains .yaml or .yml files
            contents_url = f"{base_url}/repos/{repo['full_name']}/contents"
            contents_response = requests.get(contents_url, headers=headers)

            if contents_response.status_code != 200:
                continue

            contents = contents_response.json()

            yaml_files = [file for file in contents if file['name'].endswith(('.yaml', '.yml'))]

            for yaml_file in yaml_files:
                yaml_file_url = yaml_file['download_url']
                yaml_file_content = requests.get(yaml_file_url).text

                try:
                    yaml_data = yaml.safe_load(yaml_file_content)
                except yaml.YAMLError as e:
                    print(f"YAML parsing error for file {yaml_file['name']}: {e}")
                    print("Skipping this file due to YAML parsing error.")
                    continue

                # Check if the YAML file contains the required fields for a Nuclei template
                if 'id' in yaml_data and 'requests' in yaml_data:
                    repo_url = repo['html_url']
                    if repo_url not in existing_repos:
                        print(f"Found New Nuclei Template Repo: {repo_url}")
                        found_repos.append(repo_url)
                    break

        if 'next' not in response.links:
            break

        search_params['page'] += 1

    print(f"\nFound {len(found_repos)} new Nuclei Template repositories.")
    user_input = input("Do you want to download the found repositories? (y/n): ")

    if user_input.lower() == 'y':
        with open("nuclei.txt", "a") as file:  # Open in append mode
            for repo in found_repos:
                file.write(f"{repo}\n")

        print("Running getnucleitemplates.py...")
        subprocess.run(["python3", "getnucleitemplates.py"])

if __name__ == "__main__":
    search_terms = ["nuclei-templates", "nuclei-scripts", "nuclei-configs"]
    search_github_repos(search_terms)
