# -*- coding: utf8 -*-
# Author: AcidGo
# Version: 0.0.1
# Usage: pass


import json
import logging


# Config
MODULE = "telnet"
_env = {}
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
                        "{#TELNET_IP}": "#",
                        "{#TELNET_PORT}": "#",
                    }
                ]
            }
    """
    out = {"data": []}
    for line in conf.get("_raw", []):
        logging.debug("In {!s} discovery, execute line: {!s}".format(MODULE, line))
        line_lst = map(lambda x: x.strip(), line.split("|"))
        if len(line_lst) != 3:
            logging.warning("The line is not good: {!s}".format(line))
            continue
        COMMENT = line_lst[0]
        TELNET_IP = line_lst[1]
        TELNET_PORT = line_lst[2]
        tmp = {}
        tmp["{#TELNET_IP}"] = TELNET_IP
        tmp["{#TELNET_PORT}"] = TELNET_PORT
        out["data"].append(tmp)
    out = json.dumps(out)
    return out
