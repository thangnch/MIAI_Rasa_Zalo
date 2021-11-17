import json
import requests
import time
import ZaloConfig
import APIException

class Zalolient():
    def send(self, endpoint, params, method):
        print("Send zalo ne")
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
        headers.update(ZaloConfig.DEFAULT_HEADER)
        response = requests.post(url=endpoint, data=params, headers=headers)
        if response.status_code != 200:
            raise APIException(response.text, response.status_code, method)
        return response.json()


    def create_oa_params(self, data, oa_info):
        timestamp = int(round(time.time() * 1000))

        for key, value in data.items():
            if type(value) is dict:
                data[key] = json.dumps(value)

        params = {
            'oaid': oa_info.oa_id,
            'timestamp': timestamp,
        }

        params.update(data)
        return params
