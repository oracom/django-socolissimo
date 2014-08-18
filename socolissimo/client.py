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
    def __init__(self, contract_number=SoColissimoSettings.CONTRACT_NUMBER,
                 password=SoColissimoSettings.PASSWORD):
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

        # print response
