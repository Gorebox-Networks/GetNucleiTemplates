#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: David Espejo (Fortytwo Security)
import os
import subprocess
import argparse
import re
import yaml
import logging
import hashlib
import shutil

# Global variable to track user's choice for automatic fixing
fix_all = False

def fix_template_validation_errors(file_path, output, logger):
    """
    Processes the output from the 'nuclei -validate' command, attempting to fix any errors.
    """
    global fix_all

    # Match 'field not found' errors
    errors = re.findall(r"field (\w+) not found", output.stderr)
    if errors:
        fix_errors(file_path, errors)
        return True

    # If the template still isn't valid, log the error
    revalid_output = subprocess.run(["nuclei", "-validate", "-t", file_path], capture_output=True, text=True)
    if revalid_output.returncode != 0:
        logger.error(f"Failed to fix {file_path}: {revalid_output.stderr}")
        return False

    return True

def setup_logger(debug_mode):
    logger = logging.getLogger('validator')
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    file_handler = logging.FileHandler('validation_errors.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

def hash_directory_content(directory):
    """
    Returns SHA256 hash of a directory's content.
    """
    sha256_hash = hashlib.sha256()

    # Traverse directory recursively
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
            except Exception as e:
                logger.error(f"Failed to read {file_path} while hashing: {e}")
                return None
    return sha256_hash.hexdigest()

def hash_file_content(file_path, logger):
    """
    Returns SHA256 hash of a file's content.
    """
    try:
        with open(file_path, 'rb') as file:
            bytes = file.read() # read entire file as bytes
            return hashlib.sha256(bytes).hexdigest()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None

def identify_error(error_message):
    """
    Analyzes the error message and returns a string identifying the type of error.

    :param error_message: The error message to analyze.
    :return: A string identifying the type of error.
    """

    # TODO: implement error identification based on the error_message

    return "unknown_error"

def check_duplicate_dirs(directory, logger):
    """
    Checks for duplicate directories in the given directory.
    """
    dir_hashes = {}
    duplicates = []
    dirs_removed = 0
    dirs_ignored = 0
    ignore_dirs = ['.git', '.github']

    for root, dirs, _ in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            dir_hash = hash_directory_content(dir_path)

            if dir_hash in dir_hashes:
                duplicates.append((dir_path, dir_hashes[dir_hash]))  # Store pair of duplicate dirs
            else:
                dir_hashes[dir_hash] = dir_path

    # Prompt user to fix duplicates
    for dir1, dir2 in duplicates:
        print(f"\nDuplicate directories found:\n- {dir1}\n- {dir2}")
        user_input = input(f"Do you want to delete the second directory? (y/n/a for all duplicates): ")

        if user_input.lower() in ['y', 'a']:
            try:
                shutil.rmtree(dir2)
                print(f"Deleted {dir2}")
                dirs_removed += 1
            except Exception as e:
                logger.error(f"Failed to delete {dir2}: {e}")
        else:
            dirs_ignored += 1

        # If user chooses to delete all duplicates, break the loop
        if user_input.lower() == 'a':
            break

    return dirs_removed, dirs_ignored

def check_duplicates(directory, logger):
    """
    Checks for duplicate template files in the given directory, ignoring certain directories.
    """
    ignore_dirs = ['.git', '.github']
    file_hashes = {}
    duplicates = []
    files_removed = 0
    files_ignored = 0

    for root, dirs, files in os.walk(directory):
        # Skip directories in ignore list
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            file_hash = hash_file_content(file_path, logger)

            if file_hash is not None:
                if file_hash in file_hashes:
                    duplicates.append((file_path, file_hashes[file_hash]))  # Store pair of duplicate files
                else:
                    file_hashes[file_hash] = file_path

    # Prompt user to fix duplicates
    for file1, file2 in duplicates:
        print(f"\nDuplicate templates found:\n- {file1}\n- {file2}")
        user_input = input(f"Do you want to delete the second file? (y/n/a for all duplicates): ")

        if user_input.lower() in ['y', 'a']:
            try:
                os.remove(file2)
                print(f"Deleted {file2}")
                files_removed += 1
            except Exception as e:
                logger.error(f"Failed to delete {file2}: {e}")
        else:
            files_ignored += 1

        # If user chooses to delete all duplicates, break the loop
        if user_input.lower() == 'a':
            break

    return files_removed, files_ignored

def fix_errors(file_path, errors):
    global fix_all
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    unrecognized_fields = ['risk', 'redirect', 'url', 'detections', 'params', 'reference']
    fields_to_remove = []

    for error in errors:
        error_match = re.match("line (\d+): field (\w+) not found", error)

        if error_match:
            line, field = error_match.groups()
            if field in unrecognized_fields:
                print(f"Found unrecognized field '{field}' in line {line} of {file_path}")
                if fix_all:
                    # If the user already chose 'a' for this field, remove it
                    if field in fields_to_remove:
                        if field in data:
                            del data[field]
                            print(f"Automatically removed '{field}' from {file_path}")
                else:
                    user_input = input(f"Do you want to remove '{field}'? (y/n/a for all of same type): ")
                    if user_input.lower() == 'y':
                        if field in data:
                            del data[field]
                            print(f"Removed '{field}' from {file_path}")
                    elif user_input.lower() == 'a':
                        fields_to_remove.append(field)
                        if field in data:
                            del data[field]
                            print(f"Removed '{field}' from {file_path}")

        if "cannot unmarshal !!seq into map[string]string" in error:
            print(f"Cannot automatically fix unmarshalling error in line {line} of {file_path}, manual fix required.")

    # Remove all instances of the fields that the user chose 'a' for
    for field in fields_to_remove:
        if field in data:
            del data[field]
            print(f"Automatically removed remaining instances of '{field}' from {file_path}")

    with open(file_path, 'w') as file:
        yaml.safe_dump(data, file)

def fix_template(file_path, logger):
    """
    Fixes common errors in nuclei templates.
    """
    global fix_all
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)

        if 'id' in data and not re.match('^([a-zA-Z0-9]+[-_])*[a-zA-Z0-9]+$', data['id']):
            new_id = re.sub('[^a-zA-Z0-9-_]', '_', data['id'])
            new_id = re.sub('_{2,}', '_', new_id)  # replace consecutive underscores with single underscore
            new_id = re.sub('^-|-$', '', new_id)  # remove leading or trailing hyphens
            if new_id != data['id']:
                if fix_all:
                    data['id'] = new_id
                else:
                    print(f"\nProposed fix: Change id from '{data['id']}' to '{new_id}'")
                    user_input = input("Do you want to apply this fix? (y/n/a for all): ")
                    if user_input.lower() == 'y' or user_input.lower() == 'a':
                        data['id'] = new_id
                        if user_input.lower() == 'a':
                            fix_all = True

        # Check and fix invalid attack type
        if 'attack' in data and data['attack'] not in ['network', 'clusterbomb', 'pitchfork', 'batteringram']:
            if fix_all:
                data['attack'] = 'network'  # default attack type
            else:
                print(f"\nProposed fix: Change attack type from '{data['attack']}' to 'network'")
                user_input = input("Do you want to apply this fix? (y/n/a for all): ")
                if user_input.lower() == 'y' or user_input.lower() == 'a':
                    data['attack'] = 'network'
                    if user_input.lower() == 'a':
                        fix_all = True

        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file)

        return True

    except yaml.YAMLError as err:
        logger.error(f"File {file_path}: Failed to load/fix YAML file - {err}")
        return False

def validate_templates(directory, logger):
    successful_fixes = 0
    failed_fixes = 0
    unresolved_errors = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.yaml', '.yml')):
                file_path = os.path.join(root, file)
                try:
                    output = subprocess.run(["nuclei", "-validate", "-t", file_path], capture_output=True, text=True)
                    if output.returncode != 0:
                        print(f"\nError in {file_path}:")
                        print(output.stderr)

                        fix_template(file_path, logger) # Call fix_template in all cases
                        successful_fixes += 1

                        if "invalid field format for 'id'" in output.stderr:
                            print(f"Invalid id in {file_path}, fix applied.")
                        elif "yaml: line" in output.stderr:
                            print(f"YAML syntax error in {file_path}, manual fix required.")
                            unresolved_errors += 1
                        else:
                            print(f"An unknown error occurred in {file_path}, manual fix required.")
                            unresolved_errors += 1

                except Exception as e:
                    print(f"An error occurred while validating {file_path}: {e}")
                    unresolved_errors += 1

    return successful_fixes, failed_fixes, unresolved_errors

    check_duplicates(directory, logger)

    # If fixes were applied and it's not a recursive call, validate again
    if successful_fixes > 0 and not recursive_call:
        print("\nRevalidating templates after applying fixes...")
        new_successful_fixes, new_failed_fixes, new_unresolved_errors = validate_templates(directory, recursive_call=True)
        successful_fixes += new_successful_fixes
        failed_fixes += new_failed_fixes
        unresolved_errors += new_unresolved_errors
    elif not recursive_call:  # Calculate unresolved errors only on the first run
        unresolved_errors = len(re.findall("Could not validate templates: errors occured during template validation", result.stderr))

    return successful_fixes, failed_fixes, unresolved_errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode")
    parser.add_argument("-dir", "--directory", default='nuclei_templates', help="Directory with nuclei templates to validate")
    args = parser.parse_args()

    logger = setup_logger(args.debug)

    print("Checking for duplicated directories...")
    dirs_removed, dirs_ignored = check_duplicate_dirs(args.directory, logger)

    print("Checking for duplicated templates...")
    files_removed, files_ignored = check_duplicates(args.directory, logger)

    # Validate the templates and print the summary
    successful_fixes, failed_fixes, unresolved_errors = validate_templates(args.directory, logger)
    print(f"\nValidation summary:\n- Duplicate directories removed: {dirs_removed}\n- Duplicate directories ignored: {dirs_ignored}")
    print(f"- Duplicate templates removed: {files_removed}\n- Duplicate templates ignored: {files_ignored}")
    print(f"- Successful fixes: {successful_fixes}\n- Failed fixes: {failed_fixes}\n- Unresolved errors: {unresolved_errors}")

if __name__ == "__main__":
    main()
