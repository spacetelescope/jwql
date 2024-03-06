#!/bin/bash

function echo_format {
    echo ""
    echo "Usage: $0 <branch> [-r|--reset_service] [-n|--notify <email@stsci.edu>]"
    echo ""
    echo "WARNING! the optional parameters should only be used during a JWQL release in production"
    echo "branch: the git branch to pull from"
    echo "[-r|--reset_service]: Reset the jwql service"
    echo "[-n|--notify <email@stsci.edu>]: Notify via provided email"
    echo ""
    echo "Local:"
    echo "$ bash pull_jwql_branch.sh develop"
    echo ""
    echo "Test:"
    echo "$ bash pull_jwql_branch.sh v1.2 -r"
    echo ""
    echo "Production:"
    echo "$ bash pull_jwql_branch.sh v1.2 -r -n group_email_address@stsci.edu"
}

# Check if the required number of arguments are provided
if [ "$#" -lt 1 ]; then
    echo_format
    exit 1
fi

# Set default values for optional flags
reset=false
notify=false
recipient=""

# Retrieve the branch_name from the command line argument
branch_name=$1
# Parse optional flags
while [[ $# -gt 1 ]]; do
    case "$2" in
        -r|--reset_service)
            reset=true
            ;;
        -n|--notify)
            notify=true
            recipient="$3"
            shift
            ;;
        *)
            echo "Error: Invalid option $2"
            echo_format
            exit 1
            ;;
    esac
    shift
done

if [ "$notify" = true ]  && [ -z "$recipient" ]; then
    echo_format
    exit 1
fi

echo "Branch: $branch_name";
echo "Reset: $reset";
echo "Notify: $notify $recipient";

# 1. Pull updated code from GitHub deployment branch (keep second checkout in case its already defined for some weird reason)
git checkout -b $branch_name --track origin/$branch_name
git checkout $branch_name
git fetch origin $branch_name
git pull origin $branch_name
git fetch origin --tags

# 2. Bring the service down
if [ "$reset" = true ]; then
    sudo /bin/systemctl stop jwql.service
fi

# 3. Install jwql
pip install -e ..

# 4. Merge Any Migrations
python ./website/manage.py migrate

# 5. Bring the service back up
if [ "$reset" = true ]; then
    sudo /bin/systemctl start jwql.service
fi

# 6. Initialize any new databases that have been added
python ./database/database_interface.py

# 7. Send out notification email
if [ "$notify" = true ] && [ -n "$recipient" ]; then
    subject="JWQL $branch_name Released"
    message_content="Hello, A new version of JWQL ($branch_name) has just been released.  Visit https://github.com/spacetelescope/jwql/releases for more information."
    echo "$message_content" | mail -s "$subject" "$recipient"
    echo "Notification Email Sent"
fi