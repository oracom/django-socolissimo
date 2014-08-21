# -*- coding: utf-8 -*-
import requests

from django.conf import settings
from suds.client import Client
from suds import WebFault

from socolissimo.schema import ServiceCallContext, ParcelRecipient, Parcel, ParcelSender

class SoColissimoSettings:
    WSDL = "https://ws.colissimo.fr/soap.shippingclpV2/services/WSColiPosteLetterService?wsdl"
    ENDPOINT = "https://ws.colissimo.fr/soap.shippingclpV2/services/WSColiPosteLetterService"
    HEALTH_CHECK = "http://ws.colissimo.fr/supervisionWSShipping/supervision.jsp"

    # Optionnal config via django settings
    CONTRACT_NUMBER = getattr(settings, 'SOCOLISSIMO_CONTRACT_NUMBER', None)
    PASSWORD = getattr(settings, 'SOCOLISSIMO_PASSWORD', None)

class SoColissimoException(Exception):
    """Exception happening in the SoColissimo scope"""
    pass

soap_client = Client(SoColissimoSettings.WSDL)

class SoColissimoClient(object):
    """Main entry point for generating SoColissimo letters via the webservice"""

    def __init__(self, contract_number=SoColissimoSettings.CONTRACT_NUMBER,
                 password=SoColissimoSettings.PASSWORD):
        """
        Prepare the client to generate some letters with a pair of credentials.
        
        If no credentials are explicitely given, will try to fallback on the credentials
        found in the django project settings.
        
        Args:
            contract_number (str or int, optional): your SoColissimo contract number
            password (str, optional): your SoColissimo password
        
        Raises:
            ValueError: The credentials are invalid
        """
        if not contract_number:
            raise ValueError('Please provide a socolissimo contract number')
        if not password:
            raise ValueError('Please provide a socolissimo password')

        try:
            self.contract_number = int(contract_number)
        except ValueError:
            raise ValueError('SoColissimo contract number must be an int')
        self.password = password

    @staticmethod
    def check_service_health():
        """
        Tell if the colissimo service is up and healthy.
        
        Returns:
            True if the service is up, False if the service is down
        """
        response = requests.get(SoColissimoSettings.HEALTH_CHECK)
        return response.status_code == 200 and response.content.strip() == "[OK]"

    def get_letter(self, service_call_context, parcel, recipient, sender):
        """
        Issue a request to the webservice to generate a SoCOlissimo label.
        
        Each argument is a dict containing the labelling data as defined by the schema.
        The minimum required data to validate are :
        
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
        
        For complete description of available fields, see the schema module.
        
        Returns:
            A tuple (parcel_number, pdf_url)
            
        Raises:
            SoColissimoException: When something goes wrong with the webservice call.
        """
        letter = soap_client.factory.create('Letter')
        letter.password = self.password
        letter.contractNumber = self.contract_number
        letter.coordinate = None

        service_schema = ServiceCallContext(service_call_context)
        letter.service = service_schema.build_instance()

        parcel_schema = Parcel(parcel)
        letter.parcel = parcel_schema.build_instance()

        recipient_schema = ParcelRecipient(recipient)
        letter.dest = recipient_schema.build_instance()

        sender_schema = ParcelSender(sender)
        letter.exp = sender_schema.build_instance()
        # print letter

        try:
            # soap_client.set_options(nosend=True)
            response = soap_client.service.getLetterColissimo(letter)
        except WebFault as e:
            raise SoColissimoException("Exception in the SOAP client : {}".format(e))

        if response.errorID != 0:
            raise SoColissimoException("Error {} : {}".format(response.errorID, response.error))

        return response.parcelNumber, response.PdfUrl
