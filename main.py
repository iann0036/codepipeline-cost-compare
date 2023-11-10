import boto3
import math
import os
from datetime import datetime, timezone, timedelta

COST_PER_PIPELINE_V1 = 1.00
COST_PER_ACTION_MINUTE_V2 = 0.002
FREE_TIER_V1_PIPELINES = 1
FREE_TIER_V2_ACTION_MINUTES = 100

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

client = boto3.client('codepipeline')
if 'AWS_REGION' in os.environ:
    client = boto3.client('codepipeline', region_name=os.environ['AWS_REGION'])

total_pipelines = 0
total_billable_pipelines = 0
total_billable_minutes = 0

current_month = datetime.now().month
current_month_text = datetime.now().strftime("%B")
current_year = datetime.now().year

previous_bill_month = current_month - 1
previous_bill_year = current_year
if previous_bill_month == 0:
    previous_bill_month = 12
    previous_bill_year -= 1

previous_bill_starttime = datetime(previous_bill_year, previous_bill_month, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
current_bill_starttime = datetime(current_year, current_month, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

previous_bill_month_text = previous_bill_starttime.strftime("%B")

print(f"~ Previous Bill ({previous_bill_month_text}) ~\n")

pipeline_paginator = client.get_paginator('list_pipelines')
pipeline_paginator_response_iterator = pipeline_paginator.paginate(PaginationConfig={'PageSize': 1000})
for pipeline_paginator_page in pipeline_paginator_response_iterator:
    for pipeline in pipeline_paginator_page['pipelines']:
        if 'pipelineType' not in pipeline:
            print("ERROR: Boto3 did not detect pipeline type. Upgrade boto3 to continue.")
            quit()

        print(f"{pipeline['name']}", end='', flush=True)

        pipeline_billable_minutes = 0

        if (pipeline['created'].year < previous_bill_year or pipeline['created'].month <= previous_bill_month):
            total_pipelines += 1
        else:
            print(f" • V2 Cost = $0.00")
            continue

        billable_pipeline = False

        execution_paginator = client.get_paginator('list_action_executions')
        execution_paginator_response_iterator = execution_paginator.paginate(pipelineName=pipeline['name'], PaginationConfig={'PageSize': 100})
        for execution_paginator_page in execution_paginator_response_iterator:
            for action_execution in execution_paginator_page['actionExecutionDetails']:
                if action_execution['input']['actionTypeId']['category'] == "Approval" or action_execution['input']['actionTypeId']['owner'] == "Custom": # https://aws.amazon.com/codepipeline/pricing/
                    continue

                if (
                    (action_execution['lastUpdateTime'].month == previous_bill_month and action_execution['lastUpdateTime'].year == previous_bill_year) or
                    (action_execution['startTime'].month == previous_bill_month and action_execution['startTime'].year == previous_bill_year)
                ):
                    billable_pipeline = True
                    cost = math.ceil((min(action_execution['lastUpdateTime'], current_bill_starttime) - max(previous_bill_starttime, action_execution['startTime'])).total_seconds()/60)
                    total_billable_minutes += cost
                    pipeline_billable_minutes += cost

        if ((pipeline['created'] + timedelta(days=30)) > current_bill_starttime): # https://aws.amazon.com/codepipeline/pricing/
            billable_pipeline = False

        if billable_pipeline:
            total_billable_pipelines += 1

        v2_pipeline_cost_nft = (pipeline_billable_minutes * COST_PER_ACTION_MINUTE_V2)

        if v2_pipeline_cost_nft > COST_PER_PIPELINE_V1:
            print(f" • V2 Cost = {bcolors.FAIL}${v2_pipeline_cost_nft:,.2f}{bcolors.ENDC} (V2 cost is higher)")
        elif (v2_pipeline_cost_nft == COST_PER_PIPELINE_V1) or (v2_pipeline_cost_nft == 0 and not billable_pipeline):
            print(f" • V2 Cost = ${v2_pipeline_cost_nft:,.2f} (V2 cost is equal)")
        else:
            print(f" • V2 Cost = {bcolors.OKGREEN}${v2_pipeline_cost_nft:,.2f}{bcolors.ENDC} (V2 cost is lower)")

v1_cost = max(0, total_billable_pipelines - FREE_TIER_V1_PIPELINES) * COST_PER_PIPELINE_V1
v1_cost_nft = total_billable_pipelines * COST_PER_PIPELINE_V1
v2_cost = max(0, ((total_billable_minutes - FREE_TIER_V2_ACTION_MINUTES) * COST_PER_ACTION_MINUTE_V2))
v2_cost_nft = (total_billable_minutes * COST_PER_ACTION_MINUTE_V2)

print(f"\nTotal Pipelines: {total_pipelines:,}")
print(f"Total Billable Pipelines: {total_billable_pipelines:,}")
print(f"Total Billable Minutes: {total_billable_minutes:,}")

if v1_cost > v2_cost:
    print(f"Total Cost Under V1: {bcolors.FAIL}${v1_cost:,.2f} (${v1_cost_nft:,.2f} without free tier){bcolors.ENDC}")
    print(f"Total Cost Under V2: {bcolors.OKGREEN}${v2_cost:,.2f} (${v2_cost_nft:,.2f} without free tier){bcolors.ENDC}")
    print(f"V2 is {bcolors.OKGREEN}${v1_cost - v2_cost:,.2f}{bcolors.ENDC} cheaper than V1")
elif v1_cost == v2_cost:
    print(f"Total Cost Under V1: ${v1_cost:,.2f} (${v1_cost_nft:,.2f} without free tier)")
    print(f"Total Cost Under V2: ${v2_cost:,.2f} (${v2_cost_nft:,.2f} without free tier)")
    print(f"V1 and V2 are equal in cost")
else:
    print(f"Total Cost Under V1: {bcolors.OKGREEN}${v1_cost:,.2f} (${v1_cost_nft:,.2f} without free tier){bcolors.ENDC}")
    print(f"Total Cost Under V2: {bcolors.FAIL}${v2_cost:,.2f} (${v2_cost_nft:,.2f} without free tier){bcolors.ENDC}")
    print(f"V1 is {bcolors.FAIL}${v2_cost - v1_cost:,.2f}{bcolors.ENDC} cheaper than V2")
