def getEvalDataPath_deprecated(version):
	fileName = "v" + str(version) + ".pickle.gzip"
	if isUser("hayj"):
		if lri():
			evalDataPath = nosaveDir() + "/twinews-splits/" + fileName
		else:
			twinewsSplitsDir = tmpDir("twinews-splits")
			bash("rsync -avhuP --delete-after hayj@titanv.lri.fr:~/NoSave/twinews-splits/* " + twinewsSplitsDir)
			evalDataPath = twinewsSplitsDir + "/" + fileName
	elif "yuting" in getUser():
		rootDir = homeDir() + "/PycharmProjects/data"
		bash("rsync -avhuP -e \"ssh -p 2222\" student@212.129.44.40:/data/twinews-splits " + rootDir)
		evalDataPath = rootDir + "/twinews-splits/" + fileName
	return evalDataPath

def getEvalData_deprecated(version, maxExtraNews=None, maxUsers=None, logger=None, verbose=True):
	"""
		This function return the evaluation data with the right version in the right folder.
		Use `maxUsers` to sub-sample the dataset for test purposes.

		Usage example:

			evalData = getEvalData(1, maxExtraNews=100 if TEST else None, maxUsers=100 if TEST else None, logger=logger)
			(trainUsers, testUsers, trainNews, testNews, candidates, extraNews) = \
			(evalData['trainUsers'], evalData['testUsers'], evalData['trainNews'],
			 evalData['testNews'], evalData['candidates'], evalData['extraNews'])
			bp(evalData.keys(), 5, logger)
			log(b(evalData['stats']), logger)
	"""
	# Creating tt:
	tt = TicToc(logger=logger)
	tt.tic(display=False)
	# Getting eval data:
	evalData = deserialize(getEvalDataPath(version))
	assert evalData is not None
	tt.tic("Eval data loaded")
	# Sub-sampling:
	if maxUsers is not None and maxUsers > 0:
		evalData = subsampleEvalData(evalData, maxUsers=maxUsers)
	# Checking data:
	checkEvalData(evalData)
	# Getting extraNews (WARNING, here it's very long on the computer of Yuting because the function request the database):
	extraNews = getExtraNews(evalData['trainNews'].union(evalData['testNews']), logger=logger, limit=maxExtraNews)
	evalData['extraNews'] = extraNews
	if len(extraNews) > 0:
		tt.tic("Extra news downloaded")
	# Printing the duration:
	tt.toc("Got Twinews evaluation data")
	return evalData

