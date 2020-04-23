from datastructuretools.hashmap import *
from systemtools.hayj import *
from twinews.utils import *

def toCache(cacheFields, *args):
    theJoin = " ".join(list(cacheFields.keys()))
    for arg in args:
        if not isinstance(arg, list):
            arg = [arg]
        for current in arg:
            if current in theJoin:
                return True
    return False

def getVector(url, field, cache, newsCollection):
    row = newsCollection.findOne({'url': url}, projection={field: True})
    theHash = objectToHash(row[field])
    return cache[theHash]

def dictSelect(theDict, keys):
    return dict((k, theDict[k]) for k in keys if k in theDict)

def getGenericCache(key, readOnly=False, logger=None, verbose=True):
    if readOnly:
        user = 'student'
    else:
        user = 'hayj'
    (user, password, host) = getMongoAuth(user=user)
    if not key.startswith("twinews-"):
        key = "twinews-" + key
    return SerializableDict\
    (
        key,
        user=user, host=host, password=password,
        useMongodb=True, logger=logger, verbose=verbose,
    )

genericFields = \
{
    'dbert-ft': 'detokText',
    'dbert-base': 'detokText',
    'infersent': 'detokSentences',
    'usent': 'detokText',
    'sent2vec': 'detokSentences',
    'doc2vec': 'sentences',
    'bert': 'detokSentences',
    'stylo': 'detokText',
    'nmf': 'sentences',
    'tfidf': 'sentences',
    'word2vec': 'sentences',
    'bow': 'detokSentences',
}