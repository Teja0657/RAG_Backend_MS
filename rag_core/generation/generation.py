from dotenv import load_dotenv

from langchain.chat_models import init_chat_model

from langsmith import traceable

from rag_core.config import GENERATION_MODEL

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


def get_llm(model=GENERATION_MODEL, temperature=0):

    return init_chat_model(
        model,
        temperature=temperature
    )


def extract_text(content):
    """
    Normalize a chat model's `.content` into plain text.

    Some providers (Gemini) always return a list of content
    blocks (e.g. [{"type": "text", "text": "...", "extras": {...}}]),
    while others (Claude) return a plain string. Only "text"
    blocks are kept; non-text blocks (e.g. signature extras)
    are skipped.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text_parts = []

        for block in content:

            if isinstance(block, dict):

                if block.get("type", "text") == "text":
                    text_parts.append(
                        block.get("text", "")
                    )

            elif hasattr(block, "text"):

                text_parts.append(
                    block.text
                )

        return "".join(text_parts)

    return str(content)


@traceable(name="Generation", tags=["rag","generation"],)
def generate_answer(
    question,
    documents
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

    llm = get_llm()

    response = llm.invoke(
        prompt
    )

    return extract_text(response.content)

@traceable(
    name="Generation Stream",
    tags=["rag", "generation", "streaming"],
    reduce_fn=lambda chunks: {"answer": "".join(chunks)},
)
def generate_answer_stream(question, documents):
    """
    Stream the generated answer.
    """
    llm=get_llm()
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
        text = extract_text(chunk.content)
        if text:
            yield text


