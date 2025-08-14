import re
from typing import List

def extract_column_names_from_ddl(ddl_string: str) -> List[str]:
    """
    从 SQL DDL 字符串中更健壮地提取所有字段名。
    此方法通过解析第一个 CREATE TABLE 语句的结构来工作。

    Args:
        ddl_string (str): 包含 SQL DDL 定义的字符串。

    Returns:
        List[str]: 包含所有提取到的字段名的列表。
    """
    # 1. 找到 CREATE TABLE 语句并定位其核心定义块的起止位置
    create_table_match = re.search(r"CREATE\s+TABLE\s+.*?\s*\(", ddl_string, re.IGNORECASE | re.DOTALL)
    if not create_table_match:
        return []

    content_start_index = create_table_match.end()

    # 2. 使用括号平衡法精确找到 CREATE TABLE 的结束括号
    balance = 1
    content_end_index = -1
    in_string_literal = False
    string_char = ''

    for i in range(content_start_index, len(ddl_string)):
        char = ddl_string[i]

        # 处理字符串字面量，避免其中的括号影响平衡
        if char in ("'", '"', '`') and not in_string_literal:
            in_string_literal = True
            string_char = char
        elif char == string_char and in_string_literal:
            # 检查转义字符
            if i > 0 and ddl_string[i-1] != '\\':
                in_string_literal = False

        if not in_string_literal:
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1

        if balance == 0:
            content_end_index = i
            break

    if content_end_index == -1:
        return []

    # 3. 提取核心定义内容，并按逗号分割
    table_definition = ddl_string[content_start_index:content_end_index]

    # 将换行符替换为空格，以便于处理跨行的定义
    table_definition = table_definition.replace('\n', ' ').replace('\r', ' ')

    # 按逗号分割成字段/约束定义块
    parts = table_definition.split(',')

    column_names = []
    constraint_keywords = {'primary key', 'unique', 'key', 'constraint', 'foreign key', 'check', 'index'}

    for part in parts:
        stripped_part = part.strip()
        if not stripped_part:
            continue

        # 4. 过滤掉表级约束定义
        # 检查这部分是否以一个约束关键字开头
        part_lower = stripped_part.lower()
        is_constraint = False
        for keyword in constraint_keywords:
            if part_lower.startswith(keyword):
                is_constraint = True
                break
        if is_constraint:
            continue

        # 5. 提取字段名
        # 字段名是定义中的第一个词，可能被反引号包围
        column_match = re.match(r"^\s*`?(\w+)`?", stripped_part)
        if column_match:
            column_name = column_match.group(1)
            column_names.append(column_name)

    return column_names

# --- 测试用例 ---
if __name__ == '__main__':
    ddl = """
          -- auto-generated definition
          create table patent_info_hzh
          (
              id                      int auto_increment
        primary key,
              title                   varchar(2048)                       null comment '专利标题',
              abstract_ab             text                                null comment '摘要',
              application_num         varchar(100)                        null comment '申请号',
              publication_number      varchar(100)                        null comment '公开（公告）号',
              publication_date        date                                null comment '公开（公告）日',
              application_date        date                                null comment '申请日',
              patent_type_cn_stat     varchar(50)                         null comment '专利类型 (中文统计)',
              patent_status           varchar(50)                         null comment '专利状态',
              applicants              json                                null comment '申请人列表',
              applicant_addr          varchar(2048)                       null comment '申请人地址',
              assignees               json                                null comment '专利权人（受让人）列表',
              assignees_addr          varchar(2048)                       null comment '专利权人（受让人）地址',
              inventors               json                                null comment '发明人列表',
              last_legal_status       varchar(50)                         null comment '最新法律状态',
              legal_date              date                                null comment '法律状态公告日',
              expired_date            date                                null comment '失效日',
              patent_duration         varchar(50)                         null comment '专利保护期',
              ipc_main                text                                null comment '主要IPC分类号',
              ipcTypeCN               text                                null comment 'IPC分类号对应的中文含义',
              ipc_mainclass_num       int                                 null comment 'IPC主分类号数量',
              application_country     varchar(200)                        null comment '申请国家',
              publication_country     varchar(200)                        null comment '公开国家',
              province_name           varchar(150)                        null comment '省份名称',
              city_name               varchar(50)                         null comment '城市名称',
              district_name           varchar(150)                        null comment '区/县名称',
              claims                  longtext                            null comment '权利要求书 (HTML格式)',
              description             longtext                            null comment '说明书 (HTML格式)',
              datasource_stat         varchar(50)                         null comment '数据来源地',
              kind_code               varchar(10)                         null comment '文献类型代码',
              data_type               varchar(20)                         null comment '数据类型',
              application_num_sear    varchar(100)                        null comment '用于检索的申请号',
              publication_number_sear varchar(100)                        null comment '用于检索的公开号',
              created_at              timestamp default CURRENT_TIMESTAMP not null comment '创建时间',
              updated_at              timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间'
          )
              comment '海知汇专利信息表';

          create index idx_type_and_id
              on patent_info_hzh (patent_type_cn_stat, id);

          create index idx_type_asc_id_desc
              on patent_info_hzh (patent_type_cn_stat, id);


          """

    extracted_columns = extract_column_names_from_ddl(ddl)
    print(f"成功提取了 {len(extracted_columns)} 个字段名:")
    print(extracted_columns)

    # 预期输出不应包含 'create', 'on', 'unique' 等关键字
    assert 'create' not in extracted_columns
    assert 'on' not in extracted_columns
    assert 'UNIQUE' not in extracted_columns
    assert 'id' in extracted_columns
    assert 'updated_at' in extracted_columns
    print("\n断言测试通过！")
