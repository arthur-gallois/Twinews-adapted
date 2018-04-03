# Twitter news

First we crawl all news : if the url in the tweet is a news (NewsURLFilter class) or is a shortened url (Unshortener class), we crawl it.

Next we decide if each shares is an item according to the presence of the url in the collection and the scrap text is sufficient (ItemHandler).

Before this we have to filter user according to some criterion : he must share different domain url, have tweets with only text...