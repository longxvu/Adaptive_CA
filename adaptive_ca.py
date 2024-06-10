import os
from openai import OpenAI
from assistant import GPTAssistant
import pandas as pd
import utils
from tool_functions import (generate_feedback_pretest_function_json, select_question_function_json,
                            generate_feedback_function_json, simplify_question_function_json)

from multimedia.TTS import TTSClient
from multimedia.STT import STTClient
from multimedia.video_player import VideoPlayer
import yaml
import time
import logging
import argparse


class AdaptiveCA:
    def __init__(self, config_file="configs/sample_config.yaml", text_only=False):
        with open(config_file) as f:
            self.config = yaml.safe_load(f)
        # Mainly for testing. I/O will be through console
        self.text_IO = text_only

        self._init_logging()
        self._sanity_check()
        self._retrieve_episode_content()
        self._initialize_assistant()
        self._init_multimedia_module()

    def _init_logging(self):
        # Initialize all kind of logger
        self.logging_root_dir = os.path.join(self.config["logging"]["logging_dir"],
                                             f"{self.config['childID']:04}",
                                             time.strftime(time.strftime("%y%m%d_%H%M%S")))
        os.makedirs(self.logging_root_dir, exist_ok=True)
        self.logger = logging.getLogger("adaptive_CA")
        self.logger.setLevel(logging.DEBUG)

        # Init debug logger (Everything output from the program)
        debug_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s", "%Y-%m-%d %H:%M:%S")
        debug_handler = logging.FileHandler(
            os.path.join(self.logging_root_dir, self.config["logging"]["debug_log_file"]))
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(debug_formatter)
        self.logger.addHandler(debug_handler)
        # Init console logger
        console_formatter = logging.Formatter('%(message)s')
        console_handler = logging.StreamHandler()
        if self.text_IO:  # Debug mode on console use
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        # Init info file logger (Basically all console output + timestamps)
        file_info_formatter = logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        file_info_handler = logging.FileHandler(
            os.path.join(self.logging_root_dir, self.config["logging"]["assistant_log_file"]))
        file_info_handler.setLevel(logging.INFO)
        file_info_handler.setFormatter(file_info_formatter)
        self.logger.addHandler(file_info_handler)
        self.logger.info(f"Initializing logger...")

    def _sanity_check(self):
        self.logger.info("Checking files...")
        # Private keys + all episode pretest + transcript
        targets = list(self.config["private_key_path"].values()) + list(self.config["episode"].values())
        # Videos check
        # Keeping video_idx at 1
        self.start_video_idx = self.config["video_settings"]["start_episode"]
        self.end_video_idx = self.start_video_idx + self.config["video_settings"]["max_videos"]
        for video_idx in range(self.start_video_idx, self.end_video_idx):
            targets.append(os.path.join(self.config["episode"]["video_directory"], f"{video_idx:02}_episode.mp4"))

        num_missing = 0
        for target_file in targets:
            if not os.path.exists(target_file):
                num_missing += 1
                self.logger.info(f"{target_file} doesn't exist")
        if num_missing > 0:
            self.logger.info("Missing files detected. Exiting...")
            exit()

    def _initialize_assistant(self):
        self.logger.info("Initializing adaptive conversational assistant...")
        # Initialize client and assistant
        self.client = OpenAI(api_key=utils.get_api_key(api_key_file=self.config["private_key_path"]["OpenAI"]))
        self.assistant = GPTAssistant(self.client, self.config["OpenAI_assistant"]["id"], logger=self.logger)

        # Update instructions, model, and tools assistants can use
        self.client.beta.assistants.update(assistant_id=self.assistant.id, name="Science Tutor for children")
        instructions = "As a conversational agent designed to help children from 3 to 6 learn science."
        self.client.beta.assistants.update(assistant_id=self.assistant.id, instructions=instructions)
        self.client.beta.assistants.update(assistant_id=self.assistant.id, model="gpt-4o")
        # These will verify the tool has correct format, even though we are not using it right now
        available_tools = [generate_feedback_pretest_function_json, select_question_function_json,
                           generate_feedback_function_json, simplify_question_function_json]
        available_tools = [{"type": "function", "function": tool} for tool in available_tools]
        self.client.beta.assistants.update(assistant_id=self.assistant.id, tools=available_tools)
        self.logger.debug(self.get_assistant_info())

    def _init_multimedia_module(self, ):
        self.logger.info("Initializing multimedia module...")
        # Text-to-speech, speech-to-text, video players
        tts_log_dir = os.path.join(self.logging_root_dir, self.config["logging"]["tts_log_dir"])
        stt_log_dir = os.path.join(self.logging_root_dir, self.config["logging"]["stt_log_dir"])
        os.makedirs(tts_log_dir)
        os.makedirs(stt_log_dir)
        # Init TTS, STT client, and video player to be used later
        self.tts_client = TTSClient(tts_private_key_path=self.config["private_key_path"]["GoogleTTS"],
                                    output_dir=tts_log_dir, logger=self.logger)
        self.stt_client = STTClient(stt_private_key_path=self.config["private_key_path"]["GoogleSTT"],
                                    output_dir=stt_log_dir, logger=self.logger)
        self.video_player = VideoPlayer(full_screen=True, logger=self.logger)

    def _retrieve_episode_content(self):
        self.logger.info("Retrieving episode's content...")
        # Retrieving pretest file
        df = pd.read_excel(self.config["episode"]["pretest_file"], usecols=["question", "level", "answer"])
        self.pretest = df.to_dict(orient="records")
        self.logger.info(
            f"Retrieved {len(self.pretest)} pretest questions from {self.config['episode']['pretest_file']}")

        # Retrieving transcript file
        df = pd.read_excel(self.config["episode"]["transcript_file"], usecols=["text", "question"])
        self.dialogues = df.to_dict(orient="records")
        # For now don't retrieve question without any dialogue (e.g. in town_picnic_base.xlsx)
        self.dialogues = [dialogue for dialogue in self.dialogues if dialogue["text"].strip()]
        self.logger.info(f"Retrieved {len(self.dialogues)} parts of episode with base questions from"
                         f" {self.config['episode']['transcript_file']}")

        # Retrieving question banks
        df = pd.read_excel(self.config["episode"]["question_bank"])
        df = df.sort_values(by=["id_text", "level"], ascending=[True, False])  # Some hacks here: shallow -> int -> deep
        self.question_banks = []
        for dict_item in df.groupby("id_text").agg(list).to_dict(orient="records"):
            current_questions = []
            for question, level in zip(dict_item["question"], dict_item["level"]):
                current_questions.append({"question": question, "level": level.upper()})
            self.question_banks.append(current_questions)
        self.logger.info(f"Retrieved {len(df)} questions from {self.config['episode']['question_bank']}")

        # Retrieving videos file
        episode_path_list = [os.path.join(self.config["episode"]["video_directory"], f"{video_idx:02}_episode.mp4")
                             for video_idx in range(self.start_video_idx, self.end_video_idx)]
        self.video_path_list = {
            "episodes": episode_path_list,
            "idle": self.config["episode"]["idle_video_file"],
            "lip_flap": self.config["episode"]["lip_lap_video_file"],
        }
        self.logger.info(f"Retrieved {len(self.video_path_list['episodes'])} videos from"
                         f" {self.config['episode']['video_directory']}")

    def get_assistant_info(self):
        assistant_data = self.client.beta.assistants.retrieve(self.assistant.id).model_dump()
        object_list = ["id", "name", "description", "instructions", "model", "temperature", "tools"]
        return "\n".join([f"{obj}: {assistant_data[obj]}" for obj in object_list])

    def speak(self, *texts):
        # Basically a wrapper for printing out, can choose either doing TTS or not (for debugging)
        texts = " ".join(texts)
        self.logger.info(texts)
        if not self.text_IO:
            # Playing lip flap video while TTS
            self.video_player.play_video_non_blocking(self.video_path_list["lip_flap"], stop_when_finished=False)
            self.tts_client.text_to_speech(texts)
            self.video_player.pause_video()

    def get_response(self):
        if self.text_IO:
            response = input("Response: ")
            self.logger.info(f"Response: {response}")  # TODO: input and logger slows down?
            return response

        # Playing idle video while getting response
        self.video_player.play_video_non_blocking(self.video_path_list["idle"], stop_when_finished=False)
        response = self.stt_client.speech_to_text(self.config["stt_settings"]["max_recording_duration"])
        self.video_player.pause_video()

        if response:
            response = response[0]
        self.logger.info(f"Response: {response}")
        return response

    def ask_question(self, question):
        self.speak(question)
        answer = self.get_response()
        return answer

    def run_pre_test(self):
        self.assistant.converse("Now I will begin asking the child a few pretest questions, then you will give me"
                                "feedbacks based on the child's answer")
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

            feedback, accuracy = json_response[0]["feedback"], json_response[0]["accuracy"]
            pretest_eval["accuracy"] = accuracy
            pretest_eval["feedback"] = feedback

            self.speak(feedback)

    def adaptive_learning_loop(self):
        def generate_question(learning_history):
            # Template for generating question
            question_gen_msg = (f"Here's the child learning's history: {learning_history}, please "
                                f"generate a question based on the child's learning history and the story.")
            feedback_msg, json_tool_responses = self.assistant.converse(question_gen_msg,
                                                                        tools=[generate_question_function_json])
            return feedback_msg, json_tool_responses

        def generate_feedback(question, answer):
            # Template function to generate feedback from child's answer
            feedback_generation_msg = (f"The question is: '{question}'. Here's the child's answer: '{answer}'. "
                                       f"Generate feedback based on this answer.")
            feedback_msg, json_tool_responses = self.assistant.converse(feedback_generation_msg,
                                                                        tools=[generate_feedback_function_json])
            return feedback_msg, json_tool_responses

        def simplify_question(question):
            # Template to simplify question
            simplified_generation_msg = (f"The child couldn't answer the previous question, please give me a "
                                         f"simplified version of '{question}'")
            feedback_msg, json_tool_responses = self.assistant.converse(simplified_generation_msg,
                                                                        tools=[simplify_question_function_json])
            return feedback_msg, json_tool_responses

        def select_question(question_banks, q_level, learning_history):
            question_selection_msg = (f"Here's the child's learning history: {learning_history}. Select a {q_level} "
                                      f"question from the list of questions: {question_banks}.")
            feedback_msg, json_tool_responses = self.assistant.converse(question_selection_msg,
                                                                        tools=[select_question_function_json])
            return feedback_msg, json_tool_responses

        # Question level ranges: [0,2] inclusive
        question_levels = ["shallow", "intermediate", "deep"]
        episode_learning_history = []

        for idx, dialogue in enumerate(self.dialogues[self.start_video_idx - 1:self.end_video_idx - 1],
                                       start=self.start_video_idx - 1):  # 0-index
            dialogue_text, base_question = dialogue["text"], dialogue["question"]
            current_question_bank = self.question_banks[idx]
            self.logger.info("Video playing...")
            if self.text_IO:  # Debugging
                self.logger.info(dialogue_text[:200] + "...")
            else:
                self.video_player.play_video(self.video_path_list["episodes"][idx],
                                             max_duration=self.config["video_settings"]["max_playing_duration"],
                                             stop_when_finished=False)
            # Learning history for this part only
            current_learning_history = []  # learning history sent to OpenAI
            learning_history_log = []  # logging for everything

            # Story conversing
            question_generation_msg = (f"Here's the current story: {dialogue_text}. | \n"
                                       f"Through this story, we will assist the child in learning some new science "
                                       f"concepts.")
            self.assistant.converse(question_generation_msg)
            # Keeping the old framework, now we need a mock json_response object to represent the base question
            # (not generated but fixed)
            json_responses = [{
                "question": base_question,
                "level": "BASE",
                "rationale": "Base question to start out"
            }]

            # Ask maximum 3 questions
            max_questions = 3
            next_q_level = 1  # Base question is intermediate
            for q_id in range(max_questions):  # Question levels
                # Ask question, get child's answer, and generate feedback based on that answer
                generated_question = json_responses[0]["question"]
                # level and rationale only exists if generate question is called, not simplified
                # So if level and rationale doesn't exist in the json_responses, then reuse the old one
                level = json_responses[0]["level"] if "level" in json_responses[0] else "SIMPLIFIED"
                rationale = json_responses[0]["rationale"] if "rationale" in json_responses[
                    0] else "Simplifying previous question"
                child_answer = self.ask_question(generated_question)
                feedback, json_responses = generate_feedback(generated_question, child_answer)
                accuracy, evaluation, explanation, transition = [json_responses[0][obj] for obj in [
                    "accuracy", "evaluation", "explanation", "transition"]]
                self.logger.debug(f"Answer's accuracy: {accuracy}")

                learning_history_dict = {
                    "question": generated_question,
                    "level": level,
                    "rationale": rationale,
                    "answer": child_answer,
                    "accuracy": accuracy
                }
                # Append it to the learning history
                current_learning_history.append({k: v for k, v in learning_history_dict.items() if k in
                                                 ["question", "answer", "accuracy"]})
                learning_history_log.append(learning_history_dict)

                # Modify the difficulty for the next question
                last_q_level = next_q_level
                # Adjusting question difficulty (this only affects the state we are in e.g.
                # The actual question difficulty is adjusted by learning history.
                # If that doesn't work, we can use this one to specify the question level)
                next_q_level = min(next_q_level + 1, 2) if accuracy >= 0.9 else max(next_q_level - 1, 0)
                self.logger.debug(f"Last question level: {question_levels[last_q_level]}, "
                                  f"next question level: {question_levels[next_q_level]}")
                # If we have two rights (or wrongs) in a row, evaluation + exit
                # We also check for if it's currently the last questions
                if next_q_level == last_q_level == 0 or next_q_level == last_q_level == 2 or q_id == max_questions - 1:
                    self.speak(evaluation, explanation)
                    break
                # Simplifying previous asked question
                if next_q_level < last_q_level:     # wrong answer -> simplify
                    self.speak(evaluation, transition)
                    feedback, json_responses = simplify_question(generated_question)
                else:  # Harder question only rely on learning history
                    self.speak(evaluation, explanation, transition)
                    # feedback, json_responses = generate_question(current_learning_history)
                    feedback, json_responses = select_question(current_question_bank, question_levels[next_q_level],
                                                               current_learning_history)
            # Add question answer log
            episode_learning_history.append(learning_history_log)
        return episode_learning_history

    @utils.exception_logger
    def run_pretest_program(self):
        self.logger.info("Begin pretest")
        self.logger.info("=" * 50)
        self.speak("Let's begin with a pretest!")
        self.run_pre_test()
        self.speak("You're now done with the pretest!")
        # Now save the pretest learning results
        pretest_result_file = os.path.join(self.logging_root_dir, self.config["logging"]["pretest_result"])
        saving_fields = ["child_answer", "accuracy", "feedback"]
        learning_history = []
        for pretest_item in self.pretest:
            learning_history.append("\n".join([str(pretest_item[field]) for field in saving_fields]))
        # Learning result logging
        with open(pretest_result_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(learning_history))
        self.logger.info(f"Pretest response is saved to {pretest_result_file}.")
        # Saving raw convo file
        assistant_convo_file = os.path.join(self.logging_root_dir, self.config["logging"]["raw_assistant_conversation"])
        with open(assistant_convo_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.assistant.get_all_messages()))
        self.logger.info(f"Raw assistant conversation saved to {assistant_convo_file}.")
        self.video_player.stop_video()

    @utils.exception_logger
    def run_adaptive_learning_program(self):
        # Adaptive learning loop
        self.logger.info("Begin adaptive learning loop")
        self.logger.info("=" * 50)
        pre_adaptive_loop_msg = "Let's begin learning some science concepts presented in the story!"
        self.speak(pre_adaptive_loop_msg)
        self.assistant.converse(("Now you will be presented with a transcript from an "
                                 "animation made to help children learn science concepts. The dialogue will be "
                                 "divided into multiple parts, with each part focusing on a science concept. "
                                 "Your goal is to help the child learn science knowledge from the stories."))
        learning_history_log = self.adaptive_learning_loop()

        # Post adaptive loop message
        post_adaptive_loop_msg = "Congratulations! Hope you have fun learning something new today!"
        self.speak(post_adaptive_loop_msg)
        # Writing to a log file
        saving_fields = ["question", "level", "rationale", "answer", "accuracy"]
        learning_log_file = os.path.join(self.logging_root_dir, self.config["logging"]["learning_result"])
        with open(learning_log_file, "w", encoding="utf-8") as f:
            for learning_part in learning_history_log:
                for learning_question in learning_part:
                    f.write("\n".join([str(learning_question[field]) for field in saving_fields]))
                    f.write("\n-\n")
                f.write("=\n")
        self.logger.info(f"Learning history saved to {learning_log_file}.")
        # Writing raw OpenAI's conversation
        assistant_conversation_file = os.path.join(self.logging_root_dir,
                                                   self.config["logging"]["raw_assistant_conversation"])
        with open(assistant_conversation_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.assistant.get_all_messages()))
        self.logger.info(f"Raw assistant conversation saved to {assistant_conversation_file}.")
        self.video_player.stop_video()


if __name__ == "__main__":
    # Pretest flag
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--pretest", action="store_true", help="Running pretest program")
    argparser.add_argument("--mode", choices=["terminal", "interactive"], default="interactive")
    arguments = argparser.parse_args()
    # Main program loop
    adaptive_conversational_agent = AdaptiveCA(text_only=arguments.mode == "terminal")
    if arguments.pretest:
        adaptive_conversational_agent.run_pretest_program()
    else:
        adaptive_conversational_agent.run_adaptive_learning_program()
