#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import git

def clone_repos(repo_file):
    # Read file
    with open(repo_file, 'r') as file:
        repos = file.read().splitlines()

    # Create a directory to store the repositories if it doesn't exist
    os.makedirs('nuclei_templates', exist_ok=True)

    # Change current directory to the newly created one
    os.chdir('nuclei_templates')

    # Loop over the repos and clone them
    for repo in repos:
        try:
            print(f"Cloning {repo}")
            git.Repo.clone_from(repo, os.path.basename(repo))
            print(f"Successfully cloned {repo}")
        except git.GitCommandError as e:
            print(f"Failed to clone {repo}. Reason: {str(e)}")

    print("Done cloning repositories!")

# Provide the text file containing the list of repositories
clone_repos('nuclei.txt')
