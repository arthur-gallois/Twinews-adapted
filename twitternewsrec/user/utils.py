
from datastructuretools.hashmap import *
from systemtools.basics import *
from systemtools.logger import *
from twitternewsrec.user import config as tuConf
from systemtools.hayj import *

twitterUserScoreSD = None
def getTwitterUserScoreSD(logger=None, verbose=True):
    global twitterUserScoreSD
    if twitterUserScoreSD is None:
        if isHostname("hjlat"):
            # (user, password, host) = getLocalhostMongoAuth()
            # (user, password, host) = getStudentMongoAuth()
            (user, password, host) = getOctodsMongoAuth()
        else:
            (user, password, host) = getOctodsMongoAuth()
        twitterUserScoreSD = SerializableDict \
        (
            name="twitteruserscore-" + str(tuConf.twitterUserScoreVersion),
            logger=logger, verbose=verbose,
            useMongodb=True,
            host=host, user=user, password=password,
        )
    return twitterUserScoreSD

oldTwitterUserScoreSD = None
def getOldTwitterUserScoreSD(logger=None, verbose=True, version=None):
    global oldTwitterUserScoreSD
    if oldTwitterUserScoreSD is None:
        if version is None:
            version = tuConf.oldNotBotScoreVersionToCopy
        if version is None:
            oldTwitterUserScoreSD = None
        else:
            if isHostname("hjlat"):
                # (user, password, host) = getLocalhostMongoAuth()
                (user, password, host) = getOctodsMongoAuth()
            else:
                (user, password, host) = getOctodsMongoAuth()
            oldTwitterUserScoreSD = SerializableDict \
            (
                name="twitteruserscore-" + str(version),
                logger=logger, verbose=verbose,
                useMongodb=True,
                host=host, user=user, password=password,
            )
    return oldTwitterUserScoreSD

topUserSD = None
def getTopUserSD(logger=None, verbose=True):
    global topUserSD
    if topUserSD is None:
        if isHostname("hjlat"):
            (user, password, host) = getOctodsMongoAuth()
            # (user, password, host) = getStudentMongoAuth()
        else:
            (user, password, host) = getOctodsMongoAuth()
        topUserSD = SerializableDict \
        (
            name="topuser-" + str(tuConf.topUserVersion),
            logger=logger, verbose=verbose,
            useMongodb=True,
            host=host, user=user, password=password,
        )
    return topUserSD
