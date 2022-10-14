#!/bin/bash

. ./kubeflow.env

kubectl run resetdb --restart='Never' --image=mysql:8.0.26 \
    --wait=true \
    --annotations="sidecar.istio.io/inject=false" \
    --env="OCI_KUBEFLOW_MYSQL_USER=${OCI_KUBEFLOW_MYSQL_USER}" \
    --env="OCI_KUBEFLOW_MYSQL_PASSWORD=${OCI_KUBEFLOW_MYSQL_PASSWORD}" -- \
    mysql -u "${OCI_KUBEFLOW_MYSQL_USER}" -p${OCI_KUBEFLOW_MYSQL_PASSWORD} \
    -h mysql -e "drop database mlpipeline; drop database metadb; drop database cachedb;" \
&& kubectl logs resetdb \
&& kubectl rollout restart deployments -n kubeflow \
&& kubectl delete pod resetdb