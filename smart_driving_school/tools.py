"""
this code will sotres tools by the agents
"""
from langchain.tools.retriever import create_retriever_tool
from azure_ai_search import (
    search_documents,
    filter_documents,
    chunk_documents,
    store_documents,
    create_embeddings,
)

retriever = vectorstore.as_retriever()




retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_blog_posts",
    "Search and return information about Lilian Weng blog posts on LLM agents, prompt engineering, and adversarial attacks on LLMs.",
)

# # === Main Workflow ===
# def main():
#     QUESTION = 'Tell me about Driver Knowledge Test (DKT)'

#     # Step 1: Search via Azure AI Search
#     search_results = search_documents(QUESTION)
#     documents = filter_documents(search_results)

#     print('Total Documents Found: {}, Top Returned: {}'.format(
#         search_results.get('@odata.count', 0), len(documents)))

#     # Step 2: Convert to LangChain Documents
#     raw_docs = []
#     for key, value in documents.items():
#         raw_docs.append(Document(
#             page_content=value['chunks'],
#             metadata={"source": value["file_name"]}
#         ))

#     # Step 3: Split documents into smaller chunks
#     docs = chunk_documents(raw_docs)

#     # Step 4: Create Embeddings and Vector Store
#     embeddings = create_embeddings()
#     vector_store = store_documents(docs, embeddings)

#     # Step 5: Answer the question
#     result = answer_with_langchain(vector_store, QUESTION)

#     print('\nQuestion:', QUESTION)
#     print('\nAnswer:', result['answer'])
#     print('\nReferences:\n', result['sources'].replace(",", "\n"))
#     print(result.keys())
#     print(result)
    
# # Run the main script
# if __name__ == "__main__":
#     main()
#     print("done")