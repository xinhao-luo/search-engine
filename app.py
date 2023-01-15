# SJTU EE208
INDEX_DIR = "IndexFiles.index"

import Levenshtein   #计算相似度
import re
import sys, os, lucene,jieba
from java.io import File
from java.nio.file import Path
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.core import SimpleAnalyzer ,WhitespaceAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.util import Version
from org.apache.lucene.search import BooleanQuery
from org.apache.lucene.search import BooleanClause
from org.apache.lucene.search.highlight import Highlighter, QueryScorer, SimpleFragmenter, SimpleHTMLFormatter
from typing import KeysView
from flask import Flask, redirect, render_template, request, url_for
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

# for picture searching
import time
import numpy as np
import torch
import torchvision
import torchvision.transforms as transforms
from torchvision.datasets.folder import default_loader
import PIL
import os
import numpy as np
import cv2
import extract_faces

title = ''
url = ''
date = ''
app = Flask(__name__,static_url_path='/static')

##关键词搜索
def search(keyword):
    STORE_DIR = "index"
    vm.attachCurrentThread()
    directory=SimpleFSDirectory(File(STORE_DIR).toPath())
    searcher=IndexSearcher(DirectoryReader.open(directory))
    analyzer=StandardAnalyzer()

    res_cnt,res_list=get_res(searcher,analyzer,keyword)
    return res_cnt,res_list

#返回关键词搜索结果#
def get_res(searcher,analyzer,keyword):
    command_dict = parseCommand(keyword)
    querys = BooleanQuery.Builder()
    for k,v in command_dict.items():
        query = QueryParser(k, analyzer).parse(v)
        querys.add(query, BooleanClause.Occur.MUST)
    query=QueryParser("contents",analyzer).parse(keyword)
    scoreDocs=searcher.search(query, 50).scoreDocs
    res_list=[]
    for i, scoreDoc in enumerate(scoreDocs):
        doc = searcher.doc(scoreDoc.doc)
        res={}
        res['title']=doc.get('title')
        res['url']=doc.get('url')
        res['date']=doc.get('date')
        res['contents'] = urllib.request.urlopen(doc.get('url'))
        res['img']=doc.get('img')
        res_list.append(res)
    res_list = simility(res_list)
    return len(scoreDocs),res_list

#按时间排序
def search_by_time(keyword):
    res_cnt,res_list=search(keyword)
    for i in range(len(res_list)):
        for j in range(len(res_list)-1-i):
            if timeCompare(res_list[j]['date'], res_list[j+1]['date']) == 0:
                res_list[j]['title'], res_list[j+1]['title'] = res_list[j+1]['title'], res_list[j]['title']
                res_list[j]['date'], res_list[j+1]['date'] = res_list[j+1]['date'], res_list[j]['date']
                res_list[j]['url'], res_list[j+1]['url'] = res_list[j+1]['url'], res_list[j]['url']
                res_list[j]['contents'], res_list[j+1]['contents'] = res_list[j+1]['contents'], res_list[j]['contents']
                res_list[j]['img'], res_list[j+1]['img'] = res_list[j+1]['img'], res_list[j]['img']
    return res_cnt, res_list

def parseCommand(command):
    command_dict = {'contents': ''}   
    command_dict['contents'] = ' '.join(jieba.cut(command))
    return command_dict

def timeCompare(time1, time2): # 1 -> time1 >= time2; 0 -> times2 > time1
    time1 = time1.split('-')
    time2 = time2.split('-')
    for i in range(len(time1)):
        if int(time1[i]) > int(time2[i]):
            return 1
        elif int(time1[i]) < int(time2[i]):
            return 0
        else:
            continue
    return 1

#相似度
def simility(res_list):
    simility = []
    length = len(res_list) 
    length1 = length
    pos = 1
    while(pos < length1):
        length = length1
        while(length > pos):
            simility.append(Levenshtein.ratio(res_list[pos - 1]['title'],res_list[length - 1]['title']))
            length -= 1
        length = length1
        while(length > pos):
            maxq = simility.index(max(simility))
            if(simility[maxq] >= 0.4):
                simility[maxq] = 0
                res_list[pos]['title'], res_list[maxq]['title'] = res_list[maxq]['title'], res_list[pos]['title']
                res_list[pos]['date'], res_list[maxq]['date'] = res_list[maxq]['date'], res_list[pos]['date']
                res_list[pos]['url'], res_list[maxq]['url'] = res_list[maxq]['url'], res_list[pos]['url']
                res_list[pos]['contents'], res_list[maxq]['contents'] = res_list[maxq]['contents'], res_list[pos]['contents']
                res_list[pos]['img'], res_list[maxq]['img'] = res_list[maxq]['img'], res_list[pos]['img']
                pos += 1

            else:
                break
            length -= 1
        pos += 1
        simility = []
    return res_list

#图像搜索
def queryPicture(picture): # picture is an array
    def get_picture(picture):
        cap = cv2.VideoCapture(picture)
        ret,img = cap.read()
        return img
    
    def get_color(img1):
        img = np.array(img1)
        feature = []
        sum = img.sum()
        for i in range(3):
            uni_img = img[:, :, i]
            img_color = uni_img.sum()
            feature.append(img_color/sum)
        return feature
    
    def distribution(feature):
        distribute = []
        for i in feature:
            if i >= 0 and i < 0.3:
                distribute.append(0)
            elif i >= 0.3 and i < 0.36:
                distribute.append(1)
            elif i >= 0.36:
                distribute.append(2)
        return distribute
    
    def extract(img):
        H = img.shape[0]
        W = img.shape[1]
        midH = H // 2
        midW = W // 2
        feature = []
        img1 = img[0:midH, 0:midW, :]
        img2 = img[0:midH, midW:, :]
        img3 = img[midH:, 0:midW, :]
        img4 = img[midH:, midW:, :]
        img_set = [img1, img2, img3, img4]
        for uni_img in img_set:
            feature += get_color(uni_img)
        feature = distribution(feature)
        return np.array(feature)
    
    def Unary(c, num):
        ham1 = [1 for i in range(num)]
        ham2 = [0 for i in range(c - num)]
        ham = ham1+ham2
        return ham

    def LSH(feature):
        C = 4
        g = [1, 3, 7, 8, 13, 16, 18, 21, 23, 27, 33, 34, 39, 45, 48]
        unary = []
        for i in feature:
            unary += Unary(C, i)
        gp = [unary[i-1] for i in g]
        return np.array(gp)

    def get_path(gp):
        path = ''
        for i in gp:
            path += str(i)
        return path
    
    img = get_picture(picture)
    target_feature = extract(img)
    gp = LSH(extract(img)) # 0, 1, 2
    root = get_path(gp)
    root1 = "LSH_data/" + root
    matched = []
    for root2, dir, file in os.walk(root1, topdown=False):
        for name in file:
            img = cv2.imread(os.path.join(root2, name), cv2.IMREAD_COLOR)
            feature = extract(img)
            dis = np.linalg.norm(feature - target_feature)
            if dis <= 1:
                matched.append("../static/images/LSH_data/{}/{}".format(root, name))
    
    return matched

#人脸搜索#
def face_search(filename):
    ex=extract_faces.face_recognition()
    faces_cnt,faces=ex.extract(filename)
    return faces_cnt,faces

def face_match(res_list):
    def get_picture(picture):
        cap = cv2.VideoCapture(picture)
        ret,img = cap.read()
        return img
    
    def get_color(img1):
        img = np.array(img1)
        feature = []
        sum = img.sum()
        for i in range(3):
            uni_img = img[:, :, i]
            img_color = uni_img.sum()
            feature.append(img_color/sum)
        return feature
    
    def distribution(feature):
        distribute = []
        for i in feature:
            if i >= 0 and i < 0.3:
                distribute.append(0)
            elif i >= 0.3 and i < 0.36:
                distribute.append(1)
            elif i >= 0.36:
                distribute.append(2)
        return distribute
    
    def extract(img):
        H = img.shape[0]
        W = img.shape[1]
        midH = H // 2
        midW = W // 2
        feature = []
        img1 = img[0:midH, 0:midW, :]
        img2 = img[0:midH, midW:, :]
        img3 = img[midH:, 0:midW, :]
        img4 = img[midH:, midW:, :]
        img_set = [img1, img2, img3, img4]
        for uni_img in img_set:
            feature += get_color(uni_img)
        feature = distribution(feature)
        return np.array(feature)
    
    for i in range(len(res_list)):
        img = get_picture(res_list[i])
        target_feature = extract(img)
        root1 = "static/faces_h"
        matched = []
        for root2, dir, file in os.walk(root1, topdown=False):
            for name in file:
                img = cv2.imread(os.path.join(root2, name), cv2.IMREAD_COLOR)
                feature = extract(img)
                dis = np.linalg.norm(feature - target_feature)
                print("--", dis)
                if dis == 0:
                    matched.append("../static/faces_h/{}".format(name))
    
    return len(matched), matched

@app.route('/')
def form_1():
    return render_template("index.html")

@app.route('/word')
def form_2():
    return render_template("word.html")

@app.route('/img')
def form_3():
    return render_template("img.html")

@app.route('/face')
def form_4():
    return render_template("face.html")

@app.route('/wdresult', methods=['GET','POST'])
def wd_result():
    keyword=request.args.get('keyword')
    res_cnt,res_list=search(keyword)
    res_cnt_1,res_list_1=search_by_time(keyword)
    return render_template("result.html", keyword=keyword,res_cnt=res_cnt,res_list=res_list,res_cnt_1=res_cnt_1,res_list_1=res_list_1)

@app.route('/imgresult', methods=['GET','POST'])
def img_result():
   pic = request.files['file'] # 得到照片的url
   vm.attachCurrentThread()

   start = str(pic).index("'") + 1
   l = str(pic)[str(pic).index("'")+1:].index("'")
   pic = str(pic)[start:start + l]
   searchResult = queryPicture(pic)
   print(searchResult)
   length = len(searchResult)
   return render_template('imgresult.html', res_list = searchResult, res_cnt = length)

@app.route('/faceresult', methods=['GET','POST'])
def face_result():
    pic=request.files['file'] #获取网页上传的图片
    start = str(pic).index("'") + 1
    l = str(pic)[str(pic).index("'")+1:].index("'")
    pic = str(pic)[start:start + l]
    res_cnt,res_list=face_search(pic)

    match_cnt,match_list=face_match(res_list)
    return render_template("faceresult.html",res_cnt=res_cnt,res_list=res_list,match_cnt=match_cnt,match_list=match_list)

if __name__ == '__main__':
    last_search = ''

    try:
        vm = lucene.initVM()
    except:
        vm = lucene.getVMEnv()

    app.run(debug=True,port = 8081)
    
    