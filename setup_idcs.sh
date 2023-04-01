#!/bin/bash

. ./kubeflow.env

if [[ -z "${OCI_KUBEFLOW_IDCS_URL}" ]];
then 
    read -pr "IDCS URL: " OCI_KUBEFLOW_IDCS_URL
fi;

if [[ -z "${OCI_KUBEFLOW_IDCS_CLIENT_ID}" ]];
then
    read -pr "IDCS Client ID: " OCI_KUBEFLOW_IDCS_CLIENT_ID
fi;

if [[ -z "${OCI_KUBEFLOW_IDCS_CLIENT_SECRET}" ]];
then
    read -pr "IDCS Client Secret: " OCI_KUBEFLOW_IDCS_CLIENT_SECRET
fi;

if [[ -z "${OCI_KUBEFLOW_DOMAIN_NAME}" ]];
then
    read -pr "Domain Name (Defaults to Load Balancer IP if blank): " OCI_KUBEFLOW_DOMAIN_NAME
fi;

if [[ -z ${OCI_KUBEFLOW_DOMAIN_NAME} ]]; 
then
    LBIP=$(kubectl get svc istio-ingressgateway -n istio-system -o=jsonpath="{.status.loadBalancer.ingress[0].ip}")
fi

export OCI_KUBEFLOW_ISSUER="https://${OCI_KUBEFLOW_DOMAIN_NAME:-${LBIP}}/dex"

eval "echo \"$(cat ./oci/common/dex/overlays/idcs/config.tmpl.yaml)\"" > ./oci/common/dex/overlays/idcs/config.yaml
eval "echo \"$(cat ./oci/common/oidc-authservice/overlays/idcs/params.tmpl.env)\"" > ./oci/common/oidc-authservice/overlays/idcs/params.env

