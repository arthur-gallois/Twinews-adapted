
from datastructuretools.hashmap import *
from systemtools.basics import *
from systemtools.logger import *
from twinews.user import config as tuConf
from systemtools.hayj import *
from systemtools.basics import *
from systemtools.logger import *
from newstools.newsurlfilter import *
from datatools.url import *
from unshortener.unshortener import *

################## Collections #####################
def getUserCrawlCollection(dbName="twitter", collectionName="usercrawl",
                          logger=None, verbose=True):
    """
        This function return the user crawl collection singleton
    """
    try:
        (user, password, host) = getStudentMongoAuth()
        col = MongoCollection\
        (
            dbName, collectionName,
            logger=logger, verbose=verbose,
            user=user, password=password, host=host,
        )
        return col
    except Exception as e:
        logException(e, logger, verbose=verbose, location="getUserCrawlSingleton")




################## Singletons #####################
userCrawlSingleton = None
def getUserCrawlSingleton(*args, **kwargs):
    global userCrawlSingleton
    if userCrawlSingleton is None:
        userCrawlSingleton = getUserCrawlCollection(*args, **kwargs)
    return userCrawlSingleton


newsCrawlSingleton = None
def getNewsCrawlSingleton(dbName="twitter", collectionName="newscrawl",
                          logger=None, verbose=True, write=False):
    """
        This function return the news crawl collection singleton
    """
    global newsCrawlSingleton
    if newsCrawlSingleton is None:
        try:
            if write:
                (user, password, host) = getOctodsMongoAuth()
            else:
                (user, password, host) = getStudentMongoAuth()
            newsCrawlSingleton = MongoCollection\
            (
                dbName, collectionName,
                indexOn="url",
                logger=logger, verbose=verbose,
                user=user, password=password, host=host,
                hideIndexException=True,
            )
        except Exception as e:
            logException(e, logger, verbose=verbose, location="getNewsCrawlSingleton")
    return newsCrawlSingleton

readOnlyUnshortenerSingleton = None
def getReadOnlyUnshortenerSingleton(logger=None, verbose=True):
    global readOnlyUnshortenerSingleton
    if readOnlyUnshortenerSingleton is None:
        readOnlyUnshortenerSingleton = Unshortener(readOnly=True,
                                                logger=logger, verbose=verbose)
    return readOnlyUnshortenerSingleton

newsUrlFilterSingleton = None
def getNewsUrlFilterSingleton(logger=None, verbose=True):
    global newsUrlFilterSingleton
    if newsUrlFilterSingleton is None:
        newsUrlFilterSingleton = NewsURLFilter(unshortenerReadOnly=True,
                                                   logger=logger, verbose=verbose)
    return newsUrlFilterSingleton

urlParserSingleton = None
def getURLParserSingleton(*args, **kwargs):
    global urlParserSingleton
    if urlParserSingleton is None:
        urlParserSingleton = URLParser(*args, **kwargs)
    return urlParserSingleton
