import os
import sys

from typing import List
from flask_caching import Cache
import redis
from alibabacloud_cams20200606.client import Client as cams20200606Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cams20200606 import models as cams_20200606_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
import json
from flask import Flask, request, jsonify, make_response

# get Website
import requests
import time
import math
import json

ts = math.ceil(time.time())
url_test = "https://emsd.ibot.cn/emsdbot/irobot/ask4Json?t="+str(ts)
url_pd = "https://cscagent.emsd.gov.hk/emsdbot/irobot/ask4Json?t="+str(ts)


#

app = Flask(__name__)
# Initialize Redis client
redis_client = redis.Redis(host='redis-14054.c300.eu-central-1-1.ec2.redns.redis-cloud.com', port=14054, password='wk9CAVnoyufUe0jaADxkvHBAujTPZSLG')
# Initialize Flask-Caching with Redis
cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_HOST': redis_client})
cache.init_app(app)


# cache.cached(timeout=100, key_prefix='items')
@app.route('/webhook', methods=['POST'])
def webhook_receiver():
    data = request.json 
    print(data)
    wtsmsgid = data[0]['MessageId']
    payload=request.get_json()
    print(payload)
    event_key= wtsmsgid
    if redis_client.exists(event_key):
        return jsonify({'message':'already proceeded'}), 200
    print('send message')
    redis_client.set(event_key,'1',ex=3600)
    #redis_client.add(wtsmsgid)
    #if jsonify(cached_response).data['MessageId']==jsonify(data)['MessageId']:
     # Get the JSON data from the incoming request
    # Process the data and perform actions based on the event   
    print("Received webhook data:", payload)

    EMSDreply = getEMSDreplay(data[0]['From'],'維修報障')

    
    handleMsg(EMSDreply, data[0]['From'])
    return make_response(jsonify({'success':True}),200)
    #return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/status', methods=['POST'])
def webhook_status_receiver():
    data = request.json  # Get the JSON data from the incoming request
    # Process the data and perform actions based on the event
    print("Received")
    return make_response(jsonify({'success':True}),200)

def create_client() -> cams20200606Client:
    """
    Initialize the Client with the AccessKey of the account
    @return: Client
    @throws Exception
    """
    # The project code leakage may result in the leakage of AccessKey, posing a threat to the security of all resources under the account. The following code examples are for reference only.
    # It is recommended to use the more secure STS credential. For more credentials, please refer to: https://www.alibabacloud.com/help/en/alibaba-cloud-sdk-262060/latest/configure-credentials-378659.
    config = open_api_models.Config(
        access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        # Required, please ensure that the environment variables ALIBABA_CLOUD_ACCESS_KEY_SECRET is set.,
        access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
    )
    # See https://api.alibabacloud.com/product/cams.
    config.endpoint = f'cams.ap-southeast-1.aliyuncs.com'
    return cams20200606Client(config)

@staticmethod
def handleMsg(inputMsg, receiver):
    client = create_client()
    send_chatapp_message_request = cams_20200606_models.SendChatappMessageRequest(
        channel_type='whatsapp',
        type='message',
        message_type='text',
        from_='85262098942',
        to=receiver,
        content=str({"text": "I hear you say "+inputMsg, "link": "", "caption": "", "fileName": "" })
    )
    # runtime = util_models.RuntimeOptions()
    try:
        # Copy the code to run, please print the return value of the API by yourself.
        client.send_chatapp_message(send_chatapp_message_request)
    except Exception as error:
        # Only a printing example. Please be careful about exception handling and do not ignore exceptions directly in engineering projects.
        # print error message
        print(error.message)
        # Please click on the link below for diagnosis.
        print(error.data.get("Recommend"))
        UtilClient.assert_as_string(error.message)

# Website 
def getEMSDreplay(msgFrom,inputMsg):
    data = {
        "sessionId": "77",
        "userId": "234324",
        "platform": "web",
        "question":inputMsg,
        "lang":"tc"
    }

    if data['question']!="維修報障":  
        jsession = redis_client.get(msgFrom)
        #j_cookies = Path("cookies.json").read_text()  # save them t
        #response = requests.post(url_pd, json=data,cookies={'JSESSIONID':j_cookies})
        response = requests.post(url_pd, json=data,cookies={'JSESSIONID':jsession['js']})
    else:
        response = requests.post(url_pd, json=data)


    setcookie = response.headers.get('Set-cookie')
    if setcookie != None:
        redis_client.hmset(msgFrom,{'js':response.headers['Set-cookie'].split(";")[0].split("'")[0].split("=")[1]})
        redis_client.expire(msgFrom, 259200)
    #Path("cookies.json").write_text(response.headers['Set-cookie'].split(";")[0].split("'")[0].split("=")[1])
    
    return response.json()['content']



if __name__ == '__main__':
    app.run()

