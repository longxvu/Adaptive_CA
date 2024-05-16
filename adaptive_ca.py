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
                 dialogue_file_path: str = "transcripts/lucky_shirt_base.xlsx"):
        self.client = OpenAI(api_key=utils.get_api_key())
        self.assistant = GPTAssistant(self.client, assistant_id)
        self.tts_client = TTSClient(tts_private_key_path="keys/tts-private-key.json", tmp_output_dir="temp/tts_temp")
        self.stt_client = STTClient(stt_private_key_path="keys/stt-private-key.json", tmp_output_dir="temp/stt_temp")
        self.video_player = VideoPlayer()
        self._initialize_assistant()
        self._retrieve_pretest(pretest_file_path)
        self._retrieve_dialogue(dialogue_file_path)
        self._retrieve_videos_path()

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
        self.get_assistant_info()

    def _retrieve_pretest(self, pretest_file_path):
        df = pd.read_excel(pretest_file_path, usecols=["question", "level", "answer"])
        self.pretest = df.to_dict(orient="records")

    def _retrieve_dialogue(self, dialogue_file_path):
        df = pd.read_excel(dialogue_file_path, usecols=["text", "question"])
        self.dialogues = df.to_dict(orient="records")
        # For now don't retrieve question without any dialogue (e.g. in town_picnic_base.xlsx)
        self.dialogues = [dialogue for dialogue in self.dialogues if dialogue["text"].strip()]

    def _retrieve_videos_path(self):
        videos_dir = "videos"     # TODO: ideally this should be in a config and everything is read from config
        video_names = ["01_episode.mp4", "02_episode.mp4"]  # Should be sorted according to the dialogue order
        self.video_path_list = [os.path.join(videos_dir, video_name) for video_name in video_names]

    def get_assistant_info(self):
        assistant_data = self.client.beta.assistants.retrieve(self.assistant.id).model_dump()
        object_list = ["id", "name", "description", "instructions", "model", "temperature", "tools"]
        for obj in object_list:
            print(f"{obj}: {assistant_data[obj]}")

    def ask_question(self, question):
        print(f"Question: {question}")
        self.tts_client.text_to_speech(question)
        # answer = input("Answer: ")
        answer = self.stt_client.speech_to_text(5)[0]
        print(f"Child's recorded answer: {answer}")
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
            # print(pretest_msg)
            # print("----")
            responses, json_response = self.assistant.converse(pretest_msg,
                                                               tools=[generate_feedback_pretest_function_json])
            # print(responses, json_response)

            feedback, accuracy = json_response[0]["feedback"], json_response[0]["accuracy"]
            pretest_eval["accuracy"] = accuracy

            print(feedback)
            self.tts_client.text_to_speech(feedback)

    def adaptive_learning_loop(self):
        print("Adaptive learning loop")
        print("=" * 50)
        print(self.assistant.converse(("The pretest is done. Now you will be presented with a transcript from an "
                                       "animation made to help children learn science concepts. The dialogue will be "
                                       "divided into multiple parts, with each part focusing on a science concept. "
                                       "Your goal is to help the child learn science knowledge from the stories.")))
        learning_history = []

        for idx, dialogue in enumerate(self.dialogues[:2]):
            dialogue_text, base_question = dialogue["text"], dialogue["question"]
            # print("Story begins:")
            # print(dialogue_text[:200])     # TODO: Should show video instead of displaying bunch of text.
            print("---- video playing")
            self.video_player.play_video(self.video_path_list[idx], max_duration=5)
            # Learning history for this part only
            current_learning_history = []
            # Story conversing

            question_generation_msg = (f"Here's the story: {dialogue_text}. | \n"
                                       f"Base question for the given story: {base_question}. | \n "
                                       f"Generate a question based on the given story and the base question.")
            feedback, json_responses = self.assistant.converse(question_generation_msg,
                                                               tools=[generate_question_function_json])
            # print(feedback, json_responses)
            # print("----")
            generated_question = json_responses[0]["question"]
            # Interactive part
            child_answer = self.ask_question(generated_question)

            feedback_generation_msg = (f"Here's the child's answer: {child_answer}. Generate feedback based on this "
                                       f"answer.")
            feedback, json_responses = self.assistant.converse(feedback_generation_msg,
                                                               tools=[generate_feedback_function_json])
            # print(feedback, json_responses)

            accuracy, evaluation, explanation, transition = [json_responses[0][obj] for obj
                                                             in ["accuracy", "evaluation", "explanation", "transition"]]

            current_learning_history.append({
                "question": generated_question,
                "answer": child_answer,
                "accuracy": accuracy
            })
            print(f"Answer's accuracy: {accuracy}")

            # Trigger simplifying question
            if accuracy <= 0.5:
                # Child couldn't answer question, only give evaluation
                print(evaluation, transition)
                self.tts_client.text_to_speech(evaluation + transition)
                simplified_generation_msg = (f"The child couldn't answer the previous question, please give me a "
                                             f"simplified version of {generated_question}")
                feedback, json_responses = self.assistant.converse(simplified_generation_msg,
                                                                   tools=[simplify_question_function_json])
                # print(feedback, json_responses)
            else:
                # Can answer question, give evaluation + explanation
                print(evaluation, explanation, transition)
                self.tts_client.text_to_speech(evaluation + explanation + transition)
                question_generation_msg = (f"Here's the child learning's history: {current_learning_history}, please "
                                           f"generate a question based on the child's learning history and the story.")
                feedback, json_responses = self.assistant.converse(question_generation_msg,
                                                                   tools=[generate_question_function_json])
                # print(feedback, json_responses)

            generated_question = json_responses[0]["question"]
            child_answer = self.ask_question(generated_question)
            feedback_generation_msg = (f"Here's the child's answer: {child_answer}. Generate feedback based on this "
                                       f"answer.")
            feedback, json_responses = self.assistant.converse(feedback_generation_msg,
                                                               tools=[generate_feedback_function_json])
            # print(feedback, json_responses)
            evaluation, explanation, transition = [json_responses[0][obj] for obj
                                                   in ["evaluation", "explanation", "transition"]]

            print(evaluation, explanation)
            self.tts_client.text_to_speech(evaluation + explanation)
            print("-----")

    def run_program(self):
        # Pretest
        print("=" * 50)
        pre_test_pre_msg = "Let's begin with a pretest!"
        print(pre_test_pre_msg)
        self.tts_client.text_to_speech(pre_test_pre_msg)
        self.run_pre_test()
        print("=" * 50)

        # Adaptive learning loop
        pre_adaptive_loop_msg = ("We are done with the pretest. Now let's begin learning some science concepts "
                                 "presented in the story!")
        print(pre_adaptive_loop_msg)
        self.tts_client.text_to_speech(pre_adaptive_loop_msg)
        self.adaptive_learning_loop()

        # Done. Clean up the temporary created audio files
        post_adaptive_loop_msg = "Congratulations! Hope you have fun learning something new today!"
        print(post_adaptive_loop_msg)
        self.tts_client.text_to_speech(post_adaptive_loop_msg)

        # shutil.rmtree(self.tts_client.tmp_output_dir)
        # shutil.rmtree(self.stt_client.tmp_output_dir)


if __name__ == "__main__":
    adaptive_conversational_agent = AdaptiveCA()
    adaptive_conversational_agent.run_program()
