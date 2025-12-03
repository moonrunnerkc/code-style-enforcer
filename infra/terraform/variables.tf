# Author: Bradley R. Kinnard — knobs and dials

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name, used for resource naming"
  type        = string
  default     = "code-style-enforcer"
}

variable "create_vpc" {
  description = "Create a new VPC or use default"
  type        = bool
  default     = false
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM calls"
  type        = string
  sensitive   = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 30
}

# ECS settings
variable "api_cpu" {
  description = "API task CPU units"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "API task memory (MB)"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Number of API tasks"
  type        = number
  default     = 2
}

variable "worker_cpu" {
  description = "Worker task CPU units"
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Worker task memory (MB)"
  type        = number
  default     = 512
}

variable "worker_desired_count" {
  description = "Number of worker tasks"
  type        = number
  default     = 1
}

# Redis settings
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1
}

# DynamoDB settings
variable "dynamodb_billing_mode" {
  description = "PAY_PER_REQUEST or PROVISIONED"
  type        = string
  default     = "PAY_PER_REQUEST"
}

# API settings
variable "valid_api_keys" {
  description = "Comma-separated valid API keys, or 'dev' to skip auth"
  type        = string
  default     = "dev"
  sensitive   = true
}

variable "rate_limit" {
  description = "Requests per rate window"
  type        = number
  default     = 10
}

variable "rate_window" {
  description = "Rate limit window in seconds"
  type        = number
  default     = 60
}
