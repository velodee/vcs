"""
This module provides some useful tools for ``vcs`` like annotate/diff html
output. It also includes some internal helpers.
"""

import time
def makedate():
    lt = time.localtime()
    if lt[8] == 1 and time.daylight:
        tz = time.altzone
    else:
        tz = time.timezone
    return time.mktime(lt), tz



def safe_unicode(str):
    """safe unicode function. In case of UnicodeDecode error we try to return
    unicode with errors replace, if this failes we return unicode with 
    string_escape decoding """
    
    try:
        u_str = unicode(str)
    except UnicodeDecodeError:
        try:
            u_str = unicode(str, 'utf-8', 'replace')
        except UnicodeDecodeError:
            #incase we have a decode error just represent as byte string
            u_str = unicode(str(str).encode('string_escape'))
        
    return u_str
