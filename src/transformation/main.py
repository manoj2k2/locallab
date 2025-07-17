import pika
import json
import time
import yaml
from functools import partial
from src.transformation import rules

# --- Rule Engine ---

AVAILABLE_RULES = {
    'add_metadata': rules.add_metadata
}

def apply_transformations(message: dict, config: dict) -> dict:
    """Applies a sequence of transformation rules to a message payload."""
    source_type = message.get('metadata', {}).get('sourceType')
    if not source_type:
        print("  - No sourceType in metadata, skipping transformation.")
        return message

    # Find the matching transformation config
    transformation_config = next((t for t in config.get('transformations', []) if t.get('source_type') == source_type), None)

    if not transformation_config:
        print(f"  - No transformation config found for sourceType: {source_type}")
        return message

    print(f"  - Found transformation config for {source_type}")
    payload = message.get('payload', {})
    for rule_config in transformation_config.get('rules', []):
        rule_type = rule_config.get('type')
        rule_function = AVAILABLE_RULES.get(rule_type)
        if rule_function:
            payload = rule_function(payload, rule_config)
        else:
            print(f"  - Warning: Rule type '{rule_type}' not found.")
    
    message['payload'] = payload
    return message

# --- RabbitMQ Consumer ---

def process_message(channel, method, properties, body, config):
    """Callback function to process a message from the queue."""
    print(f"\n [x] Received message from {method.routing_key}")
    try:
        message = json.loads(body)
        print("  - Original Body:", json.dumps(message, indent=2))

        # Apply transformations
        transformed_message = apply_transformations(message, config)

        print("  - Transformed Body:", json.dumps(transformed_message, indent=2))
        
        # Route to output adapter
        source_type = transformed_message.get('metadata', {}).get('sourceType')
        transformation_config = next((t for t in config.get('transformations', []) if t.get('source_type') == source_type), None)
        if transformation_config:
            target_name = transformation_config.get('target')
            target_config = next((t for t in config.get('targets', []) if t.get('name') == target_name), None)
            if target_config and target_config.get('protocol') == 'file':
                output_queue = target_config.get('queue')
                channel.basic_publish(
                    exchange='',
                    routing_key=output_queue,
                    body=json.dumps(transformed_message),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                print(f"  - Routed message to queue: {output_queue}")

        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print("  - Message acknowledged.")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag)

def main():
    """Main function to start the transformation engine."""
    # Load configuration
    try:
        with open('config/config.yml', 'r') as f:
            config = yaml.safe_load(f)
        print(" [*] Configuration loaded successfully.")
    except FileNotFoundError:
        print(" [!] Error: config.yml not found. Please ensure it exists.")
        return
    except yaml.YAMLError as e:
        print(f" [!] Error parsing config.yml: {e}")
        return

    # Set up a partial function with the loaded config for the callback
    on_message_callback = partial(process_message, config=config)

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()

            channel.queue_declare(queue='data_ingestion', durable=True)
            print(' [*] Waiting for messages. To exit press CTRL+C')

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='data_ingestion', on_message_callback=on_message_callback)

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection to RabbitMQ failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Interrupted by user. Shutting down...")
            break

if __name__ == '__main__':
    main()
