#-*-coding:utf-8-*-
import pandas as pd
import os
from twinews.yfnotebooks.dssm.data_utils import shuffle, pad_sequences
from twinews.yfnotebooks.dssm import args
import jieba
import re
from gensim.models import Word2Vec
import numpy as np
# from drcn import args
from scipy import sparse as sps


def split(word):
    '''
        Split a word with lenth of n_gram_size
    :param self:
    :param word: word to be splited by n_gram len
    :return:
    '''
    n_gram = 3
    splited_ngrams = []
    word_len = len(word)
    split_point = 0
    while split_point < word_len - 1:  # don't consider the last marks
        splited_ngrams.append(word[split_point: split_point + n_gram])
        split_point += 1
    return splited_ngrams

# new loading 3-gram vocab
def load_ngram_char_vocab():
    path = os.path.join(os.path.dirname(__file__), '../input/test_vocab.txt')
    vocab = [line.strip() for line in open(path, 'rb').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word

# ------------------------------------------------------------------------------------

# 加载字典
def load_char_vocab():
    path = os.path.join(os.path.dirname(__file__), '../input/vocab.txt')
    vocab = [line.strip() for line in open(path, encoding='utf-8').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word


# 加载词典
def load_word_vocab():
    path = os.path.join(os.path.dirname(__file__), '../output/word2vec/word_vocab.tsv')
    vocab = [line.strip() for line in open(path, encoding='utf-8').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word


# 静态w2v
def w2v(word, model):
    try:
        return model.wv[word]
    except:
        return np.zeros(args.word_embedding_len)

# ------------------------------------------------------------------------------------------

# get_n_gram_count
def get_n_gram_count(sentences, n_gram_index_map):
    '''
        Get n_gram counting term matrix
    :param sentences: sentences to be handled to get n_gram term counting matrix
    :return: n_gram term counting sparse matrix, shapes(sentences number, n_gram term size)
    '''
    #assert isinstance(sentences, list)
    n_gram_size = len(n_gram_index_map.keys())
    marks = '#'
    n_gram_count = sps.lil_matrix((len(list(sentences)), n_gram_size))
    sen_cnt = 0
    for one_sen in sentences:
        one_sen = one_sen.strip().split()
        for one_word in one_sen:
            one_word = one_word.strip()
            one_word = marks + one_word.lower() + marks
            splited_n_gram = split(one_word)
            n_gram_index = []
            for splited in splited_n_gram:
                if splited in n_gram_index_map.keys():
                    n_gram_index.append(n_gram_index_map[splited])
            # n_gram_index = map(lambda x: self.n_gram_index_map[x], splited_n_gram)
            # n_gram_count[sen_cnt, n_gram_index] += 1
            for one_n_gram_index in n_gram_index:
                n_gram_count[sen_cnt, one_n_gram_index] += 1
        sen_cnt += 1

    #print('Get n_gram count matrix done, shape with: ', n_gram_count.shape)
    return n_gram_count


# hashed index
def hashIndex(p_sentences, h_sentences):
    '''
        Get n_gram counting term matrix
    :param sentences: sentences to be handled to get n_gram term counting matrix
    :return: n_gram term counting sparse matrix, shapes(sentences number, n_gram term size)
    '''

    word2idx, idx2word = load_ngram_char_vocab()

    p_hashed = get_n_gram_count(p_sentences,word2idx)
    h_hashed = get_n_gram_count(h_sentences, word2idx)
    # for p_sentence, h_sentence in zip(p_sentences, h_sentences):
    #     p = get_n_gram_count(p_sentence, n_gram_index_map)
    #     h = get_n_gram_count(h_sentence, n_gram_index_map)
    #
    #     p_list.append(p)
    #     h_list.append(h)
    return p_hashed, h_hashed
    # return np.array(p_list), np.array(h_list)



# 加载hash_index训练数据
def load_hashed_data(file, data_size=None):
    #path = os.path.join(os.path.dirname(__file__), '../' + file)

    df = pd.read_csv(file)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    # [1,2,3,4,5] [4,1,5,2,0]
    p_c_index, h_c_index = hashIndex(p, h)

    return p_c_index.toarray(), h_c_index.toarray(), label



# --------------------------------------------------------------------------------------------------------


# 字->index
def char_index(p_sentences, h_sentences):
    word2idx, idx2word = load_char_vocab()

    p_list, h_list = [], []
    for p_sentence, h_sentence in zip(p_sentences, h_sentences):
        p = [word2idx[word.lower()] for word in p_sentence if len(word.strip()) > 0 and word.lower() in word2idx.keys()]
        h = [word2idx[word.lower()] for word in h_sentence if len(word.strip()) > 0 and word.lower() in word2idx.keys()]

        p_list.append(p)
        h_list.append(h)

    p_list = pad_sequences(p_list, maxlen=args.max_char_len)
    h_list = pad_sequences(h_list, maxlen=args.max_char_len)

    return p_list, h_list


# 词->index
def word_index(p_sentences, h_sentences):
    word2idx, idx2word = load_word_vocab()

    p_list, h_list = [], []
    for p_sentence, h_sentence in zip(p_sentences, h_sentences):
        p = [word2idx[word.lower()] for word in p_sentence if len(word.strip()) > 0 and word.lower() in word2idx.keys()]
        h = [word2idx[word.lower()] for word in h_sentence if len(word.strip()) > 0 and word.lower() in word2idx.keys()]

        p_list.append(p)
        h_list.append(h)

    p_list = pad_sequences(p_list, maxlen=args.max_char_len)
    h_list = pad_sequences(h_list, maxlen=args.max_char_len)

    return p_list, h_list


def w2v_process(vec):
    if len(vec) > args.max_word_len:
        vec = vec[0:args.max_word_len]
    elif len(vec) < args.max_word_len:
        zero = np.zeros(args.word_embedding_len)
        length = args.max_word_len - len(vec)
        for i in range(length):
            vec = np.vstack((vec, zero))
    return vec


# 加载char_index训练数据
def load_char_data(file, data_size=None):
    path = os.path.join(os.path.dirname(__file__), '../' + file)
    df = pd.read_csv(path)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    # [1,2,3,4,5] [4,1,5,2,0]
    p_c_index, h_c_index = char_index(p, h)

    return p_c_index, h_c_index, label


# 加载char_index与静态词向量的训练数据
def load_char_word_static_data(file, data_size=None):
    model = Word2Vec.load('../output/word2vec/word2vec.model')

    path = os.path.join(os.path.dirname(__file__), file)
    df = pd.read_csv(path)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    p_c_index, h_c_index = char_index(p, h)

    p_seg = map(lambda x: list(jieba.cut(x)), p)
    h_seg = map(lambda x: list(jieba.cut(x)), h)

    p_w_vec = list(map(lambda x: w2v(x, model), p_seg))
    h_w_vec = list(map(lambda x: w2v(x, model), h_seg))

    p_w_vec = list(map(lambda x: w2v_process(x), p_w_vec))
    h_w_vec = list(map(lambda x: w2v_process(x), h_w_vec))

    return p_c_index, h_c_index, p_w_vec, h_w_vec, label


# 加载char_index与动态词向量的训练数据
def load_char_word_dynamic_data(path, data_size=None):
    df = pd.read_csv(path)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    p_char_index, h_char_index = char_index(p, h)

    p_seg = map(lambda x: list(jieba.cut(re.sub("[！，。？、~@#￥%&*（）.,:：|/`()_;+；…\\\\\\-\\s]", "", x))), p)
    h_seg = map(lambda x: list(jieba.cut(re.sub("[！，。？、~@#￥%&*（）.,:：|/`()_;+；…\\\\\\-\\s]", "", x))), h)

    p_word_index, h_word_index = word_index(p_seg, h_seg)

    return p_char_index, h_char_index, p_word_index, h_word_index, label


# 加载char_index、静态词向量、动态词向量的训练数据
def load_all_data(path, data_size=None):
    model = Word2Vec.load('../output/word2vec/word2vec.model')
    df = pd.read_csv(path)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    p_c_index, h_c_index = char_index(p, h)

    p_seg = list(map(lambda x: list(jieba.cut(re.sub("[！，。？、~@#￥%&*（）.,:：|/`()_;+；…\\\\\\-\\s]", "", x))), p))
    h_seg = list(map(lambda x: list(jieba.cut(re.sub("[！，。？、~@#￥%&*（）.,:：|/`()_;+；…\\\\\\-\\s]", "", x))), h))

    p_w_index, h_w_index = word_index(p_seg, h_seg)

    p_seg = map(lambda x: list(jieba.cut(x)), p)
    h_seg = map(lambda x: list(jieba.cut(x)), h)

    p_w_vec = list(map(lambda x: w2v(x, model), p_seg))
    h_w_vec = list(map(lambda x: w2v(x, model), h_seg))

    p_w_vec = list(map(lambda x: w2v_process(x), p_w_vec))
    h_w_vec = list(map(lambda x: w2v_process(x), h_w_vec))

    # 判断是否有相同的词
    same_word = []
    for p_i, h_i in zip(p_w_index, h_w_index):
        dic = {}
        for i in p_i:
            if i == 0:
                break
            dic[i] = dic.get(i, 0) + 1
        for index, i in enumerate(h_i):
            if i == 0:
                same_word.append(0)
                break
            dic[i] = dic.get(i, 0) - 1
            if dic[i] == 0:
                same_word.append(1)
                break
            if index == len(h_i) - 1:
                same_word.append(0)

    return p_c_index, h_c_index, p_w_index, h_w_index, p_w_vec, h_w_vec, same_word, label


if __name__ == '__main__':
    # load_all_data('../input/dssm_test_train.csv', data_size=100)

    # n_gram_index_map = {'and': 0, 's#': 1, 'ey#': 2, '#te': 3, 'c#': 4, 'ord': 5, 'ic#': 6, 'atc': 7, 'nti': 8, 't#': 9, 'man': 10, 'od#': 11, 'wor': 12, 'sem': 13, 'ds#': 14, 'y#': 15, 'tch': 16, 'ema': 17, 'tic': 18, 'met': 19, 'tho': 20, 'hin': 21, 'ods': 22, 'ext': 23, 'ing': 24, 'ed#': 25, '#se': 26, 'mat': 27, 'g#': 28, 'xt#': 29, 'ase': 30, 'key': 31, '#ma': 32, 'hod': 33, '#wo': 34, '#me': 35, 'sed': 36, 'tex': 37, 'd#': 38, '#ke': 39, 'rds': 40, 'eth': 41, 'bas': 42, 'nd#': 43, '#an': 44, 'chi': 45, 'ng#': 46, '#ba': 47, 'ant': 48}
    # a = get_n_gram_count("sematic word", n_gram_index_map)
    # #print((a.toarray()).shape)
    # print(a)

    p_test, h_test, label_test = load_hashed_data('../input/dssm_test_dev.csv', data_size=None)
    print(p_test.shape)
    print(type(p_test))
    print(h_test.shape)
    print(type(h_test))

