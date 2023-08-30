#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import subprocess
import requests
from typing import List
import shutil
import argparse
from colorama import Fore, Style
from dotenv import load_dotenv, set_key
import getpass
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

print(Style.RESET_ALL)
success_prefix = f"{Fore.GREEN}[+]{Style.RESET_ALL}"
failure_prefix = f"{Fore.RED}[-]{Style.RESET_ALL}"
url_color = Fore.YELLOW
fail_color = Fore.RED
info_color = Fore.CYAN

def read_urls_from_file(filepath: str) -> List[str]:
    open(filepath, 'a').close()
    with open(filepath, 'r') as f:
        urls = f.readlines()
    return [url.strip() for url in urls if url.strip()]

def get_github_api_key():
    api_key = os.getenv('GITHUB_API_KEY')
    if not api_key:
        api_key = getpass.getpass(f"{Fore.GREEN}Enter your Github API Key (or press 'Enter' for unauthenticated search): {Style.RESET_ALL}")
        set_key(".env", "GITHUB_API_KEY", api_key)
    return api_key

def is_url_valid(url: str) -> bool:
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code != 404
    except requests.ConnectionError:
        return False

def clone_repo(url: str, index: int, dir: str) -> bool:
    repo_name = url.split('/')[-1]
    repo_name = f"{repo_name}_{index}"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    clone_success = False

    if not os.path.exists(dir):
        os.makedirs(dir)

    if os.path.exists(repo_name):
        print(f"{info_color}Repository {repo_name} already exists. Skipping.{Style.RESET_ALL}")
        return False

    try:
        print(f"{success_prefix} Cloning {url_color}{url}{Style.RESET_ALL} into {repo_name}")
        process = subprocess.Popen(
            ['git', 'clone', '--depth', '1', url, repo_name],
            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, 'git')
        else:
            print(f"{Fore.GREEN}[+] Successful cloning {url}{Style.RESET_ALL}")
            clone_success = True

    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}[-] Failed cloning repo {url}. Reason: {e}{Style.RESET_ALL}")

    return clone_success

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default="nuclei.txt", help="Filename to read the repositories from. Default is 'nuclei.txt'")
    args = parser.parse_args()

    filepath = os.path.join(script_dir, args.file)
    shutil.copy2(filepath, f'{filepath}.bak')

    dir = "nuclei-templates"
    if not os.path.exists(dir):
        os.makedirs(dir)

    os.chdir(dir)

    attempted_urls = read_urls_from_file('attempted.txt')
    urls = read_urls_from_file(filepath)

    total_attempts, successful_downloads, failed_downloads, invalid_urls = 0, 0, 0, 0

    valid_urls = [url for url in urls if not url.startswith('#')]
    invalid_urls += len(urls) - len(valid_urls)

    for index, url in enumerate(valid_urls):
        total_attempts += 1
        print(f"\n{info_color}--- Repository {total_attempts} ---{Style.RESET_ALL}")

        if url in attempted_urls:
            print(f"{info_color}URL {url_color}{url}{Style.RESET_ALL} already cloned. Skipping.")
            continue

        if not is_url_valid(url):
            print(f"{fail_color}Invalid URL: {url}{Style.RESET_ALL}")
            invalid_urls += 1
            continue

        clone_success = clone_repo(url, index, dir)

        if clone_success:
            successful_downloads += 1
        else:
            failed_downloads += 1

        with open('attempted.txt', 'a') as f:
            f.write(f"{url}\n")

    print(f"\n{info_color}---- Summary ----")
    print(f"{info_color}Total URLs attempted: {total_attempts}")
    print(f"{success_prefix} Successfully downloaded: {successful_downloads}")
    print(f"{failure_prefix} Failed to download: {failed_downloads}")
    print(f"{info_color}Invalid URLs: {invalid_urls}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
