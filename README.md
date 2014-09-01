django-socolissimo
==================

Client for the labeling webservice from SoColissimo

Installation
------------

    pip install https://github.com/oracom/django-socolissimo

Configuration
------------

You can configure your socolissimo credentials through two django settings :

    SOCOLISSIMO_CONTRACT_NUMBER = "..."
    SOCOLISSIMO_PASSWORD = "..."

Or when creating a client (which will override the global settings) :

    client = SoColissimoClient(contract_number="...", password="...") 

Usage
---------

Get a SoColissimo label with these minimal required arguments

    from socolissimo.client import SoColissimoClient
    client = SoColissimoClient() 
    parcel_number, pdf_url = client.getletter(
            service_call_context={
                'dateDeposite': ...,
                'commercialName': ...
            },
            parcel={
                'weight': ...
            },
            recipient={
                'addressVO': {
                    'Name': ...,
                    'Surname' : ...,
                    'email': ...,
                    'line2': ...,
                    'countryCode': ...,
                    'postalCode': ...,
                    'city': ...}
            },
            sender={
                'addressVO': {
                    'line2': ...,
                    'countryCode': ...,
                    'postalCode': ...,
                    'city': ...}
            })

More data can be added to the dict arguments, see schema.py

Testing
------------

Requires the [Mock library](https://pypi.python.org/pypi/mock).
