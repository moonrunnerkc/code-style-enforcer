# Author: Bradley R. Kinnard — where the weights live

resource "aws_dynamodb_table" "agent_preferences" {
  name         = "${var.project_name}-agent-preferences"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "agent"

  attribute {
    name = "agent"
    type = "S"
  }

  # enable TTL if we want to expire old weights
  ttl {
    attribute_name = "expires_at"
    enabled        = false
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = {
    Name = "${var.project_name}-agent-preferences"
  }
}

# optional: analysis results table for cold storage / RL training
resource "aws_dynamodb_table" "analysis_results" {
  name         = "${var.project_name}-analysis-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "analysis_id"

  attribute {
    name = "analysis_id"
    type = "S"
  }

  attribute {
    name = "code_hash"
    type = "S"
  }

  global_secondary_index {
    name            = "code-hash-index"
    hash_key        = "code_hash"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-analysis-results"
  }
}

# feedback events for RL training
resource "aws_dynamodb_table" "feedback_events" {
  name         = "${var.project_name}-feedback-events"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "event_id"
  range_key    = "timestamp"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "agent"
    type = "S"
  }

  global_secondary_index {
    name            = "agent-index"
    hash_key        = "agent"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-feedback-events"
  }
}
