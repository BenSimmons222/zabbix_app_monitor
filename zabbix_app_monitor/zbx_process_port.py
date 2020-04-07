# -*- coding: utf8 -*-
# Author: AcidGo
# Version: 0.0.1
# Usage: pass


import json
import logging


# Config
MODULE = "process_port"
_env = {}
SUPPORT_CONN_STATE = (
    "ESTABLISHED",
    "TIME_WAIT",
    "LISTEN",
)
# EOF Config


def init(module):
    """由 ZBXApp 基类初始化的函数。
    """
    global app
    global conf
    app = _env["app"]
    conf = app.outcall_cfg_module(module)


def discovery(*args):
    """自动发现对应模块，并格式化为 zabbix 接受 josn。

    Args:
        args: 这个主要是为了兼容旧版本。
    Returns:
        out <json>:
            {
                "data": [
                    {
                        "{#PROCESS}": "#",
                        "{#TCP_PORT}": "#",
                        "{#NETSTAT_NAME}": "#",
                        "{#NETSTAT_PORT}": "#",
                        "{#NETSTAT_NUMBER}": "#",
                    }
                ]
            }
    """
    out = {"data": []}
    filtter = None if args[0] != "process.status" else "PROCESS"
    process_set = set()
    for line in conf.get("_raw", []):
        logging.debug("In process_port discovery, execute line: {!s}".format(line))
        line_lst = map(lambda x: x.strip(), line.split("|"))
        USER = line_lst[0]
        MODULE_NAME = line_lst[1]
        PROCESS = line_lst[2]
        TCP_PORT_lst = map(lambda x: x.strip(), line_lst[3].split(",")) if len(line_lst) > 3 else []
        NETSTAT_NUMBER_lst = map(lambda x: x.strip(), line_lst[4].split(",")) if len(line_lst) > 4 else []

        for index, p in enumerate(TCP_PORT_lst):
            tmp = {}
            tmp["{#PROCESS}"] = PROCESS
            tmp["{#TCP_PORT}"] = p
            if filtter == "PROCESS" and PROCESS in process_set:
                continue
            process_set.add(PROCESS)
            if len(NETSTAT_NUMBER_lst) > index:
                tmp["{#NETSTAT_NAME}"] = PROCESS
                tmp["{#NETSTAT_PORT}"] = p
                tmp["{#NETSTAT_NUMBER}"] = NETSTAT_NUMBER_lst[index] if NETSTAT_NUMBER_lst[index] else "#"
            else:
                tmp["{#NETSTAT_NAME}"] = tmp["{#NETSTAT_NUMBER}"] = tmp["{#NETSTAT_PORT}"] = "#"
            out["data"].append(tmp)
    out = json.dumps(out)
    return out


def conn_tcp(port, state):
    """统计本地某端口上某连接状态的数量统计。

    Args:
        port: 监控的本地端口号。
        state: 统计的状态类型。
    Returns:
        count <int>: 统计的数量
    """
    import subprocess

    port = str(int(port))
    state = state.upper()
    count = 0
    if state not in SUPPORT_CONN_STATE:
        raise ValueError("The state is not supported for conn_tcp: {!s}".format(state))
    res_shell = subprocess.check_output(["netstat", "-ant"], shell=False)
    res_shell = res_shell.split("\n")
    for line in res_shell:
        t = line.split()
        if len(t) < 4 or not t[0].strip().startswith("tcp"):
            continue
        if t[3].rsplit(":", 1)[-1] == port and t[-1] == state:
            count += 1
    return count