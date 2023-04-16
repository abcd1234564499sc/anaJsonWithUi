#!/usr/bin/env python
# coding=utf-8
import copy
import json
import os
import queue
import re
import sys
import traceback
import warnings
from queue import Queue

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem, QHeaderView, QFileDialog

import myUtils
from AnaJsonThread import AnaJsonThread
from ConnectProxy import ConnectProxy
from ExportExcellThread import ExportExcellThread
from requestThread import RequestThread
from ui.mainForm import Ui_mainForm


class Main(QMainWindow, Ui_mainForm):
    ### 全局方法
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)
        self.charIde = "¿"
        self.responseTypeList = []
        self.responseTypeList.append({"name": "普通JSON类型", "key": "normal", "note": "{\"a\":123}"})
        self.responseTypeList.append({"name": "JSON字符串", "key": "jsonStr", "note": "\"{\\\"a\\\":123}\""})
        self.connectProxyThread = None
        warnings.filterwarnings("ignore")
        self.confFileName = "工具配置.conf"
        self.confHeadList = ["是否使用代理", "代理IP", "代理端口", "代理服务器使用Https", "单次导出数据条数"]
        self.responseAnaResultTreeWidget.hideColumn(3)
        self.confDic = self.initConfFile()
        self.createInputTabWidget(1)
        self.tableWidget_index1.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resultTableHeaderBase = ["输入值", "响应码", "请求结果"]
        self.createResponseTypeComboBox()
        # 开启网络请求线程
        self.anaJsonReqThread = RequestThread()
        self.anaJsonReqThread.signal_result.connect(self.doAnaJsonResponse)
        self.getResponseReqThread = RequestThread()
        self.getResponseReqThread.signal_result.connect(self.doAddResponseToResult)
        self.anaJsonThread = AnaJsonThread()
        self.anaJsonThread.signal_result.connect(self.sendReuqestUseJsonArg)
        self.anaJsonReqThread.start()
        self.getResponseReqThread.start()
        self.exportExcellThread = None

    def createResponseTypeComboBox(self):
        for tmpIndex, tmpResponseTypeDic in enumerate(self.responseTypeList):
            self.responseTypeComboBox.addItem(tmpResponseTypeDic["name"])

    # 写日志，logType：0代表普通日志，1代表警告日志（如输入错误等）,2代表异常日志
    def writeLog(self, logStr, logType=0):
        # 获取当前时间
        nowSeconed = myUtils.getNowSeconed()
        finalLog = "[{0}] {1}".format(nowSeconed, logStr)
        if logType == 0:
            finalLog = "<span>[日志] {}</span>".format(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
            self.logTextEdit.append(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
        elif logType == 1:
            finalLog = "<span style='color:blue'>[提示] {}</span>".format(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
            self.logTextEdit.append(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
        elif logType == 2:
            finalLog = "<span style='color:red'>[异常] {}</span>".format(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
            self.logTextEdit.append(finalLog)
            self.logTextEdit.moveCursor(QTextCursor.End)
        else:
            pass

    # 初始化配置文件，生成配置文件并返回一个配置字典
    # 字典结构为：{
    # "confFileName":配置文件文件名,
    # "ifProxy":是否开启代理，
    # "proxyIp":代理IP,
    # "proxyPort":代理端口
    # }
    def initConfFile(self):
        defaultIfProxy = 0
        defaultProxyIp = ""
        defaultProxyPort = ""
        defaultIfProxyUseHttps = 0
        defaultExportCount = 10000
        defaultConfHeaderList = self.confHeadList
        confDic = {defaultConfHeaderList[0]: defaultIfProxy, defaultConfHeaderList[1]: defaultProxyIp,
                   defaultConfHeaderList[2]: defaultProxyPort, defaultConfHeaderList[3]: defaultIfProxyUseHttps,
                   defaultConfHeaderList[4]: defaultExportCount}

        # 判断是否存在配置文件
        confFilePath = os.path.join(os.getcwd(), self.confFileName)
        if not os.path.exists(confFilePath):
            myUtils.writeToConfFile(confFilePath, confDic)
            confDic["confHeader"] = defaultConfHeaderList
        else:
            confDic = myUtils.readConfFile(confFilePath)
        headerList = confDic["confHeader"]

        reConfDic = {"confFilePath": confFilePath, "confHeaderList": headerList,
                     "ifProxy": True if int(confDic[headerList[0]]) == 1 else False,
                     "proxyIp": confDic[headerList[1]], "proxyPort": confDic[headerList[2]],
                     "ifProxyUseHttps": True if int(confDic[headerList[3]]) == 1 else False,
                     "exportSaveCount": int(confDic[headerList[4]])}

        # 更新代理设置
        self.proxies = self.updateProxy(reConfDic)

        # 更新代理设置页面内容
        self.updateProxyTab(reConfDic)

        return reConfDic

    ### 设置代理页面方法
    # 保存代理设置
    def saveProxy(self):
        # 读取当前代理配置值
        nowProxyCheckStatus = False if int(self.useProxyCheckBox.checkState()) == 0 else True
        nowProxyIp = self.proxyIpLineEdit.text().strip()
        nowProxyPort = self.proxyPortLineEdit.text().strip()
        nowIfProxyUseHttps = False if int(self.ifProxyUseHttpsCheckBox.checkState()) == 0 else True
        if not nowProxyCheckStatus:
            pass
        else:
            # 验证输入值是否符合规则
            if not myUtils.ifIp(nowProxyIp):
                warningStr = "输入的代理IP不符合IP规范"
                self.writeLog(warningStr, 1)
                return
            elif not nowProxyPort.isdigit():
                warningStr = "输入的代理端口必须是一个正整数"
                self.writeLog(warningStr, 1)
                return

        # 生成字典
        confDic = {self.confHeadList[0]: 1 if nowProxyCheckStatus else 0, self.confHeadList[1]: nowProxyIp,
                   self.confHeadList[2]: nowProxyPort, self.confHeadList[3]: 1 if nowIfProxyUseHttps else 0,
                   self.confHeadList[4]: int(self.confDic[self.headerList[4]])}

        # 保存到配置文件
        confFilePath = os.path.join(os.getcwd(), self.confFileName)
        myUtils.writeToConfFile(confFilePath, confDic)

        # 更新当前配置
        headerList = self.confHeadList
        self.confDic = {"confFilePath": confFilePath, "confHeaderList": headerList,
                        "ifProxy": True if int(confDic[headerList[0]]) == 1 else False,
                        "proxyIp": confDic[headerList[1]], "proxyPort": confDic[headerList[2]],
                        "ifProxyUseHttps": True if int(confDic[headerList[3]]) == 1 else False,
                        "exportSaveCount": int(confDic[headerList[4]])}
        # 更新代理设置
        self.proxies = self.updateProxy(self.confDic)

        warningStr = "成功保存代理设置"
        self.writeLog(warningStr, 0)

    def connectProxy(self):
        self.connectProxyButton.setEnabled(False)
        nowProxyIp = self.proxyIpLineEdit.text().strip()
        nowProxyPort = self.proxyPortLineEdit.text().strip()
        # 验证输入值是否符合规则
        if not myUtils.ifIp(nowProxyIp):
            warningStr = "输入的代理IP不符合IP规范"
            self.writeLog(warningStr, 1)
            self.connectProxyButton.setEnabled(True)
            return
        elif not nowProxyPort.isdigit():
            warningStr = "输入的代理端口必须是一个正整数"
            self.writeLog(warningStr, 1)
            self.connectProxyButton.setEnabled(True)
            return
        # 测试连接
        warningStr = "正在连接代理服务器..."
        self.writeLog(warningStr, 0)
        self.connectProxyThread = ConnectProxy(nowProxyIp, nowProxyPort)
        self.connectProxyThread.signal_result.connect(self.proxyConnectResult)
        self.connectProxyThread.start()

    def proxyConnectResult(self, result):
        if result:
            warningStr = "代理服务器连接成功"
            self.writeLog(warningStr, 0)
        else:
            warningStr = "代理服务器连接失败"
            self.writeLog(warningStr, 1)
        self.connectProxyButton.setEnabled(True)

    # 根据配置字典更新当前代理设置
    def updateProxy(self, confDic):
        proxies = ""
        # 更新代理设置
        if confDic["ifProxy"]:
            proxyPro = "https" if confDic["ifProxyUseHttps"] else "http"
            proxyStr = "{0}://{1}:{2}".format(proxyPro, confDic["proxyIp"], confDic["proxyPort"])
            proxies = {"http": proxyStr, "https": proxyStr}
        else:
            proxies = None
        return proxies

    # 根据配置字典更新当前代理设置页面
    def updateProxyTab(self, confDic):
        self.ifProxyUseHttpsCheckBox.setChecked(confDic["ifProxyUseHttps"])
        self.proxyIpLineEdit.setText(str(confDic["proxyIp"]))
        self.proxyPortLineEdit.setText(str(confDic["proxyPort"]))
        self.useProxyCheckBox.setChecked(confDic["ifProxy"])
        self.updateProxyUiStatus(1 if confDic["ifProxy"] else 0)

    def updateProxyUiStatus(self, status):
        if status == 0:
            self.connectProxyButton.setEnabled(False)
            self.proxyIpLineEdit.setEnabled(False)
            self.proxyPortLineEdit.setEnabled(False)
            self.ifProxyUseHttpsCheckBox.setEnabled(False)
        else:
            self.connectProxyButton.setEnabled(True)
            self.proxyIpLineEdit.setEnabled(True)
            self.proxyPortLineEdit.setEnabled(True)
            self.ifProxyUseHttpsCheckBox.setEnabled(True)

    ### 报文处理界面方法
    def addCharIden(self):
        startIndex = self.packetTextEdit.textCursor().selectionStart()
        endIndex = self.packetTextEdit.textCursor().selectionEnd()
        if startIndex == endIndex:
            return
        beforeText = self.packetTextEdit.toPlainText()
        afterText = beforeText[:startIndex] + self.charIde + beforeText[
                                                             startIndex: endIndex] + self.charIde + beforeText[
                                                                                                    endIndex:]
        afterText = self.changeToHtmlEnity(afterText)
        finText = self.setColorForCharIden(afterText)

        # 使用换行符分割
        tmpList = finText.split("\n")
        self.packetTextEdit.clear()
        for tmpStr in tmpList:
            self.packetTextEdit.append("<span>" + tmpStr + "</span>")

        # 根据当前标识的数量创建输入设置标签中的序号标签
        nowPacketStr = self.packetTextEdit.toPlainText()
        needTabCount = len(re.findall('[{}]'.format(self.charIde), nowPacketStr)) / 2
        self.createInputTabWidget(needTabCount)

    def clearCharIden(self):
        beforeText = self.packetTextEdit.toPlainText()
        afterText = beforeText.replace(self.charIde, "")
        self.packetTextEdit.setText(afterText)
        self.createInputTabWidget(0)

    # 将被标识符包围的字符区域染色
    def setColorForCharIden(self, colorStr):
        tmpList = colorStr.split(self.charIde)
        finText = ""
        for tmpIndex, tmpStr in enumerate(tmpList):
            if tmpIndex == len(tmpList) - 1:
                finText = finText + tmpStr
                break
            else:
                pass
            if tmpIndex % 2 == 0:
                finText = finText + tmpStr + "<span style='color:red;background:yellow'>" + self.charIde
            else:
                finText = finText + tmpStr + self.charIde + "</span>"
        return finText

    # 将空格替换为html实体
    def changeToHtmlEnity(self, inputStr):
        finStr = inputStr.replace(" ", "&nbsp;")
        return finStr

    def requestAndAnaJson(self):
        reFlag = self.doRequestAndAnaJson()
        self.startSendButton.setEnabled(reFlag)

    def doRequestAndAnaJson(self):
        nowPacketStr = self.packetTextEdit.toPlainText().replace(self.charIde, "")
        ifUseHttps = False if int(self.ifPacketUseHttpsCheckBox.checkState()) == 0 else True
        if nowPacketStr.strip("\n") == "":
            warningStr = "请输入报文"
            self.writeLog(warningStr, 1)
            return False
        try:
            warningStr = "开始请求并解析报文..."
            self.writeLog(warningStr, 0)
            nowPro = "https" if ifUseHttps else "http"
            nowPacketDic = myUtils.analysisPacketFromTxt(nowPacketStr)

            nowUrl = "{0}://{1}{2}".format(nowPro, nowPacketDic["host"], nowPacketDic["uri"])
            self.anaJsonReqThread.addUrl(nowUrl, cookie=nowPacketDic["cookie"], header=nowPacketDic["header"],
                                         data=nowPacketDic["data"], type=nowPacketDic["requestType"],
                                         proxies=self.proxies)
        except Exception as ex:
            warningStr = traceback.format_exc()
            self.writeLog(warningStr, 2)
            return False
        return False

    def sendPacketUseInput(self):
        # 获取返回值选择
        nowTopItemsCount = self.responseAnaResultTreeWidget.topLevelItemCount()
        selectDicList = []
        itemQueue = Queue()
        for nowTopItemIndex in range(nowTopItemsCount):
            tmpItem = self.responseAnaResultTreeWidget.topLevelItem(nowTopItemIndex)
            itemQueue.put(tmpItem)
        while not itemQueue.empty():
            tmpDic = {}
            tmpItem = itemQueue.get()
            # 处理子节点
            nowChildrenCount = tmpItem.childCount()
            for tmpIndex in range(nowChildrenCount):
                tmpChildItem = tmpItem.child(tmpIndex)
                itemQueue.put(tmpChildItem)
            # 获取当前节点信息
            nowName = tmpItem.text(1)
            nowType = tmpItem.text(2)
            nowStrcut = tmpItem.text(3)
            nowCheckStatus = tmpItem.checkState(0)
            tmpDic["name"] = nowName
            tmpDic["struct"] = nowStrcut
            tmpDic["checkStatus"] = nowCheckStatus
            if nowCheckStatus == 2 and nowStrcut != "" and nowType == "值":
                selectDicList.append(tmpDic)
            else:
                continue
        if len(selectDicList) == 0:
            warningStr = "没有勾选要输出的JSON值，请在[返回值解析]页面进行选择"
            self.writeLog(warningStr, 1)
            return
        else:
            pass
        self.anaJsonThread.setSelectDicList(selectDicList)
        self.anaJsonThread.start()
        warningStr = "正在根据勾选项进行分析"
        self.writeLog(warningStr)
        warningStr = "若勾选项过多，可能会耗费一段时间，请耐心等待"
        self.writeLog(warningStr)

    def sendReuqestUseJsonArg(self, jsonArgList):
        warningStr = "勾选项分析完成，根据勾选项共会产生{}条结果".format(len(jsonArgList) - 1)
        self.writeLog(warningStr)
        # 获取报文
        nowPacketStr = self.packetTextEdit.toPlainText()
        charIdeCount = nowPacketStr.count(self.charIde)
        if charIdeCount % 2 != 0:
            warningStr = "存在不成对的标识，请检查报文输入"
            self.writeLog(warningStr, 1)
            return
        # 分割报文
        packetSplitList = nowPacketStr.split(self.charIde)
        # 获取当前输入
        tabsCount = self.inputTabWidget.count()
        inputs = []
        for tabIndex in range(tabsCount):
            nowInput = []
            nowTabWidget = self.inputTabWidget.widget(tabIndex)
            nowTableWidget = nowTabWidget.children()[1]
            nowTableRowCount = nowTableWidget.rowCount()
            for rowIndex in range(nowTableRowCount):
                nowItem = nowTableWidget.item(rowIndex, 0)
                if nowItem is None:
                    nowText = ""
                else:
                    nowText = nowItem.text()
                nowInput.append(nowText)
            if len(nowInput) == 0:
                nowInput.append("")
            inputs.append(nowInput)
        # 构建报文
        maxCoordinate = [len(i) - 1 for i in inputs]
        nowCoordinate = [0 for a in inputs]
        ifAddFlag = True
        packetUseInputList = []
        while ifAddFlag:
            nowInputList = []
            for tmpIndex in range(len(nowCoordinate)):
                tmpInput = inputs[tmpIndex][nowCoordinate[tmpIndex]]
                nowInputList.append(tmpInput)
            tmpPacketStr = ""
            for tmpIndex, tmpStr in enumerate(packetSplitList):
                nowAddPacket = ""
                if tmpIndex % 2 != 0:
                    tmpNowInputIndex = int(tmpIndex / 2)
                    nowAddPacket = nowInputList[tmpNowInputIndex]
                else:
                    nowAddPacket = tmpStr
                tmpPacketStr = tmpPacketStr + nowAddPacket
            packetUseInputList.append({"packet": tmpPacketStr, "input": nowInputList})
            ifAddFlag, nowCoordinate = myUtils.coordinatePlus(nowCoordinate, maxCoordinate)
        # 开始请求
        # 构建输出结果表格
        tmpTableHeader = self.resultTableHeaderBase + [headerName for headerName in jsonArgList[0]]
        self.resultTable.setColumnCount(len(tmpTableHeader))
        self.resultTable.setHorizontalHeaderLabels(tmpTableHeader)
        self.resultTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        myUtils.clearTalbe(self.resultTable)
        warningStr = "开始根据输入值请求报文"
        self.writeLog(warningStr, 0)
        warningStr = "根据输入值，共需请求{0}次".format(len(packetUseInputList))
        self.writeLog(warningStr, 0)
        warningStr = "请求结果请查看[输出结果]页面"
        self.writeLog(warningStr, 0)
        ifUseHttps = False if int(self.ifPacketUseHttpsCheckBox.checkState()) == 0 else True
        try:
            for tmpPacketIndex, nowPacketUseInputDic in enumerate(packetUseInputList):
                nowPacketUseInputStr = nowPacketUseInputDic["packet"]
                nowPacketInputListStr = ",".join(nowPacketUseInputDic["input"])
                nowPro = "https" if ifUseHttps else "http"
                nowPacketDic = myUtils.analysisPacketFromTxt(nowPacketUseInputStr)
                nowUrl = "{0}://{1}{2}".format(nowPro, nowPacketDic["host"], nowPacketDic["uri"])
                extraDic = {"input": nowPacketInputListStr,
                            "ifEnd": True if tmpPacketIndex == len(packetUseInputList) - 1 else False,
                            "jsonArgList": jsonArgList}
                self.getResponseReqThread.addUrl(nowUrl, cookie=nowPacketDic["cookie"], header=nowPacketDic["header"],
                                                 data=nowPacketDic["data"], type=nowPacketDic["requestType"],
                                                 proxies=self.proxies, extraData=extraDic)
        except Exception as ex:
            warningStr = traceback.format_exc()
            self.writeLog(warningStr, 2)
            return False

    def responseTypeChange(self, nowIndex):
        nowNote = self.responseTypeList[nowIndex]["note"]
        self.responseTypeExample.setText("示例：" + nowNote)

    ### 返回值解析界面方法
    def anaResponseByResponseType(self, responseContent):
        nowSelectIndex = self.responseTypeComboBox.currentIndex()
        nowResponseTypeDic = self.responseTypeList[nowSelectIndex]
        nowKey = nowResponseTypeDic["key"]

        if nowKey == "normal":
            pass
        elif nowKey == "jsonStr":
            responseContent = json.loads(responseContent)
        else:
            pass
        return responseContent

    def doAnaJsonResponse(self, resultDic):
        inputDic = resultDic["input"]
        repDic = resultDic["result"]
        repStatus = repDic["status"]
        reqFlag = repDic["checkFlag"]
        if not reqFlag:
            warningStr = "请求URL：{0} 时发生异常，异常报错为{1}".format(inputDic["url"], repDic["resultStr"])
            self.writeLog(warningStr, 2)
            self.startSendButton.setEnabled(False)
        else:
            if int(repStatus) != 200:
                warningStr = "请求URL：{0}的响应码为{1}，请求失败".format(inputDic["url"], repStatus)
                self.writeLog(warningStr, 1)
                self.startSendButton.setEnabled(False)
            else:
                repContent = repDic["pageContent"]
                repContent = self.anaResponseByResponseType(repContent)
                anaResultStr, anaJsonDic = myUtils.anaJson(repContent)
                if anaResultStr != "":
                    warningStr = "解析当前报文失败，错误信息为：{}".format(anaResultStr)
                    self.writeLog(warningStr, 1)
                    self.startSendButton.setEnabled(False)
                else:
                    self.createTreeWidgetFromJsonTree(anaJsonDic)
                    warningStr = "请求成功，解析结果请查看[返回值解析]页面".format(inputDic["url"], repStatus)
                    self.writeLog(warningStr, 0)
                    self.startSendButton.setEnabled(True)

    # 根据传入的json结构树字典构建一个treewidget，每个节点带一个复选框
    def createTreeWidgetFromJsonTree(self, treeDic):
        self.responseAnaResultTreeWidget.itemChanged['QTreeWidgetItem*', 'int'].disconnect()
        self.responseAnaResultTreeWidget.clear()
        keyQueue = Queue()
        for tmpKey in treeDic.keys():
            keyQueue.put(
                {"key": tmpKey, "parent": self.responseAnaResultTreeWidget, "value": treeDic[tmpKey],
                 "location": []})
        while not keyQueue.empty():
            tmpKeyItem = keyQueue.get()
            if type(tmpKeyItem["key"]) != int:
                nowLocDic = {"value": tmpKeyItem["key"], "type": 0, "listCount": 0}  # 0表示值（包括值和字典类型）,1表示数组
                nowLoaction = copy.deepcopy(tmpKeyItem["location"])
                nowLoaction.append(nowLocDic)
                tmpTreeItem = QTreeWidgetItem(tmpKeyItem["parent"])
                tmpTreeItem.setCheckState(0, Qt.Unchecked)
                if tmpKeyItem["value"] == {}:
                    tmpTreeItem.setText(2, "值")
                else:
                    tmpTreeItem.setText(2, "字典")
                tmpTreeItem.setText(1, str(tmpKeyItem["key"]))
                tmpTreeItem.setText(3, json.dumps(nowLoaction))

                for tmpKey in tmpKeyItem["value"].keys():
                    tmpItem = {"key": tmpKey, "parent": tmpTreeItem, "value": tmpKeyItem["value"][tmpKey],
                               "location": nowLoaction}
                    keyQueue.put(tmpItem)
            else:
                # 处理数组的情况
                nowListCount = tmpKeyItem["key"]
                nowLoaction = tmpKeyItem["location"]
                if len(nowLoaction) != 0:
                    nowLoaction[-1]["type"] = 1
                    nowLoaction[-1]["listCount"] = nowListCount
                    nowParentObj = tmpKeyItem["parent"]
                    nowParentObj.setText(2, "数组[长度为{}]".format(nowListCount))
                    nowParentObj.setText(3, "")
                else:
                    # 根节点就是数组
                    tmpTreeItem = QTreeWidgetItem(tmpKeyItem["parent"])
                    tmpTreeItem.setText(2, "数组[长度为{}]".format(nowListCount))
                    tmpTreeItem.setText(1, "根节点")
                    tmpTreeItem.setText(3, json.dumps(nowLoaction))
                    tmpKeyItem["parent"] = tmpTreeItem
                    nowLocDic = {"value": "", "type": 1, "listCount": nowListCount}  # 0表示值（包括值和字典类型）,1表示数组
                    nowLoaction.append(nowLocDic)

                for tmpKey in tmpKeyItem["value"].keys():
                    tmpItem = {"key": tmpKey, "parent": tmpKeyItem["parent"], "value": tmpKeyItem["value"][tmpKey],
                               "location": nowLoaction}
                    keyQueue.put(tmpItem)
        self.responseAnaResultTreeWidget.itemChanged['QTreeWidgetItem*', 'int'].connect(
            self.responseAnaResultTreeWidgetCheckboxChanged)

    def responseAnaResultTreeWidgetCheckboxChanged(self, changeItem, colIndex):
        self.responseAnaResultTreeWidget.itemChanged['QTreeWidgetItem*', 'int'].disconnect()
        childQueue = queue.Queue()
        parentQueue = queue.Queue()
        # 判断当前的选中状态
        nowCheckState = changeItem.checkState(colIndex)
        childQueue.put(changeItem)
        parentQueue.put(changeItem)
        # 处理子节点
        while not childQueue.empty():
            tmpItem = childQueue.get()
            tmpCheckState = tmpItem.checkState(colIndex)
            # 将所有子节点设置为相同状态
            nowChildCount = tmpItem.childCount()
            for index in range(nowChildCount):
                tmpChildItem = tmpItem.child(index)
                tmpChildItem.setCheckState(colIndex, nowCheckState)
                childQueue.put(tmpChildItem)
        # 处理父节点
        while not parentQueue.empty():
            tmpItem = parentQueue.get()
            # 获取当前节点的父节点
            tmpParentItem = tmpItem.parent()
            if tmpParentItem is None:
                continue
            else:
                # 读取所有父节点的子节点，判断父节点的选中状态
                parentCheckStatus = 0
                tmpChildCount = tmpParentItem.childCount()
                tmpSum = 0
                for index in range(tmpChildCount):
                    tmpChildItem = tmpParentItem.child(index)
                    tmpSum = tmpSum + tmpChildItem.checkState(colIndex)
                tmpAvg = tmpSum / tmpChildCount
                if tmpAvg == 0:
                    parentCheckStatus = 0
                elif tmpAvg == 2:
                    parentCheckStatus = 2
                else:
                    parentCheckStatus = 1
                tmpParentItem.setCheckState(colIndex, parentCheckStatus)
                parentQueue.put(tmpParentItem)
        self.responseAnaResultTreeWidget.itemChanged['QTreeWidgetItem*', 'int'].connect(
            self.responseAnaResultTreeWidgetCheckboxChanged)

    ### 输入设置界面方法
    def createInputTabWidget(self, needTabCount):
        if needTabCount <= 0:
            needTabCount = 1
        nowTabCount = self.inputTabWidget.count()
        while nowTabCount > needTabCount:
            self.inputTabWidget.removeTab(nowTabCount - 1)
            nowTabCount = self.inputTabWidget.count()
        while nowTabCount < needTabCount:
            self.inputTabWidget.addTab(self.createInputTab(nowTabCount), "序号{}".format(nowTabCount + 1))
            nowTabCount = self.inputTabWidget.count()

    def createInputTab(self, tabIndex=1):
        tabName = "index{}_tab".format(tabIndex)
        nowTab = QtWidgets.QWidget()
        nowTab.setObjectName(tabName)
        horizontalLayout = QtWidgets.QHBoxLayout(nowTab)
        horizontalLayout.setObjectName("horizontalLayout_index{}".format(tabIndex))
        tableWidget = QtWidgets.QTableWidget(nowTab)
        tableWidget.setObjectName("tableWidget_index{}".format(tabIndex))
        tableWidget.setColumnCount(1)
        tableWidget.setHorizontalHeaderLabels(["输入值"])
        tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        horizontalLayout.addWidget(tableWidget)
        return nowTab

    def addInputListRow(self):
        nowTableWidget = self.inputTabWidget.currentWidget().children()[1]
        beforeRowCount = nowTableWidget.rowCount()
        if beforeRowCount != 0:
            # 获取前一行的第一列数据，判断前一行是否是空行
            lastRowWriteItem = nowTableWidget.item(beforeRowCount - 1, 0)
            if lastRowWriteItem is None:
                # 前一行为空行，不添加新的行
                return
            else:
                pass
        else:
            pass
        nowRowCount = beforeRowCount
        nowTableWidget.insertRow(nowRowCount)
        tempItem = myUtils.createTableItem("")
        nowTableWidget.setItem(nowRowCount, 0, tempItem)

    def deleteInputListRows(self):
        nowTableWidget = self.inputTabWidget.currentWidget().children()[1]
        selectedItems = nowTableWidget.selectedItems()
        selectedRows = [i.row() for i in selectedItems]
        selectedRows.sort(reverse=True)
        for rowIndex in selectedRows:
            nowTableWidget.removeRow(rowIndex)

    def clearInputList(self):
        nowTableWidget = self.inputTabWidget.currentWidget().children()[1]
        myUtils.clearTalbe(nowTableWidget)

    def loadInputFromFile(self):
        fileName, fileType = QFileDialog.getOpenFileName(self, "导入字典", QDir.currentPath(), "TXT Files (*.txt)")
        readStr = ""
        if fileName != "":
            with open(fileName, "r", encoding="utf-8") as fr:
                readStr = fr.read()
            readStr.replace("\r\n", "\n")
            readList = readStr.split("\n")

            # 写入当前表格
            nowTableWidget = self.inputTabWidget.currentWidget().children()[1]
            for readRow in readList:
                nowRowCount = nowTableWidget.rowCount()
                nowTableWidget.insertRow(nowRowCount)
                tempItem = myUtils.createTableItem(str(readRow))
                nowTableWidget.setItem(nowRowCount, 0, tempItem)
        else:
            pass

    ### 输出结果界面方法
    def doAddResponseToResult(self, reDic):
        # 获取值
        inputDic = reDic["input"]
        repDic = reDic["result"]
        dataDic = reDic["extraData"]
        repStatus = repDic["status"]
        reqFlag = repDic["checkFlag"]
        nowInput = dataDic["input"]
        ifEnd = dataDic["ifEnd"]
        jsonArgList = dataDic["jsonArgList"]
        reqResultStr = "成功" if reqFlag else repDic["resultStr"]
        if reqFlag:
            resultRowList = []
            pageContent = repDic["pageContent"]
            pageContent = self.anaResponseByResponseType(pageContent)
            pageJsonDic = json.loads(pageContent)
            for nowRowIndex, nowRowData in enumerate(jsonArgList):
                if nowRowIndex == 0:
                    continue
                resultRowList.append([])
                for nowColIndex, nowColData in enumerate(nowRowData):
                    nowJsonArg = nowColData
                    try:
                        evalText = "pageJsonDic" + nowJsonArg
                        nowVal = eval(evalText)
                    except:
                        nowVal = "None"
                    resultRowList[nowRowIndex - 1].append(nowVal)
        else:
            maxRowCount = 1
            resultRowList = [["None" * len(jsonArgList[0])]]
        # 写入表格
        nowTable = self.resultTable
        for nowRowIndex, nowRowList in enumerate(resultRowList):
            nowRowCount = nowTable.rowCount()
            nowTable.insertRow(nowRowCount)
            nowTable.setItem(nowRowCount, 0, myUtils.createTableItem(nowInput))
            nowTable.setItem(nowRowCount, 1, myUtils.createTableItem(repStatus))
            nowTable.setItem(nowRowCount, 2, myUtils.createTableItem(reqResultStr))
            for tmpIndex in range(len(nowRowList)):
                nowTable.setItem(nowRowCount, 3 + tmpIndex,
                                 myUtils.createTableItem(nowRowList[tmpIndex]))

        if ifEnd:
            warningStr = "已完成所有请求，请求结果请查看[输出结果]页面"
            self.writeLog(warningStr, 0)

    def exportResultTable(self):
        exportSaveCount = int(self.confDic["exportSaveCount"])

        nowTable = self.resultTable
        nowRowCount = nowTable.rowCount()
        if nowRowCount == 0:
            self.writeLog("当前无可导出数据", 1)
            return

        self.exportExcellThread = ExportExcellThread(nowTable, exportSaveCount)
        self.exportExcellThread.signal_end.connect(self.exportCompleted)
        self.exportExcellThread.signal_log.connect(self.writeLog)
        self.exportExcellThread.start()
        self.writeLog("开始导出文件")
        self.exportResultButton.setEnabled(False)

    def exportCompleted(self, result, logStr):
        if result:
            self.writeLog(logStr)
        else:
            self.writeLog(logStr, 1)
        self.exportResultButton.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainForm = Main()
    mainForm.show()
    sys.exit(app.exec_())
