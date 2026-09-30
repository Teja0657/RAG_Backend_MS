"""
Seeds the "Hybrid-RAG-Evaluation" LangSmith dataset with a harder 50-question
benchmark, replacing whatever examples currently exist.

The original 50-question set was mostly single-fact lookups from small
documents, which is why every metric clustered near 97-100% — it wasn't
stress-testing the system. This set is deliberately adversarial:

- numeric near-miss distractors (many different "30 day" deadlines in the
  HDFC Life policy for unrelated obligations)
- definitions that sound alike (Sum Assured vs. Free Cover Limit, Risk
  Commencement Date vs. Policy Commencement Date)
- conditional/exception logic (suicide clause pays differently depending on
  group type; several exclusions have "unless"/"except" carve-outs)
- negative facts the doc explicitly states are NOT available (no surrender
  value, no bonus, no assignment) — tests hallucination resistance
- genuine out-of-context questions for abstention scoring

Usage:
    python evaluation/seed_dataset.py
"""

from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

DATASET_NAME = "Hybrid-RAG-Evaluation"

EXAMPLES = [
    # ======================================================
    # HDFC LIFE GROUP TERM LIFE POLICY (25)
    # ======================================================
    {
        "question": "Within how many days of an accident must death occur for it to qualify as an Accidental Death under this policy?",
        "expected_answer": "Death must occur within 90 days of the date of the accident.",
        "question_type": "numeric",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the maximum Accidental Death Benefit payable by the Company, and does this limit apply per policy or across all policies?",
        "expected_answer": "Rs. 10,000,000 (Rs. 1 crore) — and this limit applies in aggregate across all policies issued by the Company to that Insured Member, not per individual policy.",
        "question_type": "cross_reference",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the grace period for paying premiums under the Monthly payment mode, and how does it compare to the Quarterly/Half-Yearly modes and the Annual mode?",
        "expected_answer": "15 days for Monthly mode, 30 days for Quarterly and Half-Yearly modes, and there is no grace period at all for the Annual mode.",
        "question_type": "numeric_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Within how many days must an Application for Cover be submitted after an Eligible Member satisfies the eligibility criteria?",
        "expected_answer": "Within 30 days from the date the Eligible Member satisfies the Eligibility Criteria.",
        "question_type": "numeric",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Within how many days must the Policyholder notify the Company of a change in an Insured Member's details?",
        "expected_answer": "Within 30 days of being informed of the change, or of becoming aware of it, whichever is earlier.",
        "question_type": "numeric_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "How soon must the Company receive written notice of an Insured Member's death, and how does that differ from the deadline for submitting supporting claim documents?",
        "expected_answer": "Written notice of death must be given within 30 days of the death; supporting documents must then be submitted within 180 days from the date of death (or from the date of intimation of death).",
        "question_type": "cross_reference",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "How much notice must the Company give the Policyholder before discontinuing or varying the Policy at an Annual Renewal Date?",
        "expected_answer": "30 days' prior written notice.",
        "question_type": "numeric",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the maximum charge the Company can collect for issuing a duplicate Certificate of Insurance?",
        "expected_answer": "Up to a maximum of Rs. 250.",
        "question_type": "numeric_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the regulatory Turn Around Time (TAT) for the Company to respond to a grievance, and how does that compare to the time given to escalate to the Grievance Redressal Officer if unsatisfied?",
        "expected_answer": "The prescribed TAT is 15 days. If dissatisfied, the complainant can escalate to the Grievance Redressal Officer; if there's no response within 8 weeks (or they remain dissatisfied), they may approach IRDAI within 15 days of that.",
        "question_type": "numeric_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "After how many years can a life insurance policy no longer be contested on the ground of fraud or misstatement?",
        "expected_answer": "3 years — no policy of life insurance can be called into question on any ground, including fraud, after expiry of 3 years.",
        "question_type": "numeric",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "If a claim is repudiated, within how many days must the Company refund the premiums collected up to the date of repudiation?",
        "expected_answer": "Within 90 days from the date of repudiation.",
        "question_type": "numeric_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the Free Cover Limit (FCL), and how is it different from the Sum Assured?",
        "expected_answer": "The Free Cover Limit is the amount of insurance cover the Company provides to a member without requiring medical underwriting — it's an underwriting threshold, not a payable amount. The Sum Assured is the amount guaranteed to be paid to the beneficiary when the insured event occurs.",
        "question_type": "definition_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What is the difference between the Policy Year and the Member Anniversary Date?",
        "expected_answer": "The Policy Year is a twelve-month period starting with the Policy Commencement Date or Annual Renewal Date, applying to the policy overall. The Member Anniversary Date is the date numerically corresponding to an individual Insured Member's own Risk Commencement Date in each subsequent Policy Year.",
        "question_type": "definition_distractor",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Are the Risk Commencement Date and the Policy Commencement Date the same date under this policy?",
        "expected_answer": "No — the Policy Commencement Date is when the Policy itself comes into effect, while the Risk Commencement Date is the date insurance coverage for a specific member actually begins; these can differ.",
        "question_type": "negation",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "If an employee dies by suicide within one year of joining an Employer-Employee group policy, is the death benefit payable in full?",
        "expected_answer": "Yes — for Employer-Employee groups, the suicide clause does not apply, so the full death benefit is payable even if death is due to suicide within the first year.",
        "question_type": "conditional",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "If a member of a Non-Employer-Employee group dies by suicide within the first year of membership, what amount is payable?",
        "expected_answer": "Only 80% of the premiums paid (excluding service tax) — not the full death benefit.",
        "question_type": "conditional",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does the Accidental Death Benefit exclusion for intoxication always apply?",
        "expected_answer": "No — the exclusion does not apply if the intoxicating substance was taken as per a lawful medical prescription.",
        "question_type": "conditional",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does the Accidental Death Benefit exclusion for flying/aviation activities always apply?",
        "expected_answer": "No — it does not apply if the Insured Member was a bona fide passenger on a licensed commercial aircraft; the exclusion is for non-passenger flying activities.",
        "question_type": "conditional",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "What additional documents are required for a death claim if the death was due to an accident or was unnatural, beyond the standard claim documents?",
        "expected_answer": "Attested copies of the FIR and the Final Investigation Report, plus an attested copy of the post-mortem report.",
        "question_type": "cross_reference",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does the automatic cessation of Insurance Cover on the listed trigger events always apply?",
        "expected_answer": "No — cessation is automatic unless the Member has opted for a Continuation Option, in which case cover doesn't automatically cease on those trigger events.",
        "question_type": "conditional",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "If an insurer wants to repudiate a policy on the ground of fraud, who bears the burden of proving there was no deliberate intention to suppress facts?",
        "expected_answer": "The Policyholder/claimant bears the burden — the onus is on them to disprove fraud, not on the insurer to prove it.",
        "question_type": "reasoning",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does the 3-year non-contestability period under Section 45 protect a policyholder from having their stated age questioned?",
        "expected_answer": "No — the 3-year rule does not apply to questioning age; the insurer can call for proof of age at any time, even after 3 years.",
        "question_type": "negation",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Is there any Surrender Value payable under this policy?",
        "expected_answer": "No, there is no Surrender Value payable under this policy.",
        "question_type": "negative_fact",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does this policy accrue any bonuses over time?",
        "expected_answer": "No — this is a non-participating policy, so no bonuses accrue under it.",
        "question_type": "negative_fact",
        "source_document": "HDFC Life Group Term Life",
    },
    {
        "question": "Does the Married Women's Property (MWP) Act apply to this policy?",
        "expected_answer": "No — the MWP Act is explicitly stated as not applicable to this Policy.",
        "question_type": "negative_fact",
        "source_document": "HDFC Life Group Term Life",
    },
    # ======================================================
    # AI-900 (9)
    # ======================================================
    {
        "question": "According to the document, what is Optical Character Recognition (OCR) used for, and how does it differ from Object Detection?",
        "expected_answer": "OCR extracts text from images by recognizing text characters and converting them into machine-encoded text. Object Detection is a different computer vision technique that detects and locates specific objects in an image, drawing bounding boxes around them, rather than extracting text.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "What is the difference between Facial Detection and Facial Analysis according to the document?",
        "expected_answer": "Facial Detection identifies and locates human faces in an image or video, producing a bounding box around each detected face. Facial Analysis goes further, providing detailed attributes about each detected face such as age, gender, ethnicity, emotion, and facial landmarks.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "According to the document, what is the goal of Regression in machine learning, and how does Classification differ from it?",
        "expected_answer": "Regression aims to predict continuous numerical values (like price or temperature) by minimizing the difference between predicted and actual values. Classification instead predicts a categorical label from a specified number of classes.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "What is the difference between binary classification and multiclass classification, according to the document?",
        "expected_answer": "Binary classification predicts one of two possible output classes (output is 0 or 1). Multiclass classification predicts one of several possible output classes, with each class assigned a probability and the highest-probability label selected.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "According to the document, what is the difference between Named Entity Recognition (NER) and Key Phrase Extraction in Azure AI Language?",
        "expected_answer": "NER identifies important information in text such as people, places, and organizations. Key Phrase Extraction identifies the most significant words or phrases that summarize the text's main meaning.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "What are features and labels in machine learning, according to the document?",
        "expected_answer": "Features are the input values/characteristics fed into a machine learning model (e.g. number of bedrooms, size of a house). Labels are the output values the model tries to predict or classify.",
        "question_type": "definition_distractor",
        "source_document": "ai-900.docx",
    },
    {
        "question": "According to the document, what is the purpose of a validation dataset in machine learning model training?",
        "expected_answer": "It provides a measure of how well the model generalizes to new, unseen data — the model is trained on the training dataset, then its accuracy is checked using the validation dataset.",
        "question_type": "detail",
        "source_document": "ai-900.docx",
    },
    {
        "question": "According to the document, how many languages does the Translator service within Azure support, and what capability does it offer beyond text translation?",
        "expected_answer": "It supports more than 70 languages and can also generate audio translations in addition to text translations.",
        "question_type": "detail",
        "source_document": "ai-900.docx",
    },
    {
        "question": "According to the document, what is tokenization used for, and how does it differ from transcribing?",
        "expected_answer": "Tokenization is part of speech synthesis and involves breaking text into individual words so each word can be assigned phonetic sounds. Transcribing is part of speech recognition and involves converting speech into a text representation — they belong to opposite processes.",
        "question_type": "distractor",
        "source_document": "ai-900.docx",
    },
    # ======================================================
    # PYTHON DOC (6)
    # ======================================================
    {
        "question": "According to the document, which Python collection types are both ordered and mutable?",
        "expected_answer": "List and Dictionary are both ordered and mutable. Tuple is ordered but not mutable, and Set is mutable but not ordered.",
        "question_type": "distractor",
        "source_document": "python_rag_10_pages.txt",
    },
    {
        "question": "Which Python file mode is used to read a file in binary form?",
        "expected_answer": "'rb' (Read binary).",
        "question_type": "detail",
        "source_document": "python_rag_10_pages.txt",
    },
    {
        "question": "According to the document, which year was Python first released, and who created it?",
        "expected_answer": "Python was first released in 1991, created by Guido van Rossum.",
        "question_type": "direct",
        "source_document": "python_rag_10_pages.txt",
    },
    {
        "question": "According to the document, what are the four OOP concepts listed, and what does polymorphism mean in that list?",
        "expected_answer": "The four concepts listed are Class, Object, Inheritance, and Polymorphism. Polymorphism means having multiple implementations.",
        "question_type": "detail",
        "source_document": "python_rag_10_pages.txt",
    },
    {
        "question": "According to the document, which Python web framework is described as best suited for high-performance APIs, and which is described for lightweight web apps?",
        "expected_answer": "FastAPI is described for high-performance APIs; Flask is described for lightweight web apps (Django is described for full-stack applications).",
        "question_type": "distractor",
        "source_document": "python_rag_10_pages.txt",
    },
    {
        "question": "According to the document's roadmap notes on Agentic RAG, what should be used to route requests, and what should be used for evaluation?",
        "expected_answer": "An API Gateway should be used to route requests, and LangSmith should be used for evaluation.",
        "question_type": "detail",
        "source_document": "python_rag_10_pages.txt",
    },
    # ======================================================
    # PORTFOLIO PERFORMANCE REPORT (4)
    # ======================================================
    {
        "question": "What is the Portfolio ID, initial investment, and status for the 'towers' portfolio?",
        "expected_answer": "Portfolio ID PF-6, initial investment 969, status PENDING.",
        "question_type": "direct",
        "source_document": "Portfolio Performance Report",
    },
    {
        "question": "What is the Portfolio ID and initial investment for 'cts'?",
        "expected_answer": "Portfolio ID PF-7, initial investment 1291.",
        "question_type": "distractor",
        "source_document": "Portfolio Performance Report",
    },
    {
        "question": "Across all three portfolios in the report, is there any gain or loss recorded, and what is the status of each?",
        "expected_answer": "No — the Gain/Loss for all three portfolios (Infobeans, towers, cts) is 0.00, and all three are marked as PENDING.",
        "question_type": "detail",
        "source_document": "Portfolio Performance Report",
    },
    {
        "question": "What is the Final Value of the Infobeans portfolio, and how does it compare to its Initial Investment?",
        "expected_answer": "The Final Value is 6969.00, which is the same as its Initial Investment of 6969 (no change).",
        "question_type": "detail",
        "source_document": "Portfolio Performance Report",
    },
    # ======================================================
    # OUT OF CONTEXT — true abstention tests (6)
    # ======================================================
    {
        "question": "What is the current stock price of HDFC Life?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
    {
        "question": "Who is the current CEO of HDFC Life?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
    {
        "question": "What is the weather in Hyderabad today?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
    {
        "question": "What is the average annual return of the PF-5 portfolio over the last five years?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
    {
        "question": "What is the current inflation rate in India?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
    {
        "question": "Which programming language is recommended for game engine development, according to these documents?",
        "expected_answer": "This information is not available in the provided documents.",
        "question_type": "out_of_context",
        "source_document": "none",
    },
]


def seed_dataset():
    client = Client()

    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)

        existing = list(client.list_examples(dataset_id=dataset.id))
        if existing:
            client.delete_examples(example_ids=[ex.id for ex in existing])
            print(f"Deleted {len(existing)} existing example(s).")
    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=(
                "Evaluation dataset for Hybrid RAG using HDFC Life policy, "
                "Portfolio Performance, ai-900, and python_rag_10_pages documents. "
                "Deliberately adversarial: numeric near-miss distractors, "
                "similar-sounding definitions, conditional/exception logic, "
                "negative facts, and out-of-context abstention checks."
            ),
        )
        print(f"Created dataset {dataset.id}.")

    client.create_examples(
        inputs=[
            {
                "question": item["question"],
                "question_type": item["question_type"],
                "source_document": item["source_document"],
            }
            for item in EXAMPLES
        ],
        outputs=[
            {"expected_answer": item["expected_answer"]}
            for item in EXAMPLES
        ],
        dataset_id=dataset.id,
    )

    print(f"Added {len(EXAMPLES)} new example(s) to '{DATASET_NAME}'.")


if __name__ == "__main__":
    seed_dataset()
