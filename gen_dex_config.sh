#!/bin/bash

read -p "IDCS URL: " IDCS_URL
read -p "IDCS Client ID: " IDCS_CLIENT_ID
read -p "IDCS Client Secret: " IDCS_CLIENT_SECRET

eval "echo \"$(cat ./deployments/add-ons/dex-idcs/config.yaml.tmpl)\"" > ./deployments/add-ons/dex-idcs/idcs-config.yaml
