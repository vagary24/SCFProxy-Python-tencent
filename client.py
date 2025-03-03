import json  # 导入json模块，用于处理JSON数据
from random import choice  # 导入choice函数，用于从列表中随机选择一个元素
from urllib.parse import urlparse  # 导入urlparse函数，用于解析URL
from base64 import b64encode, b64decode  # 导入base64编码和解码函数
from colorama import Fore

import mitmproxy  # 导入mitmproxy库，用于拦截和修改网络流量
from mitmproxy.version import VERSION  # 导入mitmproxy的版本信息
from mitmproxy import ctx
'''
开启代理开始运行：

mitmdump -s client.py -p 8081 --no-http2
如在 VPS 上运行需将 block_global 参数设为 false

mitmdump -s client.py -p 8081 --no-http2 --set block_global=false
'''

# 根据mitmproxy的版本导入Headers类
if int(VERSION[0]) > 6:
    from mitmproxy.http import Headers
else:
    from mitmproxy.net.http import Headers

# 读取包含服务器列表的文件，并去除每行的空白字符
with open('cities.txt', 'r') as f:
    scf_servers = [{line.split()[0].strip():line.split()[1].strip()} for line in f if "None_func_url" not in line]
    print(scf_servers)
# 定义CSS样式，用于美化JSON输出
css = """pre {
    /* 多行文本的CSS样式，兼容不同浏览器 */
    white-space: pre-wrap;       /* 符合CSS 2.1标准 */
    white-space: -moz-pre-wrap;  /* Mozilla早期版本 */
    white-space: -pre-wrap;      /* Opera 4-6版本 */
    white-space: -o-pre-wrap;    /* Opera 7版本 */
    word-wrap: break-word;       /* IE 5.5+版本 */
}"""

def start():
    # 设置客户端超时时间为10秒
    ctx.options.client_timeout = 10
    # 设置服务器超时时间为10秒
    ctx.options.server_timeout = 10

# 定义请求拦截函数
def request(flow: mitmproxy.http.HTTPFlow):
    # 随机选择一个服务器
    scf_server = choice(scf_servers)
    for city,scf_url in scf_server.items():
        print(Fore.GREEN+f"[+]当前区域代理: {city} {scf_url} 访问url{flow.request.pretty_url}"+Fore.RESET)
        scf_server = scf_url
    # print(Fore.GREEN+f"[+]当前区域代理: {scf_server.keys} {scf_server.values}访问{flow.request.pretty_url}"+Fore.RESET)
    # scf_server = scf_server
    request = flow.request  # 获取当前请求对象
    # print("************************请求***************************")
    # print(request)
    # 构造新的请求数据
    data = {
        "method": request.method,  # 请求方法
        "url": request.pretty_url,  # 格式化后的URL
        "headers": dict(request.headers),  # 请求头
        "body": b64encode(request.raw_content).decode('utf-8')  # 请求体
    }
    # "body": b64encode(request.raw_content).decode('utf-8'),  # 请求体，使用base64编码
    # 修改原始请求为POST请求到随机选择的服务器
    req_json = json.dumps(data)
    # print(req_json)
    b64_req_json = b64encode(req_json.encode('utf-8'))

    flow.request = flow.request.make(
        "POST",  # 设置请求方法为POST
        url=scf_server,  # 设置请求的URL
        content=b64_req_json,  # 设置请求体为JSON格式的数据
        headers={  # 设置请求头
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, compress",
            "Accept-Language": "en-us;q=0.8",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            "Connection": "Keep-Alive",
            "Host": urlparse(scf_server).netloc,  # 设置Host头为服务器的域名
        },
    )

# 定义响应拦截函数
def response(flow: mitmproxy.http.HTTPFlow):
    # print("*****************************响应**************************")
    # print(flow.response)
    status = flow.response.status_code  # 获取响应状态码

    # 根据不同的状态码执行不同的操作
    if status != 200:
        mitmproxy.ctx.log.warn("Error")  # 如果状态码不是200，记录警告

    if status == 401:
        flow.response.headers = Headers(content_type="text/html;charset=utf-8")
        return  # 401状态码，设置响应头并结束

    elif status == 433:
        flow.response.headers = Headers(content_type="text/html;charset=utf-8")
        flow.response.content = "test",  # 433状态码，设置响应内容
        return

    elif status == 430:
        # 430状态码，美化JSON响应
        body = flow.response.content.decode("utf-8")
        data = json.loads(body)
        flow.response.headers = Headers(content_type="text/html;charset=utf-8")
        flow.response.text = f'<style>{css}</style><pre id="json"></pre><script>document.getElementById("json").textContent = JSON.stringify({data}, undefined, 2);</script>'
        return

    elif status == 200:
        # 200状态码，处理响应内容
        # print(flow.response.content)
        response = flow.response.content.decode("utf-8")
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            print("解析JSON时发生错误，响应内容可能不是有效的JSON格式")
        if response :
            # print("**************************response********************************************************")
            # print(response)
            # print(response.get("headers",{}))
            headers = response.get("headers",{})
            # print("************************************headers*******************************")
            # print(headers)
            body = response.get("content","")
            if body :
                body = b64decode(body)
            # 重新构造响应对象
            r = flow.response.make(
                status_code=response["status_code"],
                headers=dict(headers),
            )
            # print("*************************************body*************************")
            # print(body)
            # if headers.get("content-encoding", None):
            r.raw_content = body
            if "transfer-encoding" not in r.headers:
                r.headers['content-length'] = str(len(r.raw_content))
            # else:

            #     r.content = body

            flow.response = r