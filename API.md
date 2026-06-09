# VVH Mock Server – API-dokumentation

Bas-URL: `https://1177-mock.jamtwest.se`

---

## Innehåll

- [SOAP-endpoints](#soap-endpoints)
  - [carelisting](#carelisting)
  - [person](#person)
- [REST – filhantering](#rest--filhantering)
- [REST – scenario](#rest--scenario)
- [REST – admin](#rest--admin)

---

## SOAP-endpoints

Alla SOAP-anrop görs med `POST` och `Content-Type: text/xml; charset=utf-8`.  
WSDL hämtas via `GET /<domän>/<operation>?wsdl`.

Gemensam request-struktur:

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header>
    <urn:LogicalAddress xmlns:urn="urn:riv:itintegration:registry:1">SE2321000156</urn:LogicalAddress>
  </soapenv:Header>
  <soapenv:Body>
    <!-- operation-specifikt innehåll -->
  </soapenv:Body>
</soapenv:Envelope>
```

---

### carelisting

#### GetListingTypes

Returnerar tillgängliga listningstyper (PRIMARY_CARE, FAST_DOCTOR_CONTACT, FAST_CARE_CONTACT).

- **WSDL:** `GET /carelisting/GetListingTypes?wsdl`
- **Endpoint:** `POST /carelisting/GetListingTypes`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2`

```xml
<req:GetListingTypesRequest xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2"/>
```

---

#### GetListing

Hämtar listningsinformation för en person.

- **WSDL:** `GET /carelisting/GetListing?wsdl`
- **Endpoint:** `POST /carelisting/GetListing`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2`

```xml
<req:GetListingRequest xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2">
  <req:actor>
    <req:actorId>
      <req:root>1.2.752.129.2.1.4.1</req:root>
      <req:extension>SE2321000156-A001</req:extension>
    </req:actorId>
    <req:actorType>healthcare_professional</req:actorType>
  </req:actor>
  <req:personId>
    <req:root>1.2.752.129.2.1.3.1</req:root>
    <req:extension>194001019999</req:extension>
  </req:personId>
</req:GetListingRequest>
```

---

#### GetListingCounty

Returnerar vilken region/landsting en person är listad i, som ett HSA-id.

- **WSDL:** `GET /carelisting/GetListingCounty?wsdl`
- **Endpoint:** `POST /carelisting/GetListingCounty`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:GetListingCountyResponder:2`

```xml
<req:GetListingCountyRequest xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingCountyResponder:2">
  <req:actor>
    <req:actorId>
      <req:root>1.2.752.129.2.1.4.1</req:root>
      <req:extension>SE2321000156-A001</req:extension>
    </req:actorId>
    <req:actorType>healthcare_professional</req:actorType>
  </req:actor>
  <req:personId>
    <req:root>1.2.752.129.2.1.3.1</req:root>
    <req:extension>194001019999</req:extension>
  </req:personId>
</req:GetListingCountyRequest>
```

**Svar (listad):**
```xml
<GetListingCountyResponse>
  <listingCounties>
    <root>1.2.752.129.2.1.4.1</root>
    <extension>SE2321000156</extension>  <!-- regionens HSA-id -->
  </listingCounties>
  <resultCode>OK</resultCode>
</GetListingCountyResponse>
```

**Svar (ej listad):** `<GetListingCountyResponse><resultCode>OK</resultCode></GetListingCountyResponse>`

Regionens HSA-id härleds från hälsocentralens HSA-id: `SE2321000156-A001` → `SE2321000156`.

---

#### GetAvailableHealthcareFacilities

Hämtar tillgängliga hälsocentraler, med valfritt filter på HSA-id eller listningstyp.

- **WSDL:** `GET /carelisting/GetAvailableHealthcareFacilities?wsdl`
- **Endpoint:** `POST /carelisting/GetAvailableHealthcareFacilities`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcareFacilitiesResponder:2`

```xml
<req:GetAvailableHealthcareFacilitiesRequest
    xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcareFacilitiesResponder:2">
  <!-- Valfritt: filtrera på specifika hälsocentraler -->
  <req:healthcareFacilities>SE2321000156-A001</req:healthcareFacilities>
  <!-- Valfritt: filtrera på listningstyp -->
  <req:listingTypes><req:code>PRIMARY_CARE</req:code></req:listingTypes>
</req:GetAvailableHealthcareFacilitiesRequest>
```

---

#### GetAvailableHealthcarePersonnel

Hämtar tillgänglig personal för en hälsocentral.

- **WSDL:** `GET /carelisting/GetAvailableHealthcarePersonnel?wsdl`
- **Endpoint:** `POST /carelisting/GetAvailableHealthcarePersonnel`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcarePersonnelResponder:2`

```xml
<req:GetAvailableHealthcarePersonnelRequest
    xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcarePersonnelResponder:2">
  <req:healthcareFacilityHSAId>SE2321000156-A001</req:healthcareFacilityHSAId>
  <!-- Valfritt: filtrera på listningstyp -->
  <req:listingTypes><req:code>FAST_DOCTOR_CONTACT</req:code></req:listingTypes>
</req:GetAvailableHealthcarePersonnelRequest>
```

---

#### CreateListing

Skapar en ny listning för en person. Sparas i minnet (nollställs vid omstart).

- **WSDL:** `GET /carelisting/CreateListing?wsdl`
- **Endpoint:** `POST /carelisting/CreateListing`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:CreateListingResponder:2`

---

#### UpdateListing

Uppdaterar en befintlig listning. Sparas i minnet (nollställs vid omstart).

- **WSDL:** `GET /carelisting/UpdateListing?wsdl`
- **Endpoint:** `POST /carelisting/UpdateListing`
- **Namespace:** `urn:riv:supportprocess:logistics:carelisting:UpdateListingResponder:2`

---

### person

#### GetPersonsForProfile

Hämtar folkbokföringsdata för en eller flera personer. Stödjer batch.

- **WSDL:** `GET /person/GetPersonsForProfile?wsdl`
- **Endpoint:** `POST /person/GetPersonsForProfile`
- **Namespace:** `urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5`

```xml
<req:GetPersonsForProfileRequest
    xmlns:req="urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5">
  <req:personId>
    <req:root>1.2.752.129.2.1.3.1</req:root>
    <req:extension>194001019999</req:extension>
  </req:personId>
  <!-- Flera personId kan anges -->
  <req:personId>
    <req:root>1.2.752.129.2.1.3.1</req:root>
    <req:extension>197505059999</req:extension>
  </req:personId>
  <req:profile>P2</req:profile>
</req:GetPersonsForProfileRequest>
```

**Profiler:**

| Profil | Innehåll |
|--------|----------|
| P1 | Identitet + namn |
| P2 | P1 + adress + folkbokföringskommun |
| P3–P5 | Som P2 (mock returnerar samma data) |

---

#### GetPersonsForProfileUnrestricted

Som GetPersonsForProfile men returnerar fullständiga uppgifter även för skyddade personer.

- **WSDL:** `GET /person/GetPersonsForProfileUnrestricted?wsdl`
- **Endpoint:** `POST /person/GetPersonsForProfileUnrestricted`

---

#### SearchPersonsForProfileByOrder

Söker personer via SimpleQL-fråga. Returnerar ett `orderId` — använd `GetFilesForOrderId` för att hämta resultatet.

- **WSDL:** `GET /person/SearchPersonsForProfileByOrder?wsdl`
- **Endpoint:** `POST /person/SearchPersonsForProfileByOrder`
- **Namespace:** `urn:riv:strategicresourcemanagement:persons:person:SearchPersonsForProfileByOrderResponder:5`

```xml
<req:SearchPersonsForProfileByOrder
    xmlns:req="urn:riv:strategicresourcemanagement:persons:person:SearchPersonsForProfileByOrderResponder:5">
  <req:query>FROM personrecord WHERE countyCode = '23';</req:query>
  <req:queryLanguage>SimpleQL</req:queryLanguage>
  <req:profile>P2</req:profile>
</req:SearchPersonsForProfileByOrder>
```

**Stödda SimpleQL-fält:**

| Fält | Beskrivning |
|------|-------------|
| `countyCode` | Länskod (t.ex. `23` för Jämtland) |
| `municipalityCode` | Kommunkod |
| `name.givenname` | Förnamn |
| `name.surname` | Efternamn |
| `protectedPersonIndicator` | `true` / `false` |

**Stödda operatorer:** `=`, `!=`, `LIKE` (med `%` som wildcard), `AND`

**Svar:**
```xml
<SearchPersonsForProfileByOrderResponse>
  <orderId>0604-TO42-12345678</orderId>
</SearchPersonsForProfileByOrderResponse>
```

---

#### GetFilesForOrderId

Hämtar nedladdningslänk för ett tidigare beställt order-id. Returnerar länken direkt (ingen poll-väntan i mock).

- **WSDL:** `GET /person/GetFilesForOrderId?wsdl`
- **Endpoint:** `POST /person/GetFilesForOrderId`
- **Namespace:** `urn:riv:strategicresourcemanagement:persons:person:GetFilesForOrderIdResponder:4`

```xml
<req:GetFilesForOrderId
    xmlns:req="urn:riv:strategicresourcemanagement:persons:person:GetFilesForOrderIdResponder:4">
  <req:orderId>0604-TO42-12345678</req:orderId>
</req:GetFilesForOrderId>
```

**Svar (klar):**
```xml
<GetFilesForOrderIdResponse>
  <multimedia>
    <mediaType>application/zip</mediaType>
    <reference>https://1177-mock.jamtwest.se/purest/order/get/{guid}</reference>
  </multimedia>
</GetFilesForOrderIdResponse>
```

**Svar (ej klar):** Tom `<GetFilesForOrderIdResponse/>` (förekommer ej i mock — alltid klar direkt).

---

## REST – filhantering

### POST /purest/getPersonsByFile

Laddar upp en CSV med personnummer och returnerar ett `orderId`. Använd `GetFilesForOrderId` + `order/get` för att hämta resultatet.

**Request:** `multipart/form-data`

| Parameter | Typ | Beskrivning |
|-----------|-----|-------------|
| `file` | fil | CSV-fil, ett personnummer per rad: `personnummer;OID` |
| `profile` | sträng | P1–P5, standard P2 |
| `fromDate` | sträng | *Ej implementerat ännu* |

**CSV-format:**
```
194001019999;1.2.752.129.2.1.3.1
197505059999;1.2.752.129.2.1.3.1
```

**Svar:** `201 Created`
```json
{ "orderId": "0604-TO42-12345678" }
```

---

### GET /purest/order/get/{guid}

Laddar ner resultatet från en beställning. ZIP-fil innehållande `result.xml` i `GetPersonsForProfileResponse`-format.

| Statuskod | Beskrivning |
|-----------|-------------|
| 200 | ZIP-fil returneras |
| 404 | Guid finns inte (eller redan nedladdad i verklig tjänst) |

---

## REST – scenario

Skyddas av Cloudflare Access.

### GET /scenario

Visar webbsida med knappar för att byta aktivt scenario.

### POST /scenario/{name}

Byter aktivt scenario. Påverkar vilka rader i databasen som används vid SOAP-anrop.

```bash
curl -X POST https://1177-mock.jamtwest.se/scenario/massavflyttning
```

**Svar:**
```json
{ "active": "massavflyttning" }
```

Tillbaka till default:
```bash
curl -X POST https://1177-mock.jamtwest.se/scenario/default
```

**Tillgängliga scenarion** bestäms av `scenario_name`-kolumnen i databasen.

---

## REST – admin

Skyddas av Cloudflare Access. Alla endpoints under `/admin/`.

Scenario-medvetna tabeller (`persons`, `patients`) tar en valfri query-parameter `?scenario=` — standard är aktivt scenario.

---

### Persons

#### GET /admin/persons

Lista alla personer i aktivt (eller angivet) scenario.

```bash
curl https://1177-mock.jamtwest.se/admin/persons?scenario=default
```

#### GET /admin/persons/{personId}

Hämta en specifik person.

#### POST /admin/persons

Skapa en ny person.

```json
{
  "personId": "199001019999",
  "scenario": "in_county",
  "givenName": "Karin",
  "surname": "Holm",
  "countyCode": "23",
  "municipalityCode": "83",
  "postalAddress1": "Långgatan 4",
  "postalCode": "83132",
  "city": "Östersund",
  "protectedPersonIndicator": false,
  "testIndicator": true
}
```

#### PUT /admin/persons/{personId}

Uppdatera en befintlig person. Samma format som POST.

#### DELETE /admin/persons/{personId}

Ta bort en person.

---

### Patients

#### GET /admin/patients

Lista alla patienter med listningstyper.

#### GET /admin/patients/{personId}

Hämta en specifik patient med listningstyper.

#### POST /admin/patients

Skapa en ny patient. `listingTypes` ingår i bodyn.

```json
{
  "personId": "199001019999",
  "scenario": "listed_with_contacts",
  "facilityHsaId": "SE2321000156-A001",
  "isInQueue": false,
  "listingTypes": [
    { "code": "PRIMARY_CARE" },
    { "code": "FAST_DOCTOR_CONTACT", "doctorHsaId": "SE2321000156-P001" }
  ]
}
```

**Listningstyp-koder:** `PRIMARY_CARE`, `FAST_DOCTOR_CONTACT`, `FAST_CARE_CONTACT`

**Patient-scenarion:** `listed_with_contacts`, `listed_no_contacts`, `in_queue`, `not_listed`, `out_of_county`

#### PUT /admin/patients/{personId}

Uppdatera patient. Om `listingTypes` anges ersätts befintliga listningstyper helt.

#### DELETE /admin/patients/{personId}

Ta bort patient och tillhörande listningstyper.

---

### Facilities

#### GET /admin/facilities

Lista alla hälsocentraler.

#### GET /admin/facilities/{hsaId}

Hämta en specifik hälsocentral.

#### POST /admin/facilities

```json
{
  "hsaId": "SE2321000156-A006",
  "name": "Krokoms hälsocentral",
  "hasQueue": true,
  "supportsHealthcarePersonnel": true,
  "supportedListingTypes": ["PRIMARY_CARE", "FAST_DOCTOR_CONTACT", "FAST_CARE_CONTACT"]
}
```

#### PUT /admin/facilities/{hsaId}

Uppdatera hälsocentral. Om `supportedListingTypes` anges ersätts befintliga listningstyper.

#### DELETE /admin/facilities/{hsaId}

Ta bort hälsocentral och tillhörande listningstyper.

---

### Personnel

#### GET /admin/personnel

Lista all personal.

#### GET /admin/personnel/{hsaId}

Hämta en specifik person.

#### POST /admin/personnel

```json
{
  "hsaId": "SE2321000156-P010",
  "name": "Eva Lindqvist",
  "title": "Allmänläkare",
  "professionCode": "DOCTOR",
  "facilityHsaId": "SE2321000156-A001"
}
```

**Yrkeskoder:** `DOCTOR`, `NURSE`, `OTHER`

#### PUT /admin/personnel/{hsaId}

Uppdatera personal.

#### DELETE /admin/personnel/{hsaId}

Ta bort personal.

---

### Rebuild

#### POST /admin/rebuild-db

Återskapar databasen från JSON-filerna i `config/`. Använd om du vill återställa till ursprungsdata.

```bash
curl -X POST https://1177-mock.jamtwest.se/admin/rebuild-db
```

**Svar:**
```json
{ "status": "Databas återskapad från JSON-filer" }
```

---

## OID-referens

| OID | Typ |
|-----|-----|
| `1.2.752.129.2.1.3.1` | Personnummer |
| `1.2.752.129.2.1.3.3` | Samordningsnummer |
| `1.2.752.129.2.1.4.1` | HSA-id |

## Testpersoner (default-scenario)

| PersonId | Namn | Scenario |
|----------|------|----------|
| `194001019999` | Anna Lindström | Listad med läkare + sjuksköterska, Östersund |
| `195001019999` | Helga Magnusson | Listad med läkare + sjuksköterska, Östersund |
| `195506069999` | Britta Halvarsson | Listad med kontakter, Brunflo |
| `197303039999` | Thomas Axelsson | Listad med läkare, Brunflo |
| `197505059999` | Lars Pettersson | Listad utan kontakter, avflyttad till Stockholm |
| `196601019999` | Bertil Johansson | Listad utan kontakter, avflyttad till Malmö |
| `198811119999` | Jenny Nilsson | I kö, avflyttad till Göteborg |
| `199505059999` | Erik Bergman | I kö, Östersund |
| `199201019999` | Sofia Hedlund | I kö, Torvalla |
| `196505051234` | Sekretess Markerad | Skyddad person, listad Torvalla |
| `195908089999` | Gösta Lindgren | Listad, avliden |
| `200101019999` | — | Ej listad |
| `199909099999` | Maja Söderberg | Ej listad |
