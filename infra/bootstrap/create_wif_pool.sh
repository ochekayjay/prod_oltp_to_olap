#!/bin/bash
# Script: create_wif_pool.sh
# Purpose: Creates a Workload Identity Pool for GitHub Actions



#steps
# gcloud auth login
# gcloud config set project my-gcp-project-id
# bash ...../create_wif_pool.sh


gcloud iam workload-identity-pools create my-olap-pool \
  --location="global" \
  --display-name="My Olap Pool"
