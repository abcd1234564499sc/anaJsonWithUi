#!/usr/bin/env python
# coding=utf-8
import copy
import json
import time
from queue import Queue

from PyQt5.QtCore import QThread, pyqtSignal


class AnaJsonThread(QThread):
    signal_result = pyqtSignal(dict)

    def __init__(self):
        super(AnaJsonThread, self).__init__()
        self.queue = Queue()

    def stopThread(self):
        self.runFlag = False

    def addSelectStructList(self,packageIndex=-1, selectStructList=[],jsonObj={},headerList=[],inputStr=""):
        tmpDict = {"packageIndex":packageIndex,"selectStructList":selectStructList,"jsonObj":jsonObj,"headerList":headerList,"inputStr":inputStr}
        self.queue.put(tmpDict)

    def run(self):
        self.runFlag = True
        while self.runFlag:
            if not self.queue.empty():
                reDict = {}
                inputDic = self.queue.get()
                nowSelectStructList = inputDic["selectStructList"]
                nowPackageIndex = inputDic["packageIndex"]
                nowJsonObj = inputDic["jsonObj"]
                nowHeaderList = inputDic["headerList"]
                nowInputStr = inputDic["inputStr"]

                # 根据勾选的struct获取对应的值
                selectedJsonVaList = []
                for nowSelectStructStr in nowSelectStructList:
                    tmpSavedResultList = [nowJsonObj]
                    tmpSelectStructs = nowSelectStructStr.split(",")
                    tmpLevel = len(tmpSelectStructs)-1
                    tmpHeaderStructStr = tmpSelectStructs[-1]
                    tmpSplitedHeaderStructList = tmpHeaderStructStr.split("_")
                    tmpHeaderKey = tmpSplitedHeaderStructList[1]
                    tmpHeaderStr = f"[{tmpLevel}]{tmpHeaderKey}"
                    for tmpStructStr in tmpSelectStructs:
                        tmpSplitedStructStrList = tmpStructStr.split("_")
                        tmpParentType = tmpSplitedStructStrList[0]
                        tmpJsonKey = tmpSplitedStructStrList[1]
                        tmpType = tmpSplitedStructStrList[2]

                        if tmpParentType == "root":
                            continue
                        if tmpParentType == "list":
                            tmpResultList = []
                            for tmpSavedItem in tmpSavedResultList:
                                if type(tmpSavedItem)!=list:
                                    tmpResultList.append(None)
                                else:
                                    for tmpItem in tmpSavedItem:
                                        tmpResultList.append(tmpItem)
                            tmpSavedResultList = copy.deepcopy(tmpResultList)
                        elif tmpParentType == "dict":
                            tmpResultList = []
                            for tmpSavedItem in tmpSavedResultList:
                                try:
                                    tmpJsonVal = tmpSavedItem[tmpJsonKey]
                                except:
                                    tmpJsonVal = None
                                tmpResultList.append(tmpJsonVal)
                            tmpSavedResultList = copy.deepcopy(tmpResultList)
                        else:
                            continue

                    # 将结果中的json对象转换为字符串
                    for tmpIndex,tmpSavedResultItem in enumerate(tmpSavedResultList):
                        if type(tmpSavedResultItem) == dict or type(tmpSavedResultItem) == list:
                            tmpSavedResultList[tmpIndex] = json.dumps(tmpSavedResultItem)
                        else:
                            continue

                    tmpSavedJsonDict = {"headerStr":tmpHeaderStr,"resultList":copy.deepcopy(tmpSavedResultList)}
                    selectedJsonVaList.append(tmpSavedJsonDict)

                # 对获取的json结果列表按长度进行排序
                selectedJsonVaList.sort(key=lambda d:len(d["resultList"]))

                # 合并相同长度的结果
                mergeJsonValDict = {}
                for nowSelectedJsonValDict in selectedJsonVaList:
                    tmpHeaderStr = nowSelectedJsonValDict["headerStr"]
                    tmpResultList = nowSelectedJsonValDict["resultList"]
                    tmpResultListLength = len(tmpResultList)

                    if tmpResultListLength not in mergeJsonValDict.keys():
                        mergeJsonValDict[tmpResultListLength] = {"headerStrList":[tmpHeaderStr],"resultLists":[[result] for result in tmpResultList]}
                    else:
                        tmpAimAppendDict = mergeJsonValDict[tmpResultListLength]
                        tmpAimAppendDict["headerStrList"].append(tmpHeaderStr)
                        for tmpAimAppendResultRowIndex,tmpAimAppendResultRow in enumerate(tmpAimAppendDict["resultLists"]):
                            tmpAimAppendResultRow.append(tmpResultList[tmpAimAppendResultRowIndex])

                # 合并不同长度的结果（直接相乘）
                seconedMergeResultList = []
                seconedMergeHeaderList = []
                for tmpLen,tmpJsonValDict in mergeJsonValDict.items():
                    tmpHeaderList = tmpJsonValDict["headerStrList"]
                    tmpResultList = tmpJsonValDict["resultLists"]

                    seconedMergeHeaderList = seconedMergeHeaderList + tmpHeaderList
                    if len(seconedMergeResultList)==0:
                        seconedMergeResultList = copy.deepcopy(tmpResultList)
                    else:
                        tmpMergeList = []
                        for tmpSavedResultRow in seconedMergeResultList:
                            for tmpNowResultRow in tmpResultList:
                                tmpMergeResultRow = tmpSavedResultRow+tmpNowResultRow
                                tmpMergeList.append(tmpMergeResultRow)
                        seconedMergeResultList = copy.deepcopy(tmpMergeList)

                # 根据传入的表头对列进行排序
                finalSortedResultList = []
                if not seconedMergeHeaderList == nowHeaderList:
                    finalKeyTableDict = {}
                    for tmpIndex, tmpKey in enumerate(seconedMergeHeaderList):
                        finalKeyTableDict[tmpKey] = [row[tmpIndex] for row in seconedMergeResultList]

                    for tmpKey in nowHeaderList:
                        tmpColList = finalKeyTableDict[tmpKey]
                        if len(finalSortedResultList) == 0:
                            for tmpCol in tmpColList:
                                finalSortedResultList.append([tmpCol])
                        else:
                            for tmpColIndex, tmpCol in enumerate(tmpColList):
                                finalSortedResultList[tmpColIndex].append(tmpCol)
                else:
                    finalSortedResultList = seconedMergeResultList

                # 构建返回结果并返回
                reDict["packageIndex"] = nowPackageIndex
                reDict["resultsList"] = finalSortedResultList
                reDict["inputStr"] = nowInputStr
                self.signal_result.emit(reDict)
            else:
                time.sleep(1)
                continue