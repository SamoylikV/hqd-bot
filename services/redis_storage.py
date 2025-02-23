import json


class AutoSaveDict(dict):
    def __init__(self, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__callback = callback
        for k, v in list(self.items()):
            if isinstance(v, dict) and not isinstance(v, AutoSaveDict):
                super().__setitem__(k, AutoSaveDict(v, callback=self.__callback))

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, AutoSaveDict):
            value = AutoSaveDict(value, callback=self.__callback)
        super().__setitem__(key, value)
        if self.__callback:
            self.__callback(self)

    def __delitem__(self, key):
        super().__delitem__(key)
        if self.__callback:
            self.__callback(self)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).items():
            self[k] = v
        if self.__callback:
            self.__callback(self)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
            return self[key]
        return self[key]

class RedisDict:
    def __init__(self, redis_client, name):
        self.redis = redis_client
        self.name = name

    def __getitem__(self, key):
        raw = self.redis.hget(self.name, key)
        if raw is None:
            raise KeyError(key)
        value = json.loads(raw)
        if isinstance(value, dict):
            return AutoSaveDict(value, callback=lambda updated: self.__setitem__(key, updated))
        return value

    def __setitem__(self, key, value):
        if isinstance(value, AutoSaveDict):
            value = dict(value)
        self.redis.hset(self.name, key, json.dumps(value))

    def __delitem__(self, key):
        if not self.redis.hdel(self.name, key):
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return self.redis.hlen(self.name)

    def get(self, key, err_item=None):
        raw = self.redis.hget(self.name, key)
        if raw is None:
            return err_item
        return json.loads(raw)

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        raw_values = self.redis.hvals(self.name)
        results = []
        for v in raw_values:
            loaded = json.loads(v)
            if isinstance(loaded, dict):
                results.append(AutoSaveDict(loaded, callback=lambda updated, key=v: self.__setitem__(key, updated)))
            else:
                results.append(loaded)
        return results

    def items(self):
        raw_items = self.redis.hgetall(self.name)
        items = {}
        for k, v in raw_items.items():
            loaded = json.loads(v)
            if isinstance(loaded, dict):
                items[k] = AutoSaveDict(loaded, callback=lambda updated, key=k: self.__setitem__(key, updated))
            else:
                items[k] = loaded
        return items.items()

    def setdefault(self, key, default):
        try:
            value = self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default
        return value

    def pop(self, key, default=object()):
        try:
            value = self.__getitem__(key)
        except KeyError:
            if default is not object():
                return default
            raise KeyError(key)
        self.__delitem__(key)
        return value

