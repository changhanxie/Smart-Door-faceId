import base64
import cv2
import boto3
import json
import time
import uuid
from random import randint
from boto3.dynamodb.conditions import Key
from datetime import datetime


REGION = 'us-east-1'
KVS_NAME = 'sd-video-stream'
KVS_ARM = 'arn:aws:kinesisvideo:us-east-1:177492267199:stream/sd-video-stream/1605398223572'
DB_VISITOR_NAME = 'sd-visitors'
DB_PASSCODE_NAME = 'sd-passcodes'
DB_MESSAGE_NAME = 'sd-message-filter'
OWNER_PHONE_NUMBER = '+16468295132'
S3_NAME = 'sd-visitor-faces'
REK_COLLECTION = 'SD-rekognition-collection'

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
kvs_client = boto3.client("kinesisvideo")
rek_client = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb', region_name=REGION)
DB_VISITOR = dynamodb.Table(DB_VISITOR_NAME)
DB_PASSCODE = dynamodb.Table(DB_PASSCODE_NAME)
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
    print("stream input", event)
    print("=========================================")
    face_detected = False
    for record in event["Records"]:
        # if face has been already detected, we will not process twice
        if face_detected:
            break

        # decode record
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        data = json.loads(payload)
        print("decoded data", data)
        print("=========================================")
        # data of the face
        face_search_response = data['FaceSearchResponse']

        # contains: StreamARN, FragmentNumber, ServerTimeStamp, ProducerTimeStamp, FrameOfSetInSeconds
        input_information = data['InputInformation']

        if face_search_response:
            face_detected = True
            print("Face detected: ", json.dumps(face_search_response))
            print("=========================================")
        else:
            print("No face detected, skip the record")
            print("=========================================")
            continue


        matched_face = False
        # search from the matched faces
        for response in face_search_response:
            for matched_face in response['MatchedFaces']:
                face_id = matched_face['Face']['FaceId']
                print("found matched face, the face id is ", face_id)
                print("=================================================")
                visitor_info = DB_VISITOR.query(KeyConditionExpression=Key('faceid').eq(face_id))
                print("visitor info from dynamodb: ", visitor_info)
                print("=================================================")
                if len(visitor_info['Items']) > 0:
                    visitor_phone = visitor_info['Items'][0]['phonenumber']
                    passcode_info = DB_PASSCODE.query(KeyConditionExpression=Key('faceid').eq(face_id))
                    print("passcode info from dynamodb: ", passcode_info)
                    print("=================================================")
                    if len(passcode_info['Items']) > 0:
                        otp = passcode_info['Items'][0]['otp']

                        print('otp found: ', otp)
                        print("=================================================")
                    else:
                        print('otp not found, we need to create one')
                        otp = randint(100000, 999999)
                        current_time_stamp = int(datetime.now().timestamp())
                        expire_time_stamp = current_time_stamp + 300
                        DB_PASSCODE.put_item(
                            Item={
                                'faceid': face_id,
                                'otp': str(otp),
                                'expirationtimestamp': expire_time_stamp,
                                'currenttimestamp': current_time_stamp,
                            }
                        )
                        print('The new OTP generated, the otp is ', otp)
                        print("=================================================")

                    if checkDuplicate(visitor_phone):
                        web_page2_url = "http://sd-wp2-host.s3-website-us-east-1.amazonaws.com"
                        msg = 'Your face id is ' + face_id + 'and yor otp is ' + str(otp) + ". Please visit " + web_page2_url \
                        + " The otp will expire in 5 minutes"
                        snsres = sns_client.publish(
                            PhoneNumber=visitor_phone,
                            Message=msg
                        )
                        print(snsres)
                        print("SNS message has been send to ", visitor_phone)
                        print("=================================================")

                    matched_face = True
                    break

        if not matched_face:
            # the visitor is not recorded in visitor dynamodb
            if checkDuplicate(OWNER_PHONE_NUMBER):
                # capture from KVS stream and store face img in S3
                end_point = endpoint = kvs_client.get_data_endpoint(
                    APIName='GET_HLS_STREAMING_SESSION_URL',
                    StreamARN=KVS_ARM
                )['DataEndpoint']
                print("KVS end point: ", end_point)
                print("=========================================")

                # get the HLS stream URL from kinesis-video-archived-media
                kvam = boto3.client('kinesis-video-archived-media', endpoint_url=endpoint)
                URL = kvam.get_hls_streaming_session_url(
                    StreamARN=KVS_ARM,
                    PlaybackMode="LIVE",
                    HLSFragmentSelector={'FragmentSelectorType': 'SERVER_TIMESTAMP'}
                )['HLSStreamingSessionURL']
                print("KVS HLS streaming session URL: ", URL)
                print("=========================================")

                # capture frame by cv2
                capture = cv2.VideoCapture(URL)
                file_name = ''
                while (True):
                    sucess, frame = capture.read()
                    if frame is not None:
                        capture.set(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT) / 2) - 1)
                        file_name = '/tmp/frame_' + time.strftime("%Y%m%d-%H%M%S") + '.jpg'
                        cv2.imwrite(file_name, frame)
                        print("KVS Frame captured, the file name is ", file_name)
                        print("=================================================")
                        break
                    else:
                        continue
                capture.release()
                face_id = str(uuid.uuid1())
                # upload img file into s3 bucket
                s3_client.upload_file(file_name, S3_NAME, file_name[1:], ExtraArgs={'ACL': 'public-read'})
                S3_image_link = 'https://' + S3_NAME + '.s3.amazonaws.com' + file_name
                print("s3 image link is ", S3_image_link)
                print("=================================================")
                print("new face found")
                web_page1_url = "http://sd-wp1-host.s3-website-us-east-1.amazonaws.com" + "?objectkey='" + file_name[1:] \
                + "'&imageid=" + face_id
                print(web_page1_url)
                msg = 'A new visitor come. Please check for the permission by ' + web_page1_url
                sns_client.publish(
                    PhoneNumber=OWNER_PHONE_NUMBER,
                    Message=msg
                )
                print("SNS message has been send to ", OWNER_PHONE_NUMBER)
                print("=================================================")





















