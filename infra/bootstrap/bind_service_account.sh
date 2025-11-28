#!/bin/bash
# Script: bind_service_account.sh
# Purpose: Binds wif provider to immitable service account
# service account should posses secret manager and secret access rights




#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../bind_service_account.sh

gcloud iam service-accounts add-iam-policy-binding github-action-olap@airflow-soln-project.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/70063168308/locations/global/workloadIdentityPools/my-olap-pool/attribute.repository/ochekayjay/prod_oltp_to_olap"
