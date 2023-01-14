# SJTU EE208

INDEX_DIR = "IndexFiles.index"

import sys, os, lucene, threading, time
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.error
import urllib.parse
import urllib.request
import jieba
from urllib.parse import urlparse

# from java.io import File
from java.nio.file import Paths
from org.apache.lucene.analysis.core import SimpleAnalyzer ,WhitespaceAnalyzer
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType, StringField, TextField
from org.apache.lucene.index import FieldInfo, IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.util import Version
from org.apache.lucene.analysis.core import SimpleAnalyzer

"""
This class is loosely based on the Lucene (java implementation) demo class 
org.apache.lucene.demo.IndexFiles.  It will take a directory as an argument
and will index all of the files in that directory and downward recursively.
It will index on the file path, the file name and the file contents.  The
resulting Lucene index will be placed in the current directory and called
'index'.
"""

class Ticker(object):

    def __init__(self):
        self.tick = True

    def run(self):
        while self.tick:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(1.0)

class IndexFiles(object):
    """Usage: python IndexFiles <doc_directory>"""

    def __init__(self, root1, root2, storeDir):

        if not os.path.exists(storeDir):
            os.mkdir(storeDir)

        store = SimpleFSDirectory(Paths.get(storeDir)) #索引文件存放的位置
        analyzer = SimpleAnalyzer()
        # analyzer = StandardAnalyzer()
        analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
        config = IndexWriterConfig(analyzer)
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
        writer = IndexWriter(store, config)

        self.indexDocs(root1, root2, writer)
        ticker = Ticker()
        print('commit index')
        threading.Thread(target=ticker.run).start()
        writer.commit()
        writer.close()
        ticker.tick = False
        print('done')

    def indexDocs(self, root1, root2, writer):

        t1 = FieldType()
        t1.setStored(True)
        t1.setTokenized(False)
        t1.setIndexOptions(IndexOptions.NONE)  
        
        t2 = FieldType()
        t2.setStored(False)
        t2.setTokenized(True)
        t2.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS) 
        
        for root1, dirnames, filenames in os.walk(root1):
            for filename in filenames:

                print("adding", filename)
                try:
                    path1 = os.path.join(root1, filename)
                    path2 = os.path.join(root2, filename)
                    file1 = open(path1, encoding='utf8')
                    file2 = open(path2, encoding='utf8')
                    url = ''
                    date = ''
                    title = ''
                    contents = ''
                    for line in file1.readlines():
                        if(url == ''):
                            url = line
                            continue
                        if(title == ''):
                            title = line
                            continue
                        if(date == ''):
                            date = line
                            continue
                        if(contents == ''):
                            contents = line
                            continue
                    a = 0
                    for line in file2.readlines():
                        a+=1
                        if(a == 6):
                            img = line 
                    contents = ' '.join(jieba.cut(contents))
                    file1.close()
                    doc = Document()
                    doc.add(Field("name", filename, t1))
                    doc.add(Field("path", path1, t1))
                    doc.add(Field("url",url,t1))
                    doc.add(Field("date",date,t1))
                    doc.add(Field("title",title,t1))
                    doc.add(Field("img",img,t1))
                    if len(contents) > 0:

                        doc.add(Field("contents", contents, t2))
                    else:
                        print("warning: no content in %s" % filename)
                    writer.addDocument(doc)
                except Exception as e:
                    print("Failed in indexDocs:", e)

if __name__ == '__main__':
    lucene.initVM()#vmargs=['-Djava.awt.headless=true'])
    print('lucene', lucene.VERSION)
    # import ipdb; ipdb.set_trace()
    start = datetime.now()
    try:
        IndexFiles('163_html','163_graph_html','163_index')
        end = datetime.now()
        print(end - start)
    except Exception as e:
        print("Failed: ", e)
        raise e

