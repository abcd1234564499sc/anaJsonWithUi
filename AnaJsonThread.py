#!/usr/bin/env python
# coding=utf-8
import copy
import json

from PyQt5.QtCore import QThread, pyqtSignal

import myUtils


class AnaJsonThread(QThread):
    signal_result = pyqtSignal(list)

    def __init__(self, selectDicList=None):
        super(AnaJsonThread, self).__init__()
        self.selectDicList = selectDicList

    def setSelectDicList(self, selectDicList):
        self.selectDicList = selectDicList

    def mergeHeader(self, nowHeaderList, newHeaderStr):
        ifExist = False
        for tmpLocIndex, tmpLoc in enumerate(nowHeaderList):
            if tmpLoc == newHeaderStr[:len(tmpLoc)]:
                nowHeaderList[tmpLocIndex] = newHeaderStr
                ifExist = True
            else:
                pass
        if not ifExist:
            nowHeaderList.append(newHeaderStr)
        nowHeaderList = list(set(nowHeaderList))
        nowHeaderList.sort(key=lambda a: len(a))
        return nowHeaderList

    def run(self):
        # 根据选择的JSONKey值转换出一个用于方便的请求JSON值的字符串二维数组，格式形如["a"][1]
        selectDicList = self.selectDicList
        sortedSelectDicList = sorted(selectDicList, key=lambda a: len(a["struct"]))
        finalJsonStrList = [[[]], [0]]  # 第一个元素为header列表，第二个元素开始是数据数组，每个数据数组的第一个元素是临时数据
        reHeaderList = []
        for tmpSelectIndex, tmpSelectDic in enumerate(sortedSelectDicList):
            nowStruct = json.loads(tmpSelectDic["struct"])
            nowName = tmpSelectDic["name"]
            reHeaderList.append(nowName)
            nowLocList = []
            nowSelectDicJsonArgList = [{"value": '', "loc": []}]
            for tmpStruct in nowStruct:
                nowStructType = tmpStruct["type"]
                nowStructValue = tmpStruct["value"]
                nowListCount = tmpStruct["listCount"]
                if nowStructType == 0:
                    # 非数组的情况
                    for tmpJsonArg in nowSelectDicJsonArgList:
                        tmpJsonArg["value"] = tmpJsonArg["value"] + '["{}"]'.format(nowStructValue)
                else:
                    # 数组的情况
                    # 构建新的结果数组
                    newSelectDicJsonArgList = []
                    for tmpJsonArg in nowSelectDicJsonArgList:
                        tmpJsonArg["value"] = tmpJsonArg["value"] + '["{}"]'.format(nowStructValue)
                        for tmpIndex in range(nowListCount):
                            newJsonArg = copy.deepcopy(tmpJsonArg)
                            newJsonArg["value"] = newJsonArg["value"] + "[{}]".format(tmpIndex)
                            newJsonArg["loc"] = self.mergeHeader(newJsonArg["loc"], newJsonArg["value"])
                            newSelectDicJsonArgList.append(newJsonArg)
                    nowSelectDicJsonArgList = copy.deepcopy(newSelectDicJsonArgList)
            # 当前选项的所有JsonArg构建完成，开始与最终结果数组对比判断如何添加
            checkJsonStrList = copy.deepcopy(finalJsonStrList)
            # 将每行数据的第一个临时数据改成当前序号
            for tmpIndex in range(1, len(finalJsonStrList)):
                finalJsonStrList[tmpIndex][0] = tmpIndex - 1
            # 开始处理
            finalAddCount = 0
            for nowSelectDicJsonArg in nowSelectDicJsonArgList:
                nowLoc = nowSelectDicJsonArg["loc"]
                nowValue = nowSelectDicJsonArg["value"]
                nowAddIndex = []
                for tmpResultIndex, tmpResultLocList in enumerate(finalJsonStrList[0]):
                    if myUtils.ifTowListHasSameItem(tmpResultLocList, nowLoc):
                        # 出现相同的数组前缀，说明该项只添加至该行
                        nowAddIndex.append(tmpResultIndex)
                    else:
                        pass
                # 遍历需要添加行序号，执行添加操作
                nowAddIndex.sort(reverse=True)
                for tmpAddIndex in nowAddIndex:
                    nowSolveIndex = tmpAddIndex
                    nowResultListLen = len(finalJsonStrList[nowSolveIndex + 1])
                    if nowResultListLen - 1 >= tmpSelectIndex + 1:
                        # 复制该行数据
                        tmpLineData = copy.deepcopy(finalJsonStrList[nowSolveIndex + 1])
                        tmpHeaderData = copy.deepcopy(finalJsonStrList[0][nowSolveIndex])
                        finalJsonStrList.insert(nowSolveIndex + 1, tmpLineData)
                        finalJsonStrList[0].insert(nowSolveIndex, tmpHeaderData)
                        # 修改处理行序号
                        nowSolveIndex = nowSolveIndex + 1
                        # 将处理行修改为原始状态
                        tmpOriIndex = tmpLineData[0]
                        finalJsonStrList[nowSolveIndex + 1] = checkJsonStrList[tmpOriIndex + 1]
                        finalJsonStrList[0][nowSolveIndex] = checkJsonStrList[0][tmpOriIndex]
                    else:
                        pass
                    # 修改结果头
                    tmpLoc = copy.deepcopy(finalJsonStrList[0][nowSolveIndex])
                    for tmpNowLocStr in nowLoc:
                        tmpLoc = self.mergeHeader(tmpLoc, tmpNowLocStr)
                    finalJsonStrList[0][nowSolveIndex] = copy.deepcopy(tmpLoc)
                    # 修改对应行的数据
                    finalJsonStrList[nowSolveIndex + 1].append(nowValue)
                finalAddCount = finalAddCount + len(nowAddIndex)
            # 若没有匹配任意一行，则往所有结果行添加本次选择的所有数据
            if finalAddCount == 0:
                checkJsonStrList = copy.deepcopy(finalJsonStrList)
                # 将每行数据的第一个临时数据改成当前序号
                for tmpIndex in range(1, len(finalJsonStrList)):
                    finalJsonStrList[tmpIndex][0] = tmpIndex - 1
                tmpJsonStrList = [[]]
                for nowSelectDicJsonArg in nowSelectDicJsonArgList:
                    nowSelectLoc = nowSelectDicJsonArg["loc"]
                    nowSelectVal = nowSelectDicJsonArg["value"]
                    for tmpAddIndex in range(len(finalJsonStrList[0])):
                        nowLoc = copy.deepcopy(finalJsonStrList[0][tmpAddIndex])
                        nowData = copy.deepcopy(finalJsonStrList[tmpAddIndex + 1])
                        for tmpNowLocStr in nowSelectLoc:
                            nowLoc = self.mergeHeader(nowLoc, tmpNowLocStr)
                        nowData.append(nowSelectVal)
                        tmpJsonStrList[0].append(nowLoc)
                        tmpJsonStrList.append(copy.deepcopy(nowData))
                finalJsonStrList = copy.deepcopy(tmpJsonStrList)
            else:
                pass

        # 处理结束，处理结果并返回
        reResultList = []
        reResultList.append(reHeaderList)
        for tmpIndex in range(1, len(finalJsonStrList)):
            nowResultList = finalJsonStrList[tmpIndex][1:]
            reResultList.append(nowResultList)
        self.signal_result.emit(reResultList)
