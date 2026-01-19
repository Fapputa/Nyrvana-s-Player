import numpy as np
import librosa
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QBrush, QLinearGradient

class AudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        # Valeurs par défaut
        self.nb_bandes = 60
        self.color_start = QColor("#ffffff")
        self.color_end = QColor("#ffffff")
        self.intensity = 5.0
        
        self.spectrogramme = None
        self.sample_rate = 22050
        self.hop_length = 512
        self.current_frame = 0

    def configure(self, config):
        """Récupère les paramètres dynamiques depuis le JSON"""
        viz_config = config.get("visualizer", {})
        
        # Nombre de barres
        self.nb_bandes = viz_config.get("num_bars", 60)
        
        # Couleurs (Gestion du dégradé)
        self.color_start = QColor(viz_config.get("color_start", "#ffffff"))
        self.color_end = QColor(viz_config.get("color_end", "#ffffff"))
        
        # Intensité du mouvement
        self.intensity = viz_config.get("intensity", 5.0)
        
        # On force la mise à jour si l'audio est déjà chargé
        self.update()

    def load_audio(self, file_path):
        """Analyse le MP3 avec le bon nombre de bandes configuré."""
        try:
            y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            stft = np.abs(librosa.stft(y, n_fft=2048, hop_length=self.hop_length))
            
            # On utilise self.nb_bandes récupéré du JSON
            mel_basis = librosa.filters.mel(sr=sr, n_fft=2048, n_mels=self.nb_bandes)
            self.spectrogramme = np.dot(mel_basis, stft)
            self.spectrogramme = librosa.amplitude_to_db(self.spectrogramme, ref=np.max)
            
            # Normalisation (0.0 à 1.0)
            self.spectrogramme = (self.spectrogramme + 80) / 80 
        except Exception as e:
            print(f"Erreur Equalizer : {e}")
            self.spectrogramme = None

    def update_visualizer(self, ms):
        if self.spectrogramme is not None:
            secondes = ms / 1000
            self.current_frame = int((secondes * self.sample_rate) / self.hop_length)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        # Calcul dynamique de la largeur selon le JSON
        bar_w = w / self.nb_bandes

        if self.spectrogramme is not None and self.current_frame < self.spectrogramme.shape[1]:
            for i in range(self.nb_bandes):
                # Utilisation de l'intensité du JSON
                amp = self.spectrogramme[i, self.current_frame]
                bar_h = max(2, amp * h * (self.intensity / 5.0)) 
                
                # Création d'un dégradé vertical pour chaque barre
                gradient = QLinearGradient(0, h, 0, h - bar_h)
                gradient.setColorAt(0, self.color_start)
                gradient.setColorAt(1, self.color_end)
                
                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                
                # drawRoundedRect rend les barres "rounded" comme demandé
                # Le '5' ici est le rayon de l'arrondi (radius)
                rect_x = int(i * bar_w + 1)
                rect_y = int(h - bar_h)
                rect_w = int(bar_w - 2)
                
                painter.drawRoundedRect(rect_x, rect_y, rect_w, int(bar_h), 5, 5)