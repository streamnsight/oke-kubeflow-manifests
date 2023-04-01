#!/bin/bash

kubectl apply -f reset-db.Job.yaml \
&& kubectl wait --for=condition=Complete --timeout=30s -n kubeflow job/reset-db \
&& kubectl logs job/reset-db \
&& kubectl rollout restart deployments -n kubeflow
