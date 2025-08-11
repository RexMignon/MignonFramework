MignonFramework
MignonFramework 是由 Mignon Rex 与Google Gemini 协同开发的一个强大而灵活的 Python 工具集，旨在为爬虫工程师和后端开发者提供一系列高效、便捷的实用工具。

这个框架整合了多种常用功能，从网络请求转换到文件处理，再到数据库和配置管理，是你日常开发中的得力助手。

核心组件
MignonFramework 包含了以下核心模块：

Curl2Request: 一个强大的 cURL 命令转换器，可以轻松将从浏览器复制的 cURL 命令转换为功能完整的 Python requests 代码，支持表单、认证、Cookies 等多种复杂场景。

MysqlManager: 一个健壮的 MySQL 数据库管理器，实现了 BaseWriter 接口。它封装了数据库的连接、关闭、以及高效的批量“更新或插入”（Upsert）操作，并通过上下文管理器（with语句）简化了资源管理。

GenericFileProcessor: 一个高度通用的文件到数据库ETL（提取、转换、加载）工具。它通过一个统一的 run() 方法，可以智能处理单个文件或整个目录，支持“整文件JSON”和“逐行JSON”两种模式，并提供了断点续传、可视化进度条、事件回调、数据过滤和高级错误处理等功能。

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
示例 1: Curl2Request
以 Curl2Request 为例，体验一下 MignonFramework 的便捷：

from MignonFramework.Curl2Reuqest import CurlToRequestsConverter

# 从浏览器开发者工具中复制的 cURL 命令
curl_command = """
curl 'https://httpbin.org/post' \
-H 'Content-Type: application/json' \
-d '{"name": "Mignon", "framework": "awesome"}'
"""

# 实例化转换器
converter = CurlToRequestsConverter(curl_input=curl_command)

# 直接获取生成的 Python 代码
python_code = converter._generate_python_code() # 注意：为了直接获取字符串，我们调用内部方法

print(python_code)

示例 2: GenericFileProcessor
使用 GenericFileProcessor 轻松将大文件导入数据库：

from MignonFramework import MysqlManager, GenericFileProcessor, Rename
from datetime import datetime

# 1. 定义数据库配置
db_config = {"host": "localhost", "user": "root", "password": "your_password", "database": "your_db"}

# 2. 定义一个优雅的修改器函数，在自动解析后对数据进行微调
def modifier(dic: dict) -> dict:
return {
# 场景1: 只重命名 (值来自源文件)
"ProjectGrantNo": Rename("project_grant_number"),

        # 场景2: 只修改值 (键名自动转为 snake_case)
        "ProjectTitleOriginal": "【Mignon处理】" + dic.get("ProjectTitleOriginal", ""),

        # 场景3: 同时重命名和赋值
        "Source": ("data_source_custom", "来自Mignon框架"),

        # 场景4: 添加新字段 (键名自动转为 snake_case)
        "processedTime": datetime.now().isoformat()
    }

# 3. 定义一个回调函数，用于记录每批处理的状态
def log_callback(status, data, filename, line_num):
print(f"\n批处理完成: 文件 '{filename}' 行号 {line_num}, 状态: {'成功' if status else '失败'}")

# 4. 使用 with 语句自动管理数据库连接
with MysqlManager(**db_config) as db:
if db.is_connected():
# 初始化处理器
processor = GenericFileProcessor(
writer=db,
table_name="project_info",
modifier_function=modifier, # 使用 modifier_function 进行高级定制
mode='line',  # 按行处理文件
batch_size=5000,
callBack=log_callback,
print_mapping_table=True # 推荐开启，用于调试
)

        # 运行处理器，并从第10001行开始（断点续传）
        processor.run(path="../data/projects.txt", start_line=10001)

许可证
本项目采用 MIT 许可证。