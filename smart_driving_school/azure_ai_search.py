import os
import azure.identity
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from azure.search.documents import SearchClient
from langchain_openai import AzureOpenAIEmbeddings
from azure.core.credentials import AzureKeyCredential
from collections import OrderedDict
import requests
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.azuresearch import AzureSearch

# Load environment variables
load_dotenv(override=True)

# Azure Search + OpenAI Config
SEARCH_SERVICE_NAME = os.getenv("SEARCH_SERVICE_NAME")
SEARCH_SERVICE_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
SEARCH_SERVICE_INDEX_NAME = os.getenv("SEARCH_SERVICE_INDEX_NAME")
SEARCH_SERVICE_KEY = os.getenv("SEARCH_SERVICE_KEY")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SEARCH_SERVICE_API_VERSION = '2023-10-01-Preview'

# Azure credentials
credential = AzureKeyCredential(SEARCH_SERVICE_KEY)
azure_credential = azure.identity.AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID)
token_provider = azure.identity.get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")

# Azure AI Search headers
HEADERS = {
    'Content-Type': 'application/json',
    'api-key': SEARCH_SERVICE_KEY
}

# === Embedding and LLM ===
def create_embeddings():
    return AzureOpenAIEmbeddings(
        openai_api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_type='azure',
        azure_deployment='text-embedding-ada-002',
        model="text-embedding-ada-002",
        chunk_size=1
    )

def get_embedding(text):
    embeddings = create_embeddings()
    return embeddings.embed_query(text)

def create_llm():
    return ChatOpenAI(
        model="gpt-4o",
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN
    )

# === Azure AI Search ===
def search_documents(question):
    url = f"{SEARCH_SERVICE_ENDPOINT.rstrip('/')}/indexes/{SEARCH_SERVICE_INDEX_NAME}/docs"
    params = {
        'api-version': SEARCH_SERVICE_API_VERSION,
        'search': question,
        'select': '*',
        '$top': 5,
        '$count': 'true'
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    return resp.json()

def filter_documents(search_results):
    """Filter documents by relevance score."""
    documents = OrderedDict()
    for result in search_results['value']:
        if result['@search.score'] > 1:  # Adjusted threshold (was 10, overly strict)
            documents[result['metadata_storage_path']] = {
                'chunks': result['pages'],
                'score': result['@search.score'],
                'file_name': result['metadata_storage_name']
            }
    return documents

# === Text Splitting ===
def chunk_documents(raw_docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "],
        length_function=len
    )
    return splitter.split_documents(raw_docs)

# === Vector Store ===
def store_documents(docs, embeddings):
    return FAISS.from_documents(docs, embeddings)

# # === LangChain QA ===
def answer_with_langchain(vector_store, question):
    llm = create_llm()
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    chain = RetrievalQAWithSourcesChain.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=retriever,
        return_source_documents=True
    )
    return chain.invoke({'question': question})

# === Main Workflow ===
def main():
    QUESTION = 'Tell me about Driver Knowledge Test (DKT)'

    # Step 1: Search via Azure AI Search
    search_results = search_documents(QUESTION)
    documents = filter_documents(search_results)

    print('Total Documents Found: {}, Top Returned: {}'.format(
        search_results.get('@odata.count', 0), len(documents)))

    # Step 2: Convert to LangChain Documents
    raw_docs = []
    for key, value in documents.items():
        raw_docs.append(Document(page_content=value['chunks'],metadata={"source": value["file_name"]}))

    # Step 3: Split documents into smaller chunks
    docs = chunk_documents(raw_docs)

    # Step 4: Create Embeddings and Vector Store
    embeddings = create_embeddings()
    # vector_store = store_documents(docs, embeddings)

    # Specify additional properties for the Azure client such as the following 
    # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md#configurations
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=SEARCH_SERVICE_ENDPOINT,
        azure_search_key=SEARCH_SERVICE_KEY,
        index_name=SEARCH_SERVICE_INDEX_NAME,
        embedding_function=embeddings.embed_query,
        # Configure max retries for the Azure client
        additional_search_client_options={"retry_total": 4},
    )
    
    print(docs[0].page_content)
    # # Step 5: Answer the question
    # result = answer_with_langchain(vector_store, QUESTION)

    # print('\nQuestion:', QUESTION)
    # print('\nAnswer:', result['answer'])
    # print('\nReferences:\n', result['sources'].replace(",", "\n"))
    # print(result.keys())
    # print(result)
    
# Run the main script
if __name__ == "__main__":
    main()
    print("done")