#!/bin/bash
set -e

# Generate backup filename with date
BACKUP_FILE="backup-$(date +%Y-%m-%d).sql"

echo "Starting database backup..."

# Create backup using pg_dump
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > /tmp/$BACKUP_FILE

echo "Backup created: $BACKUP_FILE"

# Upload to Google Cloud Storage
echo "Uploading to GCS bucket: $GCS_BUCKET"
gcloud auth activate-service-account --key-file=/secrets/key.json
gsutil cp /tmp/$BACKUP_FILE gs://$GCS_BUCKET/$BACKUP_FILE

echo "Backup uploaded successfully to gs://$GCS_BUCKET/$BACKUP_FILE"

