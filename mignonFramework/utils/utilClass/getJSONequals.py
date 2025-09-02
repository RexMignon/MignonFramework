from mignonFramework.utils.execJS.execJSTo import execJS
from mignonFramework.utils.Queues import QueueIter
import os


@execJS(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'starterUtil\static', "js\JSONcrypto.jsx"))
def jsondec(json1, json2):
    return []


def jsonContrast(json1, json2):
    que = QueueIter(shuffle=False)
    printList = jsondec(json1, json2)
    que.pages = range(0, len(printList))
    while que.hasNext():
        index = next(que)
        print(printList[index])
    return printList


