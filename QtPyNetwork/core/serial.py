import json
import datetime

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class MessageEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {
                "_type": "datetime",
                "value": obj.strftime(DATETIME_FORMAT)
            }
        return super(MessageEncoder, self).default(obj)


class MessageDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(MessageDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        obj_type = obj['_type']
        if obj_type == 'datetime':
            return datetime.datetime.strptime(obj["value"], DATETIME_FORMAT)
        return obj
