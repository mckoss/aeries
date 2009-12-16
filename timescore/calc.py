from datetime import datetime
import math
import logging

class Score():
    """
    Base functions for calculating half-life values from a stream of scoring events.
    
    Time units are abstract and zero-based.  The default half-life is 1 time unit.
    
    The Net score is valid at a particular time, time_last.  log_score is globally comparable as it is
    based at time t = 0.
    """
    
    def __init__(self, time_half=1.0, log_score=0.0, time_last=0.0):
        """
        The score cannot be 0 - since we use Log(S) as a ordering key.  Instead, all scores
        are based at value = 1 at time = 0.  Negative log scores would occur for score values less
        than 1 at time = 0 - these are not allowed.
        """
        self.time_half = float(time_half)
        self.k = 0.5 ** (1.0/self.time_half)
        self.time_last = float(time_last)
        self.log_score = float(log_score)
        self.increment(0, self.time_last)
        
    def increment(self, value=0.0, time_now=None):
        """
        Increment the current timescore, and normalize S to match the larges time
        seen to date (self.time_last).
        
        Note that self.score is an output variable only (calculated from log_score).
        """
        value = float(value)
        
        if time_now is None:
            time_now = self.time_last
        else:
            time_now = float(time_now)
        
        if time_now > self.time_last:
            self.score = 2.0 ** (self.log_score - time_now/self.time_half)
            self.score += value
            self.time_last = time_now
        else:
            self.score = 2.0 ** (self.log_score - self.time_last/self.time_half)
            self.score += (self.k ** (self.time_last - time_now)) * value

        try:    
            self.log_score = math.log(self.score)/math.log(2) + self.time_last/self.time_half
        except:
            # Even on underflow, we want to advance the time_last to the present.
            # The score for an underflow value will be zero, we also set the log to zero
            # to sort it last among its cohorts.
            """
            logging.info("Timescore underflow [%.2fL @ %.2f] + [%.2f @ %.2f] T=%.0f => [0L @ %.2f]" %
                         (self.log_score, self.time_last,
                          value, time_now,
                          self.time_half,
                          self.time_last))
            """
            self.score = 0.0
            self.log_score = 0.0
            
class RateLimit(object):
    """
    Rate accumulator - using exponential decay over time.
    
    At any time, we can query the "current value" of a rate of values, and test if it has exceeded
    a specified threshold.  In the absence of updated values, the value of the level will
    drop by half each secs_half seconds.
    """
    def __init__(self, threshold, secs_half=60):
        self.value = 0.0
        self.threshold = threshold
        self.k = 0.5 ** (1.0/secs_half)
        self.secs_last = 0
        
    def is_exceeded(self, secs, value=1.0):
        """
        Update and return the current value of the accumulator IFF the accumulated
        value would not exceed the given threshold.
        """
        # Error - should not go back in time - just fail
        if secs < self.secs_last:
            return True

        _is_exceeded = self.current_value(secs) + value > self.threshold
        
        # Only update the score on success - allows minimum rate through
        # regardless of how frequently it is called.
        if not _is_exceeded:
            self.value += value
            
        return _is_exceeded
    
    def current_value(self, secs, value=0):
        """
        Return the value for the current time.  If value is given, add it
        to the current value (regardless of the threshold limit).
        """
        # Invalid time - return the value at the latest time, if a past time is given
        if secs < self.secs_last:
            return self.value
        
        # Decay current value
        self.value *= (self.k ** (secs - self.secs_last))
        self.secs_last = secs
        self.value += value
        
        return self.value

class MemRate(object):
    """ Rate-limiter persisted to memcache """
    def __init__(self, key, rpmMax=10, secsAge=300):
        self.rate = None
        self.key = key
        self.rpmMax = rpmMax
        self.secsAge = secsAge
        self.fExceeded = None
        
    def exceeded(self):
        if self.fExceeded is not None:
            return self.fExceeded

        self.EnsureRate()
        self.fExceeded = self.rate.exceeded()
        memcache.set('rate.%s' % self.key, self.rate, self.secsAge)
        if self.fExceeded:
            logging.info('MemRate exceeded: %1.2f/%d for %s (%s)' % (self.rate.S*60, self.rpmMax, self.key, self.fExceeded))
        return self.fExceeded
    
    def rpm(self):
        # Return current number of requests per minute
        if self.rate is None:
            return 0.0
        return self.rate.S * 60.0
    
    def ensure_rate(self):
        if self.rate is None:
            self.rate = memcache.get('rate.%s' % self.key)
        if self.rate is None:
            self.rate = Rate(self.rpmMax, 60)