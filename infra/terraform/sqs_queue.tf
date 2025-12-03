# Author: Bradley R. Kinnard — async feedback pipeline

resource "aws_sqs_queue" "feedback_dlq" {
  name = "${var.project_name}-feedback-dlq"

  # keep failed messages for 14 days
  message_retention_seconds = 1209600

  tags = {
    Name = "${var.project_name}-feedback-dlq"
  }
}

resource "aws_sqs_queue" "feedback" {
  name = "feedback-queue" # matches QUEUE_NAME in feedback_processor.py

  # visibility timeout should be > processing time
  visibility_timeout_seconds = 30

  # long polling
  receive_wait_time_seconds = 20

  # message retention
  message_retention_seconds = 345600 # 4 days

  # max message size 256KB
  max_message_size = 262144

  # dead letter queue for poison messages
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.feedback_dlq.arn
    maxReceiveCount     = 3 # after 3 failures, send to DLQ
  })

  tags = {
    Name = "${var.project_name}-feedback-queue"
  }
}

# allow ECS tasks to use the queue
resource "aws_sqs_queue_policy" "feedback" {
  queue_url = aws_sqs_queue.feedback.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowECSAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task.arn
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.feedback.arn
      }
    ]
  })
}

# CloudWatch alarm for DLQ depth
resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  alarm_name          = "${var.project_name}-feedback-dlq-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Feedback DLQ has messages - check for processing errors"

  dimensions = {
    QueueName = aws_sqs_queue.feedback_dlq.name
  }

  # add SNS topic for alerts in prod
  # alarm_actions = [aws_sns_topic.alerts.arn]
}
