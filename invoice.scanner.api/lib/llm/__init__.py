from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

class RAGManager:
    def __init__(self):
        self.db = Chroma(persist_directory="./vectorstore",
                         embedding_function=OpenAIEmbeddings())

    def retrieve(self, query):
        docs = self.db.similarity_search(query, k=4)
        return "\n".join([d.page_content for d in docs])