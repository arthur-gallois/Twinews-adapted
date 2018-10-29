# coding: utf-8

"""
    Ce scrit prend toutes les urls dans twitteruser, regarde si elles sont dans unshortener,
    puis ajoute dans newscrawl si elle n'y sont pas deja, et si c'est un news.
    Utilisation de plusieurs process.

    531000 ligne avant le script dans newscrawl
    
"""

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/collectioncopy.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-2]))

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
from newscrawler.twitteruser import *
from newscrawler.sharesgenerator import *
from newscrawler import __version__ as newsCrawlerVersion
from unshortener import config as unsConfig
from hjwebbrowser import config as wbConf
from newscrawler import config as tuConf
from newscrawler.utils import *
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
                data["scrap"] = newsScraper.scrapAll(data["html"], reduce=False)
                # We add it:
                newsCrawlCollectionInsert.insert(data)
                # We print:
                log("We inserted " + url, logger)
    except Exception as e:
        logException(e, logger, location="copyUnshortedNewsToNewsCrawl")



def sequentialProcessing(ids, lock):
    with lock:
        name = getRandomName()
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

        log(name + " initialized!", logger)

    for id in ids:
        log(name + ": Requesting user " + id, logger)
        row = userCrawlCollection.findOne({"user_id": id})
        try:
            log(name + ": Got user " + row["scrap"]["username"], logger)
        except:
            log(name + ": Error getting the row username", logger)
        for url in UserSharesGenerator(row, logger=logger):
            copyUnshortedNewsToNewsCrawl(url, uns, nuf,
                newsCrawlCollectionWatch, newsCrawlCollectionInsert, newsScraper, logger=logger)
        log(name + ": User " + id + " DONE.", logger)


# if TEST:
#     # userIds = list(collection.distinct(tuConf.userIdField))[:2000]
#     cursor = userCrawlSingleton.find().limit(2000)
# else:
#     # userIds = list(collection.distinct(tuConf.userIdField))
#     cursor = userCrawlSingleton.find()






if __name__ == '__main__':
    if not isHostname("datascience01"):
        print("Please execute this script on datascience01")
        exit()

    logger = Logger("collectioncopy.log")
    TEST = False
    lock = Lock()
    tt = TicToc(logger=logger)
    tt.tic()
    userCrawlSingleton = getUserCrawlSingleton(logger=logger)
    if TEST:
        userIds = list(userCrawlSingleton.distinct(tuConf.userIdField))[:10000]
    else:
        userIds = list(userCrawlSingleton.distinct(tuConf.userIdField))
    userIdsChunks = split(userIds, cpuCount())
    tt.tic("Getting all ids DONE.")

    # We create process:
    processes = []
    for chunk in userIdsChunks:
        p = Process(target=sequentialProcessing, args=(chunk, lock,))
        processes.append(p)
    for p in processes:
        p.start()
    for p in processes:
        p.join()
    tt.tic("Map DONE.")