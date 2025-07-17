import pika
import json
import time
import os

OUTPUT_DIR = "output"

def process_message(channel, method, properties, body):
    """Callback function to process a message and write it to a file."""
    print(f" [x] Received message for file output")
    try:
        message = json.loads(body)
        message_id = message.get('metadata', {}).get('messageId', 'unknown')
        
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        file_path = os.path.join(OUTPUT_DIR, f"{message_id}.json")
        with open(file_path, 'w') as f:
            json.dump(message, f, indent=2)
        
        print(f"  - Successfully wrote message to {file_path}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"An error occurred: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag)

def main():
    """Main function to start the file writer service."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()

            # Declare the output queue
            channel.queue_declare(queue='file_output_queue', durable=True)
            print(' [*] Waiting for messages to write to file. To exit press CTRL+C')

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='file_output_queue', on_message_callback=process_message)

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection to RabbitMQ failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Interrupted by user. Shutting down...")
            break

if __name__ == '__main__':
    main()
