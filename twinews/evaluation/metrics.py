

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





def ndcg():
	pass

def ndcg_at_10():
	pass

def ndcg_at_100():
	pass