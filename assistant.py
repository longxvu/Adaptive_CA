from openai import OpenAI
import json
import time


class GPTAssistant:
    # Create an OpenAI chat assistant.
    # Normally an assistant can have multiple threads but for our purpose we restrict to 1 thread to preserve context
    # This class is mainly just to wrap around OpenAI's API call to make it easier to use
    def __init__(self, client: OpenAI, assistant_id: str, logger=None):
        self.client = client
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        self.id = assistant_id
        self.logger = logger

        # New assistant is basically old assistant but new thread, can rewrite this one maybe
        self.thread = self.client.beta.threads.create()
        if self.logger:
            self.logger.debug(f"Current thread's ID: {self.thread.id}")
        self.last_run = None

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
            return f"{message.content[0].text.value}"     # TODO: Maybe later but why 0?
        else:
            print(message.content)
            return f"{message.role}: {message.content[0].text.value}"

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
        if not self.run_requires_action():
            return
        all_tool_outputs = []
        json_responses = []
        for tool_call in self.last_run.required_action.submit_tool_outputs.tool_calls:
            # Different tool requires different tool output maybe
            name = tool_call.function.name
            # required_function = self.function_map[name]["function"]
            json_output = json.loads(tool_call.function.arguments)
            if self.logger:
                self.logger.debug(f"Calling: {name}")
                self.logger.debug(json_output)
            # Extracting required arguments from an arbitrary defined function. Need to define it in self.function_map
            # arguments = [json_output[key] for key in self.function_map[name]["arguments"]]
            # responses = required_function(*arguments)
            responses = None
            # print(responses)
            all_tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(responses)
            })

            json_responses.append(json_output)

        self.last_run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.last_run.id,
            tool_outputs=all_tool_outputs
        )
        return json_responses

    # Basically a wrapper for a conversation step. If no tools are specified, it will behave exactly like a chatbot
    # If tools are specified, the assistant will try to use the tools if context fit.
    # The reason we will use tools is to have a foolproof json response format.
    def converse(self, message, tools=None):
        # Update tools used in this message
        if tools is None:
            tools = []
        api_tools = [{"type": "function", "function": tool} for tool in tools]
        self.client.beta.assistants.update(assistant_id=self.id, tools=api_tools)
        self.submit_message(message)

        if not tools:
            return self.get_last_response()

        json_response = self.resolve_run_required_action()
        return self.get_last_response(), json_response

    def run_not_finished(self):
        return self.last_run.status == "queued" or self.last_run.status == "in_progress"

    def run_requires_action(self):
        return self.last_run.status == "requires_action"
