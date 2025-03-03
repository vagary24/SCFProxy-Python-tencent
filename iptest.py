import requests
from concurrent.futures import ThreadPoolExecutor
import threading
import config
# 创建一个锁对象
file_lock = threading.Lock()

# 设置代理
proxies = config.proxies
# proxies = None
# 目标网址
url = 'http://myip.ipip.net/'


def get_IPinfo():
    try:
        # 发送GET请求
        response = requests.get(url, proxies=proxies)
        # 确保请求成功
        response.raise_for_status()
        # 打印响应内容
        print(response.text)
        return response.text
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"OOps: Something Else: {err}")

with ThreadPoolExecutor(max_workers=10) as executor:
    # 提交一百次get_IPinfo函数调用
    futures = [executor.submit(get_IPinfo) for _ in range(100)]
    # 获取所有结果
    results = [future.result() for future in futures]
    print(results)
    for info in results:
        if info:
            with open("./proxy_ip.txt","a",encoding="utf-8") as f:
                f.write(info)