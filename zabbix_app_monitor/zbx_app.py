# -*- coding: utf8 -*-
# Author: AcidGo
# Usage: zabbix APP 监控的基类，目前处于开发中。


import sys
import os
import json
import urllib2
import logging
from collections import Iterable
from  logging.handlers import RotatingFileHandler
from urlparse import urljoin



def init_logger(level, logfile=None):
    """日志功能初始化。
    如果使用日志文件记录，那么则默认使用 RotatinFileHandler 的大小轮询方式，
    默认每个最大 10 MB，最多保留 5 个。

    Args:
        level: 设定的最低日志级别。
        logfile: 设置日志文件路径，如果不设置则表示将日志输出于标准输出。
    """
    if not logfile:
        logging.basicConfig(
            level = getattr(logging, level.upper()),
            format = "%(asctime)s [%(levelname)s] %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S"
        )
    else:
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        if logfile.lower() == "local":
            logfile = os.path.join(sys.path[0], os.path.basename(os.path.splitext(__file__)[0]) + ".log")
        handler = RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.info("Logger init finished.")


class ZBXApp(object):
    """zabbix 监控中 app[*] 的基类和统一入口。

    """
    # CONFIG - 此配置可由初始化传入的配置文件覆盖调整
    # 监控模块的路径
    MODULE_PATH = "/usr/local/zbxexec/modules"
    # 应用 cfg 文件的遍历路径
    CFG_PATH_LIST = [
        "/export",
        "/home",
        "/root",
    ]
    # 应用 cfg 文件的文件名
    CFG_BASENAME = "lps.cfg"
    # 应用 cfg 文件查找时的目录遍历深度
    CFG_FIND_DEPTH = 3
    # 应用附件是否打开多个文件合并的开关
    CFG_FIND_ISALL = False
    # 应用 cfg 文件的注释符号集合
    CFG_COMMENT_PREFIX = ("#",)
    # 应用 cfg 文件的 key/value 索引正则表达式
    CFG_RE_KEY = r"(^[\w/\.:][^=]*)={0,1}([^=]*?)$"
    # 当前支持的哈希校验算法
    SUPPORT_HASH = ("md5",)
    # 限制的最大文件遍历深度
    FINDFILE_MAX_DEPTH = 4
    # cfg 模块的别名集合
    MODULE_ALIAS_CFG = ("cfg", "app", "hfs")
    # 重定义日志级别
    LOG_LEVEL = None
    # HFS 的地址集合
    HFS_ADDRESS = ["http://hfs"]
    # HFS 配置的别名
    HFS_ADDRESS_ALIAS = ("HFS_ADDRESS", "hfs", "HFS")
    # 访问 HFS 的 HTTP 请求头，可用以标志此基类的访问请求
    HFS_CLIENT_HEADERS = {"User-Agent": "ZBXApp"}
    # 访问 HFS 时定位的依赖文件名
    HFS_REQUIREMENTS = "requirements.txt"
    # HFS 中存放外部依赖包的文件夹
    HFS_PKG_FOLDER = "pkg"
    # 基类操作错误或失败时的记录标志文件
    FLAG_EXTRA_PATH = "/usr/local/zbxexec/flags/extra.flag"
    # EOF CONFIG

    def __init__(self, appcfg):
        self.iscfg = False
        self.discovery_outempty = False
        self.requirements = {}
        self.allfile_set = set()

        # From appcfg
        sys.path.insert(1, self.MODULE_PATH)
        try:
            appcfg = __import__(appcfg)
        except ImportError:
            logging.debug("Not found the appcfg: {!s}".format(appcfg))
        except:
            logging.error("The appcfg has error: {!s}".format(appcfg))
        else:
            logging.debug("Found the appcfg.")
            for attr in dir(appcfg):
                if not attr.startswith("_") and hasattr(self, attr):
                    setattr(self, attr, getattr(appcfg, attr))
                    logging.debug("Using the attr {!s} to {!s} from appcfg.".format(attr, getattr(self, attr)))
            # 如果配置里定义了日志级别，则修改日志级别
            if self.LOG_LEVEL:
                logging.getLogger().setLevel(getattr(logging, self.LOG_LEVEL.upper()))
        # EOF From appcfg

    def findfile(self, path_lst, basename, depth=1, ignoredirs=[".git", ".ssh"]):
        """
        """
        if self.CFG_FIND_ISALL:
            self._findfile_all(path_lst, basename, depth, ignoredirs)
            return self.allfile_set
        else:
            return [self._findfile_single(path_lst, basename, depth, ignoredirs)]

    def _findfile_single(self, path_lst, basename, depth=1, ignoredirs=[".git", ".ssh"]):
        """遍历各路径下的指定深度查找文件。
        如果多个路径下都有要查找的文件，那么以目录列表的顺序为优先。

        Args:
            path_lst <list>: 待查找的目录列表。
            basename: 需要在目录中查找的文件名。
            depth: 遍历深度，为 0 表示进判断目录路径或与文件名组合是否存在。
            ignoredirs: 忽略的目录集合。
        Returns:
            filepath: 查找得到的文件绝对路径。
        """
        if depth < 0:
            return 
        if depth > self.FINDFILE_MAX_DEPTH:
            raise ValueError("The depth of finding file is {!s}, more than FINDFILE_MAX_DEPTH.".format(depth))

        basename = basename.strip()
        for path in path_lst:
            logging.debug("In finding, for scan path: {!s}".format(path))
            continue
            if os.path.basename(path)[0] in (".", "_"):
                logging.debug("Ignore the path.")
            if not os.path.exists(path):
                logging.debug("The path {!s} is not exists or no permission.".format(path))
                continue
            elif os.path.isfile(path):
                if os.path.basename(path) == basename:
                    logging.debug("Found the except path: {!s}".format(path))
                    return path
                else:
                    continue
            sub_dirs = []
            try:
                path_dirlist = os.listdir(path)
            except Exception as e:
                logging.warning("Get error when listdir from {!s}: {!s}".format(path, e))
                continue
            for target in path_dirlist:
                if os.path.isfile(os.path.join(path, target)):
                    if target == basename:
                        return os.path.join(path, target)
                else:
                    sub_dirs.append(os.path.join(path, target))
            res = self._findfile_single(sub_dirs, basename, depth-1, ignoredirs=ignoredirs)
            if res:
                return res

    def _findfile_all(self, path_lst, basename, depth=1, ignoredirs=[".git", ".ssh"]):
        """
        """
        if depth < 0:
            return
        if depth > self.FINDFILE_MAX_DEPTH:
            raise ValueError("The depth of finding file is {!s}, more than FINDFILE_MAX_DEPTH.".format(depth))

        basename = basename.strip()
        for path in path_lst:
            logging.debug("In finding, for scan path: {!s}".format(path))
            if os.path.basename(path)[0] in (".", "_"):
                logging.debug("Ignore the path.")
                continue
            if not os.path.exists(path):
                logging.debug("The path {!s} is not exists or no permission.".format(path))
                continue
            elif os.path.isfile(path):
                if os.path.basename(path) == basename:
                    logging.debug("Found the except path: {!s}".format(path))
                    self.allfile_set.add(os.path.realpath(path))
                    continue
                else:
                    continue
            sub_dirs = []
            try:
                path_dirlist = os.listdir(path)
            except Exception as e:
                logging.warning("Get error when listdir from {!s}: {!s}".format(path, e))
                continue
            for target in path_dirlist:
                if os.path.isfile(os.path.join(path, target)):
                    if target == basename:
                        self.allfile_set.add(os.path.join(path, target))
                        continue
                else:
                    sub_dirs.append(os.path.join(path, target))
            self._findfile_all(sub_dirs, basename, depth-1, ignoredirs=ignoredirs)


    def parse_args(self, *args):
        """解析 zabbix 的 item 中 app[args] 传入的参数，拆分模块和函数。

        Args:
            *args: 位置参数集合。
        """
        logging.debug("In parse_args, input the args: {!s}".format(args))
        self.module_str = args[0].split(".", 1)[0].strip()
        self.func_str = args[0].split(".", 1)[1].strip()
        # 对于函数部位，可将 . 转换为 _
        # 如 a.b.c 会被转换为 a_b_c
        self.func_str = self.func_str.replace(".", "_")
        self.args = args[1:]

        if self.module_str.startswith("_") or self.func_str.startswith("_"):
            raise ValueError("Not allow to call moudle or func_str which startswith _.")

        if self.module_str in self.MODULE_ALIAS_CFG:
            self.iscfg = True
            self.module = self
        else:
            sys.path.insert(0, self.MODULE_PATH)
            try:
                self.module = __import__("zbx_" + self.module_str)
            except ImportError as e:
                if self.func_str == "discovery":
                    self.discovery_outempty = True
                    logging.debug("The module {!s} has ImportError, and the func is discovery.".format(self.module_str))
                else:
                    raise e
            except:
                raise e
        if not self.discovery_outempty and not hasattr(self.module, self.func_str):
            raise ValueError("Not found the func {!s} in module {!s}.".format(self.func_str, self.module_str))

    def parse_cfg(self, cfgpath_lst):
        """解析应用 cfg 文件，转换为字典的格式。

        Args:
            cfgpath_lst: cfg 文件的路径集合。
        Returns:
            res_cfg <dict>: 转换后的字典格式，大体为：
                {"section": {"key1": "value1", "key2": ""}}
        """
        import re
        logging.debug("In parse_cfg, start parsing cfg: {!s}".format(cfgpath_lst))
        re_p_cfg_key = re.compile(self.CFG_RE_KEY)
        res_cfg = {}

        if isinstance(cfgpath_lst, str):
            cfgpath_lst = [cfgpath_lst]

        for cfgpath in cfgpath_lst:
            with open(cfgpath, "r") as f:
                now_section = None
                for line in f:
                    line = line.strip()
                    # 判断是否为注释或空行，如果有注释前缀则忽略
                    if len(line) == 0 or line[0] in self.CFG_COMMENT_PREFIX:
                        continue
                    # 判断是否为节点标记
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1]
                        if section in res_cfg:
                            logging.debug("The section {!s} is multi in cfg.".format(section))
                        # 如果是非键值对的，则使用 _list 键来存放多个值
                        # 提供 _raw 键保存原始数据，供模块使用
                        else:
                            res_cfg[section] = {"_list": [], "_raw": []}
                        now_section = section
                    else:
                        if not now_section:
                            raise ValueError("There are configure not in a section: {!s}".format(line))
                        res_cfg[now_section]["_raw"].append(line)
                        re_res = re_p_cfg_key.search(line)
                        if not re_res:
                            continue
                        re_res = re_res.groups()
                        if not re_res[0]:
                            raise ValueError("The config in appcfg is invalid: {!s}".format(line))
                        if re_res[1].strip():
                            res_cfg[now_section][re_res[0].strip()] = re_res[1].strip()
                        else:
                            res_cfg[now_section]["_list"].append(re_res[0].strip())
        logging.debug("After parse_cfg: {!s}".format(res_cfg))
        return res_cfg

    def _extra_auto(self, cfgpath):
        """在 app[cfg.discovery] 关于基类自动发现函数被调用时，会额外进行一些任务。
        目前将会执行的操作：
        1. 从 hfs 中搜索最新模块并下载至本地的模块目录。
        2. 查看模块依赖包，然后进行包拉取。

        Args:
            cfgpath: cfg 的文件路径。
        Returns:
            is_ok <bool>: 操作是否符合预期。
        """
        cfg_dict = self.parse_cfg(cfgpath)
        hfs = [self.HFS_ADDRESS] if isinstance(self.HFS_ADDRESS, (str, )) else self.HFS_ADDRESS
        if cfg_dict.get("hfs_address", None) or cfg_dict.get("hfs", None):
            hfs = cfg_dict.get("hfs_address", None) or cfg_dict.get("hfs", None)
            if hfs:
                hfs = hfs.get("_list", [])
        if not hfs or not isinstance(hfs, (list,)):
            logging.error("Not found the hfs address from configure.")
            return False
        is_ok = False
        try:
            self._module_update(hfs, cfg_dict)
        except Exception as e:
            logging.error("Get errors when try to update module: {!s}".format(e))
            is_ok = False
        else:
            is_ok = True
            logging.debug("Module update finished.")
        return is_ok

    def _hfs_ping(self, url_lst):
        """测试 HFS url 列表中可访问的活动 url。
        
        Args:
            url_llst <list>: url 集合列表。
        Returns:
            url <string>: 探测到第一个可用的 url。
        """
        for url in url_lst:
            logging.debug("In _hfs_ping, face the url: {!s}".format(url))
            if not url.endswith("/"):
                url = url + "/"
            url_requirements = urljoin(url, self.HFS_REQUIREMENTS)
            logging.debug("Use the url {!s} to check.".format(url_requirements))
            try:
                request = urllib2.Request(url_requirements, headers=self.HFS_CLIENT_HEADERS)
                # TODO: 这里的 timeout 不针对底层 getinfo 的耗时，这个经验值是 20 秒超时，可以尝试优化此处
                response = urllib2.urlopen(request, timeout=3)
                self.requirements["_raw"] = response.read()
            except Exception as e:
                logging.warning("The url {!s} is inactive after hfs_ping check: {!s}".format(url, e.reason))
                continue
            else:
                return url

    def _hfs_install_module(self, url, module):
        """从指定 url 安装指定模块。
        
        Args:
            url: 指定的 url。
            module: 预期安装的模块。
        Raises:
            urllib2.HTTPError: 由 urllib2 模块进行 HTTP 处理时的报错。
        """
        from hashlib import md5

        hasexists = False
        url_m = urljoin(url, module)

        request = urllib2.Request(url_m, headers=self.HFS_CLIENT_HEADERS)
        response = urllib2.urlopen(request)
        # TODO: 限制下载文件大小或者分段下载
        hfs_m_data = response.read()

        local_md5 = None
        logging.debug("Found the module {!s} from the url: {!s}".format(module, url_m))
        local_module = os.path.join(self.MODULE_PATH, module)
        if os.path.exists(local_module):
            hasexists = True
            logging.debug("The module {!s} has been exists on the local: {!s}".format(module, local_module))
            with open(local_module, "rb") as f:
                md5_obj = md5()
                md5_obj.update(f.read())
                local_md5 = md5_obj.hexdigest().lower()

        url_m_md5 = urljoin(url, module + ".md5")
        try:
            request = urllib2.Request(url_m_md5, headers=self.HFS_CLIENT_HEADERS)
            response = urllib2.urlopen(request)
            hfs_m_md5 = response.read().strip().lower()
        except urllib2.HTTPError as e:
            if e.code == 404:
                raise Exception("The md5 url {!s} is not found.".format(url_m_md5))
        except Exception as e:
            raise e

        if hasexists and local_md5 == hfs_m_md5:
            logging.debug("After md5 check, the module {!s} is not changed on remote hfs.".format(module))
            return 
        logging.debug("Start overwrite or write the local module file: {!s}".format(local_module))
        # TODO: 判断具体场景是否需要使用中继覆盖的方式来避免一些争用
        with open(local_module, "w") as f:
            f.write(hfs_m_data)

    def _hfs_install_pkg(self, url, module):
        """从指定 url 安装指定模块的依赖包。
        
        Args:
            url: 指定 url。
            module: 由于搜索该模块依赖的包的模块名。
        Raises:
            ValueError: 依赖文件处理错误。
        """
        from StringIO import StringIO
        import tarfile

        tmp = [line.strip() for line in self.requirements["_raw"].split() if not line.strip().startswith("#")]
        now_section = None
        for line in tmp:
            if line.startswith("[") and line.endswith("]"):
                now_section = line.strip()[1:-1]
                self.requirements[now_section] = []
            else:
                if now_section:
                    self.requirements[now_section].append(line.strip())
                else:
                    raise ValueError("The config {!s} is invalid on requirements.".format(line))
        logging.debug("In _hfs_install_pkg, use the url: {!s}".format(url))
        if module in self.requirements:
            for pkg in self.requirements[module]:
                if pkg.startswith("_"):
                    continue
                url_pkg = urljoin(urljoin(url, self.HFS_PKG_FOLDER) + "/", pkg + ".tgz")
                logging.debug("In _hfs_install_pkg, start try to download the pkg: {!s}".format(url_pkg))
                local_pkg_path = os.path.join(self.MODULE_PATH, pkg)
                if os.path.exists(local_pkg_path):
                    logging.debug("The pkg {!s} has exists: {!s}".format(pkg, local_pkg_path))
                    continue
                try:
                    request = urllib2.Request(url_pkg, headers=self.HFS_CLIENT_HEADERS)
                    response = urllib2.urlopen(request)
                    data = response.read()
                except Exception as e:
                    logging.error("Get errors when download pkg {!s}: {!s}".format(url_pkg, e))
                    continue
                else:
                    buf = StringIO(data)
                    with tarfile.open(fileobj=buf, mode="r:gz") as buf_f:
                        buf_f.extractall(path=self.MODULE_PATH)
                    logging.info("Download pkg {!s} is sucessful, the local path: {!s}".format(pkg, local_pkg_path))
        else:
            logging.debug("The module {!s} is not in the requirements.".format(module))

    def _module_update(self, url_lst, cfg_dict):
        """从 HFS 列表中更新模块和依赖包。
        
        Args:
            url_lst: HFS url 集合。
            cfg_dict: 配置。
        """
        url = self._hfs_ping(url_lst)
        if not url:
            raise ValueError("Not found alive hfs url.")
        logging.info("Chek a alive hfs url: {!s}".format(url))
        
        # 注意: 这里会将模块加上前缀 "zbx_"，并且默认都是 ".py" 文件。
        modules = ("zbx_"+m+".py" for m in cfg_dict if m not in self.MODULE_ALIAS_CFG)
        for m in modules:
            is_ok_module = False
            try:
                self._hfs_install_module(url, m)
            except Exception as e:
                logging.error("There are some error on _hfs_install_module when do url {!s} and module {!s}: {!s}".format(url, m, e))
                continue
            try:
                # 因为依赖文件不添加 .py 后缀，因此需要去除
                self._hfs_install_pkg(url, m.rstrip(".py"))
            except Exception as e:
                logging.error("There are some error on _hfs_install_pkg: {!s}".format(e))
                raise e
            logging.info("Finish update the module: {!s}".format(m))

    def _module_update_v1(self, url, cfg_dict):
        """模块更新功能，旧版本，已废弃使用。
        """
        import urllib2
        from urlparse import urljoin
        from hashlib import md5

        request = urllib2.Request(url, headers=self.HFS_CLIENT_HEADERS)
        response = urllib2.urlopen(request)
        logging.debug("The url is good: {!s}".format(url))

        modules = (m + ".py" for m in cfg_dict if m not in self.MODULE_ALIAS_CFG)
        for m in modules:
            hasexists = False
            url_m = urljoin(url, m)
            try:
                request = urllib2.Request(url_m, headers=self.HFS_CLIENT_HEADERS)
                response = urllib2.urlopen(request)
                # TODO: 限制下载文件大小或者分段下载
                hfs_m_data = response.read()
            except urllib2.HTTPError as e:
                if e.code == 404:
                    logging.info("The module {!s} is not found in the {!s}.".format(m, url))
            except Exception as e:
                logging.error("There are some error where get the url: {!s}".format(url_m))
                logging.error(e)
            else:
                logging.debug("Found the module {!s} from the url: {!s}".format(m, url_m))
                local_module = os.path.join(self.MODULE_PATH, m)
                if os.path.exists(local_module):
                    hasexists = True
                    logging.debug("The module {!s} has been exists on the local: {!s}".format(m, local_module))
                    with open(local_module, "rb") as f:
                        md5_obj = md5()
                        md5_obj.update(f.read())
                        local_md5 = md5_obj.hexdigest().lower()
                url_m_md5 = urljoin(url, m + ".md5")
                try:
                    request = urllib2.Request(url_m_md5, headers=self.HFS_CLIENT_HEADERS)
                    response = urllib2.urlopen(request)
                    hfs_m_md5 = response.read().strip().lower()
                except urllib2.HTTPError as e:
                    logging.error("The md5 of module is not found: {!s}".format(url_m_md5))
                    continue
                except:
                    logging.error("There are some error where get the url: {!s}".format(url_m))
                    continue
                else:
                    if local_md5 == hfs_m_md5:
                        logging.debug("After md5 check, the module {!s} is not changed on remote hfs.".format(m))
                        continue
                logging.debug("Start overwrite or write the local module file: {!s}".format(local_module))
                # TODO: 判断具体场景是否需要使用中继覆盖的方式来避免一些争用
                with open(local_module, "w") as f:
                    f.write(hfs_m_data)

    def _flag_extra(self, is_ok):
        """对标记文件做修改。
        
        Args:
            is_ok <bool>: 填写的状态内容。
        """
        from datetime import datetime
        flag_folder = os.path.dirname(self.FLAG_EXTRA_PATH)
        if not os.path.exists(flag_folder):
            os.mkdir(flag_folder)
        # TODO: 如果并发较高或更新频繁，可使用 X 锁。
        with open(self.FLAG_EXTRA_PATH, 'w') as f:
            f.write("{!s}:[{!s}]".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), is_ok))

    def outcall_cfg_module(self, module, cfgpath=None):
        """供外部模块调用。
        
        Args:
            module: 模块名。
            cfgpath: cfg 配置文件路径。
        Returns:
            <dict>: cfg 文件中解析得到的该模块的配置信息。
        """
        if cfgpath and os.path.isfile(cfgpath):
            cfgpath = cfgpath
        else:
            cfgpath = self.findfile(self.CFG_PATH_LIST, basename=self.CFG_BASENAME, depth=self.CFG_FIND_DEPTH)
        if not cfgpath or cfgpath in ("None",):
            logging.error("on outcall_cfg_module, Not found the cfg on the local.")
            raise ValueError("Not found the cfg on the local.")
        cfg_dict = self.parse_cfg(cfgpath)
        if module not in cfg_dict:
            logging.error("On outcall_cfg_module, found the cfg {!s}, but not found the section {!s}.".format(cfgpath, module))
            raise ValueError("Found the cfg {!s}, but not found the section {!s}.".format(cfgpath, module))
        return cfg_dict.get(module, {})

    def start(self):
        """基类的监控执行驱动，作为入口对接各个模块。
        """
        try:
            # 如果对自动发现需要返回空，则返回空
            if self.discovery_outempty:
                tmp = {"data": []}
                print(json.dumps(tmp))
                return 
            # 如果模块提供了 _env 变量，将对其初始化并传入参数信息
            if hasattr(self.module, "_env"):
                self.module._env.update({"app": self})
                self.module.init(self.module_str)
            # Module Caller
            res = getattr(self.module, self.func_str)(*self.args)
            # 如果模块没有做 print 而是 return，那么会进行 print
            # zabbix requires
            if res not in ("", None):
                print(res)
        except Exception as e:
            logging.error("Get error from start call: ", exc_info=True)
            # logging.exception(e)
            raise e

    def discovery(self, basename=None, extra=True):
        """zabbix app item 中基类的自动发现方法，如 app[app.discovery], app[cfg.discovery] ...

        Args:
            extra <bool>: 是否进行额外的维护操作，主要是针对 self._discovery_extra 函数的执行。
        Returns:
            <json>: 
                { "data": [ { "{#CFG}": cfgpath } ] }
        """
        out = {"data": []}
        logging.debug("Start for app discovery.")
        basename = basename if basename else self.CFG_BASENAME
        cfgfile = self.findfile(self.CFG_PATH_LIST, basename=basename, depth=self.CFG_FIND_DEPTH)
        logging.debug("In discovery, after findfile, the cfgfile is: {!s}".format(cfgfile))
        # 如果 cfgfile 符合预期地被发现，且需要 extra 则会进行额外操作
        if cfgfile not in ("None", None) and cfgfile and extra:
            if not self._extra_auto(cfgfile):
                self._flag_extra(False)
            else:
                self._flag_extra(True)
        if isinstance(cfgfile, str):
            cfgfile = [cfgfile]
        for f in cfgfile:
            out["data"].append({"{#CFG}": str(f)})
        print(json.dumps(out))

    def item(self, type_, *args):
        """基类自身的监控项集合，有传参 type_ 来确定具体监控。

        Args:
            type_: 指定执行的监控。
            args: 由 zabbix 传入的后续位置参数。
        """
        if not hasattr(self, "item_{!s}".format(type_)):
            raise ValueError("The ZBXApp does not has the item: {!s}".format(type_))
        func = getattr(self, "item_{!s}".format(type_))
        print(func(*args))

    def item_multi_v1(self):
        """对监控项的批量获取，可对接 zabbix 的 item 依赖项目。
        """
        from hashlib import md5

        isbad = False
        out = {
            "path":"",
            "md5": "",
            "sections": [],
        }
        out["path"] = str(self.findfile(self.CFG_PATH_LIST, basename=self.CFG_BASENAME, depth=1))
        logging.debug("In item_multi, found the path: {!s}.".format(out["path"]))
        isbad = True if out.get("path", "None") == "None" else isbad
        if isbad: return out
        with open(out["path"], "rb") as f:
            md5_obj = md5()
            md5_obj.update(f.read())
            out["md5"] = md5_obj.hexdigest().lower()
        out["sections"] = self.cfg_get_sections(out["path"])
        return json.dumps(out)

    def item_multi(self, cfgpath):
        """对监控项的批量获取，可对接 zabbix 的 item 依赖项目。
        这里使用 cfgpath 作为输入，由 zabbix 的自动发现中平滑过渡到监控项原型。

        Args:
            cfgpath: 应用 cfg 文件的路径。
        """
        from hashlib import md5

        isbad = False
        out = {
            "path":"",
            "md5": "",
            "sections": [],
        }
        out["path"] = cfgpath
        logging.debug("In item_multi, use the path: {!s}.".format(out["path"]))
        isbad = True if out.get("path", "None") == "None" else isbad
        if isbad: return out
        with open(out["path"], "rb") as f:
            md5_obj = md5()
            md5_obj.update(f.read())
            out["md5"] = md5_obj.hexdigest().lower()
        out["sections"] = self.cfg_get_sections(out["path"])
        return json.dumps(out)

    def cfg_get_sections(self, cfgpath):
        """
        """
        return [i for i in self.parse_cfg(cfgpath)]


if __name__ == "__main__":
    init_logger("error", "local")
    if len(sys.argv) < 1:
        raise ValueError("The input args is empty.")
    app = ZBXApp("appcfg")
    app.parse_args(*sys.argv[1:])
    app.start()
