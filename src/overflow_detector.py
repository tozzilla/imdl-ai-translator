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
        
        # Keywords che indicano contenuto diagramma/flowchart
        self.diagram_keywords = {
            # Parole chiave tedesche per diagrammi
            'überprüfung', 'inspektion', 'prüfung', 'kontrolle', 'verfahren',
            'dokumentation', 'installation', 'montage', 'wartung', 'funktionalität',
            'komponenten', 'bauteile', 'system', 'verformung', 'beschädigung',
            'effizienz', 'qualität', 'zertifizierung', 'phase', 'schritt',
            'prozess', 'ablauf', 'arbeitsverfahren', 'sichtprüfung', 'funktionsprüfung',
            
            # Parole chiave italiane equivalenti
            'ispezione', 'controllo', 'procedura', 'documentazione', 'installazione',
            'montaggio', 'manutenzione', 'funzionalità', 'componenti', 'sistema',
            'deformazione', 'danneggiamento', 'efficienza', 'qualità', 'certificazione',
            'fase', 'passo', 'processo', 'flusso', 'verifica', 'controllo visivo',
            
            # Termini operativi comuni
            'ja', 'nein', 'ok', 'nicht ok', 'sì', 'no', 'verificare', 'sostituire',
            'riparare', 'mantenere', 'installare', 'rimuovere', 'pulire'
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
    
    def detect_diagram_frames(self, frame_metrics: Dict[str, TextFrameMetrics], 
                            stories_data: Dict) -> Dict[str, Dict]:
        """
        Rileva automaticamente frame che contengono diagrammi o flowchart
        
        Args:
            frame_metrics: Metriche dei frame dal documento
            stories_data: Dati delle stories per analisi testo
            
        Returns:
            Dizionario frame_id -> informazioni diagramma rilevato
        """
        diagram_frames = {}
        
        for frame_id, metrics in frame_metrics.items():
            # Analizza caratteristiche del frame
            diagram_score = self._calculate_diagram_score(metrics, stories_data)
            
            if diagram_score >= 0.6:  # Soglia per considerare un frame come diagramma
                diagram_info = {
                    'diagram_score': diagram_score,
                    'frame_metrics': metrics,
                    'risk_factors': self._identify_diagram_risk_factors(metrics, stories_data),
                    'compression_priority': self._calculate_compression_priority(metrics, diagram_score),
                    'recommended_strategies': self._get_diagram_specific_strategies(metrics, diagram_score)
                }
                diagram_frames[frame_id] = diagram_info
                
                logger.info(f"Rilevato frame diagramma: {frame_id} (score: {diagram_score:.2f})")
        
        return diagram_frames
    
    def _calculate_diagram_score(self, metrics: TextFrameMetrics, stories_data: Dict) -> float:
        """
        Calcola un punteggio (0-1) che indica quanto probabilmente il frame contiene un diagramma
        """
        score = 0.0
        
        # 1. Analisi dimensioni - i diagrammi tendono ad essere più quadrati
        aspect_ratio = metrics.width / max(metrics.height, 1)
        if 0.7 <= aspect_ratio <= 1.4:  # Circa quadrato
            score += 0.2
        elif 0.5 <= aspect_ratio <= 2.0:  # Rettangolare ma non troppo
            score += 0.1
        
        # 2. Analisi densità testo - i diagrammi hanno meno testo per area
        area = metrics.width * metrics.height
        char_density = metrics.char_count / max(area, 1)
        if char_density < 0.5:  # Bassa densità di testo
            score += 0.3
        elif char_density < 1.0:
            score += 0.2
        
        # 3. Analisi contenuto testuale
        text_score = self._analyze_diagram_text_content(metrics, stories_data)
        score += text_score * 0.4  # Peso maggiore per il contenuto
        
        # 4. Analisi font size - i diagrammi spesso usano font più piccoli
        if metrics.font_size <= 10.0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _analyze_diagram_text_content(self, metrics: TextFrameMetrics, stories_data: Dict) -> float:
        """
        Analizza il contenuto testuale per parole chiave tipiche dei diagrammi
        """
        content_score = 0.0
        
        # Cerca il testo associato a questo frame nelle stories
        frame_text = self._extract_frame_text(metrics.frame_id, stories_data)
        if not frame_text:
            return 0.0
        
        text_lower = frame_text.lower()
        keyword_matches = 0
        
        # Conta occorrenze di parole chiave diagramma
        for keyword in self.diagram_keywords:
            if keyword in text_lower:
                keyword_matches += 1
        
        # Punteggio basato su densità di parole chiave
        if keyword_matches >= 3:
            content_score += 0.8
        elif keyword_matches >= 2:
            content_score += 0.6
        elif keyword_matches >= 1:
            content_score += 0.4
        
        # Bonus per pattern tipici di flowchart
        flowchart_patterns = [
            r'\b(ja|nein)\b',  # Decisioni tedesche
            r'\b(sì|no)\b',    # Decisioni italiane
            r'\b(step|schritt|fase)\s*\d+',  # Numerazione passi
            r'->', '→', '↓', '↑',  # Frecce direzionali
            r'\?',  # Punti interrogativi (decisioni)
        ]
        
        for pattern in flowchart_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                content_score += 0.1
        
        return min(content_score, 1.0)
    
    def _extract_frame_text(self, frame_id: str, stories_data: Dict) -> str:
        """
        Estrae il testo associato a un frame dalle stories data
        """
        # Semplificazione: concatena tutto il testo trovato
        # In un'implementazione più sofisticata, dovremmo mappare frame_id a contenuto specifico
        all_text = ""
        
        for story_name, story_data in stories_data.items():
            if 'root' in story_data:
                # Estrai tutto il testo dalla story
                for elem in story_data['root'].iter():
                    if elem.text:
                        all_text += elem.text + " "
                    if elem.tail:
                        all_text += elem.tail + " "
        
        return all_text
    
    def _identify_diagram_risk_factors(self, metrics: TextFrameMetrics, stories_data: Dict) -> List[str]:
        """
        Identifica fattori di rischio specifici per overflow in diagrammi
        """
        risk_factors = []
        
        # 1. Frame piccoli con molto testo
        area = metrics.width * metrics.height
        if area < 10000 and metrics.char_count > 100:  # Area piccola, molto testo
            risk_factors.append("Frame piccolo con testo denso")
        
        # 2. Font size piccolo (difficile da ridurre ulteriormente)
        if metrics.font_size <= 9.0:
            risk_factors.append("Font già molto piccolo")
        
        # 3. Margini stretti
        top, right, bottom, left = metrics.inset_spacing
        if max(top, right, bottom, left) < 3.0:
            risk_factors.append("Margini interni molto stretti")
        
        # 4. Testo con molte parole tecniche lunghe
        frame_text = self._extract_frame_text(metrics.frame_id, stories_data)
        if frame_text:
            avg_word_length = sum(len(word) for word in frame_text.split()) / max(len(frame_text.split()), 1)
            if avg_word_length > 8:  # Parole mediamente lunghe (tipico del tedesco tecnico)
                risk_factors.append("Terminologia tecnica complessa")
        
        # 5. Alto rischio overflow già stimato
        if metrics.estimated_overflow_risk > 1.2:
            risk_factors.append("Alto rischio overflow previsto")
        
        return risk_factors
    
    def _calculate_compression_priority(self, metrics: TextFrameMetrics, diagram_score: float) -> str:
        """
        Calcola priorità di compressione per frame diagramma
        """
        if diagram_score >= 0.8 and metrics.estimated_overflow_risk >= 1.3:
            return "critical"
        elif diagram_score >= 0.7 and metrics.estimated_overflow_risk >= 1.1:
            return "high"
        elif diagram_score >= 0.6:
            return "medium"
        else:
            return "low"
    
    def _get_diagram_specific_strategies(self, metrics: TextFrameMetrics, diagram_score: float) -> List[str]:
        """
        Suggerisce strategie specifiche per diagrammi
        """
        strategies = []
        
        # Strategie base per tutti i diagrammi
        if diagram_score >= 0.6:
            strategies.extend([
                "use_technical_abbreviations",  # Usa abbreviazioni tecniche specifiche
                "compress_procedural_language",  # Comprimi linguaggio procedurale
                "simplify_decision_points"  # Semplifica punti di decisione
            ])
        
        # Strategie aggressive per casi critici
        if diagram_score >= 0.8 or metrics.estimated_overflow_risk >= 1.2:
            strategies.extend([
                "ultra_compact_mode",  # Modalità ultra-compatta
                "remove_redundant_terms",  # Rimuovi termini ridondanti
                "use_symbols_over_words"  # Usa simboli al posto di parole dove possibile
            ])
        
        # Strategie specifiche per font piccoli
        if metrics.font_size <= 9.0:
            strategies.append("avoid_font_reduction")  # Evita ulteriore riduzione font
        
        return strategies
    
    def generate_diagram_detection_report(self, diagram_frames: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Genera report sui diagrammi rilevati
        """
        if not diagram_frames:
            return {
                'summary': {
                    'total_diagrams': 0,
                    'message': 'Nessun frame diagramma rilevato'
                }
            }
        
        # Statistiche di base
        total_diagrams = len(diagram_frames)
        priority_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        avg_score = 0.0
        
        for frame_info in diagram_frames.values():
            priority = frame_info['compression_priority']
            priority_counts[priority] += 1
            avg_score += frame_info['diagram_score']
        
        avg_score /= total_diagrams
        
        # Identifica i più problematici
        critical_frames = [
            (frame_id, info) for frame_id, info in diagram_frames.items()
            if info['compression_priority'] == 'critical'
        ]
        
        report = {
            'summary': {
                'total_diagrams': total_diagrams,
                'average_diagram_score': round(avg_score, 3),
                'priority_distribution': priority_counts,
                'critical_frames_count': len(critical_frames)
            },
            'critical_frames': [
                {
                    'frame_id': frame_id,
                    'diagram_score': info['diagram_score'],
                    'risk_factors': info['risk_factors'],
                    'recommended_strategies': info['recommended_strategies'][:3]  # Prime 3
                }
                for frame_id, info in critical_frames[:5]  # Max 5 esempi
            ],
            'recommendations': self._generate_diagram_recommendations(diagram_frames, priority_counts),
            'next_steps': [
                "Applicare compressione ultra-aggressiva ai frame critici",
                "Verificare manualmente i diagrammi più complessi",
                "Considerare riduzione margini per frame ad alta densità",
                "Testare leggibilità dopo compressione testo"
            ]
        }
        
        return report
    
    def _generate_diagram_recommendations(self, diagram_frames: Dict[str, Dict], 
                                        priority_counts: Dict[str, int]) -> List[str]:
        """
        Genera raccomandazioni basate sui diagrammi rilevati
        """
        recommendations = []
        
        total = sum(priority_counts.values())
        critical_percentage = (priority_counts['critical'] / max(total, 1)) * 100
        
        if critical_percentage > 30:
            recommendations.append("🚨 Alto numero di diagrammi critici - richiede intervento manuale")
            recommendations.append("💡 Considera pre-processing aggressivo per ridurre complessità")
        elif critical_percentage > 10:
            recommendations.append("⚠️ Alcuni diagrammi critici - monitora attentamente")
        else:
            recommendations.append("✅ Maggior parte dei diagrammi gestibili automaticamente")
        
        if priority_counts['critical'] + priority_counts['high'] > total * 0.5:
            recommendations.append("💡 Attiva modalità --diagram-mode per ottimizzazioni specifiche")
        
        if total > 10:
            recommendations.append("📊 Documento ricco di diagrammi - considera workflow specializzato")
            
        return recommendations