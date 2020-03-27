

# https://scikit-learn.org/stable/modules/classes.html#sklearn-metrics-metrics
# https://github.com/scikit-learn/scikit-learn/blob/95d4f0841d57e8b5f6b2a570312e9d832e69debc/sklearn/metrics/_ranking.py

"""
	Dans scikit-learn, on utilise nDCG car nous n'avons pas de "ground truth order". C'est à dire que nos candidats ne sont pas strictement ordonné d'une manière. Chaque item est juste soit pertinent, soit non pertinent.
	Dans la doc scikit-leanr, ils disent :

		> Compared with the ranking loss, NDCG can take into account relevance scores, rather than a ground-truth ranking. So if the ground-truth consists only of an ordering, the ranking loss should be preferred; if the ground-truth consists of actual usefulness scores (e.g. 0 for irrelevant, 1 for relevant, 2 for very relevant), NDCG can be used. 
"""

# https://gist.github.com/bwhite/3726239
# https://gist.github.com/mblondel/7337391
# https://github.com/kmbnw/rank_metrics/blob/master/python/ndcg.py



# https://medium.com/swlh/rank-aware-recsys-evaluation-metrics-5191bba16832


from twinews.evaluation.rank_metrics import *



"""

# Usage

Metrics in this file take a vector a boolean (the relevance vector of your ranking). A True in the relevance vector indicates that the item is relevant. The more there are Trues near the index 0, the more the score will be high.

For example you ranked [url3, url2, url1, url4]. And you know that only url2 and url1 are relevant. So your relevance vector is [False, True, True, False]. This relevance vector is better (given, for instance, the ndcg metric) than the relevance vector of the ranking [url3, url4, url1, url2].


"""




############################# MRR #############################
# Measure: Where is the first relevant item?
def mrr(r):
	if r is None or len(r) == 0:
		raise Exception("r must be a list")
	if not isinstance(r[0], list):
		r = [r]
	for i in range(len(r)):
		r[i] = bool2binary(r[i])
		for current in r[i]:
			assert current == 1 or current == 0
	return mean_reciprocal_rank(r)

############################# PRECISION @ K #############################
def __precision(r, k):
	assert k <= len(r)
	assert r is not None and len(r) > 0
	r = bool2binary(r)
	for current in r:
		assert current == 1 or current == 0
	return precision_at_k(r, k)
def pAt10(r):
	return __precision(r, 10)
def pAt100(r):
	return __precision(r, 100)

############################# MAP #############################
def map(r):
	if r is None or len(r) == 0:
		raise Exception("r must be a list")
	if not isinstance(r[0], list):
		r = [r]
	for i in range(len(r)):
		r[i] = bool2binary(r[i])
		for current in r[i]:
			assert current == 1 or current == 0
	return mean_average_precision(r)

############################# NDCG #############################
def ndcg(r, k=None):
	if k is None:
		k = len(r)
	assert k <= len(r)
	assert r is not None and len(r) > 0
	r = bool2binary(r)
	for current in r:
		assert current == 1 or current == 0
	return ndcg_at_k(r, k)
def ndcgAt10(r):
	return ndcg(r, 10)
def ndcgAt100(r):
	return ndcg(r, 100)


############################# UTILS #############################
def bool2binary(r):
	return [int(e) for e in r]


if __name__ == '__main__':
	print(map([0, 1, 1, 0, 1, 1]))
	print(ndcg([0, 1, 1, 0, 1, 1]))
	print(pAt10([0, 1, 1, 0, 1, 1, True, False, True, False, True, False, False]))
	print(mrr([0, 1, 1, 0, 1, 1]))