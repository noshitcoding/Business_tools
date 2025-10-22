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
