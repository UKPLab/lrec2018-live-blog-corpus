import codecs

class processGuardian(object):
    def __init__(self, json_file):
        self.url_content = {'url':'', 'category': '', 'genre': '', 'title': '',
                             'documents': [], 'summary': [], 'quality':''}
        self.json_file = json_file
    def get_content(self, url):
        
        
        
    parsed_live_blogs = codecs.open(os.path.join('.', folder, json_filename),
                                    'w', encoding="utf-8")  # file where the results are going to be stored
        