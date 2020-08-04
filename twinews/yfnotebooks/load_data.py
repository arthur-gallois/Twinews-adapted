#-*-coding:utf-8-*-
import pandas as pd
import os
from twinews.yfnotebooks.data_utils import shuffle, pad_sequences
from twinews.yfnotebooks.convnet import args
import jieba
import re
from gensim.models import Word2Vec
import numpy as np
# from drcn import args
from scipy import sparse as sps
import io

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
    path = '/home/yuting/PycharmProjects/data/test_vocab2.txt'
    vocab = [line.decode().strip() for line in io.open(path, 'rb').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word

# ------------------------------------------------------------------------------------

# load vocab for dssm title
def load_char_vocab():
    path = '/home/yuting/PycharmProjects/data/title_vocab.txt'
    vocab = [line.strip() for line in open(path, encoding='utf-8').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word

# load word vocab
def load_word_vocab():
    path = os.path.join(os.path.dirname(__file__), '../output/word2vec/word_vocab.tsv')
    vocab = [line.strip() for line in open(path, encoding='utf-8').readlines()]
    word2idx = {word: index for index, word in enumerate(vocab)}
    idx2word = {index: word for index, word in enumerate(vocab)}
    return word2idx, idx2word


# static w2v
def w2v(word, model):
    try:
        return model.wv[word]
    except:
        return np.zeros(args.word_embedding_len)

# ------------------------------------------------------------------------------------------
# this part if for word hashing

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



# loading hash_index training data
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

# this part is for word hashing
# --------------------------------------------------------------------------------------------------------


# word->index
def char_index(p_sentences, h_sentences):
    word2idx, idx2word = load_char_vocab()

    p_list, h_list = [], []
    for p_sentence, h_sentence in zip(p_sentences, h_sentences):
        p = [word2idx[word.lower()] for word in p_sentence.split() if len(word.strip()) > 0 and word.lower() in word2idx.keys()]
        h = [word2idx[word.lower()] for word in h_sentence.split() if len(word.strip()) > 0 and word.lower() in word2idx.keys()]

        p_list.append(p)
        h_list.append(h)

    p_list = pad_sequences(p_list, maxlen=args.max_char_len)
    h_list = pad_sequences(h_list, maxlen=args.max_char_len)

    return p_list, h_list


# char->index
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


# load char data for dssm title
def load_char_data(file, data_size=None):
    # path = os.path.join(os.path.dirname(__file__), '../' + file)
    path = file
    df = pd.read_csv(path)
    p = df['sentence1'].values[0:data_size]
    h = df['sentence2'].values[0:data_size]
    label = df['label'].values[0:data_size]

    p, h, label = shuffle(p, h, label)

    # [1,2,3,4,5] [4,1,5,2,0]
    p_c_index, h_c_index = char_index(p, h)

    return p_c_index, h_c_index, label




# load char_index and static word vector
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


# load char_index and dynamic word vector
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


# load char_index, static word vector, dynamic word vector data
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

    # if there are same words
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

    # p_test = ['estimated __float_3__ united __float_1__ ago economy whole grew healthy pace workforce growth uniform handful industry doubled size shed half workforce nearly industry economy subject powerful unpredictable force free market globalization technological advancement fundamentally changed economic landscape worse industry seemed unassailable appear hanging thread wall st. reviewed annual employment data bureau labor statistic identify fastest dying industry industry list shed worker lower nearly fastest dying industry']
    # h_test = ' '
    # p, h = hashIndex(p_test, h_test)
    # p_array = p.toarray()
    # h_array = h.toarray()

    p, h, y = load_char_data('/home/yuting/PycharmProjects/data/dssm_title_train.csv', data_size=None)
    p_eval, h_eval, y_eval = load_char_data('/home/yuting/PycharmProjects/data/dssm_title_dev.csv', data_size=None)


