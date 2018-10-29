# coding: utf-8

"""
    Ce scrit prend toutes les urls dans twitteruser, regarde si elles sont dans unshortener,
    puis ajoute dans newscrawl si elle n'y sont pas deja, et si c'est un news.
    Utilisation de plusieurs process.

    531000 ligne avant le script dans newscrawl
    
"""

# nn pew in twitternewsrec-venv python ~/wm-dist-tmp/TwitterNewsrec/twitternewsrec/newscrawler/uns2newscrawl.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

from datatools.url import *
from systemtools.basics import *
from systemtools.duration import *
from systemtools.file import *
from systemtools.logger import *
from systemtools.location import *
from systemtools.hayj import *
from systemtools.system import *
from webcrawler.crawler import *
from hjwebbrowser.utils import *
from hjwebbrowser.browser import *
from newstools.newsscraper import *
from machinelearning.function import *
from databasetools.mongo import *
from systemtools.hayj import *
from twitternewsrec.user.twitteruser import *
from twitternewsrec.newscrawler import __version__ as newsCrawlerVersion
from unshortener import config as unsConfig
from hjwebbrowser import config as wbConf
from twitternewsrec.user import config as tuConf
from twitternewsrec.newscrawler.utils import *
from twitternewsrec.user.utils import *
from multiprocessing import Lock, Process


def copyUnshortedNewsToNewsCrawl(url, uns, nuf, newsCrawlCollectionWatch,
    newsCrawlCollectionInsert, newsScraper, logger=None, verbose=True):
    try:
        if uns.isShortener(url) and nuf.isNews(url) and uns.isAlreadyUnshortened(url) and not newsCrawlCollectionWatch.has({"url": url}):
            data = uns.request(url)
            if data["status"] == "success":
                # We remove some elements:
                if "crawlingElement" in data:
                    del data["crawlingElement"]
                if "scrap" in data:
                    del data["scrap"]
                if "isShortener" in data:
                    del data["isShortener"]
                # We get additional data (the version and hostname are already
                # added by the MongoCollection instance):
                data["fromUnshortener"] = True
                data["scrap"] = newsScraper.smartScrap(data["html"], reduce=False)
                # We add it:
                newsCrawlCollectionInsert.insert(data)
                # We print:
                log("We inserted " + url, logger)
    except Exception as e:
        logException(e, logger, location="copyUnshortedNewsToNewsCrawl")



def lockedProcessInit(collection):
    if TEST:
        (user, password, host) = getStudentMongoAuth()
    else:
        (user, password, host) = getOctodsMongoAuth()

    uns = Unshortener(readOnly=True, logger=logger)
    nuf = NewsURLFilter(unshortenerReadOnly=True, logger=logger, useUnshortener=True)

    newsCrawlCollectionWatch = MongoCollection\
    (
        "twitter",
        "newscrawl",
        user=user, password=password, host=host,
        version=newsCrawlerVersion,
        giveHostname=True,
        giveTimestamp=True,
        logger=logger,
    )

    if TEST:
        newsCrawlCollectionInsert = MongoCollection\
        (
            "student",
            "newscrawl-test",
            indexOn=["url"],
            user=user, password=password, host=host,
            version=newsCrawlerVersion,
            giveHostname=True,
            giveTimestamp=True,
            logger=logger,
        )
    else:
        newsCrawlCollectionInsert = newsCrawlCollectionWatch


    newsScraper = NewsScraper(logger=logger)
    userCrawlCollection = getUserCrawlCollection(logger=logger)
    return \
    {
        "newsScraper": newsScraper,
        "userCrawlCollection": userCrawlCollection,
        "newsCrawlCollectionInsert": newsCrawlCollectionInsert,
        "newsCrawlCollectionWatch": newsCrawlCollectionWatch,
        "uns": uns,
        "nuf": nuf,
    }


def processFunct(row, collection=None, initVars=None):
    for url in TwitterUser(row, logger=logger).getShares():
        copyUnshortedNewsToNewsCrawl(url, initVars["uns"], initVars["nuf"],
            initVars["newsCrawlCollectionWatch"], initVars["newsCrawlCollectionInsert"], initVars["newsScraper"], logger=logger)


if __name__ == '__main__':
    if not isHostname("datascience01"):
        print("Please execute this script on datascience01")
        exit()

    logger = Logger("uns2newscrawl.log")
    TEST = False
    userCrawlSingleton = getUserCrawlSingleton(logger=logger)
    limit = None
    if TEST:
        limit = 10000
    userCrawlSingleton.map(processFunct, lockedProcessInit=lockedProcessInit, limit=limit)
