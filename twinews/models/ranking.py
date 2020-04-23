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
import numpy as np
import scipy
from machinelearning.function import *


def getDistances(xvectors, yvectors, metric='cosine', logger=None, verbose=False, multipartsThreshold=None, nJobs=None): # multipartsThreshold=500000
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
    # If a matrix is large:
    if multipartsThreshold is not None and (((xvectors.shape[0] * xvectors.shape[1]) > multipartsThreshold) or ((yvectors.shape[0] * yvectors.shape[1]) > multipartsThreshold)):
        distances = []
        for i in range(xvectors.shape[0]):
            xelement = xvectors[i]
            if len(xelement.shape) == 1:
                xelement = np.array([xelement])
            distances.append(pairwise_distances(xelement, yvectors, metric=metric)[0])
        distances = np.array(distances)
    else:
        distances = pairwise_distances(xvectors, yvectors, metric=metric, n_jobs=nJobs)
    return distances

def vstack(arrays):
    if isinstance(arrays, list):
        if isinstance(arrays[0], scipy.sparse.csr.csr_matrix):
            arrays = scipy.sparse.vstack(arrays)
        elif isinstance(arrays[0], np.ndarray):
            arrays = np.array(arrays)
    elif isinstance(arrays, np.ndarray) or isinstance(arrays, scipy.sparse.csr.csr_matrix):
        return arrays
    return arrays

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
        if historyRef == 0:
        	historyRef = 1
    else:
        historyRef = historyRef
    # Then we store all history vectors and urls in lists:
    xvectors, xurls = [], []
    for url in trainUrls:
        xvectors.append(urlsVectors[url])
        xurls.append(url)
    xvectors = vstack(xvectors)
    # Then we iterate candidates to append all rankings:
    rankings = []
    for currentCandidates in candidates:
        # We store all history vectors and urls in lists:
        yvectors, yurls = [], []
        for url in currentCandidates:
            yvectors.append(urlsVectors[url])
            yurls.append(url)
        yvectors = vstack(yvectors)
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
        ranking = [(e[0], e[1]) for e in sortBy(urlDistances, index=1, desc=False)]
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

def normalizeRankingScores(x):
    """
        This function normalize ranking scores between 0.0 and 1.0 and make it ascending.
    """
    x = minMaxNormalize(x)
    if x[0] > x[-1]:
        x = [1 - e for e in x]
    return np.array(x)


def rescore(x, *args, **kwargs):
    x = np.array(x)
    x = normalizeRankingScores(x)
    x = normalizedLawX(x, *args, inverse=False, **kwargs)
    return list(x)

def mergeRankings\
(
    rankings,
    rankAsScore=None,
    weights=None,
    alphas=None,
    betas=None,
    padShorterRankings=True,
    padToken="__no_item__",
    logger=None,
    verbose=True,
    epsilon=0.0001,
    returnScores=True,
):
    """
        This function merge rankings of different recommender systems.

        Actually this funciton works when you give same items in all rankings (same item count, same items...).
        TODO How to take into account items that are not in a sub-set of ranking: give to it the worst score (1.0) ?

        :args:

            **rankings**: rankings is a list of tuples (label, score)
            if rankings is not a list of tuples (containing only labels), scores will be automatically generating according to the rank of each item. All scores will be normalized between 0.0 and 1.0. If you give scores for each item, scores must be ordered (descending or ascending). If scores are descending, it will be converted in ascending scores, so it will be normalized, meaning different rankings can have different scoring strategies (similarity, distance...).
            **rankAsScore**: Same size as `rankings`. For each ranking, indicates if scores are ranks of items. If False, given scores will be taken into account.
            **weights**: Same size as `rankings`. For each ranking, indicates the weight of it.
            **alphas**: Same size as `rankings`. For each ranking, indicates the alpha parameter of the function `machinelearning.function.normalizedLawX`. If lower than 0.5, first items' scores will come close to 0.0 (the best rank). If higher to 0.5, last items' scores will come close to 1.0 (the worst rank).
            **betas**: Same size as `rankings`. For each ranking, indicates the beta parameter of the function `machinelearning.function.normalizedLawX`.
            **padShorterRankings**: If True (default), all rankings are padded to be the same size as the longer ranking. For exemple in case you have a ranking of 10 items and an other of 1000 items, setting `padShorterRankings` as `True` will add 990 items to the first ranking list. It prevents to have very low scores for last items (du to the normalization) in this ranking (containing only 10 items).
    """
    # We check params and rankings shape:
    assert len(rankings) >= 2
    if rankAsScore is None:
        rankAsScore = [True] * len(rankings)
    if weights is None:
        weights = [1.0 / len(rankings)] * len(rankings)
    if alphas is None:
        alphas = [0.5] * len(rankings)
    if betas is None:
        betas = [NormalizedLawBeta.LOG] * len(rankings)
    assert len(rankings) == len(alphas)
    assert len(rankings) == len(betas)
    assert len(rankings) == len(rankAsScore)
    assert len(rankings) == len(weights)
    assert sum(weights) < 1.0 + epsilon and sum(weights) > 1.0 - epsilon
    # We convert scores per rank according to `rankAsScore`:
    for i in range(len(rankings)):
        ranking = rankings[i]
        assert len(ranking) > 0
        currentRankAsScore = rankAsScore[i]
        if currentRankAsScore:
            if isinstance(ranking[0], tuple):
                labels = [e[0] for e in ranking]
            else:
                labels = ranking
            scores = list(range(len(labels)))
            ranking = [(labels[u], scores[u]) for u in range(len(labels))]
        elif not isinstance(ranking[0], tuple):
                raise Exception("You need to provide the ranking scores when using `rankAsScore` as False")
        rankings[i] = ranking
    # We find longer ranking:
    maxRankingsLength = max([len(e) for e in rankings])
    # We normalize scores:
    for i in range(len(rankings)):
        ranking = rankings[i]
        if len(ranking) == 1:
            ranking = [(ranking[0][0], 0.0)]
        else:
            labels = [e[0] for e in ranking]
            scores = [e[1] for e in ranking]
            # We pad rankings:
            if padShorterRankings and len(labels) < maxRankingsLength:
                amountToAdd = maxRankingsLength - len(labels)
                meanDistance = (max(scores) - min(scores)) / len(scores)
                currentScore = max(scores) + meanDistance
                for u in range(amountToAdd):
                    labels.append(padToken)
                    scores.append(currentScore)
                    currentScore += meanDistance
            # We normalize scores:
            scores = rescore(scores, alpha=alphas[i], beta=betas[i])
            ranking = [(labels[u], scores[u]) for u in range(len(labels))]
        rankings[i] = ranking
    # We aggregate scores per label:
    labelScores = dict()
    for i in range(len(rankings)):
        ranking = rankings[i]
        weight = weights[i]
        for label, score in ranking:
            if label != padToken:
                if label not in labelScores:
                    labelScores[label] = []
                labelScores[label].append(score * weight)
    # We mean all scores:
    labelScores = [(label, np.sum(scores)) for label, scores in labelScores.items()]
    # We generate final ranking:
    labelScores = sortBy(labelScores, index=1, desc=False)
    # Finally we return the ranking:
    if returnScores:
        return labelScores
    else:
        ranking = [e[0] for e in labelScores]
        return ranking




def rankingVariance(x): # Autre nom ? variance des écarts ?
    """
        Mesure à quel point l'histogramme d'une liste de scores est plat.
        0.0 signifie que l'histogramme est très plat (des écatrs de scores constants entre les elements ocnsécutifs), par exemple [0., 0.33, 0.66, 1.]
        1.0 signifie que l'histogramme est déséquilibré, par exemple [0., 0., 0., 1.]
        
        La valeur retournée est normalisé entre la pire variance et la variance idéale
    """
    # Min max normalization and making it ascending:
    x = normalizeRankingScores(x)
    # Getting every differences:
    x = [abs(x[i] - x[i+1]) for i in range(len(x) - 1)]
    # Getting worst and ideal variance:
    worst = np.var([0.0] * (len(x) - 1) + [1.0])
    ideal = np.var([0.0] * len(x))
    # Getting the actual variance:
    variance = np.var(x)
    # Returning the normalized variance:
    return (variance - ideal) / (worst - ideal)

def ranking_variance_test():
    v1 = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    v2 = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 1.0]
    v3 = [0.0, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.0]
    v4 = [0.0, 0.01, 0.02, 0.5, 0.51, 0.52, 0.8, 0.81, 0.82, 0.83, 1.0]
    v5 = [0.0, 0.1, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0]
    v6 = [0.0, 0.1, 0.15, 0.35, 0.4, 0.45, 0.7, 0.75, 0.9, 0.95, 1.0]
    print(ranking_variance(v1))
    print(ranking_variance(v2))
    print(ranking_variance(v3))
    print(ranking_variance(v4))
    print(ranking_variance(v5))
    print(ranking_variance(v6))


def model_comb_demo():
    """
        Cette fonction montre que le modèle r2 est avantagé
        pour rankAsScore=[False, False]
        car a des valeurs qui sont plus lisses (à quel point l'histogramme de la liste de scores est plat)
    """
    i1 = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    i2 = ['e', 'b', 'g', 'a', 'd', 'f', 'c']
    s1 = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 1.0]
    step = 1.0 / 6.0
    s2 = [0.0, step, 2 * step, 3 * step, 4 * step, 5 * step, 1.0]
    s2 = [truncateFloat(e, 2) for e in s2]
    r1 = [(i1[i], s1[i]) for i in range(len(i1))]
    r2 = [(i2[i], s2[i]) for i in range(len(i2))]
    print(r1)
    print(r2)
    print(mergeRankings([r1, r2], rankAsScore=[True, True]))
    print(mergeRankings([r1, r2], rankAsScore=[False, False]))


if __name__ == '__main__':
    # a = list(range(1))
    # print(a)
    # print(normalizeRankingScores(a))
    ranking_variance_test()
    # model_comb_demo()





