# coding: utf-8

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/sharesgenerator.py

__version__ = "0.0.4"

from systemtools.basics import *
from datatools.json import *
from datatools.url import *
from datatools.csvreader import *
from systemtools.file import *
from systemtools.location import *
from systemtools.system import *
from systemtools.logger import *
from datatools.url import *
from newstools.newsurlfilter import *
from unshortener.unshortener import *
from nlptools.basics import *
from nlptools.tokenizer import *
import random
import copy
try:
    from systemtools.hayj import *
except: pass
import datetime
from twittercrawler import __version__ as twittercrawlerVersion
from twittercrawler.twitterscraper import *

################## TEST #####################
TEST = False                                #
if isHostname("hjlat"):                     #
    TEST = True                             #
else:                                       #
    TEST = False                            #
#############################################

def isUserData(userData):
    if userData is None or \
    not dictContains(userData, "tweets") or \
    not dictContains(userData, "user_id"):
        return False
    return True

def userDataToReadableTmpFile(userData, fileName="readable-tmp-twitter-user.txt"):
    filePath = tmpDir() + "/" + fileName
    userData = copy.deepcopy(userData)
    if dictContains(userData, "scrap"):
        userData = userData["scrap"]
    userData = sortByKey(userData)
    newLine = "\n"
    bigSeparation = "\n" * 5
    littleSeparation = "\n" * 2
    text = ""
    text += userData["name"] + newLine
    text += userData["url"] + newLine
    text += "scraped tweet count: " + str(len(userData["tweets"])) + newLine
    text += bigSeparation
    for key in \
    [
        "has_enough_old_tweets",
        "follower_count",
        "following_count",
    ]:
        text += key + ": " + str(userData[key]) + newLine

    tweets = userData["tweets"]
    del userData["tweets"]

    text += bigSeparation
    if "hover_users" in userData:
        del userData["hover_users"]
    del userData["joindate_text"]
    del userData["consecutive_old_tweets"]
    text += listToStr(userData)
    text += bigSeparation

    for tweet in tweets:
        text += tweet["type"] + " at " + tweet["date"] + " from " + tweet["name"] + newLine
        text += tweet["text"].replace("\n", " ") + newLine
        for key in \
        [
            "hashtags",
            "shares",
            "atreplies",
        ]:
            text += key + " count: " + str(len(tweet[key])) + ", "
        text += newLine
        for key in \
        [
            "like_count",
            "retweet_count",
            "reply_count",
        ]:
            text += key + " count: " + str(tweet[key]) + ", "
        text += littleSeparation

    strToFile(text, filePath)


twitterUserScoresSingleton = None
def getTwitterUserScoresSingleton(twitterUserScoresParams={}):
    global twitterUserScoresSingleton
    if twitterUserScoresSingleton is None:
        twitterUserScoresSingleton = TwitterUserScores(**twitterUserScoresParams)
    return twitterUserScoresSingleton

class TwitterUserScores():
    """
        This class will store all twitter user score (not bot scores and relevance (for a recommender system) scores) in SerializableDicts (with mongodb for datascience01).
        WARNING: set useUnshortener as True
    """
    def __init__\
    (
        self,
        logger=None,
        verbose=True,
        defaultScore=0.0,
        followingCountInterval=(5, 10000),
        tweetCountInterval=(30, 1000000),
        followerCountInterval=(2, 10000),
        tweetsWithShareRatios=(0.05, 0.95),
        tweetsWithAtreplyRatios=(0.08, 0.99),
        tweetsWithHashtagRatios=(0.08, 0.99),
        maxRatioDomainBadInterval=(0.35, 0.65), # And greater is very bad
        enTweetsMinRatio=0.8,
        notGreatScrapedTweetCountInterval=(30, 150),
        notGreatNewsCountInterval=(3, 13),
        notGreat3GramOverlap=(0.0, 0.8),
        tweetOverlapCheckCount=None, # auto
        userIdField="user_id",
        useMongodbSerializableDicts=None, # TODO Set it as None for auto
        scoreMaxDecimals=2,
        notBotThreshold=0.95,
        relevanceThreshold=0.85,
        minRatioOfLeastType=0.05,
        unshortenerReadOnly=True, # TODO set it as False
        cacheLimit=400000, # TODO set it as True
        sdVersion=None,
        shortenedAsNews=False,
    ):
        self.logger = logger
        self.verbose = verbose
        self.defaultScore = defaultScore
        self.followingCountInterval = followingCountInterval
        self.tweetCountInterval = tweetCountInterval
        self.followerCountInterval = followerCountInterval
        self.tweetsWithShareRatios = tweetsWithShareRatios
        self.tweetsWithAtreplyRatios = tweetsWithAtreplyRatios
        self.tweetsWithHashtagRatios = tweetsWithHashtagRatios
        self.enTweetsMinRatio = enTweetsMinRatio
        self.userIdField = userIdField
        self.scoreMaxDecimals = scoreMaxDecimals
        self.notGreatScrapedTweetCountInterval = notGreatScrapedTweetCountInterval
        self.notGreatNewsCountInterval = notGreatNewsCountInterval
        self.notBotThreshold = notBotThreshold
        self.relevanceThreshold = relevanceThreshold
        self.minRatioOfLeastType = minRatioOfLeastType
        self.notGreat3GramOverlap = notGreat3GramOverlap
        self.tweetOverlapCheckCount = tweetOverlapCheckCount
        self.cacheLimit = cacheLimit
        self.maxRatioDomainBadInterval = maxRatioDomainBadInterval
        self.sdVersion = sdVersion
        self.unshortenerReadOnly = unshortenerReadOnly
        self.shortenedAsNews = shortenedAsNews

        # if modify versions:
        if self.sdVersion is None:
            self.sdVersion = __version__

        # If set thresholds:
        if TEST:
            self.notBotThreshold = 0.0
            self.relevanceThreshold = 0.0

        # We auto set tweetOverlapCheckCount:
        if self.tweetOverlapCheckCount is None:
            if TEST:
                self.tweetOverlapCheckCount = 100
            else:
                self.tweetOverlapCheckCount = 300

        # We create an unshortener to check domains of share:
        self.uns = Unshortener(readOnly=self.unshortenerReadOnly)

        # And a urlParser:
        self.urlParser = URLParser()

        # We create the news url filter which use an Unshortener:
        self.nuf = NewsURLFilter(logger=self.logger, verbose=self.verbose,
                                 unshortenerReadOnly=self.unshortenerReadOnly)

        # We choose useMongodbSerializableDicts:
        self.useMongodbSerializableDicts = useMongodbSerializableDicts

        if self.useMongodbSerializableDicts is None:
            if TEST:
                self.useMongodbSerializableDicts = False
            elif isHostname("datascience01"):
                self.useMongodbSerializableDicts = True
            else:
                self.useMongodbSerializableDicts = False

        # We create serializable dicts:
        (user, password, host) = ("localhost", None, None)
        try:
            (user, password, host) = getOctodsMongoAuth()
        except: pass
        self.relevanceSD = SerializableDict\
        (
            "twitteruserrelevancescores" + "-" + self.sdVersion,
            logger=self.logger,
            verbose=self.verbose,
            funct=self.relevanceScoreFunct,
            cacheCheckRatio=0.0, # because parameters can change
            useMongodb=self.useMongodbSerializableDicts,
            mongoIndex=self.userIdField,
            limit=self.cacheLimit,
            user=user, password=password, host=host,
        )
        self.notBotSD = SerializableDict\
        (
            "twitterusernotbotscores" + "-" + self.sdVersion,
            logger=self.logger,
            verbose=self.verbose,
            funct=self.notBotScoreFunct,
            # because parameters can change and we introduced random:
            cacheCheckRatio=0.0,
            useMongodb=self.useMongodbSerializableDicts,
            mongoIndex=self.userIdField,
            limit=self.cacheLimit,
            user=user, password=password, host=host,
        )

        # We reset all serializable dicts:
        if TEST:
            self.relevanceSD.reset(security=True)
            self.notBotSD.reset(security=True)
            log("relevanceSD and notBotSD reseted.", self)



    def notBotScore(self, userData, *args, **kwargs):
        return self.notBotSD.get(userData[self.userIdField],
                                 userData, *args, **kwargs)

    def notBotScoreFunct(self, userId, userData):
        """
            This function give a score which try to say if the user is
            a normal user (not a bot, not a leader or verified user...).
        """
        if not isUserData(userData):
            return self.defaultScore

        # We prepare features:
        score = 0.0
        featuresCount = 0.0

        try:
            # We start with eliminatory features:
            # Verified:
            if userData["verified"]:
                return self.defaultScore

            # hasGoodFollowingCount
            coeff = 0.6
            if userData["following_count"] >= self.followingCountInterval[0] and \
            userData["following_count"] <= self.followingCountInterval[1]:
                score += coeff
            featuresCount += coeff

            # hasGoodFollowerCount
            coeff = 0.6
            if userData["follower_count"] >= self.followerCountInterval[0] and \
            userData["follower_count"] <= self.followerCountInterval[1]:
                score += 1
            featuresCount += 1

            # hasGoodTweetCount
            coeff = 0.6
            if userData["tweet_count"] >= self.tweetCountInterval[0] and \
            userData["tweet_count"] <= self.tweetCountInterval[1]:
                score += coeff
            featuresCount += coeff

            # shares etc ratios:
            coeff = 1.0
            for key, ratios in \
            [
                ("shares", self.tweetsWithShareRatios),
                ("atreplies", self.tweetsWithAtreplyRatios),
                ("hashtags", self.tweetsWithHashtagRatios),
            ]:
                count = 0
                for tweet in userData["tweets"]:
                    if dictContains(tweet, key) and len(tweet[key]) > 0:
                        count += 1
                ratio = count / len(userData["tweets"])
                if ratio >= ratios[0] and ratio <= ratios[1]:
                    score += coeff
                featuresCount += coeff

            # Media count:
            coeff = 0.2
            if dictContains(userData, "media_count") and userData["media_count"] > 0:
                score += coeff
            featuresCount += coeff

            # Favorite count:
            coeff = 0.1
            if dictContains(userData, "favorite_count") and userData["favorite_count"] > 0:
                score += coeff
            featuresCount += coeff

            # Moment count:
            coeff = 0.1
            if dictContains(userData, "moment_count") and userData["moment_count"] > 0:
                score += coeff
            featuresCount += coeff

            # list count:
            coeff = 0.1
            if dictContains(userData, "list_count") and userData["list_count"] > 0:
                score += coeff
            featuresCount += coeff

            # Twitter website exists:
            coeff = 0.1
            if dictContains(userData, "user_website"):
                score += coeff
            featuresCount += coeff

            # Bio exists:
            coeff = 0.1
            if dictContains(userData, "bio") and len(userData["bio"]) > 0:
                score += coeff
            featuresCount += coeff

            # Avatar exists:
            coeff = 0.05
            if dictContains(userData, "avatar") and len(userData["avatar"]) > 0:
                score += coeff
            featuresCount += coeff

            # Has pics and quotes:
            coeff = 0.05
            for key in ["pics", "quotes"]:
                for tweet in userData["tweets"]:
                    if key in tweet and len(tweet[key]) > 0:
                        score += coeff
                        break
                featuresCount += coeff

            # min ratio of the least ratio over all types (tweet, retweet...):
            # This mean that the user must have a good ratio of tweets and retweet
            # over these two type. Not only tweets, not only retweets...
            coeff = 0.3
            types = dict()
            allTypeInstanceCount = 0
            for tweet in userData["tweets"]:
                theType = tweet["type"]
                # We eliminate rtcomment and reply types:
                if theType in ["tweet", "retweet"]:
                    if theType not in types:
                        types[theType] = 0
                    types[theType] += 1
                    allTypeInstanceCount += 1
            newTypes = dict()
            for key, value in types.items():
                newTypes[key] = value / allTypeInstanceCount
            types = newTypes
            theMin = 1
            for key, value in types.items():
                if value < theMin:
                    theMin = value
            if theMin > self.minRatioOfLeastType:
                score += coeff
            featuresCount += coeff

            # has tweets (type):
            coeff = 0.5
            tweetCount = 0
            for tweet in userData["tweets"]:
                if tweet["type"] == "tweet":
                    tweetCount += 1
            hasTweetsScore = linearScore(tweetCount, 1, 3)
            score += hasTweetsScore * coeff
            featuresCount += coeff

            # has retweets on some tweet (retweet_count), like_count, reply_count:
            coeff = 0.5
            for key in ["retweet_count", "like_count", "reply_count"]:
                for tweet in userData["tweets"]:
                    if tweet["type"] == "tweet":
                        if dictContains(tweet, key) and tweet[key] > 0:
                            score += coeff
                            break
                featuresCount += coeff

            # Has different names for all retweets:
            coeff = 1.0
            usernames = set()
            for tweet in userData["tweets"]:
                if tweet["type"] == "retweet":
                    usernames.add(tweet["username"])
            differentUsernamesScore = linearScore(len(usernames), 1, 3)
            if TEST:
                print("differentUsernamesScore=" + str(differentUsernamesScore))
            differentUsernamesScore = differentUsernamesScore * coeff
            score += differentUsernamesScore
            featuresCount += coeff

            # Has different hashtags and atreplies :
            coeff = 0.3
            hashtagsSet = set()
            atrepliesSet = set()
            for tweet in userData["tweets"]:
                for hashtag in tweet["hashtags"]:
                    hashtagsSet.add(hashtag["text"])
                for atreply in tweet["atreplies"]:
                    atrepliesSet.add(atreply["text"])
            for currentSet in [hashtagsSet, atrepliesSet]:
                currentScore = linearScore(len(currentSet), 1, 3)
                score += currentScore * coeff
                featuresCount += coeff
                if TEST:
                    print("Has different hashtags and atreplies: " + str(currentScore))

            # Has different shares domains (which is not shortened)
            coeff = 2.0
            domainsDict = dict()
            domainInstanceCount = 0
            for tweet in userData["tweets"]:
                for share in tweet["shares"]:
                    url = share["url"]
                    if not self.uns.isShortened(url):
                        theDomain = self.urlParser.getDomain(url)
                        if theDomain not in domainsDict:
                            domainsDict[theDomain] = 0
                        domainsDict[theDomain] += 1
                        domainInstanceCount += 1
            newDomainDict = dict()
            for key, value in domainsDict.items():
                newDomainDict[key] = value / domainInstanceCount
            domainsDict = newDomainDict
            if len(domainsDict) == 0:
                differentDomainsScore = 0.0
                featuresCount += coeff
            else:
                domainsDict = sortBy(domainsDict, index=1, desc=True)
                maxRatio = domainsDict[0][1]
                if TEST:
                    print("maxRatio=" + str(maxRatio))
                    print("maxDomain=" + str(domainsDict[0][0]))
                    printLTS(domainsDict)
                differentDomainsScore = linearScore\
                (
                    maxRatio,
                    x1=self.maxRatioDomainBadInterval[0], y1=1.0,
                    x2=self.maxRatioDomainBadInterval[1], y2=0.0,
                )
            score += differentDomainsScore * coeff
            featuresCount += coeff
            if TEST:
                print("differentDomainsScore=" + str(differentDomainsScore))

            # We compute the approximate probabilty that a random tweet or a
            # retweet has an other tweet or retweet with a 3-gram overlap
            # First we lower and tokenize all tweets:
            coeff = 2.0
            tokenizedtweets = []
            for tweet in userData["tweets"]:
                text = tweet["text"]
                text = tokenize(text)
                # We remove punct, @, # etc
                text = [c for c in text if len(c) > 1]
                tokenizedtweets.append(text)
            # We test on 40 tweets:
            totalOverlapCheck = 0
            hasOverlapSum = 0
            tweetCountToCheck = self.tweetOverlapCheckCount
            if len(tokenizedtweets) < tweetCountToCheck:
                tweetCountToCheck = len(tokenizedtweets)
            for i in range(tweetCountToCheck):
                # We get a random tweet:
                randomIndex = getRandomInt(0, len(tokenizedtweets) - 1)
                randomTweet = tokenizedtweets[randomIndex]
                hasAnOverlap = False
                # We iterate all other tweets:
                for u in range(len(tokenizedtweets)):
                    # If we are not on the same tweet:
                    if u != randomIndex:
                        theTweetToCompare = tokenizedtweets[u]
                        # We check if there is an overlap:
                        if hasOverlap(randomTweet, theTweetToCompare, 3):
                            hasAnOverlap += True
                            break
                if hasAnOverlap:
                    hasOverlapSum += 1
                totalOverlapCheck += 1
            # Now the approximate prob that one random picked tweet has an
            # overlap is:
            overlapProb = hasOverlapSum / totalOverlapCheck
            # Now we transform the score to a positive feature:
            notOverlapProb = 1.0 - overlapProb
            # And we say that between 0.8 and 1.0 it's ok, but lower it's very bad:
            overlapScore = linearScore(notOverlapProb,
                                       x1=self.notGreat3GramOverlap[0],
                                       y1=0.0,
                                       x2=self.notGreat3GramOverlap[1],
                                       y2=1.0)
            # And we update the score:
            score += overlapScore * coeff
            featuresCount += coeff
            if TEST:
                print("overlapScore=" + str(overlapScore))

            # Finally we return the score:
            finalScore = score / featuresCount
            return truncateFloat(finalScore, self.scoreMaxDecimals)
        except Exception as e:
            logException(e, self, location="notBotScoreFunct")
            return self.defaultScore

    def relevanceScore(self, userData, *args, **kwargs):
        return self.relevanceSD.get(userData[self.userIdField],
                                    userData, *args, **kwargs)

    def relevanceScoreFunct(self, userId, userData):
        """
            This function score the relevance of the user for news recommandation
        """
        if not isUserData(userData):
            return self.defaultScore

        # We prepare features:
        score = 0.0
        featuresCount = 0.0

        try:
            # We start with eliminatory features:
            # hasEnoughOldTweets
            if not userData["has_enough_old_tweets"]:
                return self.defaultScore

            # tweet en ratio:
            if userData["tweets_en_ratio"] < self.enTweetsMinRatio:
                return self.defaultScore

            # Then we can make the real score:
            # scrapedTweetCount
            coeff = 0.3
            scrapedTweetCountScore = linearScore\
            (
                len(userData["tweets"]),
                self.notGreatScrapedTweetCountInterval[0],
                self.notGreatScrapedTweetCountInterval[1],
                stayBetween0And1=True,
            )
            if TEST:
                log("scrapedTweetCountScore=" + str(scrapedTweetCountScore), self)
            scrapedTweetCountScore = scrapedTweetCountScore * coeff
            score += scrapedTweetCountScore
            featuresCount += coeff

            # News count:
            coeff = 1.0
            if coeff > 0.0:
                newsCount = 0
                for tweet in userData["tweets"]:
                    for share in tweet["shares"]:
                        url = share["url"]
                        if self.nuf.isNews(url) or (self.shortenedAsNews and self.uns.isShortened(url)):
                            newsCount += 1
                if TEST:
                    log("newsCount=" + str(newsCount), self)
                newsCountScore = linearScore\
                (
                    newsCount,
                    self.notGreatNewsCountInterval[0],
                    self.notGreatNewsCountInterval[1],
                    stayBetween0And1=True,
                )
                newsCountScore = newsCountScore * coeff
                score += newsCountScore
                featuresCount += coeff

            # TODO test
            # News count estimation over shortened urls:
            coeff = 0.0
            if  coeff > 0.0:
                # The number of shortened urls that we know for sure it's news behind:
                unshortenedNewsCount = 0
                # The number of shortened url:
                shortenedCount = 0
                # The number of urls that were previously unshortend:
                unshortenedCount = 0
                for tweet in userData["tweets"]:
                    for share in tweet["shares"]:
                        url = share["url"]
                        if self.uns.isShortened(url):
                            shortenedCount += 1
                            unshortenedUrl = self.uns.unshort(url)
                            if unshortenedUrl is not None:
                                unshortenedCount += 1
                                if self.nuf.isNews(unshortenedUrl):
                                    unshortenedNewsCount += 1
                # Now we try to estimate the number of news which are behind shortened urls:
                newsRatio = unshortenedNewsCount / unshortenedCount
                newsCountApprox = int(newsRatio * shortenedCount)
                # And we add the score:
                newsCountApproxScore = linearScore\
                (
                    newsCountApprox,
                    self.notGreatNewsCountInterval[0],
                    self.notGreatNewsCountInterval[1],
                    stayBetween0And1=True,
                )
                newsCountApproxScore = newsCountApproxScore * coeff
                score += newsCountApproxScore
                featuresCount += coeff

            # Finally we return the score:
            finalScore = score / featuresCount
            return truncateFloat(finalScore, self.scoreMaxDecimals)
        except Exception as e:
            logException(e, self, location="relevanceScoreFunct")
            return self.defaultScore

    def isNotBot(self, userData):
        """
            This function will say if a user is not a bot (or a verified user...).
            It use the threshold notBotThreshold.
        """
        currentScore = self.notBotScore(userData)
        if currentScore >= self.notBotThreshold:
            return True
        return False

    def isRelevant(self, userData):
        """
            This function will say if a user is relevant for the recommender system.
            It use the threshold relevanceThreshold.
        """
        currentScore = self.relevanceScore(userData)
        if currentScore >= self.relevanceThreshold:
            return True
        return False

    def isRecUser(self, userData):
        """
            This function will say if a user is a rec user according to
            isRelevant and isNotBot methods
        """
        if self.isNotBot(userData) and self.isRelevant(userData):
            return True
        return False

    def overallScoreWith(self, currentNotBotScore, currentRelevanceScore):
        return (currentNotBotScore + currentRelevanceScore) / 2.0

    def overallScore(self, userData):
        currentNotBotScore = self.notBotScore(userData)
        currentRelevanceScore = self.relevanceScore(userData)
        return self.overallScoreWith(currentNotBotScore, currentRelevanceScore)

    def top(self):
        """
            This function will return all rec users sorted by relevance score
            for top not bot score, we give the top of
        """
        allNotBot = []
        for key, value in self.relevanceSD.items():
            if value >= self.relevanceThreshold:
                if self.notBotSD.has(key) and \
                self.notBotSD[key] >= self.notBotThreshold:
                    currentOverAllScore = self.overallScoreWith\
                    (
                        self.notBotSD[key],
                        value,
                    )
                    if TEST:
                        print("currentOverAllScore=" + str(currentOverAllScore))
                    allNotBot.append((key, currentOverAllScore))
        currentTop = sortBy(allNotBot, desc=True, index=1)
        log("Top for " + self.sdVersion + ":\n" + listToStr(currentTop[0:20]) + "\n...\n" + listToStr(currentTop[-20:]), self)
        log("Total for " + self.sdVersion + ": " + str(len(currentTop)), self)
        return currentTop

userCrawlSingleton = None
def getUserCrawlSingleton(dbName="twitter", collectionName="usercrawl",
                          logger=None, verbose=True):
    global userCrawlSingleton
    if userCrawlSingleton is None:
        try:
            (user, password, host) = getStudentMongoAuth()
            userCrawlSingleton = MongoCollection\
            (
                dbName, collectionName,
                logger=logger, verbose=verbose,
                user=user, password=password, host=host,
            )
        except: pass
    return userCrawlSingleton
class TwitterUser():
    """
        This class will cut too recent tweet for the recommendation.
        Because the crawling started at startTimestamp (1518727244),
        we keep only tweet which is < startTimestamp old.
    """
    def __init__\
    (
        self,
        userDataOrUserId,
        twitterUserScores=None,
        collection=None,
        logger=None,
        verbose=True,
        startTimestamp=1518727244,
        userIdField="user_id",
        allowRescrap=False,
    ):
        # We get all params:
        self.twitterUserScores = twitterUserScores
        self.userData = None
        self.userId = None
        if isinstance(userDataOrUserId, dict):
            self.userData = userDataOrUserId
        else:
            self.userId = userDataOrUserId
        self.collection = collection
        self.logger = logger
        self.verbose = verbose
        self.startTimestamp = startTimestamp
        self.userIdField = userIdField
        self.html = None

        # We make globalTwitterUserScores:
        if self.twitterUserScores is None:
            self.twitterUserScores = getTwitterUserScoresSingleton()

        # We get data if this is userId which is given:
        if self.userData is None:
            if self.userId is None:
                raise Exception("Please set userData or userId as userDataOrUserId.")
            else:
                if self.collection is None:
                    self.collection = getUserCrawlSingleton(logger=self.logger,
                                                            verbose=self.verbose)
                    if self.collection is None:
                        raise Exception("Please set the usercrawl collection.")
                    self.userData = self.collection.findOne({self.userIdField: self.userId})

        # We reduce userData to the scrap:
        if dictContains(self.userData, "scrap"):
            self.html = self.userData["html"]
            self.scrapVersion = self.userData["version"]
            if self.scrapVersion != twittercrawlerVersion and allowRescrap:
                tus = TwitterScraper()
                userData = tus.scrapUser(self.html)
                self.scrapVersion = twittercrawlerVersion
                self.userData = userData
            else:
                self.userData = self.userData["scrap"]
        self.userId = self.userData[self.userIdField]

        # We cut all recent tweets:
        if self.startTimestamp is not None:
            self.cutTweets()

        if TEST:
            userDataToReadableTmpFile(self.userData)

    def getHtml(self):
        return self.html

    def getUserId(self):
        return self.userId
    def getUserData(self):
        return self.userData

    def notBotScore(self, *args, **kwargs):
        return self.twitterUserScores.notBotScore(self.userData, *args, **kwargs)
    def relevanceScore(self, *args, **kwargs):
        return self.twitterUserScores.relevanceScore(self.userData, *args, **kwargs)

    def cutTweets(self):
        """
            We cut all tweets > startTimestamp:
        """
        newTweets = []
        for tweet in self.userData["tweets"]:
            if dictContains(tweet, "timestamp") and tweet["timestamp"] < self.startTimestamp:
                newTweets.append(tweet)
#                 if TEST:
#                     log("We kept this tweet (" + timestampToDate(tweet["timestamp"]) + ")", self)
#             else:
#                 if TEST:
#                     log("We deleted this tweet (" + timestampToDate(tweet["timestamp"]) + ")", self)
        self.userData["tweets"] = newTweets


# WARNING: set unshortenerReadOnly as False

