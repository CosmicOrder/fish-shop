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
    response.raise_for_status()
    return response.json()['access_token']


def get_all_products(
        access_token,
        url='https://api.moltin.com/catalog/products',
):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(
        access_token,
        product_id,
):
    url = f'https://api.moltin.com/catalog/products/{product_id}'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    load_dotenv()
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')

    token = get_access_token(moltin_client_id)

    get_all_products(token)
    pprint(get_product(token, '66f1bca0-a9a8-445d-b0c1-1f1ba4f65492'))
