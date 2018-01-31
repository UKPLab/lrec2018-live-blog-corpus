import os.path as path
base_dir = path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
import sqlite3

class GuardianExtractionPipeline(object):
    def __init__(self):  
        self.output_file = '%s/data/raw/db/Guardian.db' % (base_dir)
        self.conn = sqlite3.connect(self.output_file)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS THE_GUARDIAN_WEB_PAGES(
             id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
             webpage TEXT,
             url TEXT
        )
        """)
        self.conn.commit()
    
    def process_item(self, item, spider):
        d = dict(item)
        self.cursor.execute("""
         INSERT INTO THE_GUARDIAN_WEB_PAGES(webpage, url) VALUES(?, ?)""", (d["content"],  d["url"]))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
        print('Finished Crawling\nURL Content in the following file:')
        print(self.output_file)
        