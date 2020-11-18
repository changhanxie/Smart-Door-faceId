import json
import boto3
import logging
from datetime import datetime
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def validateOTP(res, userOtp):
    try:
        print(res)
        print("=======================")
        name = None
        if res["Items"] is None:
            message = "invalid OTP"
        else:
            dbOTP = res["Items"][0]["otp"]
            face_id = res["Items"][0]['faceid']
            timeStamp = res["Items"][0]["expirationtimestamp"]
            curTimeStamp = int(datetime.now().timestamp())
            dbOTP = int(dbOTP)
            # logger.error("DB OTP:"+str(dbOTP)+" DB TS:"+str(timeStamp) + " INPUT OTP:"+str(userOtp)+" INPUT TS:"+str(curTimeStamp))
            timeStamp = int(timeStamp)
            if str(userOtp) == str(dbOTP) and timeStamp > curTimeStamp:
                # delete otp
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table('sd-passcodes')
                table.delete_item(
                    Key={
                        'faceid': face_id,
                    })
                table = dynamodb.Table('sd-visitors')

                res = table.query(KeyConditionExpression=Key('faceid').eq(face_id))
                if len(res['Items']) != 0:
                    name = res['Items'][0]['username']
                print(name)
                message = "ACCESS GRANTED"
            else:
                message = "ACCESS DENIED"
                logger.debug("db - " + str(timeStamp) + " now - " + str(curTimeStamp))
                logger.debug("db - " + str(dbOTP) + " user - " + str(userOtp))
    except Exception:
        logger.error("KEY ERROR:" + str(res))
        message = "Invalid OTP"
    return message, name


def queryPasscodesDb(otp):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('sd-passcodes')
    res = table.query(
        IndexName='otp-index',
        KeyConditionExpression=Key('otp').eq(otp),
    )
    return res
    # ORIGINAL DYNAMODB ACCESS CODE
    # dynamodb = boto3.client('dynamodb')
    # res = dynamodb.get_item(
    #     TableName = "sd-passcodes",
    #     Key = {
    #         'faceID' : {
    #             'S' : faceId
    #         }
    #     }
    #     )


def extractAttributes(res):
    if 'message' in res:
        res = res["message"]
    else:
        res = res['body']
        if type(res) is str:
            res = json.loads(res)
            res = res['message']
            logger.error("############" + str(res) + "##########")
        else:
            res = res["message"]
            logger.error("Load message done:============>" + str(res))
    # return res["otp"],res["faceid"]
    return res["otp"]


def lambda_handler(event, context):
    logger.error("#####################################")
    logger.error("Received event:" + str(event))
    logger.error("#####################################")
    # otp, faceId = extractAttributes(event)
    otp = extractAttributes(event)  # user otp

    # res = queryPasscodesDb(otp,faceId)
    res = queryPasscodesDb(otp)
    message, name = validateOTP(res, otp)
    # message = "ok"

    return {
        'statusCode': 200,
        'body': message,
        'name': name
    }