#!/bin/bash

. ./kubeflow.env

if [[ -z "${OCI_KUBEFLOW_MYSQL_USER}" ]] ; then
  echo "OCI_KUBEFLOW_MYSQL_USER not set"
fi

if [[ -z "${OCI_KUBEFLOW_MYSQL_PASSWORD}" ]] ; then
  echo "OCI_KUBEFLOW_MYSQL_PASSWORD not set"
fi

if [[ -z "${OCI_KUBEFLOW_MYSQL_HOST}" ]] ; then
  echo "OCI_KUBEFLOW_MYSQL_HOST not set"
fi 

eval "echo \"$(cat ./oci/apps/pipeline/mds-external-mysql/mysql.tmpl.env)\"" > ./oci/apps/pipeline/mds-external-mysql/mysql.env
eval "echo \"$(cat ./oci/apps/pipeline/mds-external-mysql/mysql.Service.tmpl.yaml)\"" > ./oci/apps/pipeline/mds-external-mysql/mysql.Service.yaml
