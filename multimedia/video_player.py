import vlc
import time


class VideoPlayer:
    def __init__(self, full_screen=False):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        if full_screen:
            self.player.toggle_fullscren()

    def play_video(self, video_path, max_duration=None):
        self.player.set_mrl(video_path)
        self.player.play()

        time.sleep(0.1)
        playing_states = {1, 2, 3, 4}
        duration = self.player.get_length() / 1000

        print(f"Playing {video_path} for {int(duration // 60)}m{int(duration % 60)}s")
        max_duration = max_duration if max_duration is not None else float("inf")
        start_time = time.time()
        while True:
            time.sleep(1)
            state = self.player.get_state()
            if state not in playing_states or time.time() - start_time > max_duration:
                break

        self.player.stop()


if __name__ == "__main__":
    video_player = VideoPlayer()
    video_player.play_video("../videos/02_episode.mp4", 5)
