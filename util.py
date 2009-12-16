import re
import urlparse
import logging

from google.appengine.ext import db

import settings
import reqfilter

DEBUG = settings.DEBUG

def href(url):
    # Quote url text so it can be embedded in an HTML href
    ich = url.find('//')
    path = url[ich+2:].replace('"', '%22')
    return url[0:ich+2] + path

def trim_string(st):
    if st == None:
        st = ''
    return re.sub('[\000-\037]', '', str(st)).strip()

def escape_html(s):
    # Escape test so it does not have embedded HTML sequences
    return s.replace('&', '&amp;').\
        replace('<', '&lt;').\
        replace('>', '&gt;').\
        replace('"', '&quot;').\
        replace("'", '&#39;')

regNonchar = re.compile(r"[^\w]")
regDashes = re.compile(r"[\-]+")
regPrePostDash = re.compile(r"(^-+)|(-+$)")

def slugify(s):
    """
    Convert runs of all non-alphanumeric characters to single dashes
    """
    if s is None:
        s = ""
    s = str(s)
    s = regNonchar.sub('-', s).lower()
    s = regDashes.sub('-', s)
    s = regPrePostDash.sub('', s)
    return s

regBanned = re.compile(r"cunt|fuck|pussy|shit|tits")

def has_bad_word(s):
    return regBanned.search(s) is not None

def run_in_transaction(func):
    """
    Function decorator to wrap entire function in an App Engine transaction
    
    Usage:
    
        @run_in_transaction
        def my_function()
            ...
    """
    def _transaction(*args, **kwargs):
        return db.run_in_transaction(func, *args, **kwargs)
    return _transaction

def group_by(aList, n):
    """ Group the elements of a list into a list with n elements in each sub-list
    Turns [1,2,3,4,5,6,7] into [[1,2,3],[4,5,6],[7]) """
    
    return [aList[i:i+n] for i in range(0, len(aList), n)]


class enum(object):
    """
    enum - an enumeration class for python to assign symbolic values to integers
    
    Usage:
    
        colors = enum('red', 'yellow', 'green', 'blue', green=20)
        
            colors.red == 0
            colors.yellow == 1
            colors.green == 20
            colors.blue == 21
    
    """
    __init = 1
    def __init__(self, *args, **kw):
        value = 0
        self.__names = args
        self.__dict = {}
        for name in args:
            if kw.has_key(name):
                value = kw[name]
            self.__dict[name] = value
            value = value + 1
        self.__init = 0

    def __getitem__(self, name):
        return getattr(self, name)

    def __getattr__(self, name):
        return self.__dict[name]

    def __setattr__(self, name, value):
        if self.__init:
            self.__dict__[name] = value
        else:
            raise AttributeError, "enum is ReadOnly"

    def __call__(self, name_or_value):
        if type(name_or_value) == type(0):
            for name in self.__names:
                if getattr(self, name) == name_or_value:
                    return name
            else:
                raise TypeError, "no enum for %d" % name_or_value
        else:
            return getattr(self, name_or_value)

    def __repr__(self):
        result = ['<enum']
        for name in self.__names:
            result.append("%s=%d" % (name, getattr(self, name)))
        return string.join(result)+'>'

    def __len__(self):
        return len(self.__dict)

    def __iter__(self):
        return self.__dict.__iter__()
    
    def items(self):
        return self.__dict.items()
    
    def keys(self):
        return self.__dict.keys()
    
    def values(self):
        return self.__dict.values()
    
"""
url parsing and helper functions
"""

# Allow all the country domains (2 letter), and the currently defined gTLD's
# Also allow raw IP addresses, e.g., 192.168.1.1
# BUG - handle "Unicode domains"
regDomain = re.compile(r"^" + \
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|" + \
    r"(([a-z0-9][a-z0-9-]*\.)+([a-z]{2}|" + \
        r"aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|net|org|pro|tel|travel))|" + \
    r"(pageslike)|(localhost)" if DEBUG else "" +
    "$", re.I)

# ordering of urlparse.urlsplit() array elements
split = enum('scheme', 'domain', 'path', 'query', 'fragment')

def normalize_url(url, domain_canonical=None):
    """
    Ensure we have a value url - raise exception if not.
    
    If given, we convert the domain to a domain_canonical
    """
    url = url.strip()
    rgURL = list(urlparse.urlsplit(url))
    if rgURL[split.scheme] == '':
        url = r"http://%s" % url
        rgURL = list(urlparse.urlsplit(url))
    
    # Invalid protocol
    if rgURL[split.scheme] != "http" and rgURL[split.scheme] != "https":
        raise reqfilter.Error("Invalid protocol: %s" % rgURL[split.scheme]) 

    if domain_canonical is not None:
        rgURL[split.domain] = domain_canonical
    
    if rgURL[split.domain]:
        rgURL[split.domain] = rgURL[split.domain].lower()
    
    if not rgURL[split.domain] or not regDomain.search(rgURL[split.domain]) or len(rgURL[split.domain]) > 255:
        raise reqfilter.Error("Invalid URL: %s" % urlparse.urlunsplit(rgURL))

    # Always end naked domains with a trailing slash as canonical
    if rgURL[split.path] == '':
        rgURL[split.path] = '/'

    return urlparse.urlunsplit(rgURL)

def domain_from_url(url):
    return urlparse.urlsplit(url)[split.domain];

