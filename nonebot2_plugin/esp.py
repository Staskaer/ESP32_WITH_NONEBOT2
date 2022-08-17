import contextlib
from re import sub
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import T_State, State
from nonebot.plugin import on_regex, on_message, on_command
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.permission import SUPERUSER
import requests
from urllib.parse import urljoin
import json


class ESP(object):
    # 储存全局配置信息的字典
    # 存储了打开关闭的url路径、状态同步路径、timeout信息
    _golbal_dict = {}
    # 储存名称与url的字典
    # 存储了房间名和对应的地址信息
    _url_dict = {}
    _conf_name = "esp_conf"

    def __init__(self):
        self._golbal_dict["on"] = "on"
        self._golbal_dict["off"] = "off"
        self._golbal_dict["conf"] = "conf"
        self._golbal_dict["timeout"] = "3"
        with contextlib.suppress(Exception):
            self._read()

    def rename(self, raw_name, new_name) -> Message:
        # 对名称进行重命名
        try:
            self._url_dict[new_name] = self._url_dict.pop(raw_name)
            self._write()
            return Message(f'"{raw_name}"已经更改成了"{new_name}"捏')
        except Exception:
            return Message("更改失败，请检测输入是否正确")

    def ls(self) -> Message:
        # 返回所有信息
        result = "内容如下：\n"
        for i in self._url_dict:
            result += f'开关"{i}"对应的地址为{self._url_dict[i]} '
        return Message(result)

    def reurl(self, name, new_url) -> Message:
        # 更新地址信息
        if name in self._url_dict.keys():
            if not new_url.startswith("http://"):
                new_url = f"http://{new_url}"
            self._url_dict[name] = new_url
            self._write()
            return Message("更新完成了捏")
        else:
            return Message("更新失败，请检查当前开关是否已被录入")

    def add_(self, name, url) -> Message:
        if name in self._url_dict.keys():
            return Message("添加失败，当前开关已经存在")
        if not url.startswith("http://"):
            url = f"http://{url}"
        self._url_dict[name] = url
        self._write()
        return Message("更新完成了捏")

    def del_(self, name) -> Message:
        # 删除某个开关
        if name in self._url_dict.keys():
            self._url_dict.pop(name)
            self._write()
            return Message(f'"{name}"已经删除了捏')
        else:
            return Message("当前开关不存在，请检查输入是否正确")

    def _write(self) -> None:
        # 持久化数据
        write_dict = {
            "_url_dict": self._url_dict,
            "_golbal_dict": self._golbal_dict
        }
        with open(self._conf_name, "w")as f:
            json.dump(write_dict, f)

    def _read(self) -> None:
        # 读取持久化的数据
        with open(self._conf_name, "r")as f:
            read_dict = json.load(f)
        self._golbal_dict = read_dict["_golbal_dict"]
        self._url_dict = read_dict["_url_dict"]

    def conf(self, key, value) -> Message:
        # 更改全局变量
        if key in self._golbal_dict.keys():
            self._golbal_dict[key] = value
            self._write()
            return Message(f'配置"{key}"已经更改了捏')
        else:
            return Message("当前配置项不存在捏")

    def on(self, name) -> Message:
        if name not in self._url_dict.keys():
            return Message("当前开关不存在捏")
        try:
            r = requests.get(
                url=urljoin(self._url_dict[name], self._golbal_dict["on"]), timeout=int(self._golbal_dict["timeout"]))
            return Message("已经打开了捏")
        except Exception:
            return Message("打开失败了捏")

    def close(self, name) -> Message:
        if name not in self._url_dict.keys():
            return Message("当前开关不存在捏")
        try:
            r = requests.get(
                url=urljoin(self._url_dict[name], self._golbal_dict["off"]), timeout=int(self._golbal_dict["timeout"]))
            return Message("已经关闭了捏")
        except Exception:
            return Message("关闭失败了捏")

    def auto_change(self, name) -> Message:
        if name not in self._url_dict.keys():
            return Message("当前开关不存在捏")
        try:
            r = requests.get(
                url=urljoin(self._url_dict[name], self._golbal_dict["conf"]), timeout=int(self._golbal_dict["timeout"]))
        except Exception:
            return Message("当前开关请求失败了捏")
        mode = int(r.text)
        return self.on(name) if mode == 0 else self.close(name)

    def help(self) -> Message:
        # 帮助文档
        return Message(r"关于命令说明请查看https://github.com/ppxxxg22/ESP32_WITH_NONEBOT2/tree/main/nonebot2_plugin")

    def callback(self, cmd_list) -> Message:
        # 根据命令来进行回调
        if len(cmd_list) == 1 or cmd_list[1] == "help":
            return self.help()
        elif cmd_list[1] == "on":
            return self.on(cmd_list[2])
        elif cmd_list[1] == "off":
            return self.close(cmd_list[2])
        elif cmd_list[1] == "ls":
            return self.ls()
        elif cmd_list[1] == "add":
            return self.add_(cmd_list[2], cmd_list[3])
        elif cmd_list[1] == "del":
            return self.del_(cmd_list[2])
        elif cmd_list[1] == "conf":
            return self.conf(cmd_list[2], cmd_list[3])
        elif cmd_list[1] == "rename":
            return self.rename(cmd_list[2], cmd_list[3])
        elif cmd_list[1] == "reurl":
            return self.reurl(cmd_list[2], cmd_list[3])
        else:
            try:
                return self.auto_change(cmd_list[1])
            except Exception:
                return Message("命令不正确捏")


ESP_CONTROL = ESP()
esp_code = on_command("esp32")


@esp_code.handle()
async def _esp(bot: Bot,
               event: Event,
               state: T_State = State(),
               permission=SUPERUSER):
    cmd_list = sub(" +", " ", str(event.get_message())).split(" ")
    await esp_code.finish(message=ESP_CONTROL.callback(cmd_list))
