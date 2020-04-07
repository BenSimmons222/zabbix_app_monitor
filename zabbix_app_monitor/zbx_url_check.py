# -*- coding: utf8 -*-
# Author: AcidGo && dongtb
# Version: 0.1.0
# Usage: pass


import json
import logging
import requests

# Config
MODULE = "url_check"
_env = {}


def init(module):
    """由 ZBXApp 基类初始化的函数。
    """
    global app
    global conf
    app = _env["app"]
    conf = app.outcall_cfg_module(module)


def discovery(*args):
    """
    """
    out = {"data": []}
    for line in conf.get("_raw", []):
        logging.debug("In {!s} discovery, execute line: {!s}".format(MODULE, line))
        line_lst = map(lambda x: x.strip(), line.split("|"))
        if len(line_lst) == 3:
            # 使用 get 
            URL_NAME = line_lst[0]
            URL_METHOD = line_lst[1]
            URL_PATH = line_lst[2]
            tmp = {}
            tmp["{#URL_NAME}"] = URL_NAME
            tmp["{#URL_METHOD}"] = URL_METHOD
            tmp["{#URL_PATH}"] = URL_PATH
            out["data"].append(tmp)
        elif len(line_lst) == 5:
            # 使用post
            URL_NAME = line_lst[0]
            URL_METHOD = line_lst[1]
            URL_PATH = line_lst[2]
            URL_SEND = line_lst[3]
            URL_RES = line_lst[4]
            tmp = {}
            tmp["{#URL_NAME}"] = URL_NAME
            tmp["{#URL_METHOD}"] = URL_METHOD
            tmp["{#URL_PATH}"] = URL_PATH
            tmp["{#URL_SEND}"] = URL_SEND
            tmp["{#URL_RES}"] = URL_RES
            out["data"].append(tmp)
        else:
            logging.error("The number of parameters is incorrect，get needs 3 and post needs 5 ,now:{!s}".format(
                len(line_lst)))
    out = json.dumps(out)
    return out


def url_code(url, mentod=None, send=None, timeout=5):
    if mentod == "get" or mentod == None:
        out = {}
        try:
            response = requests.get(url, timeout=timeout)
            out["rc"] = response.status_code
            out["rt"] = response.elapsed.seconds
            out = json.dumps(out)
            return out
        except:
            raise
            out["rc"] = 0
            out["rt"] = 0
            out = json.dumps(out)
            return out
    elif mentod == "post":
        out = {}
        try:
            response = requests.post(url, timeout=timeout, data=send)
            out["rc"] = response.status_code
            out["rt"] = response.elapsed.seconds
            out["rr"] = response.text.strip('\n')
            out = json.dumps(out)
            return out
        except:
            raise
            out["rc"] = 0
            out["rt"] = 0
            out["rr"] = 0
            out = json.dumps(out)
            return out
