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


# TODO

 * https://stackoverflow.com/questions/6861184/is-there-any-option-to-limit-mongodb-memory-usage