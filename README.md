# MignonFramework 模块文档

本文档为 MignonFramework 中的每一个模块提供了独立的、详细的说明。(基于0.5.2.4版本)
```
# 下载并使用: 
pip install mignonFramework
```
## Logger 模块

### 简单介绍

`Logger` 是一个健壮的、高度自动化的日志框架，专为提升开发体验和项目健壮性而设计。它不仅能记录日志到文件，还能**自动捕获**所有标准输出 (`print`)，并为函数提供开箱即用的异常捕获和日志记录能力。

### 原理

`Logger` 的核心原理是 **AOP (面向切面编程)** 和 **流重定向**。

1. **自动 `stdout` 拦截**: 当 `Logger` 被启用时，它会用一个自定义的流对象(HOOK)替换掉 Python 内置的 `sys.stdout`。这意味着任何地方调用 `print()`，其输出内容都会被这个自定义对象拦截，然后被格式化成结构化的日志条目，并同时输出到控制台和日志文件。
2. **AOP 装饰器**: `@log` 装饰器利用 Python 的装饰器特性，将异常捕获和日志记录这段“横切逻辑”动态地“织入”到业务函数中，而无需修改业务函数本身的源代码。
3. **线程安全**: 所有文件写入操作都使用了 `threading.RLock` 来确保在多线程环境下的数据一致性。
4. **日志轮转**: 当日志文件达到预设的最大行数时，会自动创建新的日志文件（如 `xxx_1.log`, `xxx_2.log`），防止单个文件过大。

### 使用方法

#### 1. 启用全局自动日志

这是最简单的用法。在你的项目入口处，实例化 `Logger` 并将 `enabled` 设置为 `True`。

```
from mignonFramework import Logger

# 启用自动日志，所有 print 语句都将被记录
log = Logger(True)

print("这是一条普通信息，它会被自动记录为 INFO 级别的日志。")
```

#### 2. 使用 `@log` 装饰器进行异常捕获

对于关键函数，使用 `@log` 装饰器可以实现自动的异常捕获和详细的 `traceback` 日志记录。

```
from mignonFramework import Logger

log = Logger(True)

@log
def calculate(a, b):
    print(f"正在计算 {a} / {b}")
    result = a / b
    return result

# 发生异常，@log 会自动捕获并记录详细错误，然后重新抛出
try:
    calculate(10, 0)
except ZeroDivisionError:
    print("捕获到预期的异常。")
```

### 参数

- `__init__(self, enabled=False, log_path='./resources/log', name_template='{date}.log')`
  - **`enabled`** (`bool`, 可选): 是否启用全局 `stdout` 自动拦截。默认为 `False`。
  - **`log_path`** (`str`, 可选): 日志文件存放的目录路径。默认为 `'./resources/log'`。
  - **`name_template`** (`str`, 可选): 日志文件的命名模板，`{date}` 会被替换为当前日期。默认为 `'{date}.log'`。

## ConfigReader 模块

### 简单介绍

`ConfigReader` 是一个强大且优雅的配置管理引擎，它将 Java Spring 框架中**依赖注入 (DI)** 和**控制反转 (IoC)** 的思想带到了 Python 世界。它不仅能读写 `.ini` 配置文件，还能将配置类作为单例进行管理，并通过 `@inject` 装饰器实现配置的**自动注入和生成**。

### 原理

`ConfigReader` 的核心是 **DI 容器**、**装饰器** 和 **Python 描述符**。

1. **DI 容器**: `ConfigManager` 实例扮演了 Spring 中 `ApplicationContext` 的角色。它负责创建、管理和提供配置类的单例实例 (`getInstance`)。
2. **`@inject` 装饰器**: 这是一个装饰器工厂，它将一个 `ConfigManager` 实例与一个配置类进行绑定。
3. **自动生成 `.ini`**: 当一个被 `@inject` 装饰的类的属性**首次被访问**时，框架会自动从 `.ini` 文件中读取值。如果文件或值不存在，它会根据你在类中定义的**默认值**，**自动将配置项写入 `.ini` 文件**，然后再返回值。

这个流程实现了“定义即配置”和“首次运行自动生成”的顺滑体验，完美避免了在代码中硬编码。

### 使用方法

#### 1. 定义配置类并注入

创建一个 Python 类来定义你需要的配置项。**你只需要定义，不需要实例化。**

```
# a_config.py
from mignonFramework import ConfigManager, inject

# 1. 创建一个 ConfigManager 实例，指向你的配置文件和节名
db_config_manager = ConfigManager(filename='./resources/db.ini', section='database')

# 2. 定义你的配置类，并使用 @inject 装饰
@inject(db_config_manager)
class DatabaseConfig:
    # 3. 定义配置字段，提供类型注解和默认值
    # 这些默认值会在首次运行时自动写入 db.ini 文件
    host: str = '127.0.0.1'
    port: int = 3306
    user: str = 'root'
    password: str  # 没有默认值的字段，会自动写入空值，等待用户填写
    db_name: str = 'my_app_db'

# 4. 通过 getInstance 获取配置类的单例
# 首次运行时，如果 db.ini 不存在或不完整，它会被自动创建和填充
db_cfg = db_config_manager.getInstance(DatabaseConfig)
```

#### 2. 在项目中使用配置

在项目的其他地方，直接导入配置实例即可使用。

```
# main.py
from a_config import db_cfg

# 访问属性时，会自动从 db.ini 文件读取值
print(f"正在连接到数据库: {db_cfg.host}:{db_cfg.port}")

# 修改配置并自动写回文件
db_cfg.port = 3307 # 赋值操作会自动更新 db.ini 文件
```

### 参数

- `ConfigManager(filename='./resources/config/config.ini', section='config')`
  - **`filename`** (`str`, 可选): 配置文件的路径。
  - **`section`** (`str`, 可选): 配置文件中的节 (section) 名称。
- `inject(manager)`
  - **`manager`** (`ConfigManager`): 一个 `ConfigManager` 的实例。

## MicroserviceByNodeJS 模块

### 简单介绍

`MicroserviceByNodeJS` 是 `MignonFramework` 的**创新核心**，它提供了一个高性能、持久化的微服务解决方案，专门用于解决 Python 调用复杂、特别是**异步** JavaScript 的难题。它通过 C/S (客户端/服务器) 架构，将 JS 的执行放在了其原生的 Node.js 环境中，实现了极致的性能和稳定性。

### 原理

它的原理是**将 JS 的执行环境与 Python 的调用逻辑彻底分离**。

1. **服务器端**:
   - 当你创建一个 `MicroServiceByNodeJS` 实例（非 `client_only` 模式）时，它会使用 Python 的 `subprocess` 模块启动一个**常驻的 Node.js 服务器进程** (`invoker.js`)。
   - 这个 `invoker.js` 是一个基于 Express.js 的 打包好的 HTTP 服务器。在启动时，它会**自动扫描**指定的 JS 目录 (`scan_dir`) 并**一次性将所有 JS 文件作为模块加载到内存中**。
2. **客户端**:
   - 它的 `invoke` 方法或 `@evalJS` 装饰器会将函数调用转换成一个**轻量级的 HTTP POST 请求**，发送给 Node.js 服务器。
   - Node.js 服务器接收到请求后，在内存中找到对应的、已经编译好的模块和函数，执行它（可以完美处理 `async/await`），然后将最终结果通过 HTTP 响应返回给 Python 客户端。

这个模式通过“一次加载，多次服务”的思想，避免了 `execJS` 每次调用都需要的进程启动、文件I/O和代码编译的巨大开销。

### 使用方法

#### 1. 启动 JS 微服务 (文件1)

创建一个独立的 Python 文件来启动并持久化运行 JS 微服务。

```
# run_js_service.py
from mignonFramework import MicroServiceByNodeJS

# 默认会扫描 ./resources/js 目录下的所有js文件
# 并将它们暴露成API
service_runner = MicroServiceByNodeJS()

print("JavaScript microservice is running...")
# 作为一个独立的服务持久化运行
service_runner.startAsMicro()
```

#### 2. 在其他项目中调用 (文件2)

在你的主应用或爬虫脚本中，以 `client_only` 模式连接并调用服务。

```
# main_scraper.py
from mignonFramework import MicroServiceByNodeJS, ConfigManager, inject

# 使用 ConfigManager 来管理 JS 文件名，避免硬编码
config = ConfigManager()
@inject(config)
class MyConfig:
    js_file_name: str = 'h5st_encrypt' # 对应 h5st_encrypt.js
data = config.getInstance(MyConfig)


# 1. 以 client_only=True 模式连接到正在运行的服务
service_client = MicroServiceByNodeJS(client_only=True)

# 2. 使用 @service.evalJS 装饰器，参数从配置中动态读取
@service_client.evalJS(data.js_file_name)
def get_h5st(params):
    return ""

# 3. 像调用普通 Python 函数一样调用它
if __name__ == "__main__":
    encrypted_data = get_h5st({"key": "value"})
    print(f"从 JS 微服务获取到的加密结果: {encrypted_data}")
```



```
# 当然, 也可以合并启用
# main_scraper.py
from mignonFramework import MicroServiceByNodeJS, ConfigManager, inject

# 使用 ConfigManager 来管理 JS 文件名，避免硬编码
config = ConfigManager()
@inject(config)
class MyConfig:
    js_file_name: str = 'h5st_encrypt' # 对应 h5st_encrypt.js
data = config.getInstance(MyConfig)


# 1. 以 client_only=True 模式连接到正在运行的服务
service_client = MicroServiceByNodeJS()

# 2. 使用 @service.evalJS 装饰器，参数从配置中动态读取
@service_client.evalJS(data.js_file_name)
def get_h5st(params):
    return ""

# 3. 像调用普通 Python 函数一样调用它
if __name__ == "__main__":
    encrypted_data = get_h5st({"key": "value"})
    print(f"从 JS 微服务获取到的加密结果: {encrypted_data}")
```



### 参数

- `__init__(self, client_only=False, port=3000, url_base="127.0.0.1", scan_dir="./resources/js", ...)`
  - **`client_only`** (`bool`, 可选): 是否只作为客户端连接一个已存在的服务。默认为 `False`。
  - **`port`** (`int`, 可选): Node.js 服务监听的端口。
  - **`url_base`** (`str`, 可选): Node.js 服务的 IP 地址或域名。
  - **`scan_dir`** (`str`, 可选): (仅服务端模式) Node.js 服务启动时要扫描的 JS 模块目录。

## Queues 模块(QueueIter)

### 简单介绍

`QueueIter` 是一个灵活、可重用、支持装饰器配置和随机种子的爬取队列生成器。它非常适合用于爬虫或任何需要分批处理任务的场景，并提供了强大的流程控制和任务编排能力。

### 原理

`QueueIter` 本质上是一个**线程安全的、可动态配置的迭代器**。

1. **动态配置**: 队列的核心属性（如 `pages` 任务列表, `current_index` 当前进度）都设计为 Python `property`，允许在运行时安全地修改。
2. **任务终结与编排 (`@target`)**: `@target` 装饰器与 `ConfigManager` 联动。它允许你注册一个“终结任务”，当队列迭代完成时，会自动执行这个任务，例如修改某个配置类的属性。这是一种非常优雅的**跨对象状态管理**和任务编排方式。
3. 同时QueueIter只要seed固定, 生成的顺序虽然打乱, 但每次生成的顺序一定相同, 因此, 在断点续爬的过程中需要通过current_index来控制

### 使用方法

#### 1. 基本用法

```
from mignonFramework import QueueIter

# 创建一个从 1 到 100 的任务队列，并打乱顺序
task_queue = QueueIter(pages=range(1, 101), shuffle=True)

while task_queue.hasNext():
    page_number = next(task_queue)
    print(f"正在处理页面: {page_number}")
```

#### 2. 使用 `@target` 进行任务编排

当一个队列跑完后，自动修改另一个配置。

```
from mignonFramework import QueueIter, target, ConfigManager, inject


config = ConfigManager(section='SpiderState')
user_queue = QueueIter(pages=range(1, 51), config_manager=config)




# 使用 @target 装饰器，定义一个终结任务
# 当 user_queue 跑完后，会自动将 SpiderState 的 current_task 属性值改为 'products'
@target(user_queue, 'current_task', 'products')
@inject(config)
class SpiderState:
    current_task: str = 'users'
state = config.getInstance(SpiderState)





while user_queue.hasNext():
    user_id = next(user_queue)
    print(f"处理用户 {user_id}, 当前任务: {state.current_task}")

# 循环结束后
print(f"用户队列处理完毕, 下一个任务是: {state.current_task}") # 输出: products
```

### 参数

- `__init__(self, config_manager=None, shuffle=True, callback=None, pages=range(0, 1), ...)`
  - **`config_manager`** (`ConfigManager`, 可选): 一个 `ConfigManager` 实例，在使用 `@target` 功能时**必需**。
  - **`shuffle`** (`bool`, 可选): 是否在初始化时打乱 `pages` 列表的顺序。
  - **`pages`** (`list` 或 `range`, 可选): 包含所有任务的列表或 `range` 对象。
  - **`seed`** (`int`, 可选): 用于随机数生成的种子，以确保每次打乱的顺序一致。

## GenericProcessor 模块 (InsertQuick)

### 简单介绍

`GenericFileProcessor` (别名 `InsertQuick`) 是框架的**ETL心脏**。它是一个高度可定制的、通用的逐行JSON文件处理器，用于将文件内容批量写入指定目标（如数据库）。它支持**零配置启动**、交互式的`Eazy Mode`和强大的行级错误处理与恢复机制。

### 原理

`GenericProcessor` 的核心是一个**可定制的数据处理流水线 (Pipeline)**。

1. **写入器抽象 (`BaseWriter`)**: 它不关心数据最终写到哪里。它依赖于一个实现了 `BaseWriter` 接口的 `writer` 对象（如 `MysqlManager`），这使得它的输出端是完全可插拔的。
2. **强大的错误恢复**: 当 `upsert_batch` 批量写入失败时，它不会直接崩溃，而是**自动降级为逐行恢复模式**。在逐行模式下，它会精确定位到出错的行和数据，并提供交互式选项或全自动跳过。
3. **零配置与自动生成INI**: 如果在初始化时不提供 `writer` 或 `table_name`，它会自动查找 `generic.ini` 配置文件。如果文件或配置项不存在，它会**自动生成一个带注释的模板文件**，引导用户填写数据库连接信息和表名。

### 使用方法

#### 1. 零配置启动 (推荐)

你不需要在代码里写任何数据库连接信息。

```
# main.py
from mignonFramework import InsertQuick

# 1. 直接实例化，不传入任何参数
# 它会自动寻找 ./resources/config/generic.ini
processor = InsertQuick()

# 2. 运行
# 首次运行时，如果 generic.ini 不存在，它会被自动创建
# 你只需要去文件里填写好数据库信息和表名，然后再次运行即可
processor.run()
```

#### 2. 高级用法：自定义数据转换

```
from mignonFramework import InsertQuick, Rename

# 定义一个修改器函数
def modify_user_data(data_dict):
    return {
        'user_id': Rename('id'), # 将 'user_id' 重命名为 'id'
        'fullName': (data_dict.get('firstName', '') + ' ' + data_dict.get('lastName', ''))
    }

# 同样使用零配置方式初始化
processor = InsertQuick(
    modifier_function=modify_user_data,
    exclude_keys=['firstName', 'lastName']
)
processor.run()
```

#### 3. EAZY_MODE(极为推荐)

```
# 使用方法
from mignonFramework import InsertQuick


InsertQuick(eazy=True).run("./文件路径")
# 即可启动内部Flask, 随机抽取行做解析, 粘贴DDL即可一键生成inclue_key等代码, 极为迅速
```



### 参数

- `__init__(self, writer=None, table_name=None, modifier_function=None, ...)`
  - **`writer`** (`BaseWriter`, 可选): 写入器实例。**推荐不传**，让框架自动从配置文件加载。
  - **`table_name`** (`str`, 可选): 目标表名。**推荐不传**，让框架自动从配置文件加载。
  - **`modifier_function`** (`Callable`, 可选): 一个接收原始数据字典、返回修改指令字典的函数。
  - **`filter_function`** (`Callable`, 可选): 一个接收原始数据字典和行号、返回 `bool` 值的函数。返回 `False` 则跳过该行。
  - **`exclude_keys`** (`list`, 可选): 需要排除的**原始键名**列表。
  - **`include_keys`** (`list`, 可选): “白名单”，只有这些**目标键名(snake_case)**才会被保留。
  - **`eazy`** (`bool`, 可选): 是否启动 。
  - **`auto_skip_error`** (`bool`, 可选): 在逐行恢复模式中，是否自动跳过错误行。

## MySQLManager 模块

### 简单介绍

`MySQLManager` 是一个线程安全、带自动重连和高效 `UPSERT` 功能的MySQL数据库管理器。它是 `BaseWriter` 接口的官方实现，专门设计用来与 `GenericProcessor` 无缝协作。

### 原理

1. **线程安全**: 使用 `threading.local()` 为每个线程创建独立的数据库连接，避免了多线程操作同个连接导致的常见问题。
2. **自动重连**: 在执行操作前会检查连接是否断开，如果断开则会自动尝试重连，增加了长时间运行任务的稳定性。
3. **高效的 `UPSERT`**: 它能智能地构建 `INSERT ... ON DUPLICATE KEY UPDATE` 语句，实现了高效的数据写入和更新操作。

### 使用方法

`MySQLManager` 主要被设计为在 `GenericProcessor` 内部**通过配置文件自动初始化**，用户通常不需要手动实例化它。但如果需要独立使用，方法如下：

```
from mignonFramework import MysqlManager

# 不推荐在代码中硬编码，这里仅作演示
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'my_db',
    'port': 3306
}

db_manager = MysqlManager(**db_config)

if db_manager.is_connected():
    users_to_insert = [
        {'id': 1, 'name': 'Alice', 'age': 30},
        {'id': 2, 'name': 'Bob', 'age': 25}
    ]
    # 批量写入
    db_manager.upsert_batch(users_to_insert, 'users')
    
    # 单条写入
    db_manager.upsert_single({'id': 3, 'name': 'Charlie', 'age': 35}, 'users')
    
    db_manager.close()
```

### 参数

- `__init__(self, host, user, password, database, port=3306, **kwargs)`
  - **`host`**, **`user`**, **`password`**, **`database`**, **`port`**: 标准的MySQL连接参数。

## ProcessFile 模块

### 简单介绍

`ProcessFile` 是一个开箱即用的文件批处理引擎，内置了基于SQLite或文件移动的状态管理，实现了可靠的**“断点续传”**功能。它的任务是持续不断地监控一个目录，将文件进行解析、转换，并追加写入到大型结果文件中。

### 原理

1. **配置驱动**: 整个流程完全由一个独立的 `.ini` 配置文件驱动。
2. **自动生成INI**: 如果配置文件不存在，它会自动生成一个带详细注释的模板文件，引导用户填写输入/输出路径等信息。
3. **双模式状态管理**:
   - **config 模式**: 使用 `SQLiteStateTracker`，通过数据库来记录每个文件的处理状态（成功、失败），适合需要持久化和可查询记录的场景, 缺点是如果自己想记录的话还需要查。
   - **move 模式**: 使用 `MoveStateTracker`，通过物理移动文件到 `finish` 或 `exception` 目录来标记状态，简单直观, 缺点是慢,即时有异步的支持IO操作也很巨大。
4. **异步核心**: 文件的读写操作使用了 `aiofiles` 和 `asyncio`，在处理大量小文件时能提供更好的 I/O 性能。

### 使用方法

你**几乎不需要写任何Python代码**来使用它。

1. **创建启动脚本**:

   ```
   # run_process.py
   from mignonFramework import processRun
   
   # 指定你的配置文件路径，然后运行
   processRun(config_path='./resources/config/processFile.ini')
   ```

2. **运行与配置**:

   - 第一次运行 `python run_process.py`。
   - 程序会提示配置缺失，并自动在 `./resources/config/` 目录下创建一个 `processFile.ini` 文件。
   - 打开 `processFile.ini`，根据里面的注释填写你的输入目录 (`input_dir`) 和输出目录 (`output_dir`)。
   - 再次运行 `python run_process.py`，处理流程就会自动开始。

### 参数

- `run(config_path: str = './resources/config/processFile.ini')`
  - **`config_path`** (`str`, 可选): 指向该模块专属配置文件的路径。

## execJSTo 模块

### 简单介绍

`execJSTo` 提供了一个极其优雅的装饰器 `@execJS`，通过智能的参数签名“翻译”，实现了Python函数到**同步**JS函数的无缝代理调用。它是处理**同步、无I/O、纯计算型**JS逻辑的最轻量、最便捷的方案。

### 原理

`@execJS` 装饰器在 `PyExecJS` 库的基础上，构建了一个智能的、声明式的调用层。本质还是AOP.

1. **参数签名“翻译”**: 它利用 Python 的 `inspect` 模块去分析你装饰的 Python 函数的签名。这使得它可以正确处理**位置参数**和**关键字参数**，并自动按照 JS 函数期望的顺序来传递。
2. **声明式编程**: 它将一个命令式的调用（`ctx.call(...)`）转换成了一个声明式的注解（`@execJS(...)`）。开发者只需要“声明”这个 Python 函数对应哪个 JS 文件，剩下的所有细节（文件读取、编译、参数绑定、执行）都由装饰器自动完成。

### 使用方法

```
from mignonFramework import execJS

# 假设有一个 crypto.js 文件:
# function encrypt(data, key) { ... return encrypted_data; }

# 1. 使用 @execJS 装饰一个函数，参数为JS文件路径
@execJS('./resources/js/crypto.js')
def encrypt(data, key):
    # 2. Python 函数体不会被执行
    # 它的签名 (参数) 会被用来调用 JS 函数
    pass

# 3. 像调用普通Python函数一样调用它
# 关键字参数和位置参数都能被正确处理
encrypted_text = encrypt(data="hello", key="secret")
print(encrypted_text)

# 也可以指定JS函数名
@execJS('./resources/js/crypto.js', js_function_name='decrypt_data')
def decrypt(text):
    pass
```

### 参数

- `execJS(js_file_path: str, js_function_name: str = None)`
  - **`js_file_path`** (`str`): 目标 JavaScript 文件的路径。
  - **`js_function_name`** (`str`, 可选): 要调用的 JavaScript 函数名。如果为 `None`，则默认使用被装饰的 Python 函数的名称。

## getJSONequals 模块

### 简单介绍

`getJSONequals` (别名 `jsonContrast`) 是一个强大的JSON对比工具

### 原理

1. 对于不标准的JSON也能够处理, 以及会将Object转为String做比较

### 使用方法

在Android逆向和Web逆向中, 难免会遇到很难识别出不同的JSON数据

```
from mignonFramework import jsonContrast


test1 = {
    "a":"b",
    "c":"d",
    "e":"f"
}


test2 = {
    "a":"b",
    "c":"d",
    "e":"f"
}


jsonContrast(test2,test1)

# 此时自动打印
```

### 参数

- `jsonContrast(json1, json2)`

  - **`json1`** (`dict` ): 原始的JSON数据1。

  - **`json2`* (`dict` ): 原始的JSON数据2。

    

## 辅助工具模块

### mignonFramework_starter 模块

- **简单介绍**: 框架的可视化Web UI启动器。它通过 `start()` 函数启动一个本地 Flask Web 服务器，集成了代码生成、cURL转换 等多种高效开发工具，是 MignonFramework “开发者友好”理念的最终体现。

- **使用方法**:

  ```
  from mignonFramework import start
  
  # 启动 Web UI，默认监听 5001 端口
  start()
  ```

### Curl2Reuqest 模块

- **简单介绍**: 一个实用的开发者工具，能将从浏览器开发者工具复制的cURL命令字符串自动转换为等效的、格式化好的Python `requests`代码。

- **使用方法**:

  ```
  from mignonFramework import Curl2Reuqest
  
  curl_command = 'curl "http://example.com" -H "User-Agent: my-agent"'
  converter = Curl2Reuqest(curl_command)
  python_code = converter.get_requests_code()
  print(python_code)
  ```

### Deduplicate 模块

- **简单介绍**: 提供了内存高效的大文件去重功能，以及复制、替换指定行的原子操作，是 `GenericProcessor` 的完美数据调试搭档。

- **使用方法**:

  ```
  from mignonFramework import deduplicateFile, copyLineByNumber
  
  # 对大文件进行去重
  deduplicateFile('./data/large_log.txt', mode='chunk')
  
  # 复制文件的第 123 行到新文件
  copyLineByNumber('./data/source.txt', 123, './data/line_123.txt')
  ```

### SqlDDL2List 模块

- **简单介绍**: 一个精准的SQL DDL解析器，能从 `CREATE TABLE` 语句中提取表结构信息（字段名、类型、约束等），是 `GenericProcessor` Eazy Mode 智能化的重要支撑。

- **使用方法**:

  ```
  from mignonFramework import extractDDL2List
  
  ddl_string = """
  CREATE TABLE `users` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(255) DEFAULT NULL,
    PRIMARY KEY (`id`)
  );
  """
  columns = extractDDL2List(ddl_string)
  # columns -> [('id', 'int(11)', 'NOT NULL', None), ('name', 'varchar(255)', '', 'NULL'), ...]
  print(columns)
  ```

### PortForwarding 模块

- **简单介绍**: 一个简洁可靠的TCP端口转发工具，用于网络抓包和流量分析。

- **使用方法**:

  ```
  from mignonFramework import portForwordRun
  
  # 将本地 8080 端口的流量转发到 example.com 的 80 端口
  services = [
      ('0.0.0.0', 8080, 'example.com', 80)
  ]
  portForwordRun(services)
  ```

### CountLinesInFolder 模块

- **简单介绍**: 提供了一系列高效的函数，用于统计单个文件、多个文件或整个目录（支持递归和正则匹配）的代码行数。

- **使用方法**:

  ```
  from mignonFramework import countSingleFileLines, countDirectoryFileLines
  
  # 统计单个文件行数
  lines = countSingleFileLines('my_script.py')
  print(f"文件行数: {lines}")
  
  # 统计整个项目（.py文件）的总行数
  total_lines = countDirectoryFileLines('.', file_regex=r'.*\.py$')
  print(f"项目总行数: {total_lines}")
  ```