# -*- coding: utf-8 -*-
"""Module tests."""
import datetime
from mock import patch
from django.test import SimpleTestCase
from socolissimo import client as client_module
from socolissimo.client import SoColissimoClient
import copy
from socolissimo.schema import SchemaValidationError


CONTRACT_NUMBER = '123'
PASSWORD = 'password'

LETTER_REQUIRED_KWARGS = dict(
    service_call_context={
        'dateDeposite': datetime.datetime.now(),
        'commercialName': 'Chuck Norris'
    },
    parcel={
        'weight': '10.20'
    },
    recipient={
        'addressVO': {
            'Name': 'Norris',
            'Surname' : 'Chuck',
            'email': 'chuck.norris@awesome.com',
            'line2': '1 round-kick street',
            'countryCode': 'FR',
            'postalCode': '01000',
            'city': 'Bourg-en-Bresse'}
    },
    sender={
        'addressVO': {
            'line2': '1 round-kick street',
            'countryCode': 'FR',
            'postalCode': '01000',
            'city': 'Bourg-en-Bresse'}
    })


class TestClient(SimpleTestCase):
    def get_client(self):
        return SoColissimoClient(contract_number=CONTRACT_NUMBER,
                                 password=PASSWORD)

    def test_init(self):
        with self.settings(SOCOLISSIMO_CONTRACT_NUMBER=None,
                           SOCOLISSIMO_PASSWORD=None):
            # No password
            self.assertRaises(ValueError, SoColissimoClient,
                              contract_number=CONTRACT_NUMBER,
                              password=None)
            # No contract number
            self.assertRaises(ValueError, SoColissimoClient, contract_number=None,
                              password=PASSWORD)
            # contract number is not an int
            self.assertRaises(ValueError, SoColissimoClient,
                              contract_number='contract_number', password=PASSWORD)

            client = SoColissimoClient(contract_number=CONTRACT_NUMBER,
                                       password=PASSWORD)
            self.assertEqual(client.contract_number, int(CONTRACT_NUMBER))
            self.assertEqual(client.password, PASSWORD)

    def test_init_from_settings(self):
        with self.settings(SOCOLISSIMO_CONTRACT_NUMBER=CONTRACT_NUMBER,
                           SOCOLISSIMO_PASSWORD=PASSWORD):
            reload(client_module)
            client = client_module.SoColissimoClient()
            self.assertEqual(client.contract_number, int(CONTRACT_NUMBER))
            self.assertEqual(client.password, PASSWORD)

    def test_check_service_health(self):
        with patch('socolissimo.client.requests') as mock_requests:
            mock_requests.get.return_value.status_code = 200
            mock_requests.get.return_value.content = '  [OK]  '
            self.assertTrue(SoColissimoClient.check_service_health())

            mock_requests.get.return_value.content = '[KO]'
            self.assertFalse(SoColissimoClient.check_service_health())

    def test_get_letter_ok(self):
        client = self.get_client()
        to_patch = 'socolissimo.client.SOAP_CLIENT.soap_client.service.getLetterColissimo'
        with patch(to_patch) as soap_call_mock:
            soap_call_mock.return_value.errorID = 0
            client.get_letter(**LETTER_REQUIRED_KWARGS)

            letter = soap_call_mock.call_args[0][0]
            self.assertEquals(letter.service.returnType, 'CreatePDFFile')
            self.assertEquals(letter.service.serviceType, 'SO')
            self.assertEquals(letter.service.crbt, False)
            self.assertEquals(letter.service.portPaye, False)
            self.assertEquals(letter.service.languageConsignor, 'FR')
            self.assertEquals(letter.service.languageConsignee, 'FR')

            self.assertEquals(letter.parcel.insuranceRange, '00')
            self.assertEquals(letter.parcel.DeliveryMode, 'DOM')
            self.assertEquals(letter.parcel.ReturnReceipt, False)
            self.assertEquals(letter.parcel.Recommendation, False)

            self.assertEquals(letter.dest.alert, 'none')
            self.assertEquals(letter.dest.codeBarForreference, False)
            self.assertEquals(letter.dest.deliveryError, False)

            self.assertEquals(letter.exp.alert, 'none')

    def test_get_letter_missing_required_param(self):
        def remove_one_param_iter(original_dict):
            for key, value in original_dict.items():
                dict_copy = copy.deepcopy(original_dict)

                if isinstance(value, basestring):
                    del dict_copy[key]
                    yield dict_copy

                elif isinstance(value, dict):
                    for subdict in remove_one_param_iter(value):
                        dict_copy[key] = subdict
                        yield dict_copy

        client = self.get_client()
        to_patch = 'socolissimo.client.SOAP_CLIENT.soap_client.service.getLetterColissimo'
        with patch(to_patch):
            for invalid_dict in remove_one_param_iter(LETTER_REQUIRED_KWARGS):
                self.assertRaises(SchemaValidationError, client.get_letter,
                                  **invalid_dict)

    def test_get_letter_invalid_param(self):
        client = self.get_client()

        def modified_dict(original_dict, deep_key, value):
            dict_copy = target_dict = copy.deepcopy(original_dict)
            key_list = deep_key.split('.')
            for key in key_list[:-1]:
                target_dict = target_dict[key]
            target_dict[key_list[-1]] = value
            return dict_copy

        def assert_invalid_param(deep_key, value):
            invalid_dict = modified_dict(LETTER_REQUIRED_KWARGS, deep_key, value)
            self.assertRaises(SchemaValidationError, client.get_letter, **invalid_dict)

        # Not a valid choice
        assert_invalid_param('service_call_context.VATCode', 4)
        # Not a valid percentage format
        assert_invalid_param('service_call_context.VATPercentage', 20.00)
        assert_invalid_param('service_call_context.VATPercentage', -1)
        assert_invalid_param('service_call_context.VATPercentage', 10000)
        # Not a valid VAT amount
        assert_invalid_param('service_call_context.VATAmount', -1)
        # Not a valid transportation amount
        assert_invalid_param('service_call_context.transportationAmount', -1)

        # Not a valid weight
        assert_invalid_param('parcel.weight', '-1')
        assert_invalid_param('parcel.weight', '31')
        assert_invalid_param('parcel.weight', '10.005')
        # Not a valid assurance value
        assert_invalid_param('parcel.insuranceValue', -1)
        # Not a valid transportation amount
        assert_invalid_param('parcel.HorsGabaritAmount', -1)
