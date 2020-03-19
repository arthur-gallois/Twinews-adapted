# Collections

 * **users**: Corresponds to all users with all tweets. You will find the field `news` a list of url (primary key in the `news` collection) and `timestamps` all timestamps when the user shared the news.
 * **news**: Corresponds all news data. You will find `users` all users who shared the news. `timestamps` are all timestamps when users shared the news. `minTimestamp` is the timestamp when the news was shared for the first time.
 * **rankings**: Corresponds to models outputs. Keys are lda-RHG9H-v1 first 5 letters of the hash of the config of the model instance following by the evaluation split version. The data inside must follow the same guideline.
 * **scores**: Corresponds to all results scores of rankings. Folders are the same as folders in `rankings`.


# Splits (evaluation data)

Splits corresponds to all dataset splits with candidates to rank and stats.
There are in `/users/modhel/hayj/NoSave/twinews-splits`
