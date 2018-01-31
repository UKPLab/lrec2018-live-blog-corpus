import os.path as path
base_dir = path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

class GuardianExtractionPipeline(object):
    def __init__(self):
        self.output_file = '%s/data/raw/urls/Guardian.txt' % (base_dir)
        self.fp = open(self.output_file, 'w')
        
    def process_item(self, item, spider):
        self.fp.write(item['url'] + '\n')
        return item

    def close_spider(self, spider):
        self.fp.close()
        print('Finished Crawling\nURLs in the following file:')
        print(self.output_file)
        