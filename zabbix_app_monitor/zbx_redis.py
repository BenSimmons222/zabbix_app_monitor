# -*- coding: utf8 -*-
# Author: AcidGo
# Date: 2019-12-15
# Usage:
#   Monitor redis on zabbix.


import json
import redis


# Config
MODULE = "redis"
_env = {}

STATUS_OUTPUT = {
    "Server": [
        # Redis 的版本
        "redis_version",
        # 运行模式
        "redis_mode",
        # 进程 PID
        "process_id",
        # Redis 的随机标识符
        #"run_id",
        # Redis 端口
        "tcp_port",
        # Redis 运行时长的秒数
        "uptime_in_seconds",
    ],
    "Clients": [
        # 已连接客户端的数量（不包括通过从属服务器连接的客户端）
        "connected_clients",
        # 正在等待阻塞命令（BLPOP、BRPOP、BRPOPLPUSH）的客户端的数量
        "blocked_clients",
    ],
    "Memory": [
        # 由 Redis 分配的内存的总量，字节数
        "used_memory",
        # Redis 进程从 OS 角度分配的物理内存
        "used_memory_rss",
        # Redis 使用内存的峰值，字节数
        "used_memory_peak",
        # Lua 引擎使用的内存总量
        "used_memory_lua",
        # Redis 内存碎片率
        "mem_fragmentation_ratio",
    ],
    "Persistence": [
        # 标志位，是否在载入数据文件，0代表没有，1 代表正在载入
        #"loading",
        # 从最近一次 dump 快照后，未被 dump 的变更次数
        "rdb_changes_since_last_save",
        # 标志位，记录当前是否在创建 RDB 快照
        #"rdb_bgsave_in_progress",
        # 最近一次创建 RDB 快照文件的 Unix 时间戳
        "rdb_last_save_time",
        # 标志位，记录最近一次 bgsave 操作是否创建成功
        "rdb_last_bgsave_status",
        # 最近一次 bgsave 操作耗时秒数
        "rdb_last_bgsave_time_sec",
        # appenonly 是否开启，appendonly 为 yes 则为 1,no 则为 0
        "aof_enabled",
        # AOF 重写是否被 RDB save 操作阻塞等待
        "aof_rewrite_scheduled",
        # 最近一次 AOF 重写操作耗时
        "aof_last_rewrite_time_sec",
        # 当前 AOF 重写持续的耗时
        #"aof_current_rewrite_time_sec",
        # 最近一次 AOF 重写操作是否成功
        "aof_last_bgrewrite_status",
        # 最近一次 AOF 写入操作是否成功
        "aof_last_write_status",
        # AOF 文件目前的大小，字节
         "aof_current_size",
        # 被延迟的 fsync 调用数量
        #"aof_delayed_fsync",
    ],
    "Stats": [
        # Redis 已接受的连接请求数量
        "total_connections_received",
        # Redis 已执行的命令数量
        "total_commands_processed",
        # Redis 每秒钟执行的命令数量
        "instantaneous_ops_per_sec",
        # Redis 每秒网络输入的字节数
        "total_net_input_bytes",
        # Redis 每秒网络输出的字节数
        "total_net_output_bytes",
        # 因连接数达到 maxclients 上限后，被拒绝的连接个数
        "rejected_connections",
        # 累计 Master full sync 的次数
        # 如果值比较大，说明常常出现全量复制，就得分析原因，或调整 repl-backlog-size
        "sync_full",
        # Redis 累计剔除（超过maxmemory后）的key数量
        "evicted_keys",
        # 查找键命中的次数
        "keyspace_hits",
        # 查找键未命中的次数
        "keyspace_misses",
        # 目前被订阅的频道数量
        #"pubsub_channels",
        # 目前被订阅的模式数量
        #"pubsub_patterns",
        # 最近一次 fork 操作的耗时的微秒数
        # BGREWRITEAOF,BGSAVE,SYNC等都会触发fork,当并发场景fork耗时过长对服务影响较大
        "latest_fork_usec",
    ],
    "Replication": [
        # 当前 Redis 的主从状态
        "role",
        # 有几个 slave
        "connected_slaves",
        # 主从复制连接状态，slave端可查看它与master之间同步状态，当复制断开后表示down,正常情况下是up
        "master_link_status",
        # 从库是否设置只读，“1”表示设置只读，“0”表示没有设置可读
        "slave_read_only",
    ],
    "Keyspace": [
        "db{!s}".format(i) for i in range(20)
    ],
	"Sentinel":[
		"master{!s}".format(i) for i in range(20)
	]
}

CLUSTER_STATUS_OUTPUT = {
    # ok 状态表示节点可以接收查询请求，fail 表示至少有一个 slot 没有分配或者在 error 状态
    "cluster_state",
    # 已经分配到集群节点的slot。16384个slot全部被分配到集群节点是集群节点正常运行的必要条件
    "cluster_slots_assigned",
    # slot状态是FAIL的数量
    # 如果不是0，那么集群节点将无法提供服务，
    # 除非cluster-require-full-coverage被设置为no
    "cluster_slots_fail",
    # 集群中的节点数量
    "cluster_known_nodes",
    # 至少包含一个slot且能够提供服务的master节点数量
    "cluster_size",
}

SENTINEL_STATUS_OUTPUT = {
    # sentienl监控集群的名字，可以同时监控多个集群
    "name",
    # 集群的状态，ok表示正常，odown表示客观下线
    "status",
    # 集群的主节点信息
    "address",
    # 集群中从节点的数量
    "slaves",
    # sentinels集群的哨兵数量
    "sentinels",
}

CONFIG_OUTPU = {
    # 配置的 Redis 最大内存限制，单位为 bytes
    "maxmemory",
    # 当 Redis 达到最大内存后的处理策略
    "maxmemory-policy",
    # 配置客户端连接超时的超时时间，单位为秒
    # 当客户端在这段时间内没有发出任何指令，则关闭连接
    "timeout",
    # 配置同一时间 Redis 上接受的最大客户端连接数
    "maxclients",
}
# EOF Config


def init(module):
    """由 ZBXApp 基类初始化的函数。
    """
    global app
    global conf
    app = _env["app"]
    conf = app.outcall_cfg_module(module)


def _parse_local_redis(confpath):
    """
    """
    import os
    if not os.path.isfile(confpath) or not os.access(confpath, os.R_OK):
        raise ValueError("The redis confpath is not exists or be read: {!s}".format(confpath))
    bind = "127.0.0.1"
    port = "6379"
    requirepass = None
    with open(confpath, "r") as f:
        for line in f:
            if not line.strip().startswith("#") and line.split("=", 1)[0].strip() in ("bind", "requirepass", "port"):
                tmp_k = line.split("=", 1)[0].strip()
                tmp_v = line.split("=", 1)[1].strip()
                if tmp_k == "bind":
                    bind = tmp_v
                elif tmp_k == "requirepass":
                    requirepass = tmp_v
                elif tmp_k == "port":
                    port = tmp_v
    return bind + ":" + port, requirepass


def discovery(*args):
    """
    """
    out_res = {"data": []}
    for i in conf.get("_list", []):
        addr = i.split("|")[0].strip()
        passwd = i.split("|")[1].strip()
        if not passwd:
            passwd = "None"
        out_res["data"].append({"{#REDIS}": addr, "{#PASSWORD}": passwd})
    out_res = json.dumps(out_res)
    return out_res


def status(redis_addr, passwd, keyword):
    """
    """
    if keyword in STATUS_OUTPUT:
        return _redis_info(redis_addr, passwd, keyword)
    elif keyword.lower() in ("conf", "config"):
        return _redis_conf(redis_addr, passwd)
    else:
        raise ValueError("Not support the keyword {!s} for the redis.".format(keyword))


def _redis_info(redis_addr, passwd, keyword):
    """
    """
    addr = redis_addr.strip().split(":")[0]
    port = int(redis_addr.strip().split(":")[1])
    if passwd in (None, "<nil>", "None"):
        passwd = None
    res = {}
    r = redis.Redis(host=addr, port=port, password=passwd, decode_responses=True)
    now_info = r.info()
    for i in STATUS_OUTPUT.get(keyword, []):
        if i in now_info:
            res[i] = now_info[i]
    if keyword == "Stats" and "keyspace_hits" in res and "keyspace_misses" in res:
        res["keyspace_hit_ratio"] = float(res["keyspace_hits"])/(res["keyspace_hits"]+res["keyspace_misses"])

    res = json.dumps(res)
    return res


def _redis_conf(redis_addr, passwd):
    """
    """
    addr = redis_addr.strip().split(":")[0]
    port = int(redis_addr.strip().split(":")[1])
    if passwd in (None, "<nil>", "None"):
        passwd = None
    res = {}
    r = redis.Redis(host=addr, port=port, password=passwd, decode_responses=True)
    now_conf = r.config_get()
    for i in CONFIG_OUTPU:
        if i in now_conf:
            if i == "maxmemory-policy":
                res["maxmemory_policy"] = now_conf["maxmemory-policy"]
                continue
            res[i] = now_conf[i]
    res = json.dumps(res)
    return res
