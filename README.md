# Description

This set of Python scripts helps to automate the process of gathering and organizing various GitHub repositories which contain Nuclei templates. The first script, getnucleitemplates.py, clones repositories from a list in a text file, checks for validity of the URLs, handles any issues with gists or duplicates, and organizes the clones in a directory. The second script, searchmore.py, uses the GitHub API to search for additional repositories containing Nuclei templates, prompts the user if they wish to clone the discovered repositories, and adds them to the list.

Nuclei is a project that allows you to customize scanning for specific vulnerabilities, and these templates are the definitions of those specific vulnerabilities. This script helps in automating the process of getting those templates.

# Installation

# Prerequisites

* Python 3.6 or newer: You can download it from the official Python website.
* GitPython package: You can install it via pip with the following command in your terminal:

  pip install GitPython

* Git: This script uses git commands to clone repositories. If you haven't installed git yet, you can download it from the official Git website.

# Usage

* Update the nuclei.txt file with the list of repositories you want to clone.
* Run the getnucleitemplates.py script to clone the repositories. It will clone the repositories into a new nuclei_templates directory, ignore commented lines, and comment out any invalid URLs.

  python3 getnucleitemplates.py
  
  By default it uses the provided nuclei.txt file. With -f (--file) you can provide a custom file.

* You will see a summary of the attempted downloads, successful downloads, failed downloads, ignored gists, and ignored invalid URLs. Any failed or invalid repository URLs will be commented out in nuclei.txt.
* To find more repositories, run the searchmore.py script. This will search GitHub for repositories containing the string "nuclei-templates". It will handle pagination to ensure all possible repositories are found, and respect GitHub's rate limits.

  python3 searchmore.py

You will be presented with a summary of the found repositories. If you choose to download the found repositories, they will be added to the nuclei.txt file and getnucleitemplates.py will be executed to clone them.

Please note that using the GitHub API may require a personal access token if you need to make a large number of requests. Refer to the GitHub API documentation for more information.

# Notes

The scripts will treat GitHub Gist links as invalid URLs and ignore them.

The scripts check for the existence of repositories before attempting to clone them to avoid errors.

For the searchmore.py script, the search terms are currently hard-coded. If you want to search for different terms, you will need to modify the script.

IMPORTANT: This script now asks for your GitHub token in the terminal. Make sure to handle it carefully, as this token provides access to your GitHub account. Never share it with anyone and don't store it in a publicly accessible location. Consider using environment variables or a secure credential management system for storing sensitive information like this.

You can generate a personal access token on GitHub by following these steps:

1. In the upper-right corner of any page, click your profile photo, then click Settings.
2. In the left sidebar, click Developer settings.
3. In the left sidebar, click Personal access tokens.
4. Click Generate new token.
5. Give your token a descriptive name.
6. Select the scopes you wish to grant to this token. To access public repositories, you do not need to check any boxes.
7. Click Generate token.
8. Copy the token to your clipboard. For security reasons, after you navigate off the page, you will not be able to see the token again.

If you want to do unauthenticated search on Github API, just press 'Enter' when request for API token.

# Legal Disclaimer

This information, code, or software is provided "as is" and without any express or implied warranties, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose. The use of this information, code, or software is entirely at your own risk.

The creator or provider of this information, code, or software does not assume responsibility for any errors that may appear in the provided materials, nor for any damages or losses that may arise from its use, whether such damages be direct, indirect, incidental, special, consequential, or otherwise.

Any application or use of the information, code, or software should be done only after carefully evaluating its appropriateness and applicability to your specific situation. The user assumes full responsibility for any decisions made based on this information, code, or software.

The content provided here is for informational purposes only and should not be construed as legal, financial, or professional advice. Users are urged to consult with an appropriate professional for specific advice tailored to their situation.
