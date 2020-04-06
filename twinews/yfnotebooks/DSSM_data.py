#-*-coding:utf-8-*-
from systemtools.hayj import *
from systemtools.location import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.printer import *
from databasetools.mongo import *
from newstools.goodarticle.utils import *
from nlptools.preprocessing import *
from nlptools.news import parser as newsParser
from machinelearning.iterator import *
import pymongo
import json
import pandas as pd
import sys ; sys.path.append('/home/yuting/PycharmProjects/Twinews')
from twinews.utils import *

ConnUsers = getUsersCollection()
# ConnNews = getNewsCollection()
output = []
# read user with more than 30 news
for row in ConnUsers.find().limit(10):
    userTemp = {}
    if len(row["news"]) >= 30:
        userTemp[row["user_id"]] = row["news"]
        output.append(userTemp)









