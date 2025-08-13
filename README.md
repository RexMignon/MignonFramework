# mignonFramework

`pip install mignonFramework`

mignonFramework 是一个由 Mignon Rex 设计和开发的轻量级、模块化的 Python 工具框架。它旨在通过提供一系列即用型的高性能组件，来简化和加速数据处理、网络爬虫、自动化任务和日常开发流程。

核心理念
模块化: 每个组件都专注于解决一个特定的问题，可以独立使用。

易用性: 提供简洁的 API 和“零配置”启动能力，上手快，集成方便。

高性能: 在文件处理、数据库操作等方面，针对性能进行了优化。

安装与使用
mignonFramework 作为本地包使用。请确保你的项目结构能够正确解析导入路径。

在你的项目中，可以像这样导入整个框架或特定的组件：

# 推荐方式：导入整个框架并使用别名
`import mignonFramework as mg`

# 或者只导入需要的特定组件
`from mignonFramework import InsertQuick, Curl2Reuqest`

核心组件概览
1. GenericFileProcessor (别名: InsertQuick)
   一个功能强大的通用 ETL (提取、转换、加载) 工具，专门用于高效处理逐行 JSON 文件 (.jsonl, .txt) 并将其导入数据库。

核心功能:

自动映射: 自动将 JSON 的驼峰命名法键 (camelCase) 转换为数据库的蛇形命名法 (snake_case)。

数据转换: 通过 modifier_function，可以轻松地重命名字段、修改值、或添加新字段。

数据过滤: 使用 filter_function，可以根据内容或行号跳过不需要的数据。

批量写入: 高效地将数据分批次写入目标，支持 MySQLManager 等写入器。

零配置启动: 如果未提供数据库配置，它会智能引导用户创建配置文件。

测试模式: 提供 -test 模式，可以自动诊断并建议修复方案（如自动排除表中不存在的字段）。

示例:
假设有一个 data.txt 文件，内容如下：

`{"userName": "Mignon", "userAge": 30, "city": "Shanghai"}
{"userName": "Rex", "userAge": 28, "city": "Beijing"}
`
我们可以这样处理它：

```
import mignonFramework as mg
from datetime import datetime

# 1. 定义一个 Mock 写入器用于演示
class MockWriter(mg.BaseWriter):
def upsert_batch(self, data_list, table_name, test=False):
print(f"--> 正在向表 '{table_name}' 写入 {len(data_list)} 条数据:")
for item in data_list:
print(f"    {item}")
return True`

# 2. 定义一个修改器函数
def my_modifier(data: dict) -> dict:
return {
"userName": mg.Rename("name"),  # 将 userName 重命名为 name
"userAge": ("age_in_years", data.get("userAge", 0)), # 重命名并确保有值
"processedAt": datetime.now().isoformat() # 添加一个新字段
}

# 3. 初始化并运行处理器
processor = mg.InsertQuick(
writer=MockWriter(),
table_name="users",
modifier_function=my_modifier,
exclude_keys=["city"] # 忽略原始数据中的 city 字段
)
processor.run(path="data.txt")
```
输出:

`--> 正在向表 'users' 写入 2 条数据:
{'name': 'Mignon', 'age_in_years': 30, 'processed_at': '...'}
{'name': 'Rex', 'age_in_years': 28, 'processed_at': '...'}
`

2. ProcessFile (别名: processRun)
   一个健壮的、可断点续传的文件处理引擎。它的核心任务是监控一个输入目录，将目录中的每个文件（默认视为一个完整的 JSON 对象）进行解析、添加元数据，然后追加写入到一个大的结果文件中。

核心功能:

自动化: 持续监控指定目录，自动处理新文件。

断点续传: 通过两种模式保证处理的连续性：

config (默认): 使用 SQLite 数据库记录已处理文件的状态，稳定可靠。

move: 处理完文件后，将其移动到 finish 或 exception 目录，简单直观。

文件合并: 将多个小文件的内容（处理后）合并到一个或多个大的输出文件中。

自动分割: 当输出文件达到指定行数时，会自动创建新的输出文件。

配置驱动: 所有路径和参数都通过 processFile.ini 配置文件管理。

示例:
首先，创建配置文件 ./resources/config/processFile.ini:

```[config]
mode = config
input_dir = ./input_data
output_dir = ./output_data
exception_dir = ./exception_data
db_path = ./state.db
max_lines_per_file = 10000
filename_key = source_file
```

然后，在 input_data 目录中放入一些 JSON 文件，例如 file1.json: {"id": 1, "data": "..."}。

最后，只需一行代码即可启动：
```
import mignonFramework as mg

# 启动文件处理引擎，它会自动读取配置文件并开始工作
mg.processRun()
```

运行后，output_data 目录中会生成 output_0.jsonl 文件，其内容为：
{"id": 1, "data": "...", "source_file": "file1.json"}
3. CurlToRequestsConverter (别名: Curl2Reuqest)
   一个非常实用的开发工具，可以将 cURL 命令字符串快速转换为功能完整的 Python requests 代码。对于需要分析和复现网络请求的逆向工程师和爬虫工程师来说，这是一个巨大的效率提升工具。

核心功能:

全面解析: 支持解析 -X (方法), -H (请求头), -d (数据), -F (表单), -u (认证), --cookie, --proxy 等常用 cURL 参数。

智能识别: 自动区分 json 数据和普通 data 表单。

文件生成: 将转换后的 Python 代码直接保存到 .py 文件中，立即可用。

支持从文件读取: 可以直接读取包含 cURL 命令的文本文件。

示例:
```
import mignonFramework as mg

# 一个复杂的 cURL 命令，包含方法、JSON数据、请求头
curl_command = """
curl -X POST 'https://httpbin.org/post' \
-H 'Content-Type: application/json' \
-H 'User-Agent: MyClient/1.0' \
-d '{"name": "Mignon", "is_active": true}'
"""

# 创建转换器实例并执行转换
converter = mg.Curl2Reuqest(
curl_input=curl_command,
output_filename='my_request.py'
)
converter.run()

print("Python requests 代码已生成到 my_request.py 文件中。")
```
生成的 my_request.py 文件内容如下：
```
import requests
import json

# 由 Mignon Rex 的 MignonFramework.CurlToRequestsConverter 生成
# Have a good Request

headers = {
"Content-Type": "application/json",
"User-Agent": "MyClient/1.0"
}

json_data = {
"name": "Mignon",
"is_active": True
}

url = "https://httpbin.org/post"

response = requests.post(
url,
headers=headers,
json=json_data
)

print(f"状态码: {response.status_code}")
try:
print("响应 JSON:", response.json())
except json.JSONDecodeError:
print("响应文本:", response.text)
```
4. PortForwarding (别名: portForwordRun)
   一个简单的多线程端口转发工具。可以轻松地将本地端口的流量转发到指定的远程主机和端口，非常适合在开发和调试中建立临时的网络隧道。

核心功能:

多规则支持: 可以同时启动多个端口转发服务。

多线程: 每个连接都在独立的线程中处理，不会相互阻塞。

稳定运行: 作为一个阻塞服务运行，直到手动中断。

示例:
```
import mignonFramework as mg

# 定义转发规则
# 将本地 8080 端口的流量转发到远程服务器的 80 端口
# 将本地 3307 端口的流量转发到远程数据库的 3306 端口
port_mappings = [
{
'local_host': '127.0.0.1',
'local_port': 8080,
'remote_host': 'example.com',
'remote_port': 80
},
{
'local_host': '127.0.0.1',
'local_port': 3307,
'remote_host': 'remote-db.example.com',
'remote_port': 3306
}
]

print("启动端口转发服务... 按 Ctrl+C 停止。")
# 启动服务 (这是一个阻塞操作)
mg.portForwordRun(port_mappings)
```
5. MySQLManager
   一个对 pymysql 进行封装的数据库管理类，提供了更便捷和健壮的数据库操作方式。

核心功能:

简化连接: 通过 with 语句自动管理连接和关闭，避免资源泄漏。

高效批量操作: 核心方法 upsert_batch 能够以极高的性能执行“更新或插入”(ON DUPLICATE KEY UPDATE) 操作。

示例:
```
import mignonFramework as mg

# 数据库配置
db_config = {
'host': '127.0.0.1',
'user': 'root',
'password': 'password',
'database': 'my_db'
}

# 待写入的数据
data_to_insert = [
{'id': 1, 'name': 'Mignon', 'age': 30},
{'id': 2, 'name': 'Rex', 'age': 29} # age 将被更新
]

try:
with mg.MysqlManager(**db_config) as db:
if db.is_connected():
success = db.upsert_batch(data_to_insert, table_name='users')
if success:
print("数据批量写入/更新成功！")
except Exception as e:
print(f"数据库操作失败: {e}")
```
6. 其他实用工具
   Deduplicate (deduplicateFile, readLines2otherFiles)
   deduplicateFile: 高效地对大文件进行逐行去重，并显示进度条。

readLines2otherFiles: 从一个文件中读取指定行数到另一个文件。

示例:
```
import mignonFramework as mg

# 为大文件去重
mg.deduplicateFile('raw_data.txt', 'unique_data.txt')

# 从 a.txt 复制前 100 行到 b.txt
mg.readLines2otherFiles(100, 'a.txt', 'b.txt')
```
CountLinesInFolder (countFolderFileLines, countSingleFileLines)
countFolderFileLines: 统计一个文件夹内所有文件的总行数，支持按前缀、后缀或正则表达式过滤。

countSingleFileLines: 统计单个文件的行数。

示例:
```
import mignonFramework as mg

# 统计当前目录下所有 .py 文件的总行数
mg.countFolderFileLines('.', suffix='.py')
```
QueueRandomIterator (别名: QueueIter)
一个线程安全的迭代器，用于生成爬取队列或任务队列。

核心功能:

多种源: 支持从 list 或 range 创建。

随机化: 可设置随机种子以生成可复现的随机序列。

断点续传: 可从指定的索引开始。

示例:
```
import mignonFramework as mg

# 创建一个从 1 到 100 的随机爬取队列
task_queue = mg.QueueIter(range(1, 101), shuffle=True)

for page_num in task_queue:
print(f"正在处理页面: {page_num}")
# 可以在这里保存进度
# current_progress = task_queue.get_current_index()
```
Logger (别名: logInfo)
一个简单的日志记录函数。

示例:
```
import mignonFramework as mg

# 将日志记录到 ./logs/app.log
mg.logInfo("程序启动", log_path="./logs", log_name="app.log")
```