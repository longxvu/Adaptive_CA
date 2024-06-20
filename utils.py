import json
import os
import threading
import time
from openai import OpenAI
from google.api_core import exceptions


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


def load_json_response(obj):
    return json.loads(obj.model_dump_json())


def list_all_assistant(client: OpenAI, concise=True):
    assistant_data = client.beta.assistants.list().model_dump()
    concise_object_list = ["id", "name", "description", "instructions", "model", "temperature", "tools"]
    for assistant in assistant_data["data"]:
        if concise:
            for obj in concise_object_list:
                print(f"{obj}: {assistant[obj]}")
        else:
            print(json.dumps(assistant, indent=4))
        # Tools needs json pretty print for easier debugging
        print("=" * 50)


def get_api_key(api_key_file="keys/.api_key"):
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__module__
        # print(shell)
        if shell == "google.colab._shell":
            from google.colab import userdata
            return userdata.get("OPENAI_API_KEY")
    except (NameError, ModuleNotFoundError):
        # Probably standard interpreter
        pass
    # All other cases
    assert os.path.isfile(api_key_file), ("API key file not found. "
                                          "You should save OpenAI's API key in keys/.api_key file.")
    with open(api_key_file, "r") as f:
        key = f.read().strip()
    return key


def exception_logger(func):
    # Mainly used for logging error
    def inner(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            self = args[0]
            print(e)
            # Should log all exception, even nested one
            self.logger.exception(e)
    return inner


def time_logger(logger=None):
    def middle(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            log_msg = f"Function ({func.__name__}) took {(time.time() - start):.2f}s"
            if logger:
                logger.debug(log_msg)
            else:
                print(log_msg)
            return result
        return wrapper
    return middle


def multithread(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()
        return t
    return wrapper


_GCS_RETRIABLE_TYPES = (
   exceptions.TooManyRequests,  # 429
   exceptions.InternalServerError,  # 500
   exceptions.BadGateway,  # 502
   exceptions.ServiceUnavailable,  # 503
)


def is_gcs_retryable(exc):
    # Check if exception thrown is one of the defined exception above
    return isinstance(exc, _GCS_RETRIABLE_TYPES)


def generate_question_configuration(num_questions, difficulty_weights=None, max_score_answer=10):
    question_configuration = []
    if difficulty_weights is None:
        difficulty_weights = [2, 5, 10]  # 2 for easy, 5 for med, 10 for hard
    for easy in range(num_questions + 1):
        for medium in range(num_questions + 1):
            for hard in range(num_questions + 1):
                if easy + medium + hard == num_questions:
                    question_configuration.append((easy, medium, hard,
                                                   easy * difficulty_weights[0] + medium * difficulty_weights[1] +
                                                    hard * difficulty_weights[2]))
    question_configuration = sorted(question_configuration, key=lambda x: x[3])
    return question_configuration
