import sys
if sys.platform == 'linux':
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
__version__ = '0.5.1'
# Path: src/jarvis_conversationalist/conversationalist.py