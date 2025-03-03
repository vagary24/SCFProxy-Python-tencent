# Help
由于腾讯云停用api网关，导致原本的SCFProxy-Python项目中腾讯云云函数代理的项目失效，这里用函数url实现了云函数代理的功能，原项目是shimmeris师傅的python版本[https://github.com/shimmeris/SCFProxy](https://github.com/shimmeris/SCFProxy)
由于项目是2024年10月写的，不知道原项目作者修改腾讯云api网关用不了的问题没有，这两天突然刚好用到就发了出来。如果遇到任何问题欢迎留言，长时间不回复请加微信king8n94
## 使用前置

1. 在config.py中配置腾讯云SecretId和SecretKey

    参考这篇文章[腾讯云如何查看secretKey（只能查看secretId而secretKey无法查看）_腾讯云secretkey-CSDN博客](https://blog.csdn.net/lightlyg/article/details/137376702)
    config.py中MAX_SCF设置某区域内最大云函数数量，腾讯云好像限制单个区域最大是10个云函数，根据需求自行调整。
2. 创建python虚拟机(自行原则，mitmproxy依赖可能与本地一些环境会起冲突，建议创建python虚拟机)
    ```cmd
    python3 -m venv myenv

3. 安装依赖

   ```cmd
   pip install -r requirements.txt
   ```

## 启动

1. 查看使用帮助*** 国外部署的云函数延迟较高，推荐只使用国内的 ***

   ```cmd
   python ./setup.py -h
   
   usage: python3 setup.py action [-c city] [-a area] [-h]
   
   腾讯云函数 HTTP 代理一键配置
   
   # 部署单个城市
   python setup.py install -c ap-beijing
   
   # 部署区域内所有城市
   python setup.py install -a domestic
   
   # 删除所有通过 setup.py 部署的云函数
   python setup.py delete
   
   建议：
   1. 国外部署的云函数延迟较高，推荐只使用国内的
   2. 随用随装，用完删除
   
   positional arguments:
     action                install 或 delete
   
   optional arguments:
     -h, --help            展示帮助信息
     -c city, --city city  云函数部署城市
   
                           可选城市:
                               大陆地区: ap-beijing, ap-chengdu, ap-guangzhou, ap-shanghai, ap-nanjing
                               亚太地区: ap-hongkong, ap-mumbai, ap-singapore, ap-bangkok, ap-seoul, ap-tokyo
                               欧洲地区: eu-frankfurt
                               北美地区: na-siliconvalley, na-ashburn
   
     -a area, --area area  云函数部署区域（包含多个城市）
   
                           可选区域:
                               大陆地区: domestic
                               非大陆地区: foreign
                               所有地区: all
   ```

2. 而开启云函数后（例如：python setup.py install -a domestic），云函数信息会记录在cities.txt文件中

   ![setup](./img\setup.png)

3. 开启mitmproxy代理

   #### 本地启动

   ```cmd
   mitmdump -s client.py -p 8080 --no-http2
   ```

   #### vps上启动

   **vps会有额外的延迟**，如果自己一个人用直接本地运行就行，运行在vps上**记得在策略组中开放端口**

   ``` cmd
   // vps上启动要加 --set block_global=false
   // 建议加上proxyauth认证，避免被别人消耗
   mitmdump -s client.py -p 8080 --no-http2 --set block_global=false --proxyauth "username:password"
   
   // 后台启动
   nohup mitmdump -s client.py -p 8080 --no-http2 --set block_global=false --proxyauth "username:password" &
   
   // 查看日志
   tail -n 100 nohup.out
   ```
   #### 启动后在config.py中加入代理信息方便测试

   ```python
   proxies = {
       'http': 'http://username:password@127.0.0.1:8080',
       'https': 'https://username:password@127.0.0.1:8080',  # 通常https代理也使用http协议
   }
   ```

4. 测试代理有效性

   ```cmd
   python ./intest.py   #先在config.py中配置代理再测试
   ```

   当出现这样多处ip地址就成功了

   ![image-20250303012252932](./img/image-20250303012252932.png)

5. 正常使用直接挂代理就可以了
    ![SCFProxy](./img/SCFProxy.png)

6. 删除云函数

  ```cmd
  python setup.py delete
  ```

  ![delete](./img/delete.png)