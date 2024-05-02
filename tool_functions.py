display_quiz_function_json = {
    "name": "display_quiz",
    "description": "Displays a quiz to the student, and returns the student's response. "
                   "A single quiz can have multiple questions.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "questions": {
                "type": "array",
                "description": "An array of questions, each with a title and potentially options (if multiple choice).",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {"type": "string"},
                        "question_type": {
                            "type": "string",
                            "enum": ["MULTIPLE_CHOICE", "FREE_RESPONSE"],
                        },
                        "difficulty": {
                            "type": "string",
                            "description": "The difficulty level of each question. Easy difficulty level question "
                                           "only requires yes and no answer. Medium difficulty level question asks for "
                                           "the definition of a certain concepts. Hard difficulty level question asks "
                                           "further interpretation of the concepts (e.g. Why/How did something occurs)",
                            "enum": ["EASY", "MEDIUM", "HARD"]
                        },
                        "choices": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["question_text", "question_type", "difficulty"],
                },
            },
        },
        "required": ["title", "questions"],
    },
}