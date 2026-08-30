"""JSON schemas for Gemini's structured output (§5, ai/schemas.py). Passed as
response_schema so screening/interview-summary calls return parseable JSON
rather than free text."""

SCREENING_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "summary": {"type": "string"},
        "extracted": {
            "type": "object",
            "properties": {
                "skills": {"type": "array", "items": {"type": "string"}},
                "years_experience": {"type": "number"},
                "education": {"type": "string"},
            },
        },
        "requirement_matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement": {"type": "string"},
                    "met": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
            },
        },
    },
    "required": ["score", "summary", "extracted", "requirement_matches"],
}

INTERVIEW_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "scorecard_draft": {"type": "object"},
    },
    "required": ["summary", "scorecard_draft"],
}
