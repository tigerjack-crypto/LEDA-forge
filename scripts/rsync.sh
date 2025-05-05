#!/bin/bash - 
#===============================================================================
#
#          FILE: rsync.sh
# 
#         USAGE: ./rsync.sh 
# 
#   DESCRIPTION: 
# 
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: YOUR NAME (), 
#  ORGANIZATION: 
#       CREATED: 30/04/2025 14:31
#      REVISION:  ---
#===============================================================================

set -o nounset                              # Treat unset variables as an error
PROJECT=isd-leda
PROJECT_ROOT="$MDIR_LINUX_DATA"/vc/crypto
echo "project root $PROJECT_ROOT"
# SERVER=alphonseasproxy
if [ -z "$1" ]; then
  echo "Usage: $0 <SERVER>"
  exit 1
fi

SERVER=$1

echo "syncing to $SERVER"

rsync -avz --info=progress2 \
  --filter="merge $PROJECT_ROOT/$PROJECT/rsync_filter.txt" \
  "$PROJECT_ROOT/$PROJECT" "$SERVER":vc/

