from google.appengine.ext import db

from datetime import datetime, timedelta
import logging
import math
import reqfilter
import mixins

import calc

hrsDay = 24
hrsWeek = 7*hrsDay
hrsYear = 365*hrsDay+6
hrsMonth = hrsYear/12

# Scores are based on hours since 1/1/2000
dtBase = datetime(2000,1,1)

def scorable(half_lives=None):
    """
    Class decorator to make a db.Model class scorable.
    
    Usage:
    
        @scorable([half_lives])
        class MyModel(db.Model)
            ...
            
    If using python 2.5:
    
        class MyModel(db.Model)
            ...
            
        MyModel = scorable([half_lives])(MyModel)
    
    The following methods will be added to the class:
    
        update_scores(value, [datetime])
        order_by_score(query, half_life)
        set_timescore_results(results, half_life, [datetime])
        score_now(half_life, [datetime], [increment])
        named_scores([datetime])
    
    The following attributes will be added to the class:
    
        TS_NAME_score = db.FloatProperty() - Log(S) for each half-life being scored
        TS_hrs = db.FloatProperty() - Number of hours since 1/1/2001 at last scoring
        TS_half_lives - non-persisted list of half lives computed for this model       
        
    Note, because app engine db.Model uses a metaclass, this could not
    be implemented as a class decorator, as it must be run during
    class definition time, before the metaclass code runs.
    """
    
    if half_lives is None:
        half_lives = [hrsDay, hrsWeek, hrsMonth, hrsYear]
        
    def _scorable(cls_base):
        """
        Return a new class with the same name as the original, but derived from
        the original class as it's base.  This will allow the metaclass for the db.Model
        to execute at (new) class initialization time and recognize our newly added properties.
        """
        prop_dict = {}
        prop_dict['TS_half_lives'] = tuple(half_lives)
        
        # Add Model properties to the class    
        for hrs in half_lives:
            prop_dict['TS_%s_score' % halflife_name(hrs)] = db.FloatProperty(required=True, default=0.0)
            
        prop_dict['TS_hrs'] = db.FloatProperty(required=True, default=0.0)
        
        # Add timescore methods to the class
        for func in [update_scores, score_now, named_scores, is_new_score]:
            prop_dict[func.__name__] = func
            
        cls_new = type(cls_base.__name__, (cls_base,mixins.Cacheable), prop_dict)
        
        # For pickling to work - we need to have the same module name as the
        # wrapped class
        cls_new.__module__ = cls_base.__module__
            
        logging.info("Scoreable class: %r" % cls_base.__name__)
        
        return cls_new

    """
    These methods will be (dynamically) added to a db.Model class
    """

    def update_scores(self, value=0, dt=None):
        """
        Update the model properties for the timescore values to bring up to the current
        time.  Increasing in score will (attempt to) write the datastore.
        """
        for half_life in self.TS_half_lives:
            ts = self.score_now(half_life, dt, value=value)
            setattr(self, halflife_attr(half_life), ts.log_score)
            self.TS_hrs = ts.time_last
        
        # If we've updated score - we want to persist the model (eventually)
        if value > 0:    
            self.set_dirty()
    
    def score_now(self, half_life, dt=None, value=0):
        """
        Return the current timescore for the given half_life - optionally add a
        value to the current score.
        
        NOT written back to the data store
        """
        ts = calc.Score(half_life, getattr(self, halflife_attr(half_life)), time_last=self.TS_hrs)
        ts.increment(value, hours_from_datetime(dt))
        return ts
    
    def named_scores(self, dt=None):
        """
        Return a dictionary of timescore values for the current time.  It is assumed
        that dt is >= any past scoring time for this model.
        """
        mScores = {}
        for half_life in self.TS_half_lives:
            mScores[halflife_name(half_life)] = self.score_now(half_life, dt).score
        return mScores
    
    def is_new_score(self):
        """
        Return True when the scores seem to be newly initialized.
        """
        return self.TS_hrs == 0.0

    return _scorable

"""
Timescore helper functions
"""

def order_by_score(query, half_life):
    """
    modify the query to be ordered by descending score for the half-life given
    """
    return query.order('-%s' % halflife_attr(half_life))

def set_timescore_results(results, half_life, dt=None):
    """
    Add a (non-persisted) attribute 'timescore' to each model in the
    list of results, corresponding to the current (time-based) score
    for the given half_life.
    """
    for model in results:
        if model is None:
            continue
        model.timescore = model.score_now(half_life, dt).score
    return results
            
def hours_from_datetime(dt=None):
    if dt is None:
        dt = reqfilter.get_request().dtNow
    ddt = dt - dtBase
    hrs = ddt.days*hrsDay + float(ddt.seconds)/60/60
    return hrs

def datetime_from_hours(hrs):
    ddt = timedelta(float(hrs/hrsDay))
    dt = dtBase + ddt
    return dt

def halflife_name(half_life):
    return {hrsDay:'day', hrsWeek:'week', hrsMonth:'month', hrsYear:'year'}.get(half_life, str(half_life))

def halflife_attr(half_life):
    return 'TS_%s_score' % halflife_name(half_life)
