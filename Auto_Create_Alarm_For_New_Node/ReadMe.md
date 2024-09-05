
# 创建Event Bridge Rule

![Uploading image.png…]()

{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["shutting-down", "pending"]
  }
}
