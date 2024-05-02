import json
import os
from openai import OpenAI


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


def load_json_response(obj):
    return json.loads(obj.model_dump_json())


def list_all_assistant(client: OpenAI, concise=True):
    assistant_data = client.beta.assistants.list().model_dump()
    concise_object_list = ["id", "name", "description", "instructions", "model", "tools", "temperature"]
    for assistant in assistant_data["data"]:
        if concise:
            for obj in concise_object_list:
                print(f"{obj}: {assistant[obj]}")
        else:
            print(assistant)
        print("")


def get_api_key():
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__module__
        print(shell)
        if shell == "google.colab._shell":
            pass
    except NameError:
        # Probably standard interpreter
        pass
    # All other cases
    assert os.path.isfile(".api_key"), "API key file not found."
    with open(".api_key", "r") as f:
        key = f.read().strip()
    return key


