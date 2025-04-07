from kafka import KafkaConsumer
import json

# Initialize Kafka Consumer
consumer = KafkaConsumer(
    'qr_scans',
    'lost_person_reports',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Kafka Consumer is Listening...")

for message in consumer:
    print(f"Received Message: {message.value}")
