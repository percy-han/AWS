# EC2 Abnormal Instance Auto Detection System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-CloudFormation-orange.svg)](https://aws.amazon.com/cloudformation/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)

一个基于AWS CloudFormation的自动化EC2实例故障检测系统，支持跨区域部署和自定义时区配置。

## 🌟 功能特性

- ✅ **自动检测** - 定期检测EC2实例的系统和实例状态异常
- ✅ **EBS监控** - 监控EBS卷的IOPS和吞吐量超限情况
- ✅ **智能去重** - 避免重复记录相同的故障事件
- ✅ **实时通知** - 通过SQS队列发送异常通知
- ✅ **跨区域支持** - 支持在任何AWS区域部署
- ✅ **时区本地化** - 支持UTC-12到UTC+14的全球时区
- ✅ **灵活配置** - 支持多环境和自定义参数
- ✅ **详细日志** - 完整的检测和处理日志

## 🏗️ 架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│  Lambda Function │───▶│   DynamoDB      │
│   (Schedule)    │    │  (Detection)     │    │   (Records)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        │
                       ┌──────────────────┐              │
                       │  CloudWatch      │              │
                       │  (Logs)          │              │
                       └──────────────────┘              │
                                                         │
┌─────────────────┐    ┌──────────────────┐              │
│   SQS Queue     │◀───│ EventBridge Pipe │◀─────────────┘
│ (Notifications) │    │  (Stream)        │
└─────────────────┘    └──────────────────┘
```

## 🚀 快速开始

### 前置要求

- AWS CLI 已配置
- 具有以下权限的AWS账户：
  - CloudFormation 完整权限
  - IAM 角色创建权限
  - EC2、Lambda、DynamoDB、SQS、EventBridge 相关权限

### 基本部署

```bash
# 克隆仓库
git clone git clone https://github.com/percy-han/AWS.git
cd  AWS/Auto-detect-abnormal-instance/

# 部署到 us-east-1，使用默认配置
aws cloudformation create-stack \
  --stack-name ec2-detection-prod \
  --template-body file://ec2-abnormal-detection-cdk-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### 自定义部署

```bash
# 部署到指定区域，使用自定义配置
aws cloudformation create-stack \
  --stack-name my-ec2-detection \
  --template-body file://ec2-abnormal-detection-cdk-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=ResourcePrefix,ParameterValue=my-company-detection \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=TimezoneOffset,ParameterValue=8 \
    ParameterKey=ScheduleExpression,ParameterValue="rate(5 minutes)" \
  --region ap-southeast-1
```

## ⚙️ 配置参数

| 参数名 | 类型 | 默认值 | 说明 | 示例 |
|--------|------|--------|------|------|
| `ResourcePrefix` | String | `ec2-detection` | 资源名称前缀，用于区分不同项目 | `my-company-detection` |
| `Environment` | String | `prod` | 部署环境标识 | `dev`, `test`, `staging`, `prod` |
| `TimezoneOffset` | Number | `0` | 时区偏移量（UTC±小时） | `8` (UTC+8), `-5` (UTC-5) |
| `ScheduleExpression` | String | `rate(5 minutes)` | 检测频率 | `rate(1 minute)`, `rate(1 hour)` |
| `LambdaMemorySize` | Number | `256` | Lambda内存大小(MB) | `128`, `512`, `1024` |
| `LambdaTimeout` | Number | `300` | Lambda超时时间(秒) | `60`, `600`, `900` |
| `LogRetentionDays` | Number | `30` | 日志保留天数 | `7`, `90`, `365` |
| `CreateNewSQS` | String | `true` | 是否创建新SQS队列 | `true`, `false` |
| `ExistingSQSArn` | String | `""` | 现有SQS队列ARN | `arn:aws:sqs:...` |

## 🌍 时区支持

系统支持全球标准时区，常用时区配置：

| 地区 | 时区 | TimezoneOffset | 示例时间显示 |
|------|------|----------------|--------------|
| 中国/新加坡 | UTC+8 | `8` | `2025-01-01 16:00:00` |
| 日本/韩国 | UTC+9 | `9` | `2025-01-01 17:00:00` |
| 印度 | UTC+5:30 | `5` | `2025-01-01 13:00:00` |
| 英国(冬季) | UTC+0 | `0` | `2025-01-01 08:00:00` |
| 美国东部(冬季) | UTC-5 | `-5` | `2025-01-01 03:00:00` |
| 美国西部(冬季) | UTC-8 | `-8` | `2025-01-01 00:00:00` |

## 📊 监控和维护

### 查看检测日志

```bash
# 查看Lambda函数日志
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/your-prefix-detection-lambda"

# 实时查看日志
aws logs tail /aws/lambda/your-prefix-detection-lambda-prod --follow
```

### 查看异常记录

```bash
# 查看DynamoDB表中的异常记录
aws dynamodb scan --table-name your-prefix-abnormal-instances-prod --region us-east-1
```

### 监控SQS队列

```bash
# 查看SQS队列消息
aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/your-prefix-abnormal-notifications-prod
```

## 🔧 高级配置

### 使用现有SQS队列

```bash
aws cloudformation create-stack \
  --stack-name ec2-detection \
  --template-body file://ec2-abnormal-detection-cdk-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=CreateNewSQS,ParameterValue=false \
    ParameterKey=ExistingSQSArn,ParameterValue=arn:aws:sqs:us-east-1:123456789012:my-existing-queue
```

### 多环境部署

```bash
# 开发环境
aws cloudformation create-stack \
  --stack-name ec2-detection-dev \
  --template-body file://ec2-abnormal-detection-cdk-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=Environment,ParameterValue=dev \
    ParameterKey=ScheduleExpression,ParameterValue="rate(10 minutes)"

# 生产环境
aws cloudformation create-stack \
  --stack-name ec2-detection-prod \
  --template-body file://ec2-abnormal-detection-cdk-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=ScheduleExpression,ParameterValue="rate(5 minutes)"
```

## 📋 输出信息

部署完成后，CloudFormation会输出以下重要信息：

- **DeploymentRegion** - 部署的AWS区域
- **DynamoDBTableName** - 异常记录表名称
- **LambdaFunctionName** - 检测函数名称
- **SQSQueueUrl** - 通知队列URL
- **StackInfo** - 完整的部署信息摘要

## 🛠️ 故障排除

### 常见问题

**Q: Lambda函数执行失败**
```bash
# 查看详细错误日志
aws logs filter-log-events \
  --log-group-name /aws/lambda/your-prefix-detection-lambda-prod \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Q: 没有检测到异常实例**
- 确认EC2实例确实存在状态异常
- 检查Lambda函数的执行权限
- 验证部署区域是否正确

**Q: 时区显示不正确**
- 检查TimezoneOffset参数设置
- 确认参数值在-12到+14范围内

**Q: DynamoDB写入失败**
- 检查IAM角色权限
- 确认DynamoDB表存在且可访问

### 权限问题

如果遇到权限相关错误，请确保部署用户具有以下权限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "lambda:*",
        "dynamodb:*",
        "sqs:*",
        "events:*",
        "pipes:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## 💰 成本估算

基于默认配置的月度成本估算（us-east-1区域）：

| 服务 | 用量 | 月度成本 |
|------|------|----------|
| Lambda | 8,640次调用/月，256MB，5秒执行 | ~$0.20 |
| DynamoDB | 按需计费，少量读写 | ~$0.50 |
| SQS | 标准队列，少量消息 | ~$0.10 |
| CloudWatch Logs | 10MB日志/月 | ~$0.05 |
| **总计** | | **~$0.85/月** |

*注：实际成本可能因使用量和区域而异*


---

**免责声明**: 本工具仅用于监控目的，不能替代AWS官方的监控和告警服务。请根据实际需求进行配置和使用。
