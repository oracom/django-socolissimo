# -*- coding: utf-8 -*-
"""Webservice schema objects."""
import datetime

from django.forms.forms import Form
from django.forms.fields import (DateTimeField, IntegerField, ChoiceField,
                                 CharField, DecimalField, Field, EmailField,
                                 BooleanField)
from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES


class SchemaValidationError(ValidationError):
    """An error while validating SoColissimo schema."""

    def __init__(self, schema_name, message, *args, **kwargs):
        self.schema_name = schema_name
        self.message = message
        super(SchemaValidationError, self).__init__(message, *args, **kwargs)

    def __str__(self):
        msg = 'Schema {} did not validate : {}'
        return msg.format(self.schema_name,
                          super(SchemaValidationError, self).__str__())


class SoColissimoSchema(Form):
    """
    Specify and validate the format expected by an complexType in the WSDL.

    Attributes:
        soap_type_name: The name of the complexType that this schema reflects,
            as defined in the WSDL.
    """

    soap_type_name = None

    def build_instance(self):
        """
        Build a suds object instance for the soap type represented by this
        schema, using the form's data.

        The cleaned_data values will be translated onto the suds object.
        Empty values (Such as None, "", []) will be omitted, and won't be set as
        "nil" on the instance.

        Returns:
            A valid suds object for this schema.

        Raises :
            SchemaValidationError: The schema do not validate.
        """
        if not self.is_valid():
            raise SchemaValidationError(self.__class__.__name__,
                                        repr(self.errors))

        from socolissimo.client import SOAP_CLIENT
        instance = SOAP_CLIENT.soap_client.factory.create(self.soap_type_name)

        for field, value in self.cleaned_data.items():
            if value not in EMPTY_VALUES:
                setattr(instance, field, value)

        self._set_constants(instance)
        return instance

    def _set_constants(self, instance):
        """
        Allow subclasses to set constant values on the suds instance.

        Such constants are enforced by the SoColissimo specification.

        Args:
            instance (suds object): Subclasses must set the constants directly
                on this suds instance.
        """
        pass


class NestedSchemaField(Field):
    """
    Embed a schema inside a parent schema. Allows to represent nested
    complexType.

    Args:
        form_class (schema class): The child schema to nest.
    """

    def __init__(self, form_class, *args, **kwargs):
        self.form_class = form_class
        super(NestedSchemaField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Expect an empty value, or a dict. The dict is used as source data for
        the nested schema.

        Returns:
            A suds object representing the child schema, or None.

        Raises :
            SchemaValidationError: The child schema do not validate.
        """
        if not value:
            return value
        form = self.form_class(value)
        return form.build_instance()


class ServiceCallContext(SoColissimoSchema):
    """Service call context schema."""
    soap_type_name = "ServiceCallContextV2"

    dateDeposite = DateTimeField(required=True)
    commercialName = CharField(required=True)

    VATCode = ChoiceField(required=False,
                          choices=[ (vat, vat) for vat in range(3) ])
    VATPercentage = IntegerField(required=False, min_value=0, max_value=9999)
    VATAmount = IntegerField(required=False, min_value=0)
    transportationAmount = IntegerField(required=False, min_value=0)
    totalAmount = IntegerField(required=False, min_value=0)
    commandNumber = CharField(required=False)

    def _set_constants(self, service):
        service.dateValidation = datetime.datetime.today() \
            + datetime.timedelta(7)
        service.returnType = 'CreatePDFFile'
        service.serviceType = 'SO'
        service.crbt = False

        service.portPaye = False
        service.languageConsignor = "FR"
        service.languageConsignee = "FR"


class Parcel(SoColissimoSchema):
    """Parcel schema."""
    soap_type_name = "ParcelVO"
    DELIVERY_MODES = ('DOM', 'RDV', 'BPR', 'ACP', 'CDI', 'A2P',
                      'MRL', 'CIT', 'DOS', 'CMT', 'BDP')


    weight = DecimalField(required=True, min_value=0, max_value=30,
                          decimal_places=2)
    DeliveryMode = ChoiceField(required=False,
                               choices=[(d, d) for d in DELIVERY_MODES])
    horsGabarit = BooleanField(required=False)

    insuranceValue = IntegerField(required=False, min_value=0)
    HorsGabaritAmount = IntegerField(required=False, min_value=0)
    Instructions = CharField(required=False)

    def clean_weight(self):
        """Ensure weight does not have a decimal part equals to 00"""
        weight = self.cleaned_data.get('weight')
        if weight % 1 == 0:
            weight = int(weight)
        return weight

    def clean_DeliveryMode(self):
        """ Default to "DOM" delivery mode if not specified """
        delivery_mode = self.cleaned_data.get('delivery_mode')
        if not delivery_mode:
            delivery_mode = "DOM"
        return delivery_mode

    def _set_constants(self, parcel):
        parcel.insuranceRange = "00"
        parcel.ReturnReceipt = False
        parcel.Recommendation = False


class Address(SoColissimoSchema):
    """
    Address schema, shared by sender and recipient
    """
    soap_type_name = "AddressVO"
    COUNTRIES = [('FR', 'France'), ('MC', 'Monaco')]
    CIVILITIES = ['M', 'Mlle', 'Mme']

    Name = CharField(required=False, help_text='Nom')
    Surname = CharField(required=False, help_text='Prénom')
    email = EmailField(required=False)
    line2 = CharField(required=True, help_text='Numéro et libellé de voie')
    countryCode = ChoiceField(required=True, choices=COUNTRIES)
    city = CharField(required=True)
    postalCode = CharField(required=True)

    companyName = CharField(required=False)
    Civility = ChoiceField(required=False, choices=[(c, c) for c in CIVILITIES])
    line0 = CharField(required=False,
                      help_text='Etage, couloir, escalier, n° d’appartement')
    line1 = CharField(required=False,
                      help_text='Entrée, bâtiment, immeuble, résidence')
    line3 = CharField(required=False,
                      help_text='Lieu dit ou autre mention spéciale')
    phone = CharField(required=False)
    MobileNumber = CharField(required=False)
    DoorCode1 = CharField(required=False)
    DoorCode2 = CharField(required=False)
    Interphone = CharField(required=False)


class RecipientAddress(Address):
    """
    Recipient address schema.

    Recipient addresses has additionnal required fields : name, surname, email.
    """

    def __init__(self, *args, **kwargs):
        super(RecipientAddress, self).__init__(*args, **kwargs)
        for field_name in ('Name', 'Surname', 'email'):
            self.fields[field_name].required = True


class ParcelRecipient(SoColissimoSchema):
    """Parcel recipient schema."""
    soap_type_name = "DestEnvVO"

    addressVO = NestedSchemaField(RecipientAddress)

    def _set_constants(self, recipient):
        recipient.alert = "none"
        recipient.codeBarForreference = False
        recipient.deliveryError = False


class ParcelSender(SoColissimoSchema):
    """Parcel sender schema."""
    soap_type_name = "ExpEnvVO"

    addressVO = NestedSchemaField(Address)

    def _set_constants(self, sender):
        sender.alert = "none"
