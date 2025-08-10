# MignonFramework

MignonFramework 是由 Mignon Rex 开发的一个强大而灵活的 Python 工具集，旨在为爬虫工程师和后端开发者提供一系列高效、便捷的实用工具。

这个框架整合了多种常用功能，从网络请求转换到文件处理，再到日志和配置管理，是你日常开发中的得力助手。

核心组件
MignonFramework 包含了以下核心模块：

Curl2Request: 一个强大的 cURL 命令转换器，可以轻松将从浏览器复制的 cURL 命令转换为功能完整的 Python requests 代码，支持表单、认证、Cookies 等多种复杂场景。

ConfigReader: 线程安全的配置文件管理器，简化 .ini 文件的读取和写入操作。

Queue: 一个灵活的队列生成器，支持对列表或 range 对象进行随机化排序，非常适合用于爬虫的目标队列管理。

Deduplicate: 高效的大文件去重工具，可以快速移除文件中的重复行。

CountLinesInFolder: 代码行数统计工具，支持按前缀、后缀或正则表达式筛选文件。

Logger: 一个简单的日志记录器。

PortForwarding: 一个基础的端口转发工具。

安装
你可以通过 pip 轻松安装 MignonFramework：

pip install MignonFramework

快速开始
以 Curl2Request 为例，体验一下 MignonFramework 的便捷：

from mignon_framework.Curl2Reuqest import CurlToRequestsConverter

# 从浏览器开发者工具中复制的 cURL 命令
curl_command = """
curl '[https://httpbin.org/post](https://httpbin.org/post)' \
-H 'Content-Type: application/json' \
-d '{"name": "Mignon", "framework": "awesome"}'
"""

# 实例化转换器
converter = CurlToRequestsConverter(curl_input=curl_command)

# 直接获取生成的 Python 代码
python_code = converter._generate_python_code() # 注意：为了直接获取字符串，我们调用内部方法

print(python_code)

许可证
本项目采用 MIT 许可证。