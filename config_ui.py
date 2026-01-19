import json
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QColorDialog,
    QComboBox, QSpinBox, QFileDialog, QApplication, QHBoxLayout,
    QSlider, QTabWidget, QScrollArea, QCheckBox, QGroupBox
)
from PyQt6.QtGui import QColor, QFontDatabase
from PyQt6.QtCore import Qt
import pyqtgraph as pg

CONFIG_FILE = "config.json"

class ButtonConfigUI(QWidget):
    def __init__(self, button_name, config):
        super().__init__()
        self.button_name = button_name
        self.config = config

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Configuration du bouton '{button_name}'"))

        # Forme
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["rounded", "square", "circle"])
        self.shape_combo.setCurrentText(self.config[button_name].get("shape", "rounded"))
        layout.addWidget(QLabel("Forme"))
        layout.addWidget(self.shape_combo)

        # Couleur de fond
        self.color_button = QPushButton("Choisir couleur de fond")
        bg_color = self.config[button_name].get("color", "#FFFFFF")
        self.color_button.setStyleSheet(f"background-color: {bg_color}")
        self.color_button.clicked.connect(self.pick_bg_color)
        layout.addWidget(QLabel("Couleur de fond"))
        layout.addWidget(self.color_button)

        # Couleur de texte
        self.text_color_button = QPushButton("Choisir couleur du texte")
        text_color = self.config[button_name].get("text_color", "#000000")
        self.text_color_button.setStyleSheet(f"background-color: {text_color}")
        self.text_color_button.clicked.connect(self.pick_text_color)
        layout.addWidget(QLabel("Couleur du texte"))
        layout.addWidget(self.text_color_button)

        # Taille
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 200)
        self.width_spin.setValue(self.config[button_name].get("size", [50, 50])[0])
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 200)
        self.height_spin.setValue(self.config[button_name].get("size", [50, 50])[1])
        size_layout.addWidget(QLabel("Largeur"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("Hauteur"))
        size_layout.addWidget(self.height_spin)
        layout.addWidget(QLabel("Taille"))
        layout.addLayout(size_layout)

        # Bordure
        border_layout = QHBoxLayout()
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(0, 10)
        self.border_width_spin.setValue(self.config[button_name].get("border_width", 0))
        border_layout.addWidget(QLabel("Épaisseur bordure"))
        border_layout.addWidget(self.border_width_spin)
        layout.addLayout(border_layout)

        self.border_color_button = QPushButton("Couleur bordure")
        border_color = self.config[button_name].get("border_color", "#000000")
        self.border_color_button.setStyleSheet(f"background-color: {border_color}")
        self.border_color_button.clicked.connect(self.pick_border_color)
        layout.addWidget(self.border_color_button)

        # Image ou GIF
        self.image_button = QPushButton("Charger image/GIF")
        self.image_button.clicked.connect(self.load_image)
        layout.addWidget(self.image_button)

        img_path = self.config[button_name].get("image_path", "")
        self.image_path_label = QLabel(img_path if img_path else "Aucune image chargée")
        layout.addWidget(self.image_path_label)

        # Opacité
        opacity_layout = QHBoxLayout()
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(int(self.config[button_name].get("opacity", 1.0) * 100))
        opacity_layout.addWidget(QLabel("Opacité (%)"))
        opacity_layout.addWidget(self.opacity_spin)
        layout.addLayout(opacity_layout)

    def pick_bg_color(self):
        current = QColor(self.config[self.button_name].get("color", "#FFFFFF"))
        color = QColorDialog.getColor(current, self, "Choisir couleur")
        if color.isValid():
            self.config[self.button_name]["color"] = color.name()
            self.color_button.setStyleSheet(f"background-color: {color.name()}")

    def pick_text_color(self):
        current = QColor(self.config[self.button_name].get("text_color", "#000000"))
        color = QColorDialog.getColor(current, self, "Choisir couleur du texte")
        if color.isValid():
            self.config[self.button_name]["text_color"] = color.name()
            self.text_color_button.setStyleSheet(f"background-color: {color.name()}")

    def pick_border_color(self):
        current = QColor(self.config[self.button_name].get("border_color", "#000000"))
        color = QColorDialog.getColor(current, self, "Choisir couleur de bordure")
        if color.isValid():
            self.config[self.button_name]["border_color"] = color.name()
            self.border_color_button.setStyleSheet(f"background-color: {color.name()}")

    def load_image(self):
        dlg = QFileDialog(self, "Choisir une image ou un GIF")
        dlg.setNameFilters(["Images (*.png *.jpg *.bmp *.gif)"])
        if dlg.exec():
            path = dlg.selectedFiles()[0]
            self.config[self.button_name]["image_path"] = path
            self.image_path_label.setText(path)

    def update_config(self):
        self.config[self.button_name]["shape"] = self.shape_combo.currentText()
        self.config[self.button_name]["size"] = [self.width_spin.value(), self.height_spin.value()]
        self.config[self.button_name]["border_width"] = self.border_width_spin.value()
        self.config[self.button_name]["opacity"] = self.opacity_spin.value() / 100.0

class ConfigUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Interface")
        self.config = self.load_config()

        self.resize(self.config["window"].get("width", 800), self.config["window"].get("height", 700))
        self.setStyleSheet(f"background-color: {self.config['window'].get('background_color', '#FFFFFF')};")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.scroll.setWidget(self.container)
        self.main_layout = QVBoxLayout(self.container)

        self.add_window_config_ui()
        self.add_animation_config_ui()
        self.add_buttons_general_ui()
        self.add_buttons_detailed_ui()
        self.add_progress_bar_ui()
        self.add_volume_bar_ui()
        self.add_visualizer_ui()
        self.add_overlay_config_ui()

        self.save_button = QPushButton("💾 Enregistrer la configuration")
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.save_button.clicked.connect(self.save_config)
        self.main_layout.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                return self.merge_defaults(self.default_config(), loaded)
        except Exception:
            return self.default_config()

    def default_config(self):
        return {
            "window": {
                "width": 270,
                "height": 450,
                "title": "Lecteur de musique",
                "background_color": "#9141ac",
                "background_image_path": "",
                "opacity": 1.0
            },
            "animations": {
                "enabled": True,
                "hover_enabled": True,
                "click_enabled": True,
                "window_fade_in": True,
                "duration": 150,
                "hover_scale": 1.1,
                "click_scale": 0.95
            },
            "buttons": {
                "font_family": "Arial",
                "font_path": "",
                "font_size": 12,
                "text_color": "#000000",
                "play": {"shape": "rounded", "color": "#613583", "text_color": "#FFFFFF", "size": [50, 50], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "loop": {"shape": "rounded", "color": "#613583", "text_color": "#FFFFFF", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "rewind": {"shape": "rounded", "color": "#613583", "text_color": "#FFFFFF", "size": [40, 40], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "forward": {"shape": "rounded", "color": "#613583", "text_color": "#FFFFFF", "size": [40, 40], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "config": {"shape": "rounded", "color": "#ffffff", "text_color": "#000000", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "search": {"shape": "rounded", "color": "#ffffff", "text_color": "#000000", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "reload": {"shape": "rounded", "color": "#ffffff", "text_color": "#000000", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "minimize": {"shape": "rounded", "color": "#ffffff", "text_color": "#000000", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0},
                "close": {"shape": "rounded", "color": "#ff5555", "text_color": "#FFFFFF", "size": [30, 30], "image_path": "", "border_width": 0, "border_color": "#000000", "opacity": 1.0}
            },
            "progress_bar": {
                "color": "#d09dd2",
                "background_color": "#350b4a",
                "height": 10,
                "radius": 10,
                "show_time": True,
                "animated": True
            },
            "visualizer": {
                "enabled": True,
                "num_bars": 20,
                "color_start": "#FF0000",
                "color_end": "#0000FF",
                "intensity": 1.0,
                "style": "bars"
            },
            "volume_bar": {
                "background_color": "#62a0ea",
                "slider_color": "#ffffff",
                "height": 10,
                "slider_shape": "rounded",
                "radius": 5
            },
            "overlay": {
                "show_on_hover": False,
                "opacity": 0.8,
                "color": "#000000"
            }
        }

    def add_animation_config_ui(self):
        group = QGroupBox("⚡ Configuration des animations")
        layout = QVBoxLayout()

        self.anim_enabled_check = QCheckBox("Activer les animations")
        self.anim_enabled_check.setChecked(self.config.get("animations", {}).get("enabled", True))
        layout.addWidget(self.anim_enabled_check)

        self.hover_anim_check = QCheckBox("Animation au survol")
        self.hover_anim_check.setChecked(self.config.get("animations", {}).get("hover_enabled", True))
        layout.addWidget(self.hover_anim_check)

        self.click_anim_check = QCheckBox("Animation au clic")
        self.click_anim_check.setChecked(self.config.get("animations", {}).get("click_enabled", True))
        layout.addWidget(self.click_anim_check)

        self.fade_in_check = QCheckBox("Animation d'apparition de la fenêtre")
        self.fade_in_check.setChecked(self.config.get("animations", {}).get("window_fade_in", True))
        layout.addWidget(self.fade_in_check)

        duration_layout = QHBoxLayout()
        self.anim_duration_spin = QSpinBox()
        self.anim_duration_spin.setRange(50, 1000)
        self.anim_duration_spin.setValue(self.config.get("animations", {}).get("duration", 150))
        duration_layout.addWidget(QLabel("Durée (ms)"))
        duration_layout.addWidget(self.anim_duration_spin)
        layout.addLayout(duration_layout)

        hover_scale_layout = QHBoxLayout()
        self.hover_scale_spin = QSpinBox()
        self.hover_scale_spin.setRange(100, 200)
        self.hover_scale_spin.setValue(int(self.config.get("animations", {}).get("hover_scale", 1.1) * 100))
        hover_scale_layout.addWidget(QLabel("Échelle survol (%)"))
        hover_scale_layout.addWidget(self.hover_scale_spin)
        layout.addLayout(hover_scale_layout)

        click_scale_layout = QHBoxLayout()
        self.click_scale_spin = QSpinBox()
        self.click_scale_spin.setRange(50, 100)
        self.click_scale_spin.setValue(int(self.config.get("animations", {}).get("click_scale", 0.95) * 100))
        click_scale_layout.addWidget(QLabel("Échelle clic (%)"))
        click_scale_layout.addWidget(self.click_scale_spin)
        layout.addLayout(click_scale_layout)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def add_overlay_config_ui(self):
        group = QGroupBox("🎨 Configuration de l'overlay")
        layout = QVBoxLayout()

        self.overlay_hover_check = QCheckBox("Afficher overlay au survol")
        self.overlay_hover_check.setChecked(self.config.get("overlay", {}).get("show_on_hover", False))
        layout.addWidget(self.overlay_hover_check)

        opacity_layout = QHBoxLayout()
        self.overlay_opacity_spin = QSpinBox()
        self.overlay_opacity_spin.setRange(0, 100)
        self.overlay_opacity_spin.setValue(int(self.config.get("overlay", {}).get("opacity", 0.8) * 100))
        opacity_layout.addWidget(QLabel("Opacité (%)"))
        opacity_layout.addWidget(self.overlay_opacity_spin)
        layout.addLayout(opacity_layout)

        self.overlay_color_btn = QPushButton("Couleur overlay")
        overlay_color = self.config.get("overlay", {}).get("color", "#000000")
        self.overlay_color_btn.setStyleSheet(f"background-color: {overlay_color}")
        self.overlay_color_btn.clicked.connect(self.pick_overlay_color)
        layout.addWidget(self.overlay_color_btn)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def pick_overlay_color(self):
        current = QColor(self.config.get("overlay", {}).get("color", "#000000"))
        color = QColorDialog.getColor(current, self, "Choisir couleur overlay")
        if color.isValid():
            if "overlay" not in self.config:
                self.config["overlay"] = {}
            self.config["overlay"]["color"] = color.name()
            self.overlay_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def add_window_config_ui(self):
        group = QGroupBox("🪟 Configuration de la fenêtre")
        layout = QVBoxLayout()

        # Titre
        title_layout = QHBoxLayout()
        self.title_input = QLabel()
        title_layout.addWidget(QLabel("Titre:"))
        from PyQt6.QtWidgets import QLineEdit
        self.title_line = QLineEdit()
        self.title_line.setText(self.config.get("window", {}).get("title", "Lecteur de musique"))
        title_layout.addWidget(self.title_line)
        layout.addLayout(title_layout)

        layout.addWidget(QLabel("Couleur de fond de la fenêtre :"))
        self.bg_color_btn = QPushButton()
        color = self.config["window"].get("background_color", "#FFFFFF")
        self.bg_color_btn.setStyleSheet(f"background-color: {color}")
        self.bg_color_btn.clicked.connect(self.pick_bg_color)
        layout.addWidget(self.bg_color_btn)

        layout.addWidget(QLabel("Image de fond :"))
        self.bg_img_btn = QPushButton("Choisir image/GIF")
        self.bg_img_btn.clicked.connect(self.pick_bg_image)
        layout.addWidget(self.bg_img_btn)

        img_path = self.config["window"].get("background_image_path", "")
        self.bg_img_label = QLabel(img_path if img_path else "Aucune image chargée")
        layout.addWidget(self.bg_img_label)

        layout.addWidget(QLabel("Taille de la fenêtre :"))
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(200, 1920)
        self.width_spin.setValue(self.config["window"].get("width", 800))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(200, 1080)
        self.height_spin.setValue(self.config["window"].get("height", 600))
        size_layout.addWidget(QLabel("Largeur"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("Hauteur"))
        size_layout.addWidget(self.height_spin)
        layout.addLayout(size_layout)

        # Opacité fenêtre
        opacity_layout = QHBoxLayout()
        self.window_opacity_spin = QSpinBox()
        self.window_opacity_spin.setRange(10, 100)
        self.window_opacity_spin.setValue(int(self.config["window"].get("opacity", 1.0) * 100))
        opacity_layout.addWidget(QLabel("Opacité fenêtre (%)"))
        opacity_layout.addWidget(self.window_opacity_spin)
        layout.addLayout(opacity_layout)

        group.setLayout(layout)
        self.main_layout.addWidget(group)
        
    def merge_defaults(self, defaults, loaded):
        if not isinstance(loaded, dict):
            return defaults
        result = dict(defaults)
        for k, v in defaults.items():
            if k not in loaded:
                result[k] = v
            else:
                if isinstance(v, dict):
                    result[k] = self.merge_defaults(v, loaded[k])
                else:
                    result[k] = loaded[k]
        return result

    def add_volume_bar_ui(self):
        group = QGroupBox("🔊 Configuration de la barre de volume")
        layout = QVBoxLayout()
        
        self.volume_slider_color_btn = QPushButton()
        self.volume_slider_color_btn.setStyleSheet(f"background-color: {self.config['volume_bar']['slider_color']}")
        self.volume_slider_color_btn.clicked.connect(self.pick_volume_slider_color)
        layout.addWidget(QLabel("Couleur du slider"))
        layout.addWidget(self.volume_slider_color_btn)

        self.volume_bg_color_btn = QPushButton()
        self.volume_bg_color_btn.setStyleSheet(f"background-color: {self.config['volume_bar']['background_color']}")
        self.volume_bg_color_btn.clicked.connect(self.pick_volume_bg_color)
        layout.addWidget(QLabel("Couleur du fond"))
        layout.addWidget(self.volume_bg_color_btn)

        self.volume_height_spin = QSpinBox()
        self.volume_height_spin.setRange(1, 50)
        self.volume_height_spin.setValue(self.config["volume_bar"]["height"])
        layout.addWidget(QLabel("Hauteur"))
        layout.addWidget(self.volume_height_spin)

        self.volume_radius_spin = QSpinBox()
        self.volume_radius_spin.setRange(0, 30)
        self.volume_radius_spin.setValue(self.config["volume_bar"]["radius"])
        layout.addWidget(QLabel("Rayon"))
        layout.addWidget(self.volume_radius_spin)

        self.volume_slider_shape_combo = QComboBox()
        self.volume_slider_shape_combo.addItems(["rounded", "square"])
        self.volume_slider_shape_combo.setCurrentText(self.config["volume_bar"]["slider_shape"])
        layout.addWidget(QLabel("Forme du slider"))
        layout.addWidget(self.volume_slider_shape_combo)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def pick_volume_slider_color(self):
        current = QColor(self.config['volume_bar']['slider_color'])
        color = QColorDialog.getColor(current, self, "Choisir couleur du slider volume")
        if color.isValid():
            self.config['volume_bar']['slider_color'] = color.name()
            self.volume_slider_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def pick_volume_bg_color(self):
        current = QColor(self.config['volume_bar']['background_color'])
        color = QColorDialog.getColor(current, self, "Choisir couleur de fond volume")
        if color.isValid():
            self.config['volume_bar']['background_color'] = color.name()
            self.volume_bg_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def add_buttons_general_ui(self):
        group = QGroupBox("🔘 Configuration générale des boutons")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Police de caractères :"))

        self.font_family_combo = QComboBox()
        fonts = QFontDatabase.families()
        self.font_family_combo.addItems(fonts)
        self.font_family_combo.setCurrentText(self.config["buttons"].get("font_family", "Arial"))
        layout.addWidget(self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(5, 50)
        self.font_size_spin.setValue(self.config["buttons"].get("font_size", 12))
        layout.addWidget(QLabel("Taille de police"))
        layout.addWidget(self.font_size_spin)

        layout.addWidget(QLabel("Couleur du texte par défaut"))
        self.text_color_btn = QPushButton()
        self.text_color_btn.setStyleSheet(f"background-color: {self.config['buttons']['text_color']}")
        self.text_color_btn.clicked.connect(self.pick_text_color)
        layout.addWidget(self.text_color_btn)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def pick_text_color(self):
        current = QColor(self.config['buttons']['text_color'])
        color = QColorDialog.getColor(current, self, "Choisir couleur du texte")
        if color.isValid():
            self.config['buttons']['text_color'] = color.name()
            self.text_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def add_buttons_detailed_ui(self):
        group = QGroupBox("🎛️ Configuration détaillée des boutons")
        layout = QVBoxLayout()
        
        self.buttons_tabs = QTabWidget()
        self.button_config_uis = {}
        for btn_name in self.config["buttons"]:
            if btn_name in ("font_family", "font_size", "text_color", "font_path"):
                continue
            ui = ButtonConfigUI(btn_name, self.config["buttons"])
            self.buttons_tabs.addTab(ui, btn_name.capitalize())
            self.button_config_uis[btn_name] = ui
        layout.addWidget(self.buttons_tabs)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def add_progress_bar_ui(self):
        group = QGroupBox("📊 Configuration de la barre de progression")
        layout = QVBoxLayout()
        
        self.progress_color_btn = QPushButton()
        self.progress_color_btn.setStyleSheet(f"background-color: {self.config['progress_bar']['color']}")
        self.progress_color_btn.clicked.connect(self.pick_progress_color)
        layout.addWidget(QLabel("Couleur"))
        layout.addWidget(self.progress_color_btn)

        self.progress_bg_color_btn = QPushButton()
        self.progress_bg_color_btn.setStyleSheet(f"background-color: {self.config['progress_bar']['background_color']}")
        self.progress_bg_color_btn.clicked.connect(self.pick_progress_bg_color)
        layout.addWidget(QLabel("Couleur du fond"))
        layout.addWidget(self.progress_bg_color_btn)

        self.progress_height_spin = QSpinBox()
        self.progress_height_spin.setRange(1, 100)
        self.progress_height_spin.setValue(self.config["progress_bar"]["height"])
        layout.addWidget(QLabel("Hauteur"))
        layout.addWidget(self.progress_height_spin)

        self.progress_radius_spin = QSpinBox()
        self.progress_radius_spin.setRange(0, 50)
        self.progress_radius_spin.setValue(self.config["progress_bar"]["radius"])
        layout.addWidget(QLabel("Rayon"))
        layout.addWidget(self.progress_radius_spin)

        self.progress_animated_check = QCheckBox("Barre animée")
        self.progress_animated_check.setChecked(self.config.get("progress_bar", {}).get("animated", True))
        layout.addWidget(self.progress_animated_check)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def pick_progress_color(self):
        current = QColor(self.config['progress_bar']['color'])
        color = QColorDialog.getColor(current, self, "Choisir couleur de la barre de progression")
        if color.isValid():
            self.config['progress_bar']['color'] = color.name()
            self.progress_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def pick_progress_bg_color(self):
        current = QColor(self.config['progress_bar']['background_color'])
        color = QColorDialog.getColor(current, self, "Choisir couleur de fond de la barre de progression")
        if color.isValid():
            self.config['progress_bar']['background_color'] = color.name()
            self.progress_bg_color_btn.setStyleSheet(f"background-color: {color.name()}")

    def add_visualizer_ui(self):
        group = QGroupBox("🎵 Configuration du visualiseur")
        layout = QVBoxLayout()

        self.visualizer_enabled_check = QCheckBox("Activer le visualiseur")
        self.visualizer_enabled_check.setChecked(self.config.get("visualizer", {}).get("enabled", True))
        layout.addWidget(self.visualizer_enabled_check)

        self.num_bars_spin = QSpinBox()
        self.num_bars_spin.setRange(1, 100)
        self.num_bars_spin.setValue(self.config["visualizer"]["num_bars"])
        layout.addWidget(QLabel("Nombre de barres"))
        layout.addWidget(self.num_bars_spin)

        self.color_start_btn = QPushButton()
        self.color_start_btn.setStyleSheet(f"background-color: {self.config['visualizer']['color_start']}")
        self.color_start_btn.clicked.connect(self.pick_visualizer_color_start)
        layout.addWidget(QLabel("Couleur de début"))
        layout.addWidget(self.color_start_btn)

        self.color_end_btn = QPushButton()
        self.color_end_btn.setStyleSheet(f"background-color: {self.config['visualizer']['color_end']}")
        self.color_end_btn.clicked.connect(self.pick_visualizer_color_end)
        layout.addWidget(QLabel("Couleur de fin"))
        layout.addWidget(self.color_end_btn)

        self.intensity_spin = QSpinBox()
        self.intensity_spin.setRange(1, 50)
        self.intensity_spin.setValue(int(self.config["visualizer"]["intensity"] * 10))
        layout.addWidget(QLabel("Intensité (1-50)"))
        layout.addWidget(self.intensity_spin)

        self.visualizer_style_combo = QComboBox()
        self.visualizer_style_combo.addItems(["bars", "wave", "circle"])
        self.visualizer_style_combo.setCurrentText(self.config.get("visualizer", {}).get("style", "bars"))
        layout.addWidget(QLabel("Style"))
        layout.addWidget(self.visualizer_style_combo)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def pick_visualizer_color_start(self):
        current = QColor(self.config['visualizer']['color_start'])
        color = QColorDialog.getColor(current, self, "Choisir couleur début visualiseur")
        if color.isValid():
            self.config['visualizer']['color_start'] = color.name()
            self.color_start_btn.setStyleSheet(f"background-color: {color.name()}")

    def pick_visualizer_color_end(self):
        current = QColor(self.config['visualizer']['color_end'])
        color = QColorDialog.getColor(current, self, "Choisir couleur fin visualiseur")
        if color.isValid():
            self.config['visualizer']['color_end'] = color.name()
            self.color_end_btn.setStyleSheet(f"background-color: {color.name()}")

    def pick_bg_color(self):
        current = QColor(self.config["window"].get("background_color", "#FFFFFF"))
        color = QColorDialog.getColor(current, self, "Choisir couleur de fond")
        if color.isValid():
            self.config["window"]["background_color"] = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.setStyleSheet(f"background-color: {color.name()};")

    def pick_bg_image(self):
        dlg = QFileDialog(self, "Choisir une image ou un GIF")
        dlg.setNameFilters(["Images (*.png *.jpg *.bmp *.gif)"])
        if dlg.exec():
            path = dlg.selectedFiles()[0]
            self.config["window"]["background_image_path"] = path
            self.bg_img_label.setText(path)

    def save_config(self):
        # Window
        self.config["window"]["width"] = self.width_spin.value()
        self.config["window"]["height"] = self.height_spin.value()
        self.config["window"]["title"] = self.title_line.text()
        self.config["window"]["opacity"] = self.window_opacity_spin.value() / 100.0

        # Animations
        if "animations" not in self.config:
            self.config["animations"] = {}
        self.config["animations"]["enabled"] = self.anim_enabled_check.isChecked()
        self.config["animations"]["hover_enabled"] = self.hover_anim_check.isChecked()
        self.config["animations"]["click_enabled"] = self.click_anim_check.isChecked()
        self.config["animations"]["window_fade_in"] = self.fade_in_check.isChecked()
        self.config["animations"]["duration"] = self.anim_duration_spin.value()
        self.config["animations"]["hover_scale"] = self.hover_scale_spin.value() / 100.0
        self.config["animations"]["click_scale"] = self.click_scale_spin.value() / 100.0

        # Overlay
        if "overlay" not in self.config:
            self.config["overlay"] = {}
        self.config["overlay"]["show_on_hover"] = self.overlay_hover_check.isChecked()
        self.config["overlay"]["opacity"] = self.overlay_opacity_spin.value() / 100.0

        # Buttons general
        self.config["buttons"]["font_family"] = self.font_family_combo.currentText()
        self.config["buttons"]["font_size"] = self.font_size_spin.value()

        # Buttons detailed
        for btn_name, ui in self.button_config_uis.items():
            ui.update_config()

        # Progress bar
        self.config["progress_bar"]["height"] = self.progress_height_spin.value()
        self.config["progress_bar"]["radius"] = self.progress_radius_spin.value()
        self.config["progress_bar"]["animated"] = self.progress_animated_check.isChecked()

        # Visualizer
        self.config["visualizer"]["enabled"] = self.visualizer_enabled_check.isChecked()
        self.config["visualizer"]["num_bars"] = self.num_bars_spin.value()
        self.config["visualizer"]["intensity"] = self.intensity_spin.value() / 10.0
        self.config["visualizer"]["style"] = self.visualizer_style_combo.currentText()

        # Volume bar
        self.config["volume_bar"]["height"] = self.volume_height_spin.value()
        self.config["volume_bar"]["radius"] = self.volume_radius_spin.value()
        self.config["volume_bar"]["slider_shape"] = self.volume_slider_shape_combo.currentText()

        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

        print("✅ Configuration enregistrée avec succès!")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = ConfigUI()
    win.show()
    sys.exit(app.exec())