# These functions below are used by OpenAI API

display_quiz_function_json = {
    "name": "display_quiz",
    "description": "Displays a quiz to the student. A single quiz can have multiple questions.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string"
            },
            "questions": {
                "type": "array",
                "description": "An array of questions, each with a title and potentially options (if multiple choice).",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {
                            "type": "string",
                            "description": "The text for question. Don't include question choices, question type, "
                                           "difficulty, and category inside question text",
                        },
                        "choices": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
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
                        "category": {
                            "type": "string",
                            "description": "The category of the question.",
                            "enum": ["VERIFICATION", "DISJUNCTIVE", "CONCEPT_COMPLETION", "EXAMPLE",
                                     "FEATURE_SPECIFICATION", "QUANTIFICATION", "DEFINITION", "COMPARISON",
                                     "INTERPRETATION", "CAUSAL_ANTECEDENT", "CAUSAL_CONSEQUENCE", "GOAL_ORIENTATION",
                                     "PROCEDURAL", "ENABLEMENT", "EXPECTATION", "JUDGEMENTAL"],
                        }

                    },
                    "required": ["question_text", "question_type", "difficulty", "category"],
                },
            },
        },
        "required": ["title", "questions"],
    },
}

generate_feedback_function_json = {
    "name": "generate_feedback",
    "description": "Based on the answer provided, generate feedback based on each of the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "evaluation": {
                "type": "array",
                "description": "An array of feedbacks for the answered quiz",
                "items": {
                    "type": "object",
                    "properties": {
                        "student_response": {
                            "type": "string",
                            "description": "Student's response for the given question.",
                        },
                        "feedback": {
                            "type": "string",
                            "description": "Feedback for the student's answer."
                        },
                        "score": {
                            "type": "integer",
                            "description": "The correctness of the given answer. If the answer is correct, give a score"
                                           "of 10. If the answer is incorrect or there's no response, give a score"
                                           "of 0. If the answer is partially correct, then give a score depending on"
                                           "how well the student answer the question.",
                            "minimum": 0,
                            "maximum": 10
                        },
                        "difficulty": {
                            "type": "string",
                            "description": "The difficulty level of the answered question.",
                            "enum": ["EASY", "MEDIUM", "HARD"]
                        },
                        "concept": {
                            "type": "string",
                            "description": "A concise description of the concept asked in this question. This should be"
                                           " less than 5 words.",
                        }
                    },
                    "required": ["student_response", "feedback", "score", "concept", "difficulty"]
                }
            }
        }
    }
}

# categorize_question_function_json = {
#     "name": "categorize_question",
#     "description": "Categorizes a question into one of several categories.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "question_category": {
#                 "type": "string",
#                 "description": "The category of the question.",
#                 "enum": ["VERIFICATION", "DISJUNCTIVE", "CONCEPT_COMPLETION", "EXAMPLE",
#                          "FEATURE_SPECIFICATION", "QUANTIFICATION", "DEFINITION", "COMPARISON",
#                          "INTERPRETATION", "CAUSAL_ANTECEDENT", "CAUSAL_CONSEQUENCE", "GOAL_ORIENTATION",
#                          "PROCEDURAL", "ENABLEMENT", "EXPECTATION", "JUDGEMENTAL"],
#             }
#         }
#     }
# }
