import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def get_access_token(
        client_id,
        client_secret,
        url='https://api.moltin.com/oauth/access_token',
        grant_type='client_credentials',
):
    data = {
        'client_id': f'{client_id}',
        'client_secret': client_secret,
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


def get_product_main_image_id(
        access_token,
        product_id,
):
    url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def download_product_main_image(
        access_token,
        file_id,
        folder='media',
):
    Path(folder).mkdir(exist_ok=True)

    url = f'https://api.moltin.com/v2/files/{file_id}'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    image_data = response.json()['data']

    image_url = image_data['link']['href']

    filename = f'main_image_{image_data["file_name"]}'

    response = requests.get(image_url)
    response.raise_for_status()

    path = Path(folder, filename)

    with open(path, 'wb') as file:
        file.write(response.content)

    return path.as_posix()


def add_product_to_cart(
        access_token,
        product_id,
        quantity,
        card_id=697013533,
):
    url = f'https://api.moltin.com/v2/carts/{card_id}/items'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_cart_items(
        access_token,
        card_id=697013533,
):
    url = f'https://api.moltin.com/v2/carts/{card_id}/items'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def remove_item_from_cart(
        access_token,
        cart_id,
        cart_item_id,
):
    url = f'https://api.moltin.com/v2/carts/{cart_id}/items/{cart_item_id}'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_customer(
        access_token,
        email,
        name='Unknown',
):
    url = 'https://api.moltin.com/v2/customers'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'data': {
            'type': 'customer',
            'name': name,
            'email': email,
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    load_dotenv()
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')
    moltin_client_secret = os.getenv('MOLTIN_CLIENT_SECRET')

    token = get_access_token(moltin_client_id, moltin_client_secret)
