# Requirements

Use this script to install all dependencies : <https://github.com/hayj/Bash/blob/master/hjupdate.sh>

# Collections

 * **twinews**: A mongo database containing the following collections.
   * **users**: Corresponds to all users with all tweets. You will find the field `news` a list of url (primary key in the `news` collection) and `timestamps` all timestamps when the user shared the news.
   * **news**: Corresponds all news data. You will find `users` all users who shared the news. `timestamps` are all timestamps when users shared the news. `minTimestamp` is the timestamp when the news was shared for the first time.
   * **scores**: Corresponds to all results scores of rankings. Folders are the same as folders in `rankings`.
 * **twinews-splits**: A GridFS mongo database. Corresponds to dataset splits for the evaluation of models.
 * **twinews-rankings**: A GridFS mongo database. Corresponds to models outputs. Keys are lda-RHG9H-v1 first 5 letters of the hash of the config of the model instance following by the evaluation split version. The data inside must follow the same guideline.


# Splits (evaluation data)

Splits corresponds to all dataset splits with candidates to rank and stats.
All splits are in the mongo database twinews-splits.

Version of splits are the following:

 1. The train / test split over the whole dataset with minimum 8 train news per users and 2 test news per user. Candidates are 1000 for each user. 
 2. The train / validation split over the train set of the split version 1 with minimum 8 train news per users and 2 test news per user. Candidates are 1000 for each user.

# Evaluation data shape

```python
{
  'meta': # Informations about the current evaluation data
  {
    'created': '2020.03.24-14.28.06',
    'endDate': '2018-01-15',
    'id': 2, # 2 is for validation, 1 is for test
    'ranksLength': 1000,
    'splitDate': '2017-12-25',
    'startDate': '2017-10-01',
    'testMaxNewsPerUser': 97,
    'testMeanNewsPerUser': 7.22,
    'testMinNewsPerUser': 2,
    'testNewsCount': 71781,
    'totalNewsAvailable': 570210,
    'trainMaxNewsPerUser': 379,
    'trainMeanNewsPerUser': 26.48,
    'trainMinNewsPerUser': 8,
    'trainNewsCount': 237150,
    'usersCount': 15905
  },
  'extraNews': { url1, url2, ... }, # These are extra news you can use (not in train / test)
  'candidates': # You need to take that and rand all candidates
  {
    <user id>: # Here it's a list because we can have multiple lists of candidates per user
    [
      {
        <url 1>,
        ...,
        <url 1000>
      }
    ],
    ...,
    '100022528': 
    [
      {
        http://ow.ly/GNQM30hSXPU,
        ...,
        https://usat.ly/2Db0QTH
      }
    ]
  },
  'testNews': # These are news after splitDate
  {
    <url 1>,
    ...,
    <url 71781>
  },
  'trainNews': # These are news before splitDate
  {
    <url 1>,
    ...,
    <url 237150>
  },
  'trainUsers': # Users in train (you can specify maxUsers for subsampling the dataset)
  {
    '100022528': 
    {
      <url 1>: <timestamp in seconds the user shared the news>,
      ...,
      <url 42>: 1515609959,
    },
    ...,
    <user id>: 
    {
      <url 1>: 1515670765,
      ...,
      <url 34> : 1514572410
    }
  },
  'testUsers': 
  {
    '100022528': 
    {
      <url 1>: <timestamp in seconds the user shared the news>,
      ...,
      <url 11>: 1515609959,
    },
    ...,
    <user id>: 
    {
      <url 1>: 1515670765,
      ...,
      <url 6> : 1514572410
    }
  }
}
```

# Pour dump la base de données Twinews

Sur le docker jupyter, ouvrir un terminal, installer mongodb <https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/>

Puis dans le docker faire :

	hjpassword=<voir dataencryptor>
	/NoSave/twinews-dumps/dump.sh $hjpassword

Le script contient :

```
rm -rf /NoSave/twinews-dumps/twinews-rankings
mongodump --gzip --username hayj --password $1 --host titanv.lri.fr --authenticationDatabase admin --db twinews-rankings --out /NoSave/twinews-dumps
rm -rf /NoSave/twinews-dumps/twinews-splits
mongodump --gzip --username hayj --password $1 --host titanv.lri.fr --authenticationDatabase admin --db twinews-splits --out /NoSave/twinews-dumps
rm -rf /NoSave/twinews-dumps/twinews
mongodump --gzip --username hayj --password $1 --host titanv.lri.fr --authenticationDatabase admin --db twinews --out /NoSave/twinews-dumps
```

Puis depuis n'importe quel tipi :

	nn -o ~/tmp/nohup-twinews-dumps-sync.out rsync -avhP -e "ssh -p 2222" --delete-after ~/NoSave/twinews-dumps hayj@212.129.44.40:~ ; sleep 1 ; tail -f ~/tmp/nohup-twinews-dumps-sync.out


# TODO

 * https://stackoverflow.com/questions/6861184/is-there-any-option-to-limit-mongodb-memory-usage


 Problème avec la distance kl_divergence :

	return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
	Traceback (most recent call last):
	File "/users/modhel/hayj/notebooks/twinews/hjmodels/topicmodels.ipynb.py", line 530, in <module>
	File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 148, in usersRankingsByHistoryDistance
	kwargs,
	File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 89, in userRankingsByHistoryDistance
	distances = getDistances(xvectors, yvectors, metric=distanceMetric, logger=logger)
	File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 31, in getDistances
	distances = pairwise_distances(xvectors, yvectors, metric=metric)
	File "/users/modhel/hayj/.local/share/virtualenvs/st-venv/lib/python3.6/site-packages/sklearn/metrics/pairwise.py", line 1752, in pairwise_distances
	return _parallel_pairwise(X, Y, func, n_jobs, kwds)
	File "/users/modhel/hayj/.local/share/virtualenvs/st-venv/lib/python3.6/site-packages/sklearn/metrics/pairwise.py", line 1348, in _parallel_pairwise
	return func(X, Y, kwds)
	File "/users/modhel/hayj/.local/share/virtualenvs/st-venv/lib/python3.6/site-packages/sklearn/metrics/pairwise.py", line 1392, in _pairwise_callable
	out[i, j] = metric(X[i], Y[j], kwds)
	File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 19, in kl_divergence
	return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
	File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 19, in <genexpr>
	return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
	ValueError: math domain error