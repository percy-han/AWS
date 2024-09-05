# AWS-Create-EKS-Node-Alarm
AWS instance级别的告警可以出发多种action，比如：auto-recovery,auto-scaling,执行lambda，发送通知等。然而该告警的配置是实例级别的，即只能为每一台实例配置告警，而无法配置一个统计模版。更重要的是，在生产环境中并非所有的workload都需要如此配置。这里以EKS集群为例，说明下当EKS集群扩容之后如何对新增节点配置instance级别的告警，当实例底层出现硬件故障之后自动触发auto-recovery

## Limition:
Each log group can have up to two subscription filters associated with it!


## Create IAM Policy 
Policy Nmae: Lambda-EKS-Node-Alarm-Policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "cloudwatch:PutMetricAlarm",
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
            "Resource": "*"
        }
    ]
}
```

## Create IAM Role 
Role Name: Lambda-EKS-Node-Alarm-Role
![image](https://github.com/user-attachments/assets/64b99973-955c-4e36-aaa6-bfd3e3501f7c)

![image](https://github.com/user-attachments/assets/41c00fdd-198e-4c1e-a3ad-08cb4dba5775)

## customize Python Code
代码中的region配置为您实际的region name

filter_name修改为cloudwatch log 中的subscription filter name，这里为New-Node-Join-EKS-Cluster

如果想触发更多action，可以在AlarmActions部分进行添加

将代码压缩成gzip文件，这里用的文件名为Create-EKS-Node-Alarm.zip

## Create Lambda Function

Lambda Function中的Timeout可根据实际情况调大
```
aws lambda create-function \
    --function-name Create-EKS-New-Node-Alarm \
    --zip-file fileb://<file-path>/Create-EKS-Node-Alarm.zip \
    --role arn:aws:iam::<your-account>:role/Lambda-EKS-Node-Alarm-Role \
    --handler lambda_function.lambda_handler \
    --runtime python3.10 \
    --region <your-region>
```

## Grant CloudWatch Logs the permission to execute your function
```
aws lambda add-permission \
    --function-name "Create-EKS-New-Node-Alarm" \
    --statement-id "Create-EKS-New-Node-Alarm" \
    --principal "logs.amazonaws.com" \
    --action "lambda:InvokeFunction" \
    --source-arn "<EKS-Audit-Log-ARN> \
    --source-account "<your-account>" \
    --region <your-region>
```


## Create a subscription filter using the following command
```
aws logs put-subscription-filter \
    --log-group-name "<EKS-Audit-Log-Name>" \
    --filter-name New-Node-Join-EKS-Cluster \
    --filter-pattern "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.verb = \"patch\") &&($.objectRef.resource = \"nodes\") &&($.objectRef.subresource = \"status\") && ($.requestObject.status.conditions[3].type =  \"Ready\") &&  ($.requestObject.status.conditions[3].status =  \"True\")}" \
    --destination-arn arn:aws:lambda:<your-region>:<your-account-id>:function:Create-EKS-New-Node-Alarm \
    --region <your-region>
```
