#!/bin/bash

if [[ -z "${IDCS_URL}" ]];
then 
    read -p "IDCS URL: " IDCS_URL
fi;

if [[ -z "${IDCS_CLIENT_ID}" ]];
then
    read -p "IDCS Client ID: " IDCS_CLIENT_ID
fi;

if [[ -z "${IDCS_CLIENT_SECRET}" ]];
then
    read -p "IDCS Client Secret: " IDCS_CLIENT_SECRET
fi;

if [[ -z "${DOMAIN_NAME}" ]];
then
    read -p "Domain Name (Defaults to Load Balancer IP if blank): " DOMAIN_NAME
fi;

if [[ -z ${DOMAIN_NAME} ]]; 
then
    LBIP=$(kubectl get svc istio-ingressgateway -n istio-system -o=jsonpath="{.status.loadBalancer.ingress[0].ip}")
fi

ISSUER="https://${DOMAIN_NAME:-${LBIP}}/dex"

eval "echo \"$(cat ./oci/common/dex/overlays/idcs/config.yaml.tmpl)\"" > ./oci/common/dex/overlays/idcs/idcs-config.yaml
echo "OIDC_PROVIDER=${ISSUER}" > ./oci/common/oidc-authservice/overlays/idcs/params.env

