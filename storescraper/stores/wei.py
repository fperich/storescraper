import re
from bs4 import BeautifulSoup
from decimal import Decimal

from storescraper.product import Product
from storescraper.store import Store
from storescraper.utils import remove_words, html_to_markdown, \
    session_with_proxy


class Wei(Store):
    @classmethod
    def categories(cls):
        return [
            'Notebook',
            'VideoCard',
            'Processor',
            'Monitor',
            'Motherboard',
            'Ram',
            'StorageDrive',
            'SolidStateDrive',
            'PowerSupply',
            'ComputerCase',
            'CpuCooler',
            'Tablet',
            'ExternalStorageDrive',
            'UsbFlashDrive',
            'MemoryCard',
            'Television',
            'Lamp',
            'LightTube',
            'LightProjector',
            'Mouse',
            'Printer',
            'VideoGameConsole',
            'Keyboard',
            'KeyboardMouseCombo',
            'AllInOne',
            'Headphones',
            'Projector',
            'StereoSystem',
            'Ups',
        ]

    @classmethod
    def discover_urls_for_category(cls, category, extra_args=None):
        category_urls = [
            # ['752', 'Tablet'],  # Tablets
            ['678', 'Tablet'],  # TABLETS
            ['1267', 'Notebook'],  # Notebooks
            # ['731', 'Notebook'],  # NOTEBOOK GAMER
            # ['755', 'Notebook'],  # MACBOOK
            ['1252', 'Mouse'],  # Mouse
            ['807', 'Mouse'],  # MOUSE GAMER
            ['1138', 'ExternalStorageDrive'],  # Discos externos
            ['515', 'SolidStateDrive'],  # SSD
            ['1142', 'UsbFlashDrive'],  # Pendrive
            ['511', 'StorageDrive'],  # DISCOS DUROS INTERNOS
            ['769', 'AllInOne'],  # ALL IN ONE - AIO
            ['770', 'Headphones'],  # AUDIFONOS CON MICROFONO
            ['1176', 'Headphones'],  # AUDíFONOS
            ['805', 'Headphones'],  # AUDIFONOS GAMER
            ['1126', 'Motherboard'],  # PLACAS MADRES
            ['730', 'Motherboard'],  # PLACAS GAMER
            ['1219', 'ComputerCase'],  # GABINETES
            ['729', 'ComputerCase'],  # GABINETES GAMER
            ['1222', 'PowerSupply'],  # FUENTES DE PODER (PSU)
            ['1305', 'VideoCard'],  # TARJETAS DE VIDEO
            ['811', 'VideoCard'],  # TARJETAS GRAFICAS GAMER
            ['1117', 'Processor'],  # Procesadores
            ['1238', 'Ram'],  # MEMORIAS
            ['1240', 'Ram'],  # MEMORIA PC GAMER
            ['1162', 'CpuCooler'],  # VENTILADORES / FAN
            ['804', 'CpuCooler'],  # REFRIGERACION E ILUMINACION
            ['1267', 'Notebook'],  # NOTEBOOKS
            ['784', 'Printer'],  # IMPRESORA TINTA
            ['773', 'Printer'],  # IMPRESORAS LASER
            ['775', 'Printer'],  # IMPRESORAS MULTIFUNCIONALES
            ['1226', 'Printer'],  # IMPRESORAS TINTA
            ['1249', 'Projector'],  # PROYECTORES
            ['1245', 'Monitor'],  # MONITORES LED, LCD, TFT
            ['810', 'Monitor'],  # MONITORES GAMER
            ['1248', 'Television'],  # TELEVISORES
            ['1295', 'Cell'],  # SMARTPHONES
            ['1141', 'MemoryCard'],  # Tarjetas de memoria
            ['806', 'Keyboard'],  # TECLADOS GAMER
            # ['1254', 'Keyboard'],  # TECLADOS (PS2, USB, NUMERICOS)
            # ['1253', 'KeyboardMouseCombo'],  # COMBOS TECLADO / MOUSE
            ['808', 'KeyboardMouseCombo'],  # KIT TECLADO Y MOUSE GAMER
            ['1175', 'StereoSystem'],  # PARLANTES
            # ['793', 'StereoSystem'],  # AMPLIFICADORES
            ['1209', 'VideoGameConsole'],  # CONSOLAS JUEGOS Y CONTROLES
            ['782', 'Ups'],  # UPS
        ]

        session = session_with_proxy(extra_args)

        product_urls = []
        for category_path, local_category in category_urls:
            if local_category != category:
                continue

            page = 0

            while True:
                if page >= 10:
                    raise Exception('Page overflow: ' + category_path)

                page_url = 'https://www.wei.cl/categoria/{}?page={}' \
                           ''.format(category_path, page)
                print(page_url)

                soup = BeautifulSoup(session.get(page_url).text, 'html.parser')

                product_cells = soup.findAll('div', 'box-producto')

                if not product_cells:
                    if page == 0:
                        raise Exception('Empty category: {}'.format(
                            category_path))
                    break

                for cell in product_cells:
                    product_url = cell.find('a')['href']
                    if product_url in product_urls:
                        continue
                    product_urls.append(product_url)

                page += 1

        return product_urls

    @classmethod
    def products_for_url(cls, url, category=None, extra_args=None):
        print(url)
        session = session_with_proxy(extra_args)
        page_source = session.get(url).text
        sku = re.search(r"productoPrint\('(.+)'\);", page_source)

        if not sku:
            return []

        sku = sku.groups()[0]
        soup = BeautifulSoup(page_source, 'html.parser')
        name_container = soup.find('div', 'titulo')

        if name_container.text == 'PRODUCTO NO DISPONIBLE':
            return []

        availability_link = soup.find('a', 'fa fa-check-circle bdg')

        if availability_link:
            if availability_link['data-tooltip'] == 'Sin Stock':
                stock = 0
            else:
                stock = -1
        else:
            stock = 0

        name = name_container.contents[-1].replace('&sol;', '').strip()
        pricing_container = soup.find('div', 'producto-precio')

        if not pricing_container.find('div', 'txt18'):
            return []

        offer_price = Decimal(remove_words(pricing_container.find(
            'div', 'txt18').contents[0].split('$')[1]))

        normal_price = pricing_container.find(
            'div', 'txt14').contents[0].split('$')[1]

        normal_price = Decimal(remove_words(normal_price))

        if 'reacondicionado' in name.lower():
            condition = 'https://schema.org/RefurbishedCondition'
        else:
            condition = 'https://schema.org/NewCondition'

        description = html_to_markdown(str(soup.find(
            'div', {'id': 'tab-producto'})))

        if normal_price < offer_price:
            offer_price = normal_price

        picture_urls = []
        for picture_container in soup.findAll('div', 'slider-item'):
            picture_url = picture_container.find('img')['src'].replace(
                ' ', '%20')
            picture_urls.append(picture_url)

        p = Product(
            name,
            cls.__name__,
            category,
            url,
            url,
            sku,
            stock,
            normal_price,
            offer_price,
            'CLP',
            sku=sku,
            condition=condition,
            description=description,
            picture_urls=picture_urls
        )

        return [p]
