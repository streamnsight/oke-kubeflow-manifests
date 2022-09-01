#!/bin/bash

. kubeflow.env

if [[ -z "${REGION}" ]] ; then
  echo "Region not set"
fi

if [[ -z "${DBUSER}" ]] ; then
  echo "User not set"
fi

if [[ -z "${DBPASS}" ]] ; then
  echo "DB Pass not set"
fi

if [[ -z "${DBPORT}" ]] ; then
  DBPORT=3306
fi

if [[ -z "${DBHOST}" ]] ; then
  echo "DB HOST not set"
fi

export OCI_REGION=$REGION

# echo "dbhost=$DBHOST">./oci/apps/pipeline/mds-external-mysql/params.env
# echo "dbport=$DBPORT">>./oci/apps/pipeline/mds-external-mysql/params.env
# echo "mlmdDb=metadb">>./oci/apps/pipeline/mds-external-mysql/params.env

echo "username=$DBUSER">./oci/apps/pipeline/mds-external-mysql/mysql.env
echo "password=$DBPASS">>./oci/apps/pipeline/mds-external-mysql/mysql.env

eval "echo \"$(cat ./oci/apps/pipeline/mds-external-mysql/mysql.Service.yaml.tmpl)\"" > ./oci/apps/pipeline/mds-external-mysql/mysql.Service.yaml
