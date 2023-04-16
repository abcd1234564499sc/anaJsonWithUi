#!/usr/bin/env python
# coding=utf-8
import traceback

import openpyxl as oxl
from PyQt5.QtCore import QThread, pyqtSignal

import myUtils


class ExportExcellThread(QThread):
    signal_end = pyqtSignal(bool, str)
    signal_log = pyqtSignal(str)

    def __init__(self, resultTable, saveCount=1000):
        super(ExportExcellThread, self).__init__()
        self.resultTable = resultTable
        self.saveCount = saveCount
        self.notExportColIndexList = [2]  # 不导出的列序号，从0开始

    def run(self):
        nowTable = self.resultTable
        nowRowCount = nowTable.rowCount()
        nowColCount = nowTable.columnCount()
        nowHeader = [nowTable.horizontalHeaderItem(index).text() for index in range(nowColCount)]
        nowHeader = ["序号"] + [item for index, item in enumerate(nowHeader) if index not in self.notExportColIndexList]

        filename = "导出文件 " + myUtils.getNowSeconed()
        filename = myUtils.updateFileNameStr(filename)
        resultFlag = False
        logStr = ""
        self.signal_log.emit("导出文件名为：{}".format(filename))

        try:
            # 创建一个excell文件对象
            wb = oxl.Workbook()
            # 创建URL扫描结果子表
            ws = wb.active
            ws.title = "JSON返回值请求结果"
            # 创建表头
            myUtils.writeExcellHead(ws, nowHeader)

            # 遍历当前结果
            self.signal_log.emit("开始导出URL扫描结果")
            for rowIndex in range(nowRowCount):
                if rowIndex % self.saveCount == 0:
                    minIndex = rowIndex + 1
                    maxIndex = rowIndex + self.saveCount if nowRowCount > rowIndex + self.saveCount else nowRowCount
                    tmpLogStr = "正在导出{0}-{1}行数据".format(minIndex, maxIndex)
                    self.signal_log.emit(tmpLogStr)
                else:
                    pass
                myUtils.writeExcellCell(ws, rowIndex + 2, 1, str(rowIndex + 1), 0, True)
                exportColIndex = 2
                for colIndex in range(nowColCount):
                    if colIndex not in self.notExportColIndexList:
                        nowItemText = nowTable.item(rowIndex, colIndex).text()

                        # 将值写入excell对象
                        myUtils.writeExcellCell(ws, rowIndex + 2, exportColIndex, nowItemText, 0, True)
                        exportColIndex = exportColIndex + 1
                    else:
                        continue
                myUtils.writeExcellSpaceCell(ws, rowIndex + 2, exportColIndex)

                # 指定数量行保存一次
                if rowIndex != 0 and rowIndex % self.saveCount == 0:
                    myUtils.saveExcell(wb, saveName=filename)
                    wb = oxl.open(filename)
                    ws = wb.get_sheet_by_name(wb.get_sheet_names()[0])

            # 设置列宽
            colWidthArr = [7, 20, 8]
            for colIndex in range(nowColCount - 1):
                colWidthArr.append(30)
            myUtils.setExcellColWidth(ws, colWidthArr)

            myUtils.saveExcell(wb, saveName=filename)
            resultFlag = True
            logStr = "成功保存文件：{0}.xlsx 至当前文件夹".format(filename)
            self.signal_end.emit(resultFlag, logStr)
        except Exception as ex:
            resultFlag = False
            logStr = "保存文件失败，报错信息为：{0}".format(traceback.format_exc())
            self.signal_end.emit(resultFlag, logStr)
