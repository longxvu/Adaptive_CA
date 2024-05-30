import os
from openai import OpenAI
from assistant import GPTAssistant
import pandas as pd
import utils
from tool_functions import (generate_feedback_pretest_function_json, generate_question_function_json,
                            generate_feedback_function_json, simplify_question_function_json)

from multimedia.TTS import TTSClient
from multimedia.STT import STTClient
from multimedia.video_player import VideoPlayer


class AdaptiveCA:
    def __init__(self, assistant_id: str = "asst_ZNz4lbi6z8bpKkE6APKdrpQ8",
                 pretest_file_path: str = "transcripts/lucky_shirt_pre_test.xlsx",
                 dialogue_file_path: str = "transcripts/lucky_shirt_base.xlsx",
                 text_only=False):
        self.client = OpenAI(api_key=utils.get_api_key())
        self.assistant = GPTAssistant(self.client, assistant_id)
        self.tts_client = TTSClient(tts_private_key_path="keys/tts-private-key.json", tmp_output_dir="temp/tts_temp")
        self.stt_client = STTClient(stt_private_key_path="keys/stt-private-key.json", tmp_output_dir="temp/stt_temp")
        self.video_player = VideoPlayer(full_screen=True)
        self._initialize_assistant()
        self._retrieve_pretest(pretest_file_path)
        self._retrieve_dialogue(dialogue_file_path)
        self._retrieve_videos_path()
        # Mainly for testing. I/O will be through console
        self.text_IO = text_only

    def _initialize_assistant(self):
        # Update instructions, model, and tools assistants can use
        self.client.beta.assistants.update(assistant_id=self.assistant.id, name="Science Tutor for children")
        instructions = "As a conversational agent designed to help children from 3 to 6 learn science."
        self.client.beta.assistants.update(assistant_id=self.assistant.id, instructions=instructions)
        self.client.beta.assistants.update(assistant_id=self.assistant.id, model="gpt-4o")
        available_tools = [generate_feedback_pretest_function_json, generate_question_function_json,
                           generate_feedback_function_json, simplify_question_function_json]
        available_tools = [{"type": "function", "function": tool} for tool in available_tools]
        self.client.beta.assistants.update(assistant_id=self.assistant.id, tools=available_tools)

    def _retrieve_pretest(self, pretest_file_path):
        df = pd.read_excel(pretest_file_path, usecols=["question", "level", "answer"])
        self.pretest = df.to_dict(orient="records")

    def _retrieve_dialogue(self, dialogue_file_path):
        df = pd.read_excel(dialogue_file_path, usecols=["text", "question"])
        self.dialogues = df.to_dict(orient="records")
        # For now don't retrieve question without any dialogue (e.g. in town_picnic_base.xlsx)
        self.dialogues = [dialogue for dialogue in self.dialogues if dialogue["text"].strip()]

    def _retrieve_videos_path(self):
        videos_dir = "videos"  # TODO: ideally this should be in a config and everything is read from config
        video_names = ["01_episode.mp4", "02_episode.mp4"]  # Should be sorted according to the dialogue order
        episode_path_list = [os.path.join(videos_dir, video_name) for video_name in video_names]
        self.video_path_list = {
            "episodes": episode_path_list,
            "idle": os.path.join(videos_dir, "rosita-idle.mp4"),
            "lip_flap": os.path.join(videos_dir, "rosita-lip-flap.mp4"),
        }

    def get_assistant_info(self):
        assistant_data = self.client.beta.assistants.retrieve(self.assistant.id).model_dump()
        object_list = ["id", "name", "description", "instructions", "model", "temperature", "tools"]
        return "\n".join([f"{obj}: {assistant_data[obj]}" for obj in object_list])

    def speak(self, *texts):
        # Basically a wrapper for printing out, can choose either doing TTS or not (for debugging)
        texts = " ".join(texts)
        print(texts)
        if not self.text_IO:
            # Playing lip flap video while TTS
            self.video_player.play_video_non_blocking(self.video_path_list["lip_flap"])
            self.tts_client.text_to_speech(texts)
            self.video_player.stop_video()

    def get_response(self):
        if self.text_IO:
            return input("Response: ")

        # Playing idle video while getting response
        self.video_player.play_video_non_blocking(self.video_path_list["idle"])
        response = self.stt_client.speech_to_text(5)
        self.video_player.stop_video()

        if response:
            response = response[0]
        print(f"Response: {response}")
        return response

    def ask_question(self, question):
        self.speak(question)
        answer = self.get_response()
        return answer

    def run_pre_test(self):
        print("Pretest phase")
        print("=" * 50)
        print(self.assistant.converse("Now I will begin asking the child a few pretest questions, then you will give me"
                                      "feedbacks based on the child's answer"))
        for pretest_eval in self.pretest:
            pretest_question, pretest_answer = pretest_eval["question"], pretest_eval["answer"]
            question_level = pretest_eval["level"]
            # I/O stuffs
            child_answer = self.ask_question(pretest_question)
            pretest_eval["child_answer"] = child_answer

            # Get feedback from GPT
            pretest_msg = (f"Here's a {question_level} pretest question: {pretest_question}, and a sample "
                           f"answer: {pretest_answer}. Here's the child's answer: {child_answer}. Please give the "
                           "child a feedback based on their answer.")
            responses, json_response = self.assistant.converse(pretest_msg,
                                                               tools=[generate_feedback_pretest_function_json])
            # print(responses, json_response)

            feedback, accuracy = json_response[0]["feedback"], json_response[0]["accuracy"]
            pretest_eval["accuracy"] = accuracy

            self.speak(feedback)

    def adaptive_learning_loop(self):
        def generate_question(learning_history):
            # Template for generating question
            question_gen_msg = (f"Here's the child learning's history: {learning_history}, please "
                                f"generate a question based on the child's learning history and the story.")
            feedback_msg, json_tool_responses = self.assistant.converse(question_gen_msg,
                                                                        tools=[generate_question_function_json])
            return feedback_msg, json_tool_responses

        def generate_feedback(answer):
            # Template function to generate feedback from child's answer
            feedback_generation_msg = (f"Here's the child's answer: {answer}. Generate feedback based on this "
                                       f"answer.")
            feedback_msg, json_tool_responses = self.assistant.converse(feedback_generation_msg,
                                                                        tools=[generate_feedback_function_json])
            return feedback_msg, json_tool_responses

        def simplify_question(question):
            # Template to simplify question
            simplified_generation_msg = (f"The child couldn't answer the previous question, please give me a "
                                         f"simplified version of {question}")
            feedback_msg, json_tool_responses = self.assistant.converse(simplified_generation_msg,
                                                                        tools=[simplify_question_function_json])
            return feedback_msg, json_tool_responses

        print("Adaptive learning loop")
        print("=" * 50)
        print(self.assistant.converse(("The pretest is done. Now you will be presented with a transcript from an "
                                       "animation made to help children learn science concepts. The dialogue will be "
                                       "divided into multiple parts, with each part focusing on a science concept. "
                                       "Your goal is to help the child learn science knowledge from the stories.")))
        # Question level ranges: [0,2] inclusive
        question_levels = ["shallow", "intermediate", "deep"]
        episode_learning_history = []

        for idx, dialogue in enumerate(self.dialogues[:2]):
            dialogue_text, base_question = dialogue["text"], dialogue["question"]
            print("---- video playing")
            if self.text_IO:  # Debugging
                print(dialogue_text[:200] + "...")
            else:
                self.video_player.play_video(self.video_path_list["episodes"][idx], max_duration=5)
            # Learning history for this part only
            current_learning_history = []

            # Story conversing + generating base question
            question_generation_msg = (f"Here's the story: {dialogue_text}. | \n"
                                       f"Base question for the given story: {base_question}. | \n "
                                       f"Generate an intermediate question based on the given story and the base "
                                       f"question.")
            feedback, json_responses = self.assistant.converse(question_generation_msg,
                                                               tools=[generate_question_function_json])

            # Ask maximum 3 questions
            max_questions = 3
            next_q_level = 1    # Base question is intermediate
            for q_id in range(max_questions):
                # Ask question, get child's answer, and generate feedback based on that answer
                generated_question = json_responses[0]["question"]
                child_answer = self.ask_question(generated_question)
                feedback, json_responses = generate_feedback(child_answer)
                accuracy, evaluation, explanation, transition = [json_responses[0][obj] for obj in [
                    "accuracy", "evaluation", "explanation", "transition"]]
                print(f"Answer's accuracy: {accuracy}")

                # Append it to the learning history
                current_learning_history.append({
                    "question": generated_question,
                    "answer": child_answer,
                    "accuracy": accuracy
                })

                # Modify the difficulty for the next question
                last_q_level = next_q_level
                # Adjusting question difficulty (this only affects the state we are in e.g.
                # The actual question difficulty is adjusted by learning history.
                # If that doesn't work, we can use this one to specify the question level)
                next_q_level = min(next_q_level + 1, 2) if accuracy >= 0.9 else max(next_q_level - 1, 0)
                print(f"Last question level: {question_levels[last_q_level]}, "
                      f"next question level: {question_levels[next_q_level]}")
                # If we have two rights (or wrongs) in a row, evaluation + exit
                # We also check for if it's currently the last questions
                if next_q_level == last_q_level == 0 or next_q_level == last_q_level == 2 or q_id == max_questions - 1:
                    self.speak(evaluation, explanation)
                    break
                # Simplifying previous asked question
                if next_q_level == 0:   # TODO: currently deep -> intermediate doesn't simplify
                    self.speak(evaluation, transition)
                    feedback, json_responses = simplify_question(generated_question)
                else:   # Harder question only rely on learning history
                    self.speak(evaluation, explanation, transition)
                    feedback, json_responses = generate_question(current_learning_history)
                print("-----")

    def run_program(self):
        # Pretest
        # print("=" * 50)
        # pre_test_pre_msg = "Let's begin with a pretest!"
        # print(pre_test_pre_msg)
        # self.tts_client.text_to_speech(pre_test_pre_msg)
        # self.run_pre_test()
        # print("=" * 50)

        # Adaptive learning loop
        pre_adaptive_loop_msg = "Let's begin learning some science concepts presented in the story!"
        self.speak(pre_adaptive_loop_msg)
        self.adaptive_learning_loop()

        # Done. Clean up the temporary created audio files
        post_adaptive_loop_msg = "Congratulations! Hope you have fun learning something new today!"
        self.speak(post_adaptive_loop_msg)

        # shutil.rmtree(self.tts_client.tmp_output_dir)
        # shutil.rmtree(self.stt_client.tmp_output_dir)


if __name__ == "__main__":
    adaptive_conversational_agent = AdaptiveCA(text_only=False)
    print(adaptive_conversational_agent.get_assistant_info())
    adaptive_conversational_agent.run_program()
