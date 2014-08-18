# -*- coding: utf-8 -*-
import datetime

from django.forms.forms import Form
from django.forms.fields import DateTimeField, IntegerField, ChoiceField, CharField, DecimalField, Field, EmailField, \
    BooleanField
from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES

class SchemaValidationError(ValidationError):
    def __init__(self, schema_name, message, *args, **kwargs):
        self.schema_name = schema_name
        self.message = message
        super(SchemaValidationError, self).__init__(message, *args, **kwargs)

    def __str__(self):
        return "Schema {} did not validate : {}".format(self.schema_name,
                                                        super(SchemaValidationError, self).__str__())

class SoColissimoSchema(Form):
    soap_type_name = None

    def build_instance(self):
        if not self.is_valid():
            raise SchemaValidationError(self.__class__.__name__, repr(self.errors))

        from .client import soap_client
        instance = soap_client.factory.create(self.soap_type_name)

        for field, value in self.cleaned_data.items():
            if value not in EMPTY_VALUES:
                setattr(instance, field, value)

        self._set_constants(instance)
        return instance

    def _set_constants(self, instance):
        pass

class NestedFormField(Field):
    def __init__(self, form_class, *args, **kwargs):
        self.form_class = form_class
        super(NestedFormField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return value
        form = self.form_class(value)
        return form.build_instance()

class ServiceCallContext(SoColissimoSchema):
    soap_type_name = "ServiceCallContextV2"

    dateDeposite = DateTimeField(required=True)
    commercialName = CharField(required=True)
    VATCode = ChoiceField(required=False, choices=[ (vat, vat) for vat in range(3) ])
    VATPercentage = IntegerField(required=False, min_value=0, max_value=9999)
    VATAmount = IntegerField(required=False, min_value=0)
    transportationAmount = IntegerField(required=False, min_value=0)
    commandNumber = CharField(required=False)

    def _set_constants(self, service):
        service.dateValidation = datetime.datetime.today() + datetime.timedelta(7)
        service.returnType = 'CreatePDFFile'
        service.serviceType = 'SO'
        service.crbt = False

        service.portPaye = False
        service.languageConsignor = "FR"
        service.languageConsignee = "FR"

class Parcel(SoColissimoSchema):
    soap_type_name = "ParcelVO"

    weight = DecimalField(required=True, min_value=0, max_value=30, decimal_places=2)
    horsGabarit = BooleanField(required=False)

    insuranceAmount = IntegerField(required=False, min_value=0)
    HorsGabaritAmount = IntegerField(required=False, min_value=0)
    Instructions = CharField(required=False)

    def clean_weight(self):
        """Ensure weight does not have a decimal part equals to 00"""
        weight = self.cleaned_data.get('weight')
        if weight % 1 == 0:
            weight = int(weight)
        return weight

    def _set_constants(self, parcel):
        parcel.insuranceRange = "00"
        parcel.DeliveryMode = "DOM"
        parcel.ReturnReceipt = False
        parcel.Recommendation = False

class Address(SoColissimoSchema):
    soap_type_name = "AddressVO"

    companyName = CharField(required=False)
    Civility = CharField(required=False)
    Name = CharField(required=False)
    Surname = CharField(required=False)
    line0 = CharField(required=False)
    line1 = CharField(required=False)
    line2 = CharField(required=True)
    line3 = CharField(required=False)
    phone = CharField(required=False)
    MobileNumber = CharField(required=False)
    DoorCode1 = CharField(required=False)
    DoorCode2 = CharField(required=False)
    Interphone = CharField(required=False)
    country = CharField(required=False)
    countryCode = CharField(required=True)
    city = CharField(required=True)
    email = EmailField(required=False)
    postalCode = CharField(required=True)

class RecipientAddress(Address):
    """
    Recipient addresses has additionnal required fields : name, surname, email
    """

    def __init__(self, *args, **kwargs):
        super(RecipientAddress, self).__init__(*args, **kwargs)
        for field_name in ('Name', 'Surname', 'email'):
            self.fields[field_name].required = True

class ParcelRecipient(SoColissimoSchema):
    soap_type_name = "DestEnvVO"

    addressVO = NestedFormField(RecipientAddress)

    def _set_constants(self, recipient):
        recipient.alert = "none"
        recipient.codeBarForreference = False
        recipient.deliveryError = False

class ParcelSender(SoColissimoSchema):
    soap_type_name = "ExpEnvVO"

    addressVO = NestedFormField(Address)

    def _set_constants(self, sender):
        sender.alert = "none"

