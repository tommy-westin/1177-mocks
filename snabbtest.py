from zeep import Client, Settings
import requests
from lxml import etree

session = requests.Session()
session.trust_env = False
from zeep.transports import Transport
c = Client('http://localhost:8088/schemas/person/interactions/GetPersonsForProfileInteraction/GetPersonsForProfileInteraction_5.0_RIVTABP21.wsdl',
           settings=Settings(strict=False), transport=Transport(session=session))
la = etree.Element('{urn:riv:itintegration:registry:1}LogicalAddress')
la.text = 'SE2321000156'
result = c.service.GetPersonsForProfile(
    _soapheaders=[la],
    personId=[{'root': '1.2.752.129.2.1.3.1', 'extension': '197505059999'}],
    profile='P2',
    ignoreReferredIdentity=False,
)
print(result)

# Detektera utflyttad patient
county = record.personRecord.populationRegistrationLocality.countyCode
is_moved_away = county != "23"

# Detektera avregistrerad/avliden
is_deregistered = record.personRecord.deregistration is not None

# Sekretessmarkerad (inga adressuppgifter returneras)
is_protected = record.personRecord.protectedPersonIndicator
