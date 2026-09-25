from dotenv import load_dotenv

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from langchain_anthropic import (
    ChatAnthropic
)

from langsmith import traceable

load_dotenv()


UNANSWERABLE_PHRASE = (
    "I could not find the answer "
    "in the provided document, please ask a relevant question."
)


SYSTEM_PROMPT = f"""
You are a helpful assistant answering
questions using the provided context.

Use ONLY the information present in
the provided context.

Do not use outside knowledge.

Do not make up information.

If the answer cannot be found in the
provided context, say exactly:

"{UNANSWERABLE_PHRASE}"
"""


def get_llm(model="claude"):

    model = model.lower()

    if model == "claude":

        return ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0
        )

    if model == "gemini":

        return ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite-preview",
            temperature=0
        )

    raise ValueError(
        f"Unsupported model: {model}"
    )


@traceable(name="Generation", tags=["rag","generation"],)
def generate_answer(
    question,
    documents,
    model="claude"
):

    context_parts = []

    for document in documents:

        if hasattr(
            document,
            "page_content"
        ):

            context_parts.append(
                document.page_content
            )

        elif isinstance(
            document,
            dict
        ):

            context_parts.append(
                document.get(
                    "document",
                    ""
                )
            )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
{SYSTEM_PROMPT}

Context:
{context}

Question:
{question}

Answer:
"""

    llm = get_llm(model)

    response = llm.invoke(
        prompt
    )

    return response.content

def generate_answer_stream(question, documents):
    """
    Stream the generated answer from claude.
    """
    llm=get_llm("claude")
    context="\n\n".join(
        document.page_content for document in documents
    )
    prompt=f"""
    You are a helpful assistant answering questions based only on the provided context.
    
    Context: {context}

    Question: {question}

    Instructions:
    - Answer only using the provided context.
    - Do not make up information.
    - If the answer cannot found in the context, say: {UNANSWERABLE_PHRASE}

    """
    for chunk in llm.stream(prompt):
        if chunk.content:
            yield chunk.content


