import sys
import os
import json
import subprocess
import argparse
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QListWidget, QSlider
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPixmap, QFont, QMovie
from core.actions import (
    load_playlist_from_folder, play_music, pause_music, stop_music,
    load_track_by_index, get_current_position_ms, get_current_track_duration_ms,
    set_volume, playlist, get_current_track_name, get_current_index, set_current_index,
    seek_to_position
)
from core.visualizer import AudioVisualizer
import pygame 


def ms_to_mmss(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 60:02}:{seconds % 60:02}"


def load_config(path="config.json") -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args():
    parser = argparse.ArgumentParser(description='Lecteur de musique')
    parser.add_argument('--tiled', action='store_true', help='Mode fenêtre tiled (non flottante)')
    return parser.parse_args()


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_width = None
        self._base_height = None
        self._animations = []
        
    def showEvent(self, event):
        super().showEvent(event)
        if self._base_width is None:
            self._base_width = self.width()
            self._base_height = self.height()
        
    def enterEvent(self, event):
        if self._base_width is None:
            self._base_width = self.width()
            self._base_height = self.height()
        
        new_w = int(self._base_width * 1.15)
        new_h = int(self._base_height * 1.15)
        self.animate_size(new_w, new_h, 120)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if self._base_width is not None:
            self.animate_size(self._base_width, self._base_height, 120)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if self._base_width is None:
            self._base_width = self.width()
            self._base_height = self.height()
        
        new_w = int(self._base_width * 0.9)
        new_h = int(self._base_height * 0.9)
        self.animate_size(new_w, new_h, 80)
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self._base_width is not None:
            if self.underMouse():
                new_w = int(self._base_width * 1.15)
                new_h = int(self._base_height * 1.15)
            else:
                new_w = self._base_width
                new_h = self._base_height
            self.animate_size(new_w, new_h, 80)
        super().mouseReleaseEvent(event)
    
    def animate_size(self, target_w, target_h, duration):
        for anim in self._animations:
            if anim and anim.state() == QPropertyAnimation.State.Running:
                anim.stop()
        self._animations.clear()
        
        anim_w = QPropertyAnimation(self, b"maximumWidth")
        anim_w.setDuration(duration)
        anim_w.setStartValue(self.width())
        anim_w.setEndValue(target_w)
        anim_w.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        anim_h = QPropertyAnimation(self, b"maximumHeight")
        anim_h.setDuration(duration)
        anim_h.setStartValue(self.height())
        anim_h.setEndValue(target_h)
        anim_h.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        anim_minw = QPropertyAnimation(self, b"minimumWidth")
        anim_minw.setDuration(duration)
        anim_minw.setStartValue(self.width())
        anim_minw.setEndValue(target_w)
        anim_minw.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        anim_minh = QPropertyAnimation(self, b"minimumHeight")
        anim_minh.setDuration(duration)
        anim_minh.setStartValue(self.height())
        anim_minh.setEndValue(target_h)
        anim_minh.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._animations = [anim_w, anim_h, anim_minw, anim_minh]
        
        for anim in self._animations:
            anim.start()


class MusicApp(QWidget):
    def __init__(self, tiled_mode=False):
        super().__init__()
        self.config = load_config()
        self.is_playing = False
        self.is_looping = False
        self.track_finished = False
        self._drag_pos = None
        self.tiled_mode = tiled_mode

        self.setup_window()
        self.setup_ui()
        self.load_music()

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start()

        self.on_volume_change(self.volume_slider.value())
        self.show()

    def setup_window(self):
        cfg = self.config.get("window", {})
        width = cfg.get("width", 270)
        height = cfg.get("height", 450)

        # En mode tiled, ne pas fixer la taille !
        if not self.tiled_mode:
            self.setFixedSize(width, height)
        else:
            self.resize(width, height)
            
        self.setWindowTitle(cfg.get("title", "MusicPlayer"))
        bg_color = cfg.get("background_color", "#9141ac")
        self.setStyleSheet(f"background-color: {bg_color};")

        if not self.tiled_mode:
            self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
            self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        else:
            self.setWindowFlag(Qt.WindowType.Window, True)

        # BACKGROUND
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        self.bg_label.lower()
        self.bg_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Stocker le chemin du fond
        self.bg_path = cfg.get("background_image_path", "")
        
        self.music_gif_label = QLabel(self)
        self.music_gif_label.setScaledContents(True)
        self.music_gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        border_color = bg_color
        self.music_gif_label.setStyleSheet(f"""
            border: 3px solid {border_color};
            background-color: rgba(0, 0, 0, 0.3);
        """)
        self.music_gif_label.hide()
        
        self.music_gif_movie = None
        self.bg_movie = None

        self.update_background()

    def run_c_converter(self, mp4_file):
        print(f"Lancement du convertisseur C pour {mp4_file}...")
        try:
            subprocess.run(["./core/convert", mp4_file], check=True)
            print("Conversion terminée avec succès.")
            self.reload_playlist()
        except Exception as e:
            print(f"Erreur convertisseur C : {e}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        btn_cfg = self.config.get("buttons", {})
        font_family = btn_cfg.get("font_family", "Arial")
        font_size = btn_cfg.get("font_size", 14)
        self.app_font = QFont(font_family, font_size)

        title_bar = QHBoxLayout()
        title_bar.setSpacing(5)
        title_bar.addStretch()

        def create_btn_from_config(symbol, callback, btn_name):
            cfg = self.config.get("buttons", {}).get(btn_name, {})
            size = cfg.get("size", [30, 30])
            color = cfg.get("color", "#ffffff")
            text_color = cfg.get("text_color", "#000000")
            shape = cfg.get("shape", "")
            border_radius = 8 if shape == "rounded" else 0
            image_path = cfg.get("image_path", "")

            btn = AnimatedButton(symbol)
            btn.setFont(self.app_font)
            btn.setFixedSize(*size)

            if image_path and os.path.isfile(image_path):
                btn.setText("")
                btn.setStyleSheet(f"background-color: {color}; border-radius: {border_radius}px; background-image: url({image_path}); background-repeat: no-repeat; background-position: center; border: none;")
            else:
                btn.setStyleSheet(f"background-color: {color}; color: {text_color}; border-radius: {border_radius}px;")
            btn.clicked.connect(callback)
            return btn

        self.config_button = create_btn_from_config("☼", self.launch_config_ui, "config")
        self.search_button = create_btn_from_config("♫", self.launch_research_ui, "search")
        self.reload_button = create_btn_from_config("⤷", self.reload_playlist, "reload")
        self.btn_minimize = create_btn_from_config("—", self.showMinimized, "minimize")
        self.btn_close = create_btn_from_config("✕", self.close, "close")

        for btn in [self.config_button, self.search_button, self.reload_button, self.btn_minimize, self.btn_close]:
            title_bar.addWidget(btn)
        main_layout.addLayout(title_bar)

        # PLAYLIST EN HAUT
        self.list_widget = QListWidget()
        self.list_widget.setFont(self.app_font)
        self.list_widget.clicked.connect(self.select_track)
        self.list_widget.setMaximumHeight(80)
        self.list_widget.setMinimumHeight(80)
        
        pb_cfg = self.config.get("progress_bar", {})
        progress_bg_color = pb_cfg.get("background_color", "#350b4a")
        
        self.list_widget.setStyleSheet(f"""
            QListWidget::item:selected {{
                background: {progress_bg_color};
                color: white;
            }}
            QListWidget::item:selected:!active {{
                background: {progress_bg_color};
                color: white;
            }}
        """)
        main_layout.addWidget(self.list_widget)

        # MODE TILED : GIF après la playlist
        if self.tiled_mode:
            gif_container = QHBoxLayout()
            gif_container.addStretch()
            
            self.gif_widget = QWidget()
            self.gif_widget.setFixedSize(100, 100)
            self.gif_widget.setStyleSheet("background: transparent;")
            
            self.music_gif_label.setParent(self.gif_widget)
            self.music_gif_label.setGeometry(0, 0, 120, 120)
            
            gif_container.addWidget(self.gif_widget)
            gif_container.addStretch()
            main_layout.addLayout(gif_container)

        # Spacer pour pousser le titre vers le bas
        main_layout.addStretch()

        # TITRE juste au-dessus des contrôles play
        self.track_label = QLabel("")
        self.track_label.setFont(self.app_font)
        self.track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_label.setStyleSheet("color: white; background: transparent;")
        main_layout.addWidget(self.track_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        chunk_color = pb_cfg.get("color", "#d09dd2")
        bg_color = pb_cfg.get("background_color", "#350b4a")
        radius = pb_cfg.get("radius", 10)
        height = pb_cfg.get("height", 10)

        self.progress_bar.setFixedHeight(height)
        self.progress_bar.setStyleSheet(f"QProgressBar {{background-color: {bg_color}; border-radius: {radius}px;}} QProgressBar::chunk {{background-color: {chunk_color}; border-radius: {radius}px;}}");
        self.progress_bar.mousePressEvent = self.progress_clicked
        main_layout.addWidget(self.progress_bar)

        self.buttons = {}

        def create_btn(name, symbol, handler):
            cfg = self.config.get("buttons", {}).get(name, {})
            size = cfg.get("size", [30, 30])
            color = cfg.get("color", "#613583")
            text_color = self.config.get("buttons", {}).get("text_color", "#FFFFFF")
            border_radius = 8 if cfg.get("shape", "") == "rounded" else 0
            image_path = cfg.get("image_path", "")
            btn = AnimatedButton(symbol)
            btn.setFont(self.app_font)
            btn.setFixedSize(*size)
            if image_path and os.path.isfile(image_path):
                btn.setText("")
                btn.setStyleSheet(f"background-color: {color}; border-radius: {border_radius}px; background-image: url({image_path}); background-repeat: no-repeat; background-position: center; border: none;")
            else:
                btn.setStyleSheet(f"background-color: {color}; color: {text_color}; border-radius: {border_radius}px;")
            btn.clicked.connect(handler)
            return btn

        time_layout = QHBoxLayout()
        time_layout.addStretch(1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFont(self.app_font)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: white; background: transparent;")
        self.time_label.setFixedWidth(260) 
        time_layout.addWidget(self.time_label)

        self.buttons["loop"] = create_btn("loop", "↻", self.on_toggle_loop)
        self.loop_btn_original_style = self.buttons["loop"].styleSheet()
        time_layout.addStretch(1)
        time_layout.addWidget(self.buttons["loop"])

        main_layout.addLayout(time_layout)

        controls = QHBoxLayout()
        self.buttons["rewind"] = create_btn("rewind", "❮❮", self.on_skip_back)
        self.buttons["play"] = create_btn("play", "➤", self.on_toggle_play_pause)
        self.buttons["forward"] = create_btn("forward", "❯❯", self.on_skip)

        for btn in ["rewind", "play", "forward"]:
            controls.addWidget(self.buttons[btn])
        main_layout.addLayout(controls)

        volume_layout = QHBoxLayout()
        self.volume_label = QLabel("🔈")
        self.volume_label.setFont(self.app_font)
        self.volume_label.setStyleSheet("background: transparent;")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)

        vol_cfg = self.config.get("volume_bar", {})
        height = vol_cfg.get("height", 10)
        bg_color = vol_cfg.get("background_color", "#62a0ea")
        slider_color = vol_cfg.get("slider_color", "#ffffff")
        slider_shape = vol_cfg.get("slider_shape", "rounded")
        radius = vol_cfg.get("radius", 5)

        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.on_volume_change)
        self.volume_slider.setFixedHeight(height)

        border_radius = radius if slider_shape == "rounded" else 0

        style = f"""
            QSlider::groove:horizontal {{
                border-radius: {border_radius}px;
                background: {bg_color};
                height: {height}px;
            }}
            QSlider::handle:horizontal {{
                background: {slider_color};
                border-radius: {border_radius}px;
                width: {int(height * 1.5)}px;
                margin: -{height // 2}px 0;
            }}
        """
        self.volume_slider.setStyleSheet(style)

        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)
        main_layout.addLayout(volume_layout)

        self.visualizer = AudioVisualizer()
        self.visualizer.configure(self.config)
        main_layout.addWidget(self.visualizer)
        
        self.music_gif_label.raise_()

    def launch_config_ui(self):
        subprocess.Popen([sys.executable, "config_ui.py"])

    def launch_research_ui(self):
        subprocess.Popen([sys.executable, "research.py"])

    def reload_playlist(self):
        """Recharge la playlist sans fermer l'application"""
        print("🔄 Rechargement de la playlist...")
        
        # Sauvegarder l'état actuel
        was_playing = self.is_playing
        current_track = get_current_track_name()
        
        # Recharger la playlist
        music_dir = os.path.join(os.getcwd(), "assets", "music")
        load_playlist_from_folder(music_dir)
        
        # Mettre à jour l'affichage
        self.list_widget.clear()
        for path in playlist:
            self.list_widget.addItem(os.path.basename(path))
        
        if playlist:
            # Essayer de retrouver la piste actuelle
            try:
                current_path = os.path.join(music_dir, current_track) if current_track else None
                if current_path and current_path in playlist:
                    idx = playlist.index(current_path)
                else:
                    idx = 0
            except (ValueError, TypeError):
                idx = 0
            
            set_current_index(idx)
            load_track_by_index(idx)
            self.list_widget.setCurrentRow(idx)
            self.update_track_label()
            self.visualizer.load_audio(playlist[idx])
            
            # Reprendre la lecture si elle était en cours
            if was_playing:
                play_music()
        else:
            self.track_label.setText("Aucune musique trouvée")
        
        print("✅ Playlist rechargée")

    def load_music(self):
        music_dir = os.path.join(os.getcwd(), "assets", "music")
        os.makedirs(music_dir, exist_ok=True)
        load_playlist_from_folder(music_dir)
        self.list_widget.clear()
        for path in playlist:
            self.list_widget.addItem(os.path.basename(path))
        if playlist:
            set_current_index(0)
            load_track_by_index(0)
            self.track_finished = False
            self.list_widget.setCurrentRow(0)
            self.update_track_label()
            self.visualizer.load_audio(playlist[0])
        else:
            self.track_label.setText("Aucune musique trouvée")

    def update_track_label(self):
        name = get_current_track_name()
        self.track_label.setText(name or "Aucune musique")
        try:
            idx = playlist.index(os.path.join(os.getcwd(), "assets", "music", name))
            self.list_widget.setCurrentRow(idx)
        except ValueError:
            pass
        
        self.load_background_gif(name)

    def update_progress(self):
        pos = get_current_position_ms()
        dur = get_current_track_duration_ms()
        if dur > 0:
            self.progress_bar.setValue(int((pos / dur) * 1000))
            self.time_label.setText(f"{ms_to_mmss(pos)} / {ms_to_mmss(dur)}")

            if pos >= dur - 500:
                if self.is_looping:
                    seek_to_position(0)
                    pygame.mixer.music.play(loops=-1)
                    self.track_finished = False
                    self.is_playing = True
                    self.buttons["play"].setText("❚❚")
                else:
                    if not self.track_finished:
                        self.track_finished = True
                        self.on_skip()
            elif pos < dur - 1000:
                self.track_finished = False
        else:
            self.progress_bar.setValue(0)
            self.time_label.setText("00:00 / 00:00")

        self.visualizer.update_visualizer(pos)

    def progress_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ratio = event.position().x() / self.progress_bar.width()
            seek_to_position(int(get_current_track_duration_ms() * ratio))

    def select_track(self, index):
        i = index.row()
        if 0 <= i < len(playlist):
            set_current_index(i)
            load_track_by_index(i)
            self.track_finished = False
            self.update_track_label()
            self.visualizer.load_audio(playlist[i]) 
            if self.is_playing:
                play_music()

    def on_toggle_play_pause(self):
        if self.is_playing:
            pause_music()
            self.is_playing = False
            self.buttons["play"].setText("➤")
        else:
            pos = get_current_position_ms()
            dur = get_current_track_duration_ms()
            if pos >= dur or pos == 0:
                seek_to_position(0)
                pygame.mixer.music.play(loops=-1 if self.is_looping else 0)
            else:
                play_music()
            self.is_playing = True
            self.buttons["play"].setText("❚❚")

    def on_skip_back(self):
        i = (get_current_index() - 1) % len(playlist)
        set_current_index(i)
        load_track_by_index(i)
        self.track_finished = False
        self.update_track_label()
        self.visualizer.load_audio(playlist[i])
        if self.is_playing:
            play_music()

    def on_skip(self):
        i = (get_current_index() + 1) % len(playlist)
        set_current_index(i)
        load_track_by_index(i)
        self.track_finished = False
        self.update_track_label()
        self.visualizer.load_audio(playlist[i])
        if self.is_playing:
            play_music()

    def on_toggle_loop(self):
        self.is_looping = not self.is_looping
        btn = self.buttons["loop"]
        original_size = btn.size()
        if self.is_looping:
            btn.setFixedSize(original_size.width() - 2, original_size.height() - 0)
        else:
            btn.setFixedSize(original_size.width() + 2, original_size.height() + 0)

    def on_volume_change(self, value):
        volume_float = value / 100
        set_volume(value / 100)
        self.volume_label.setText("🔊" if value > 0 else "🔇")

    def mousePressEvent(self, event):
        if not self.tiled_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition()

    def mouseMoveEvent(self, event):
        if not self.tiled_mode and self._drag_pos:
            diff = event.globalPosition() - self._drag_pos
            new_x = int(self.x() + diff.x())
            new_y = int(self.y() + diff.y())
            self.move(new_x, new_y)
            self._drag_pos = event.globalPosition()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def resizeEvent(self, event):
        """Appelé quand la fenêtre est redimensionnée (mode tiled)"""
        super().resizeEvent(event)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.update_background()

    def update_background(self):
        """Met à jour le fond pour qu'il remplisse toute la fenêtre"""
        if self.bg_path and os.path.isfile(self.bg_path):
            width = self.width()
            height = self.height()
            
            if self.bg_path.lower().endswith('.gif'):
                if self.bg_movie:
                    self.bg_movie.stop()
                self.bg_movie = QMovie(self.bg_path)
                self.bg_movie.setScaledSize(QSize(width, height))
                self.bg_label.setMovie(self.bg_movie)
                self.bg_movie.start()
            else:
                # ÉTIRER L'IMAGE pour remplir exactement la taille actuelle
                pixmap = QPixmap(self.bg_path).scaled(
                    width, 
                    height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.bg_label.setPixmap(pixmap)

    def load_background_gif(self, track_name):
        if not track_name:
            return
        
        base_name = os.path.splitext(track_name)[0]
        gif_path = os.path.join(os.getcwd(), "assets", "music", f"{base_name}.gif")
        
        if os.path.isfile(gif_path):
            if self.music_gif_movie:
                self.music_gif_movie.stop()
            
            self.music_gif_movie = QMovie(gif_path)
            self.music_gif_label.setMovie(self.music_gif_movie)
            self.music_gif_movie.start()
            self.music_gif_label.show()
            self.music_gif_label.raise_()
            
            print(f"✅ GIF chargé : {gif_path}")
        else:
            if self.music_gif_movie:
                self.music_gif_movie.stop()
                self.music_gif_movie = None
            self.music_gif_label.hide()
            
            print(f"⚠️ Pas de GIF trouvé pour : {track_name}")


if __name__ == "__main__":
    args = parse_args()
    pygame.mixer.init()
    app = QApplication(sys.argv)
    window = MusicApp(tiled_mode=args.tiled)
    sys.exit(app.exec())