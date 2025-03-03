# -*- coding: utf8 -*-
import json
import urllib3
from urllib3.util.timeout import Timeout
from base64 import b64decode, b64encode

def main_handler(event, context):
    try:
        req = b64decode(event.get("body"))
        kwargs = json.loads(req)
        kwargs['body'] = b64decode(kwargs['body'])
        # 设置超时
        timeout_config = Timeout(connect=5.0, read=10.0)  
        # 连接超时10秒，读取超时10秒
        http = urllib3.PoolManager(cert_reqs="CERT_NONE", timeout=timeout_config)
        r = http.request(**kwargs, retries=False, decode_content=False)
        response = {
            "msg" : r.msg,
            "version" : r.version,
            "headers": {k.lower(): v.lower() for k, v in r.headers.items()},
            "status_code": r.status,
            "content": b64encode(r._body).decode('utf-8')
        }
        # print(response)
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(response)
        }
    except Exception as e:
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {},
            "body": e
        }