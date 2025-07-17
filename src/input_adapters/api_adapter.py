from fastapi import FastAPI, Request
import pika
import json
import uuid
from datetime import datetime, timezone

app = FastAPI()

def publish_to_rabbitmq(data: dict):
    """Connects to RabbitMQ and publishes a message."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()

        channel.queue_declare(queue='data_ingestion', durable=True)

        # Construct the canonical message
        message = {
            "metadata": {
                "messageId": str(uuid.uuid4()),
                "sourceSystem": "user_form_api",
                "sourceType": "user_form",
                "sourceTimestamp": datetime.now(timezone.utc).isoformat(),
                "ingestionTimestamp": datetime.now(timezone.utc).isoformat(),
            },
            "payload": data
        }

        channel.basic_publish(
            exchange='',
            routing_key='data_ingestion',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        print(f" [x] Sent message to RabbitMQ")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return False

@app.get("/")
def read_root():
    return {"message": "API Input Adapter is running"}

@app.post("/ingest/form")
async def ingest_form_data(request: Request):
    """Receives data from a user form and publishes it to the ingestion hub."""
    data = await request.json()
    
    if publish_to_rabbitmq(data):
        return {"status": "success", "message": "Data received and queued for processing."}
    else:
        return {"status": "error", "message": "Failed to queue data."}
