# -*- coding: utf8 -*-
# Date: 2019-12-23
# Usage:
#   Monitor zookeeper znode on zabbix.

# test

import json


# Config
_env = {}
MODULE = "zk"
# 使用 kazoo 模块连接 zk 时的超时时间，单位为秒。
ZK_CLIENT_TIMEOUT = 20
# EOF Config


def init(module):
    """由 ZBXApp 基类初始化的函数。
    """
    global app
    global conf
    app = _env["app"]
    conf = app.outcall_cfg_module(module)


def discovery():
    """
    """
    out_res = {"data": []}
    if "zks" in conf:
        zks = conf["zks"]
    else:
        raise ValueError("Not found the zks in conf.")
    tmp = {}
    for i in conf:
        if i.lower() == "zks":
            continue
        out_res["data"].append({"{#ZKS}": zks, "{#ZNODE}": i, "{#EXPECT}": conf[i]})
    out_res = json.dumps(out_res)
    return out_res


def info(zkaddrs, znode_path, decode="utf8"):
    """获取指定 znode 中的注册信息。

    Args:
        zkaddrs: 连接 zk 的连接串，可支持节点或集群访问。
        znode_path: 需获取 znode 的路径。
        decode: 对 znode 信息的编码方式。
    Raises:
        ValueError: 未发现对应的 znode。
    Returns:
        res <str>: znode 的注册信息。
    """
    from kazoo.client import KazooClient
    res = None
    zk = KazooClient(
            hosts = zkaddrs,
            timeout = ZK_CLIENT_TIMEOUT
        )
    zk.start()
    try:
        if not zk.exists(znode_path):
            logging.error("Not found the znode: {!s}.".format(znode_path))
            # raise ValueError("Not found the znode: {!s}.".format(znode_path))
            res = "<nil>"
        else:
            data, stat = zk.get(znode_path)
            res = data.decode(decode)
    finally:
        zk.stop()
        zk.close()
    return res