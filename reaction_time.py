import random
import time
import wave
import pyaudio
import threading
import keyboard
import pandas as pd
import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime

# 生成唯一的四位数ID
def generate_id(tester_id, group_id):
    return f"{tester_id:02d}{group_id:02d}"

# 播放WAV格式的语音提示音
def play_audio(file_path, stop_event):
    print("Starting audio playback")
    chunk = 1024
    wf = wave.open(file_path, 'rb')
    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    data = wf.readframes(chunk)
    while data and not stop_event.is_set():
        stream.write(data)
        data = wf.readframes(chunk)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Audio playback finished")

# 等待随机时间并重复播放提示音
def wait_and_play_audio(file_path, stop_event):
    wait_time = 60  #单位为秒
    print(f"Waiting for {wait_time // 60} minutes before playing audio")

    for _ in range(wait_time):
        if stop_event.is_set():
            return
        time.sleep(1)

    while not stop_event.is_set():
        play_audio(file_path, stop_event)
        if stop_event.is_set():
            break

# 记录用户按空格键的时间
def record_response(app, tester_id, group_id, file_path, stop_event, on_complete, results):
    user_id = generate_id(tester_id, group_id)
    start_time = None
    audio_thread = None

    def on_space(event):
        nonlocal start_time, audio_thread
        if start_time is None:
            start_time = time.time()
            print(f"Start time recorded for user {user_id}")
            app.space_prompt_label.config(text="Please press the space key to stop")
            stop_event.clear()
            audio_thread = threading.Thread(target=wait_and_play_audio, args=(file_path, stop_event))
            audio_thread.start()
        else:
            waitting_time = 60
            reaction_time = time.time() - start_time- waitting_time
            print(f"User ID: {user_id}, Reaction Time: {reaction_time} seconds")
            results.append((user_id, reaction_time))
            stop_event.set()
            if audio_thread:
                audio_thread.join()
            keyboard.unhook_all()
            on_complete()

    keyboard.on_press_key("space", on_space)

# 保存到Excel文件
def save_to_excel(results, file_path):
    data = {
        'User ID': [user_id for user_id, _ in results],
        'Reaction Time (seconds)': [reaction_time for _, reaction_time in results]
    }

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)

# GUI界面
class ReactionTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reaction Time Test")

        self.main_frame = ttk.Frame(root, padding="10 10 10 10")
        self.main_frame.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.label = ttk.Label(self.main_frame, text="Please enter the number of testers:")
        self.label.grid(column=1, row=1, sticky=tk.W)

        self.entry = ttk.Entry(self.main_frame, width=7)
        self.entry.grid(column=2, row=1, sticky=(tk.W, tk.E))

        self.wav_path_button = ttk.Button(self.main_frame, text="Select WAV file", command=self.select_wav_file)
        self.wav_path_button.grid(column=1, row=2, sticky=tk.W)

        self.start_button = ttk.Button(self.main_frame, text="Start Test", command=self.on_start, state=tk.DISABLED)
        self.start_button.grid(column=2, row=2, sticky=tk.E)

        self.user_id_label = ttk.Label(self.main_frame, text="")
        self.user_id_label.grid(column=1, row=3, columnspan=2, sticky=(tk.W, tk.E))

        self.space_prompt_label = ttk.Label(self.main_frame, text="", foreground="red")
        self.space_prompt_label.grid(column=1, row=4, columnspan=2, sticky=(tk.W, tk.E))

        for child in self.main_frame.winfo_children():
            child.grid_configure(padx=5, pady=5)

        self.stop_event = threading.Event()
        self.audio_thread = None
        self.num_testers = 0
        self.tester_id = 1
        self.file_path = ""
        self.results = []

    def select_wav_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if self.file_path:
            self.start_button.config(state=tk.NORMAL)

    def on_start(self):
        try:
            self.num_testers = int(self.entry.get())
            if self.num_testers <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a positive integer.")
            return

        self.tester_id = 1
        self.results = []
        self.entry.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.start_test()

    def start_test(self):
        if self.tester_id > self.num_testers:
            self.on_record()
            return

        self.stop_event.clear()
        self.group_id = random.choice([1, 2, 3, 4])
        self.user_id_label.config(text=f"Current Tester ID: {generate_id(self.tester_id, self.group_id)}")
        self.space_prompt_label.config(text="Please press the space key to start")
        record_response(self, self.tester_id, self.group_id, self.file_path, self.stop_event, self.on_complete, self.results)

    def on_stop(self):
        if self.audio_thread and self.audio_thread.is_alive():
            print("Stopping audio thread")
            self.stop_event.set()
            print("Waiting for audio thread to finish")
            self.audio_thread.join()
            print("Audio thread has finished")
        self.space_prompt_label.config(text="")
        keyboard.unhook_all()

    def on_record(self):
        print("Recording results")
        self.on_stop()
        if self.results:
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                     filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
            if file_path:
                save_to_excel(self.results, file_path)
                messagebox.showinfo("Save Successful", f"Results have been saved to {file_path}")
                self.results = []
        self.entry.config(state=tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.user_id_label.config(text="")
        self.space_prompt_label.config(text="")

    def on_complete(self):
        self.space_prompt_label.config(text="")
        self.tester_id += 1
        self.start_test()

def main():
    root = tk.Tk()
    app = ReactionTestApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
