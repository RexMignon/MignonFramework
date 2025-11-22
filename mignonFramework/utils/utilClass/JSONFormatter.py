import os
import json


def JSONFormatter(data, path="./data.json"):
    with open(resolve_json_path(path), 'w', encoding='utf-8') as f:
        f.write(json.dumps(json.loads(data), ensure_ascii=False, indent=4))




def resolve_json_path(filename):
    if os.path.isabs(filename):
        return filename
    return os.path.join(os.getcwd(), filename)


