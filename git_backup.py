#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Dani Westlake
# Created Date: 2022-05-25
# version ='1.0'
# ---------------------------------------------------------------------------
"""
Created to pull an archive of the Brainlabs organisation
from Github and save to googledrive

TODO:
- Error handling
"""
# ---------------------------------------------------------------------------

# Import os.path to allow script to be run from outside project directory
from os import path, remove

# Allow command line arguments
import argparse

# Config parser for reading config file with auth key
import configparser
from time import sleep
from datetime import datetime, timedelta

# Import error handling
import logging

# Import json compatability
import json

# Import io module
import io

# import math ceiling
from math import ceil

# requests to make API request to Git
import requests

# Import socket to allow Google API to upload large files without timing out
import socket

# Import Google Auth and Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient import errors as GoogleErrors
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

# Imports the Cloud Logging client library
import google.cloud.logging


# Setup/parse command line arguments
argparser = argparse.ArgumentParser()
argparser.add_argument(
    "--config",
    "-c",
    help="Specify alternate config file",
    type=str,
    default="config.ini",
)
argparser.add_argument(
    "--gitenv",
    "-g",
    help="The section of the config file \
        that contains GitHub login information",
    type=str,
    default="git-prod",
)
argparser.add_argument(
    "--googledrive",
    "-o",
    help="The section of the config file that\
         contains Google Drive folder information",
    type=str,
    default="drive-prod",
)
argparser.add_argument(
    "--level",
    "-l",
    help="Set log level. Accepted values: \
        DEBUG, INFO or WARN. Default value is INFO",
    type=str,
    default="INFO",
)
argparser.add_argument(
    "--driveauth",
    "-d",
    help="Specify alternate Google Auth file",
    type=str,
    default="client_secret.json",
)
argparser.add_argument(
    "--unlock",
    "-u",
    help="Perform Github repo unlock only",
    type=bool,
    default=False
)
args = argparser.parse_args()


# Set run date for filename
today = datetime.now()
rundate = today.strftime("%Y-%m-%d-%H-%M")
# Set retention period in days for logs and archives
retention = 30
# Set logfile location as the root of project
ROOT_DIR = path.dirname(path.abspath(__name__))
LOGFILE = f"{ROOT_DIR}/git_backup_{rundate}.log"
# Logging defaults
if args.level.upper() == "DEBUG":
    LOG_LEVEL = logging.DEBUG
    MESSAGE = "Logging set to DEBUG - This will expose secrets in terminal"
elif args.level.upper() == "INFO":
    LOG_LEVEL = logging.INFO
    MESSAGE = "Logging set to INFO - Processes will be explained"
else:
    LOG_LEVEL = logging.WARN
    MESSAGE = "Logging set to WARN - Only warnings and errors will be logged"


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
    level=LOG_LEVEL
)

filelogger = logging.FileHandler(LOGFILE)
if args.level.upper() == "DEBUG":
    filelogger.setLevel(logging.INFO)
else:
    filelogger.setLevel(LOG_LEVEL)

fileformat = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
filelogger.setFormatter(fileformat)

logging.getLogger('').addHandler(filelogger)

log = logging.getLogger(__name__)

if args.level.upper() == "DEBUG":
    logging.FileHandler(LOGFILE).setLevel("INFO")

logging.info(MESSAGE)
MESSAGE = f"logfile is {LOGFILE}"
logging.info(MESSAGE)


# Read config file
configfile = ROOT_DIR + "/" + (args.config)
log_message = f"Config file being used - {configfile}"
logging.debug(log_message)
config = configparser.ConfigParser()
config.read(configfile)

# allow Google API to upload large files without timing out
socket.setdefaulttimeout(60 * 30)


def google_cloud_logging():
    service_account_info = ROOT_DIR + "/" + args.driveauth
    scopes = ["https://www.googleapis.com/auth/logging.write"]

    creds = service_account.Credentials.from_service_account_file(
        service_account_info, scopes=scopes
    )

    # Instantiates a GCP logging client
    client = google.cloud.logging.Client(credentials=creds)

    # Retrieves a Cloud Logging handler based on the environment
    # you're running in and integrates the handler with the
    # Python logging module. By default this captures all logs
    # at INFO level and higher
    client.setup_logging()


def git_login():
    """Function to test Github login is working"""
    token = config[args.gitenv]["token"]
    url = "https://api.github.com/user"
    header = {"Authorization": f"token {token}"}
    login_log_message = f"git_login - GitHub token is {token}"
    logging.debug(login_log_message)
    login_log_message = f"git_login - Github URL is {url}"
    logging.debug(login_log_message)
    try:
        response = requests.get(url, headers=header)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            return "Success"
    except requests.exceptions.RequestException as error:
        logging.critical("git_login - Login failed")
        logging.critical(error)


def google_login():
    """Function to test Google Auth is working"""
    try:
        service_account_info = ROOT_DIR + "/" + args.driveauth
        scopes = ["https://www.googleapis.com/auth/drive"]

        creds = service_account.Credentials.from_service_account_file(
            service_account_info, scopes=scopes
        )

        build("drive", "v3", credentials=creds, cache_discovery=False)

        return "Success"
    except FileNotFoundError as error:
        logging.critical("google_login - Login failed")
        logging.critical(error)
    except GoogleErrors.Error as error:
        logging.critical("google_login - Login failed")
        logging.critical(error)


def list_repos(page):
    """Create list of repos under the named Org"""
    token = config[args.gitenv]["token"]
    url = config[args.gitenv]["url"] + "repos"
    header = {"Authorization": f"token {token}"}
    params = (
        ("per_page", "100"),
        ("page", page)
    )

    try:
        repos = {}
        total_repos = 0
        set_count = 0
        all_repos = ""
        response = requests.get(url, headers=header, params=params)
        r_json = json.loads(response.text)
        response.raise_for_status()
        while response.text != '[]':
            if response.status_code == requests.codes.ok:
                for i in r_json:
                    set_count += 1
                    repos[page] = {}
                    repos[page]['repos'] = ""
                    repos[page]['retry_count'] = 0
                    repos[page]['mig_url'] = ""
                    repo_name = i["full_name"]
                    list_log_message = f"list_repos - \
Found {repo_name} - Adding to repos list - set {page}"
                    total_repos += 1
                    logging.info(list_log_message)
                    if set_count > 1:
                        all_repos += ", "
                    all_repos += "'"+repo_name+"'"
                    repos[page]['repos'] = all_repos
                page += 1
                set_count = 0
                all_repos = ""
                params = (
                    ("per_page", "100"),
                    ("page", page)
                )

                logging.info("Checking for more repos")

                response = requests.get(
                    url,
                    headers=header,
                    params=params
                )

                r_json = json.loads(response.text)
        logging.info("No more repos found")
        list_message = f"Total repos found : {total_repos}"
        logging.info(list_message)
        list_message = f'This will create \
{ceil(total_repos / 100)} archive files'
        logging.info(list_message)
        return repos
    except requests.exceptions.RequestException as error:
        logging.error("An error occoured")
        logging.error(error)


def start_archive(repos):
    """Function to start a new archive process"""
    all_arc_url = {}
    for i in list(repos.keys()):
        start_archive_message = f'Attempting to archive repo set {i}'
        logging.info(start_archive_message)
        str_repos = "["+str(repos[i]['repos']).replace("'", '"')+"]"
        token = config[args.gitenv]["token"]
        url = config[args.gitenv]["url"] + "migrations"
        payload = f"""{{"lock_repositories":false,\
"repositories":{str_repos}}}"""

        header = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}",
        }

        try:
            response = requests.post(url, headers=header, data=payload)
            r_json = json.loads(response.text)
            arc_url = r_json["url"]
            response.raise_for_status()
            if response.status_code == 201:
                logging.info(
                    "start_archive - \
returned 201 - Created"
                )
                all_arc_url[i] = arc_url
            if response.status_code == 404:
                logging.warning(
                    "start_archive - \
returned 404 - Not Found"
                )
                all_arc_url[i] = "404"
            if response.status_code == 422:
                logging.warning(
                    "start_archive - \
returned 422 - Validation Failed"
                )
                all_arc_url[i] = "422"
        except requests.exceptions.RequestException as error:
            logging.error("An error occoured")
            logging.error(error)
    return all_arc_url


def check_archive(url):
    """Check archive status
    Cannot be downloaded unless status is "Exported"""

    token = config[args.gitenv]["token"]
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }
    all_arc_state = {}
    for i in url.keys():
        try:
            response = requests.get(url[i]['mig_url'], headers=header)
            r_json = json.loads(response.text)
            arc_state = r_json["state"]
            response.raise_for_status()
            if response.status_code == requests.codes.ok:
                check_archive_message = f'check_archive - \
Archive set {i} status : {arc_state}'
                logging.debug(check_archive_message)
                if arc_state == "exported":
                    check_archive_message = f'Archive set \
{i} is ready for download'
                    logging.info(check_archive_message)
                all_arc_state[i] = arc_state
        except requests.exceptions.RequestException as error:
            logging.error("An error occoured")
            logging.error(error)

    return all_arc_state


def pull_archive(archive_key, url):
    """Download archive as tarball
    Set to pull in chunks and upload from iostream"""

    token = config[args.gitenv]["token"]
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }

    arc_url = url + "/archive"
    pull_message = f'Archive URL - {arc_url}'
    logging.debug(pull_message)
    try:

        local_filename = "git-archive-" + rundate + \
            "-set-" + str(archive_key) + ".tar.gz"

        pull_message = f'archive filename - {local_filename}'

        response = requests.get(
            arc_url,
            headers=header,
            allow_redirects=True,
            stream=True
        )

        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            logging.info(
                "pull_archive - \
retreiving information to begin upload"
            )

            logging.info("Saving archive locally")

            local_file = open(local_filename, 'wb')
            for chunk in response.iter_content(chunk_size=512 * 1024 * 10):
                if chunk:
                    logging.debug("writing chunk")
                    local_file.write(chunk)

            upload_response = upload_archive(local_filename)
            upload_retry = 0

            while upload_response[0] is not None and upload_retry < 3:
                upload_retry += 1
                upload_retry_message = f'Upload failed - \
Retrying - Attempt {upload_retry} of 3'
                logging.warning(upload_retry_message)
                upload_response = upload_archive(local_filename)

            if upload_response[0] is None:
                logging.info('Upload success - cleaning up local files')
                remove(local_filename)
                return

            if upload_retry == 3:
                upload_message = f'Maximim retries reached \
for {local_filename} upload'
                logging.error(upload_message)
            pull_message = f'Upload response for \
{local_filename} - {response.status_code} - {response.reason}'
            logging.info(pull_message)
            return local_filename, response.reason
    except requests.exceptions.RequestException as error:
        logging.error("An error occourred")
        logging.error(error)


def upload_archive(file):
    """Upload to G-Drive in 5242880 byte chunks
    Called inside pull_archive() function
    client_secret.json pulled from Google developers console
    Specific to service account
    Folder in Google Drive needs to be shared with service account"""

    try:
        service_account_info = ROOT_DIR + "/" + args.driveauth
        scopes = ["https://www.googleapis.com/auth/drive"]

        creds = service_account.Credentials.from_service_account_file(
            service_account_info, scopes=scopes
        )

        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        file_body = {
            "name": file,
            "parents": [config[args.googledrive]["folder"]]
        }
        upload_message = f'file body: {file_body}'
        logging.debug(upload_message)

        # logging.info("creating file buffer")
        # buffer = io.BytesIO(data.content)

        media = MediaFileUpload(
            file, chunksize=5242880,
            mimetype="application/gzip",
            resumable=True
            )

        upload_data = service.files().create(
            body=file_body,
            media_body=media,
            supportsAllDrives=True,
            fields="id"
            )

        upload_message = f'upload data - {upload_data}'
        logging.debug(upload_message)
        logging.info(
            "upload archive - \
Uploading archive to Google Drive"
        )
        response = None
        logging.info('Beginning upload...')
        while response is None:
            progress, response = upload_data.next_chunk()
            if progress:
                upload_message = file + " upload : \
" + str(round(progress.progress() * 100)) + "%"
                logging.info(upload_message)
        logging.info('Upload complete')
        logging.debug(response)
        upload_archive_message = f"Archive uploaded \
as {file} - with ID: {response['id']}"
        logging.info(upload_archive_message)
        return progress, response['id']
    except GoogleErrors.Error as error:
        logging.error("upload_archive - \
    An error occourred while uploading the archive")
        logging.error(error)
        raise


def unlock_repo(url, repos):
    """Unlock repos after archive is pulled
    No longer used - Kept for reference"""
    lock_url = url + "/repos/"
    token = config[args.gitenv]["token"]
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }

    for i in repos:
        name = i.split("/")
        full_url = lock_url + name[1] + "/lock"
        try:
            response = requests.delete(full_url, headers=header)
            response.raise_for_status()
            if response.status_code == 204:
                unlock_log_message = f"Lock for {i} removed"
                logging.info(unlock_log_message)
        except requests.exceptions.RequestException as error:
            unlock_log_message = f"Unlock returned unexpected\
                HTTP code {response.status_code}"
            logging.error(unlock_log_message)
            logging.error(error)


def delete_archive(url):
    """To remove archive after use
    Not tested or used at present"""

    token = config[args.gitenv]["token"]
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }

    arc_url = url + "/archive"

    try:
        response = requests.delete(arc_url, headers=header)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            return response.status_code
    except requests.exceptions.RequestException as error:
        logging.error("An error occoured")
        logging.error(error)


def upload_logfile():
    """Upload log file to Google Drive"""
    service_account_info = ROOT_DIR + "/" + args.driveauth
    scopes = ["https://www.googleapis.com/auth/drive"]

    try:
        creds = service_account.Credentials.from_service_account_file(
            service_account_info, scopes=scopes
        )

        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        # Have to split the name otherwise it uploads as
        # "/git_backup/git_backup_YYYY-MM-DD.log"
        log_name = LOGFILE.split("/")[-1]

        file_body = {
            "name": log_name,
            "parents": [config[args.googledrive]["logfolder"]]
            }

        media = MediaFileUpload(LOGFILE, mimetype="text/plain", resumable=True)

        upload_message = f"Log file name- {log_name}"
        logging.debug(upload_message)

        upload_log = service.files().create(
            body=file_body, media_body=media, supportsAllDrives=True, fields="*"
        )

        return upload_log.execute()["id"]
    except GoogleErrors.Error as error:
        logging.error("upload_archive - \
An error occourred while uploading the archive")
        logging.error(error)
        raise


def remove_old_archives_and_logs():
    """Remove old archives and logs"""
    last_date = str((today - timedelta(retention)).date())

    logging.info("Removing old archives and logs")
    cleanup_message = f"Retention period set to \
{retention} days - Files older than {last_date} will be removed"
    logging.info(cleanup_message)

    service_account_info = ROOT_DIR + "/" + args.driveauth
    scopes = ["https://www.googleapis.com/auth/drive"]

    try:
        creds = service_account.Credentials.from_service_account_file(
            service_account_info, scopes=scopes
        )

        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        response = service.files().list(
            q="'" + config[args.googledrive]["logfolder"] + "' in parents \
or '" + config[args.googledrive]["folder"] + "' in parents \
and createdTime < " + last_date + "'",
            pageSize=100,
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
            ).execute()

        files = response.get('files', [])

        for f in files:
            try:
                service.files().delete(fileId=f["id"]).execute()
            except GoogleErrors.Error as error:
                logging.error(error)

    except GoogleErrors.Error as error:
        logging.error(error)


def main():
    """Main process
    Check GitHub login is OK`
    Gather list of repos
    Start archive process
    Wait for completion
    Download archive and send to Google Drive"""

    if git_login() == "Success":
        logging.info("Git login OK")
        if google_login() == "Success":
            logging.info("Google login OK")
            try:
                page = 1
                logging.info("Listing Repos")
                repos = list_repos(page)
                logging.info("Starting Archive Process")
                check = {}
                for key, item in (start_archive(repos)).items():
                    repos[key]['mig_url'] = item
                    check[key] = {}
                    check[key]['mig_url'] = item
                    main_message = f'Archive set {key} URL - {item}'
                    log.info(main_message)
                pause = 0
                log.info('Checking archive status...')
                while check:
                    skip_pause = False
                    status = check_archive(check)
                    for key, value in status.items():
                        if value == "exported":
                            main_message = f'Archive set {key} \
is exported - downloading'
                            logging.info(main_message)
                            pull_archive(key, repos[key]['mig_url'])
                            del check[key]
                            skip_pause = True
                        if value == "failed":
                            if repos[key]['retry_count'] < 3:
                                repos[key]['retry_count'] += 1
                                main_message = f'Archive set \
{key} failed - Attempting retry {repos[key]["retry_count"]}'
                                logging.info(main_message)
                                retry_repo = {}
                                retry_repo[key] = repos[key]
                                repos[key]['mig_url'] = (start_archive(retry_repo))[key]
                                main_message = f'Archive set {key} URL is now - \
{repos[key]["mig_url"]}'
                                logging.error(main_message)
                            elif repos[key]['retry_count'] == 3:
                                main_message = f'Maximum retries for set \
{key} reached - Try again later'
                                logging.error(main_message)
                                del check[key]
                    if pause < 600:
                        pause = pause + 300
                    pause_minute = int(pause / 60)
                    if skip_pause is False:
                        if check:
                            message = f"No archives are ready for download - \
Starting {str(pause_minute)} minute wait"
                        logging.info(message)
                        sleep(pause)
                    elif skip_pause is True:
                        logging.info("An archive was downloaded - \
Skipping wait between checks")
                        # Reset pause counter to not have this wait forever
                        pause = 0
                    else:
                        logging.info("Uploads complete")
                logging.info("Cleaning up old archives and logs")
                remove_old_archives_and_logs()
                if args.level.upper() != "DEBUG":
                    upload_logfile()
                else:
                    logging.info("Logging was set to DEBUG - \
Log will be uploaded with DEBUG messages removed")
                    upload_logfile()
            except Exception as error:
                logging.critical("Archive process failed")
                logging.critical(error)
                if args.level.upper() != "DEBUG":
                    logging.info("Uploading logs to Google Drive")
                    upload_logfile()
                else:
                    logging.info("Logging was set to DEBUG - \
Log will be uploaded with DEBUG messages removed")
                    upload_logfile()
        elif git_login() != "Success" and google_login() == "Success":
            logging.critical("Git login failed - Aborting archive process")
            if LOG_LEVEL != "DEBUG":
                logging.info("Uploading logs to Google Drive")
                upload_logfile()
            else:
                logging.info("Logging was set to DEBUG - \
Log will be uploaded with DEBUG messages removed")
                upload_logfile()
        else:
            logging.critical("Google login failed")
            upload_logfile()
    else:
        logging.critical("Git login Failed")
        upload_logfile()


if __name__ == "__main__":
    main()
