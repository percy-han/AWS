# -*- coding: utf-8 -*-
import logging
import datetime
import numpy as np
import pandas as pd
import multiprocessing as mp
from urllib.parse import quote
from itertools import combinations
import time

# 设置日志配置
logging.basicConfig(filename='process_data.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 把给定机型组合中每个时间点数据相加，得到一个实例容量的总和波动曲线
def calculate_min_value(combo, pdx_data):
    total_capacity_series = None
    for instance_item in combo:
        capacity_series = np.array(pdx_data[instance_item])
        # 检查形状是否相同,如果不同则广播数组
        # 如果 total_capacity_series 为 None,则初始化为与 capacity_series 相同的形状
        if total_capacity_series is None and capacity_series.size > 0:
            total_capacity_series = np.zeros_like(capacity_series)
        # 只有当 capacity_series 不为空时,才进行累加
        if capacity_series.size > 0:
            total_capacity_series += capacity_series
    #print(total_capacity_series)
    #获取到这个波动曲线的最低点
    min_value = min(total_capacity_series)
    return min_value, combo

# 多进程处理函数
def process_combos(chunk, data):
    max_min_value = -np.inf
    best_combo = None
    for combo in chunk:
        min_value, combo = calculate_min_value(combo, data)
        #获取到每个组合的最小值，并筛选出最小值最大的组合
        if min_value > max_min_value:
            max_min_value = min_value
            best_combo = combo

    return max_min_value, best_combo

# 包装参数的辅助函数
def wrapper_process_combos(args):
    return process_combos(*args)

def process_data(az_code, data, tries=4, delay=3, backoff=2):
    # 初始化总结果变量
    overall_max_min_value = -np.inf
    overall_best_combo = None

    for attempt in range(tries):
        try:
            logging.info(f"Processing {az_code}")
            instance_types = list(data.keys())
            logging.info(f"Instance types in {az_code}: {instance_types}")

            # 如果实例类型数量小于等于30，直接返回这些实例类型
            if len(instance_types) <= 30:
                logging.info(f"Instance types are less than or equal to 30, returning: {instance_types}")
                return instance_types.tolist()

            #从给定机型列表中筛选出30种机型，并排列组合其可能性
            combos = list(combinations(instance_types, 30))
            logging.info(f"Number of combos in {az_code}: {len(combos)}")
            # 对排列组合进行分块，并行计算
            num_chunks = mp.cpu_count()  # 使用CPU核心数量
            chunk_size = len(combos) // num_chunks
            chunks = [combos[i:i + chunk_size] for i in range(0, len(combos), chunk_size)]
            logging.info(f"Number of chunks created: {len(chunks)}")
            # 创建进程池
            pool = mp.Pool(processes=num_chunks)
            # 并行计算
            results = pool.map(wrapper_process_combos, [(chunk, data) for chunk in chunks])
            # 关闭进程池
            pool.close()
            pool.join()
            # 汇总结果
            for max_min_value, best_combo in results:
                if max_min_value > overall_max_min_value:
                    overall_max_min_value = max_min_value
                    overall_best_combo = best_combo
            # 获取当前时间并记录到日志文件
            #logging.info('Result:')
            logging.info(f"overall_best_combo: {overall_best_combo}")
            logging.info(f"overall_max_min_value: {overall_max_min_value}")
            #metrics = [' + instance_type + '.generic.novice.' + az_code + '.AdmissionControl.Available for instance_type in overall_best_combo]
            metrics = [f"{instance_type}.generic.novice.{az_code}.AdmissionControl.Available" for instance_type in overall_best_combo]
            metric_string = '|'.join(metrics)
            original_string = "schemaname=$Service$ dataset=$Prod$ marketplace=$PDX$ hostgroup=$ALL$ host=$ALL$ servicename=$EC2SpotCapacityMonitorService$ methodname=$ALL$ client=$ALL$ metricclass=$NONE$ instance=$NONE$ metric=" + metric_string
            encoded_url = quote(original_string, safe='')
            url = "https://monitorportal.amazon.com/igraph?SchemaName1=Search&Pattern1=" + encoded_url + "&Period1=FiveMinute&Stat1=avg&HeightInPixels=756&WidthInPixels=2004&GraphTitle=spotusage&DecoratePoints=true&GraphType=zoomer&TZ=Asia%2FShanghai@TZ%3A%20Shanghai&LabelLeft=slots&StartTime1=-P14D&EndTime1=-PT0H&FunctionExpression1=SUM%28S1%29&FunctionLabel1=Total%20%28sum%20of%20sums%3A%20%7Bsum%7D%29&FunctionYAxisPreference1=left"
            logging.info(url)
            return overall_max_min_value,overall_best_combo
        except Exception as e:
            logging.error(f"Error: {str(e)}, Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff
    logging.error(f"Processing {az_code} failed after {tries} attempts.")
    return None
