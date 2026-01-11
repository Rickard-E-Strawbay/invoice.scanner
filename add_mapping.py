import json

# Mapping från PEPPOL fältnamn till invoice_data_raw vägar
mapping = {
    # Header
    "InvoiceID": "invoiceNumber",
    "IssueDate": "dates.invoiceDate",
    "DocumentCurrencyCode": "currency.invoiceCurrency",
    "TaxCurrencyCode": "currency.baseCurrency",
    "InvoiceTypeCode": "type",
    "OrderReference": "debtor.ourOrderNumber",
    "Notes": "debtor.remark",
    
    # Dates
    "DueDate": "dates.expireDate",
    "DeliveryDate": "dates.deliveryDate",
    
    # Buyer (Debtor)
    "BuyerName": "debtor.name",
    "BuyerReference": "debtor.customerNumber",
    "BuyerIdentificationNumber": "debtor.identificationNumber",
    "BuyerVATNumber": "debtor.vatNumber",
    "BuyerOrderNumber": "debtor.yourOrderNumber",
    "BuyerContactPoint": "debtor.yourContactPerson",
    "BuyerPhoneNumber": "debtor.cellPhone",
    "BuyerStreetAddress": "debtor.invoiceAddress.address",
    "BuyerCity": "debtor.invoiceAddress.city",
    "BuyerPostalZone": "debtor.invoiceAddress.zip",
    "BuyerCountryCode": "debtor.invoiceAddress.countryCode",
    
    # Seller
    "SellerName": "debtor.name",
    "SellerIdentificationNumber": "debtor.identificationNumber",
    "SellerVATNumber": "debtor.vatNumber",
    
    # Articles/Line items
    "ArticleDescription": "articleRows[].description",
    "ArticleQuantity": "articleRows[].quantity",
    "ArticleUnitPrice": "articleRows[].unitPrice",
    "ArticleNetAmount": "articleRows[].exclVAT",
    "ArticleVATAmount": "articleRows[].vat",
    "ArticleUnit": "articleRows[].unit",
    "ArticleDiscount": "articleRows[].discountPercentage",
    
    # Totals & Monetary
    "InvoiceTotalWithoutVAT": "totals.totalExclVat",
    "InvoiceTotalVAT": "totals.totalVat",
    "InvoiceTotalWithVAT": "totals.totalToPay",
    "TaxExclusiveAmount": "totals.totalExclVat",
    "TaxInclusiveAmount": "totals.totalToPay",
    "PayableAmount": "totals.totalToPay",
    "RoundingAmount": "totals.totalRoundOff",
    "AllowancesTotalAmount": "debtor.fees.administration",
    "ChargesTotalAmount": "debtor.fees.freight",
    "LineExtensionAmount": "calculated_from_articleRows",  # Calculated field, not directly mapped
    
    # Payment
    "PaymentTerms": "debtor.terms.payment",
    "DeliveryTerms": "debtor.terms.delivery",
    "PaymentReference": "paymentReference",
    "PaymentDueDate": "dates.expireDate",
    
    # VAT
    "VATTaxableAmount": "vats[].totalTaxable",
    "VATTaxAmount": "vats[].totalVat",
    "VATPercent": "vats[].percentage",
    "TaxAmount": "totals.totalVat",
}

with open('ic_shared/utils/3_0_peppol.json', 'r') as f:
    peppol = json.load(f)

sections = peppol['Properties']['PeppolInvoice']['Properties']

mapped_count = 0
unmapped_count = 0
unmapped_fields = []

for section_name, section_data in sections.items():
    if 'Properties' in section_data:
        for field_name, field_data in section_data['Properties'].items():
            map_value = None
            
            # Direct name match
            if field_name in mapping:
                map_value = mapping[field_name]
                mapped_count += 1
            else:
                # Try to match by partial name or description
                unmapped_count += 1
                unmapped_fields.append({
                    'section': section_name,
                    'field': field_name,
                    'description': field_data.get('Description', 'N/A'),
                    'BT-ID': field_data.get('BT-ID', 'N/A'),
                    'Obligation': field_data.get('Obligation', 'N/A')
                })
            
            if map_value:
                field_data['map'] = map_value

# Save updated file
with open('ic_shared/utils/3_0_peppol.json', 'w') as f:
    json.dump(peppol, f, indent=2)

print(f"✅ Mappning slutförd!")
print(f"Mappade fält: {mapped_count}")
print(f"Omappade fält: {unmapped_count}")

if unmapped_fields:
    print(f"\n⚠️  Omappade fält (osäker på mapping):\n")
    for item in unmapped_fields:
        print(f"  {item['section']} → {item['field']}")
        print(f"    Description: {item['description']}")
        print(f"    BT-ID: {item['BT-ID']}")
        print(f"    Obligation: {item['Obligation']}\n")
