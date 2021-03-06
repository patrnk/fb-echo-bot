import os
import sys
import json
import logging
import datetime

import requests
from flask import Flask, request


app = Flask(__name__)
logger = logging.getLogger(__name__)

COOL_BUTTON_PAYLOAD = 'COOL'


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == os.environ['VERIFY_TOKEN']:
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200

    return '''
    This is a 
    <a href=https://www.facebook.com/Cryptic-tor-11398-134739810390203>Facebook bot</a>
    ''', 200


@app.route('/', methods=['POST'])
def webhook():
    SUCCESS = ('Success.', 200)
    facebook_request = request.get_json()
    if facebook_request['object'] != 'page':
        return SUCCESS
    for entry in facebook_request['entry']:
        for messaging_event in entry['messaging']:
            echo_message(messaging_event)
            react_to_cool_button(messaging_event)
    return SUCCESS


def echo_message(messaging_event):
    ''' For thorough description of messaging events,
        see https://developers.facebook.com/docs/messenger-platform/webhook-reference/message
    '''
    if 'message' not in messaging_event:
        return
    if 'text' not in messaging_event['message']:  # happens when user sends a like
        return
    sender_id = messaging_event['sender']['id']
    timestamp = messaging_event['timestamp']
    text_received = messaging_event['message']['text']
    
    text_to_send = 'Your id is {0}.  You\'ve sent a message with the  timestamp {1}'\
                   ' and the following text: "{2}"'.format(sender_id, timestamp, text_received)
    send_message(sender_id, text_to_send, add_button=True)


def send_message(recipient_id, message_text, add_button=False):
    headers = {
            'Content-Type': 'application/json',
            }
    params = {
            'access_token': os.environ['PAGE_ACCESS_TOKEN'],
            }

    post_request_data = {
            'recipient': {
                'id': recipient_id,
                },
            }
    if add_button:
        post_request_data['message'] = {
                        'attachment': form_cool_button(message_text),
                        }
    else:
        post_request_data['message'] = {
                        'text': message_text,
                        }
    json_post_request_data = json.dumps(post_request_data)
    response = requests.post('https://graph.facebook.com/v2.6/me/messages', headers=headers,
                             params=params, data=json_post_request_data)
    if response.status_code != 200:
        logger.error(response.status_code)
        logger.error(response.text)


def form_cool_button(message_text):
    return {
        'type': 'template',
        'payload': {
            'template_type': 'button',
            'text': message_text,
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Cool!',
                    'payload': COOL_BUTTON_PAYLOAD,
                }
            ]
        }
    }


def react_to_cool_button(messaging_event):
    if 'postback' not in messaging_event:
        return
    if 'payload' not in messaging_event['postback']:
        return
    if messaging_event['postback']['payload'] != COOL_BUTTON_PAYLOAD:
        return
    sender_id = messaging_event['sender']['id']
    send_message(sender_id, 'Thank you!')


if __name__ == '__main__':
    app.run(debug=True)
