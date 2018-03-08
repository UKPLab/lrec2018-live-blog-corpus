import sys, os.path as path
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
import argparse
import numpy as np
import re


def get_vals(score):
    vals = score.split(' ')
    return [float(val) for val in vals]

def get_scores(text):
    pattern = re.search(' ([^\s:]+): ROUGE-1: ([^,]+), ROUGE-2: ([^,]+), ROUGE-L: ([^\n]+)', text)
    system = pattern.group(1)
    scores = []
    for index in range(2,5):
        scores.append(get_vals(pattern.group(index)))
    return system, scores

def aggregate(file_name):

    systems = ['UB1', 'UB2', 'ICSI', 'Luhn', 'LexRank', 'TextRank', 'LSA', 'KL']
    scores_rtype = ['ROUGE-1', 'ROUGE-2', 'ROUGE-L']
    scores_measures = ['F', 'P', 'R']

    baselines = []
    with open(file_name, 'r') as fp:
        lines = fp.read().splitlines()

    i = 0
    items = []
    while(i < len(lines)):
        #if re.search("Topic", lines[i]):
        #    print('Topic', lines[i])
        if re.search('###', lines[i]):
            if items:
                baselines.append(items) 
            items = []
        elif re.search('UB1:', lines[i]):
            for j in range(len(systems)):
                #print('I AM Here', lines[i])
                system, scores = get_scores(lines[i])
                #print(system, scores)    
                items.append(scores)
                i += 1     
        i += 1

    if items:
        baselines.append(items) 

    print '### Total topics: %d' % (len(baselines))
    for index in range(len(systems)):
        print '%s: ' % systems[index],
        for i, scores_type in enumerate(scores_rtype):
            vals = []
            for j, scores_measure in enumerate(scores_measures):
                #print index, i, j, baselines
                vals.append(np.array([x[index][i][j] for x in baselines]))
            print ' %s: %4f %4f %4f, ' % (scores_type, np.mean(vals[0]), np.mean(vals[1]), np.mean(vals[2])),
        print

def get_args():
    ''' This function parses and return arguments passed in'''

    parser = argparse.ArgumentParser(description='Baselines Results Aggregator')
    parser.add_argument('-l', '--summary_length', type= str, help='Scores file', required=False)
    parser.add_argument('-d', '--data_set', type= str, help='Year of the data set', required=True)

    args = parser.parse_args()
    summary_len = args.summary_length
    data_set = args.data_set
    return summary_len, data_set

if __name__ == '__main__':
    summary_len, data_set = get_args()
    ios_basedir = path.join(path.dirname(path.dirname(path.abspath(__file__))))

    data_path = '%s/data/logs/baselines_%s.log' % (ios_basedir, data_set)
    aggregate = aggregate(data_path)