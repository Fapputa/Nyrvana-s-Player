import sys
import os
import json
import subprocess
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QMovie
import yt_dlp

# === Lecture de la configuration ===
def load_config(path="config.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# === Bouton animé ===
class AnimatedButton(QPushButton):
    def __init__(self, text, config):
        super().__init__(text)
        self.config = config
        self.animations_enabled = config.get("animations", {}).get("enabled", True)
        self.hover_enabled = config.get("animations", {}).get("hover_enabled", True)
        self.click_enabled = config.get("animations", {}).get("click_enabled", True)
        self.duration = config.get("animations", {}).get("duration", 150)
        self.hover_scale = config.get("animations", {}).get("hover_scale", 1.1)
        self.click_scale = config.get("animations", {}).get("click_scale", 0.95)
        
        self._scale = 1.0
        self.scale_animation = QPropertyAnimation(self, b"scale")
        self.scale_animation.setDuration(self.duration)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def get_scale(self):
        return self._scale
    
    def set_scale(self, scale):
        self._scale = scale
        self.setStyleSheet(self.styleSheet() + f"transform: scale({scale});")
        
    scale = pyqtProperty(float, get_scale, set_scale)
    
    def enterEvent(self, event):
        if self.animations_enabled and self.hover_enabled:
            self.scale_animation.stop()
            self.scale_animation.setStartValue(self._scale)
            self.scale_animation.setEndValue(self.hover_scale)
            self.scale_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if self.animations_enabled and self.hover_enabled:
            self.scale_animation.stop()
            self.scale_animation.setStartValue(self._scale)
            self.scale_animation.setEndValue(1.0)
            self.scale_animation.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if self.animations_enabled and self.click_enabled:
            self.scale_animation.stop()
            self.scale_animation.setStartValue(self._scale)
            self.scale_animation.setEndValue(self.click_scale)
            self.scale_animation.start()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.animations_enabled and self.click_enabled:
            self.scale_animation.stop()
            self.scale_animation.setStartValue(self._scale)
            self.scale_animation.setEndValue(self.hover_scale if self.underMouse() else 1.0)
            self.scale_animation.start()
        super().mouseReleaseEvent(event)

# === Thread de téléchargement et conversion ===
class DownloadThread(QThread):
    started_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, query: str, output_dir='assets/music'):
        super().__init__()
        self.query = query
        self.output_dir = output_dir

    def run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'quiet': False,
                'noplaylist': True,
                'nocheckcertificate': True,
                'extractor_args': {'youtube': {'skip': ['dash', 'hls']}},
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate'
                }
            }

            self.started_signal.emit("Recherche...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{self.query}", download=True)
                video_info = info['entries'][0] if 'entries' in info else info
                path_mp4 = ydl.prepare_filename(video_info)
                base_name = os.path.splitext(os.path.basename(path_mp4))[0]

            if not os.path.exists(path_mp4):
                self.error_signal.emit("Fichier introuvable")
                return

            self.started_signal.emit("Conversion...")
            
            convert_path = "./core/convert"
            if not os.path.exists(convert_path):
                self.error_signal.emit(f"Programme introuvable : {convert_path}")
                return
            
            result = subprocess.run([convert_path, path_mp4], 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode != 0:
                self.error_signal.emit(f"Erreur : {result.stderr}")
                return

            core_dir = "./core"
            files_moved = []
            
            for ext in ['.mp3', '.gif']:
                file_name = f"{base_name}{ext}"
                src = os.path.join(core_dir, file_name)
                dst = os.path.join(self.output_dir, file_name)
                
                if os.path.exists(src):
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(src, dst)
                    files_moved.append(file_name)

            if os.path.exists(path_mp4):
                os.remove(path_mp4)

            if files_moved:
                self.finished_signal.emit("Terminé")
            else:
                self.error_signal.emit("Aucun fichier généré")

        except yt_dlp.utils.DownloadError as e:
            self.error_signal.emit(f"Erreur : {str(e)}")
        except Exception as e:
            self.error_signal.emit(f"Erreur : {str(e)}")

# === Interface Principale ===
class MP3DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.setWindowTitle("Downloader")
        win_cfg = self.config.get("window", {})
        self.setFixedSize(win_cfg.get("width", 400), win_cfg.get("height", 180))
        self.setStyleSheet(f"background-color: {win_cfg.get('background_color', '#434343')}; color: white;")
        
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Bouton fermeture avec style du JSON
        close_cfg = self.config.get("buttons", {}).get("close", {})
        close_btn = AnimatedButton("✕", self.config)
        close_w, close_h = close_cfg.get("size", [30, 30])
        close_btn.setFixedSize(close_w, close_h)
        
        border_radius = 0 if close_cfg.get("shape") == "square" else close_w // 2
        close_btn.setStyleSheet(f"""
            background-color: {close_cfg.get('color', '#5e1e14')};
            color: {close_cfg.get('text_color', '#000000')};
            border: {close_cfg.get('border_width', 0)}px solid {close_cfg.get('border_color', '#000000')};
            border-radius: {border_radius}px;
            font-weight: bold;
        """)
        close_btn.clicked.connect(self.close)
        
        close_layout = QVBoxLayout()
        close_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(close_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Titre ou URL...")
        self.search_input.setStyleSheet(f"""
            padding: 10px;
            border-radius: 5px;
            background: #333;
            color: white;
            font-size: 13px;
            font-family: {self.config.get('buttons', {}).get('font_family', 'Arial')};
        """)
        self.search_input.returnPressed.connect(self.start_download)
        layout.addWidget(self.search_input)

        # Bouton download avec style play du JSON
        play_cfg = self.config.get("buttons", {}).get("play", {})
        self.search_button = AnimatedButton("Download", self.config)
        play_w, play_h = play_cfg.get("size", [35, 35])
        
        border_radius = 0 if play_cfg.get("shape") == "square" else play_w // 4
        self.search_button.setStyleSheet(f"""
            padding: 10px;
            background-color: {play_cfg.get('color', '#955151')};
            color: {play_cfg.get('text_color', '#FFFFFF')};
            border: {play_cfg.get('border_width', 0)}px solid {play_cfg.get('border_color', '#000000')};
            border-radius: {border_radius}px;
            font-weight: bold;
            font-size: 13px;
            font-family: {self.config.get('buttons', {}).get('font_family', 'Arial')};
        """)
        self.search_button.clicked.connect(self.start_download)
        layout.addWidget(self.search_button)

        self.status_label = QLabel("Prêt")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            padding: 5px;
            font-size: 11px;
            font-family: {self.config.get('buttons', {}).get('font_family', 'Arial')};
        """)
        layout.addWidget(self.status_label)

        # GIF de chargement
        gif_path = "assets/gifs/load.gif"
        if os.path.exists(gif_path):
            self.loading_gif = QMovie(gif_path)
            self.loading_label = QLabel()
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.loading_label.setMovie(self.loading_gif)
            self.loading_label.setVisible(False)
            layout.addWidget(self.loading_label)
        else:
            self.loading_label = None

        self.setLayout(layout)

    def start_download(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un titre ou URL")
            return

        self.search_button.setEnabled(False)
        if self.loading_label:
            self.loading_label.setVisible(True)
            self.loading_gif.start()

        self.thread = DownloadThread(query)
        self.thread.started_signal.connect(self.status_label.setText)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.error_signal.connect(self.on_error)
        self.thread.start()

    def on_finished(self, message):
        self.status_label.setText(message)
        self.search_button.setEnabled(True)
        if self.loading_label:
            self.loading_label.setVisible(False)
            self.loading_gif.stop()
        QMessageBox.information(self, "Succès", message)

    def on_error(self, error_msg):
        self.status_label.setText("Erreur")
        QMessageBox.critical(self, "Erreur", error_msg)
        self.search_button.setEnabled(True)
        if self.loading_label:
            self.loading_label.setVisible(False)
            self.loading_gif.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            diff = event.globalPosition() - self._drag_pos
            self.move(int(self.x() + diff.x()), int(self.y() + diff.y()))
            self._drag_pos = event.globalPosition()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MP3DownloaderApp()
    window.show()
    sys.exit(app.exec())