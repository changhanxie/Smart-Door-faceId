import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
import random
from decimal import Decimal
import time
COLLECTION_ID = 'SD-rekognition-collection'
DB_VISITOR_NAME = 'sd-visitors'
DB_MESSAGE_NAME = 'sd-message-filter'
REGION = 'us-east-1'

sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb', region_name=REGION)

DB_VISITOR = dynamodb.Table(DB_VISITOR_NAME)
DB_MESSAGE = dynamodb.Table(DB_MESSAGE_NAME)
def checkDuplicate(phone_number):
    response = DB_MESSAGE.query(KeyConditionExpression=Key('phonenumber').eq(phone_number))
    if len(response['Items']) == 0:
        DB_MESSAGE.put_item(
            Item={
                'phonenumber': phone_number,
                'timestamp': int(datetime.now().timestamp())
            }
        )
    else:
        span = int(datetime.now().timestamp()) - response['Items'][0]['timestamp']
        print("time span is ", span, " s")
        if span < 60:
            return False
        DB_MESSAGE.update_item(
            Key={'phonenumber': phone_number},
            UpdateExpression='set #ts = :t',
            ExpressionAttributeValues={':t': int(datetime.now().timestamp())},
            ExpressionAttributeNames={'#ts': "timestamp"}
        )
    return True

def lambda_handler(event, context):
    print("manually create user: ", json.dumps(event))

    face_id = event["message"]["faceid"]
    phonenumber = event["message"]["phonenumber"]
    objectkey = event["message"]["photos"]["objectkey"]
    bucket = event["message"]["photos"]["bucket"]
    user_name = event["message"]["username"]
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(
            Bucket=bucket,
            Key=objectkey
        )

        print("s3 response: ", response)
        print("=============================")
    except Exception:
        return {
            'statusCode': 200,
            'body': json.dumps('invalid image object key')
        }

    data = response['Body'].read()
    rek = boto3.client('rekognition')
    res = rek.index_faces(
        CollectionId=COLLECTION_ID,
        Image={
            'Bytes': data
        },
        ExternalImageId=face_id
    )

    print(res)
    print("=============================")
    rek_face_id = res['FaceRecords'][0]['Face']['FaceId']
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('sd-visitors')
    visitor_info = DB_VISITOR.query(KeyConditionExpression=Key('faceid').eq(rek_face_id))
    print("visitor info from dynamodb: ", visitor_info)
    print("=================================================")
    if len(visitor_info['Items']) > 0:
        return {
            'statusCode': 200,
            'body': "the visitor has already existed"
        }

    table.put_item(
        Item={
            'faceid': rek_face_id,
            'username': user_name,
            'phonenumber': phonenumber,
            'photos': {
                'objectkey': objectkey,
                'bucket': bucket,
                'createdtimestamp': Decimal.from_float(time.time())
            },
        })

    table = dynamodb.Table('sd-passcodes')
    print(table.creation_date_time)
    OTP = random.randint(100000, 999999)
    currentTime = int(datetime.now().timestamp())

    table.put_item(
        Item={
            'faceid': rek_face_id,
            'expirationtimestamp': (currentTime + 300),
            'currenttimestamp': currentTime,
            'otp': str(OTP)
        })

    sns = boto3.client('sns')
    url = "http://sd-wp2-host.s3-website-us-east-1.amazonaws.com"
    message = "Your OTP is - " + str(OTP) + "\n\n Click here to enter OTP " + url

    print(message)
    try:
        res = sns.publish(
            PhoneNumber=phonenumber,
            Message=message,
        )
    except KeyError:
        print("error in sending sms")

    return {
        'statusCode': 200,
        'body': json.dumps('wf1: the visitor is added to database')
    }
