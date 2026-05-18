<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:template match="/testsuite">
		<html>
			<head>
				<style>
					ul {
						margin-top: 10px;
						margin-bottom: 10px;
					}
					h2, h3 {
						color: #196619;
					}
				</style>
			</head>
			<body>
				<h1>TK-testsvit för <xsl:value-of select="id"/></h1>
				
				<h2>Om testsviten</h2>
				<p>Detta dokument beskriver testsviten för <xsl:value-of select="id"/>. Testsviten innehåller ett antal testfall som kan användas för att verifiera implementationen innan integrationen med den nationella tjänsteplattformen.<br/>
				Testsviten använder SoapUI för att verifiera implementationen. Dokumentation om SoapUI hittas här: <a target="blank" href="https://www.soapui.org/getting-started/introduction.html">www.soapui.org</a>.<br/>
				Klicka på <a target="blank" href="https://www.soapui.org/downloads/soapui.html">den här länken</a> för att ladda hem en gratisversion av SoapUI. Installera enligt anvisning.</p>
				
				<h2>Förberedelser</h2>
				<p>
					<ul>
						<li>Gå till mappen <b>test-suite</b> i release-paketet</li>
						<li>Kopiera filen <b>‘soapui-support-N.N.NN.jar’</b> ('N.N.NN' är versionsnummer) till mappen <b>/bin/ext</b> där Soap-UI är installerat (leta efter mappen <b>/Program Files/Smartbear</b> på PC eller <b>/contents/java/app</b> på MAC OS)</li>
						<li>Öppna SoapUI och importera SoapUI-projektet (<b>test-suite/<xsl:value-of select="contractName"/>/<xsl:value-of select="contractName"/>-soapui-project.xml</b>) (välj ‘Import Project’ från menyn 'File')</li>
						<li>Om din webservice kräver ett SSL-certifikat, kan detta konfigureras via 'Preferences' (via menyn 'File').  
						I fönstret för inställningar, gå till fliken 'SSL Settings' och importera ditt certifikat under 'Keystore'</li>
						<li>Uppdatera <i>data.xml</i> så att den matchar den testdata du har i ditt system. Om du inte har testdata som passar så behöver detta läggas in i källsystemet (se nedan för instruktioner)</li>
						<li>Du borde nu kunna köra testfallen i SoapUI</li>
					</ul>
				</p>
				
				<h2>Testdata i <i>data.xml</i></h2>
				<p>
					Innan man kör testfallen i SoapUI så måste den data som skickas med i anropen anpassas utifrån det system som man vill testa. Detta görs genom att ändra i filen <i>data.xml</i> enligt nedan.<br/>
					<br/>
					Filen är i XML-format och i början finns en sektion som heter "globaldata". Här anger man den konfiguration som kommer att användas av alla testfall.<br/>
					Varje element i "globaldata" kan omdefinieras för ett specifikt testfall vid behov. Följande element är globala:
					<ul>
						<xsl:for-each select="globaldata/*">
							<li>
								<xsl:value-of select="name()"/>
							</li>
						</xsl:for-each>
					</ul>
					Globaldata innehåller ett antal konfigurationsparametrar för loggning: <br/>
                    <b>logTestData:</b> Sätts till true/false beroende på om loggning ska utföras eller ej. <b> Observera att patientdata kan lagras vid påslagen loggning.</b> <br/>
                    <b>logTestDataPath:</b> Sökvägen till den katalog där loggfilerna sparas, måste vara en katalog som användaren har rättighet att skriva i. <br/>
                    <b>logTestDataFilesAllowed:</b> Max antal filer som sparas. Det blir en fil för varje testfall som körs. När max antal filer har uppnåtts tas de äldsta bort så nya kan sparas.<br/>
				</p>
				
				<h2>Allmänna tips</h2>
				<p>
					<ul>
						<li>Kör ett testfall i taget och verifiera resultatet. Man kan också köra en hel testsvit (t.ex. "1 Basic tests") för att köra igenom alla testfall i just den sviten.<br/>
						Om du gör någon ändring som ska påverka ett specifikt testfall, kan man efter att ha verifierat just det testfallet köra genom hela sviten för att snabbt se att det "hänger ihop".</li>
						<li>Eventuella felmeddelanden skrivs ut dels till fönstret för testfallet och dels i sektionen "assertions" i anrops-fönstret.</li>
					</ul>
				</p>
				
				<h2>Beskrivning av testfallen</h2>
				<p>De parametrar man anger för ett specifikt testfall kompletterar och/eller omdefinierar de parametrar som anges i "globaldata".<br/>
				Det betyder att både parametrar från "globaldata" och det specifika testfallets sektion i filen används för det aktuella testfallet.<br/>
				OBS! Om en parameter med samma namn definieras både i "globaldata" och specifikt för testfallet, så kommer värdet från testfalls-sektionen att användas.<br/>
				Ett exempel kan vara "patientId". Denna definieras i "globaldata", eftersom det är troligt att det mesta av testdatan kommer att röra samma patient.<br/>
				Men för vissa testfall vill man kunna använda en annan patient och för dessa testfall definierar man detta genom att ta bort kommentars-markeringen runt parametern "patientId" i testfallets sektion.<br/>
				Glöm inte att spara <i>data.xml</i> efter att du har ändrat i den.</p>
				<ul style="list-style-type:none">
					<xsl:for-each select="testcase|section">
						<h3>
							<li>
								<xsl:value-of select="@id"/>
							</li>
						</h3>
						<p>
							<xsl:choose>
								<xsl:when test="starts-with(@id, '3.1 SoapFault')">Verifierar att ett Soap Fault-meddelande returneras vid tekniskt fel.
			<br/>Testet förutsätter att miljön kan modifieras så att ett tekniskt fel uppstår.</xsl:when>
								<xsl:when test="starts-with(@id, '4.1 Encoding_HeaderProlog')">Verifierar att 
          <br/>1. Content-Type header attributet charset har värdet UTF-8 eller UTF-16.
          <br/>2. XML Prolog attributet encoding har värdet UTF-8 or UTF-16.
          <br/>3. Om båda är satta ska de ha samma värde.</xsl:when>
								<xsl:when test="starts-with(@id, '4.2 Encoding_SpecialCharacters')">Testet verifierar att specialtecken så som åäö kan hanteras.
            <br/>Använd en sträng med de specialtecken som systemet ska kunna hantera.</xsl:when>
								<xsl:when test="starts-with(@id, '6.1 Loadtest')"><b>6.1.1 Grund</b><br />
								Syftet med testet är dels att verifiera att systemet kan hantera minst 10 samtidiga trådar, dels att skapa sig en bild av systemets prestanda. Testet är designat att ta max 3 minuter.<br />
								I SLA-kapitlet i självdeklarationen, under "Övrig kommentar", ange genomsnittlig responstid. Ta värdet som visas i sista raden i kolumn "avg" och dela med antal anrop (oftast 2). Ange sedan värdet med enhet millisekunder (ms).

								<br /><br /><b>6.1.2 Uthållighet</b><br />
								Syftet med testet är att undersöka prestanda hos systemet över längre tid (30 minuter). I SLA-kapitlet i självdeklarationen, under "Övrig kommentar", notera om testet gick att genomföra utan problem. Om inte, notera hur lång tid det var möjligt att köra.	</xsl:when>
								<xsl:when test="starts-with(@id, '6.2 Recovery')"><b>6.2.1 Återhämtning</b><br />
								Syftet med testet är att utsätta systemet för maximal last och att verifiera att systemet automatiskt återhämtar sig. För att kontrollera att systemet har kunnat återhämta sig efter maximal last så rekommenderas att köra testfall "1.1.1 Personnummer" för att se att systemet svarar. I SLA-kapitlet i självdeklarationen, under "Övrig kommentar", notera om systemet kunde återhämta sig efter att ha utsatts för maximal last. Ange även hur många trådar som testet avslutades med.</xsl:when>
								<xsl:otherwise>
									<xsl:copy-of select="description"/>
								</xsl:otherwise>							
							</xsl:choose>						
						</p>
						<xsl:if test="data/*">
							<b>Testfalls-specifika parametrar</b>
						</xsl:if>
						<ul>
							<xsl:for-each select="data/*">
								<li>
									<xsl:value-of select="name()"/>
								</li>
							</xsl:for-each>
						</ul>
					</xsl:for-each>
				</ul>
				<br/>
				<br/>
			</body>
		</html>
	</xsl:template>
</xsl:stylesheet> 