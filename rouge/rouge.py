from __future__  import  print_function
import tempfile
from os import path, mkdir
import shutil

from utils.misc import write_to_file
from subprocess import check_output
import re

class Rouge(object):
    def __init__(self, rouge_dir):
        self.ROUGE_DIR = rouge_dir
        self.summary_tmp = "summary.txt"
        config_file = "config.xml"
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_file = path.join(self.temp_dir, config_file)
        self.peers_dir = path.join(self.temp_dir, "peers")
        self.models_dir = path.join(self.temp_dir, "models")
        
        mkdir(self.peers_dir)
        mkdir(self.models_dir)

    def create_config(self, peers, models):
        config_file = "<EVAL ID=\"1\">\n"
        config_file += "<PEER-ROOT>\n"
        config_file += self.peers_dir + "\n"
        config_file += "</PEER-ROOT>\n"
        config_file += "<MODEL-ROOT>\n"
        config_file += self.models_dir + "\n"
        config_file += "</MODEL-ROOT>\n"

        config_file += "<INPUT-FORMAT TYPE=\"SPL\">\n</INPUT-FORMAT>\n"
        config_file += "<PEERS>\n"
        for i, peer in enumerate(peers):
            config_file += "<P ID=\"" + str(i + 1) + "\">" + peer + "</P>\n"
        config_file += "</PEERS>\n"

        config_file += "<MODELS>\n"
        for i, _ in enumerate(models):
            config_file += "<M ID=\"" + str(i + 1) + "\">" +  "models%s.txt" % (str(i + 1)) + "</M>\n"
        config_file += "</MODELS>\n"
        config_file += "</EVAL>\n"

        return config_file

    def extract_results(self, output):
        pattern = re.compile(r"(\d+) (ROUGE-\S+) (Average_\w): (\d.\d+) \(95%-conf.int. (\d.\d+) - (\d.\d+)\)")
        results = {}
        output = output.decode("utf-8")
        for line in output.split("\n"):
            match = pattern.match(line)
            if match:
                sys_id, rouge_type, measure, result, conf_begin, conf_end = match.groups()
                measure = {'Average_R': 'recall', 'Average_P': 'precision', 'Average_F': 'f_score'}[measure]
                rouge_type = rouge_type.lower().replace("-", '_')
                key = "{}_{}".format(rouge_type, measure)


                results[key] = float(result)
                results["{}_cb".format(key)] = float(conf_begin)
                results["{}_ce".format(key)] = float(conf_end)
        return results


    def execute_rouge(self):
        cmd = "perl " + self.ROUGE_DIR + "ROUGE-1.5.5.pl -e " + self.ROUGE_DIR + "data " + self.ROUGE_ARGS + ' -a ' + self.temp_config_file
        #print("execute_rouge command is" , cmd)
        
        return check_output(cmd, shell=True)

    def get_scores(self, summary, models):
        write_to_file(summary, path.join(self.peers_dir, self.summary_tmp))
        for i, model in enumerate(models):
            write_to_file(" ".join(model), path.join(self.models_dir, "models%s.txt" % (str(i + 1))))

        config = self.create_config([self.summary_tmp], models)

        write_to_file(config, self.temp_config_file)

        output = self.execute_rouge()

        results = self.extract_results(output)
        return results

    def __call__(self, summary, models, summary_len):
        self.ROUGE_ARGS = '-n 4 -m -x -c 95 -r 1000 -f A -p 0.5 -t 0 -a -2 4 -u -l %s' % (summary_len)
        scores = self.get_scores(summary, models)
        return scores 
    
    def _cleanup(self):
        shutil.rmtree(self.temp_dir)
