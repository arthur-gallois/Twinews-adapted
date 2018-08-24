
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from twitternewsrec.newscrawler.utils import *
from nlptools.overlap import *

def reduceDuplicates(newsData, logger=None, verbose=True, similarityThreshold=0.93, ngramsMin=4, batchMaxSize=800):
	texts = []
	for currentNewsData in newsData:
		texts.append(currentNewsData["scrap"]["boilerpipe"]["text"])
	# First we aggregate exacts sames documents with findDuplicates(texts) and same documents according to ngram overlap with the Overlap class:
	duplicatessSame = findDuplicates(texts)
	o = Overlap(texts, verbose=verbose, ngramsMin=ngramsMin, batchMaxSize=batchMaxSize)
	duplicatessNgram = o.findDuplicates(threshold=similarityThreshold)
	# Then we merge duplicates:
	duplicatess = mergeDuplicates([duplicatessSame, duplicatessNgram])
	# And we reconstruct all:
	newNewsData = [] # We keep only one news per duplicates
	urlMapping = dict() # We retain all urls per duplicates {<url>: <url>}
	# We insert all duplicates:
	i = 0
	for duplicates in duplicatess:
		duplicates = list(duplicates)
		newNewsData.append(newsData[duplicates[0]])
		megaUrl = newsData[duplicates[0]]["url"]
		for duplicateId in duplicates:
			urlMapping[newsData[duplicateId]["url"]] = megaUrl
	# We insert all others news:
	for currentNewsData in newsData:
		if currentNewsData["url"] not in urlMapping:
			urlMapping[currentNewsData["url"]] = currentNewsData["url"]
			newNewsData.append(currentNewsData)
	return newNewsData, urlMapping

if __name__ == '__main__':
	# Il y a ~63 sur 580 news qui vont être jettées à cause de duplicates
	# Donc urlMapping fait 580 et newsData fait ~ 580 - 63
    newsData = []
    newsCrawl = getNewsCrawlSingleton()
    urls = list(set(fileToStrList(execDir(__file__) + "/testdata/nytimes.txt")))
    for url in urls:
    	currentNewsData = newsCrawl[url]
    	newsData.append(currentNewsData)
    newsData, urlMapping = reduceDuplicates(newsData, batchMaxSize=20, similarityThreshold=0.3)
    print(len(newsData))
    print(len(urlMapping))
    for url in urls:
    	if url not in urlMapping:
    		print(url)
    # printLTS(reduceDictStr(newsData))
    # printLTS(urlMapping)
