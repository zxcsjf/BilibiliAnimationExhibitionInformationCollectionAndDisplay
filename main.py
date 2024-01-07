import requests
import time
import re
import os
import threading
import urllib
from urllib import parse
import pandas as pd  # 用于数据输出
from jsonsearch import JsonSearch

areas = [
    {"name": "上海", "code": 310100},
    {"name": "杭州", "code": 330100},
    {"name": "苏州", "code": 320500}
]
typeLists = ['全部类型', '演出', '展览', '本地生活']
pageNum = 4

resultFolder = '漫展信息/'


def DF2Excel(data_path, data_list, sheet_name_list):
    '''将多个dataframe 保存到同一个excel 的不同sheet 上
    参数：
    data_path：str
        需要保存的文件地址及文件名
    data_list：list
        需要保存到excel的dataframe
    sheet_name_list：list
        sheet name 每个sheet 的名称
    '''
    if (os.path.exists(data_path)):
        os.remove(data_path)
    write = pd.ExcelWriter(data_path)
    for da, sh_name in zip(data_list, sheet_name_list):
        da.to_excel(write, sheet_name=sh_name, header=None)

    # 必须运行write.save()，不然不能输出到本地
    write._save()


def getAllInfo():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 SLBrowser/8.0.0.9231 SLBChan/105',
        'Cookie': 'HMACCOUNT_BFESS=46935071688D78C1; BDUSS_BFESS=l1SU5nNXJhem5NUUtuUGF3M0tUZFh5V356bE43d3lCc2FQT3dKYThTU1VRMVpqRVFBQUFBJCQAAAAAAAAAAAEAAAACCeP-tv60ztSq1q7N6NfTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJS2LmOUti5jSW; BAIDUID_BFESS=ADBC15F9539AC3DC4E2B4357892C6338:FG=1; ZFY=0tSY2YREU0sWPj7omdNG8nhw:AMIBJMcSjpUUKTA0:BvE:C; H_PS_PSSID='
    }
    if not os.path.isdir(resultFolder):  # 判断是否为目录
        os.mkdir(resultFolder)  # 创建一级目录

    for area in areas:
        totalResultList = []
        collectEachAreaInfo(area, headers, totalResultList)
        DF2Excel(resultFolder + area.get("name") + "-漫展信息.xlsx", totalResultList, typeLists)


def collectEachAreaInfo(area, headers, totalResultList):
    print("开始搜集：" + area.get("name"))
    i = 0
    for type in typeLists:
        resultList = []
        i += 1
        for page in range(1, pageNum):
            url = ("https://show.bilibili.com/api/ticket/project/listV2?version=134&page={}&pagesize=16&area={}&filter=&platform=web&p_type={}").format(
                page, area.get("code"), urllib.parse.quote(type))
            pageContent = requests.get(url=url, headers=headers).content.decode('utf-8').split('"project_id":')
            # print('这是第{}页'.format(page))
            if (len(pageContent) <= 1):
                break
            collectEachPage(headers, pageContent, resultList)
            # print('第{}页，匹配了{}个活动'.format(page, j))
        resultList.sort()
        columnHeader = ['开始时间', '名称', '地点', '具体时间范围', '想去人数', '最低票价', '是否有舞台（字符串匹配）',
                        'Link']
        resultList.insert(0, columnHeader)
        totalResultList.append(pd.DataFrame(resultList))
        print(" - " + type + ": 共 " + str(len(resultList) - 1) + " 条数据")


def collectEachPage(headers, pageContent, resultList):
    j = 0
    for activity in pageContent[1:]:
        activityName = re.compile('"project_name":"(.*?)"')
        j += 1
        city = re.compile('"city":"(.*?)"')
        lowPrice = re.compile('"price_low":([0-9]+)')
        highPrice = re.compile('"price_high":([0-9]+)')
        startTime = re.compile('"start_time":"(.*?)"')
        location = re.compile('"venue_name":"(.*?)"')
        url = re.compile('"url":"(.*?)"')

        project_name = ''.join(activityName.findall(activity))  # 不合并是列表，合并是字符串
        # city = ''.join((city.findall(activity)))

        price_low = ''.join(lowPrice.findall(activity))[0:-2]
        price_high = ''.join((highPrice.findall(activity)))[0:-2]
        startTime = ''.join((startTime.findall(activity)))
        # location = ''.join((location.findall(activity)))
        activityUrl = ''.join((url.findall(activity)))  # 活动详情页面
        id = activity.split(",")[0]  # id for find the details time range
        url = (("https://show.bilibili.com/api/ticket/project/getV2?version=134&id={}&project_id={}&requestSource=pc-new").format(
            id, id))
        details = requests.get(url=url, headers=headers).content.decode('utf-8')
        hasDancing = details.__contains__("舞")

        jsondata = JsonSearch(object=details, mode='s')
        wantToCount = JsonSearch(object=jsondata.search_first_value(key='wish_info'),
                                 mode='j').search_first_value(key='count')

        timeRange = jsondata.search_first_value('project_label')
        addressDetail = jsondata.search_first_value('address_detail')
        sale_flag = JsonSearch(jsondata.search_first_value('sale_flag'), mode='j').search_first_value('display_name')

        list = [startTime, project_name, addressDetail, timeRange, wantToCount,
                (price_low if price_low != "" else sale_flag), hasDancing, activityUrl]
        resultList.append(list)


thread1 = threading.Thread(name='t1', target=getAllInfo())
thread1.start()
# 这里看起来是用了进程，实际上完全没有显示，不用管这个，就算没有打包成类也可以直接爬取。
