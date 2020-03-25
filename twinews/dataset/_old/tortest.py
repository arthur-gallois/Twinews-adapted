import requests
from datatools.url import *
from datatools.bashscripts import BashScripts
from urllib.request import urlopen
from systemtools.basics import *
from systemtools.location import *
from systemtools.logger import *
import requests.auth
from datastructuretools.hashmap import *
from hjwebbrowser.utils import *
from hjwebbrowser.tor import *
from hjwebbrowser.browser import *
try:
    from newstools.newsscraper import *
except: pass
from hjwebbrowser.httpbrowser import *
from bs4 import BeautifulSoup
import socks
import socket
import sh


def torTest3():
    tor = getTorSingleton(portCount=10, initSleepTime=0.1)
    b = HTTPBrowser()
    for i in range(1):
        b.setProxy(tor.getRandomProxy())
        print(b.get("http://httpbin.org/ip")["html"])
    tor.stop()


def torTest1():
    urls = URLParser().strToUrls(\
    """
    http://bit.ly/girlgazefilm
    http://bit.ly/2nxFv2A was in the Unshortener database!
    http://bit.ly/2j1KHKD was in the Unshortener database!
    http://bit.ly/2y4y3B4 was in the Unshortener database!
    http://bit.ly/2AMS4sE was in the Unshortener database!
    http://bit.ly/2iwRziH was in the Unshortener database
    """)
    printLTS(urls)

#     def get_tor_session():
#         session = requests.session()
#         # Tor uses the 9050 port as the default socks port
#         session.proxies = {'http':  'socks5://127.0.0.1:9050',
#                            'https': 'socks5://127.0.0.1:9050'}
#         return session
#
#     # Make a request through the Tor connection
#     # IP visible through Tor
#     session = get_tor_session()
#     print(session.get("http://httpbin.org/ip").text)
#     # Above should print an IP different than your public IP
#
#     # Following prints your normal public IP
#     print(requests.get("http://httpbin.org/ip").text)


    proxy = getRandomProxy()
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9062)
#     socks.set_default_proxy(socks.SOCKS5, proxy["ip"], 80)
    socket.socket = socks.socksocket
    print (requests.get('http://httpbin.org/ip').text)


if __name__ == '__main__':
    torTest3()






