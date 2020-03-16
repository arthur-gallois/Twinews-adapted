# pew in st-venv python /home/hayj/Workspace/Python/Datasets/TwitterNewsrec/twitternewsrec/extractor/wsjtest.py

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

# from domainduplicate import config as ddConf
# ddConf.useMongodb = False
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.logger import *
from datatools.jsonutils import *
from datatools.url import *
from newstools.newsscraper import *
from twinews.user.topuser import *
from twinews.user.twitteruser import *
from twinews.extractor.utils import *
from datastructuretools.processing import *

text = """
http://on.wsj.com/2nnOcKx
https://www.wsj.com/articles/six-chinese-ships-covertly-aided-north-korea-the-u-s-was-watching-1516296799
https://www.wsj.com/articles/why-uber-can-find-you-but-911-cant-1515326400
https://www.wsj.com/articles/the-island-where-chinese-mothers-deliver-american-babies-1513852203
https://www.wsj.com/articles/chinas-tech-giants-have-a-second-job-helping-the-government-see-everything-1512056284
https://www.wsj.com/articles/surveillance-cameras-made-by-china-are-hanging-all-over-the-u-s-1510513949
https://www.wsj.com/articles/what-to-do-with-dead-malls-1508936402
https://www.wsj.com/articles/lacroix-fizzy-water-is-everyones-favorite-nobody-knows-whats-in-it-1505313912?mod=e2fb
http://on.wsj.com/2uvYNbU
https://www.wsj.com/articles/the-internet-is-filling-up-because-indians-are-sending-millions-of-good-morning-texts-1516640068
http://on.wsj.com/2gr0u4C
https://www.wsj.com/articles/the-variedand-globalthreats-confronting-democracy-1511193763
https://www.wsj.com/articles/epa-withdraws-air-pollution-policy-1516935178
https://www.wsj.com/articles/special-counsel-mueller-probes-jared-kushners-contact-with-foreign-leaders-1511306515
https://www.wsj.com/articles/president-trump-spent-nearly-one-third-of-first-year-in-office-at-trump-owned-properties-1514206800
http://on.wsj.com/2yhYgqY
https://www.wsj.com/articles/trump-cancels-mar-a-lago-appearance-amid-government-shutdown-1516493796
http://on.wsj.com/2BMxx9b
https://www.wsj.com/articles/trump-lawyer-arranged-130-000-payment-for-adult-film-stars-silence-1515787678
"""




newsCrawl = getNewsCrawlSingleton()
urlParser = URLParser()
urls = urlParser.strToUrls(text)
newScraper = NewsScraper()
# for url in urls:
for data in newsCrawl.find(limit=1000):
	url = data["url"]
	print("\n" * 3 + "-" * 40 + "\n" * 3)
	printLTS(newScraper.scrapAll(newsCrawl[url]["html"], reduce=True))
	print("\n\nsmart")
	smart = newScraper.smartScrap(newsCrawl[url]["html"], reduce=False)
	printLTS(smart)
	print()
	print()
	print("isGoodNews: " + str(isGoodNews(smart)))
	input()
