# coding: utf-8

from systemtools.basics import *
from systemtools.logger import *
from systemtools.file import *
from systemtools.location import *
from systemtools.system import *
from datatools.jsonreader import *
from datatools.csvreader import *
from datatools.url import *
from newstools.newsurlfilter import *
from unshortener.unshortener import *
from nlptools.basics import *
from nlptools.tokenizer import *
import random
import copy
from twitternewsrec.user.utils import *
from twitternewsrec.newscrawler.utils import *
from twitternewsrec.user import config as tuConf
from multiprocessing import Lock, Process


class TwitterUser():
    def __init__\
    (
        self,
        userDataOrUserId,
        userCrawlCollection=None,
        logger=None,
        verbose=True,
        lazyLoad=True,
    ):
        # We init all vars:
        self.userDataOrUserId = userDataOrUserId
        if isinstance(self.userDataOrUserId, dict) and dictContains(self.userDataOrUserId, "scrap"):
            self.userDataOrUserId = self.userDataOrUserId["scrap"]
        self.lazyLoad = lazyLoad
        self.logger = logger
        self.verbose = verbose
        self.scoresSD = getTwitterUserScoreSD(logger=self.logger, verbose=self.verbose)
        self.oldScoresSD = getOldTwitterUserScoreSD(logger=self.logger, verbose=self.verbose)
        self.uns = getReadOnlyUnshortenerSingleton(logger=self.logger, verbose=self.verbose)
        self.nuf = getNewsUrlFilterSingleton(logger=self.logger, verbose=self.verbose)
        self.newsCrawl = getNewsCrawlSingleton(logger=self.logger, verbose=self.verbose)
        self.urlParser = getURLParserSingleton(logger=self.logger, verbose=self.verbose)

        # The extractor config for datset scores:
        self.extractorConfig = jsonToDict(getParentDir(execDir(__file__)) + "/extractor/config.json")

        # We init all data:
        self.alreadyCutTooRecentTweets = False
        self.userCrawlCollection = userCrawlCollection
        self.data = None
        self.id = None
        if TwitterUser.isUserData(self.userDataOrUserId):
            self.data = self.userDataOrUserId
            if dictContains(self.data, "scrap"):
                self.data = self.data["scrap"]
            self.id = self.data["user_id"]
        else:
            self.id = self.userDataOrUserId
        self.scores = None
        if not self.lazyLoad:
            self.initData()


    def getData(self):
        self.initData()
        return self.data


    @staticmethod
    def isUserData(userData):
        """
            This function check if the object given is a dict
            representing a user (from mongodb)
        """
        if userData is None or \
        not isinstance(userData, dict) or \
        not dictContains(userData, "tweets") or \
        not dictContains(userData, "user_id"):
            return False
        return True

    def initData(self, ignoreHtml=True):
        if self.data is None or self.id is None:
            if self.data is None:
                if self.userCrawlCollection is None:
                    self.userCrawlCollection = getUserCrawlSingleton(logger=self.logger, verbose=self.verbose)
                projection = None
                if ignoreHtml:
                    projection = {"html": False}
                self.data = self.userCrawlCollection.findOne({tuConf.userIdField: self.id}, projection=projection)
            elif dictContains(self.data, tuConf.userIdField):
                self.id = self.data[tuConf.userIdField]
            if self.id is None or self.data is None:
                raise Exception("User not found.")
            if dictContains(self.data, "scrap"):
                self.data = self.data["scrap"]
        self.cutTooRecentTweets()

    def cutTooRecentTweets(self, lastTweetTimestamp=None):
        if not self.alreadyCutTooRecentTweets:
            if lastTweetTimestamp is None:
                lastTweetTimestamp = tuConf.lastTweetTimestamp
            if lastTweetTimestamp is not None:
                newTweets = []
                for tweet in self.data["tweets"]:
                    if dictContains(tweet, "timestamp") and tweet["timestamp"] < lastTweetTimestamp:
                        newTweets.append(tweet)
                self.data["tweets"] = newTweets
            self.alreadyCutTooRecentTweets = True
 
    def __getUrlCounts(self):
        # We init the dict:
        result = dict()
        for key in \
        [
            "shortenedCount", # the number of shortened urls
            "unshortenedCount", # the number of already unshortened urls
            "unshortenedNewsCount", # the number of already unshortened urls which are news
            "notShortenedCount", # the number of urls (not shortened)
            "notShortenedNewsCount", # the number of news (not shortened)
            "newsCount", # the number of news
            "urlCount", # the number of urls
            "estimatedNewsCount", # the number of news + an estimation of the number of news in shortened urls
            "optimisticNewsCount", # newsCount + unshortenedNewsCount + all not unshortened urls
            "crawledNewsCount", # The number of news which are crawled with status success (shortened or not)
            "remainingShortenedCount", # The number of shortened share to be unshortned (crawled)
            "remainingNewsCount", # The number of news to be crawled
            "goodNewsCount", # The number of crawled good news according to the isGoodNews function
        ]:
            result[key] = 0
        # We count all:
        for share in self.getShares(removeDuplicates=True):
            result["urlCount"] += 1
            if self.uns.isShortener(share):
                result["shortenedCount"] += 1
                if self.uns.isAlreadyUnshortened(share):
                    result["unshortenedCount"] += 1
                    if self.nuf.isNews(share):
                        # Here we check if we have the url in the news crawl collection:
                        if share not in self.newsCrawl:
                            logError("We found an unshortened news but it doesn't exist in newscrawl... maybe invalid or 404... " + str(share), self)
                        result["unshortenedNewsCount"] += 1
                        result["newsCount"] += 1
                        if self.newsCrawl.has({"url": share, "status": "success"}):
                            result["crawledNewsCount"] += 1
                        if isGoodNews(self.newsCrawl.findOne({"url": share}),
                            minTextLength=self.extractorConfig["newsMinTextLength"],
                            minMeanLineLength=self.extractorConfig["newsMinMeanLineLength"],
                            logger=self.logger):
                            result["goodNewsCount"] += 1
            else:
                result["notShortenedCount"] += 1
                if self.nuf.isNews(share):
                    result["notShortenedNewsCount"] += 1
                    result["newsCount"] += 1
                    if self.newsCrawl.has({"url": share, "status": "success"}):
                        result["crawledNewsCount"] += 1
                    if isGoodNews(self.newsCrawl.findOne({"url": share}),
                        minTextLength=self.extractorConfig["newsMinTextLength"],
                        minMeanLineLength=self.extractorConfig["newsMinMeanLineLength"],
                        logger=self.logger):
                        result["goodNewsCount"] += 1

        # We estimate news:
        result["estimatedNewsCount"] = result["newsCount"]
        if result["unshortenedCount"] > 0:
            rate = result["unshortenedNewsCount"] / result["unshortenedCount"]
            estimation = math.floor(rate * float(result["shortenedCount"] - result["unshortenedCount"]))
            result["estimatedNewsCount"] += estimation
        # If we are optimistic:
        result["optimisticNewsCount"] = result["newsCount"] + result["shortenedCount"] - result["unshortenedCount"]
        # We calculate remainingShortenedCount and remainingNewsCount:
        result["remainingShortenedCount"] = result["shortenedCount"] - result["unshortenedCount"]
        result["remainingNewsCount"] = result["newsCount"] - result["crawledNewsCount"]
        # We return all counts:
        return result

    def getScores(self, eraseCache=False, skipNotBotScore=False):
        """
            The notBotScore take a lot of processing time
            (because of a high tweetOverlapCheckCount),
            so you can skip it using skipNotBotScore=True,
            but if you set it as True, the cache will not be affected
        """
        if self.scores is not None and len(self.scores) > 0:
            return self.scores
        if not eraseCache and self.id in self.scoresSD:
            return self.scoresSD[self.id]
        self.initData()
        self.scores = dict()
        self.scores = mergeDicts(self.scores, self.__getUrlCounts())
        if not skipNotBotScore:
            if self.oldScoresSD is not None and self.id in self.oldScoresSD:
                self.scores = mergeDicts(self.scores,
                    {"notBotScore": self.oldScoresSD[self.id]["notBotScore"]})
            else:
                self.scores = mergeDicts(self.scores,
                        {"notBotScore": self.getNotBotScore()})
        self.scores = mergeDicts(self.scores,
                {"relevanceScore": self.getRelevanceScore(
                newsCount=self.scores["newsCount"])})
        self.scores = mergeDicts(self.scores,
                {"estimatedRelevanceScore": self.getRelevanceScore(
                newsCount=self.scores["estimatedNewsCount"])})
        self.scores = mergeDicts(self.scores,
                {"optimisticRelevanceScore": self.getRelevanceScore(
                newsCount=self.scores["optimisticNewsCount"])})
        self.scores = mergeDicts(self.scores,
                {"datasetRelevanceScore": self.getRelevanceScore(
                newsCount=self.scores["goodNewsCount"])})
        if not skipNotBotScore:
            self.scoresSD[self.id] = self.scores
        return self.scores

    def __str__(self):
        return str(self.id)

    def __repr__(self, displayTweets=True, displayShares=True):
        userData = copy.deepcopy(self.data)
        userData = sortByKey(userData)
        newLine = "\n"
        bigSeparation = "\n" * 1
        littleSeparation = "\n" * 1
        text = ""
        text += "----- Importants infos -----" + newLine
        theTab = []
        theTab.append(["name", userData["name"]])
        theTab.append(["url", userData["url"]])
        theTab.append(["tweet count", str(len(userData["tweets"]))])
        for key in \
        [
            "has_enough_old_tweets",
            "follower_count",
            "following_count",
        ]:
            theTab.append([key, str(userData[key])])
        text += tabulate(theTab)
        text += bigSeparation
        tweets = userData["tweets"]
        del userData["tweets"]

        text += bigSeparation
        if "hover_users" in userData:
            del userData["hover_users"]
        del userData["joindate_text"]
        del userData["consecutive_old_tweets"]
        text += "----- Others infos -----" + newLine
        theTab = []
        for key, value in sortByKey(userData).items():
            theTab.append([key, str(userData[key])])
        text += tabulate(theTab)
        text += newLine
        text += bigSeparation
        text += "----- Counts -----" + newLine
        theTab = []
        for key, value in sortByKey(self.getScores()).items():
            if "Count" in key:
                theTab.append([key, str(value)])
        text += tabulate(theTab)
        text += newLine
        text += littleSeparation
        text += "----- Scores -----" + newLine
        theTab = []
        for key, value in sortByKey(self.getScores()).items():
            if "Score" in key:
                theTab.append([key, str(value)])
        text += tabulate(theTab)
        text += newLine

        if displayShares:
            text += bigSeparation
            text += "----- Shares -----" + newLine
            theTab = []
            for share in self.getShares(removeDuplicates=True):
                try:
                    row = []
                    row.append(self.urlParser.getDomain(share))
                    if not self.uns.isShortener(share):
                        row.append("n/a")
                    else:
                        if self.uns.isAlreadyUnshortened(share):
                            row[0] += " (" + self.uns.request(share)["lastUrlDomain"] + ')'
                            row.append(str(True))
                        else:
                            row.append(str(False))
                    row.append(str(self.nuf.isNews(share)))
                    row.append(str(self.newsCrawl.has(share)))
                    if row[1] == "False":
                        row[2] = "False (n/a)"
                    theTab.append(row)
                except Exception as e:
                    logException(e, self)
            theTab = sortBy(theTab, index=1, desc=True)
            theTab = sortBy(theTab, index=3, desc=True)
            theTab = sortBy(theTab, index=2, desc=True)
            theTab = [["domain", "isAlreadyUnshortened", "isNews", "isCrawled"]] + theTab
            text += tabulate(theTab)
            text += newLine

        if displayTweets:
            text += bigSeparation
            text += "----- Tweets -----" + newLine
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
                text += littleSeparation * 2

        text += bigSeparation * 3
        return text

    def toTmpFile(self, *args, fileName="readable-tmp-twitter-user.txt", **kwargs):
        self.initData()
        filePath = tmpDir() + "/" + fileName
        strToFile(repr(self, *args, **kwargs), filePath)

    def getNotBotScore(self):
        """
            This function give a score which try to say if the user is
            a normal user (not a bot, not a leader or verified user...).
        """
        self.initData()
        userData = self.data
        userId = self.id

        # We prepare features:
        score = 0.0
        featuresCount = 0.0

        try:
            # We start with eliminatory features:
            # format:
            if not TwitterUser.isUserData(userData):
                return tuConf.defaultScore

            # Verified:
            if userData["verified"]:
                return tuConf.defaultScore

            # Tweet count > 0:
            if not dictContains(userData, "tweets") or len(userData["tweets"]) == 0:
                return tuConf.defaultScore

            # hasGoodFollowingCount
            coeff = 0.6
            if dictContains(userData, "following_count"):
                if userData["following_count"] >= tuConf.followingCountInterval[0] and \
                userData["following_count"] <= tuConf.followingCountInterval[1]:
                    score += coeff
            featuresCount += coeff

            # hasGoodFollowerCount
            coeff = 0.6
            if dictContains(userData, "follower_count"):
                if userData["follower_count"] >= tuConf.followerCountInterval[0] and \
                userData["follower_count"] <= tuConf.followerCountInterval[1]:
                    score += 1
            featuresCount += 1

            # hasGoodTweetCount
            coeff = 0.6
            if dictContains(userData, "tweet_count"):
                if userData["tweet_count"] >= tuConf.tweetCountInterval[0] and \
                userData["tweet_count"] <= tuConf.tweetCountInterval[1]:
                    score += coeff
            featuresCount += coeff

            # shares etc ratios:
            coeff = 1.0
            for key, ratios in \
            [
                ("shares", tuConf.tweetsWithShareRatios),
                ("atreplies", tuConf.tweetsWithAtreplyRatios),
                ("hashtags", tuConf.tweetsWithHashtagRatios),
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
            if theMin > tuConf.minRatioOfLeastType:
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
#             if TEST:
#                 print("differentUsernamesScore=" + str(differentUsernamesScore))
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
#                 if TEST:
#                     print("Has different hashtags and atreplies: " + str(currentScore))

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
#                 if TEST:
#                     print("maxRatio=" + str(maxRatio))
#                     print("maxDomain=" + str(domainsDict[0][0]))
#                     printLTS(domainsDict)
                differentDomainsScore = linearScore\
                (
                    maxRatio,
                    x1=tuConf.maxRatioDomainBadInterval[0], y1=1.0,
                    x2=tuConf.maxRatioDomainBadInterval[1], y2=0.0,
                )
            score += differentDomainsScore * coeff
            featuresCount += coeff
#             if TEST:
#                 print("differentDomainsScore=" + str(differentDomainsScore))

            
            # tt = TicToc(logger=self.logger)
            # tt.tic()

            # for aa in [50, 100, 200, 300]:
            #     tuConf.tweetOverlapCheckCount = aa
            #     log(tuConf.tweetOverlapCheckCount, self)
            
            # We compute the approximate probability that a random tweet or a
            # retweet has an other tweet or retweet with a 3-gram overlap
            # First we lower and tokenize all tweets:
#             log("We compute the approximate probability that a random tweet or...", self)
            coeff = 2.0
            tokenizedtweets = []
            for tweet in userData["tweets"]:
                text = tweet["text"]
                text = tokenize(text)
                if text is not None:
                    # We remove punct, @, # etc
                    text = [c for c in text if len(c) > 1]
                    tokenizedtweets.append(text)
            # We test on 40 tweets:
            totalOverlapCheck = 0
            hasOverlapSum = 0
            tweetCountToCheck = tuConf.tweetOverlapCheckCount
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
                                       x1=tuConf.notGreat3GramOverlap[0],
                                       y1=0.0,
                                       x2=tuConf.notGreat3GramOverlap[1],
                                       y2=1.0)
            # And we update the score:
            score += overlapScore * coeff
            featuresCount += coeff
#             if TEST:
#                 print("overlapScore=" + str(overlapScore))
#             log("DONE.", self.logger)

            # log(notOverlapProb, self)

            # tt.tic()

            # Finally we return the score:
            finalScore = score / featuresCount
            return truncateFloat(finalScore, tuConf.scoreMaxDecimals)
        except Exception as e:
            logException(e, self, location="notBotScoreFunct")
            return tuConf.defaultScore


    def isNotBot(self, notBotThreshold=None):
        """
            This function will say if a user is not a bot (or a verified user...).
            It use the threshold notBotThreshold.
        """
        self.initData()
        if notBotThreshold is None:
            notBotThreshold = tuConf.notBotThreshold
        currentScore = self.getNotBotScore()
        if currentScore >= self.notBotThreshold:
            return True
        return False

    def isRecUser(self, userData):
        """
            This function will say if a user is a rec user according to
            isRelevant and isNotBot methods
        """
        self.initData()
        return self.isNotBot() and self.isRelevant()


    def getRelevanceScore(self, newsCount):
        """
            This function score the relevance of the user for news recommandation
        """
        self.initData()
        
        userData = self.data
        userId = self.id

        # We prepare features:
        score = 0.0
        featuresCount = 0.0

        try:
            # We start with eliminatory features:
            if not TwitterUser.isUserData(userData):
                return tuConf.defaultScore

            # hasEnoughOldTweets
            if not userData["has_enough_old_tweets"]:
                return tuConf.defaultScore

            # tweet en ratio:
            if userData["tweets_en_ratio"] < tuConf.enTweetsMinRatio:
                return tuConf.defaultScore

            # Then we can make the real score:
            # scrapedTweetCount
            coeff = 0.3
            scrapedTweetCountScore = linearScore\
            (
                len(userData["tweets"]),
                tuConf.notGreatScrapedTweetCountInterval[0],
                tuConf.notGreatScrapedTweetCountInterval[1],
                stayBetween0And1=True,
            )
#             if TEST:
#                 log("scrapedTweetCountScore=" + str(scrapedTweetCountScore), self)
            scrapedTweetCountScore = scrapedTweetCountScore * coeff
            score += scrapedTweetCountScore
            featuresCount += coeff

            # News count:
            coeff = 1.0
            if coeff > 0.0:
                newsCountScore = linearScore\
                (
                    newsCount,
                    tuConf.notGreatNewsCountInterval[0],
                    tuConf.notGreatNewsCountInterval[1],
                    stayBetween0And1=True,
                )
                newsCountScore = newsCountScore * coeff
                score += newsCountScore
                featuresCount += coeff

            # Finally we return the score:
            finalScore = score / featuresCount
            return truncateFloat(finalScore, tuConf.scoreMaxDecimals)
        except Exception as e:
            logException(e, self, location="relevanceScoreFunct")
            return self.defaultScore

    def getShares(self, removeDuplicates=True):
        self.initData()
        if dictContains(self.data, "tweets"):
            shares = []
            for tweet in self.data["tweets"]:
                for share in tweet["shares"]:
                    url = share["url"]
                    if self.urlParser.isNormalizable(url):
                        url = self.urlParser.normalize(url)
                        shares.append(url)
                    else:
                        logError(url + " is not normalizable.", self)
        alreadyYielded = set()
        for share in shares:
            if (not removeDuplicates) or (share not in alreadyYielded):
                yield share
                alreadyYielded.add(share)

    def getNews(self, ignoreAlreadyCrawled=False):
        for current in self.getShares():
            if self.nuf.isNews(current):
                if ignoreAlreadyCrawled and current in self.newsCrawl:
                    continue
                yield current

    def getShortened(self, ignoreAlreadyUnshortened=False):
        for current in self.getShares():
            if self.uns.isShortener(current):
                if ignoreAlreadyUnshortened and self.uns.isAlreadyUnshortened(current):
                    if self.nuf.isNews(current) and current not in self.newsCrawl:
                        logWarning("This url was unshortened but is not in newscrawl: " + current, self)
                    continue
                yield current




