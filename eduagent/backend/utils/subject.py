import re


SUBJECT_KEYWORDS: dict[str, set[str]] = {
    "dsa": {"dsa", "data structure", "data structures", "algorithm", "algorithms", "array", "arrays", "linked list", "stack", "queue", "tree", "trees", "graph", "graphs", "sorting", "searching", "dynamic programming"},
    "dbms": {"dbms", "database", "databases", "sql", "relational", "normalization", "transaction", "transactions", "acid", "schema", "query processing"},
    "os": {"operating system", "operating systems", "process", "processes", "scheduling", "deadlock", "paging", "virtual memory", "file system"},
    "networks": {"computer network", "computer networks", "networking", "tcp", "udp", "osi", "routing", "subnet"},
    "math": {"mathematics", "jee", "algebra", "calculus", "trigonometry", "coordinate geometry", "probability", "integration", "differentiation"},
    "physics": {"physics", "mechanics", "electrostatics", "thermodynamics", "optics", "electromagnetism"},
    "chemistry": {"chemistry", "organic chemistry", "inorganic chemistry", "physical chemistry", "chemical bonding"},
}


def infer_subject(filename: str = "", text: str = "") -> str | None:
    """Infer a broad academic subject from a filename and representative content."""
    haystack = f"{filename} {text[:16000]}".lower().replace("_", " ").replace("-", " ")
    scores: dict[str, int] = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            hits = len(re.findall(rf"\b{re.escape(keyword)}\b", haystack))
            score += hits * (4 if keyword in filename.lower() else 1)
        scores[subject] = score
    winner = max(scores, key=scores.get)
    return winner if scores[winner] >= 2 else None


def subjects_match(selected_topic: str, filename: str = "", document_text: str = "") -> bool:
    selected = infer_subject(text=selected_topic)
    document = infer_subject(filename=filename, text=document_text)
    # Unknown classifications are handled by strict keyword excerpt matching.
    return not selected or not document or selected == document
