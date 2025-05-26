#!/usr/bin/env python
# coding=utf-8
import copy
import json
import time
from queue import Queue

from PyQt5.QtCore import QThread, pyqtSignal

import myUtils


class AnaJsonThread(QThread):
    signal_result = pyqtSignal(dict)

    def __init__(self):
        super(AnaJsonThread, self).__init__()
        self.queue = Queue()
        self.splitChar = myUtils.getSplitChar()

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
                    tmpSavedVisitLinkDictList = [{}]
                    tmpSelectStructs = nowSelectStructStr.split(",")
                    tmpLevel = len(tmpSelectStructs)-1
                    tmpHeaderStructStr = tmpSelectStructs[-1]
                    tmpSplitedHeaderStructList = tmpHeaderStructStr.split(self.splitChar)
                    tmpHeaderKey = tmpSplitedHeaderStructList[1]
                    tmpHeaderStr = f"[{tmpLevel}]{tmpHeaderKey}"
                    for tmpStructIndex,tmpStructStr in enumerate(tmpSelectStructs):
                        tmpSplitedStructStrList = tmpStructStr.split(self.splitChar)
                        tmpParentType = tmpSplitedStructStrList[0]
                        tmpJsonKey = tmpSplitedStructStrList[1]
                        tmpType = tmpSplitedStructStrList[2]

                        if tmpParentType == "root":
                            continue
                        if tmpParentType == "list":
                            tmpResultList = []
                            tmpVisitLinkDictList = []
                            for tmpSavedIndex,tmpSavedItem in enumerate(tmpSavedResultList):
                                if type(tmpSavedItem)!=list:
                                    tmpResultList.append(None)
                                    tmpVisitLinkDictList.append(None)
                                else:
                                    for tmpSavedListIndex,tmpItem in enumerate(tmpSavedItem):
                                        tmpResultList.append(tmpItem)
                                        # 更新JSON访问链列表
                                        tmpUpdateVisitLinkDict = copy.deepcopy(tmpSavedVisitLinkDictList[tmpSavedIndex])
                                        tmpVisitLinkHeader = f"[{tmpStructIndex}]{tmpJsonKey}"
                                        tmpUpdateVisitLinkDict[tmpVisitLinkHeader] = json.dumps(tmpItem)
                                        tmpVisitLinkDictList.append(tmpUpdateVisitLinkDict)
                            tmpSavedResultList = copy.deepcopy(tmpResultList)
                            tmpSavedVisitLinkDictList = copy.deepcopy(tmpVisitLinkDictList)
                        elif tmpParentType == "dict":
                            tmpResultList = []
                            tmpVisitLinkDictList = []
                            for tmpSavedIndex,tmpSavedItem in enumerate(tmpSavedResultList):
                                try:
                                    tmpJsonVal = tmpSavedItem[tmpJsonKey]
                                except:
                                    tmpJsonVal = None
                                tmpResultList.append(tmpJsonVal)
                                # 更新JSON访问链列表
                                tmpUpdateVisitLinkDict = copy.deepcopy(tmpSavedVisitLinkDictList[tmpSavedIndex])
                                tmpVisitLinkHeader = f"[{tmpStructIndex}]{tmpJsonKey}"
                                tmpUpdateVisitLinkDict[tmpVisitLinkHeader] = json.dumps(tmpJsonVal)
                                tmpVisitLinkDictList.append(tmpUpdateVisitLinkDict)

                            tmpSavedResultList = copy.deepcopy(tmpResultList)
                            tmpSavedVisitLinkDictList = copy.deepcopy(tmpVisitLinkDictList)
                        else:
                            continue

                    # 将结果中的json对象转换为字符串
                    for tmpIndex,tmpSavedResultItem in enumerate(tmpSavedResultList):
                        if type(tmpSavedResultItem) == dict or type(tmpSavedResultItem) == list:
                            tmpSavedResultList[tmpIndex] = json.dumps(tmpSavedResultItem)
                        else:
                            continue

                    tmpSavedJsonDict = {"headerLevel":int(tmpLevel),"headerStr":tmpHeaderStr,"resultList":copy.deepcopy(tmpSavedResultList),"visitLinkDictList":copy.deepcopy(tmpSavedVisitLinkDictList) }
                    selectedJsonVaList.append(tmpSavedJsonDict)

                mergedResultList = self.mergeSelectedJsonVaList(selectedJsonVaList)
                sortedResultList = self.createResultListWithHeaderList(mergedResultList,nowHeaderList)

                # # 对获取的json结果列表按headerLevel进行升序排序
                # selectedJsonVaList.sort(key=lambda d:len(d["resultList"]))
                #
                # # 合并相同长度的结果
                # mergeJsonValDict = {}
                # for nowSelectedJsonValDict in selectedJsonVaList:
                #     tmpHeaderStr = nowSelectedJsonValDict["headerStr"]
                #     tmpResultList = nowSelectedJsonValDict["resultList"]
                #     tmpResultListLength = len(tmpResultList)
                #
                #     if tmpResultListLength not in mergeJsonValDict.keys():
                #         mergeJsonValDict[tmpResultListLength] = {"headerStrList":[tmpHeaderStr],"resultLists":[[result] for result in tmpResultList]}
                #     else:
                #         tmpAimAppendDict = mergeJsonValDict[tmpResultListLength]
                #         tmpAimAppendDict["headerStrList"].append(tmpHeaderStr)
                #         for tmpAimAppendResultRowIndex,tmpAimAppendResultRow in enumerate(tmpAimAppendDict["resultLists"]):
                #             tmpAimAppendResultRow.append(tmpResultList[tmpAimAppendResultRowIndex])
                #
                # # 合并不同长度的结果（直接相乘）
                # seconedMergeResultList = []
                # seconedMergeHeaderList = []
                # for tmpLen,tmpJsonValDict in mergeJsonValDict.items():
                #     tmpHeaderList = tmpJsonValDict["headerStrList"]
                #     tmpResultList = tmpJsonValDict["resultLists"]
                #
                #     seconedMergeHeaderList = seconedMergeHeaderList + tmpHeaderList
                #     if len(seconedMergeResultList)==0:
                #         seconedMergeResultList = copy.deepcopy(tmpResultList)
                #     else:
                #         tmpMergeList = []
                #         for tmpSavedResultRow in seconedMergeResultList:
                #             for tmpNowResultRow in tmpResultList:
                #                 tmpMergeResultRow = tmpSavedResultRow+tmpNowResultRow
                #                 tmpMergeList.append(tmpMergeResultRow)
                #         seconedMergeResultList = copy.deepcopy(tmpMergeList)
                #

                #
                # 构建返回结果并返回
                reDict["packageIndex"] = nowPackageIndex
                reDict["resultsList"] = sortedResultList
                reDict["inputStr"] = nowInputStr
                self.signal_result.emit(reDict)
            else:
                time.sleep(1)
                continue

    def mergeSelectedJsonVaList(self,selectedJsonVaList):
        reList = []
        tmpMergedResultDict = {}
        tmpMergedJsonValList = copy.deepcopy(selectedJsonVaList)

        while len(tmpMergedJsonValList)>0:
            # 获取当前所有的headerLevel
            tmpHeaderLevelList = list(set([d["headerLevel"] for d in tmpMergedJsonValList]))
            # 对获取到的列表进行降序排序
            tmpHeaderLevelList.sort(reverse=True)

            # 获取当前需要处理的level
            tmpSolvedLevel = tmpHeaderLevelList[0]

            # 将tmpMergedJsonValList转换为一个以headerStr为key的字典
            tmpMergedJsonValDict = {d["headerStr"]: d for d in tmpMergedJsonValList}
            # 为字典添加一个root节点(若不存在)
            # tmpRootHeaderStr = "[0]root"
            # if tmpRootHeaderStr not in tmpMergedJsonValDict.keys():
            #     tmpMergedJsonValDict[tmpRootHeaderStr] = {"headerLevel": 0, "headerStr": tmpRootHeaderStr,
            #                                               "resultList": [], "visitLinkDictList": []}

            # 构造一个headerStr列表，并按headerLevel降序排序
            tmpAllHeaderStrList = list(tmpMergedJsonValDict.keys())
            tmpAllHeaderStrList.sort(reverse=True)

            # 遍历tmpMergedJsonValList，提取需要处理级别的数据
            tmpSolveJsonValList = []
            for tmpJsonValDict in tmpMergedJsonValList:
                tmpJsonValHeaderLevel = tmpJsonValDict["headerLevel"]
                if tmpJsonValHeaderLevel != tmpSolvedLevel:
                    continue
                else:
                    tmpHeaderStr = tmpJsonValDict["headerStr"]
                    tmpPopedJsonValDict = tmpMergedJsonValDict.pop(tmpHeaderStr)
                    tmpSolveJsonValList.append(tmpPopedJsonValDict)

            # 合并同级元素
            tmpSameLevelMegedResultDict = {}
            for tmpSolvedIndex,tmpSolveJsonValDict in enumerate(tmpSolveJsonValList):
                tmpValHeaderStr = tmpSolveJsonValDict["headerStr"]

                for tmpItemIndex,tmpSolveVisitLinkDict in enumerate(tmpSolveJsonValDict["visitLinkDictList"]):
                    tmpCheckVisitLinkDict = copy.deepcopy(tmpSolveVisitLinkDict)
                    tmpCheckVisitLinkDict.pop(tmpValHeaderStr)
                    tmpCheckVisitLinkDictStr = json.dumps(tmpCheckVisitLinkDict)
                    if tmpCheckVisitLinkDictStr not in tmpSameLevelMegedResultDict.keys():
                        tmpSameLevelMegedResultDict[tmpCheckVisitLinkDictStr] = {"headerStrList":[tmpValHeaderStr],"resultList":[tmpSolveJsonValDict["resultList"][tmpItemIndex]]}
                    else:
                        tmpSameLevelMegedResultDict[tmpCheckVisitLinkDictStr]["headerStrList"].append(tmpValHeaderStr)
                        tmpSameLevelMegedResultDict[tmpCheckVisitLinkDictStr]["resultList"].append(tmpSolveJsonValDict["resultList"][tmpItemIndex])

            if len(tmpMergedResultDict.keys())==0:
                # 当前最终结果字典为空，直接使用合并同级的结果覆盖结果字典
                tmpMergedResultDict = copy.deepcopy(tmpSameLevelMegedResultDict)
            else:
                # 根据结果字典存储的访问链，判断当前元素是否为存储子级的父级
                tmpMergedFinalResultDict = {}
                for tmpSameLevelVisitLinkDictStr,tmpSameLevelResultItem in tmpSameLevelMegedResultDict.items():
                    tmpIfHasParentItemFlag = False
                    for tmpFinalResultVisitLinkDictStr,tmpFinalResultDict in tmpMergedResultDict.items():
                        tmpCheckSameLevelVisitLinkDictStr = tmpSameLevelVisitLinkDictStr[:-1]
                        if tmpFinalResultVisitLinkDictStr.startswith(tmpCheckSameLevelVisitLinkDictStr):
                            # 为父级，直接合并结果
                            tmpWriteKey = self.createKeyInDictWithBase(tmpSameLevelVisitLinkDictStr,tmpMergedFinalResultDict)
                            tmpMergedFinalResultDict[tmpWriteKey] = {"headerStrList": tmpSameLevelResultItem["headerStrList"]+tmpFinalResultDict["headerStrList"],
                             "resultList": tmpSameLevelResultItem["resultList"]+tmpFinalResultDict["resultList"]}
                            tmpIfHasParentItemFlag = True
                        else:
                            continue
                    if not tmpIfHasParentItemFlag:
                        # 当前存储结果中不存在父级，将结果相乘
                        for tmpFinalResultVisitLinkDictStr, tmpFinalResultDict in tmpMergedResultDict.items():
                            tmpMergedFinalResultDict[tmpSameLevelVisitLinkDictStr] = {
                                "headerStrList": tmpSameLevelResultItem["headerStrList"] + tmpFinalResultDict[
                                    "headerStrList"],
                                "resultList": tmpSameLevelResultItem["resultList"] + tmpFinalResultDict["resultList"]}
                # 将构造后的结果字典覆盖全局结果字典
                tmpMergedResultDict = copy.deepcopy(tmpMergedFinalResultDict)
            # 将tmpMergedJsonValDict转换回list并覆盖tmpMergedJsonValList
            tmpMergedJsonValList = [tmpVal for tmpKey,tmpVal in tmpMergedJsonValDict.items()]
        # 将结果字典转换为数组
        reResultList = [tmpDict for tmpKey,tmpDict in tmpMergedResultDict.items()]

        return reResultList

    def createKeyInDictWithBase(self,baseKey,aimDict):
        tmpIndex = 1
        while True:
            tmpKey = f"{baseKey}_{tmpIndex}"
            if tmpKey not in aimDict.keys():
                break
            else:
                tmpIndex+=1
                continue
        return f"{baseKey}_{tmpIndex}"

    def createResultListWithHeaderList(self,oriResultList,headerList):
        reResultList = []

        for tmpResultDict in oriResultList:
            tmpHeaderStrList = tmpResultDict["headerStrList"]
            tmpResultList = tmpResultDict["resultList"]
            tmpWriteRowList = []

            for tmpColIndex,tmpColHeaderStr in enumerate(headerList):
                if tmpColHeaderStr not in tmpHeaderStrList:
                    tmpWriteRowList.append("None")
                else:
                    tmpHeaderIndex = tmpHeaderStrList.index(tmpColHeaderStr)
                    tmpWriteRowList.append(tmpResultList[tmpHeaderIndex])
            reResultList.append(copy.deepcopy(tmpWriteRowList))
        return reResultList

















