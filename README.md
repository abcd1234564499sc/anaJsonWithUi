# anaJsonWithUi
 
用于解析JSON格式相应报文，通过修改请求报文中的字段（通常是page），批量请求并解析返回的JSON格式数据，最后目的是提取返回值中的特定字段   
使用界面库：pyQt5    
使用核心库：json、requests    
使用可执行程序打包库：pyinstaller    
    
使用说明：    
1、在报文处理页面输入报文    
2、点击解析结果按钮，成功会在返回值解析处按json格式节点生成可勾选项，失败会打印日志    
3、返回报文处理页面，选择需要批量输入的部分，点击添加标识按钮生成标识，也可不生成标识，代表不使用输入，只请求原始报文一次    
4、进入输入设置页面，根据生成的标识数量会自动调整该页面的tab数，按照需要输入或导入输入值    
5、返回报文处理页面，点击批量输入按钮，开始请求，请求结果会显示在输出结果页面    
    
程序截图如下：    
![报文处理页面](https://github.com/abcd1234564499sc/anaJsonWithUi/blob/main/img/1.jpg "报文处理页面")    
![返回值解析页面](https://github.com/abcd1234564499sc/anaJsonWithUi/blob/main/img/2.jpg "返回值解析页面")    
![输入设置页面](https://github.com/abcd1234564499sc/anaJsonWithUi/blob/main/img/3.jpg "输入设置页面")    
![输出结果页面](https://github.com/abcd1234564499sc/anaJsonWithUi/blob/main/img/4.jpg "输出结果页面")    
![代理设置页面](https://github.com/abcd1234564499sc/anaJsonWithUi/blob/main/img/5.jpg "代理设置页面")    
