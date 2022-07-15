#!/bin/bash

python "/git_backup/git_backup.py"

tail -f $(ls -t | grep git_backup_ | head -1)