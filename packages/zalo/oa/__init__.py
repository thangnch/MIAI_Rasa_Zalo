import json
import time

import requests

from packages.zalo import ZaloConfig
from packages.zalo import APIException

class ZaloOaClient(object):
    def __init__(self, access_token, oa_info):
        self.oa_info = oa_info
        self.access_token = access_token

    @property
    def headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
        return headers


    def load_file(self, path):
        if 'http' in path:
            file = requests.get(path, stream=True).content
        else:
            file = open(path, 'rb').read()
        if len(file) > ZaloConfig.MAXIMUM_FILE_SIZE:
            raise APIException("file size exceeded the maximum size permitted")
        return file

    def send(self, payload, recipient_id, event_name='user_send_text', notification_type='REGULAR', timeout=None, tag=None):
        endpoint = ZaloConfig.DEFAULT_FEEDBACK_API_TO_CLIENT + '?access_token=' + self.access_token

        if event_name not in ZaloConfig.EVENTS_ALLOW:
            payload = {"text": ZaloConfig.MESSAGE_EVENT_NOT_EXTSTS}

        if event_name in ZaloConfig.EVENTS_NOT_ALLOW:
            payload = {"text": ZaloConfig.MESSAGE_NOT_ALLOW}

        body = {
            "recipient": {
                "user_id": recipient_id
            },
            "message": payload
        }
        r = requests.post(url=endpoint,data=json.dumps(body), headers=self.headers)
        return r.json()