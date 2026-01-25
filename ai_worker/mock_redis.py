
class MockRedis:
    def __init__(self):
        self._data = {}
        
    def from_url(self, url, **kwargs):
        return self
        
    def get(self, key):
        return self._data.get(key)
        
    def set(self, key, value):
        self._data[key] = value
        return True
    
    def mget(self, keys):
        return [self._data.get(k) for k in keys]
        
    def keys(self, pattern):
        import fnmatch
        # Convert redis pattern to python fnmatch
        # Redis: * -> *, ? -> ?
        # This is rough, but enough for "brain:correct:*"
        return fnmatch.filter(self._data.keys(), pattern)
        
    def lpush(self, key, value):
        if key not in self._data:
             self._data[key] = []
        if not isinstance(self._data[key], list):
             return False
        self._data[key].insert(0, value)
        return True
    
    def delete(self, key):
        if key in self._data:
            del self._data[key]
            return 1
        return 0
        
    def pipeline(self):
        return self
        
    def execute(self):
        return []

    def ping(self):
        return True
