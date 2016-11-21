import pika
from settings import RABBIT_SERVER

rabbitSetting = RABBIT_SERVER

credentials = pika.PlainCredentials(
    rabbitSetting['credential']['username'],
    rabbitSetting['credential']['password'])
parameters = pika.ConnectionParameters(
    rabbitSetting['server'],
    rabbitSetting['port'],
    '/',
    credentials)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()


channel.queue_declare(
    queue      = rabbitSetting['chanells']['recive'],
    durable    = True,
    exclusive  = False,
    auto_delete= False)

print ' [*] Waiting for messages. To exit press CTRL+C'

def get_request(ch, method, properties, body):
    print " [x] Received %r" % (body,)

channel.basic_consume(
    get_request,
    queue = rabbitSetting['chanells']['recive'],
    no_ack= True)

channel.start_consuming()
