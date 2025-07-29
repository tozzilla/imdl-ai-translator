"""
Overflow Manager - Gestisce risoluzione overflow e modifiche frame
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from overflow_detector import OverflowPrediction, TextFrameMetrics

logger = logging.getLogger(__name__)

@dataclass
class OverflowResolution:
    """Risultato risoluzione overflow"""
    original_text: str
    resolved_text: str
    resolution_method: str
    space_saved: int
    success: bool
    notes: str

@dataclass
class FrameAdjustment:
    """Regolazione proposta per un frame"""
    frame_id: str
    adjustment_type: str  # 'resize', 'font_size', 'leading', 'inset'
    original_value: float
    new_value: float
    expected_benefit: str

class OverflowManager:
    """Manager per gestire e risolvere overflow di testo"""
    
    def __init__(self):
        """Inizializza manager con strategie di risoluzione"""
        
        # Strategie di compressione testo ordinate per priorità
        self.compression_strategies = [
            'remove_redundancy',     # Rimuovi ridondanze
            'use_abbreviations',     # Usa abbreviazioni
            'simplify_language',     # Semplifica linguaggio
            'remove_optional_words', # Rimuovi parole opzionali
            'compact_numbers',       # Compatta numeri e unità
        ]
        
        # Dizionario abbreviazioni tecniche tedesche
        self.german_abbreviations = {
            # Misure e unità
            'millimetro': 'mm',
            'millimetri': 'mm', 
            'centimetro': 'cm',
            'centimetri': 'cm',
            'chilogrammo': 'kg',
            'chilogrammi': 'kg',
            'kilonewton': 'kN',
            'metri quadri': 'm²',
            'metro quadro': 'm²',
            
            # Termini tecnici
            'installazione': 'Install.',
            'montaggio': 'Mont.',
            'verificare': 'verif.',
            'controllare': 'kontroll.',
            'assicurare': 'sicherstell.',
            'utilizzare': 'verwend.',
            'secondo': 'gem.',
            'conforme': 'gem.',
            'istruzioni': 'Anweis.',
            'manuale': 'Handb.',
            'documento': 'Dok.',
            'pagina': 'S.',
            'figura': 'Abb.',
            'tabella': 'Tab.',
            'capitolo': 'Kap.',
            'sezione': 'Abschn.',
            'paragrafo': 'Abs.',
            
            # Frasi comuni
            'per maggiori informazioni': 'für Details',
            'come mostrato nella figura': 'siehe Abb.',
            'secondo le istruzioni': 'gem. Anweis.',
            'in base al tipo': 'je nach Typ',
            'durante il montaggio': 'bei Mont.',
            
            # Sicurezza
            'dispositivo di protezione individuale': 'PSA',
            'equipaggiamento di protezione individuale': 'PSA',
            'dispositivo anticaduta': 'Absturzsich.',
            'sistema di sicurezza': 'Sich.syst.',
        }
        
        # Pattern per rimuovere ridondanze
        self.redundancy_patterns = [
            # Ripetizioni
            (r'\b(\w+)\s+\1\b', r'\1'),  # parola ripetuta
            (r'\b(der|die|das)\s+(der|die|das)\b', r'\1'),  # articoli doppi
            
            # Frasi verbali ridondanti
            (r'es ist notwendig zu', 'zu'),
            (r'es ist wichtig zu', 'zu'),
            (r'stellen Sie sicher, dass', 'sicherstellen:'),
            (r'achten Sie darauf, dass', 'beachten:'),
            
            # Riduzioni di cortesia
            (r'bitte beachten Sie', 'beachten'),
            (r'wir empfehlen', 'empfohlen:'),
            (r'es wird empfohlen', 'empfohlen:'),
            
            # Connettori ridondanti
            (r'darüber hinaus', 'außerdem'),
            (r'zusätzlich dazu', 'zusätzlich'),
            (r'abgesehen davon', 'außerdem'),
        ]
        
        # Parole opzionali removibili in contesto tecnico
        self.optional_words = {
            'auch', 'noch', 'bereits', 'schon', 'dann', 'danach', 
            'dabei', 'hierzu', 'dazu', 'außerdem', 'zusätzlich',
            'entsprechend', 'jeweilig', 'gegebenenfalls', 'eventuell'
        }
        
    def resolve_overflow_predictions(self, predictions: List[OverflowPrediction],
                                   max_iterations: int = 3) -> List[OverflowResolution]:
        """
        Risolve predizioni overflow con strategie multiple
        
        Args:
            predictions: Lista predizioni overflow
            max_iterations: Massimo numero iterazioni per testo
            
        Returns:
            Lista risoluzioni overflow
        """
        resolutions = []
        
        for pred in predictions:
            if pred.overflow_risk <= 1.0:
                # Nessun overflow previsto
                resolution = OverflowResolution(
                    original_text=pred.original_text,
                    resolved_text=pred.original_text,
                    resolution_method='no_action_needed',
                    space_saved=0,
                    success=True,
                    notes='Nessun overflow previsto'
                )
            else:
                # Tenta risoluzione overflow
                resolution = self._resolve_single_overflow(pred, max_iterations)
            
            resolutions.append(resolution)
        
        return resolutions
    
    def _resolve_single_overflow(self, prediction: OverflowPrediction,
                               max_iterations: int) -> OverflowResolution:
        """Risolve overflow per singolo testo"""
        
        current_text = prediction.original_text
        target_length = prediction.recommended_max_length
        methods_used = []
        total_saved = 0
        
        logger.debug(f"Risoluzione overflow: {len(current_text)} -> {target_length} caratteri")
        
        # Applica strategie in ordine di priorità
        for iteration in range(max_iterations):
            if len(current_text) <= target_length:
                break
                
            # Prova ogni strategia
            for strategy in self.compression_strategies:
                previous_length = len(current_text)
                current_text = self._apply_compression_strategy(current_text, strategy)
                saved = previous_length - len(current_text)
                
                if saved > 0:
                    methods_used.append(strategy)
                    total_saved += saved
                    logger.debug(f"Strategia {strategy}: salvati {saved} caratteri")
                
                if len(current_text) <= target_length:
                    break
        
        # Verifica successo
        success = len(current_text) <= target_length
        final_length = len(current_text)
        
        notes = f"Lunghezza finale: {final_length}/{target_length}. "
        if methods_used:
            notes += f"Strategie: {', '.join(methods_used)}"
        else:
            notes += "Nessuna compressione applicata"
        
        return OverflowResolution(
            original_text=prediction.original_text,
            resolved_text=current_text,
            resolution_method='+'.join(methods_used) if methods_used else 'no_compression',
            space_saved=total_saved,
            success=success,
            notes=notes
        )
    
    def _apply_compression_strategy(self, text: str, strategy: str) -> str:
        """Applica strategia di compressione specifica"""
        
        if strategy == 'remove_redundancy':
            return self._remove_redundancy(text)
        
        elif strategy == 'use_abbreviations':
            return self._apply_abbreviations(text)
        
        elif strategy == 'simplify_language':
            return self._simplify_language(text)
        
        elif strategy == 'remove_optional_words':
            return self._remove_optional_words(text)
        
        elif strategy == 'compact_numbers':
            return self._compact_numbers(text)
        
        return text
    
    def _remove_redundancy(self, text: str) -> str:
        """Rimuove ridondanze dal testo"""
        result = text
        
        for pattern, replacement in self.redundancy_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Rimuovi spazi multipli
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def _apply_abbreviations(self, text: str) -> str:
        """Applica abbreviazioni tecniche"""
        result = text
        
        # Applica abbreviazioni dal dizionario
        for full_term, abbrev in self.german_abbreviations.items():
            # Usa word boundaries per sostituzioni precise
            pattern = r'\b' + re.escape(full_term) + r'\b'
            result = re.sub(pattern, abbrev, result, flags=re.IGNORECASE)
        
        return result
    
    def _simplify_language(self, text: str) -> str:
        """Semplifica costruzioni linguistiche complesse"""
        result = text
        
        # Semplificazioni grammaticali tedesche
        simplifications = [
            # Passivo -> attivo (più corto)
            (r'wird\s+(\w+)', r'\1t'),  # "wird gemacht" -> "macht"
            
            # Riduci costruzioni relative
            (r',\s*der\s+(\w+)\s+ist', r' (\1)'),
            (r',\s*die\s+(\w+)\s+ist', r' (\1)'),
            (r',\s*das\s+(\w+)\s+ist', r' (\1)'),
            
            # Riduci costruzioni preposizionali
            (r'in\s+der\s+Regel', 'normalerweise'),
            (r'im\s+Falle\s+von', 'bei'),
            (r'mit\s+Hilfe\s+von', 'mit'),
            (r'aufgrund\s+von', 'wegen'),
            
            # Riduci forme composte
            (r'sowohl\s+(\w+)\s+als\s+auch\s+(\w+)', r'\1 und \2'),
            (r'nicht\s+nur\s+(\w+)\s+sondern\s+auch\s+(\w+)', r'\1 und \2'),
        ]
        
        for pattern, replacement in simplifications:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _remove_optional_words(self, text: str) -> str:
        """Rimuove parole opzionali non essenziali"""
        words = text.split()
        filtered_words = []
        
        for word in words:
            # Rimuovi punteggiatura per controllo
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Mantieni parola se non è opzionale
            if clean_word not in self.optional_words:
                filtered_words.append(word)
            else:
                logger.debug(f"Rimossa parola opzionale: {word}")
        
        return ' '.join(filtered_words)
    
    def _compact_numbers(self, text: str) -> str:
        """Compatta numeri e unità di misura"""
        result = text
        
        # Compattazioni numeriche
        compactions = [
            # Numeri con virgola -> punto per brevità
            (r'(\d+),(\d+)', r'\1.\2'),
            
            # Range numerici
            (r'von\s+(\d+)\s+bis\s+(\d+)', r'\1-\2'),
            (r'zwischen\s+(\d+)\s+und\s+(\d+)', r'\1-\2'),
            
            # Unità con spazi -> senza spazi dove possibile
            (r'(\d+)\s+x\s+(\d+)', r'\1x\2'),
            (r'(\d+)\s+/\s+(\d+)', r'\1/\2'),
            
            # Percentuali
            (r'(\d+)\s+Prozent', r'\1%'),
            (r'(\d+)\s+prozent', r'\1%'),
        ]
        
        for pattern, replacement in compactions:
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def suggest_frame_adjustments(self, frame_metrics: Dict[str, TextFrameMetrics],
                                predictions: List[OverflowPrediction]) -> List[FrameAdjustment]:
        """Suggerisce regolazioni ai frame per ridurre overflow"""
        adjustments = []
        
        # Crea mappa predizioni per frame
        pred_by_frame = {}
        for pred in predictions:
            if pred.overflow_risk > 1.0:  # Solo frame con overflow
                pred_by_frame[pred.frame_id] = pred
        
        for frame_id, frame_metric in frame_metrics.items():
            if frame_id not in pred_by_frame:
                continue
                
            prediction = pred_by_frame[frame_id]
            
            # Suggerimento 1: Riduzione font size
            if frame_metric.font_size > 8.0:
                new_font_size = max(8.0, frame_metric.font_size * 0.9)
                space_gain = ((frame_metric.font_size / new_font_size) ** 2 - 1) * 100
                
                adjustments.append(FrameAdjustment(
                    frame_id=frame_id,
                    adjustment_type='font_size',
                    original_value=frame_metric.font_size,
                    new_value=new_font_size,
                    expected_benefit=f"~{space_gain:.1f}% più spazio"
                ))
            
            # Suggerimento 2: Riduzione leading (interlinea)
            if frame_metric.leading > frame_metric.font_size * 1.1:
                new_leading = frame_metric.font_size * 1.1
                lines_gained = (frame_metric.leading - new_leading) / frame_metric.leading
                
                adjustments.append(FrameAdjustment(
                    frame_id=frame_id,
                    adjustment_type='leading',
                    original_value=frame_metric.leading,
                    new_value=new_leading,
                    expected_benefit=f"~{lines_gained*100:.1f}% più linee"
                ))
            
            # Suggerimento 3: Riduzione margini interni
            top, right, bottom, left = frame_metric.inset_spacing
            if max(top, right, bottom, left) > 3.0:
                new_inset = max(3.0, max(top, right, bottom, left) * 0.7)
                space_gain = ((sum(frame_metric.inset_spacing) - new_inset * 4) / 
                            (frame_metric.width * frame_metric.height)) * 100
                
                adjustments.append(FrameAdjustment(
                    frame_id=frame_id,
                    adjustment_type='inset',
                    original_value=max(top, right, bottom, left),
                    new_value=new_inset,
                    expected_benefit=f"~{space_gain:.1f}% più area"
                ))
            
            # Suggerimento 4: Resize frame (se possibile)
            overflow_amount = prediction.estimated_translated_length - prediction.available_space_chars
            if overflow_amount > 0:
                height_increase = (overflow_amount / prediction.available_space_chars) * frame_metric.height * 0.5
                new_height = frame_metric.height + height_increase
                
                adjustments.append(FrameAdjustment(
                    frame_id=frame_id,
                    adjustment_type='resize',
                    original_value=frame_metric.height,
                    new_value=new_height,
                    expected_benefit=f"Elimina overflow di {overflow_amount} caratteri"
                ))
        
        return adjustments
    
    def apply_text_compression(self, texts: List[str], target_reductions: List[int]) -> List[str]:
        """
        Applica compressione testo con target specifici
        
        Args:
            texts: Lista testi da comprimere
            target_reductions: Lista percentuali riduzione desiderata per ogni testo
            
        Returns:
            Lista testi compressi
        """
        compressed_texts = []
        
        for text, target_reduction in zip(texts, target_reductions):
            if target_reduction <= 0:
                compressed_texts.append(text)
                continue
            
            target_length = int(len(text) * (1 - target_reduction / 100))
            
            # Crea predizione mock per usare il sistema di risoluzione
            mock_prediction = OverflowPrediction(
                original_text=text,
                estimated_translated_length=len(text),
                available_space_chars=target_length,
                overflow_risk=len(text) / target_length,
                recommended_max_length=target_length,
                frame_id="mock_frame",
                suggestions=[]
            )
            
            # Risolvi overflow
            resolution = self._resolve_single_overflow(mock_prediction, max_iterations=3)
            compressed_texts.append(resolution.resolved_text)
            
            logger.info(f"Compressione: {len(text)} -> {len(resolution.resolved_text)} "
                       f"(-{resolution.space_saved} caratteri)")
        
        return compressed_texts
    
    def generate_compression_report(self, resolutions: List[OverflowResolution]) -> Dict[str, Any]:
        """Genera report sulle compressioni applicate"""
        
        total_texts = len(resolutions)
        successful_resolutions = sum(1 for r in resolutions if r.success)
        total_space_saved = sum(r.space_saved for r in resolutions)
        
        # Analisi metodi utilizzati
        method_usage = {}
        for resolution in resolutions:
            if resolution.resolution_method != 'no_action_needed':
                methods = resolution.resolution_method.split('+')
                for method in methods:
                    method_usage[method] = method_usage.get(method, 0) + 1
        
        # Trova casi problematici
        failed_resolutions = [r for r in resolutions if not r.success and r.resolution_method != 'no_action_needed']
        
        report = {
            'summary': {
                'total_texts': total_texts,
                'successful_resolutions': successful_resolutions,
                'success_rate': round((successful_resolutions / max(total_texts, 1)) * 100, 1),
                'total_space_saved': total_space_saved,
                'average_space_saved': round(total_space_saved / max(total_texts, 1), 1)
            },
            'method_usage': method_usage,
            'failed_resolutions': len(failed_resolutions),
            'failed_examples': [
                {
                    'original_length': len(r.original_text),
                    'final_length': len(r.resolved_text),
                    'text_preview': r.original_text[:100] + '...' if len(r.original_text) > 100 else r.original_text,
                    'notes': r.notes
                }
                for r in failed_resolutions[:5]  # Max 5 esempi
            ],
            'recommendations': self._generate_compression_recommendations(resolutions, method_usage)
        }
        
        return report
    
    def _generate_compression_recommendations(self, resolutions: List[OverflowResolution], 
                                           method_usage: Dict[str, int]) -> List[str]:
        """Genera raccomandazioni basate sui risultati compressione"""
        recommendations = []
        
        total_resolutions = len([r for r in resolutions if r.resolution_method != 'no_action_needed'])
        success_rate = sum(1 for r in resolutions if r.success) / max(len(resolutions), 1)
        
        if success_rate > 0.9:
            recommendations.append("✅ Ottimo tasso di successo compressione")
        elif success_rate > 0.7:
            recommendations.append("⚠️ Buon tasso di successo, migliorabile")
        else:
            recommendations.append("🚨 Basso tasso di successo - rivedere strategie")
        
        # Analizza metodi più efficaci
        if method_usage:
            most_used = max(method_usage.items(), key=lambda x: x[1])
            recommendations.append(f"💡 Metodo più efficace: {most_used[0]} (usato {most_used[1]} volte)")
        
        # Suggerimenti specifici
        failed_count = len([r for r in resolutions if not r.success])
        if failed_count > 0:
            recommendations.append(f"📋 {failed_count} testi richiedono intervento manuale")
            recommendations.append("💡 Considera regolazione font size o frame per casi critici")
        
        return recommendations