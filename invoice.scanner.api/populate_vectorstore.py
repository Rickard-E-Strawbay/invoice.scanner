"""
Script to populate the vectorstore with company data for RAG.
This will load company information and create embeddings for retrieval.
"""

import os
import json
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import lib.constants as C


def load_all_companies(company_id: str):
    """
    Load all company JSON files from the companies folder.
    Returns a list of company dictionaries.
    """
    companies = []
    company_folder = os.path.join(C.DATA_FOLDER, company_id, C.COMPANY_DETAILS_FOLDER)
    
    if not os.path.exists(company_folder):
        print(f"[ERROR] Company folder not found: {company_folder}")
        return companies
    
    for filename in os.listdir(company_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(company_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    company_data = json.load(f)
                    companies.append(company_data)
            except Exception as e:
                print(f"[ERROR] Failed to load {filename}: {e}")
    
    print(f"[INFO] Loaded {len(companies)} companies from {company_folder}")
    return companies


def company_to_text(company: dict) -> str:
    """
    Convert company dictionary to a text representation for embedding.
    This creates a searchable text that includes all relevant information.
    """
    parts = []
    
    # Basic information
    if company.get("company_name"):
        parts.append(f"Företag: {company['company_name']}")
    
    if company.get("org_nr"):
        parts.append(f"Organisationsnummer: {company['org_nr']}")
    
    # Contact information
    contact = company.get("contact", {})
    if contact.get("email"):
        parts.append(f"E-post: {contact['email']}")
    if contact.get("phone"):
        parts.append(f"Telefon: {contact['phone']}")
    if contact.get("website") or company.get("link"):
        website = contact.get("website") or company.get("link")
        parts.append(f"Webbplats: {website}")
    
    # Address
    address = contact.get("address", {})
    if address.get("street"):
        parts.append(f"Adress: {address['street']}")
    if address.get("zip_code") and address.get("city"):
        parts.append(f"{address['zip_code']} {address['city']}")
    if address.get("country"):
        parts.append(f"Land: {address['country']}")
    
    # Business information
    if company.get("sector_tags"):
        parts.append(f"Sektor: {company['sector_tags']}")
    
    if company.get("num_employees"):
        parts.append(f"Antal anställda: {company['num_employees']}")
    
    if company.get("chairman"):
        parts.append(f"Ordförande: {company['chairman']}")
    
    # Turnover
    if company.get("turn_over"):
        for turnover in company["turn_over"]:
            year = turnover.get("year", "")
            value = turnover.get("value", 0)
            unit = turnover.get("unit", "SEK")
            parts.append(f"Omsättning {year}: {value:,} {unit}")
    
    # People related (if exists)
    if company.get("people_related"):
        parts.append("\nNyckelpersoner:")
        for person in company["people_related"]:
            name = person.get("name", "")
            role = person.get("role", "")
            title = person.get("title", "")
            email = person.get("email", "")
            phone = person.get("phone", "")
            
            person_info = f"- {name}"
            if role:
                person_info += f" ({role})"
            if title:
                person_info += f" - {title}"
            if email:
                person_info += f", E-post: {email}"
            if phone:
                person_info += f", Telefon: {phone}"
            
            parts.append(person_info)
            
            # LinkedIn profiles
            if person.get("linkedin_profiles"):
                for profile in person["linkedin_profiles"]:
                    parts.append(f"  LinkedIn: {profile.get('name')} - {profile.get('link')}")
    
    return "\n".join(parts)


def populate_vectorstore(company_id: str):
    """
    Main function to populate the vectorstore with company data.
    """
    print(f"\n{'='*60}")
    print("POPULATING VECTORSTORE WITH COMPANY DATA")
    print(f"{'='*60}\n")
    
    # Load all companies
    companies = load_all_companies(company_id)
    if not companies:
        print("[ERROR] No companies found to index")
        return False
    
    # Convert companies to Document objects
    documents = []
    for i, company in enumerate(companies):
        text = company_to_text(company)
        
        # Create metadata for filtering and tracking
        metadata = {
            "company_name": company.get("company_name", "Unknown"),
            "org_nr": company.get("org_nr", ""),
            "sector": company.get("sector_tags", ""),
            "source": "company_database",
            "company_id": company_id
        }
        
        doc = Document(page_content=text, metadata=metadata)
        documents.append(doc)
        
        if (i + 1) % 10 == 0:
            print(f"[INFO] Prepared {i + 1}/{len(companies)} documents...")
    
    print(f"\n[INFO] Total documents prepared: {len(documents)}")
    
    # Split documents if they're too long
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    print("[INFO] Splitting documents into chunks...")
    split_docs = text_splitter.split_documents(documents)
    print(f"[INFO] Created {len(split_docs)} chunks from {len(documents)} documents")
    
    # Create embeddings and store in Chroma
    print("\n[INFO] Creating embeddings and storing in vectorstore...")
    print("[INFO] This may take a while depending on the number of companies...")
    
    try:
        embeddings = OpenAIEmbeddings()
        
        # Create or update the vectorstore
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=embeddings,
            persist_directory="./vectorstore"
        )
        
        print(f"\n{'='*60}")
        print("✓ SUCCESS: Vectorstore populated successfully!")
        print(f"{'='*60}")
        print(f"Total companies indexed: {len(companies)}")
        print(f"Total chunks created: {len(split_docs)}")
        print(f"Vectorstore location: ./vectorstore")
        print(f"\nYou can now use RAG to search for company information!\n")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to populate vectorstore: {e}")
        print("Make sure you have set OPENAI_API_KEY in your environment")
        return False


def test_search(query: str):
    """
    Test the vectorstore by performing a search.
    """
    print(f"\n{'='*60}")
    print(f"TESTING SEARCH: {query}")
    print(f"{'='*60}\n")
    
    try:
        embeddings = OpenAIEmbeddings()
        vectorstore = Chroma(
            persist_directory="./vectorstore",
            embedding_function=embeddings
        )
        
        results = vectorstore.similarity_search(query, k=3)
        
        print(f"Found {len(results)} results:\n")
        for i, doc in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"Company: {doc.metadata.get('company_name', 'Unknown')}")
            print(f"Sector: {doc.metadata.get('sector', 'Unknown')}")
            print(f"\nContent preview:")
            print(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)
            print(f"\n{'-'*60}\n")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to search: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python populate_vectorstore.py <company_id> [test_query]")
        print("\nExample:")
        print("  python populate_vectorstore.py strawbay")
        print("  python populate_vectorstore.py strawbay 'CEO contact information'")
        sys.exit(1)
    
    company_id = sys.argv[1]
    
    # Populate the vectorstore
    success = populate_vectorstore(company_id)
    
    if success and len(sys.argv) > 2:
        # Run test search if query provided
        test_query = " ".join(sys.argv[2:])
        test_search(test_query)
