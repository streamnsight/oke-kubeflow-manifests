#!/bin/bash

. ./kubeflow.env

if [[ -z "${OCI_KUBEFLOW_DOMAIN_NAME}" ]];
then
    read -pr "Domain Name: " OCI_KUBEFLOW_DOMAIN_NAME
fi;

DEFAULT_DOMAIN_ADMIN_EMAIL="admin@${OCI_KUBEFLOW_DOMAIN_NAME}"

if [[ -z "${OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL}" ]];
then
    read -pr "Domain Name Admin Email (defaults to ${DEFAULT_DOMAIN_ADMIN_EMAIL}) " DOMAIN_ADMIN_EMAIL
fi;

if [[ -z "${DOMAIN_ADMIN_EMAIL}" ]];
then
    export OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL=${DEFAULT_DOMAIN_ADMIN_EMAIL}
fi;

export OCI_KUBEFLOW_DOMAIN_NAME
export OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL

eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/kubeflow-gw.Certificate.tmpl.yaml)\"" \
> ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/kubeflow-gw.Certificate.yaml

eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/letsencrypt.ClusterIssuer.tmpl.yaml)\"" \
> ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/letsencrypt.ClusterIssuer.yaml

eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/kubeflow-gw.Certificate.tmpl.yaml)\"" \
> ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/kubeflow-gw.Certificate.yaml

eval "echo \"$(cat ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/letsencrypt.ClusterIssuer.tmpl.yaml)\"" \
> ./oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/letsencrypt.ClusterIssuer.yaml

eval "echo \"$(cat ./oci/apps/kserve/domain/config-domain.tmpl.yaml)\"" \
> ./oci/apps/kserve/domain/config-domain.yaml
