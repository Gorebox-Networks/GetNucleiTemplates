#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import requests
import json
import time
import os
import subprocess

def search_github_repos(query_terms):
    base_url = "https://api.github.com"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    search_url = f"{base_url}/search/repositories"
    search_params = {'q': ' OR '.join(query_terms), 'page': 1}

    found_repos = []

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
            if any(file['name'].endswith(('.yaml', '.yml')) for file in contents):
                print(f"Found Nuclei Template Repo: {repo['html_url']}")
                found_repos.append(repo['html_url'])

        if 'next' not in response.links:
            break

        search_params['page'] += 1

    print(f"\nFound {len(found_repos)} Nuclei Template repositories.")
    user_input = input("Do you want to download the found repositories? (y/n): ")

    if user_input.lower() == 'y':
        with open("nuclei.txt", "a") as file:
            for repo in found_repos:
                file.write(f"{repo}\n")

        print("Running getnucleitemplates.py...")
        subprocess.run(["python3", "getnucleitemplates.py"])

if __name__ == "__main__":
    search_terms = ["nuclei-templates", "nuclei-scripts", "nuclei-configs"]
    search_github_repos(search_terms)
