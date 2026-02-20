#!/bin/bash
# Deploy Baloot AI server to Google Cloud Run.
#
# Usage:
#   ./deploy.sh              # Deploy with defaults
#   ./deploy.sh --tag v1.2   # Deploy with custom tag
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Project set: gcloud config set project baloot-game-v2-project

set -euo pipefail

PROJECT_ID="baloot-game-v2-project"
REGION="me-central1"
SERVICE_NAME="baloot-server"
PORT=3005

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
echo "   Project: ${PROJECT_ID}"
echo ""

# Deploy from source (Cloud Build will build the Dockerfile)
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --port "${PORT}" \
  --allow-unauthenticated \
  --session-affinity \
  --min-instances 0 \
  --max-instances 20 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "BALOOT_ENV=production,PYTHONUNBUFFERED=1"

echo ""
echo "✅ Deployment complete!"
echo "   URL: https://${SERVICE_NAME}-$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)' | sed 's|https://||')"
