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
redis_client = redis.Redis(host='redis-18057.c14.us-east-1-3.ec2.redns.redis-cloud.com', port=18057, password='utgvvXEMTVMuMdIhHcWVZmKS31UeJwqN')
# Initialize Flask-Caching with Redis
cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_HOST': redis_client})
cache.init_app(app)

#'維修報障':'964527751929401344',
nodeNameTemplate = {
    '補充稱呼':'965465089543114752',
    '咨詢裝置':'965466943903645696',
    '上傳圖片':'965751411386228736',
    '故障位置及具體信息':'965829406364942336'
    }

templateList =['補充稱呼','咨詢裝置','上傳圖片','故障位置及具體信息']

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
    

    EMSDreply, nodeName = getEMSDreplay(data[0]['From'],data[0]['Message'].replace('我已明白','維修報障'))
    if nodeName[0]['nodeName'] == '新對話':
        defaultReplay(data[0]['From'])
    else if nodeName[0]['nodeName'] in templateList:
        handleMsgTemplate(nodeNameTemplate[nodeName[0]['nodeName']],data[0]['From'])
    else:
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
        content=str({"text": inputMsg, "link": "", "caption": "", "fileName": "" })
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


@staticmethod
def handleMsgTemplate(template, receiver):
    client = create_client()
    send_chatapp_message_request = cams_20200606_models.SendChatappMessageRequest(
        channel_type='whatsapp',
        type='template',
        from_='85262098942',
        to=receiver,
        template_code=template,
        language='zh_HK'
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
        "userId": msgFrom,
        "platform": "web",
        "question":inputMsg,
        "lang":"tc"
    }

    if data['question']!="維修報障":  
        jsession = redis_client.hget('jkey',msgFrom)
        #j_cookies = Path("cookies.json").read_text()  # save them t
        #response = requests.post(url_pd, json=data,cookies={'JSESSIONID':j_cookies})
        print(jsession.decode('utf-8'))
        if jsession != None:
            response = requests.post(url_pd, json=data,cookies={'JSESSIONID':jsession.decode('utf-8')})
        else:
            response = requests.post(url_pd, json=data)
    else:
        response = requests.post(url_pd, json=data)


    setcookie = response.headers.get('Set-cookie')
    
    if setcookie != None:
        redis_client.hset('jkey',msgFrom,response.headers['Set-cookie'].split(";")[0].split("'")[0].split("=")[1])
        redis_client.expire(msgFrom, 259200)
            
    
    #Path("cookies.json").write_text(response.headers['Set-cookie'].split(";")[0].split("'")[0].split("=")[1])
    if "nodeName" in response.json():
        nodeDataJson = [{'nodeName':"維修報障"}]
    else if resppnse.json['type']==0:
        nodeDataJson = [{'nodeName':"新對話"}]
    else:
        try:
            nodeData = response.json()['commands'][3]['args'][0]
            nodeDataJson = json.loads(nodeData)
        except:
            nodeDataJson = [{'nodeName':"no"}]

    #if "nodeName" in response.json():
        #nodeDataJson = [{'nodeName':"維修報障"}]
    return response.json()['content'], nodeDataJson

def defaultReplay(msgFrom):
    handleMsgTemplate(966145163388940288, msgFrom)

if __name__ == '__main__':
    app.run()
