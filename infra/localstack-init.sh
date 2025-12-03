#!/bin/bash
# Author: Bradley R. Kinnard — bootstrap LocalStack resources

set -e

echo "Creating SQS queue..."
awslocal sqs create-queue --queue-name feedback-queue

echo "Creating DynamoDB table..."
awslocal dynamodb create-table \
  --table-name AgentPreferences \
  --attribute-definitions AttributeName=agent,AttributeType=S \
  --key-schema AttributeName=agent,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

echo "Seeding initial weights..."
for agent in style naming minimalism docstring security; do
  awslocal dynamodb put-item \
    --table-name AgentPreferences \
    --item "{\"agent\": {\"S\": \"$agent\"}, \"weight\": {\"N\": \"1.0\"}, \"update_count\": {\"N\": \"0\"}}"
done

echo "LocalStack init complete!"
