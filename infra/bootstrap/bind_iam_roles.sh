#!/bin/bash
# Script: create_wif_pool.sh
# Purpose: Creates a Workload Identity Pool for GitHub Actions

# ${REPO} is the full repo name including the parent GitHub organization,
# such as "my-org/my-repo".
#
# ${WORKLOAD_IDENTITY_POOL_ID} is the full pool id, such as
# "projects/123456789/locations/global/workloadIdentityPools/github".

#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../bind_iam_roles.sh


gcloud secrets add-iam-policy-binding "my-secret" \
  --project="airflow-soln-project" \
  --role="roles/secretmanager.secretAccessor" \
  --member="principalSet://iam.googleapis.com/projects/70063168308/locations/global/workloadIdentityPools/oltp-olap-main-pool/attribute.repository/ochekayjay/prod_oltp_to_olap"
