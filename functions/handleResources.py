import boto3
import os
import re
import json
from secrets import token_hex

table_name = os.environ.get('TABLE_DATA01')
aws_region = os.environ.get('AWS_REGION')
db = boto3.client('dynamodb')

handlers = {
  'GET': lambda event: handle_get(event),
  'POST': lambda event: handle_post(event),
  'PUT': lambda event: handle_put(event),
}

def handler(event, context):
  try:
    if event['httpMethod'] in handlers:
      return handlers[event['httpMethod']](event)
    else:
      return methodNotSupported()
  except BaseException as err:
    print('Error: ', err)


def trySanitizeResourceId(value):
  basic = trySanitize(value)
  return basic and re.sub(r'[^\w\d\\-]', '', basic, flags=re.I | re.M)


def toResourceResponse(ddbData):
  return {
    'id': ddbData['pk']['S'],
    'email': ddbData['email']['S'],
    'name': ddbData['name']['S'],
  }

def getResourceAttribute(resource, attr):
  if type(resource) == dict and attr in resource:
    return trySanitize(resource[attr])
  else:
    return None

def getResourceFromBody(event):
  if not 'body' in event:
    return {
      'error': badRequest()
    }

  try:
    parsed_body = json.loads(event['body']) if type(event['body']) == str else event['body']
    return {
      'result': parsed_body
    }
  except BaseException as err:
    print('Failed to parse message body', event['body'], err)
    return {
      'error': badRequest()
    }

def handle_get(event):
  print('Getting resource(s)')

  resource_id = None

  if (
    'pathParameters' in event and
    type(event['pathParameters']) == dict and
    'resourceId' in event['pathParameters']
  ):
    resource_id = trySanitizeResourceId(event['pathParameters']['resourceId'])

  if resource_id:
    resource = db.get_item(
      TableName=table_name,
      Key={
        'pk': { 'S': resource_id },
        'sk': { 'S': resource_id },
      }
    )

    return success(toResourceResponse(resource['Item'])) if 'Item' in resource else notFound()

  resources = db.scan(
    TableName=table_name,
    Limit=50,
  )

  is_found = (resources and
    'Items' in resources and
    type(resources['Items']) == list and
    len(resources['Items']) > 0)

  if not is_found:
    return notFound()
  else:
    result = [
      toResourceResponse(x)
      for x in resources['Items']
    ]

    return success(result)

def handle_post(event):
  print('Creating resource')

  resource_body_result = getResourceFromBody(event)

  if 'error' in resource_body_result:
    return resource_body_result['error']

  resource_info = resource_body_result['result']

  resource_name = getResourceAttribute(resource_info, 'name')
  resource_email = getResourceAttribute(resource_info, 'email')
  resource_id = token_hex(16)

  if type(resource_name) != str or type(resource_email) != str:
    return badRequest()

  db.put_item(
    TableName=table_name,
    ConditionExpression= 'attribute_not_exists(pk)',
    Item= {
      'pk': { 'S': resource_id },
      'sk': { 'S': resource_id },
      'name': { 'S': resource_name },
      'email': { 'S': resource_email },
    }
  )

  return success({
    'id': resource_id,
    'name': resource_name,
    'email': resource_email,
  })

def handle_put(event):
  print('Updating resource')

  resource_body_result = getResourceFromBody(event)

  if 'error' in resource_body_result:
    return resource_body_result['error']

  resource_info = resource_body_result['result']

  resource_name = getResourceAttribute(resource_info, 'name')
  resource_email = getResourceAttribute(resource_info, 'email')

  if not 'pathParameters' in event or not 'resourceId' in event['pathParameters']:
    return badRequest()

  resource_id = trySanitizeResourceId(event['pathParameters']['resourceId'])

  is_valid = 0 == len([
    x
    for x in [resource_id, resource_name, resource_email]
    if type(x) != str or x == ''
  ])

  if not is_valid:
    return badRequest()

  try:
    db.update_item(
      TableName=table_name,
      Key= {
        'pk': { 'S': resource_id },
        'sk': { 'S': resource_id },
      },
      ConditionExpression= '#pk = :pk',
      UpdateExpression= 'set #name = :name, #email = :email',
      ExpressionAttributeNames= {
        '#pk': 'pk',
        '#name': 'name',
        '#email': 'email',
      },
      ExpressionAttributeValues= {
        ':pk': { 'S': resource_id },
        ':name': { 'S': resource_name },
        ':email': { 'S': resource_email },
      }
    )
  except db.exceptions.ConditionalCheckFailedException:
    print('Resource update in DDB failed validation for existing item', resource_id)
    return notFound()
  except BaseException as err:
    print('Resource update in DDB failed unexpectedly', err)
    return serverError()

  return success()

def success(value = ''):
  if type(value) != str:
    value = json.dumps(value, skipkeys=True)

  return {
    'statusCode': 200,
    'body': value if value else 'Success!',
  }

def notFound():
  return {
    'statusCode': 404,
    'body': 'Not found'
  }

def badRequest():
  return {
    'statusCode': 400,
    'body': 'Bad request',
  }

def serverError(reason = ''):
  if type(reason) != str:
    reason = json.dumps(reason, skipkeys=True)

  return {
    'statusCode': 500,
    'body': reason if reason else 'Unexpected error occurred',
  }

def methodNotSupported():
  return {
    'statusCode': 405,
    'body': 'Bad request',
  }

def trySanitize(value):
  try:
    return value and str(value)[:36]
  except BaseException as err:
    print('Error during value sanitation.\n', err)
