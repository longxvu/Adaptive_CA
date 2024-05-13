from openai import OpenAI
import json
import time
from utils import load_json_response


class GPTAssistant:
    # Create an OpenAI chat assistant.
    # Normally an assistant can have multiple threads but for our purpose we restrict to 1 thread to preserve context
    def __init__(self, client: OpenAI, assistant_id: str = None, assistant_name: str = None,
                 instruction: str = None, model: str = "gpt-3.5-turbo-0125"):
        # TODO: In the API example, they seem to encourage only using 1 assistant for multiple threads, instead of using
        # 1 assistant for only 1 thread. Need to figure out why (?) Maybe one assistant when creating multiple threads
        # are trained on those specific threads? So the later usage of the same assistant will be better?
        self.client = client
        if not assistant_id:
            self.assistant = self.client.beta.assistants.create(
                name=assistant_name,
                instructions=instruction,
                model=model
            )
        else:
            self.assistant = self.client.beta.assistants.retrieve(assistant_id)

        # New assistant is basically old assistant but new thread, can rewrite this one maybe
        self.thread = self.client.beta.threads.create()
        self.last_run = None
        self.function_map = {
            "display_quiz": {
                "function": self.display_quiz,
                "arguments": ["title", "questions"]
            },
            "generate_feedback": {
                "function": self.display_feedback,
                "arguments": ["evaluation"]
            }
        }

    def submit_message(self, message):
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=message
        )
        self.last_run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )
        return self.last_run

    def wait_on_run(self):
        # Wait until a run is finished or an action is required
        while self.last_run and self.run_not_finished() and not self.run_requires_action():
            self.last_run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=self.last_run.id,
            )
            time.sleep(0.5)
        return self.last_run

    # Mainly used for getting a response after submitting a message. Will wait for either response or actions are
    # required
    def get_last_response(self, pretty=True):
        self.wait_on_run()
        message = next(iter(self.client.beta.threads.messages.list(thread_id=self.thread.id)))
        if pretty:
            return f"{message.role}: {message.content[0].text.value}"     # TODO: Maybe later but why 0?
        else:
            return message

    def get_all_messages(self):
        self.wait_on_run()
        all_messages = self.client.beta.threads.messages.list(thread_id=self.thread.id, order="asc")
        results = []
        for message in all_messages:
            results.append(f"{message.role}: {message.content[0].text.value}")
        return results

    # Basically the way function call work for the API is (if I understand correctly)
    # 1) Chat thread like normal
    # 2) Whenever our prompt is the same as one of the defined function, OpenAI will trigger the function, and depending
    # on the definition, we might need to resolve the required action
    # 3) Function information can be found in tool_call.function.arguments, and we can use those to get the required
    # input from our side, and submit it back to the GPT model
    def resolve_run_required_action(self):
        self.wait_on_run()
        assert self.run_requires_action()
        all_tool_outputs = []
        action_items = {}
        for tool_call in self.last_run.required_action.submit_tool_outputs.tool_calls:
            # Different tool requires different tool output maybe
            name = tool_call.function.name
            required_function = self.function_map[name]["function"]
            arguments = json.loads(tool_call.function.arguments)
            print(f"Calling: {name}")
            # print(arguments)
            # Extracting required arguments from an arbitrary defined function. Need to define it in self.function_map
            arguments = [arguments[key] for key in self.function_map[name]["arguments"]]
            responses = required_function(*arguments)
            # print(responses)
            all_tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(responses)
            })
            action_items[name] = responses  # Return from each function is mapped to the function name
        self.last_run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.last_run.id,
            tool_outputs=all_tool_outputs
        )
        return action_items

    def run_not_finished(self):
        return self.last_run.status == "queued" or self.last_run.status == "in_progress"

    def run_requires_action(self):
        return self.last_run.status == "requires_action"

    def get_user_input(self):
        return input("Answer: ")

    def display_quiz(self, title, questions):
        # print(title, questions)   # this is for debugging arguments passed by OpenAI API
        print("Quiz:", title)
        print()
        num_q_difficulty = [0] * 3
        diff_map = {"EASY": 0, "MEDIUM": 1, "HARD": 2}      # TODO: hardcoded
        responses = []

        for q in questions:
            print(f"Questions: {q['question_text']} ({q['difficulty']} - {q['category']})")
            num_q_difficulty[diff_map[q["difficulty"]]] += 1
            response = ""

            # If multiple choice, print options
            if q["question_type"] == "MULTIPLE_CHOICE":
                for i, choice in enumerate(q["choices"]):
                    print(f"{chr(i + ord('a'))}) {choice}")
                response = self.get_user_input()

            # Otherwise, just get response
            elif q["question_type"] == "FREE_RESPONSE":
                response = self.get_user_input()

            responses.append(response)
            print()
        print(f"Student responses: {responses}")

        return num_q_difficulty, responses

    def display_feedback(self, evaluation):
        scores = [list() for _ in range(3)]    # scores for easy, medium, hard
        diff_map = {"EASY": 0, "MEDIUM": 1, "HARD": 2}
        concepts = {"mastered": [], "learning": []}
        for idx, e in enumerate(evaluation):
            print(f"Question {idx + 1}:")
            print(f"Student response: {e['student_response']}")
            print(f"Feedback: {e['feedback']}")
            print(f"Score: {e['score']}")
            scores[diff_map[e["difficulty"]]].append(e["score"])
            if e['score'] <= 4:
                concepts["learning"].append(e['concept'])
            else:
                concepts["mastered"].append(e['concept'])
            print()
        # print(f"Quiz score: {sum(scores)}/{len(scores)}")
        print(f"Mastered concepts: {concepts['mastered']}")
        print(f"Learning concepts: {concepts['learning']}")
        return scores, concepts
