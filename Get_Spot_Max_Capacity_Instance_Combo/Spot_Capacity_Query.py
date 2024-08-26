# -*- coding: utf-8 -*-
import re
import os
import pytz
import time
import json
import boto3
import datetime
import logging
import Find_Best_Combo
import numpy as np
import pandas as pd
import multiprocessing as mp
import matplotlib.pyplot as plt
from scipy.stats import norm
from itertools import combinations


aws_access_key_id = ''
aws_secret_access_key = ''
logging.basicConfig(filename='example.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
region = 'us-west-2'
sqs_url = ''
current_time = datetime.datetime.now(pytz.utc)
before_time = current_time - datetime.timedelta(days=7) #最多可获取过去60天数据，数据越多计算量越大
cloudwatch_client = boto3.client('cloudwatch', region_name=region)
ec2_client = boto3.client('ec2',region_name=region)
az_code_list = ['PDX1', 'PDX2', 'PDX4','PDX80'] #根据实际情况调整

def send_message_to_queue(message):
    sqs_client = boto3.client('sqs', region_name=region)
    retry_count = 3  # 设置重试次数
    while retry_count > 0:
        try:
            response = sqs_client.send_message(
                QueueUrl = sqs_url,
                MessageBody = message,
                MessageGroupId = '1',  # 消息分组 ID，用于确保 FIFO 顺序
                MessageDeduplicationId = '1'  # 消息去重 ID，用于确保消息的唯一性
            )
            #print('Message sent:', response['MessageId'])
            logging.info('Message sent: %s', response['MessageId'])
            return
        except Exception as e:
            print('Error:', e)
            logging.info('Error: %s',e)
            retry_count -= 1
            print(f'Retrying... ({retry_count} attempts left)')
            logging.info('Retrying... %d attempts left)',retry_count)
            time.sleep(1)  # 休眠一秒后重试

def az_mappint(az_code):  #根据实际需要调整
    if az_code == 'PDX1':
        AZ_Name = 'us-west-2a'
    elif az_code == 'PDX2':
        AZ_Name = 'us-west-2b'
    elif az_code == 'PDX4':
       AZ_Name = 'us-west-2c'
    elif az_code == 'PDX80':
        AZ_Name = 'us-west-2d'
    return AZ_Name

def get_instance_list(instance_type_filters=None, pattern=r'(8|12|16|24|32|48)xlarge'):
    if instance_type_filters is None:
        instance_type_filters = [
            {
                'Name': 'instance-type',
                'Values': ['r5a.*', 'r5ad.*', 'r5b.*', 'r5.*', 'r5d.*', 'r6a.*', 'r6i.*', 'r6id.*', 'r6g.*', 'r6gd.*', 'r7a.*', 'r7i.*', 'r7g.*', 'r7gd.*']
            },
            {
                'Name': 'bare-metal',
                'Values': ['false']  # 过滤掉Metal的实例类型
            }
        ]
    paginator = ec2_client.get_paginator('describe_instance_types')
    response_iterator = paginator.paginate(
    DryRun=False,
    Filters=instance_type_filters)
    # 打印实例类型及其详细信息
    result_list = []
    for page in response_iterator:
        for instance_type in page['InstanceTypes']:
            inst_type = instance_type['InstanceType']
            if re.search(pattern, inst_type):
                item = {}
                item['instance_type'] = inst_type
                item['vcpu'] = instance_type['VCpuInfo']['DefaultVCpus']
                result_list.append(item)
    return result_list

def get_cw_timestimp(before_time, current_time):
    response = cloudwatch_client.get_metric_data(MetricDataQueries=[{
        'Id':
        'string',
        'MetricStat': {
            'Metric': {
                'Namespace':
                'Service',
                'MetricName':'r6i.4xlarge.generic.novice.PDX1.AdmissionControl.Available',
                "Dimensions": [{
                    "Name": "DataSet",
                    "Value": "Prod"
                }, {
                    "Name": "HostGroup",
                    "Value": "ALL"
                }, {
                    "Name": "ServiceName",
                    "Value": "EC2SpotCapacityMonitorService"
                }, {
                    "Name": "Client",
                    "Value": "ALL"
                }, {
                    "Name": "Marketplace",
                    "Value": "PDX"
                }, {
                    "Name": "Host",
                    "Value": "ALL"
                }, {
                    "Name": "MethodName",
                    "Value": "ALL"
                }, {
                    "Name": "MetricClass",
                    "Value": "NONE"
                }, {
                    "Name": "Instance",
                    "Value": "NONE"
                }]
            },
            'Period': 3600,
            'Stat': 'Minimum',
            'Unit': 'None'
        },
        'ReturnData':
        True,
        'AccountId':
        'igraph'
    }],
                                                 StartTime=before_time,
                                                 EndTime=current_time,
                                                 ScanBy='TimestampAscending')
    result = response['MetricDataResults'][0]['Timestamps']
    timestamp_strings = [ts.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M') for ts in result]
    return timestamp_strings


def Spot_query(instance_type,instance_vcpu,metric_name, before_time, current_time):
    response = cloudwatch_client.get_metric_data(MetricDataQueries=[{
        'Id':
        'string',
        'MetricStat': {
            'Metric': {
                'Namespace':
                'Service',
                'MetricName':
                metric_name,
                "Dimensions": [{
                    "Name": "DataSet",
                    "Value": "Prod"
                }, {
                    "Name": "HostGroup",
                    "Value": "ALL"
                }, {
                    "Name": "ServiceName",
                    "Value": "EC2SpotCapacityMonitorService"
                }, {
                    "Name": "Client",
                    "Value": "ALL"
                }, {
                    "Name": "Marketplace",
                    "Value": "PDX"
                }, {
                    "Name": "Host",
                    "Value": "ALL"
                }, {
                    "Name": "MethodName",
                    "Value": "ALL"
                }, {
                    "Name": "MetricClass",
                    "Value": "NONE"
                }, {
                    "Name": "Instance",
                    "Value": "NONE"
                }]
            },
            'Period': 3600,
            'Stat': 'Minimum',
            'Unit': 'None'
        },
        'ReturnData':
        True,
        'AccountId':
        'igraph'
    }],
                                                 StartTime=before_time,
                                                 EndTime=current_time,
                                                 ScanBy='TimestampAscending')
    Spot_Capacity = {}
    result = response['MetricDataResults'][0]['Values']
    vcpu_result = list(map(lambda x: x * instance_vcpu, result))
    avg_value = sum(vcpu_result) / len(vcpu_result) if vcpu_result else 0
    #筛选掉数量较少的实例
    if avg_value < 100:
        return None
    Spot_Capacity[instance_type] = vcpu_result
    score = get_score(vcpu_result)
    return (score,Spot_Capacity)

#对容量进行打分，总和考虑容量平均值和波动率，平均值越大波动率越小得分越高
def get_score(data_list):
    avg = np.mean(data_list)
    std = np.std(data_list)
    volatility = std / avg
    score = avg / (1 + volatility)
    return score


def main():
    current_dir = os.getcwd()
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M")
    file_name = f"spot_output_{timestamp}.csv"
    file_path = os.path.join(current_dir, file_name)
    instances_combo = {}
    # 定义默认值
    instance_type_filters = [
        {
            'Name': 'instance-type',
            'Values': ['r5a.*', 'r5ad.*', 'r5b.*', 'r5.*', 'r5d.*', 'r6a.*', 'r6i.*', 'r6id.*', 'r6g.*', 'r6gd.*', 'r7a.*', 'r7i.*', 'r7g.*', 'r7gd.*']
        },
        {
            'Name': 'bare-metal',
            'Values': ['false']  # 过滤掉Metal的实例类型
        }
    ] #根据实际情况进行筛选
    pattern = r'(8|12|16|24|32|48)xlarge' #根据实际情况进行筛选

    try:
        calculate_result = {}
        instance_type_list = get_instance_list(instance_type_filters, pattern)
        for az_code in az_code_list:
            print(f"Fetching Data: {az_code}")
            all_results = []
            filtered_results = {}
            for instance_item in instance_type_list:
                inst_type = instance_item['instance_type']
                inst_vcpu = instance_item['vcpu']
                metric_name = inst_type + '.generic.novice.' + az_code + '.AdmissionControl.Available'
                #查询spot容量
                query_result = Spot_query(inst_type,inst_vcpu,metric_name, before_time, current_time)
                if query_result:
                    all_results.append(query_result)
            #根据 score 从大到小排序
            all_results.sort(reverse=True, key=lambda x: x[0])
            #print(all_results)
            # 列score排名前35的实例清单，然后进行排列组合计算。这个该值越大计算难度越高
            for i in range(min(35, len(all_results))):
                filtered_results.update(all_results[i][1])
            min_value,combo_result = Find_Best_Combo.process_data(az_code,filtered_results)
            az_name = az_mappint(az_code)
            calculate_result[az_name] = combo_result
            print(min_value)
            print(list(combo_result))
        #send_message_to_queue(json.dumps(calculate_result))
    except Exception as e:
        print("An error occurred:", e)
        logging.info('An error occurred:: %s',e)

if __name__ == "__main__":
    main()
