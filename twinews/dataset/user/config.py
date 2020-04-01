


################## Collection #####################
lastTweetTimestamp = 1518727244 # 1518727244
userIdField="user_id"




################## Not bot score calculation #####################
followingCountInterval = (5, 10000)
tweetCountInterval = (30, 1000000)
followerCountInterval = (2, 10000)
tweetsWithShareRatios = (0.05, 0.95)
tweetsWithAtreplyRatios = (0.08, 0.99)
tweetsWithHashtagRatios = (0.08, 0.99)
maxRatioDomainBadInterval = (0.35, 0.65) # And greater is very bad
notGreat3GramOverlap = (0.0, 0.8)
tweetOverlapCheckCount = 200 # 300 = 10 seconds, 20 = 1 second per user
minRatioOfLeastType = 0.05


################## Relevance score calculation #####################
enTweetsMinRatio = 0.8
notGreatScrapedTweetCountInterval = (30, 150)
notGreatNewsCountInterval = (4, 25) # (4, 13)



################## Thresholds and defaults values #####################
defaultScore = 0.0
scoreMaxDecimals = 2
# notBotThreshold=0.95
# relevanceThreshold=0.85


################## Version #####################
twitterUserScoreVersion = "0.0.12" # the last is 0.0.12 (12/09/18)
oldNotBotScoreVersionToCopy = "0.0.4" # "0.0.4"
topUserVersion = "0.0.4"


