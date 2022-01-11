import json

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
