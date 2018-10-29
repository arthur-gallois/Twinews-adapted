# coding: utf-8

# nn 19 pew in twitternewsrec-venv python /home/hayj/wm-dist-tmp/TwitterNewsrec/twitternewsrec/user/twitteruserscore.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

from systemtools.hayj import *

from domainduplicate import config as ddConf
(user, password, host) = getStudentMongoAuth()
ddConf.user = user
ddConf.password = password
ddConf.host = host

from twitternewsrec.user import config as tuConf

TEST = False
if TEST:
	tuConf.twitterUserScoreVersion = "test2"

from datastructuretools.hashmap import *
from systemtools.basics import *
from systemtools.logger import *
from twitternewsrec.user.utils import *
from twitternewsrec.newscrawler.utils import *
from twitternewsrec.user.twitteruser import *

def lockedProcessInit(collection):
	TwitterUser(collection.findOne({})["user_id"], userCrawlCollection=collection)

def processFunct(row, collection=None, initVars=None):
	u = TwitterUser(row["user_id"], userCrawlCollection=collection, lazyLoad=True, logger=logger)
	u.getScores()

if __name__ == '__main__':
	logger = Logger("twitteruserscore.log")
	limit = None
	if TEST:
		limit = 300
	collection = getUserCrawlSingleton(logger=logger)
	collection.map(processFunct, lockedProcessInit=lockedProcessInit, limit=limit)


