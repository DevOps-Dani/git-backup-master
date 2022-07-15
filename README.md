# **Github backup + DR**

2022.05.23

─

Dani Westlake

Brainlabs

[![linting:flake8](https://img.shields.io/badge/linting-flake8-purple)](https://github.com/PyCQA/flake8)
[![formatting:black](https://img.shields.io/badge/formatting-black-red)](https://github.com/psf/black)

#

# Overview

Created due to the following issue:

A malicious Github admin can delete, publicize, or arbitrarily alter repositories and users in the Brainlabs-Digital organization [#7922](https://github.com/Brainlabs-Digital/Project-X/issues/7922)


# Solution Setup:

## Config.ini:

Config file saved in script run location. Example file in code repository:

```
[git-prod]
user = github-user
token = personal-access-token
url = https://api.github.com/orgs/ORGNAME/
[drive-prod]
folder = google-drive-folder-id
logfolder = google-drive-folder-id
```

## Command line arguments:

All command line arguments have a default for production

Specify alternate config file. Default is config.ini in the root of the project:
--config CONFIG, -c CONFIG

The section of the config file that contains GitHub login information:
--gitenv GITENV, -g GITENV

The section of the config file that contains Google Drive folder information:
--googledrive GOOGLEDRIVE, -d GOOGLEDRIVE, -o GOOGLEDRIVE

Set log level. Accepted values: DEBUG, INFO or WARN. Default value is WARN:
--level LEVEL, -l LEVEL

Specify alternate Google Auth file:
--driveauth DRIVEAUTH, -d DRIVEAUTH

## Testing
# Notes
Testing can be performed against personal GitHub organisations using your own
access token and with the output sent to a personal Google Drive folder using
generated secrets. An example of the config file is saved as example_config.ini
in the root of the project

Github requires the account be an owner of the organisation for the script to work
The Google Drive folder must be shared with the account used for authentication
and requires the drive API v3 scope if using a service account

To generate client_secrets.json for Google authentication:
In Google developers console you should see a section titled OAuth 2.0 client IDs
Click the Create credentials button, and follow the instructions to create new
credentials, and then follow the steps outlined above to find the Client secret

The default config.ini and client_secret.json used for production is saved in Bitwarden

More info on Google Drive API V3 scope:
https://developers.google.com/identity/protocols/oauth2/scopes#drive

# Process
The production process can be run with:

```
python3.10 git_backup.py
```
