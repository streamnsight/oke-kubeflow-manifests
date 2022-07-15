#!/bin/bash

read -p "Domain Name: " DOMAIN_NAME
read -p "Domain Name Admin Email: " DOMAIN_ADMIN_EMAIL

export DOMAIN_NAME
export DOMAIN_ADMIN_EMAIL

kustomize build deployments/add-ons/letsencrypt | envsubst | kubectl apply -f -
kubectl delete pod authservice-0 -n istio-system

