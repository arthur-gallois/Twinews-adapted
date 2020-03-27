from systemtools.hayj import *
from systemtools.location import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.printer import *
from twinews.utils import *
import pandas as pd
from IPython.display import display, HTML


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


def printReport\
(
    model=None,
    splitVersion=None,
    metaFilter={}, # A dict that map field to mandatory values
    metricsFilter=None, # A set of allowed metrics
    noSubsampling=True,
    logger=None,
    sortBy=None,
):
    twinewsRankings = getTwinewsRankings(verbose=False)
    twinewsScores = getTwinewsScores(verbose=False)
    data = []
    if noSubsampling and "maxUsers" not in metaFilter:
        metaFilter = mergeDicts(metaFilter, {"maxUsers": None})
    if model is not None and "model" not in metaFilter:
        metaFilter = mergeDicts(metaFilter, {"model": model})
    if splitVersion is not None and "splitVersion" not in metaFilter:
        metaFilter = mergeDicts(metaFilter, {"splitVersion": splitVersion})
    for key in twinewsRankings.keys():
        toKeep = True
        meta = twinewsRankings.getMeta(key)
        if 'historyRef' in meta:
            meta['historyRef'] = str(meta['historyRef'])
        for filtKey in metaFilter:
            if filtKey not in meta:
                raise Exception(filtKey + "is not in " + b(meta, 5))
            if metaFilter[filtKey] != meta[filtKey]:
                toKeep = False
                break
        if toKeep:
            data.append(meta)
    if len(data) == 0:
        log("No data found", logger)
    else:
        try:
            refKeys = data[0].keys()
            for e in data:
                assert e.keys() == refKeys
        except:
            raise Exception("Some data keys doesn't match:\n" + b(data, 5))
        if len(data) > 1:
            keysHavingSameValues = set(data[0].keys())
            baseValues = data[0]
            for current in data[1:]:
                for key in baseValues.keys():
                    if key in keysHavingSameValues and baseValues[key] != current[key]:
                        keysHavingSameValues.remove(key)
            sameValues = dict()
            for key in keysHavingSameValues:
                sameValues[key] = data[0][key]
            log("These values are common to all rows:\n", logger)
            for key, value in sameValues.items():
                log("\t- " + str(key) + ": " + str(value), logger)
            for i in range(len(data)):
                for key in keysHavingSameValues:
                    del data[i][key]
        # We add scores:
        metrics = set()
        for current in data:
            key = current['id']
            scores = twinewsScores.find({'id': key})
            for score in scores:
                if metricsFilter is None or score['metric'] in metricsFilter:
                    metrics.add(score['metric'])
                    current[score['metric']] = score['score']
        if len(metrics) > 0:
            metrics = sorted(list(metrics))
            if sortBy is None:
                sortBy = metrics[0]
        else:
            metrics = []
        df = pd.DataFrame(data)
        df = reorderDFColumns(df, start=['id'], end=metrics)
        if sortBy not in df.columns:
            sortBy = None
        if sortBy is not None:
            df.sort_values(sortBy, ascending=False, inplace=True)
        display(df)
        return df