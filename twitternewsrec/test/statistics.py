
from twitternewsrec.newscrawler.crawler import *
from systemtools.basics import *
from systemtools.logger import *



def printTopDomains(scoreVersion="0.0.10"):
    topMemory = SerializableDict("printTopDomains-topMemory",
                                limit=100,
                              serializeEachNAction=1,
                              logger=logger,
                              useMongodb=False)
    tusParams = sortByKey(\
    {
        "shortenedAsNews": False,
        "notBotThreshold": 0.3,
        "relevanceThreshold": 0.3,
        "sdVersion": scoreVersion,
        "unshortenerReadOnly": True,
    })
    tus = TwitterUserScores(**tusParams)
    top = tus.top()
    topMemory[str(tusParams)] = top
    topMemory.save()
    print(top)


def test1():
    failsSD = SerializableDict\
    (
        "newscrawlfails",
        logger=logger,
        limit=100000000,
        useMongodb=True,
        user=user, password=password, host=host,
    )
    newscrawlCollection = MongoCollection\
    (
        "twitter",
        "newscrawl",
        user=user, password=password, host=host,
        giveHostname=True,
        giveTimestamp=True,
        logger=logger,
    )

def tmpFileUser():
    u = TwitterUser("3390472065")
    u.toTmpFile()


if __name__ == '__main__':
    # if not isHostname("datasc"):
    #     print("Please execute this script on datascience01!")
    #     exit()
    # # Logger:
    # logger = Logger("newscrawler-statistics-" + getRandomStr() + ".log")
    # # Collections:
    # (user, password, host) = getStudentMongoAuth()

    # printTopDomains()


    u = TwitterUser("522810685")
    # printLTS(u.getScores())
    u.toTmpFile()

    # tmpFileUser()
    
