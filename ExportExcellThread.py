#!/usr/bin/env python
# coding=utf-8
import copy
import traceback

import openpyxl as oxl
from PyQt5.QtCore import QThread, pyqtSignal

import myUtils
from ExportExcellUtils import ExportExcellUtils


class ExportExcellThread(QThread):
    signal_end = pyqtSignal(bool, str)
    signal_log = pyqtSignal(str)

    def __init__(self, resultTable, saveCount=10000):
        super(ExportExcellThread, self).__init__()
        self.resultTable = resultTable
        self.saveCount = saveCount
        self.notExportColIndexList = []  # 不导出的列序号，从0开始

    def run(self):
        nowTable = self.resultTable
        nowRowCount = nowTable.rowCount()
        nowColCount = nowTable.columnCount()
        nowHeader = [nowTable.horizontalHeaderItem(index).text() for index in range(nowColCount)]
        nowHeader = [item for index, item in enumerate(nowHeader) if index not in self.notExportColIndexList]

        filename = "JSON解析结果"
        filename = myUtils.updateFileNameStr(filename)
        fileFullName = filename
        resultFlag = False
        logStr = ""
        self.signal_log.emit("导出文件名为：{}".format(filename))

        # 获取所有导出数据
        rowsList = []
        for rowIndex in range(nowRowCount):
            tmpRowList = []
            for colIndex in range(nowColCount):
                if colIndex not in self.notExportColIndexList:
                    nowItem = nowTable.item(rowIndex, colIndex)
                    if nowItem is None:
                        nowItemText = "None"
                    else:
                        nowItemText = nowItem.text()
                    tmpRowList.append(nowItemText)
            rowsList.append(copy.deepcopy(tmpRowList))



        exportExcellUtils = ExportExcellUtils(saveCount=10000)  # 实例化一个导出工具类
        nowExcellFileObj = exportExcellUtils.addFile(filename)  # 添加一个excell文件，传入文件名
        nowExcellSheetObj = nowExcellFileObj.getFinalSheet()  # 获取最后一个sheet，第一个sheet会自动创建
        nowExcellSheetObj.sheetName = filename  # 设置sheet名
        nowExcellSheetObj.setHeaderList(
            exportExcellUtils.transformListToHeaderList(nowHeader))  # 设置sheet的表头，表头不用包含序号，序号会自动添加
        nowExcellSheetObj.addRows([exportExcellUtils.transformListToCellList(tmpResults) for tmpResults in rowsList])  # 传入需要写入的数据列表
        exportExcellUtils.exportExcell(0)  # 保存excell文件

        logStr = "成功保存文件"
        self.signal_end.emit(resultFlag, logStr)
