


class TwitterUserScores():
    def __init__\
    (
        self

    ):
        pass








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




