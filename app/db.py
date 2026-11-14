import boto3
import os
import time
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-south-1'))
chat_table = dynamodb.Table('SportsSyncChats')
user_table = dynamodb.Table('SportsSyncUsers')

def get_user(username: str):
    try:
        response = user_table.get_item(Key={'username': username}, ConsistentRead=True)
        return response.get('Item')
    except Exception as e:
        print(f"DynamoDB Get User Error: {e}")
        return None

def create_user(username: str, hashed_password: str):
    try:
        user_table.put_item(
            Item={
                'username': username,
                'password': hashed_password,
                'created_at': str(time.time())
            },
            ConditionExpression='attribute_not_exists(username)'
        )
        return True
    except Exception as e:
        print(f"DynamoDB Create User Error: {e}")
        return False

def save_message(user_id: str, session_id: str, text: str, is_user: bool):
    chat_id = f"{user_id}#{session_id}"
    msg_timestamp = str(time.time())
    
    try:
        chat_table.put_item(
            Item={
                'chat_id': chat_id,       # Partition Key
                'timestamp': msg_timestamp,   # Sort Key
                'text': text,
                'is_user': is_user
            }
        )
    except Exception as e:
        print(f"DynamoDB Save Error: {e}")

def get_chat_history(user_id: str, session_id: str):
    chat_id = f"{user_id}#{session_id}"
    
    try:
        # Querying by Partition Key returns all items automatically sorted by the Sort Key (timestamp)
        response = chat_table.query(
            KeyConditionExpression=Key('chat_id').eq(chat_id)
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB Read Error: {e}")
        return []

def clear_user_chats(username: str):
    """Wipes the chat history for all sports when a user starts a new login session."""
    sessions = ["f1_live", "football_pl_1", "cricket"]
    try:
        with chat_table.batch_writer() as batch:
            for session_id in sessions:
                chat_id = f"{username}#{session_id}"
                # Find all messages for this sport
                response = chat_table.query(KeyConditionExpression=Key('chat_id').eq(chat_id))
                
                # Delete them rapidly in the batch
                for item in response.get('Items', []):
                    batch.delete_item(Key={
                        'chat_id': item['chat_id'], 
                        'timestamp': item['timestamp']
                    })
    except Exception as e:
        print(f"DynamoDB Clear History Error: {e}")