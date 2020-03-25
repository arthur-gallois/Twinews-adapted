from datatools.jsonutils import *
from systemtools.basics import *
from systemtools.location import *
from systemtools.printer import *


print(sortedGlob(homeDir() + "/*.bz2"))


users = [e for e in NDJson('/home/hayj/Data/Twinews/twinews1/users/part0.bz2')]
users = users[:4]
bp(users)
toJsonFile(users, homeDir() + "/users.json")


news = [e for e in NDJson('/home/hayj/Data/Twinews/twinews1/news/bbc.com.bz2')]
news = news[:4]
bp(news)
toJsonFile(news, homeDir() + "/news.json")

