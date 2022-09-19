#!/bin/bash

. ./kubeflow.env
kubectl exec -it mysql-temp -n default -- mysql -u ${DBUSER} -p${DBPASS} -h mysql -e "drop database mlpipeline; drop database metadb; drop database cachedb;"
kubectl rollout restart deployments -n kubeflow