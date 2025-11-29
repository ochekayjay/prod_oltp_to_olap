#!/bin/bash
# Script: create_wif_pool.sh
# Purpose: Creates a Workload Identity Pool for GitHub Actions



#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../view_wif_provider.sh

# TODO: replace ${PROJECT_ID} with your value below.

gcloud iam workload-identity-pools providers describe "oltp-olap-main-pool-provider" \
  --project="airflow-soln-project" \
  --location="global" \
  --workload-identity-pool="oltp-olap-main-pool" \
  --format="value(name)"