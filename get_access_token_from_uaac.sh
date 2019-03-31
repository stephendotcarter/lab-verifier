#!/bin/bash
UAAC_TARGET='https://<opsman>/uaa'
UAAC_CLIENT_NAME='opsman'
UAAC_CLIENT_SECRET=''
UAAC_USER_NAME=''
UAAC_USER_PASSWORD=''

uaac target $UAAC_TARGET --skip-ssl-validation
uaac token owner get "$UAAC_CLIENT_NAME" "$UAAC_USER_NAME" -s "$UAAC_CLIENT_SECRET" -p "$UAAC_USER_PASSWORD"

ACCESS_TOKEN=$(uaac contexts | grep -A1 "client_id: opsman" | grep access_token | awk '{print $2}')
echo $ACCESS_TOKEN
