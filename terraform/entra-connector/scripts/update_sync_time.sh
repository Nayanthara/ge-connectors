#!/usr/bin/env bash
set -euo pipefail

# Required environment variables passed from Terraform
: "${GE_LOCATION:?Environment variable GE_LOCATION is required}"
: "${PROJECT_NUMBER:?Environment variable PROJECT_NUMBER is required}"
: "${PROJECT_ID:?Environment variable PROJECT_ID is required}"
: "${COLLECTION_ID:?Environment variable COLLECTION_ID is required}"
: "${ACCESS_TOKEN:?Environment variable ACCESS_TOKEN is required}"
: "${REFRESH_INTERVAL:?Environment variable REFRESH_INTERVAL is required}"
: "${SYNC_TIME_HOURS:?Environment variable SYNC_TIME_HOURS is required}"
: "${SYNC_TIME_MINUTES:?Environment variable SYNC_TIME_MINUTES is required}"
: "${SYNC_TIME_TZ:?Environment variable SYNC_TIME_TZ is required}"

API_ENDPOINT="https://${GE_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/${GE_LOCATION}/collections/${COLLECTION_ID}/dataConnector"

echo "Polling connection state until active..."
while true; do
  RESPONSE=$(curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" "${API_ENDPOINT}")
  STATE=$(echo "${RESPONSE}" | jq -r '.state // "UNKNOWN"')
  ERR_MSG=$(echo "${RESPONSE}" | jq -r '.errors[0].message // "No detailed error message provided"')

  if [[ "${STATE}" == "ACTIVE" || "${STATE}" == "RUNNING" || "${STATE}" == "WARNING" ]]; then
    echo "Connector is ${STATE}. Executing nextSyncTime PATCH..."
    break
  elif [[ "${STATE}" == "FAILED" || "${STATE}" == "INITIALIZATION_FAILED" ]]; then
    echo "ERROR: Connector failed to initialize with state: ${STATE}"
    echo "Error details: ${ERR_MSG}"
    exit 1
  elif [[ "${STATE}" == "UNKNOWN" || -z "${STATE}" ]]; then
    echo "ERROR: Failed to retrieve connector state from API response:"
    echo "${RESPONSE}"
    exit 1
  fi

  echo "Connector is currently in state ${STATE}, waiting 15 seconds..."
  sleep 15
done

PAYLOAD=$(cat <<EOF
{
  "name": "projects/${PROJECT_NUMBER}/locations/${GE_LOCATION}/collections/${COLLECTION_ID}/dataConnector",
  "refreshInterval": "${REFRESH_INTERVAL}",
  "nextSyncTime": {
    "hours": ${SYNC_TIME_HOURS},
    "minutes": ${SYNC_TIME_MINUTES},
    "timeZone": {
      "id": "${SYNC_TIME_TZ}"
    }
  }
}
EOF
)

# Perform the PATCH request with valid connection state
HTTP_RESPONSE=$(curl -sS -w "\n%{http_code}" -X PATCH \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d "${PAYLOAD}" \
  "${API_ENDPOINT}?updateMask=next_sync_time,refresh_interval")

HTTP_STATUS=$(echo "${HTTP_RESPONSE}" | tail -1)
HTTP_BODY=$(echo "${HTTP_RESPONSE}" | sed '$d')

echo "Response body: ${HTTP_BODY}"
echo "HTTP Status: ${HTTP_STATUS}"

if [ "${HTTP_STATUS}" -ge 200 ] && [ "${HTTP_STATUS}" -lt 300 ]; then
  echo "SUCCESS: Entra sync time set to ${SYNC_TIME_HOURS}:${SYNC_TIME_MINUTES} ${SYNC_TIME_TZ}"
else
  echo "FAILED: HTTP ${HTTP_STATUS} setting Entra connector nextSyncTime."
  echo "${HTTP_BODY}"
  exit 1
fi
