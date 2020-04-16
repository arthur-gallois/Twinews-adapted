# Requirements

Use this script to install all dependencies : <https://github.com/hayj/Bash/blob/master/hjupdate.sh>

# Collections

 * **twinews**: A mongo database containing the following collections.
   * **users**: Corresponds to all users with all tweets. You will find the field `news` a list of url (primary key in the `news` collection) and `timestamps` all timestamps when the user shared the news.
   * **news**: Corresponds all news data. You will find `users` all users who shared the news. `timestamps` are all timestamps when users shared the news. `minTimestamp` is the timestamp when the news was shared for the first time.
   * **scores**: Corresponds to all results scores of rankings. Folders are the same as folders in `rankings`.
 * **twinews-splits**: A GridFS mongo database. Corresponds to dataset splits for the evaluation of models.
 * **twinews-rankings**: A GridFS mongo database. Corresponds to models outputs. Keys are lda-RHG9H-v1 first 5 letters of the hash of the config of the model instance following by the evaluation split version. The data inside must follow the same guideline.


# How to get the text of a news?

Use `twinews.utils.getNewsText(url)` to get the text (which correspond to the field `detokText`) and `twinews.utils.getNewsSentences(url)` to get the text (which correspond to the field `detokSentences`) that is already tokenized by word and sentences.

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
	'extraNews': { 'url1', 'url2', '...' }, # These are extra news you can use (not in train / test)
	'candidates': # You need to take that and rank all candidates
	{
		'<user id>':
		[ # Here it's a list because we can have multiple lists of candidates per user
			{
				'<url 1>',
				# ...,
				'<url 1000>'
			}
		],
		# ...,
		'100022528': 
		[
			{
				'http://ow.ly/GNQM30hSXPU',
				# ...,
				'https://usat.ly/2Db0QTH'
			}
		]
	},
	'testNews': # These are news after splitDate
	{
		'<url 1>',
		# ...,
		'<url 71781>'
	},
	'trainNews': # These are news before splitDate
	{
		'<url 1>',
		# ...,
		'<url 237150>'
	},
	'trainUsers': # Users in train (you can specify maxUsers for subsampling the dataset)
	{
		'100022528': 
		{
			'<url 1>': '<timestamp in seconds the user shared the news>',
			# ...,
			'<url 42>': 1515609959,
		},
		# ...,
		'<user id>': 
		{
			'<url 1>': 1515670765,
			# ...,
			'<url 34>' : 1514572410
		}
	},
	'testUsers': 
	{
		'100022528': 
		{
			'<url 1>': '<timestamp in seconds the user shared the news>',
			# ...,
			'<url 11>': 1515609959,
		},
		# ...,
		'<user id>': 
		{
			'<url 1>': 1515670765,
			# ...,
			'<url 6>' : 1514572410
		}
	}
}
```

# How the continuous evaluation work?

A **model** is a particular algorithm which is intended to rank items. A **model instance** is a model with particular parameters definined in `config`. For example `nmf-9cd4f` is the `nmf` model with a config that gave the hash `9cd4f`. A **model instance**'s rankings is a unique *entry* (or a unique *row*) of the `twinews-rankings` database.

The `twinews-rankings` database is the data each **model instance** produced (rankings). The `twinews.scores` collection is connected to the `twinews-rankings` database and will map scores of all **model instances** for all metrics (`evaluation.ipynb` is looping infinitely and add rows in `twinews.scores` when a new model is added in the `twinews-rankings` database).

When you implement a model. You need to init a config dict:

	config = \
	{
	    'splitVersion': 2, # Mandatory
	    'maxUsers': None, # Mandatory
	    'historyRef': 0.3, # A hyperparameter you can optimize
	}

Then you get candidates in evaluation data (see the shape of eval data in the README):

	candidates = getEvalData(config['splitVersion'], maxUsers=config['maxUsers'])['candidates']

You need to produce all rankings in a variable `rankings` that is the same as `candidates` but with lists instead of sets of urls.

Finally you add `rankings` in the `twinews-rankings` database:

	addRanking('nmf', rankings, config)


# How to generate rankings?

In eval data you get candidates for each user (so `evalData['candidates']`:

```python
{
	'<user id>':
	[ # Here it's a list because we can have multiple lists of candidates per user
		{
			'<url 1>',
			# ...,
			'<url 1000>'
		}
	],
	# ...,
	'100022528': 
	[
		{
			'http://ow.ly/GNQM30hSXPU',
			# ...,
			'https://usat.ly/2Db0QTH'
		}
	]
}
```

Your rankings must be the same shape but lists (to order items by relevance):

```python
{
	'<user id>':
	[
		[
			'<url 102>',
			# ...,
			'<url 506>'
		]
	],
	# ...,
	'100022528': 
	[
		[
			'http://ow.ly/JHDG',
			# ...,
			'https://bit.ly/465JHGV'
		]
	]
}
```

**BUT** you can also give scores with urls (distance or similarity, it doesn't matter, and you don't need to normalize it, it doesn't matter). This is usefull when we will combinate multiple models outputs.

```python
{
	'<user id>':
	[
		[
			('<url 102>', <score for url 102>), # A tuple url and score
			# ...,
			('<url 506>', <score for url 506>),
		]
	],
	# ...,
	'100022528': 
	[
		[
			('http://ow.ly/JHDG', 100548),
			# ...,
			('https://bit.ly/465JHGV', 845),
		]
	]
}
```


# Faire un dump de la base de donnée

Faire `mongopass` sur hjlat puis cette suite de commandes :

```bash
password=<password>
scriptname="twinews-dump-and-sync" ; scriptlog=~/tmp/nohup-$scriptname.out ; scriptpath=~/tmp/$scriptname.sh
nn -o $scriptlog $scriptpath $password
tail -f $scriptlog
```

Dans `vim ~/tmp/twinews-dump-and-sync.sh` sur titanv :

```bash
#!/bin/bash
source ~/.bash_profile
source ~/.hjbashrc
shopt -s expand_aliases
source ~/.bash_aliases
dockerName=hjmongo1 ; username=hayj ; password=$1
dockerRootDir=/dumps
realRootDir=/special/hayj/mongodb-dumps
for db in "twinews-rankings" "twinews-splits" "twinews" "serializabledict"
do
	echo "Dumping the $db database"
	rm -rf $dockerRootDir/$db
	# Remove the `-it` option because it say "the input device is not a TTY" under nohup
	docker exec $dockerName mongodump --gzip --host 127.0.0.1 --db $db --out $dockerRootDir --username $username --password $password --authenticationDatabase admin
done
rsync --delete-after -avhuP -e "ssh -p 2222" $realRootDir hayj@212.129.44.40:~/twinews-dumps
rm -rf $realRootDir/*
```

# TODO

 * https://stackoverflow.com/questions/6861184/is-there-any-option-to-limit-mongodb-memory-usage


 Problème avec la distance kl_divergence :

```
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
File "/users/modhel/hayj/.local/share/virtualenvs/st-venv/lib/python3.6/site-packages/sklearn/metrics/pairwise.py", line 1348, in parallel_pairwise
return func(X, Y, kwds)
File "/users/modhel/hayj/.local/share/virtualenvs/st-venv/lib/python3.6/site-packages/sklearn/metrics/pairwise.py", line 1392, in _pairwise_callable
out[i, j] = metric(X[i], Y[j], kwds)
File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 19, in kl_divergence
return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
File "/users/modhel/hayj/Workspace/Python/Datasets/Twinews/twinews/ranking.py", line 19, in <genexpr>
return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
ValueError: math domain error
```

Essayer de faire des colonnes verticales :

```python
# Tentative de header vertical:
# https://stackoverflow.com/questions/46715736/rotating-the-column-name-for-a-panda-dataframe
df.style.hide_index().set_table_styles(
    [dict(selector="th",props=[('max-width', '3px')]),
        dict(selector="th.col_heading",
                 props=[("writing-mode", "vertical-rl"),
                        # ("height", "1px"),
                        # ("position", "relative"),
                        # ("left", "10px"),
                        ("text-align", "left"),
                        ("padding-bottom", "0px"),
                        # ("margin-top", "200px"),
                        # ("margin", "0"),
                        # ("margin-top", "150px"),
                        # ("bottom", "0"),
                        ('transform', 'rotate(-50deg)'),
                        ("transform-origin", "top left"),
                        ])]
)
```





