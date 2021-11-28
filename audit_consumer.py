import json
from ast import literal_eval
from os import environ
from confluent_kafka import Consumer
from elasticsearch import (Elasticsearch,
                           helpers)

def main():    
    ELASTICSEARCH_HOSTS = environ.get('ELASTICSEARCH_HOSTS',
                                      '["localhost:9200"]')
    ELASTICSEARCH_USE_SSL= environ.get('ELASTICSEARCH_USE_SSL',
                                       'False')
    ELASTICSEARCH_PASSWORD = environ.get('ELASTICSEARCH_PASSWORD',
                                         '')
    KAFKA_BOOTSTRAP_SERVERS = environ.get('KAFKA_BOOTSTRAP_SERVERS',
                                          'localhost:9091,localhost:9092')
    AUDIT_TOPICS=['store']

    # Sep up elastic search client
    if literal_eval(ELASTICSEARCH_USE_SSL):
        es = Elasticsearch(literal_eval(ELASTICSEARCH_HOSTS),
                           http_auth=['elastic', ELASTICSEARCH_PASSWORD],
                           use_ssl=literal_eval(ELASTICSEARCH_USE_SSL),
                           verify_certs=False,
                           ssl_show_warn=False)
    else:
        es = Elasticsearch(literal_eval(ELASTICSEARCH_HOSTS))
    
    # Set up kafka consumer 
    config = {'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
              'group.id': 'group-audit',
              'auto.offset.reset': 'largest',
              'session.timeout.ms': 10000}    
    consumer = Consumer(**config)
    # Subscribe to all the topics that require audit trail
    consumer.subscribe(AUDIT_TOPICS)

    # Polling kafka broker topic for message
    try:
        docs = []
        doc_len_prev = 0
        doc_len_current = 0
        doc_len_stagnant = False
        
        while True:
            # determine whether the fetched document list 
            # is growing or stagnant 
            doc_len_current = len(docs)
            if doc_len_current == doc_len_prev and doc_len_current > 0: 
                doc_len_stagnant = True
            else:
                doc_len_stagnant = False
            doc_len_prev = doc_len_current     

            # if the number of document in the list exceed 100
            # OR the document list is stagnant,
            # trigger bulk insert to the elastic search
            # and reset the docuemnt list  
            if doc_len_current > 100 or doc_len_stagnant:
                helpers.bulk(client=es, index='audit', actions=docs)
                docs = []

            # poll kafka for new message, add the message to 
            # document list if available 
            msg = consumer.poll(timeout=1)
            if msg is None:
                continue
            elif msg.error():
                print(f'ERROR: Kafka error code {msg.error().code()}'
                    f'- {msg.error().str()}') 
                continue
            else:
                msg_id = msg.topic() + '-' + \
                         str(msg.partition()) + '-' + \
                         str(msg.offset())
                docs.append(json.loads(msg.value()) |
                            {"_id": msg_id})
    
    except KeyboardInterrupt:
        print('Audit consumer program is aborted')
    finally:
        consumer.close()
        es.close()            
    
if __name__ == '__main__':
    main()    