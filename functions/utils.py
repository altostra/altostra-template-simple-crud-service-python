def success(value):
  result = {
    'statusCode': 200,
  }

  if value:
    result['body'] = value

  return result


def notFound():
  return { 'statusCode': 404 }

def badRequest():
  return { 'statusCode': 400 }

def serverError(reason):
  result = {
    'statusCode': 500,
  }

  if reason:
    result['body'] = reason

  return result



def methodNotSupported():
  return { 'statusCode': 405 }


def trySanitize(value):
  try:
    return value and value.str()[:36]
  except BaseException as err:
    print('Error during value sanitation.\n', err)
