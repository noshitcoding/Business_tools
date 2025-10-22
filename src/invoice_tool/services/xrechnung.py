"""Generate EN 16931 compliant XRechnung XML."""
from __future__ import annotations

from typing import Iterable

from lxml import etree

from ..models import Invoice, InvoiceLine, TaxCategory
from ..services.tax import compute_tax
from ..services.validators import ensure_reverse_charge_text

NSMAP = {
    "rsm": "urn:ferd:CrossIndustryDocument:invoice:1p0",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
}


def generate_xrechnung(invoice: Invoice) -> bytes:
    root = etree.Element("rsm:CrossIndustryInvoice", nsmap=NSMAP)
    header = etree.SubElement(root, "rsm:ExchangedDocument")
    etree.SubElement(header, "ram:ID").text = invoice.invoice_number
    etree.SubElement(header, "ram:TypeCode").text = "380"
    etree.SubElement(header, "ram:IssueDateTime").text = invoice.issue_date.isoformat()

    supply_chain = etree.SubElement(root, "rsm:SupplyChainTradeTransaction")
    _add_trade_parties(supply_chain, invoice)
    _add_invoice_lines(supply_chain, invoice.lines)
    _add_monetary_summaries(supply_chain, invoice)

    return etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)


def _add_trade_parties(parent: etree.Element, invoice: Invoice) -> None:
    agreement = etree.SubElement(parent, "ram:ApplicableHeaderTradeAgreement")
    seller = etree.SubElement(agreement, "ram:SellerTradeParty")
    etree.SubElement(seller, "ram:Name").text = invoice.issuer.name
    _add_address(seller, invoice.issuer.street, invoice.issuer.postal_code, invoice.issuer.city, invoice.issuer.country)
    if invoice.issuer.vat_id:
        etree.SubElement(seller, "ram:SpecifiedTaxRegistration", schemeID="VA").text = invoice.issuer.vat_id

    buyer = etree.SubElement(agreement, "ram:BuyerTradeParty")
    etree.SubElement(buyer, "ram:Name").text = invoice.customer.name
    _add_address(buyer, invoice.customer.street, invoice.customer.postal_code, invoice.customer.city, invoice.customer.country)
    if invoice.customer.vat_id:
        etree.SubElement(buyer, "ram:SpecifiedTaxRegistration", schemeID="VA").text = invoice.customer.vat_id

    terms = etree.SubElement(parent, "ram:ApplicableHeaderTradeSettlement")
    etree.SubElement(terms, "ram:PaymentReference").text = invoice.invoice_number
    due_el = etree.SubElement(terms, "ram:SpecifiedTradePaymentTerms")
    if invoice.due_date:
        etree.SubElement(due_el, "ram:DueDateDateTime").text = invoice.due_date.isoformat()
    note_text = ensure_reverse_charge_text(invoice)
    if note_text:
        notes = etree.SubElement(parent, "ram:IncludedNote")
        etree.SubElement(notes, "ram:Content").text = note_text


def _add_address(parent: etree.Element, street: str, postal: str, city: str, country: str) -> None:
    postal_address = etree.SubElement(parent, "ram:PostalTradeAddress")
    etree.SubElement(postal_address, "ram:PostcodeCode").text = postal
    etree.SubElement(postal_address, "ram:LineOne").text = street
    etree.SubElement(postal_address, "ram:CityName").text = city
    etree.SubElement(postal_address, "ram:CountryID").text = country


def _add_invoice_lines(parent: etree.Element, lines: Iterable[InvoiceLine]) -> None:
    for index, line in enumerate(lines, start=1):
        trade = etree.SubElement(parent, "ram:IncludedSupplyChainTradeLineItem")
        item = etree.SubElement(trade, "ram:SpecifiedTradeProduct")
        etree.SubElement(item, "ram:SellerAssignedID").text = str(line.article_id or index)
        etree.SubElement(item, "ram:Name").text = line.description
        delivery = etree.SubElement(trade, "ram:SpecifiedLineTradeDelivery")
        quantity = etree.SubElement(delivery, "ram:BilledQuantity", unitCode=line.unit)
        quantity.text = f"{line.quantity:.2f}"
        settlement = etree.SubElement(trade, "ram:SpecifiedLineTradeSettlement")
        etree.SubElement(settlement, "ram:LineTotalAmount", currencyID="EUR").text = f"{line.net_amount * line.quantity:.2f}"
        tax = etree.SubElement(settlement, "ram:ApplicableTradeTax")
        tax_type = "VAT" if line.tax_category not in {TaxCategory.REVERSE_CHARGE, TaxCategory.EXPORT, TaxCategory.EU_SUPPLY} else "AE"
        etree.SubElement(tax, "ram:TypeCode").text = tax_type
        etree.SubElement(tax, "ram:CategoryCode").text = _category_code(line.tax_category)
        etree.SubElement(tax, "ram:RateApplicablePercent").text = f"{line.tax_rate * 100:.2f}"
        price = etree.SubElement(trade, "ram:SpecifiedLineTradeAgreement")
        etree.SubElement(price, "ram:NetPriceProductTradePrice").text = f"{line.net_amount:.2f}"


def _category_code(category: TaxCategory) -> str:
    mapping = {
        TaxCategory.STANDARD: "S",
        TaxCategory.REDUCED: "AA",
        TaxCategory.ZERO: "Z",
        TaxCategory.REVERSE_CHARGE: "AE",
        TaxCategory.EU_SUPPLY: "K",
        TaxCategory.EXPORT: "G",
    }
    return mapping[category]


def _add_monetary_summaries(parent: etree.Element, invoice: Invoice) -> None:
    summary = etree.SubElement(parent, "ram:ApplicableHeaderTradeSettlement")
    for line in invoice.lines:
        tax = etree.SubElement(summary, "ram:ApplicableTradeTax")
        etree.SubElement(tax, "ram:CalculatedAmount", currencyID=invoice.currency).text = f"{line.net_amount * line.quantity * line.tax_rate:.2f}"
        etree.SubElement(tax, "ram:TypeCode").text = "VAT"
        etree.SubElement(tax, "ram:CategoryCode").text = _category_code(line.tax_category)
        etree.SubElement(tax, "ram:RateApplicablePercent").text = f"{line.tax_rate * 100:.2f}"

    total_net, total_tax, _ = compute_tax(invoice.lines)
    etree.SubElement(summary, "ram:LineTotalAmount", currencyID=invoice.currency).text = f"{total_net:.2f}"
    etree.SubElement(summary, "ram:TaxBasisTotalAmount", currencyID=invoice.currency).text = f"{total_net:.2f}"
    etree.SubElement(summary, "ram:TaxTotalAmount", currencyID=invoice.currency).text = f"{total_tax:.2f}"
    etree.SubElement(summary, "ram:GrandTotalAmount", currencyID=invoice.currency).text = f"{total_net + total_tax:.2f}"
    etree.SubElement(summary, "ram:DuePayableAmount", currencyID=invoice.currency).text = f"{total_net + total_tax:.2f}"
