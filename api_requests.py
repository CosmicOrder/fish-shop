import os
from pprint import pprint

import requests
from dotenv import load_dotenv


def get_access_token(
        client_id,
        url='https://api.moltin.com/oauth/access_token',
        grant_type='implicit',
):
    data = {
        'client_id': f'{client_id}',
        'grant_type': grant_type
    }
    response = requests.post(url, data=data)
    return response.json()['access_token']


def get_all_products(
        access_token,
        url='https://api.moltin.com/catalog/products',
):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    return response.json()


if __name__ == '__main__':
    load_dotenv()
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')

    pprint(get_all_products(get_access_token(moltin_client_id)))
