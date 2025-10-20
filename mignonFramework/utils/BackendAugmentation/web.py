import json
from typing import final, Any

from quart import Response
from http import HTTPStatus


class Result:
    def __init__(self):
        pass

    @final
    @staticmethod
    def success(data: Any = None):
        return json.dumps({"status": True, "data": data}, ensure_ascii=False), HTTPStatus.OK

    @final
    @staticmethod
    def fail(data: Any = None, code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR):
        return json.dumps({"status": False, "data": data}, ensure_ascii=False), code
