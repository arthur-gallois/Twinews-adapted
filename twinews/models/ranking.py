from systemtools.hayj import *
from systemtools.location import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.printer import *
from twinews.utils import *
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances
from math import log2
from math import sqrt
from numpy import asarray


def getDistances(xvectors, yvectors, metric='cosine', logger=None, verbose=False):
	"""
		metric can be 'cosine', 'euclidean', 'kl', 'js'
	"""
	# Kullback–Leibler and Jensen-Shannon divergence: 
	def kl_divergence(p, q):
		return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
	def js_divergence(p, q):
		m = 0.5 * (p + q)
		return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)
	if metric == 'cosine':
		pass
	elif metric == 'euclidean':
		pass
	elif metric == 'kl':
		metric = kl_divergence
	elif metric == 'js':
		metric = js_divergence
	distances = pairwise_distances(xvectors, yvectors, metric=metric)
	return distances


def userRankingsByHistoryDistance\
(
	trainUrls,
	candidates,
	historyRef,
	urlsVectors,
	distanceMetric='cosine',
	logger=None,
	verbose=True,
):
	"""
		This function return all rankings corresponding to candidates

		The historyRef param is very important, it allow to choose, for a particular candidate, how many train history items will be used to calculate the similarity with the user history.
	    Float are ratio on train history
	    Integers are absolute number of train item in the history
	    For example:
	     * 1.0 will allow to mean similarities of a candidate with all train history items
	     * 1 will allow to use only the most similar train item for the similarity of the candidate with the history of the user
	     * 0.5 will allow to use the half of history for each candidates
	     * 3 to use 3 most similar items with the current candidate...

	    `historyRef` is a parameter that say "For a particular candidate, I want to score it by similarity with the history of the user. But how many items I take for that? A float of 0.3 mean we take 30% train items. An integer of 10 mean  we take max 10 train items."

	    My hypothesis is that "One particular candidate item has same topic as a sub-part of all history items of a user (because the user read several topics). So to match the candidate with a sub-set of the history will allow to better match the item with particular topics. If we choose 1.0 as the value for this parameter, it can down the similarity of the candidate because a large part of the user history is not related to the topic of the candidate"
		
		Args:
		
			trainUrls: url in the history (train)
			candidates: all lists of candidates to rank (e.g. [['url1', 'url2', 'url3'], ['url4', 'url5', 'url6']])
			historyRef: the float or int that indicates how many history items we must take into account
			urlsVectors: a dict that map urls with there vector representation
		
		Kwargs:
		
			distanceMetric: the distance metric (default is 'cosine')
	"""
	assert (isinstance(historyRef, int) and historyRef >= 1) or (isinstance(historyRef, float) and historyRef > 0.0 and historyRef <= 1.0)
	# First we convert the historyRef to a float
	if isinstance(historyRef, float):
		historyRef = int(historyRef * len(trainUrls))
	else:
		historyRef = historyRef
	# Then we store all history vectors and urls in lists:
	xvectors, xurls = [], []
	for url in trainUrls:
		xvectors.append(urlsVectors[url])
		xurls.append(url)
	xvectors = np.array(xvectors)
	# Then we iterate candidates to append all rankings:
	rankings = []
	for currentCandidates in candidates:
		# We store all history vectors and urls in lists:
		yvectors, yurls = [], []
		for url in currentCandidates:
			yvectors.append(urlsVectors[url])
			yurls.append(url)
		yvectors = np.array(yvectors)
		# Then we compute distances:
		distances = getDistances(xvectors, yvectors, metric=distanceMetric, logger=logger)
		# We map candidate urls to the mean distance:
		urlDistances = dict()
		for testIndex in range(len(yurls)):
			# We get the distance column:
			currentDists = distances[:, testIndex]
			assert currentDists.shape[0] == len(xurls)
			# We sort distances with the history:
			currentDists = sorted(list(currentDists), reverse=False)
			# We retain only a sub part of it according to `historyRef`:
			currentDists = currentDists[:historyRef]
			# We mean all value to get a unique distance for this candidate:
			currentDist = np.mean(currentDists)
			# And we add it in the dict:
			urlDistances[yurls[testIndex]] = currentDist
		# Finally we rank candidates by sorting distances:
		ranking = [e[0] for e in sortBy(urlDistances, index=1, desc=False)]
		# And we add to rankings:
		rankings.append(ranking)
	# Finally we return all rankings:
	return rankings


def usersRankingsByHistoryDistance\
(
	trainUsers,
	candidates,
	*args,
	printRatio=0.01,
	logger=None,
	verbose=True,
	**kwargs,
):
	"""
		This function return all rankings of all users given.

		Args:
			
			trainUsers: a dict mapping user ids with train urls (history)
			candidates: a dict mapping user ids with multiple lists of candidate urls
			*args: correponds to args for `userRankingsByHistoryDistance`

		Kwargs:

			**kwargs: correponds to kwargs for `userRankingsByHistoryDistance`
	"""
	# We init the dict to return:
	rankings = dict()
	# For each user:
	for userId in pb(list(trainUsers.keys()), logger=logger,
					 message="Generating ranking", printRatio=printRatio, verbose=verbose):
		# We get his rankings:
		currentRankings = userRankingsByHistoryDistance\
		(
			trainUsers[userId],
			candidates[userId],
			*args,
			logger=logger,
			verbose=verbose,
			**kwargs,
		)
		# We add it:
		rankings[userId] = currentRankings
	# And we return all rankings of all users:
	return rankings


