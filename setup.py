# -*- coding: utf8 -*-
import sys
import json
import time
import base64
import zipfile
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore
import config
from urllib.parse import urlparse
import socket
import requests
from requests.exceptions import RequestException

from tencentcloud.common import credential
from tencentcloud.scf.v20180416 import scf_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)


# 填入腾讯云的 SecretId 和 SecretKey
SecretId = config.SecretId
SecretKey = config.SecretKey

# "ap-nanjin"
domestic_areas = [
    "ap-beijing",
    "ap-chengdu",
    "ap-guangzhou",
    "ap-shanghai",
    "ap-hongkong",
    "ap-nanjing"
]
foreign_areas = [
    "ap-singapore",
    "ap-bangkok",
    "ap-seoul",
    "ap-tokyo",
    "eu-frankfurt",
    "na-ashburn",
    "na-siliconvalley",
]
areas_dict = {
    "domestic": domestic_areas,
    "foreign": foreign_areas,
    "all": domestic_areas + foreign_areas,
}


def get_zip():
    # with zipfile.ZipFile("server.zip", "w", zipfile.ZIP_DEFLATED) as f:
    #     f.write("server.py")

    with open("server.zip", "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


def remove_file(filename):
    f = Path(filename)
    f.unlink(missing_ok=True)


def create_client(city):
    cred = credential.Credential(SecretId, SecretKey)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "scf.tencentcloudapi.com"

    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    return scf_client.ScfClient(cred, city, clientProfile)

# 创建云函数
def create_scf(client, function_name):
    req = models.CreateFunctionRequest()
    params = {
        "FunctionName": function_name,
        "Code": {
            "ZipFile": get_zip(),
        },
        "Handler": "server.main_handler",
        "Runtime": "Python3.6",
        "Timeout": 60,
        "Namespace": "default",
        # "Type": "Event",
        "AutoDeployClsTopicIndex": "FALSE",
        "AutoCreateClsTopic": "FALSE",
        "Description": "SCF_Proxy",

    }
    body = client.call(action="CreateFunction",params=params)
    if "Error" in body:
        response = json.loads(body)
        code = response["Response"]["Error"]["Code"]
        message = response["Response"]["Error"]["Message"]
        reqid = response["Response"]["RequestId"]
        raise TencentCloudSDKException(code, message, reqid)
    

# 创建函数url
def create_func_url(client,function_name):
    req = models.CreateTriggerRequest()
    trigger_desc = {
        "AuthType": "NONE",
        "NetConfig": {
            "EnableIntranet": False,
            "EnableExtranet":  True
        }
    }
    params = {
        "FunctionName": function_name,
        "TriggerName": "func_url",
        "TriggerDesc": json.dumps(trigger_desc),
        "Type": "http",
        "Namespace": "default",
        "Enable": "OPEN"
    }
    # print(f"creat_func_url :\n{json.dumps(params)}")
    '''
    
    '''
    req.from_json_string(json.dumps(params))
    resp = client.CreateTrigger(req)
    data = json.loads(resp.to_json_string())
    trigger_url = json.loads(data["TriggerInfo"]["TriggerDesc"])["NetConfig"]["ExtranetUrl"]
    return trigger_url

# API网关已经弃用
'''
def create_trigger(client, function_name):
    req = models.CreateTriggerRequest()
    params = {
        "FunctionName": function_name,
        "TriggerName": "http_trigger",
        "Type": "apigw",
        "TriggerDesc": """{
            "api":{
                "authRequired":"FALSE",
                "requestConfig":{
                    "method":"ANY"
                },
                "isIntegratedResponse":"TRUE"
            },
            "service":{
                "serviceName":"SCF_API_SERVICE"
            },
            "release":{
                "environmentName":"release"
            }
        }""",
    }
    req.from_json_string(json.dumps(params))
    resp = client.CreateTrigger(req)

    data = json.loads(resp.to_json_string())
    print(data)
    trigger_url = json.loads(data["TriggerInfo"]["TriggerDesc"])["service"]["subDomain"]
    return trigger_url
'''

def delete_scf(SCF_Proxy):
    city = SCF_Proxy.split()[0]
    url = SCF_Proxy.split()[1]
    function_name = SCF_Proxy.split()[2]
    # print(f"[INFO] 正在删除 {city} 区域云函数 {function_name} in {url}")
    client = create_client(city)
    try:
        req = models.DeleteFunctionRequest()
        params = {"FunctionName": f"{function_name}", "Namespace": "default"}
        req.from_json_string(json.dumps(params))
        client.DeleteFunction(req)
        print(Fore.GREEN+f"[SUCCESS] {city} 区域云函数 {function_name} 删除成功"+Fore.RESET)
        return True
    except TencentCloudSDKException as err:
        print(Fore.RED+f"[ERROR] 删除时错误{err}"+Fore.RESET)
        return False

def Delete_Triggers(client,function_name):
    try:
        req = models.ListTriggersRequest()
        params = {
            "FunctionName": function_name
        }
        req.from_json_string(json.dumps(params))
        resp = client.ListTriggers(req)
        trigger_names_types = []
        # print(resp.Triggers)
        for trigger in resp.Triggers:
            trigger_names_types.append((trigger.TriggerName,trigger.Type,trigger.Qualifier))
        # print(trigger_names_types)
        for trigger_name,type,Qualifier in trigger_names_types:
            # 调用DeleteTrigger接口删除触发器
            delete_request = models.DeleteTriggerRequest()
            delete_request.FunctionName = function_name
            delete_request.TriggerName = trigger_name
            delete_request.Qualifier = Qualifier
            delete_request.Type = type
            # print(delete_request)
            delete_response = client.DeleteTrigger(delete_request)
            print(Fore.GREEN+f"[INFO] Deleted trigger: {trigger_name} for {function_name}"+Fore.RESET)
    except Exception as e:
        print(Fore.RED+f"[ERROR] 删除自动创建的触发器失败{e}"+Fore.RESET)

def install(city_num):
    city = city_num[0]
    i = city_num[1]
    function_name = f"http_{city}_{i}"
    # print(f"function_name: {function_name}")
    # print("create_client......")
    client = create_client(city)
    print(f"[INFO] 正在创建{city}区域云函数：{function_name}")
    create_scf_times = 0
    while True:
        create_scf_times += 1
        # 最多请求10次避免死锁
        if create_scf_times > 10 :
            print(Fore.RED+f"[ERROR] {city}区域云函数{function_name}创建失败"+Fore.RESET)
            return city, "None_func_url", function_name
        try:
            create_scf(client, function_name)
        except TencentCloudSDKException as err:
            # err.code
            # print(Fore.RED+f"[ERROR] {city} 区域云函数创建失败 {err}"+Fore.RESET)
            if err.code == "FailedOperation":
                time.sleep(5)
                continue
            else :
                break
        except Exception as e:
            # print(e)
            break
        else:
            print(Fore.GREEN+f"[SUCCESS] {city} 区域云函数创建成功 {function_name}"+Fore.RESET)
            break

    time.sleep(5)
    trigger_url = "None_func_url"
    print(f"[INFO] 正在为函数{function_name}创建函数url")
    Delete_Triggers(client,function_name)
    Delete_Triggers_times = 0
    while True:
        Delete_Triggers_times += 1
        # 最多请求5次避免死锁
        if Delete_Triggers_times > 10 :
            break
        # print(f"{city_num} Delete_Triggers_times:{Delete_Triggers_times}")
        try:
            trigger_url = create_func_url(client, function_name)
        #     response = requests.get(trigger_url)
        # except RequestException as e:
        #     print(e)
        #     Delete_Triggers(client,function_name)   
        except TencentCloudSDKException as err:
            if err.code == "FailedOperation":
                # print(Fore.RED+f"[ERROR] 为{function_name}创建函数url时错误:{err}"+Fore.RESET)
                time.sleep(5)
                continue
            if err.code == "LimitExceeded.Trigger":
                print(Fore.RED+f"[ERROR] 为{function_name}创建函数url时错误:{err}"+Fore.RESET)
                break
        except Exception as e:
            print(Fore.RED+f"[ERROR] 为{function_name}创建函数url时错误:{e}"+Fore.RESET)
            break
        else:
            if trigger_url:
                print(Fore.GREEN+f"[SUCCESS] {city} 区域云函数{function_name}已创建函数url {trigger_url}"+Fore.RESET)
                break
        
    return city, trigger_url, function_name


def get_parser():
    parser = argparse.ArgumentParser(
        description="""腾讯云函数 HTTP 代理一键配置

# 部署单个城市
python setup.py install -c ap-beijing

# 部署区域内所有城市
python setup.py install -a domestic

# 删除所有通过 setup.py 部署的云函数
python setup.py delete

建议：
1. 大陆外地区部署的云函数延迟较高，推荐只使用国内的
2. 随用随装，用完删除
""",
        add_help=False,
        usage="python3 %(prog)s action [-c city] [-a area] [-h]",
        
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("install", "delete"),
        default="install",
        metavar="action",
        help="install 或 delete",
    )
    parser.add_argument(
        "-h", "--help", action="help", default=argparse.SUPPRESS, help="展示帮助信息"
    )
    parser.add_argument(
        "-c", "--city", dest="city", metavar="city", 
        help="""云函数部署城市

可选城市:
    大陆地区: ap-beijing, ap-chengdu, ap-guangzhou, ap-shanghai, sp-nanjing
    亚太地区: ap-hongkong, ap-mumbai, ap-singapore, ap-bangkok, ap-seoul, ap-tokyo
    欧洲地区: eu-frankfurt
    北美地区: na-siliconvalley, na-ashburn
        
"""
    )
    parser.add_argument(
        "-a", "--area",
        metavar="area",
        dest="area",
        help="""云函数部署区域（包含多个城市）

可选区域: 
    大陆地区: domestic
    非大陆地区: foreign
    所有地区: all
    """,
    )
    return parser



def test():
    # print(areas_dict["domestic"])
    # results = install("ap-shanghai")
    # print(results)
    # delete_scf("ap-shanghai")
    num = [i for i in range(0,5)]
    city_num = [(city,i) for city in areas_dict["domestic"] for i in num]
    print(city_num)
    # client = create_client("ap-guangzhou")
    # Delete_Triggers(client,"http_ap-guangzhou")

def main():
    parser = get_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        exit()

    args = parser.parse_args()
    print(f"[INFO] action:{args.action}")
    print(f"[INFO] city:{args.city}")
    print(f"[INFO] area:{args.area}")
    if args.action == 'install':
        if not (args.city or args.area):
            print(f"请输入城市或区域")
            exit()
        
        with open("cities.txt", "a") as f:
            if args.area in ["all", "domestic", "foreign"]:
                
                # 创建并启动线程池
                threads = []
                num = [i for i in range(0,config.MAX_SCF)]
                city_num = [(city,i) for city in areas_dict[args.area] for i in num]
                print(city_num)
                with ThreadPoolExecutor(max_workers=len(city_num)) as executor:
                    results = list(executor.map(install, city_num))

                for city, trigger, function_name in results:
                    if trigger:
                        f.write(f"{city} {trigger} {function_name}\n")

            elif args.city in areas_dict['all']:
                city, trigger, function_name = install(args.city)
                if trigger:
                    f.write(f"{city} {trigger} {function_name}\n")
            else:
                print(f"请输入有效的城市或区域")
                exit()

        # remove_file("code.zip")


    elif args.action == "delete":
        try:
            with open("cities.txt", "r") as f:
                SCF_Proxies = f.readlines()
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = list(executor.map(delete_scf, SCF_Proxies))

        except TencentCloudSDKException as err:
            print(err)
        else:
            remove_file("cities.txt")
            print(Fore.GREEN+"[Success] 已成功删除cities.txt文件"+Fore.RESET)

if __name__ == "__main__":
    # test()
    main()