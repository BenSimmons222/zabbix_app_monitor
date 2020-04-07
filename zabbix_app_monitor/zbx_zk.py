# -*- coding: utf8 -*-
# Date: 2019-12-18
# Usage:
#   Monitor zookeeper on zabbix.


import json


# Config
MODULE = "zk"
# 使用 kazoo 模块连接 zk 时的超时时间，单位为秒。
ZK_CLIENT_TIMEOUT = 20
# 对于四字监控的返回结果使用不同的正则表达式获取预期结果
RE_KEYWORD = {
    "mntr": r"(\w+)\s*(\S+)\n",
    "conf": r"(\w+)\s*=\s*(\w+)\n",
    "ruok": r"^(.*)$",
}
# 四字监控中对返回 key 值的过滤
STATUS_OUTPUT = {
    "mntr":
        [
            # ZK 进程软件版本
            "zk_version", 
            # ZK 进程平均响应延时，单位为 ms
            "zk_avg_latency", 
            # ZK 进程最大响应延时，单位为 ms
            "zk_max_latency", 
            # ZK 进程最小响应延时，单位为 ms
            # "zk_min_latency", 
            # ZK 进程接受包数
            "zk_packets_received", 
            # ZK 进程发送包数
            "zk_packets_sent", 
            # ZK 进程活跃连接数
            "zk_num_alive_connections", 
            # ZK 进程堆积请求数
            "zk_outstanding_requests", 
            # ZK 进程主从状态
            "zk_server_state", 
            # ZK 进程 znode 数
            "zk_znode_count", 
            # ZK 进程 watch 数
            "zk_watch_count", 
            # ZK 临时节点数
            # "zk_ephemerals_count", 
            # ZK 进程近似数据总和大小，单位为 bytes
            "zk_approximate_data_size", 
            # ZK 进程打开的文件描述符数
            # "zk_open_file_descriptor_count", 
            # ZK 进程最大文件描述符数
            # "zk_max_file_descriptor_count", 
        ],
    "conf":
        [
            # ZK 数据文件目录
            "dataDir",
            "dataLogDir",
            # ZK 最大会话超时时间，单位为 ms
            "maxSessionTimeout",
            # ZK 最大连接数
            "maxClientCnxns",
            # ZK 标识 ID
            "serverId",
            # ZK 间隔单位时间
            "tickTime",
            # ZK 初始化时间
            "initLimit",
            # ZK 心跳时间间隔
            "syncLimit",
            # ZK 选举算法
            "electionAlg",
            # ZK 选举端口
            "electionPort",
            # ZK 法人端口
            "quorumPort",
            # 客户端端口
            "clientPort",
        ],
    "ruok":
        [
            "imok",
        ]
}
_env = {}
# EOF Config

def init(module):
    """由 ZBXApp 基类初始化的函数。
    """
    global app
    global conf
    app = _env["app"]
    conf = app.outcall_cfg_module(module)


def discovery():
    """自动发现 zk 来注册监控。

    Args:
        zkaddrs: zk 的长连接串，格式为 "IP1:port1,IP2:port2,IP3:port3"
    Returns:
        {
            "data": [
                {"{#CLUSTER}": "cluster", "{#ZK}": "zkaddr"}
            ]
        }
    """
    out_res = {"data": []}
    tmp = {}
    if "cluster" in conf:
        tmp["{#CLUSTER}"] = conf["cluster"]
    if "zk" in conf:
        tmp["{#ZK}"] = conf["zk"]
    out_res["data"].append(tmp)
    out_res = json.dumps(out_res)
    return out_res


def status(zkaddr, keyword):
    """获取对应 zk 节点的状态，由四字监控关键词来决定所监控要素。

    Args:
        zkaddr: 单个 zk 的连接地址，格式为 IP:Port。
        keyword: 四字监控的关键词。
    Returns:
        res <json>:
        {
            item1: value1,
            item2: value2,
            # ...
        }
    """
    import socket, re
    from contextlib import closing

    res = ""
    addr = (zkaddr.split(':')[0].strip(), int(zkaddr.split(':')[-1].strip()))
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(10)
        s.connect(addr)
        s.send(keyword.encode("utf8"))
        data_zk_status = s.recv(4096)
    data_zk_status = data_zk_status.decode("utf8")
    re_res = re.findall(RE_KEYWORD[keyword], data_zk_status)
    if keyword == "ruok": 
        tmp = {"ruok": i for i in re_res if "ruok" in STATUS_OUTPUT}
    else:
        tmp = {i[0]: i[1] for i in re_res if i[0] in STATUS_OUTPUT[keyword]}
    res = json.dumps(tmp)
    return res