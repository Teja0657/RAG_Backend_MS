from dotenv import load_dotenv
from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings
)


load_dotenv()


EMBEDDING_MODEL = "gemini-embedding-001"


def get_embedding_model():

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL
    )