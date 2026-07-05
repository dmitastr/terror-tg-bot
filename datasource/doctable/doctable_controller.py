from typing import List

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from datasource.models import UserData, ConversationData


class YDocTableController:
    def __init__(self, endpoint: str | None, secret_key: str | None, access_key: str | None) -> None:
        if not all([endpoint, secret_key, access_key]):
            raise AssertionError("Нужно указать обе переменные окружения")

        self._client = boto3.resource('dynamodb', endpoint_url=endpoint, aws_access_key_id=access_key,
                                      aws_secret_access_key=secret_key, region_name='ru-central1')

        self.user_data_table = 'tg_persistence/user_data'
        self.conversation_data_table = 'tg_persistence/conversation_data'

    def get_user_data(self) -> List["UserData"]:
        response = self._client.Table(self.user_data_table).scan()
        items = response['Items']

        return [UserData(**item) for item in items]

    def update_user_data(self, user_data: UserData) -> None:
        self._client.Table(self.user_data_table).update_item(
            Key={
                'user_id': user_data.user_id,
            },
            UpdateExpression='SET cans=:cans, wants=:wants, comment=:comment, username=:username',
            ExpressionAttributeValues=user_data.to_flat_dict(key_prefix=":")
        )

    def delete_user_data(self, user_id: int) -> None:
        self._client.Table(self.user_data_table).delete_item(
            Key={'user_id': user_id})

    def get_conversations(self, conversation_name: str) -> List["ConversationData"]:
        try:
            response = self._client.Table(self.conversation_data_table).query(
                KeyConditionExpression=Key('conversation_name').eq(conversation_name))

        except ClientError as e:
            print(e.response['Error']['Message'])

        else:
            items = response['Items']
            print(f'Receive Item={items}')

            return [ConversationData(**item) for item in items]

    def update_conversation(self, conversation_data: ConversationData) -> None:
        data_dump = conversation_data.model_dump()
        self._client.Table(self.conversation_data_table).update_item(
            Key={
                'conversation_name': conversation_data.conversation_name,
                'key': data_dump['key']
            },
            UpdateExpression='SET state=:state',
            ExpressionAttributeValues={':state': data_dump['state']}
        )
