# Author: Bradley R. Kinnard — the important bits

output "alb_dns_name" {
  description = "ALB DNS name - use this to access the API"
  value       = aws_lb.api.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID for Route53 alias records"
  value       = aws_lb.api.zone_id
}

output "api_url" {
  description = "Full API URL"
  value       = "http://${aws_lb.api.dns_name}/api/v1"
}

output "ecr_api_repository_url" {
  description = "ECR repository URL for API image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repository_url" {
  description = "ECR repository URL for worker image"
  value       = aws_ecr_repository.worker.repository_url
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "sqs_feedback_queue_url" {
  description = "SQS feedback queue URL"
  value       = aws_sqs_queue.feedback.url
}

output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value = {
    agent_preferences = aws_dynamodb_table.agent_preferences.name
    analysis_results  = aws_dynamodb_table.analysis_results.name
    feedback_events   = aws_dynamodb_table.feedback_events.name
  }
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    api    = aws_cloudwatch_log_group.api.name
    worker = aws_cloudwatch_log_group.worker.name
  }
}

# deployment commands
output "deploy_commands" {
  description = "Commands to deploy after terraform apply"
  value       = <<-EOT
    # Build and push API image
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com
    docker build -t ${aws_ecr_repository.api.repository_url}:latest -f Dockerfile.api .
    docker push ${aws_ecr_repository.api.repository_url}:latest

    # Build and push worker image
    docker build -t ${aws_ecr_repository.worker.repository_url}:latest -f Dockerfile.worker .
    docker push ${aws_ecr_repository.worker.repository_url}:latest

    # Force new deployment
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${var.project_name}-api --force-new-deployment
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${var.project_name}-worker --force-new-deployment
  EOT
}
