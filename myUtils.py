#!/usr/bin/env python
# coding=utf-8
import copy
import datetime
import json
import os
import re
import socket
import traceback
from queue import Queue

import openpyxl as oxl
import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
# 全局变量区域
from openpyxl.styles import Border, Side, Font, PatternFill

borderNumDic = {-1: None, 0: "thin"}


# 处理json字符串，返回一个用字典存储的树状结构，注意，该方法只能处理list中结构相同的字符串
# 返回结果字典，列表中存储一个树状结构，每个节点是一个字典的key值或者list的指代符号或者空字典，key值一定是字符串，list指代符号是该list的长度，
# 例：
# {"flag":{},"data":{5:{"id":{},"name":{}}}}
def anaJson(jsonStr):
    reStr = ""
    reDic = {}
    try:
        jsonObj = json.loads(jsonStr)
    except Exception as ex:
        reStr = "传入的字符串不符合json格式"
        return reStr, reDic
    processList = []
    processList.append({"obj": jsonObj, "saveDic": reDic})
    try:
        while len(processList) != 0:
            nowProcessDic = processList.pop()
            nowObj = nowProcessDic["obj"]
            nowSaveDic = nowProcessDic["saveDic"]
            nowType = checkObjType(nowObj)
            if nowType == 1:
                # 当前类型为字典时
                nowKeys = nowObj.keys()
                for nowKey in nowKeys:
                    nowKey = str(nowKey)
                    # 判断树状结构上是否存在相同的key
                    if nowKey in nowSaveDic.keys():
                        # 存在，则不进行处理
                        continue
                    else:
                        # 不存在，进行处理
                        nowKeyObj = nowObj[nowKey]
                        nowSaveDic[nowKey] = {}
                        processList.append({"obj": nowKeyObj, "saveDic": nowSaveDic[nowKey]})
            elif nowType == 2:
                # 当前类型为列表时
                nowLen = len(nowObj)
                nowSaveDic[nowLen] = {}
                if nowLen != 0:
                    nowKeyObj = nowObj[0]
                    processList.append({"obj": nowKeyObj, "saveDic": nowSaveDic[nowLen]})
                else:
                    pass
            else:
                # 当前类型为其他时
                pass
    except Exception as ex:
        reStr = "解析时发生异常，异常为：" + str(ex)
        reDic = {}

    return reStr, reDic


# 传入json的树状结构列表，返回一个节点字典的列表，节点字典结构如下：
# {
#   "key":节点键值,
#   "parent":父节点对象，根节点该值为{},
#   "value":该节点对应的值,
#   "location":节点的访问用nodelist，从根节点开始，结合getJsonResultByNodeList函数使用,
#   "type":节点类型，值为0，字典为1，数组为2
# }
def anaJsonTreeToNodeList(jsonTreeDic):
    resultList = []
    keyQueue = Queue()
    for tmpKey in jsonTreeDic.keys():
        keyQueue.put({"key": tmpKey, "parent": {}, "value": jsonTreeDic[tmpKey], "location": []})
    while not keyQueue.empty():
        tmpKeyItem = keyQueue.get()
        if type(tmpKeyItem["key"]) != int:
            tmpResultDic = {}
            tmpResultDic.update(tmpKeyItem)
            nowLocDic = {"value": tmpKeyItem["key"], "type": 0}  # 0表示值（包括值和字典类型）,1表示数组
            nowLoaction = copy.deepcopy(tmpKeyItem["location"])
            nowLoaction.append(nowLocDic)
            tmpResultDic["location"] = nowLoaction

            if tmpKeyItem["value"] == {}:
                tmpResultDic["type"] = 0
            else:
                tmpResultDic["type"] = 1
            resultList.append(tmpResultDic)

            for tmpKey in tmpKeyItem["value"].keys():
                tmpItem = {"key": tmpKey, "parent": tmpResultDic, "value": tmpKeyItem["value"][tmpKey],
                           "location": nowLoaction}
                keyQueue.put(tmpItem)
        else:
            # 处理数组的情况
            nowListCount = tmpKeyItem["key"]
            nowLoaction = tmpKeyItem["location"]
            nowLoaction[-1]["type"] = 1
            nowParentObj = tmpKeyItem["parent"]
            nowParentObj["type"] = 2
            nowParentObj["location"] = nowLoaction
            for tmpKey in tmpKeyItem["value"].keys():
                tmpItem = {"key": tmpKey, "parent": tmpKeyItem["parent"], "value": tmpKeyItem["value"][tmpKey],
                           "location": nowLoaction}
                keyQueue.put(tmpItem)
    return resultList


# 判断传入的对象类型，是dict返回1，是list返回2，否则返回0
def checkObjType(obj):
    retStatus = 0
    if type(obj) == dict:
        retStatus = 1
    elif type(obj) == list:
        retStatus = 2
    else:
        retStatus = 0
    return retStatus


# 根据传入的contentDic写入配置文件，若配置文件不存在会创建
# contentDic格式为：{"配置名":"配置值"}，
# 对list和dict格式的值会使用json.dumps进行转换
def writeToConfFile(filePath, contentDic):
    with open(filePath, "w+", encoding="utf-8") as fr:
        for key, value in contentDic.items():
            if isinstance(value, list) or isinstance(value, dict):
                value = json.dumps(value)
            content = "{0}={1}".format(key, value)
            fr.write(content + "\n")


# 读取配置文件，生成一个配置字典，
# 字典结构为：{"配置名":"配置值"}，
# 文件结构为：配置名=配置值，对list和dict格式的值会使用json.loads进行转换
# 配置字典的最后一项固定为"confHeader":配置名列表
def readConfFile(filePath):
    confDic = {}
    headerList = []
    with open(filePath, "r", encoding="utf-8") as fr:
        fileLines = fr.readlines()
    fileLines = [a.replace("\r\n", "\n").replace("\n", "") for a in fileLines if a != ""]
    for fileLine in fileLines:
        fileLine = fileLine.replace("\r\n", "\n").replace("\n", "")
        tempList = fileLine.split("=")
        key = tempList[0].strip()
        value = "=".join(tempList[1:]).strip()
        try:
            value = json.loads(value)
        except:
            pass
        confDic[key] = value
        headerList.append(key)
    confDic["confHeader"] = headerList

    return confDic


# 判断该字符串是否是IP，返回一个布尔值
def ifIp(matchStr):
    reFlag = True
    ipReg = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(ipReg, matchStr):
        reFlag = True
    else:
        reFlag = False
    return reFlag


# 测试指定IP的指定端口是否能联通
def connectIpPort(ip, port):
    ifConnected = False
    socketObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = socketObj.connect_ex((ip, port))
    if result == 0:
        ifConnected = True
    else:
        ifConnected = False
    return ifConnected


# 获得精确到秒的当前时间
def getNowSeconed():
    formatStr = "%Y-%m-%d %H:%M:%S"
    nowDate = datetime.datetime.now()
    nowDateStr = nowDate.strftime(formatStr)
    return nowDateStr


# 访问URL,type表示请求类型，0为GET，1为POST，2为PUT
# 返回值类型如下：
# {
# "url":传入URL,
# "resultStr":访问结果字符串,
# "checkFlag":标志是否访问成功的布尔类型变量,
# "title":访问成功时的页面标题,
# "pageContent":访问成功时的页面源码，
# "status":访问的响应码，
# "requestSeconed":访问耗时，单位为秒
# }
def requestsUrl(url, cookie={}, header={}, data={}, files=None, type=0, reqTimeout=10, readTimeout=10,
                allow_redirects=False, session=None, proxies=None):
    if session is None:
        session = requests.session()
    else:
        pass
    resDic = {}
    url = url.strip()
    url = url.strip()

    resultStr = ""
    checkedFlag = False
    status = ""
    title = ""
    reContent = ""
    totalSeconed = 0
    timeout = (reqTimeout, readTimeout)
    header = header if header != {} else {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
    }
    try:
        if type == 0:
            response = session.get(url, headers=header, verify=False, cookies=cookie, timeout=timeout,
                                   allow_redirects=allow_redirects, proxies=proxies)
        elif type == 1:
            response = session.post(url, headers=header, verify=False, cookies=cookie, data=data, files=files,
                                    timeout=timeout, allow_redirects=allow_redirects, proxies=proxies)
        elif type == 2:
            response = session.put(url, headers=header, verify=False, cookies=cookie, data=data, files=files,
                                   timeout=timeout, allow_redirects=allow_redirects, proxies=proxies)
        else:
            pass
        status = response.status_code
        totalSeconed = response.elapsed.total_seconds()
        if str(status)[0] == "2" or str(status)[0] == "3":
            # 获得页面编码
            pageEncoding = response.apparent_encoding
            # 设置页面编码
            response.encoding = pageEncoding
            # 获得页面内容
            reContent = response.text
            reTitleList = re.findall(r"<title.*?>(.+?)</title>", reContent)
            title = "成功访问，但无法获得标题" if len(reTitleList) == 0 else reTitleList[0]
            resultStr = "验证成功，标题为：{0}".format(title)
            checkedFlag = True
        else:
            resultStr = "验证失败，状态码为{0}".format(status)
            checkedFlag = False
    except Exception as e:
        resultStr = traceback.format_exc()
        checkedFlag = False

    # 构建返回结果
    resDic["url"] = url
    resDic["resultStr"] = resultStr
    resDic["checkFlag"] = checkedFlag
    resDic["title"] = title
    resDic["status"] = status
    resDic["pageContent"] = reContent
    resDic["requestSeconed"] = totalSeconed
    return resDic


# 传入一个请求包格式字符串，解析并返回一个格式化的请求包字典，用于进行requests请求
# 可以设置header字段中不读取的字段名，默认不读取Content-Length
# 返回请求包字典格式为：
# {
#   "requestType":返回请求方式，0为GET，1为POST，2为PUT，其他返回-1
#   "host":请求的域名（不包含路径部分）,
#   "uri":请求的路径（不包含域名部分）,
#   "header":请求包中的header部分，是一个字典,
#   "data":请求包中的数据行，若不存在数据行则返回一个空字符串,
#   "cookie":请求包中的cookie,是字典类型变量
# }
def analysisPacketFromTxt(packetTxt, notReadKeys=["Content-Length"]):
    reDic = {}
    requestTypeDic = {"get": 0, "post": 1, "put": 2}
    # 解析报文内容
    packetTxt = packetTxt.replace("\r\n", "\n")
    packetContents = packetTxt.split("\n")
    # 判断请求方式和请求地址
    requestTypeTxt = packetContents[0].split(" ")[0].lower()
    if requestTypeTxt in requestTypeDic.keys():
        requestType = requestTypeDic[requestTypeTxt]
    else:
        requestType = -1
    uri = packetContents[0].split(" ")[1]
    host = ""
    cookieStr = ""

    # 生成header和data行的数据
    header = {}
    dataLineContent = ""
    for index in range(1, len(packetContents)):
        nowLine = packetContents[index]
        nowLine = nowLine.replace("\n", "")
        # 发现当前行为空行，且不是数据包的最后一行，判定下面的内容中存在数据行,执行完后结束循环
        if nowLine == "" and index != len(packetContents) - 1:
            for tmpIndex in range(1, len(packetContents) - index):
                tmpLine = packetContents[index + 1].replace("\n", "")
                if tmpLine == "":
                    continue
                else:
                    dataLineContent = tmpLine
                    break
            break
        tempArr = nowLine.split(":")
        nowKey = tempArr[0]
        nowValue = ":".join(tempArr[1:]).strip()

        if nowKey.lower() == "cookie":
            cookieStr = nowValue
            continue

        if nowKey.lower() == "host":
            host = nowValue
            continue

        if nowKey not in notReadKeys:
            header.update({nowKey: nowValue})

    # 处理cookie字符串
    cookie = {}
    tmpList = cookieStr.split(";")
    for tmpStr in tmpList:
        tmpCookieItem = tmpStr.split("=")
        nowKey = tmpCookieItem[0]
        nowValue = "=".join(tmpCookieItem[1:])
        cookie[nowKey] = nowValue

    # 生成返回结果字典
    reDic["requestType"] = requestType
    reDic["host"] = host
    reDic["uri"] = uri
    reDic["header"] = header
    reDic["data"] = dataLineContent
    reDic["cookie"] = cookie
    return reDic


# 创建一个QTableWidgetItem对象，传入文本参数text，以及verAlign和horAlign两个整形参数控制文本位置
# verAlign的值含义如下：-1 靠左、0 居中、1 靠右
# horAlign的值含义如下：-1 靠下、0 居中、1 靠上
def createTableItem(text, verAlign=0, horAlign=0):
    tmpItem = QTableWidgetItem(str(text))
    verAlignDic = {-1: Qt.AlignLeft, 0: Qt.AlignVCenter, 1: Qt.AlignRight}
    horAlignDic = {-1: Qt.AlignBottom, 0: Qt.AlignHCenter, 1: Qt.AlignTop}
    tmpItem.setTextAlignment(verAlignDic[verAlign] | horAlignDic[horAlign])
    return tmpItem


# 传入一个QTableWidget对象，清空这个表格
def clearTalbe(tableObject):
    while tableObject.rowCount() != 0:
        tableObject.removeRow(tableObject.rowCount() - 1)


# 用于进行动态坐标系加1，传入一个当前坐标值的列表，以及一个最大坐标系长度的列表，按从后到前的顺序进行计算（例子：多重for嵌套）
# 返回一个布尔类型参数ifAddFlag和一个进行坐标系加法后的坐标值列表，当ifAddFlag为True时表示进行了坐标系加法，否则表示所有坐标已遍历完
def coordinatePlus(nowCoordinate, maxCoordinate):
    ifAddFlag = False
    nowAddIndex = -1
    while not ifAddFlag:
        if len(nowCoordinate) + nowAddIndex == -1:
            ifAddFlag = False
            break
        else:
            nowCoordinateItem = nowCoordinate[nowAddIndex]
            nowMaxCoordinateItem = maxCoordinate[nowAddIndex]
            if nowCoordinateItem == nowMaxCoordinateItem:
                tmpAddIndex = nowAddIndex
                while tmpAddIndex != 0:
                    nowCoordinate[tmpAddIndex] = 0
                    tmpAddIndex = tmpAddIndex + 1
                nowAddIndex = nowAddIndex - 1
            else:
                nowCoordinate[nowAddIndex] = nowCoordinate[nowAddIndex] + 1
                ifAddFlag = True
    return ifAddFlag, nowCoordinate


# nodeList 的结构为：{"value":键值,"type":类型，0为值，1为数组}
# 根据传入的nodeList,获取对应的值，返回一个list
def getJsonResultByNodeList(jsonContent, nodeList):
    finalResultList = []
    parentResultQueue = []
    nowResultQueue = []
    parentResultQueue.append(jsonContent)
    try:
        for tmpIndex, node in enumerate(nodeList):
            nowVal = node["value"]
            nowType = int(node["type"])
            while not len(parentResultQueue) == 0:
                tmpParentObj = parentResultQueue.pop(0)
                if nowType == 0:
                    tmpNowResultObj = tmpParentObj[nowVal]
                    nowResultQueue.append(tmpNowResultObj)
                else:
                    for tmpNowResultObj in tmpParentObj[nowVal]:
                        nowResultQueue.append(tmpNowResultObj)

            parentResultQueue = copy.deepcopy(nowResultQueue)
            nowResultQueue = []
        finalResultList = copy.deepcopy(parentResultQueue)
    except:
        finalResultList = [None]
    return finalResultList


# 获得excell的常用样式
def getExcellStyleDic():
    styleDic = {}

    # 单线边框
    thinBorder = Border(left=Side(border_style='thin', color='000000'),
                        right=Side(border_style='thin', color='000000'),
                        top=Side(border_style='thin', color='000000'),
                        bottom=Side(border_style='thin', color='000000'))

    # 文字居中
    alignStyle = oxl.styles.Alignment(horizontal='center', vertical='center')
    leftStyle = oxl.styles.Alignment(horizontal='left', vertical='center')
    rightStyle = oxl.styles.Alignment(horizontal='right', vertical='center')

    # 加粗字体
    boldFont = Font(bold=True)
    hyperLinkFont = Font(color='0000FF')
    underLineFont = Font(underline='single')

    styleDic["thin"] = thinBorder
    styleDic["align"] = alignStyle
    styleDic["bold"] = boldFont
    styleDic["left"] = leftStyle
    styleDic["right"] = rightStyle
    styleDic["link"] = hyperLinkFont
    styleDic["underLine"] = underLineFont
    return styleDic


# 写入一个标准的excell表头（居中，单线框，加粗）
def writeExcellHead(ws, headArr):
    # 获得常用样式
    styleDic = getExcellStyleDic()
    # 写入表头
    for index, head in enumerate(headArr):
        ws.cell(row=1, column=index + 1).value = head
        ws.cell(row=1, column=index + 1).border = styleDic["thin"]
        ws.cell(row=1, column=index + 1).alignment = styleDic["align"]
        ws.cell(row=1, column=index + 1).font = styleDic["bold"]
    return ws


# 写入一个内容单元格
# borderNum表示该单元格的边框对象，其值可查询全局变量styleDic
# ifAlign是一个boolean对象，True表示居中
# hyperLink表示该单元格指向的链接，默认为None，表示不指向任何链接
# fgColor表示该单元格的背景颜色，为一个RGB16进制字符串，默认为“FFFFFF”（白色）
# otherAlign表示当ifAlign为False时指定的其他对齐方式，是一个数字型变量，默认为None，当其为0时表示左对齐，1为右对齐
def writeExcellCell(ws, row, column, value, borderNum, ifAlign, hyperLink=None, fgColor="FFFFFF", otherAlign=None):
    value = str(value)
    ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
    value = ILLEGAL_CHARACTERS_RE.sub("", value)
    # 获得常用样式
    styleDic = getExcellStyleDic()
    # 获得指定单元格
    aimCell = ws.cell(row=row, column=column)
    # 设置值
    aimCell.value = value
    # 设置边框
    styleObjKey = borderNumDic[borderNum]
    if not styleObjKey:
        pass;
    else:
        styleObj = styleDic[styleObjKey]
        aimCell.border = styleObj
    # 设置居中
    if ifAlign:
        aimCell.alignment = styleDic["align"]
    elif otherAlign is not None:
        otherAlign = int(otherAlign)
        if otherAlign == 0:
            aimCell.alignment = styleDic["left"]
        else:
            aimCell.alignment = styleDic["right"]
    else:
        pass

    # 设置超链接
    if hyperLink:
        # 写入超链接
        aimCell.hyperlink = hyperLink
        # 设置当前单元格字体颜色为深蓝色，并添加下划线
        aimCell.font = styleDic["link"]
    else:
        pass

    # 设置填充颜色
    fill = PatternFill("solid", fgColor=fgColor)
    aimCell.fill = fill

    return ws


# 写入一个空格单元格，防止上一列文本超出
def writeExcellSpaceCell(ws, row, column):
    # 设置值
    ws.cell(row=row, column=column).value = " "

    return ws


# 设置excell的列宽
def setExcellColWidth(ws, colWidthArr):
    for colWidindex in range(len(colWidthArr)):
        ws.column_dimensions[chr(ord("A") + colWidindex)].width = colWidthArr[colWidindex]

    return ws


# 保存excell文件
def saveExcell(wb, saveName):
    savePath = ""
    # 处理传入的文件名
    saveName = saveName.split(".")[0] + ".xlsx"
    savePath = "{0}\\{1}".format(os.getcwd(), saveName)

    # 检测当前目录下是否有该文件，如果有则清除以前保存文件
    if os.path.exists(savePath):
        deleteFile(savePath)
    wb.save(savePath)
    return True


# 删除指定路径的文件,传入一个绝对路径,返回一个布尔变量以及一个字符串变量，
# 布尔变量为True表示是否删除成功,若为False则字符串变量中写入错误信息
def deleteFile(filePath):
    deleteFlag = True
    reStr = ""
    if os.path.exists(filePath):
        try:
            os.remove(filePath)
        except Exception as ex:
            reStr = "删除失败，失败信息为：{0}".format(ex)
            deleteFlag = False
    else:
        reStr = "未找到指定路径的文件"
        deleteFlag = False
    return deleteFlag, reStr


# 将传入的字符串修改为符合windows文件名规范的字符串
def updateFileNameStr(oriStr):
    resultStr = oriStr
    # 替换换行符
    resultStr = resultStr.replace("\r\n", "\n").replace("\n", "")
    # 将违法字符替换为下划线
    notAllowCharList = ["\\", "/", ":", "*", "?", "\"", "<", ">", "|", "-"]
    for nowNotAllowChar in notAllowCharList:
        resultStr = resultStr.replace(nowNotAllowChar, "_")
    return resultStr


# 输入一个JSON字符串，返回一个包含所有结果的列表
def getJsonResultList(jsonContent):
    jsonObj = json.loads(jsonContent)
    reStr, jsonDic = anaJson(jsonContent)
    resultList = [["[]"], ["[]"]]  # 第一个数组存储键值，后面的每个数组的第一位为键值
    keyQueue = Queue()
    for tmpKey in jsonDic.keys():
        keyQueue.put(
            {"key": tmpKey, "parent": {}, "value": jsonDic[tmpKey], "location": [], "resultLoc": "[]",
             "jsonValue": jsonObj})
    while not keyQueue.empty():
        tmpKeyItem = keyQueue.get()
        if type(tmpKeyItem["key"]) != int:
            tmpResultDic = {}
            tmpResultDic.update(tmpKeyItem)
            nowLocDic = {"value": tmpKeyItem["key"], "type": 0}  # 0表示值（包括值和字典类型）,1表示数组

            if len(tmpKeyItem["value"].keys()) == 1 and type(list(tmpKeyItem["value"].keys())[0]) == int:
                tmpResultDic["type"] = 2
                nowLocDic["type"] = 1
            elif type(tmpKeyItem["value"]) == dict:
                tmpResultDic["type"] = 1
            else:
                tmpResultDic["type"] = 0
            resultLocationStr = tmpKeyItem["resultLoc"]
            nowLoaction = copy.deepcopy(tmpKeyItem["location"])
            nowLoaction.append(nowLocDic)
            tmpResultDic["location"] = nowLoaction
            tmpResultDic["resultLoc"] = tmpKeyItem["resultLoc"]
            jsonVal = tmpKeyItem["jsonValue"][tmpKeyItem["key"]]
            tmpResultDic["jsonValue"] = jsonVal

            resultListIndexList = []
            for tmpIndex, tmpKey in enumerate(resultList[0]):
                if tmpKey[:len(resultLocationStr)] == resultLocationStr:
                    resultListIndexList.append(tmpIndex)

            for tmpIndex in resultListIndexList:
                tmpResultList = resultList[tmpIndex + 1]
                tmpResultList.append(tmpResultDic)

            for tmpKey in tmpKeyItem["value"].keys():
                tmpItem = {"key": tmpKey, "parent": tmpResultDic, "value": tmpKeyItem["value"][tmpKey],
                           "location": nowLoaction, "resultLoc": resultLocationStr, "jsonValue": jsonVal}
                keyQueue.put(tmpItem)
        else:
            # 处理数组的情况
            nowListCount = tmpKeyItem["key"]
            nowLoaction = tmpKeyItem["location"]
            nowResultLocation = tmpKeyItem["resultLoc"]
            if nowListCount != 0:
                # 修改resultList
                tmpResultList = [[]]
                for tmpIndex, tmpKey in enumerate(resultList[0]):
                    for tmpAddIndex in range(nowListCount):
                        nowHeader = tmpKey + "[{}]".format(str(tmpAddIndex))
                        # 修改表头
                        tmpResultList[0].append(nowHeader)
                        # 修改数据
                        tmpDataList = copy.deepcopy(resultList[tmpIndex + 1])
                        tmpDataList[0] = nowHeader
                        tmpResultList.append(tmpDataList)
                resultList = copy.deepcopy(tmpResultList)
                nowJsonVal = tmpKeyItem["jsonValue"] if type(tmpKeyItem["jsonValue"]) == list else []
                # 将数组中的元素加入队列
                for tmpKey in tmpKeyItem["value"].keys():
                    for tmpIndex in range(len(nowJsonVal)):
                        tmpResultLocation = nowResultLocation + "[{}]".format(str(tmpIndex))
                        tmpJsonVal = nowJsonVal[tmpIndex]
                        tmpValue = tmpKeyItem["value"][tmpKey]
                        if tmpKey not in tmpJsonVal.keys():
                            tmpJsonVal.update({tmpKey: "None"})
                            tmpValue = {}
                        tmpItem = {"key": tmpKey, "parent": tmpKeyItem["parent"], "value": tmpValue,
                                   "location": nowLoaction, "resultLoc": tmpResultLocation,
                                   "jsonValue": tmpJsonVal}
                        keyQueue.put(tmpItem)
            else:
                pass

    # 处理返回结果
    reResultDic = {}
    for index in range(1, len(resultList)):
        nowResultItem = resultList[index]
        for tmpIndex in range(1, len(nowResultItem)):
            nowTmpResultDic = nowResultItem[tmpIndex]
            nowResultVal = nowTmpResultDic["jsonValue"]
            nowLoc = nowTmpResultDic["location"]
            nowLocStr = json.dumps(nowLoc)
            if nowLocStr in reResultDic.keys():
                reResultDic[nowLocStr].append(nowResultVal)
            else:
                reResultDic[nowLocStr] = [nowResultVal]
    return reResultDic

def ifTowListHasSameItem(list1,list2):
    reFlag = False
    for item1 in list1:
        for item2 in list2:
            if item1 == item2:
                reFlag = True
                break
            else:
                pass
        if reFlag:
            break
        else:
            pass
    return reFlag
