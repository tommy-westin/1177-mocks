
	@REM ---------------------------------------------------------------------------------
	@REM Generates c# WCF service contracts (interface), client proxies and wcf config
	@REM file for the WSDLs + XML Schemas of the service domain, using .Net WCF tool svcuti.exe
	@REM ---------------------------------------------------------------------------------
	@REM Licensed to the Apache Software Foundation (ASF) under one
	@REM or more contributor license agreements. See the NOTICE file
	@REM distributed with this work for additional information
	@REM regarding copyright ownership. Inera AB licenses this file
	@REM to you under the Apache License, Version 2.0 (the
	@REM "License"); you may not use this file except in compliance
	@REM with the License. You may obtain a copy of the License at
	@REM
	@REM http://www.apache.org/licenses/LICENSE-2.0
	@REM Unless required by applicable law or agreed to in writing,
	@REM software distributed under the License is distributed on an
	@REM "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
	@REM KIND, either express or implied. See the License for the
	@REM specific language governing permissions and limitations
	@REM under the License.
	@REM ---------------------------------------------------------------------------------
	CD ..\..
	
	SET SCHEMADIR=schemas
	
	SET W0=%SCHEMADIR%\interactions\GetPersonsForProfileInteraction\GetPersonsForProfileInteraction_4.0_RIVTABP21.wsdl
SET X0=%SCHEMADIR%\interactions\GetPersonsForProfileInteraction\*.xsd

SET W1=%SCHEMADIR%\interactions\GetPersonsForProfileUnrestrictedInteraction\GetPersonsForProfileUnrestrictedInteraction_4.0_RIVTABP21.wsdl
SET X1=%SCHEMADIR%\interactions\GetPersonsForProfileUnrestrictedInteraction\*.xsd

SET W2=%SCHEMADIR%\interactions\SearchPersonsForProfileByOrderInteraction\SearchPersonsForProfileByOrderInteraction_4.0_RIVTABP21.wsdl
SET X2=%SCHEMADIR%\interactions\SearchPersonsForProfileByOrderInteraction\*.xsd

SET W3=%SCHEMADIR%\interactions\SearchPersonsForProfileByOrderUnrestrictedInteraction\SearchPersonsForProfileByOrderUnrestrictedInteraction_4.0_RIVTABP21.wsdl
SET X3=%SCHEMADIR%\interactions\SearchPersonsForProfileByOrderUnrestrictedInteraction\*.xsd

SET W4=%SCHEMADIR%\interactions\SearchPersonsForProfileInteraction\SearchPersonsForProfileInteraction_4.0_RIVTABP21.wsdl
SET X4=%SCHEMADIR%\interactions\SearchPersonsForProfileInteraction\*.xsd

SET W5=%SCHEMADIR%\interactions\SearchPersonsForProfileUnrestrictedInteraction\SearchPersonsForProfileUnrestrictedInteraction_4.0_RIVTABP21.wsdl
SET X5=%SCHEMADIR%\interactions\SearchPersonsForProfileUnrestrictedInteraction\*.xsd

SET W6=%SCHEMADIR%\interactions\UpdatePersonInteraction\UpdatePersonInteraction_4.0_RIVTABP21.wsdl
SET X6=%SCHEMADIR%\interactions\UpdatePersonInteraction\*.xsd

SET XCORE=%SCHEMADIR%\core_components\*.xsd

SET SCHEMAS=%XCORE% %W0% %X0% %W1% %X1% %W2% %X2% %W3% %X3% %W4% %X4% %W5% %X5% %W6% %X6% 

SET OUTFILE=code_gen\wcf\generated-src\StrategicresourcemanagementPersonsPersonInteractions.cs
SET APPCONFIG=/config:code_gen\wcf\generated-src\app.config
SET NAMESPACE=/namespace:*,Riv.Strategicresourcemanagement.Persons.Person.Schemas.v4
SET SVCUTIL="svcutil.exe"
%SVCUTIL% /language:cs /syncOnly /out:%OUTFILE% %APPCONFIG% %NAMESPACE% %SCHEMAS%

ECHO Adding #pragma warning disable 1591 to %OUTFILE%
ECHO #pragma warning disable 1591 > %OUTFILE%.tmp
TYPE %OUTFILE% >> %OUTFILE%.tmp
MOVE /Y %OUTFILE%.tmp %OUTFILE%

CD code_gen\wcf
ECHO Generating Service contract .Net Binding interfaces and classes for strategicresourcemanagement:persons:person Release 4
ECHO I DotNetprojektet ska du ta lagga till referens till System.ServiceModel
