import sys
import socket
import threading
import pyaudio
import wave
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar,
    QFileDialog, QMainWindow, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QUrl
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

MAGIC_HEADER = b'SVCA'  # Stands for Secure Voice Chat App

# ========== AES ENCRYPTION UTILS ==========

KEY = b'ThisIsASecretKey'  # 16-byte key for AES-128
BLOCK_SIZE = 16

def encrypt_audio(data):
    """Encrypts audio data using AES encryption."""
    try:
        cipher = AES.new(KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data, BLOCK_SIZE))
        return cipher.iv + ct_bytes
    except Exception as e:
        print(f"Error encrypting audio: {e}")
        return None

def decrypt_audio(data):
    """Decrypts audio data using AES decryption."""
    try:
        iv = data[:BLOCK_SIZE]
        ct = data[BLOCK_SIZE:]
        cipher = AES.new(KEY, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), BLOCK_SIZE)
        return pt
    except Exception as e:
        print(f"Error decrypting audio: {e}")
        return None

# ========== MEDIA PLAYER WINDOW ==========

class AudioPlayerWindow(QMainWindow):
    """A simple window to play decrypted audio files."""
    def __init__(self, audio_file):
        super().__init__()
        self.setWindowTitle("🎵 Decrypted Audio Player")
        self.setGeometry(100, 100, 500, 120)

        self.player = QMediaPlayer()
        media_content = QMediaContent(QUrl.fromLocalFile(audio_file))
        self.player.setMedia(media_content)

        play_btn = QPushButton("▶️ Play")
        pause_btn = QPushButton("⏸ Pause")
        stop_btn = QPushButton("⏹ Stop")

        play_btn.clicked.connect(self.player.play)
        pause_btn.clicked.connect(self.player.pause)
        stop_btn.clicked.connect(self.player.stop)

        layout = QHBoxLayout()
        layout.addWidget(play_btn)
        layout.addWidget(pause_btn)
        layout.addWidget(stop_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

# ========== MAIN GUI CLASS ==========

class VoiceApp(QWidget):
    """The main application window for the Secure Voice Chat."""
    def __init__(self):
        super().__init__()
        self.audio = pyaudio.PyAudio()
        self.saved_frames = []
        self.saving_enabled = False
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface."""
        self.setWindowTitle("🔒 Secure Voice Chat")
        self.setFixedSize(600, 500)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 16px;
            }
            QPushButton {
                background-color: #1e1e1e;
                border: 2px solid #03dac5;
                border-radius: 10px;
                padding: 14px;
                color: #ffffff;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #03dac5;
                color: #000000;
            }
            QProgressBar {
                border: 2px solid #03dac5;
                border-radius: 5px;
                background-color: #2b2b2b;
                text-align: center;
                color: #ffffff;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #03dac5;
                width: 20px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(18)
        layout.setContentsMargins(40, 40, 40, 40)

        self.status = QLabel("🎙️ Choose a mode:")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        self.conn_status = QLabel("🔴 Not Connected")
        self.conn_status.setAlignment(Qt.AlignCenter)
        self.conn_status.setStyleSheet("color: red;")
        layout.addWidget(self.conn_status)

        self.btn_send = QPushButton("🔊 Start Sending Audio")
        self.btn_send.clicked.connect(self.start_sending)
        layout.addWidget(self.btn_send)

        self.btn_recv = QPushButton("🎧 Start Receiving Audio")
        self.btn_recv.clicked.connect(self.start_receiving)
        layout.addWidget(self.btn_recv)

        self.btn_toggle_save = QPushButton("💾 Enable Audio Saving")
        self.btn_toggle_save.clicked.connect(self.toggle_audio_saving)
        layout.addWidget(self.btn_toggle_save)

        self.btn_upload_encrypted = QPushButton("📂 Upload Encrypted Audio to Play")
        self.btn_upload_encrypted.clicked.connect(self.upload_and_play)
        layout.addWidget(self.btn_upload_encrypted)

        self.btn_close = QPushButton("❌ Close Application")
        self.btn_close.clicked.connect(QApplication.instance().quit)
        layout.addWidget(self.btn_close)

        self.visualizer = QProgressBar(self)
        self.visualizer.setRange(0, 100)
        layout.addWidget(self.visualizer)

        self.setLayout(layout)
        QTimer.singleShot(100, self.animate_ui)

    def animate_ui(self):
        """Animates the UI elements for a smooth appearance."""
        self.anim_group = QSequentialAnimationGroup(self)
        widgets = [self.status, self.conn_status, self.btn_send, self.btn_recv,
                   self.btn_toggle_save, self.btn_upload_encrypted, self.btn_close, self.visualizer]

        for widget in widgets:
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(250)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            self.anim_group.addAnimation(anim)

        self.anim_group.start()

        self.pulse_direction = 1
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.pulse_visualizer)
        self.pulse_timer.start(100)

    def pulse_visualizer(self):
        """Pulses the visualizer to indicate activity."""
        current = self.visualizer.value()
        next_value = current + (5 * self.pulse_direction)
        if next_value >= 100 or next_value <= 0:
            self.pulse_direction *= -1
        self.visualizer.setValue(next_value)

    def update_visualizer(self, level):
        """Updates the visualizer with a given level."""
        self.visualizer.setValue(level)

    def toggle_audio_saving(self):
        """Toggles audio saving functionality."""
        self.saving_enabled = not self.saving_enabled
        if self.saving_enabled:
            self.saved_frames = []
            self.btn_toggle_save.setText("✅ Saving Enabled")
        else:
            self.save_audio_to_file()
            self.btn_toggle_save.setText("💾 Enable Audio Saving")

    def save_audio_to_file(self):
        """Saves the recorded audio frames to an encrypted file."""
        if not self.saved_frames:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Encrypted Audio", "", "Encrypted Audio (*.enc)")
        if not path:
            return

        raw_audio = b''.join(self.saved_frames)
        encrypted_audio = encrypt_audio(raw_audio)

        if encrypted_audio:
            try:
                with open(path, 'wb') as f:
                    f.write(MAGIC_HEADER + encrypted_audio)
                self.status.setText(f"✅ Encrypted audio saved to:\n{path}")
            except Exception as e:
                print("❌ Error saving file:", e)
                self.status.setText("❌ Failed to save file.")
        else:
            self.status.setText("❌ Encryption failed, audio not saved.")

    def upload_and_play(self):
        """Uploads an encrypted audio file, decrypts it, and plays it."""
        path, _ = QFileDialog.getOpenFileName(self, "Select Encrypted Audio", "", "Encrypted Audio (*.enc)")
        if not path:
            return

        try:
            with open(path, 'rb') as f:
                data = f.read()

            if not data.startswith(MAGIC_HEADER):
                raise ValueError("Not a valid encrypted file from this app.")

            encrypted = data[len(MAGIC_HEADER):]
            decrypted = decrypt_audio(encrypted)

            if decrypted:
                temp_path = "decrypted_temp.wav"
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(44100)
                    wf.writeframes(decrypted)

                self.player_window = AudioPlayerWindow(temp_path)
                self.player_window.show()
            else:
                self.status.setText("❌ Decryption failed.")
        except Exception as e:
            self.status.setText("❌ Failed to decrypt or play file.")
            print("❌ Decryption failed:", e)

    def start_sending(self):
        """Starts the audio sending thread."""
        threading.Thread(target=self.send_audio, daemon=True).start()
        self.status.setText("🔐 Sending encrypted audio...")
        self.conn_status.setText("🟢 Connected to Receiver")
        self.conn_status.setStyleSheet("color: green;")

    def start_receiving(self):
        """Starts the audio receiving thread."""
        threading.Thread(target=self.receive_audio, daemon=True).start()
        self.status.setText("🔓 Receiving and decrypting audio...")
        self.conn_status.setText("🟢 Connected to Sender")
        self.conn_status.setStyleSheet("color: green;")

    def send_audio(self):
        """Sends audio data over the network, encrypting it before sending."""
        CHUNK = 1024
        RATE = 44100
        stream = self.audio.open(format=pyaudio.paInt16, channels=1,
                                 rate=RATE, input=True, frames_per_buffer=CHUNK)
        client = socket.socket()
        try:
            client.connect(('localhost', 9999))
            print("✅ Successfully connected to receiver.")
        except ConnectionRefusedError:
            self.status.setText("❌ Receiver not running!")
            self.conn_status.setText("🔴 Disconnected")
            self.conn_status.setStyleSheet("color: red;")
            return

        try:
            while True:
                data = stream.read(CHUNK)
                if self.saving_enabled:
                    self.saved_frames.append(data)
                encrypted_data = encrypt_audio(data)

                if encrypted_data:
                    try:
                        client.sendall(len(encrypted_data).to_bytes(4, 'big'))
                        client.sendall(encrypted_data)
                        self.update_visualizer(100)  # Fully active visualizer during streaming
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                        break
        finally:
            stream.stop_stream()
            stream.close()

    def receive_audio(self):
        """Receives audio data over the network, decrypting it after receiving."""
        server = socket.socket()
        server.bind(('localhost', 9999))
        server.listen(1)
        print("Waiting for sender to connect...")

        client, _ = server.accept()
        print("✅ Connection established with sender.")

        try:
            while True:
                try:
                    length_data = client.recv(4)
                    if not length_data:
                        break

                    length = int.from_bytes(length_data, 'big')
                    encrypted_audio = b""
                    while len(encrypted_audio) < length:
                        chunk = client.recv(length - len(encrypted_audio))
                        if not chunk:
                            break
                        encrypted_audio += chunk

                    decrypted_audio = decrypt_audio(encrypted_audio)
                    if decrypted_audio:
                        self.update_visualizer(50)  # Moderate activity during receiving
                    else:
                        self.status.setText("❌ Failed to decrypt audio.")
                        break
                except Exception as e:
                    print(f"Error receiving audio: {e}")
                    break
        finally:
            client.close()
            server.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VoiceApp()
    ex.show()
    sys.exit(app.exec_())
