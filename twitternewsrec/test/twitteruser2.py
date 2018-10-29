# coding: utf-8
# pew in newscrawler-venv python ./test/twitteruser2.py

import os
import sys
sys.path.append('../')

import unittest
import doctest
from newscrawler import config as tuConf
from newscrawler import twitteruser2
from newscrawler.twitteruser2 import *

# The level allow the unit test execution to choose only the top level test
mini = 0
maxi = 4
assert mini <= maxi

print("==============\nStarting unit tests...")

if mini <= 0 <= maxi:
    class DocTest(unittest.TestCase):
        def testDoctests(self):
            """Run doctests"""
            doctest.testmod(twitteruser2)

RESET_LOCAL_COLLECTION = False
RESET_LOCAL_SCORES = True

if mini <= 1 <= maxi:
    class Test1(unittest.TestCase):
        def setUp(self):
#              super(Test1, self).__init__(*args, **kwargs)
             self.initDatabase()

        def initDatabase(self):
            tuConf.TEST = True
            tuConf.__version__ = "0.0.1-test"
            if RESET_LOCAL_SCORES:
                tuConf.getTwitterUserScoreSingleton().reset()
            remoteCollection = tuConf.getUserCrawlSingleton()
            self.localCollection = MongoCollection\
            (
                "test", "usercrawl",
                user=None, password=None, host="localhost",
                indexNotUniqueOn=\
                [
                    "scrap.page_state",
                    "scrap.has_enough_old_tweets",
                    "date_limit",
                    "version",
                    "hostname",
                ],
                indexOn=["user_id", "url"],
            )
            usersToAdd = \
            {
                "https://twitter.com/lukepruett",
                "11730942",
                "15929200",
                "https://twitter.com/fariskhanNY",
                "https://twitter.com/AleannaSiacon",
                "843643812",
                "7613582",
                "47168485",
                "https://twitter.com/KNBC4Desk",
                "205856540",
                "21277285",
                "3390472065",
                "11730942",
                "15929200",
                "1851861800",
                "https://twitter.com/AlanaSemuels",
                "https://twitter.com/joedrape",
                "https://twitter.com/euforaHQ",
            }

            if len(self.localCollection) < int(0.8 * len(usersToAdd)) or RESET_LOCAL_COLLECTION:
                print("Deleting the database...")
                localCollection.resetCollection(security=False)
                print("Starting the database initialization...")
                for userIdOrUrl in usersToAdd:
                    key = "user_id"
                    if "http" in userIdOrUrl:
                        key = "url"
                    query = {key: userIdOrUrl}
                    if not localCollection.has(query):
                        userData = remoteCollection.findOne(query)
                        self.localCollection.insert(userData)
                print("Database initialization DONE.")
            else:
                print("The collection was already made...")
            # We replace the userCrawlSingleton:
            tuConf.userCrawlSingleton = self.localCollection



        def test1(self):
            query = {"url": "https://twitter.com/lukepruett"}
            query = {}
            for current in self.localCollection.find(query):
                tu = TwitterUser(current)
                tu.getScores()
                print(repr(tu))
#                 tu.toTmpFile()


if __name__ == '__main__':
    unittest.main() # Or execute as Python unit-test in eclipse








