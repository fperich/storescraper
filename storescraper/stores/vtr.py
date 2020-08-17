import re
import json
from bs4 import BeautifulSoup
from decimal import Decimal

from storescraper.product import Product
from storescraper.store import Store
from storescraper.utils import session_with_proxy, remove_words, \
    html_to_markdown


class Vtr(Store):
    prepago_url = 'https://vtr.com/productos/moviles/prepago'
    planes_url = 'https://www.vtr.com/moviles/MovilesPlanes-planes-multimedia/'

    @classmethod
    def categories(cls):
        return [
            'CellPlan',
            'Cell'
        ]

    @classmethod
    def discover_urls_for_category(cls, category, extra_args=None):
        product_urls = []

        if category == 'CellPlan':
            product_urls.extend([
                cls.prepago_url,
                cls.planes_url
            ])
        elif category == 'Cell':
            session = session_with_proxy(extra_args)

            data = json.loads(session.get(
                'https://www.vtr.com/ccstoreui/v1/search?'
                'Ntk=product.category&Ntt=Equipments&No=0&'
                'Nrpp=100&Ns=Device.x_OrderForCollectionPage%7C0').text)

            if not data:
                raise Exception('Empty cell category')

            for record in data['resultsList']['records']:
                product_id = record['attributes']['product.repositoryId'][0]
                product_url = 'https://www.vtr.com/product/{}'.format(product_id)
                product_urls.append(product_url)

        return product_urls

    @classmethod
    def products_for_url(cls, url, category=None, extra_args=None):
        products = []
        if url == cls.prepago_url:
            # Plan Prepago
            p = Product(
                'VTR Prepago',
                cls.__name__,
                category,
                url,
                url,
                'VTR Prepago',
                -1,
                Decimal(0),
                Decimal(0),
                'CLP',
            )
            products.append(p)
        elif url == cls.planes_url:
            # Plan Postpago
            products.extend(cls._plans(url, extra_args))
        elif 'product' in url:
            # Equipo postpago
            products.extend(cls._celular_postpago(url, extra_args))
        else:
            raise Exception('Invalid URL: ' + url)
        return products

    @classmethod
    def _plans(cls, url, extra_args):
        session = session_with_proxy(extra_args)
        data = json.loads(session.get(
            'https://www.vtr.com/ccstoreui/v1/products?categoryId='
            'MovilesPlanes&fields=items.displayName%2Citems.listPrice').text)
        products = []

        portability_suffixes = [
            ('', Decimal('0.9')),
            (' Portabilidad', Decimal('0.7'))
        ]

        for item in data['items']:
            base_plan_name = item['displayName']
            base_price = Decimal(item['listPrice'])

            for portability_suffix, price_multiplier in portability_suffixes:
                price = (base_price * price_multiplier).quantize(0)
                plan_name = '{}{}'.format(base_plan_name, portability_suffix)

                p = Product(
                    plan_name,
                    cls.__name__,
                    'CellPlan',
                    url,
                    url,
                    plan_name,
                    -1,
                    price,
                    price,
                    'CLP',
                )

                products.append(p)

        return products

    @classmethod
    def _celular_postpago(cls, url, extra_args):
        print(url)
        session = session_with_proxy(extra_args)

        product_id = url.split('/')[-1]

        base_price_url = 'https://www.vtr.com/ccstoreui/v1/prices/{}'.format(
            product_id)
        price_data = json.loads(session.get(base_price_url).text)
        normal_price = Decimal(price_data['priceMin'])

        data_url = 'https://www.vtr.com/ccstoreui/v1/pages/product/{}'.format(
            product_id)
        response = session.get(data_url)
        product_data = json.loads(response.text)['data']['page']['product']

        base_name = product_data['displayName']

        variants = product_data['childSKUs']
        plans = product_data['relatedProducts']

        products = []

        for variant in variants:
            name = '{} - {}'.format(base_name, variant['x_device_color'])
            cell_url = '{}?selection={}'.format(url, variant['x_colorClass'])

            for plan in plans:
                print(json.dumps(plan, indent=2))
                cell_plan_name = plan['displayName']
                price = Decimal(plan['listPrice'])

                # Portabilidad
                p = Product(
                    name,
                    cls.__name__,
                    'Cell',
                    cell_url,
                    url,
                    '{} {} {} Portabilidad'.format(product_id, variant['x_device_color'], cell_plan_name),
                    -1,
                    portability_price,
                    portability_price,
                    'CLP',
                    sku=product_id,
                    cell_plan_name=cell_plan_name,
                    cell_monthly_payment=Decimal(0)
                )
                products.append(p)

        return products
