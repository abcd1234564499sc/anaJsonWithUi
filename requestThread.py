#!/usr/bin/env python
# coding=utf-8
import time
from queue import Queue

from PyQt5.QtCore import QThread, pyqtSignal

import myUtils


class RequestThread(QThread):
    signal_result = pyqtSignal(dict)

    def __init__(self):
        super(RequestThread, self).__init__()
        self.queue = Queue()

    def run(self):
        self.runFlag = True
        while self.runFlag:
            if not self.queue.empty():
                inputDic = self.queue.get()
                repDic = myUtils.requestsUrl(inputDic["url"], cookie=inputDic["cookie"], header=inputDic["header"],
                                             data=inputDic["data"], type=inputDic["type"],
                                             proxies=inputDic["proxies"])
                # 重构获取的结果列表
                if repDic["checkFlag"]:
                    tmpReqResultList = repDic.pop("resultList")
                    tmpReqResultDict = tmpReqResultList[-1]
                    repDic.update(tmpReqResultDict)

                resultDic = {"input": inputDic, "result": repDic, "extraData": inputDic["extraData"]}
                self.signal_result.emit(resultDic)
            else:
                time.sleep(1)
                continue

    def addUrl(self, url, cookie={}, header={}, proxies=None, data={}, type=0, extraData=None):
        tmpDic = {"url": url, "cookie": cookie, "header": header, "proxies": proxies, "data": data, "type": type,
                  "extraData": extraData}
        self.queue.put(tmpDic)

    def stopThread(self):
        self.runFlag = False
