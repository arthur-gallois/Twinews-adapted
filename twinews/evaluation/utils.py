from systemtools.hayj import *
from systemtools.location import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.printer import *
from dataviztools.pandasutils import *
from twinews.utils import *
import pandas as pd
from IPython.display import display, HTML


METRICS_ORDER = \
[
	# Ranking accuracy:
	'ndcg', 'ndcg@10', 'ndcg@100', 'map', 'mrr', 'p@10', 'p@100',
	# Diversity:
	'div@100', 'topic-div@100', 'jacc-div@100', 'swjacc-div@100', 'style-div@100',
	# Novelty:
	'nov@100', 'topic-nov@100', 'jacc-nov@100', 'swjacc-nov@100', 'style-nov@100',
	# Strict novelty:
	'snov@100', 'topic-snov@100', 'jacc-snov@100', 'swjacc-snov@100', 'style-snov@100',
	# Serendipity:
	'tfidf-ser@100', 'wtfidf-ser@100', 'bm25-ser@100', 'jacc-ser@100', 'style-ser@100',
	'avg-ser@100',
]

# See evaluation/metrics-normalization
"""
	metric			minId			min			nmin	maxId		max		nmax
0	snov@100		tfidf-4b89a		0.87		0.8		worst-f3f99	0.94	1
1	swjacc-snov@100	bm25-c84fd		0.91		0.9		bm25-c4813	0.95	1
2	style-snov@100	dbert-ft-fdc3b	0.25		0.2		worst-f3f99	0.46	0.6
3	jacc-snov@100	combin-75494	0.83		0.8		worst-f3f99	0.85	1
4	topic-snov@100	nmf-17852		0.38		0.3		worst-f3f99	0.68	0.8

"""
METRICS_MIN_MAX_NORMALIZATION = \
{
	'topic-div@100': {'min': 0.7, 'max': 1.0},
	'style-div@100': {'min': 0.4, 'max': 0.8},
	'div@100': {'min': 0.9, 'max': 1.0},
	
	'topic-nov@100': {'min': 0.7, 'max': 1.0},
	'style-nov@100': {'min': 0.4, 'max': 0.8},
	'nov@100': {'min': 0.9, 'max': 1.0},
	
	'topic-snov@100': {'min': 0.3, 'max': 0.8},
	'style-snov@100': {'min': 0.2, 'max': 0.6},
	'snov@100': {'min': 0.8, 'max': 1.0},
}


def rankingToRelevanceVector(ranking, gtUrls):
	assert isinstance(gtUrls, set)
	assert isinstance(ranking, list)
	rel = []
	for url in ranking:
		if url in gtUrls:
			rel.append(True)
		else:
			rel.append(False)
	return rel

def checkRankings(rankings, candidates, maxUsers=None):
	"""We check if rankings are coherent with candidates (for the right split version)"""
	gotACheck = False
	rankingsKeys = set(rankings.keys())
	candidatesKeys = set(candidates.keys())
	if maxUsers is None:
		assert len(rankingsKeys) == len(candidatesKeys)
	assert len(rankingsKeys.union(candidatesKeys)) == len(candidatesKeys)
	for userId in rankings:
		assert len(rankings[userId]) == len(candidates[userId])
		for u, ranking in enumerate(rankings[userId]):
			assert len(ranking) > 0
			assert isinstance(ranking, list)
			if isinstance(ranking[0], tuple):
				ranking = [e[0] for e in ranking]
			rankingSet = set(ranking)
			currentCandidates = candidates[userId][u]
			assert len(rankingSet) == len(currentCandidates)
			assert isinstance(currentCandidates, set)
			assert len(rankingSet.union(currentCandidates)) == len(rankingSet)
			gotACheck = True
	assert gotACheck

def purgeSubsampledRankings():
	toRemove = set()
	rks = getTwinewsRankings(verbose=False)
	scores = getTwinewsScores(verbose=False)
	for current in t.keys():
		meta = t.getMeta(current)
		if meta['maxUsers'] is not None:
			toRemove.add(meta['id'])
	log(str(len(toRemove)) + " rankings to remove: " + b(toRemove))
	for currentId in toRemove:
		del rks[currentId]
		scores.delete({'id': currentId})

twinewsGetCache = None
def twinewsGet(*args, **kwargs):
	global twinewsGetCache
	if twinewsGetCache is None:
		twinewsGetCache = dict()
	kwargsCopy = copy.deepcopy(kwargs)
	if 'verbose' in kwargsCopy:
		del kwargsCopy['verbose']
	if 'logger' in kwargsCopy:
		del kwargsCopy['logger']
	theHash = objectToHash((args, kwargsCopy))
	if theHash in twinewsGetCache:
		return copy.deepcopy(twinewsGetCache[theHash])
	else:
		result = __twinewsGet(*args, **kwargs)
		twinewsGetCache[theHash] = copy.deepcopy(result)
		return result

def __twinewsGet\
(
	whiteModels=None,
	blackModels=None,
	splitVersion=1,
	# metaFilter={}, # A dict that map field to mandatory values
	onlyBestForField=None,
	noSubsampling=True,
	doNormalization=False,
	meanRandomScores=True,
	averageSerendipities=True,
	serendipitiesToAverage={'tfidf-ser@100', 'wtfidf-ser@100'},
	averagedSerendiptyLabel='avg-ser@100',
	logger=None,
	verbose=True,
	randomAvgVerbose=False,
):
	# Getting databases:
	twinewsScores = getTwinewsScores(verbose=False)
	twinewsRankings = getTwinewsRankings(verbose=False)
	dominancesSD = getDominancesSD(verbose=False)
	# Shape of params:
	if not (blackModels is None or isinstance(blackModels, list) or isinstance(blackModels, set)):
		blackModels = {blackModels}
	if not (whiteModels is None or isinstance(whiteModels, list) or isinstance(whiteModels, set)):
		whiteModels = {whiteModels}
	# Gettings rows:
	rows = []
	for key in twinewsRankings.keys():
		row = twinewsRankings.getMeta(key)
		if splitVersion is not None and row['splitVersion'] != splitVersion:
			continue
		if noSubsampling and row['maxUsers'] is not None:
			continue
		if blackModels is not None and row['model'] in blackModels:
			continue
		if whiteModels is not None and row['model'] not in whiteModels:
			continue
		rows.append(row)
	# Getting dominances:
	for row in rows:
		if row['id'] in dominancesSD:
			row['dominance'] = dominancesSD[row['id']]
	# Getting scores:
	allMetrics = set()
	for row in rows:
		for scoreRow in twinewsScores.find({'id': row['id']}):
			assert scoreRow['metric'] not in row
			allMetrics.add(scoreRow['metric'])
			row[scoreRow['metric']] = scoreRow['score']
	# We mean random models:
	if meanRandomScores:
		rdCount = 0
		for row in rows:
			if row['model'] == 'random':
				rdCount += 1
		if rdCount > 1:
			assert splitVersion is not None and noSubsampling
			randomScores = dict()
			for row in rows:
				if row['model'] == 'random':
					for metric in allMetrics:
						if metric in row:
							if metric not in randomScores:
								randomScores[metric] = []
							randomScores[metric].append(row[metric])
			randomMeanScores = dict()
			for metric, scores in randomScores.items():
				log("We averaged " + str(len(scores)) + " scores of random models for the " + metric + " metric", logger, verbose=verbose and randomAvgVerbose)
				score = float(np.mean(scores))
				randomMeanScores[metric] = score
			keysToRemove = {'seed', 'id'}.union(set(allMetrics))
			aloneRandomRow = {'id': 'random-xxxxx', 'model': 'random', 'maxUsers': None, 'splitVersion': splitVersion}
			aloneRandomRow = mergeDicts(randomMeanScores, aloneRandomRow)
			rows = [e for e in rows if e['model'] != 'random']
			rows.append(aloneRandomRow)
	# We average serendipities:
	if averageSerendipities:
		# First we check if all rows have all serendipities:
		try:
			for row in rows:
				for ser in serendipitiesToAverage:
					assert ser in row
			# Then we average all:
			for row in rows:
				row[averagedSerendiptyLabel] = float(np.mean([row[ser] for ser in serendipitiesToAverage]))
		except Exception as e:
			logError("No serendipities to average in a row.", logger=logger, verbose=verbose)
	# Keeping only bests:
	if onlyBestForField is not None:
		assert isinstance(onlyBestForField, str)
		bests = dict()
		for row in rows:
			assert onlyBestForField in row
			if row['model'] not in bests:
				bests[row['model']] = (row['id'], row[onlyBestForField])
			elif bests[row['model']][1] < row[onlyBestForField]:
				bests[row['model']] = (row['id'], row[onlyBestForField])
		whites = [v[0] for _, v in bests.items()]
		rows = [e for e in rows if e['id'] in whites]
	# We normalize metrics:
	if doNormalization:
		wereNormalized = set()
		for row in rows:
			for metric in METRICS_MIN_MAX_NORMALIZATION:
				mini = METRICS_MIN_MAX_NORMALIZATION[metric]['min']
				maxi = METRICS_MIN_MAX_NORMALIZATION[metric]['max']
				if metric in row:
					assert row[metric] > mini
					assert row[metric] < maxi
					row[metric] = float((row[metric] - mini) / (maxi - mini))
					wereNormalized.add(metric)
		if len(wereNormalized) > 0:
			log("Normalized metrics: " + str(wereNormalized), logger, verbose=verbose)
	return rows


def printReport\
(
	*args,
	onlyFields=None,
	whiteMetrics=None, # This are patterns
	blackMetrics=None, # This are patterns
	sortBy=None,
	colorize=True,
	logger=None,
	verbose=True,
	**kwargs,
):
	# We normalize parameters:
	global METRICS_ORDER
	if whiteMetrics is not None and isinstance(whiteMetrics, str):
		whiteMetrics = {whiteMetrics}
	if blackMetrics is not None and isinstance(blackMetrics, str):
		blackMetrics = {blackMetrics}
	# We get data:
	data = twinewsGet(*args, **kwargs)
	if data is None or len(data) == 0:
		return None
	# We add metrics in onlyFields:
	if isinstance(onlyFields, set):
		onlyFields = list(onlyFields)
	if onlyFields is not None:
		for m in METRICS_ORDER:
			onlyFields.append(m)
	# For each row:
	for i in range(len(data)):
		# We remove specific fields:
		if onlyFields is not None and len(onlyFields) > 0:
			data[i] = dictSelect(data[i], onlyFields)
		# We remove some metrics:
		for m in METRICS_ORDER:
			if m in data[i]:
				foundWhite = False
				foundBlack = False
				if whiteMetrics is not None:
					for wm in whiteMetrics:
						if re.search(wm, m) is not None:
							foundWhite = True
				if blackMetrics is not None:
					for wm in blackMetrics:
						if re.search(wm, m) is not None:
							foundBlack = True
				if not ((whiteMetrics is None or foundWhite) and (blackMetrics is None or not foundBlack)):
					del data[i][m]
				else:
					data[i][m] = truncateFloat(data[i][m], 5)
	# We fill empty field with 'N/A':
	firstKeys = set(data[0].keys())
	refKeys = set(data[0].keys())
	for e in data:
		if e.keys() != firstKeys:
			subs = set(substract(set(e.keys()), firstKeys) + substract(firstKeys, set(e.keys())))
			logWarning("Found key difference: " + str(subs), logger)
		for key in e.keys():
			refKeys.add(key)
	for i in range(len(data)):
		toAdd = substract(refKeys, set(data[i].keys()))
		for k in toAdd:
			data[i][k] = 'N/A'
	# We take out common values:
	if len(data) > 1:
		keysHavingSameValues = set(data[0].keys())
		baseValues = data[0]
		for current in data[1:]:
			for key in baseValues.keys():
				if key in keysHavingSameValues and baseValues[key] != current[key]:
					keysHavingSameValues.remove(key)
		sameValues = dict()
		for key in keysHavingSameValues:
			sameValues[key] = data[0][key]
		if len(sameValues) > 0:
			log("These values are common to all rows (" + str(len(data)) + "):\n", logger)
			for key, value in sameValues.items():
				log("\t- " + str(key) + ": " + str(value), logger)
		for i in range(len(data)):
			for key in keysHavingSameValues:
				del data[i][key]
	# We truncate dominances:
	for current in data:
		if 'dominance' in current:
			current['dominance'] = truncateFloat(current['dominance'], 2)
	# We re-order metrics:
	metrics = set()
	for row in data:
		for key in row:
			if key in METRICS_ORDER:
				metrics.add(key)
	if metrics is not None and len(metrics) > 0:
		newMetrics = []
		for key in METRICS_ORDER:
			if key in metrics:
				newMetrics.append(key)
		metrics = newMetrics
	# The sortBy is the first metric:
	if len(metrics) > 0:
		if sortBy is None:
			sortBy = metrics[0]
	else:
		metrics = []
	# We set the sortBy metric at first:
	if sortBy is not None and sortBy in metrics:
		metrics.remove(sortBy)
		metrics = [sortBy] + metrics
	# We convert data to a dataframe:
	df = pd.DataFrame(data)
	# We order columns:
	df = reorderDFColumns(df, start=['id'], end=metrics)
	# We sort a column:
	if sortBy not in df.columns:
		sortBy = None
	if sortBy is not None:
		df.sort_values(sortBy, ascending=False, inplace=True)
	# We colorize columns:
	if colorize:
		greenMetrics = metrics
		if sortBy is not None and sortBy in metrics:
			greenMetrics.remove(sortBy)
		df = colorise_df_columns(df, grey={'id'}, green=greenMetrics, blue=sortBy, red='dominance')
	# Finally we display the table and return it:
	display(df)
	return df

def printReport_deprecated\
(
	model=None,
	excludedModels=None,
	onlyFields=None,
	splitVersion=None,
	metaFilter={}, # A dict that map field to mandatory values
	allowedMetrics=None, # A set of allowed metrics
	discardedMetrics=None, # A set of allowed metrics
	blackMetricPatterns=None,
	whiteMetricPatterns=None,
	noSubsampling=True,
	logger=None,
	verbose=True,
	sortBy=None,
	colorize=True,
	doNormalization=True,
):
	global METRICS_ORDER
	global METRICS_MIN_MAX_NORMALIZATION
	if blackMetricPatterns is not None and isinstance(blackMetricPatterns, str):
		blackMetricPatterns = {blackMetricPatterns}
	if whiteMetricPatterns is not None and isinstance(whiteMetricPatterns, str):
		whiteMetricPatterns = {whiteMetricPatterns}
	twinewsRankings = getTwinewsRankings(verbose=False)
	twinewsScores = getTwinewsScores(verbose=False)
	data = []
	if noSubsampling and "maxUsers" not in metaFilter:
		metaFilter = mergeDicts(metaFilter, {"maxUsers": None})
	if model is not None and "model" not in metaFilter:
		metaFilter = mergeDicts(metaFilter, {"model": model})
	if splitVersion is not None and "splitVersion" not in metaFilter:
		metaFilter = mergeDicts(metaFilter, {"splitVersion": splitVersion})
	for key in twinewsRankings.keys():
		toKeep = True
		meta = twinewsRankings.getMeta(key)
		if 'historyRef' in meta:
			meta['historyRef'] = str(meta['historyRef'])
		for filtKey in metaFilter:
			if filtKey not in meta:
				raise Exception(filtKey + "is not in " + b(meta, 5))
			if metaFilter[filtKey] != meta[filtKey]:
				toKeep = False
				break
		if excludedModels is not None and len(excludedModels) > 0:
			if meta['model'] in excludedModels:
				toKeep = False
		if onlyFields is not None and len(onlyFields) > 0:
			meta = dictSelect(meta, onlyFields)
		if toKeep:
			data.append(meta)
	if len(data) == 0:
		log("No data found", logger)
	else:
		firstKeys = set(data[0].keys())
		refKeys = set(data[0].keys())
		for e in data:
			if e.keys() != firstKeys:
				subs = set(substract(set(e.keys()), firstKeys) + substract(firstKeys, set(e.keys())))
				logWarning("Found key difference: " + str(subs), logger)
			for key in e.keys():
				refKeys.add(key)
		if len(data) > 1:
			for i in range(len(data)):
				toAdd = substract(refKeys, set(data[i].keys()))
				for k in toAdd:
					data[i][k] = 'N/A'
			keysHavingSameValues = set(data[0].keys())
			baseValues = data[0]
			for current in data[1:]:
				for key in baseValues.keys():
					if key in keysHavingSameValues and baseValues[key] != current[key]:
						keysHavingSameValues.remove(key)
			sameValues = dict()
			for key in keysHavingSameValues:
				sameValues[key] = data[0][key]
			if len(sameValues) > 0:
				log("These values are common to all rows (" + str(len(data)) + "):\n", logger)
				for key, value in sameValues.items():
					log("\t- " + str(key) + ": " + str(value), logger)
			for i in range(len(data)):
				for key in keysHavingSameValues:
					del data[i][key]
		# We add scores:
		metrics = set()
		for current in data:
			key = current['id']
			scores = twinewsScores.find({'id': key})
			for score in scores:
				if (allowedMetrics is None or score['metric'] in allowedMetrics) and (discardedMetrics is None or score['metric'] not in discardedMetrics):
					isBlack = False
					if blackMetricPatterns is not None:
						for key in blackMetricPatterns:
							if key in score['metric']:
								isBlack = True
					isNotWhite = False
					if whiteMetricPatterns is not None:
						isNotWhite = True
						for key in whiteMetricPatterns:
							if key in score['metric']:
								isNotWhite = False
					if not isBlack and not isNotWhite: # ok wtf
						metrics.add(score['metric'])
						current[score['metric']] = truncateFloat(score['score'], 5)
		# We normalize metrics:
		if doNormalization:
			wereNormalized = set()
			for row in data:
				for metric in METRICS_MIN_MAX_NORMALIZATION:
					mini = METRICS_MIN_MAX_NORMALIZATION[metric]['min']
					maxi = METRICS_MIN_MAX_NORMALIZATION[metric]['max']
					if metric in row:
						assert row[metric] > mini
						assert row[metric] < maxi
						row[metric] = float((row[metric] - mini) / (maxi - mini))
						wereNormalized.add(metric)
			if len(wereNormalized) > 0:
				log("Normalized metrics: " + str(wereNormalized), logger, verbose=verbose)
		# We add dominances:
		dominancesSD = getDominancesSD()
		for current in data:
			if current['id'] in dominancesSD:
				current['dominance'] = truncateFloat(dominancesSD[current['id']], 2)
		# We re-order metrics:
		if metrics is not None and len(metrics) > 0:
			newMetrics = []
			for key in METRICS_ORDER:
				if key in metrics:
					newMetrics.append(key)
			metrics = newMetrics
		# The sortBy is the first metric:
		if len(metrics) > 0:
			if sortBy is None:
				sortBy = metrics[0]
		else:
			metrics = []
		# We set the sortBy metric at first:
		if sortBy is not None and sortBy in metrics:
			metrics.remove(sortBy)
			metrics = [sortBy] + metrics
		df = pd.DataFrame(data)
		df = reorderDFColumns(df, start=['id'], end=metrics)
		if sortBy not in df.columns:
			sortBy = None
		if sortBy is not None:
			df.sort_values(sortBy, ascending=False, inplace=True)
		if colorize:
			greenMetrics = metrics
			if sortBy is not None and sortBy in metrics:
				greenMetrics.remove(sortBy)
			df = colorise_df_columns(df, grey={'id'}, green=greenMetrics, blue=sortBy, red='dominance')
		display(df)
		return df