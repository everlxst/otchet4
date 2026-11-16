import io
import math
import queue
import random
import struct
import sys
import threading
import wave

import customtkinter as ctk
import pyttsx3

try:
    import pygame
except ImportError:
    pygame = None


class SpeechEngine:
    """Последовательно произносит фразы в отдельном потоке."""

    def __init__(self):
        self.requests = queue.Queue()
        self.completed = queue.Queue()

        self.thread = threading.Thread(
            target=self._worker,
            daemon=True,
        )
        self.thread.start()

    def say(self, text, callback=None):
        if text:
            self.requests.put((text, callback))

    def _worker(self):
        pythoncom = None
        voice = None
        engine = None

        if sys.platform == "win32":
            try:
                import pythoncom as _pythoncom
                import win32com.client

                pythoncom = _pythoncom
                pythoncom.CoInitialize()

                # SAPI создаётся и используется в одном потоке.
                voice = win32com.client.Dispatch("SAPI.SpVoice")

                # Если установлен русский голос, выбираем его.
                try:
                    voices = voice.GetVoices()
                    for index in range(voices.Count):
                        candidate = voices.Item(index)
                        description = candidate.GetDescription().lower()

                        if "russian" in description or "рус" in description:
                            voice.Voice = candidate
                            break
                except Exception:
                    pass

            except Exception as error:
                print(f"SAPI5 недоступен, попробуем pyttsx3: {error}")
                voice = None

        if voice is None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 130)

                for candidate in engine.getProperty("voices"):
                    language = candidate.languages[0] if candidate.languages else ""
                    if isinstance(language, bytes):
                        language = language.decode("utf-8", errors="ignore")

                    details = f"{language} {candidate.name}".lower()
                    if "ru" in details or "russian" in details or "рус" in details:
                        engine.setProperty("voice", candidate.id)
                        break

            except Exception as error:
                print(f"Голосовой движок недоступен: {error}")
                engine = None

        while True:
            request = self.requests.get()

            if request is None:
                break

            text, callback = request

            try:
                if voice is not None:
                    # Синхронный вызов внутри рабочего потока.
                    voice.Speak(text)
                elif engine is not None:
                    engine.say(text)
                    engine.runAndWait()
                else:
                    print("Озвучка недоступна. Текст:", text)
            except Exception as error:
                print(f"Ошибка озвучивания: {error}")
            finally:
                if callback:
                    self.completed.put(callback)

        if pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


DATABASE = [
    {
        "name": "Кошка",
        "emoji": "🐱",
        "sound": "Мяу! Мяу!",
        "hint": "Любит молоко и ловит мышей.",
    },
    {
        "name": "Собака",
        "emoji": "🐶",
        "sound": "Гав! Гав!",
        "hint": "Верный друг, охраняет дом.",
    },
    {
        "name": "Корова",
        "emoji": "🐮",
        "sound": "Му-у-у!",
        "hint": "Даёт вкусное молоко.",
    },
    {
        "name": "Лев",
        "emoji": "🦁",
        "sound": "Ррррр!",
        "hint": "Царь зверей с большой гривой.",
    },
    {
        "name": "Петух",
        "emoji": "🐓",
        "sound": "Ку-ка-ре-ку!",
        "hint": "Просыпается самым первым утром.",
    },
    {
        "name": "Лягушка",
        "emoji": "🐸",
        "sound": "Ква! Ква!",
        "hint": "Зелёная прыгунья, которая живёт у воды.",
    },
    {
        "name": "Барабан",
        "emoji": "🥁",
        "sound": "Бум! Бум! Бам!",
        "hint": "По нему стучат палочками.",
    },
    {
        "name": "Колокольчик",
        "emoji": "🔔",
        "sound": "Динь! Дон!",
        "hint": "Весело звенит, если его потрясти.",
    },
]


class SoundGameApp(ctk.CTk):
    CARD_COLORS = [
        ("#E5F7FF", "#B9E9FF"),
        ("#FFF0E8", "#FFD5C2"),
        ("#F0EAFE", "#D8CBFF"),
        ("#E8F8EC", "#C5EED0"),
    ]

    def __init__(self):
        super().__init__()

        self.title("Угадай звук!")
        self.geometry("720x790")
        self.minsize(650, 700)
        self.configure(fg_color="#F2F5FF")

        self.speaker = SpeechEngine()

        self.score = 0
        self.total = 0
        self.streak = 0
        self.round_number = 0
        self.current_item = None
        self.previous_item = None
        self.answered = False
        self.card_buttons = []
        self.victory_sound = None

        self.init_victory_sound()
        self.setup_ui()

        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.after(100, self.process_speech_callbacks)
        self.next_round()

    def init_victory_sound(self):
        """Создаёт мелодию победы, если доступен pygame."""
        if pygame is None:
            print("pygame не установлен: будет произнесено «Ура! Правильно!»")
            return

        try:
            pygame.mixer.init(
                frequency=22050,
                size=-16,
                channels=1,
                buffer=512,
            )
            self.victory_sound = pygame.mixer.Sound(
                file=io.BytesIO(self.create_victory_tune())
            )
        except Exception as error:
            print(f"Не удалось включить мелодию победы: {error}")
            self.victory_sound = None

    @staticmethod
    def create_victory_tune():
        """Генерирует короткую мелодию победы в формате WAV."""
        sample_rate = 22050
        frequencies = [523, 659, 784, 1047]
        note_duration = 0.14
        pause_duration = 0.025
        frames = []

        for frequency in frequencies:
            sample_count = int(sample_rate * note_duration)

            for index in range(sample_count):
                envelope = min(
                    1.0,
                    index / 300,
                    (sample_count - index) / 500,
                )
                value = int(
                    11000
                    * envelope
                    * math.sin(
                        2 * math.pi * frequency * index / sample_rate
                    )
                )
                frames.append(struct.pack("<h", value))

            pause_samples = int(sample_rate * pause_duration)
            frames.extend([b"\x00\x00"] * pause_samples)

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frames))

        return buffer.getvalue()

    def play_victory_sound(self):
        if self.victory_sound is not None:
            try:
                self.victory_sound.play()
                return
            except Exception as error:
                print(f"Не удалось проиграть мелодию победы: {error}")

        self.speaker.say("Ура! Правильно!")

    def process_speech_callbacks(self):
        """Выполняет завершённые действия озвучки в основном потоке интерфейса."""
        try:
            while True:
                callback = self.speaker.completed.get_nowait()
                callback()
        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self.process_speech_callbacks)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.main_frame.pack(
            fill="both",
            expand=True,
            padx=24,
            pady=20,
        )

        self.header = ctk.CTkFrame(
            self.main_frame,
            fg_color="#6C63FF",
            corner_radius=26,
            height=112,
        )
        self.header.pack(fill="x", pady=(0, 14))
        self.header.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Угадай звук!",
            font=ctk.CTkFont(
                family="Arial",
                size=30,
                weight="bold",
            ),
            text_color="#FFFFFF",
        )
        self.title_label.pack(
            side="left",
            padx=(24, 0),
            pady=(18, 0),
        )

        self.subtitle_label = ctk.CTkLabel(
            self.header,
            text="Слушай внимательно и выбирай карточку ✨",
            font=ctk.CTkFont(family="Arial", size=15),
            text_color="#EAE8FF",
        )
        self.subtitle_label.pack(
            side="left",
            padx=18,
            pady=(27, 0),
        )

        self.mascot_label = ctk.CTkLabel(
            self.header,
            text="🎧",
            font=ctk.CTkFont(family="Arial", size=46),
            text_color="#FFFFFF",
        )
        self.mascot_label.pack(side="right", padx=24)

        self.stats_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#E6E9F5",
            height=60,
        )
        self.stats_frame.pack(fill="x", pady=(0, 14))
        self.stats_frame.pack_propagate(False)

        self.score_label = ctk.CTkLabel(
            self.stats_frame,
            text="⭐ Очки: 0 из 0",
            font=ctk.CTkFont(
                family="Arial",
                size=17,
                weight="bold",
            ),
            text_color="#26324A",
        )
        self.score_label.pack(side="left", padx=20)

        self.streak_label = ctk.CTkLabel(
            self.stats_frame,
            text="🔥 Серия: 0",
            font=ctk.CTkFont(
                family="Arial",
                size=17,
                weight="bold",
            ),
            text_color="#F07B3F",
        )
        self.streak_label.pack(side="right", padx=20)

        self.sound_btn = ctk.CTkButton(
            self.main_frame,
            text="▶  Послушать звук ещё раз",
            font=ctk.CTkFont(
                family="Arial",
                size=19,
                weight="bold",
            ),
            height=60,
            corner_radius=20,
            fg_color="#FF9233",
            hover_color="#E67E22",
            text_color="#FFFFFF",
            command=self.play_sound,
        )
        self.sound_btn.pack(fill="x", padx=10, pady=(4, 8))

        self.feedback_label = ctk.CTkLabel(
            self.main_frame,
            text="Слушай звук и нажми на подходящую карточку",
            font=ctk.CTkFont(
                family="Arial",
                size=16,
                weight="bold",
            ),
            wraplength=600,
            text_color="#58647A",
            height=46,
        )
        self.feedback_label.pack(fill="x", pady=6)

        self.grid_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
        )
        self.grid_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=4,
        )

        for row in range(2):
            self.grid_frame.rowconfigure(row, weight=1, uniform="row")

        for column in range(2):
            self.grid_frame.columnconfigure(
                column,
                weight=1,
                uniform="column",
            )

        self.bottom_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
        )
        self.bottom_frame.pack(fill="x", pady=(10, 0))

        self.hint_btn = ctk.CTkButton(
            self.bottom_frame,
            text="💡 Подсказка",
            font=ctk.CTkFont(
                family="Arial",
                size=16,
                weight="bold",
            ),
            fg_color="#A77BFF",
            hover_color="#895BE8",
            text_color="#FFFFFF",
            height=48,
            corner_radius=15,
            command=self.show_hint,
        )
        self.hint_btn.pack(
            side="left",
            expand=True,
            fill="x",
            padx=(0, 8),
        )

        self.next_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Дальше ➜",
            font=ctk.CTkFont(
                family="Arial",
                size=16,
                weight="bold",
            ),
            fg_color="#42C77A",
            hover_color="#2EAA62",
            text_color="#FFFFFF",
            height=48,
            corner_radius=15,
            command=self.next_round,
        )

    def play_sound(self):
        """Повторно озвучивает звук текущего раунда."""
        if not self.current_item:
            return

        self.sound_btn.configure(
            text="🔊 Сейчас звучит...",
            state="disabled",
        )

        self.speaker.say(
            self.current_item["sound"],
            callback=self.restore_sound_button,
        )

    def restore_sound_button(self):
        if self.winfo_exists():
            self.sound_btn.configure(
                text="▶  Послушать звук ещё раз",
                state="normal",
            )

    def next_round(self):
        self.answered = False
        self.round_number += 1

        self.feedback_label.configure(
            text=f"Раунд {self.round_number} — слушай и выбирай!",
            text_color="#58647A",
        )
        self.next_btn.pack_forget()
        self.hint_btn.configure(state="normal")
        self.sound_btn.configure(
            text="▶  Послушать звук ещё раз",
            state="normal",
        )

        choices = [item for item in DATABASE if item != self.previous_item]
        self.current_item = random.choice(choices)
        self.previous_item = self.current_item

        options = [self.current_item]
        while len(options) < 4:
            candidate = random.choice(DATABASE)
            if candidate not in options:
                options.append(candidate)

        random.shuffle(options)

        for button in self.card_buttons:
            button.destroy()
        self.card_buttons.clear()

        for index, item in enumerate(options):
            row = index // 2
            column = index % 2
            card_color, hover_color = self.CARD_COLORS[index]

            card = ctk.CTkButton(
                self.grid_frame,
                text=f"{item['emoji']}\n{item['name']}",
                font=ctk.CTkFont(
                    family="Arial",
                    size=23,
                    weight="bold",
                ),
                fg_color=card_color,
                hover_color=hover_color,
                text_color="#26324A",
                corner_radius=22,
                border_width=3,
                border_color="#FFFFFF",
                command=lambda selected=item, card_index=index: self.check_answer(
                    selected,
                    card_index,
                ),
            )
            card.grid(
                row=row,
                column=column,
                padx=9,
                pady=9,
                sticky="nsew",
            )
            self.card_buttons.append(card)

        # Автоматически произносим звук после появления карточек.
        self.after(800, self.play_sound)

    def check_answer(self, selected_item, clicked_index):
        if self.answered:
            return

        self.answered = True
        self.total += 1
        self.hint_btn.configure(state="disabled")
        self.next_btn.pack(
            side="right",
            expand=True,
            fill="x",
            padx=(8, 0),
        )

        if selected_item == self.current_item:
            self.score += 1
            self.streak += 1

            self.feedback_label.configure(
                text=random.choice([
                    "Правильно! Ты отлично угадал(а)! 🎉",
                    "Ура! Совершенно верно! 🌟",
                    "Здорово! Продолжай в том же духе! 🥳",
                ]),
                text_color="#21864A",
            )

            self.card_buttons[clicked_index].configure(
                fg_color="#CFF3D9",
                hover_color="#CFF3D9",
                border_color="#42C77A",
                text_color="#17683A",
            )
            self.play_victory_sound()

        else:
            self.streak = 0

            self.feedback_label.configure(
                text=(
                    f"Почти! Это {selected_item['name']}. "
                    f"Правильный ответ — {self.current_item['name']}!"
                ),
                text_color="#D34E5A",
            )

            self.card_buttons[clicked_index].configure(
                fg_color="#FFE0E3",
                hover_color="#FFE0E3",
                border_color="#F06B76",
                text_color="#A92F3B",
            )

            for button in self.card_buttons:
                if self.current_item["name"] in button.cget("text"):
                    button.configure(
                        fg_color="#CFF3D9",
                        hover_color="#CFF3D9",
                        border_color="#42C77A",
                        text_color="#17683A",
                    )

            self.speaker.say("Попробуй ещё раз!")

        self.score_label.configure(
            text=f"⭐ Очки: {self.score} из {self.total}"
        )
        self.streak_label.configure(
            text=f"🔥 Серия: {self.streak}"
        )

    def show_hint(self):
        if not self.answered and self.current_item:
            hint = self.current_item["hint"]
            self.feedback_label.configure(
                text=f"💡 Подсказка: {hint}",
                text_color="#7651C9",
            )
            self.speaker.say(hint)

    def close_app(self):
        self.speaker.requests.put(None)

        if pygame is not None:
            try:
                pygame.mixer.quit()
            except Exception:
                pass

        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = SoundGameApp()
    app.mainloop()