#-*-coding:utf-8-*-
import numpy as np


def one_hot(y, nb_classes):
    """ one_hot

    vector to one-hot

    Arguments:
        y: vector
        nb_classes: int, # of classification

    """
    y = np.asarray(y, dtype='int32')
    if not nb_classes:
        nb_classes = np.max(y) + 1
    Y = np.zeros((len(y), nb_classes))
    Y[np.arange(len(y)), y] = 1.
    return Y


def pad_sequences(sequences, maxlen=None, dtype='int32', padding='post',
                  truncating='post', value=0.):
    """ pad_sequences

    to set the length of sequence, if maxlen is specified, the length of sequence equals to maxlen,
    else equals to the maximum length of all sequences.
    either by padding, or truncating the sequence to keep the length uniformed.
    padding or truncating from the end(post), or from the beginning (pre)

    Arguments:
        sequences: data sequence
        maxlen: int maximum lendth
        dtype: datatype
        padding: 'pre' or 'post'
        truncating: truncatiing method, from 'pre' or 'post'
        value: float, the value to fill in

    Returns:
        x: numpy array sequence after padding (number_of_sequences, maxlen)

    """
    lengths = [len(s) for s in sequences]

    nb_samples = len(sequences)
    if maxlen is None:
        maxlen = np.max(lengths)

    x = (np.ones((nb_samples, maxlen)) * value).astype(dtype)
    for idx, s in enumerate(sequences):
        if len(s) == 0:
            continue  # empty list was found
        if truncating == 'pre':
            trunc = s[-maxlen:]
        elif truncating == 'post':
            trunc = s[:maxlen]
        else:
            raise ValueError("Truncating type '%s' not understood" % padding)

        if padding == 'post':
            x[idx, :len(trunc)] = trunc
        elif padding == 'pre':
            x[idx, -len(trunc):] = trunc
        else:
            raise ValueError("Padding type '%s' not understood" % padding)
    return x


def shuffle(*arrs):
    """ shuffle

    Shuffle data

    Arguments:
        *arrs: input array data

    Returns:
        shuffled data

    """
    arrs = list(arrs)
    for i, arr in enumerate(arrs):
        assert len(arrs[0]) == len(arrs[i])
        arrs[i] = np.array(arr)
    p = np.random.permutation(len(arrs[0]))
    return tuple(arr[p] for arr in arrs)
