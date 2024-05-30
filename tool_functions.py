# These functions below are used by OpenAI API

generate_feedback_pretest_function_json = {
    "name": "generate_feedback_pretest",
    "description": "The pretest is to measure the child's current science knowledge. You are given a pretest "
                   "question-answer pair and the child's response. Please provide neutral feedback to the child’s "
                   "response to a question, without telling the child whether the answer is correct or incorrect.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The pretest question."
            },
            "answer": {
                "type": "string",
                "description": "The child answer."
            },
            "accuracy": {
                "type": "number",
                "description": "If the child answers the question correctly, return 1. If the child answers the "
                               "question partially correctly, return 0.5. If the child answers the question incorrectly"
                               ", does not respond, or provides an irrelevant answer, provide 0."
            },
            "feedback": {
                "type": "string",
                "description": "Provide neutral feedback to the child without telling the child whether the answer is "
                               "correct or incorrect. Even if a child asks you for help, do not tell the child the "
                               "answer. Your feedback should never contain a question. Your feedback should be within "
                               "15 words. Do not tell the child anything about the correct answer. Simply encourage "
                               "the child."
            },
        },
        "required": ["question", "answer", "accuracy", "feedback"]
    }
}

generate_question_function_json = {
    "name": "generate_question",
    "description": "Your goal is to generate a question to help the child learn science knowledge from the given "
                   "stories (represented as dialogue between multiple characters). You will be given a base question, "
                   "and the children's learning history. The question generated should be related to the story, with "
                   "the same concept asked in the base question. The difficulty should be adapted based on the "
                   "children's learning history. The question should focus on a science concept presented in the story.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The generated question. It should be related to the story using the same concept asked "
                               "in the base question."
            },
            "level": {
                "type": "string",
                "description": "The difficulty level of the question. If the child demonstrates great understanding "
                               "of the knowledge, a deeper question should be generated. If the child is struggling "
                               "with answering the question, an easier question should be generated.\n"
                               "Shallow level questions are straightforward and often require short answers. They can "
                               "be answered with a simple 'yes' or 'no', offer a choice between two options, "
                               "require specific factual information, or ask for straightforward examples. These "
                               "questions are typically fact-based and don't require much interpretation or critical "
                               "thinking.\n"
                               "Intermediate level questions delve deeper and require the respondent to provide "
                               "descriptions, quantities, definitions, or comparisons. They ask about "
                               "characteristics/features, definitions, numerical information, or require identifying "
                               "similarities and differences. These questions require a moderate level of thought and "
                               "understanding of the topic.\n"
                               "Deep level questions are the most complex and demand higher cognitive skills. They "
                               "involve interpreting meanings, understanding causes and consequences, exploring goals "
                               "and motivations, detailing processes, considering enabling factors, analyzing unmet "
                               "expectations, and eliciting personal judgments or evaluations. These questions "
                               "encourage critical thinking, explanation, inference, and personal reflection.",
                "enum": ["SHALLOW", "INTERMEDIATE", "DEEP"]
            },
            "rationale": {
                "type": "string",
                "description": "The rationale for generating the question based on learning history and the story."
            }
        }
    }
}

simplify_question_function_json = {
    "name": "simplify_question",
    "description": "You are given a question, you will rephrase the question such that it is easier for a child to "
                   "answer. The rephrased question can be answered by a yes/no answer. The simplified question must "
                   "be different from the original question.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The rephrased and simplified question."
            }
        }
    }
}

generate_feedback_function_json = {
    "name": "generate_feedback",
    "description": "Generate the feedback for the child's answer. The feedback is meant to be encouraging and as simple"
                   "as possible to aid the child's in understanding the science concept.",
    "parameters": {
        "type": "object",
        "properties": {
            # "rephrased_response": {
            #     "type": "string",
            #     "description": "The rephrased child's answer. This should be different from the child's original "
            #                    "answer and should begin with 'Your answer is '.",
            # },
            "accuracy": {
                "type": "number",
                "description": "Give a score from 0 (incorrect) to 1 (correct) based on how well the child answer."
            },
            "evaluation": {
                "type": "string",
                "description": "Evaluation of the correctness of their answers using encouraging tone, such as: "
                               "'Good job', 'Good thinking', etc. If the child's answer is irrelevant, direct them "
                               "back."
            },
            "explanation": {
                "type": "string",
                "description": "An explanation of the question within 20 words. The explanation should have its "
                               "language as close as the language used in the story. It should be as simple as possible"
                               "such that a child from 5 to 8 years old can understand."
            },
            "transition": {
                "type": "string",
                "description": "Brief transition to the next question, such as 'Here's a new question', 'Let's move on "
                               "reading!', ‘Let’s keep going!’, etc. Keep it under 5 words."
            },
        },
        "required": ["rephrased_response", "accuracy", "evaluation", "explanation", "transition"]
    }
}



# Example feedback: 'That’s an " "interesting idea!' 'That’s so interesting!' 'It’s okay that you need more
# time to ""think about this!'. If we put this in the function description, it will only return those 3 as answer
# even with GPT4

# Comment out before deleting

# display_quiz_function_json = {
#     "name": "display_quiz",
#     "description": "Displays a quiz to the student. A single quiz can have multiple questions.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "title": {
#                 "type": "string"
#             },
#             "questions": {
#                 "type": "array",
#                 "description": "An array of questions, each with a title and potentially options (if multiple choice).",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "question_text": {
#                             "type": "string",
#                             "description": "The text for question. Don't include question choices, question type, "
#                                            "difficulty, and category inside question text",
#                         },
#                         "choices": {
#                             "type": "array",
#                             "items": {"type": "string"}
#                         },
#                         "question_type": {
#                             "type": "string",
#                             "enum": ["MULTIPLE_CHOICE", "FREE_RESPONSE"],
#                         },
#                         "difficulty": {
#                             "type": "string",
#                             "description": "The difficulty level of each question. Easy difficulty level question "
#                                            "only requires yes and no answer. Medium difficulty level question asks for "
#                                            "the definition of a certain concepts. Hard difficulty level question asks "
#                                            "further interpretation of the concepts (e.g. Why/How did something occurs)",
#                             "enum": ["EASY", "MEDIUM", "HARD"]
#                         },
#                         "category": {
#                             "type": "string",
#                             "description": "The category of the question.",
#                             "enum": ["VERIFICATION", "DISJUNCTIVE", "CONCEPT_COMPLETION", "EXAMPLE",
#                                      "FEATURE_SPECIFICATION", "QUANTIFICATION", "DEFINITION", "COMPARISON",
#                                      "INTERPRETATION", "CAUSAL_ANTECEDENT", "CAUSAL_CONSEQUENCE", "GOAL_ORIENTATION",
#                                      "PROCEDURAL", "ENABLEMENT", "EXPECTATION", "JUDGEMENTAL"],
#                         }
#
#                     },
#                     "required": ["question_text", "question_type", "difficulty", "category"],
#                 },
#             },
#         },
#         "required": ["title", "questions"],
#     },
# }

# generate_feedback_function_json = {
#     "name": "generate_feedback",
#     "description": "Based on the answer provided, generate feedback based on each of the answer",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "evaluation": {
#                 "type": "array",
#                 "description": "An array of feedbacks for the answered quiz",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "student_response": {
#                             "type": "string",
#                             "description": "Student's response for the given question.",
#                         },
#                         "feedback": {
#                             "type": "string",
#                             "description": "Feedback for the student's answer."
#                         },
#                         "score": {
#                             "type": "integer",
#                             "description": "The correctness of the given answer. If the answer is correct, give a score"
#                                            "of 10. If the answer is incorrect or there's no response, give a score"
#                                            "of 0. If the answer is partially correct, then give a score depending on"
#                                            "how well the student answer the question.",
#                             "minimum": 0,
#                             "maximum": 10
#                         },
#                         "difficulty": {
#                             "type": "string",
#                             "description": "The difficulty level of the answered question.",
#                             "enum": ["EASY", "MEDIUM", "HARD"]
#                         },
#                         "concept": {
#                             "type": "string",
#                             "description": "A concise description of the concept asked in this question. This should be"
#                                            " less than 5 words.",
#                         }
#                     },
#                     "required": ["student_response", "feedback", "score", "concept", "difficulty"]
#                 }
#             }
#         }
#     }
# }

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
