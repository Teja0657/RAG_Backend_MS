from dotenv import load_dotenv
from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings
)

from rag_core.config import EMBEDDING_MODEL


load_dotenv()


def get_embedding_model():

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL
    )