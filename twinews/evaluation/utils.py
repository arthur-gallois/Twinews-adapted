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
]

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


def printReport\
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
	sortBy=None,
	colorize=True,
):
	global METRICS_ORDER
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
			df = colorise_df_columns(df, grey={'id'}, green=greenMetrics, blue=sortBy)
		display(df)
		return df