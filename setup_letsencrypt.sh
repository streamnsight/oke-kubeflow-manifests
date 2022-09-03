#!/bin/bash


if [[ -z "${DOMAIN_NAME}" ]];
then
    read -p "Domain Name: " DOMAIN_NAME
fi;

if [[ -z "${DOMAIN_ADMIN_EMAIL}" ]];
then
    read -p "Domain Name Admin Email: " DOMAIN_ADMIN_EMAIL
fi;

export DOMAIN_NAME
export DOMAIN_ADMIN_EMAIL

eval "echo \"$(cat ./oci/common/istio-1-14/kubeflow-istio-resources/overlays/letsencrypt/kubeflow-gw.Certificate.yaml.tmpl)\"" \
> ./oci/common/istio-1-14/kubeflow-istio-resources/overlays/letsencrypt/kubeflow-gw.Certificate.yaml

eval "echo \"$(cat ./oci/common/istio-1-14/kubeflow-istio-resources/overlays/letsencrypt/letsencrypt.ClusterIssuer.yaml.tmpl)\"" \
> ./oci/common/istio-1-14/kubeflow-istio-resources/overlays/letsencrypt/letsencrypt.ClusterIssuer.yaml
