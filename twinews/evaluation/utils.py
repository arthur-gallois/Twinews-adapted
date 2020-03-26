def rankingToRelevanceVector(ranking, gtUrls):
    assert isinstance(gtUrls, set)
    assert isinstance(ranking, list)
    rel = []
    for url in ranking:
        if url in gtUrls:
            rel.append(True)
        else:
            rel.append(False)
    return rel