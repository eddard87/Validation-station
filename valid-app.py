import streamlit as st
from PIL import Image
import os

# Define fake data for demonstration
fake_data = {
    "Filename": "example.pdf",
    "DomandaGeneraleSuFile": "General Question about File",
    "Language": "English",
    "SecurityType": "Stock",
    "SecurityTypeExtracted": "Stock Extracted",
    "SecurityTypeComment": "No comments",
    "SecurityTypeTextUsed": "Security Text",
    "ISIN": "US1234567890",
    "ISINExtracted": "US1234567890 Extracted",
    "ISINComment": "ISIN Comment",
    "ISINTextUsed": "ISIN Text Used",
    "SecurityID": "SEC123456",
    "SecurityIDExtracted": "SEC123456 Extracted",
    "SecurityIDComment": "Security ID Comment",
    "SecurityIDUsed": "Security ID Used",
    "Name": "Example Name",
    "Issuer": "Example Issuer",
    "IssuerExtracted": "Example Issuer Extracted",
    "IssuerComment": "Issuer Comment",
    "CompanyType": "Private",
    "CompanyTypeExtracted": "Private Extracted",
    "CompanyTypeComment": "Company Type Comment",
    "CountryIssuer": "USA",
    "CountryFreeCode": "US",
    "CountryFreeCodeComment": "Country Code Comment",
    "CountryFreeCodeTextUsed": "Country Code Text Used",
    "Exchange": "NASDAQ",
    "ExchangeExtracted": "NASDAQ Extracted",
    "ExchangeComment": "Exchange Comment",
    "ExchangeTextUsed": "Exchange Text Used",
    "BankHoliday": "No",
    "IssueCurrency": "USD",
    "QuotationCurrency": "USD",
    "QuotationCurrencyExtracted": "USD Extracted",
    "QuotationCurrencyComment": "Quotation Currency Comment",
    "QuotationCurrencyTextUsed": "Quotation Currency Text Used",
    "IssuedShares": "1000000",
    "IssuedSharesExtracted": "1000000 Extracted",
    "IssuedSharesComment": "Issued Shares Comment",
    "IssuedSharesTextUsed": "Issued Shares Text Used",
    "NomPerShare": "10",
    "NomPerShareExtracted": "10 Extracted",
    "NomPerShareComment": "Nom Per Share Comment",
    "CoreCapitel": "10000000",
    "CoreCapitelExtracted": "10000000 Extracted",
    "CoreCapitelComment": "Core Capitel Comment",
    "FilePath": "example.png"
}

# Streamlit app layout
st.title("Validation Station")

uploaded_file = st.file_uploader("Upload Document", type=["png", "jpg", "jpeg", "pdf"])
if uploaded_file is not None:
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.image(Image.open(file_path), caption='Uploaded Document')

# Display editable fields
st.subheader("Editable Fields")
for field, value in fake_data.items():
    if field != "FilePath":
        input_value = st.text_input(field, value)
        st.text(f"Extracted: {value}")
