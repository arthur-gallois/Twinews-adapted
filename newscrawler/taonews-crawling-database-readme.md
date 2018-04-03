 
twitter_expanded_url est l'url utilisé par les utilisateur twitter
twitter_url est le lien raccourcie de cette url
normalized_url est la normalisation de twitter_expanded_url est est clef primaire ==> indexUnique <==
last_url est le dernière url de redirection lors du crawling
last_url_domain est le domain (avec public suffix) de last_url ==> indexNotUnique <==
twitter_expanded_url_domain est le domain (avec public suffix) de twitter_expanded_url
normalized_url_domain est le domain (avec public suffix) de normalized_url (probablement identique à twitter_expanded_url_domain) ==> indexNotUnique <==

