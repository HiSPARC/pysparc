#!/usr/bin/python

import redis

db = redis.StrictRedis(socket_timeout=1)
db.set('test', (2 ** 16 - 1 - 8) * 'x')
db.get('test')
