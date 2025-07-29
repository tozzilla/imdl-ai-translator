"""
Overflow Detector - Analizza frame di testo IDML e predice potenziali overflow
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Any
from xml.etree import ElementTree as ET
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TextFrameMetrics:
    """Metriche di un text frame IDML"""
    frame_id: str
    width: float
    height: float
    x: float
    y: float
    column_count: int
    column_gutter: float
    inset_spacing: Tuple[float, float, float, float]  # top, right, bottom, left
    font_size: float
    leading: float
    char_count: int
    estimated_overflow_risk: float
    
@dataclass
class OverflowPrediction:
    """Predizione di overflow per un segmento di testo"""
    original_text: str
    estimated_translated_length: int
    available_space_chars: int
    overflow_risk: float
    recommended_max_length: int
    frame_id: str
    suggestions: List[str]

class OverflowDetector:
    """Detector per analizzare e predire overflow di testo in IDML"""
    
    def __init__(self):
        """Inizializza detector con metriche predefinite"""
        
        # Fattori di espansione per lingue (rispetto all'italiano)
        self.expansion_factors = {
            'de': 1.30,  # Tedesco: +30% più lungo
            'en': 1.10,  # Inglese: +10% più lungo
            'fr': 1.15,  # Francese: +15% più lungo
            'es': 1.05,  # Spagnolo: +5% più lungo
            'pt': 1.10,  # Portoghese: +10% più lungo
        }
        
        # Metriche caratteri per font comuni (caratteri per punto)
        self.font_metrics = {
            'arial': 2.1,
            'helvetica': 2.0,
            'times': 1.9,
            'calibri': 2.0,
            'verdana': 1.8,
            'default': 2.0
        }
        
        # Soglie di rischio overflow
        self.risk_thresholds = {
            'low': 0.75,      # <75% dello spazio = rischio basso
            'medium': 0.90,   # 75-90% = rischio medio
            'high': 1.0,      # 90-100% = rischio alto
            'critical': 1.0   # >100% = critico
        }
        
    def analyze_document_frames(self, idml_processor) -> Dict[str, TextFrameMetrics]:
        """
        Analizza tutti i text frame del documento IDML
        
        Args:
            idml_processor: IDMLProcessor caricato
            
        Returns:
            Dizionario frame_id -> TextFrameMetrics
        """
        frames_metrics = {}
        
        if not idml_processor.idml_package:
            logger.error("IDML package non caricato")
            return frames_metrics
        
        try:
            # Analizza i file spread per trovare text frame
            spreads = self._get_spread_files(idml_processor)
            
            for spread_path in spreads:
                spread_content = idml_processor.idml_package.read(spread_path)
                if isinstance(spread_content, bytes):
                    spread_content = spread_content.decode('utf-8')
                
                spread_root = ET.fromstring(spread_content)
                frame_metrics = self._extract_textframe_metrics(spread_root, spread_path)
                frames_metrics.update(frame_metrics)
                
        except Exception as e:
            logger.error(f"Errore analisi frame: {e}")
        
        logger.info(f"Analizzati {len(frames_metrics)} text frame")
        return frames_metrics
    
    def _get_spread_files(self, idml_processor) -> List[str]:
        """Ottiene lista dei file spread dal package IDML"""
        spread_files = []
        
        try:
            for file_info in idml_processor.idml_package.infolist():
                if file_info.filename.startswith('Spreads/') and file_info.filename.endswith('.xml'):
                    spread_files.append(file_info.filename)
        except Exception as e:
            logger.error(f"Errore lettura spreads: {e}")
        
        return spread_files
    
    def _extract_textframe_metrics(self, spread_root: ET.Element, spread_path: str) -> Dict[str, TextFrameMetrics]:
        """Estrae metriche dai text frame in uno spread"""
        metrics = {}
        
        def remove_namespace(tag):
            return tag.split('}')[-1] if '}' in tag else tag
        
        # Cerca tutti i TextFrame nello spread
        for element in spread_root.iter():
            if remove_namespace(element.tag) == 'TextFrame':
                try:
                    frame_metrics = self._parse_textframe_element(element, spread_path)
                    if frame_metrics:
                        metrics[frame_metrics.frame_id] = frame_metrics
                except Exception as e:
                    logger.warning(f"Errore parsing TextFrame in {spread_path}: {e}")
        
        return metrics
    
    def _parse_textframe_element(self, textframe_elem: ET.Element, spread_path: str) -> Optional[TextFrameMetrics]:
        """Parsa un singolo elemento TextFrame"""
        
        # Ottieni ID del frame
        frame_id = textframe_elem.get('Self', f"{spread_path}_frame_{id(textframe_elem)}")
        
        # Parse transform matrix per posizione e dimensioni
        item_transform = textframe_elem.get('ItemTransform', '1 0 0 1 0 0')
        transform_values = [float(x) for x in item_transform.split()]
        
        if len(transform_values) >= 6:
            # Matrix formato: [scaleX, skewY, skewX, scaleY, translateX, translateY]
            scale_x, skew_y, skew_x, scale_y, x, y = transform_values[:6]
            
            # Per frame rettangolari, scale rappresenta dimensioni
            width = abs(scale_x)
            height = abs(scale_y)
        else:
            # Fallback su valori predefiniti
            width = 200.0
            height = 100.0
            x = 0.0
            y = 0.0
        
        # Parse proprietà del testo
        column_count = int(textframe_elem.get('TextColumnCount', '1'))
        column_gutter = float(textframe_elem.get('TextColumnGutter', '12'))
        
        # Parse inset spacing (margini interni)
        inset_spacing = self._parse_inset_spacing(textframe_elem)
        
        # Stima proprietà del font dai contenuti
        font_size, leading = self._estimate_font_properties(textframe_elem)
        
        # Conta caratteri nel contenuto
        char_count = self._count_frame_characters(textframe_elem)
        
        # Calcola rischio overflow iniziale
        overflow_risk = self._calculate_initial_overflow_risk(
            width, height, char_count, font_size, column_count, inset_spacing
        )
        
        return TextFrameMetrics(
            frame_id=frame_id,
            width=width,
            height=height, 
            x=x,
            y=y,
            column_count=column_count,
            column_gutter=column_gutter,
            inset_spacing=inset_spacing,
            font_size=font_size,
            leading=leading,
            char_count=char_count,
            estimated_overflow_risk=overflow_risk
        )
    
    def _parse_inset_spacing(self, textframe_elem: ET.Element) -> Tuple[float, float, float, float]:
        """Parsa margini interni del text frame"""
        # Cerca attributi di inset spacing
        inset_str = textframe_elem.get('TextFramePreferenceInsetSpacing', '0 0 0 0')
        
        try:
            inset_values = [float(x) for x in inset_str.split()]
            if len(inset_values) >= 4:
                return tuple(inset_values[:4])
            elif len(inset_values) == 1:
                # Tutti i margini uguali
                val = inset_values[0]
                return (val, val, val, val)
        except (ValueError, AttributeError):
            pass
        
        # Default: nessun margine
        return (0.0, 0.0, 0.0, 0.0)
    
    def _estimate_font_properties(self, textframe_elem: ET.Element) -> Tuple[float, float]:
        """Stima proprietà font dal text frame"""
        font_size = 12.0  # Default
        leading = 14.4    # Default (120% del font size)
        
        # Cerca nelle proprietà del frame
        try:
            # Cerca caratteristiche tipografiche comuni
            for attr, value in textframe_elem.attrib.items():
                if 'FontSize' in attr or 'PointSize' in attr:
                    font_size = float(value)
                elif 'Leading' in attr or 'LineSpacing' in attr:
                    leading = float(value)
        except (ValueError, AttributeError):
            pass
        
        # Se leading non specificato, usa 120% del font size
        if leading <= font_size:
            leading = font_size * 1.2
        
        return font_size, leading
    
    def _count_frame_characters(self, textframe_elem: ET.Element) -> int:
        """Conta caratteri nel text frame"""
        char_count = 0
        
        # Cerca tutti gli elementi con testo
        for elem in textframe_elem.iter():
            if elem.text:
                char_count += len(elem.text.strip())
            if elem.tail:
                char_count += len(elem.tail.strip())
        
        return char_count
    
    def _calculate_initial_overflow_risk(self, width: float, height: float, 
                                       char_count: int, font_size: float,
                                       column_count: int, inset_spacing: Tuple[float, float, float, float]) -> float:
        """Calcola rischio overflow iniziale basato su dimensioni frame"""
        
        # Calcola area disponibile per il testo
        top, right, bottom, left = inset_spacing
        effective_width = width - left - right
        effective_height = height - top - bottom
        
        # Considera colonne
        if column_count > 1:
            # Riduci larghezza per gutter tra colonne
            effective_width = (effective_width - (column_count - 1) * 12) / column_count
        
        # Stima caratteri che possono entrare
        chars_per_line = max(1, int(effective_width / (font_size * 0.6)))  # Stima caratteri per linea
        lines_available = max(1, int(effective_height / (font_size * 1.2)))  # Linee disponibili
        total_chars_capacity = chars_per_line * lines_available * column_count
        
        # Calcola rischio come rapporto caratteri/capacità
        if total_chars_capacity > 0:
            risk = char_count / total_chars_capacity
        else:
            risk = 1.0  # Massimo rischio se non c'è spazio
        
        return min(risk, 2.0)  # Cap a 2.0 per overflow estremi
    
    def predict_translation_overflow(self, texts: List[str], target_language: str,
                                   frame_metrics: Dict[str, TextFrameMetrics]) -> List[OverflowPrediction]:
        """
        Predice overflow per lista di testi da tradurre
        
        Args:
            texts: Lista testi da tradurre
            target_language: Lingua destinazione
            frame_metrics: Metriche frame associati
            
        Returns:
            Lista predizioni overflow
        """
        predictions = []
        expansion_factor = self.expansion_factors.get(target_language, 1.20)
        
        for i, text in enumerate(texts):
            # Stima lunghezza tradotta
            estimated_length = int(len(text) * expansion_factor)
            
            # Trova frame associato (semplificato - usa metriche medie se non trovato)
            frame_id = f"frame_{i}"
            if frame_metrics:
                # Usa primo frame disponibile o media
                frame_metric = next(iter(frame_metrics.values()))
            else:
                # Frame virtuale con dimensioni standard
                frame_metric = TextFrameMetrics(
                    frame_id=frame_id,
                    width=200.0, height=100.0, x=0.0, y=0.0,
                    column_count=1, column_gutter=12.0,
                    inset_spacing=(6.0, 6.0, 6.0, 6.0),
                    font_size=12.0, leading=14.4,
                    char_count=len(text),
                    estimated_overflow_risk=0.8
                )
            
            # Calcola spazio disponibile in caratteri
            available_chars = self._calculate_available_character_space(frame_metric)
            
            # Calcola rischio overflow
            overflow_risk = estimated_length / max(available_chars, 1)
            
            # Genera suggerimenti
            suggestions = self._generate_overflow_suggestions(
                text, estimated_length, available_chars, overflow_risk
            )
            
            prediction = OverflowPrediction(
                original_text=text,
                estimated_translated_length=estimated_length,
                available_space_chars=available_chars,
                overflow_risk=overflow_risk,
                recommended_max_length=int(available_chars * 0.9),  # 90% dello spazio
                frame_id=frame_metric.frame_id,
                suggestions=suggestions
            )
            
            predictions.append(prediction)
        
        return predictions
    
    def _calculate_available_character_space(self, frame_metric: TextFrameMetrics) -> int:
        """Calcola spazio disponibile in caratteri per un frame"""
        
        # Area effettiva del testo
        top, right, bottom, left = frame_metric.inset_spacing
        effective_width = frame_metric.width - left - right
        effective_height = frame_metric.height - top - bottom
        
        # Considera colonne
        if frame_metric.column_count > 1:
            effective_width = (effective_width - (frame_metric.column_count - 1) * frame_metric.column_gutter) / frame_metric.column_count
        
        # Stima caratteri basata su font
        font_char_width = frame_metric.font_size * 0.6  # Approssimazione larghezza carattere
        chars_per_line = max(1, int(effective_width / font_char_width))
        lines_available = max(1, int(effective_height / frame_metric.leading))
        
        total_chars = chars_per_line * lines_available * frame_metric.column_count
        
        return max(total_chars, 50)  # Minimo 50 caratteri
    
    def _generate_overflow_suggestions(self, text: str, estimated_length: int,
                                     available_chars: int, overflow_risk: float) -> List[str]:
        """Genera suggerimenti per gestire potenziale overflow"""
        suggestions = []
        
        if overflow_risk < self.risk_thresholds['low']:
            suggestions.append("✅ Nessun rischio overflow - traduzione normale")
        
        elif overflow_risk < self.risk_thresholds['medium']:
            suggestions.append("⚠️ Rischio basso - monitorare lunghezza traduzione")
            suggestions.append("💡 Usa traduzioni concise quando possibile")
        
        elif overflow_risk < self.risk_thresholds['high']:
            suggestions.append("⚠️ Rischio medio - richiedi traduzione compatta")
            suggestions.append("💡 Usa abbreviazioni tecniche standard")
            suggestions.append("💡 Rimuovi parole non essenziali")
        
        else:
            suggestions.append("🚨 Rischio alto/critico - azione necessaria")
            suggestions.append("💡 Richiedi traduzione ultra-concisa")
            suggestions.append("💡 Usa abbreviazioni e acronimi")
            suggestions.append("💡 Considera riduzione font size")
            
            if len(text) > 100:
                suggestions.append("💡 Dividi testo in segmenti più piccoli")
        
        # Suggerimenti specifici per lunghezza
        if estimated_length > available_chars:
            reduction_needed = estimated_length - available_chars
            percentage_reduction = (reduction_needed / estimated_length) * 100
            suggestions.append(f"📏 Riduci lunghezza di ~{reduction_needed} caratteri ({percentage_reduction:.1f}%)")
        
        return suggestions
    
    def generate_overflow_report(self, predictions: List[OverflowPrediction],
                               target_language: str) -> Dict[str, Any]:
        """Genera report completo sui rischi overflow"""
        
        total_texts = len(predictions)
        if total_texts == 0:
            return {'error': 'Nessun testo da analizzare'}
        
        # Classifica rischi
        risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        high_risk_texts = []
        
        for pred in predictions:
            if pred.overflow_risk < self.risk_thresholds['low']:
                risk_counts['low'] += 1
            elif pred.overflow_risk < self.risk_thresholds['medium']:
                risk_counts['medium'] += 1
            elif pred.overflow_risk < self.risk_thresholds['high']:
                risk_counts['high'] += 1
            else:
                risk_counts['critical'] += 1
                high_risk_texts.append(pred)
        
        # Calcola statistiche
        avg_overflow_risk = sum(p.overflow_risk for p in predictions) / total_texts
        total_chars_original = sum(len(p.original_text) for p in predictions)
        total_chars_estimated = sum(p.estimated_translated_length for p in predictions)
        
        expansion_factor = self.expansion_factors.get(target_language, 1.20)
        
        report = {
            'summary': {
                'total_texts': total_texts,
                'target_language': target_language,
                'expansion_factor': expansion_factor,
                'average_overflow_risk': round(avg_overflow_risk, 3),
                'total_original_chars': total_chars_original,
                'total_estimated_chars': total_chars_estimated,
                'estimated_expansion': round((total_chars_estimated / max(total_chars_original, 1) - 1) * 100, 1)
            },
            'risk_distribution': risk_counts,
            'risk_percentages': {
                k: round((v / total_texts) * 100, 1) for k, v in risk_counts.items()
            },
            'high_risk_texts': [
                {
                    'text_preview': pred.original_text[:100] + '...' if len(pred.original_text) > 100 else pred.original_text,
                    'overflow_risk': round(pred.overflow_risk, 3),
                    'estimated_length': pred.estimated_translated_length,
                    'available_space': pred.available_space_chars,
                    'recommended_max': pred.recommended_max_length,
                    'suggestions': pred.suggestions[:3]  # Prime 3 suggestions
                }
                for pred in high_risk_texts[:10]  # Max 10 esempi
            ],
            'recommendations': self._generate_global_recommendations(risk_counts, avg_overflow_risk)
        }
        
        return report
    
    def _generate_global_recommendations(self, risk_counts: Dict[str, int], avg_risk: float) -> List[str]:
        """Genera raccomandazioni globali basate sui rischi"""
        recommendations = []
        
        total = sum(risk_counts.values())
        high_risk_percentage = ((risk_counts['high'] + risk_counts['critical']) / max(total, 1)) * 100
        
        if avg_risk < 0.7:
            recommendations.append("✅ Documento a basso rischio overflow - procedi con traduzione standard")
        
        elif avg_risk < 0.9:
            recommendations.append("⚠️ Rischio moderato - usa modalità traduzione compatta")
            recommendations.append("💡 Monitora attentamente i testi più lunghi")
        
        else:
            recommendations.append("🚨 Alto rischio overflow - necessaria strategia preventiva")
            recommendations.append("💡 Usa traduzione ultra-concisa per tutti i testi")
            recommendations.append("💡 Considera pre-processamento per ridurre lunghezza")
        
        if high_risk_percentage > 20:
            recommendations.append(f"📊 {high_risk_percentage:.1f}% dei testi ad alto rischio")
            recommendations.append("💡 Considera revisione manuale delle traduzioni problematiche")
        
        if risk_counts['critical'] > 0:
            recommendations.append(f"🚨 {risk_counts['critical']} testi a rischio critico - richiesta intervento manuale")
        
        return recommendations