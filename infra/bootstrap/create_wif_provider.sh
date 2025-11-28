#!/bin/bash
# Script: create_wif_provider.sh
# Purpose: Creates a Workload Identity Provider for GitHub Actions


#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../create_wif_provider.sh


gcloud iam workload-identity-pools providers create-oidc "my-olap-provider" \
    --location="global" \
    --workload-identity-pool="my-olap-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com/" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.aud=assertion.aud,attribute.actor=assertion.actor" \
    --attribute-condition="assertion.actor == 'ochekayjay' && assertion.ref == 'refs/heads/main'"


# to see your provider info
# gcloud iam workload-identity-pools providers describe my-olap-provider --location="global" --workload-identity-pool="my-olap-pool" --format="value(name)"

