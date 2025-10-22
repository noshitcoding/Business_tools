# Invoice Tool

Dieses Projekt implementiert ein deutsches Online-Rechnungstool mit Fokus auf die gesetzlichen Anforderungen ab 2025 (E-Rechnungspflicht, GoBD, DSGVO).

## Hauptfunktionen

- Verwaltung von Organisationen, Kunden, Artikeln und Rechnungen mit GoBD-konformen Audit-Logs.
- Steuerlogik für Standard-, ermäßigte und steuerfreie Umsätze sowie Reverse-Charge-, EU- und Exportfälle.
- Generierung von PDF/A-3-, XRechnung- und ZUGFeRD-2.2-konformen Rechnungen mit identischen Werten.
- EPC-QR-Code (SEPA) Erstellung, Zahlungslinks und automatischer Zahlungsabgleich.
- Schnittstellen zu DATEV/SKR-Export, Peppol und Webhook-basierter Integration.
- Rollen- und Rechtemanagement inklusive 2FA, Audit-Trails und DSGVO-konformen Export-/Löschfunktionen.

## Entwicklung

```bash
uvicorn invoice_tool.app:app --reload
```

Tests können mit `pytest` ausgeführt werden. Weitere Details finden sich in der Entwickler-Dokumentation innerhalb der Module.

## Frontend und Backend im Docker-Setup

Für die Auslieferung stehen getrennte Container für Frontend und Backend zur Verfügung. Beide Services lassen sich gemeinsam über `docker-compose` starten.

```bash
docker compose up --build
```

- **rechnung-backend**: Startet die FastAPI-Anwendung auf Port `8000` mit gehärteter Sicherheitskonfiguration.
- **rechnung-frontend**: Liefert eine minimierte, statische Verwaltungsoberfläche über Nginx auf Port `8080`.
- **rechnung-backend**: Startet die FastAPI-Anwendung auf Port `8000`.
- **rechnung-frontend**: Liefert das statische Dashboard über Nginx auf Port `8080`.

Das Frontend leitet API-Aufrufe standardmäßig an `http://localhost:8000` weiter. Über die Umgebungsvariablen `BACKEND_URL` und `BACKEND_PORT` kann das Ziel zur Laufzeit überschrieben werden:

```bash
BACKEND_URL="https://mein-backend.example" BACKEND_PORT=443 docker compose up --build rechnung-frontend
```

Nach dem Start sind die Dienste wie folgt erreichbar:

- Frontend: <http://localhost:8080>
- Backend API: <http://localhost:8000>

Die interaktiven API-Dokumentationen (`/docs`, `/redoc`, `/openapi.json`) sind aus Sicherheitsgründen standardmäßig deaktiviert. Für lokale Entwicklungszwecke können sie explizit wieder zugänglich gemacht werden:

```bash
INVOICE_TOOL_EXPOSE_DOCS=1 docker compose up --build rechnung-backend
```

## Sicherheitsarchitektur

Das Deployment ist auf einen Betrieb in abgeschotteten Serverumgebungen ausgelegt:

- Host-Header und CORS-Ursprünge werden streng gegen Whitelists geprüft.
- Security-Header wie CSP, HSTS, Referrer-Policy und Permissions-Policy werden erzwungen.
- Docker-Images laufen ohne Root-Rechte; das Frontend nutzt eine gehärtete Nginx-Konfiguration.
- Firewall- und TLS-Hinweise sind in der Oberfläche dokumentiert, um den sicheren Betrieb zu erleichtern.

Die erlaubten Ursprünge und Hosts können per Environment-Variable gesetzt werden, beispielsweise:

```bash
INVOICE_TOOL_ALLOWED_ORIGINS="https://portal.example" \
INVOICE_TOOL_ALLOWED_HOSTS="portal.example,api.portal.example" \
docker compose up --build rechnung-backend
```

## Frontend-Oberfläche

Die ausgelieferte Oberfläche fokussiert sich auf sicherheitsrelevante Hinweise statt interaktiver Debug-Funktionen. Sie zeigt den adressierten Backend-Endpunkt an und listet aktive Schutzmaßnahmen sowie empfohlene Betriebsrichtlinien auf.

Individuelle Module (z. B. Freigabe- oder Reporting-Workflows) können hier verlinkt werden, ohne das Kern-API oder administrative Schnittstellen ungeschützt zu exponieren.
- Backend API: <http://localhost:8000/docs>

## Frontend-Funktionen

Das ausgelieferte Frontend bietet einen schnellen Einstieg in zentrale Abläufe:

- Sofortiger Gesundheitscheck gegen `/health` beim Laden der Seite.
- Formular zum Abrufen offener Posten einer Organisation über `/invoices/open`.
- Leichtgewichtige API-Konsole für ad-hoc GET-Anfragen an weitere Endpunkte.

Die Oberfläche kann als Ausgangspunkt für erweiterte Dashboards dienen und lässt sich durch zusätzliche Skripte, Stile oder Build-Prozesse ergänzen.
