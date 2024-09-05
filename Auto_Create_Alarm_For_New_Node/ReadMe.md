# AWS-Create-EKS-Node-Alarm
AWS instance级别的告警可以触发多种action，比如：auto-recovery,auto-scaling,执行lambda，发送通知等。然而该告警的配置是实例级别的，即只能为每一台实例配置告警，而无法配置一个统计模版。更重要的是，在生产环境中并非所有的workload都需要如此配置。这里以EKS集群为例，说明下当EKS集群扩容之后如何对新增节点配置instance级别的告警，从而实例底层出现硬件故障之后自动触发auto-recovery以及发送SNS通知；当实例终止之时，随后删除掉对应的告警


## Create IAM Policy 
Policy Nmae: Lambda-Create-Instance-Alarm-Policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricAlarm",
                "ec2:DescribeInstances",
                "cloudwatch:DeleteAlarms",
                "cloudwatch:DescribeAlarmsForMetric",
                "cloudwatch:DescribeAlarms"
            ],
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:us-west-2:887221633712:*"
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-west-2:887221633712:log-group:/aws/lambda/Auto-Create-Delete-Instance-Alarm:*"
        }
    ]
}
```

## Create IAM Role 
Role Name: Lambda-Create-Instance-Alarm-Role
![image](https://github.com/user-attachments/assets/64b99973-955c-4e36-aaa6-bfd3e3501f7c)

![image](https://github.com/user-attachments/assets/8977d18a-e938-49e7-8038-4ede1e021fa1)


## Customize Python Code
代码中的region配置为您实际的region name

filter_name修改为cloudwatch log 中的subscription filter name，这里为New-Node-Join-EKS-Cluster

如果想触发更多action，可以在AlarmActions部分进行添加

将代码压缩成gzip文件，这里用的文件名为Create-EKS-Node-Alarm.zip

## Create Lambda Function

Lambda Function中的Timeout可根据实际情况调大
```
aws lambda create-function \
    --function-name Auto-Create-Delete-Instance-Alarm \
    --zip-file fileb://<file-path>/Create-EKS-Node-Alarm.zip \
    --role arn:aws:iam::<your-account>:role/Lambda-Create-Instance-Alarm-Role \
    --handler lambda_function.lambda_handler \
    --runtime python3.10 \
    --region <your-region>
```


## Create Event Bridge Rule

![image](https://github.com/user-attachments/assets/662422e0-f6a0-462a-8df8-9b9ebf8d137d)

Event Pattern
```
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["shutting-down", "pending"]
  }
}
```

![image](https://github.com/user-attachments/assets/848acebe-5689-4e50-a9e2-b227e7e5014a)


