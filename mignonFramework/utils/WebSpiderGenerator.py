"""
思路:
1.先通过Curl2Request生成普通的request方法
会根据是否为json调整
要求需修改Curl方法,分别对post和get有特殊支持
2. 通过Queue自动回调.
背景: 每次调用Queue的hasNext函数后都会赋值, 为1 或者为0
生成整个只需编写部分具体逻辑代码 的一站式的, 全依赖几乎所有mignonFramework的生成爬虫, 与GenericProcessor类似
包括自动Ioc和Dl
"""