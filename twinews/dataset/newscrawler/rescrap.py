# nn 3 pew in twitternewsrec-venv python ~/wm-dist-tmp/TwitterNewsrec/twitternewsrec/newscrawler/rescrap.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

from systemtools.basics import *
from systemtools.duration import *
from systemtools.file import *
from systemtools.logger import *
from systemtools.location import *
from systemtools.hayj import *
from systemtools.system import *
from newstools.newsscraper import *
from databasetools.mongo import *
from systemtools.hayj import *
from twinews.user.twitteruser import *
from twinews.newscrawler.utils import *
from twinews.user.utils import *


def rescrap():
	raise Exception("DEPRECATED, refaire la fonction...")
	logger = Logger("rescrap.log")
	newsScraper = NewsScraper(logger=logger)
	newsCrawl = getNewsCrawlSingleton(write=True)
	ids = newsCrawl.distinct("_id")
	pbar = ProgressBar(len(ids), printRatio=0.0000001, logger=logger)
	doneCount = 0
	for id in ids:
		try:
			newsData = newsCrawl.findOne({"_id": id})
			isDone = False
			if (not dictContains(newsData, "scrap")) or dictContains(newsData["scrap"], "boilerpipe") or (not dictContains(newsData["scrap"], "text")):
				scrap = newsScraper.smartScrap(newsData["html"])
				newsCrawl.updateOne({"_id": newsData["_id"]}, {'$set': {'scrap': dictToMongoStorable(scrap)}})
				doneCount += 1
				isDone = True
			if isDone:
				pbar.tic(newsData["url"] + "... >>>>>>>>>>>>>> DONE <<<<<<<<<<<<<<<")
			else:
				pbar.tic(newsData["url"][:38] + "... SKIPPED")
		except Exception as e:
			logException(e, logger)

	logger.log("DONE COUNT: " + str(doneCount))


def removeNone():
	logger = Logger("remove-none.log")
	newsCrawl = getNewsCrawlSingleton(write=True)
	ids = newsCrawl.distinct("_id")
	pbar = ProgressBar(len(ids), printRatio=0.01, logger=logger, message="Getting urls to be removed")
	toRemove = []
	for id in ids:
		try:
			newsData = newsCrawl.findOne({"_id": id})
			if not dictContains(newsData["scrap"], "text"):
				toRemove.append(id)
			pbar.tic()
		except Exception as e:
			logException(e, logger)
	logger.log("To delete: " + str(len(toRemove)))
	if len(toRemove) < 10000:
		pbar = ProgressBar(len(toRemove), printRatio=0.000001, logger=logger, message="Removing")
		for id in toRemove:
			newsCrawl.deleteOne({"_id": id})
			pbar.tic(id)
	else:
		logger.log("Too much to remove...")

def test1():
	newsScraper = NewsScraper()
	newsCrawl = getNewsCrawlSingleton(write=True)
	urls = ["https://wamu.org/story/18/01/05/ahead-key-vote-bowser-comes-public-financing-political-campaigns-d-c/"]
	for url in urls:
		newsData = newsCrawl.findOne({"url": url})
		strToTmpFile(newsData["html"], "test", ext="html")
		strToTmpFile(html2Text(newsData["html"]), "text", ext="html")
		scrap = newsScraper.scrapAll(newsData["html"])
		printLTS(scrap)

if __name__ == '__main__':
	# rescrap()
	# test1()
	removeNone()