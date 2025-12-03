# Author: Bradley R. Kinnard — hot cache, cold storage

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis"
  subnet_ids = local.private_subnet_ids

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-redis-params"
  family = "redis7"

  # maxmemory-policy: evict least recently used when full
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-redis"
  description          = "Redis cluster for code analysis cache and rate limiting"

  engine             = "redis"
  engine_version     = "7.0"
  node_type          = var.redis_node_type
  num_cache_clusters = var.redis_num_nodes
  port               = 6379

  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false # set true if using TLS

  # maintenance
  maintenance_window       = "sun:05:00-sun:06:00"
  snapshot_retention_limit = var.environment == "prod" ? 7 : 0
  snapshot_window          = "04:00-05:00"

  # automatic failover for multi-node
  automatic_failover_enabled = var.redis_num_nodes > 1

  tags = {
    Name = "${var.project_name}-redis"
  }
}
