import sqlite3
import os.path as path
base_dir = path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

class GuardianExtractionPipeline(object):
    def __init__(self):
        print(base_dir)
        self.conn = sqlite3.connect('%s/data/urls/THE_GUARDIAN_live_blogs.db' % (base_dir))
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS THE_GUARDIAN_WEB_PAGES(
             id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
             webpage TEXT,
             url TEXT,
             title TEXT
        )
        """)
        self.conn.commit()

    def process_item(self, item, spider):
        self.cursor.execute("""
        INSERT INTO THE_GUARDIAN_WEB_PAGES (url) VALUES(:url)""", dict(item))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
        
        