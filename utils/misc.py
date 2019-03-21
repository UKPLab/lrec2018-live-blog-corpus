import os
import errno
import logging
import sys
import codecs

def write_to_file(text, filename):
    fp = codecs.open(filename, 'w', 'utf-8', errors='ignore')
    fp.write(text)
    fp.close()


def mkdirp(path):
    """Checks if a path exists otherwise creates it
    Each line in the filename should contain a list of URLs separated by comma.
    Args:
        path: The path to check or create
    """
    if path == '':
        return
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def set_logger(log_file):
    console_format = '[%(levelname)s] (%(name)s) %(message)s'
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console)

    if os.path.dirname(log_file):
        file_format = '[%(levelname)s] (%(name)s) %(message)s'
        log_file = logging.FileHandler(log_file, mode='w')
        log_file.setLevel(logging.DEBUG)
        log_file.setFormatter(logging.Formatter(file_format))
        logger.addHandler(log_file)


class ProgressBar(object):
        """Simple progress bar.
        Output example:
                100.00% [2152/2152]
        """

        def __init__(self, total=100, stream=sys.stderr):
            self.total = total
            self.stream = stream
            self.last_len = 0
            self.curr = 0

        def Increment(self):
            self.curr += 1
            self.PrintProgress(self.curr)

            if self.curr == self.total:
                print('')

        def PrintProgress(self, value):
            self.stream.write('\b' * self.last_len)
            pct = 100 * self.curr / float(self.total)
            out = '{:.2f}% [{}/{}]'.format(pct, value, self.total)
            self.last_len = len(out)
            self.stream.write(out)
            self.stream.flush()
