#!/bin/bash
# Script: create_wif_provider.sh
# Purpose: Creates a Workload Identity Provider for GitHub Actions


#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../create_wif_provider.sh


# TODO: replace ${PROJECT_ID} and ${GITHUB_ORG} with your values below.

gcloud iam workload-identity-pools providers create-oidc "oltp-olap-main-pool-provider" \
  --project="airflow-soln-project" \
  --location="global" \
  --workload-identity-pool="oltp-olap-main-pool" \
  --display-name="My OLTP OLAP repo Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == \"ochekayjay\"" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# to see your provider info
# gcloud iam workload-identity-pools providers describe my-olap-provider --location="global" --workload-identity-pool="my-olap-pool" --format="value(name)"

