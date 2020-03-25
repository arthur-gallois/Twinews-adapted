# TwitterNewsrec Dataset

## Description

This dataset is reserved for research and intended to be used for an offline news recommandation task. It contains users in the `users` folder and news in the `news` folder. All data are "[Newline Delimited Json](http://jsonlines.org/)" files.

You will find news urls of each users in the `news` field which correspond to a news entry in news data.

In order to use this dataset, you have to folow these rules:

 * In order to compare performance between reseacher, **this dataset must not be improved** (for example in adding informations about the user, or by re-scraping news, downloading additional news etc.). Instead you can suggest an enhancment to us and it will be added in the new realease of the dataset.
 * Follow the test procedure described below for the news recommendation task.
 * Cite us (see articles below) because the data collect and making available this dataset required 1 year of work.
 * Sign TODO
 * Mention the version of the dataset you used when you show your results.


## Indexor

To index these data in a mongo database, use scripts in the `indexor` folder. Or use this package as example to index all data in an other database. All package which are mandatory to execute the indexor can be installed using `hjupdate.sh` (in your virtual env if you have one) with the `a` option: `hjupdate.sh -a`.

	 1. Create a virtual env: `pew new -p /path/to/python3bin student-venv`
	 2. Execute `./hjupdate -a` in your virtual env: `pew in student-venv ./hjupdate.sh -a`
	 3. Install boilerpipe and newspaper3k by hand: `pew in student-venv pip install https://github.com/misja/python-boilerpipe/zipball/master#egg=python-boilerpipe ; pew in student-venv pip install newspaper3k`
	 4. Set parameters in `config.json` (the `dbName` for mongodb, `user`, `password`, the `dataDir`...)
	 5. Install and launch mongodb
	 6. Execute `indexor.py`: `pew in student-venv python indexor.py`

## Licence

TODO

## Test procedure

TODO

## Releases

 * Version 1: 500 users, generate at august 2018
 * Version 2: 10000 users, generate at september 2018
 * Version 3: 40000 users, generate at september 2018