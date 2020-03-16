from systemtools.basics import *
from systemtools.printer import *
from systemtools.file import *
from systemtools.location import *
from systemtools.system import *
from datatools.dataencryptor import *
from datastructuretools.hashmap import *

def getTipiStudentMongoAuth(*args, **kwargs):
    password = getDataEncryptorSingleton()["mongoauth"]['titanv']
    host = '127.0.0.1'
    return ('student', password['student'], host)

(user, password, host) = getTipiStudentMongoAuth()